#!/usr/bin/env python3
"""
KG Summary Worker - Async LLM Summarization

Background worker that:
1. Processes file summarization tasks from queue
2. Uses model_router to generate LLM summaries (routes to LocalAI = FREE)
3. Stores summaries to Knowledge Graph

Based on claude-context-extender's IndexManager pattern:
- LLM-generated summaries (not heuristic)
- Keyword extraction for search
- Semantic understanding over pattern matching

Usage:
    python daemon/kg_summary_worker.py         # Run once (process pending)
    python daemon/kg_summary_worker.py --watch # Watch mode (continuous)

Part of token efficiency architecture (Phase 11).
"""

import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Local imports
from task_queue import TaskQueue, TaskStatus
from model_router import ModelRouter, TaskType

# Knowledge Graph storage
KG_PATH = Path.home() / '.claude' / 'memory' / 'knowledge-graph.jsonl'

# Summarization prompt (following claude-context-extender pattern)
SUMMARIZATION_PROMPT = """Analyze this code/document and provide:
1. SUMMARY: A concise 2-3 sentence summary of what this file does
2. KEYWORDS: 5-10 keywords/concepts for search (comma-separated)
3. PURPOSE: Primary purpose (one of: config, utility, api, component, test, docs, model, service)

Format your response exactly as:
SUMMARY: <your summary>
KEYWORDS: <keyword1>, <keyword2>, ...
PURPOSE: <purpose>

Content to analyze:
{content}
"""


def parse_llm_response(response: str) -> Dict[str, str]:
    """Parse structured LLM response into fields."""
    result = {
        "summary": "",
        "keywords": "",
        "purpose": "unknown"
    }

    if not response:
        return result

    lines = response.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line.upper().startswith('SUMMARY:'):
            result["summary"] = line[8:].strip()
        elif line.upper().startswith('KEYWORDS:'):
            result["keywords"] = line[9:].strip()
        elif line.upper().startswith('PURPOSE:'):
            result["purpose"] = line[8:].strip().lower()

    return result


def store_to_kg(file_name: str, file_path: str, summary: str,
               keywords: str, purpose: str):
    """Store LLM-generated summary to Knowledge Graph JSONL."""
    KG_PATH.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().isoformat()
    entity_name = f"file:{file_name}"

    # Create entity entry (following claude-context-extender's chunk structure)
    entity = {
        "type": "entity",
        "name": entity_name,
        "entityType": "file_cache",
        "observations": [
            f"SUMMARY:{summary}",
            f"KEYWORDS:{keywords}",
            f"PURPOSE:{purpose}",
            f"CACHED:{timestamp}",
            f"PATH:{file_path}",
            f"SOURCE:llm"  # Mark as LLM-generated (not heuristic)
        ]
    }

    # Append to JSONL
    with open(KG_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entity) + '\n')

    return entity_name


def process_summarization_task(task, router: ModelRouter) -> bool:
    """Process a single file summarization task."""
    metadata = task.metadata or {}

    if metadata.get("type") != "file_summarization":
        return False

    file_path = metadata.get("file_path", "")
    file_name = metadata.get("file_name", "")
    content = metadata.get("content_preview", "")

    if not content or not file_name:
        return False

    print(f"  Summarizing: {file_name}")

    # Use model_router to generate summary
    # SUMMARIZE task type routes to LocalAI (FREE) when available
    prompt = SUMMARIZATION_PROMPT.format(content=content[:6000])

    try:
        result = router.route(
            task="summarize",  # Triggers SUMMARIZE classification → LocalAI
            content=prompt
        )

        # If routed to Claude (LocalAI unavailable), result has response=None
        # In that case, we'd need to handle differently, but for now just use what we get
        response = result.get("response", "")

        if response:
            parsed = parse_llm_response(response)

            if parsed["summary"]:
                store_to_kg(
                    file_name=file_name,
                    file_path=file_path,
                    summary=parsed["summary"],
                    keywords=parsed["keywords"],
                    purpose=parsed["purpose"]
                )
                print(f"    [OK] Stored to KG: {parsed['summary'][:60]}...")
                return True
            else:
                print(f"    [FAIL] Could not parse response")
                return False
        else:
            # LocalAI unavailable, Claude pass-through indicated
            print(f"    [SKIP] LocalAI unavailable, skipping (would cost tokens)")
            return False

    except Exception as e:
        print(f"    [ERR] Error: {e}")
        return False


def run_worker(watch: bool = False, interval: int = 30):
    """Run the summary worker."""
    print("KG Summary Worker")
    print("=" * 40)

    queue = TaskQueue()
    router = ModelRouter()

    # Check LocalAI availability
    if router.localai.available():
        print("[OK] LocalAI available (FREE summarization)")
    else:
        print("[WARN] LocalAI unavailable (summaries will be skipped)")

    while True:
        # Get pending summarization tasks
        pending = queue.get_pending_tasks(limit=50)
        summarization_tasks = [
            t for t in pending
            if t.prompt == "SUMMARIZE_FILE"
        ]

        if summarization_tasks:
            print(f"\nProcessing {len(summarization_tasks)} tasks...")

            for task in summarization_tasks:
                # Mark in progress
                queue.mark_in_progress(task.id)

                try:
                    success = process_summarization_task(task, router)

                    if success:
                        queue.mark_completed(task.id, "Summary stored to KG")
                    else:
                        queue.mark_failed(task.id, "Could not generate summary")
                except Exception as e:
                    queue.mark_failed(task.id, str(e))

        if not watch:
            print("\nDone. Run with --watch for continuous mode.")
            break

        print(f"\nWaiting {interval}s for new tasks...")
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description='KG Summary Worker')
    parser.add_argument('--watch', action='store_true',
                       help='Watch mode - continuously process queue')
    parser.add_argument('--interval', type=int, default=30,
                       help='Check interval in seconds (default: 30)')
    parser.add_argument('--stats', action='store_true',
                       help='Show queue stats')

    args = parser.parse_args()

    if args.stats:
        queue = TaskQueue()
        pending = [t for t in queue.get_pending_tasks(100)
                  if t.prompt == "SUMMARIZE_FILE"]
        print(f"Pending summarization tasks: {len(pending)}")
        return

    run_worker(watch=args.watch, interval=args.interval)


if __name__ == "__main__":
    main()
