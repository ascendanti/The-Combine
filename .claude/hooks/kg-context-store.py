#!/usr/bin/env python3
"""
KG Context Store - PostToolUse Hook (Async LLM Pattern)

Based on claude-context-extender's LLM summarization approach:
- Does NOT generate summaries inline (would block)
- Queues files for async LLM summarization via task_queue
- Worker (kg-summary-worker.py) processes queue with model_router

This follows the user's directive: "adapt something effective from
one of the repos" rather than using heuristic extraction.

Part of token efficiency architecture (Phase 11).
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# File extensions worth caching
CODE_EXTENSIONS = {'.py', '.ts', '.tsx', '.js', '.jsx', '.go', '.rs', '.java'}
DOC_EXTENSIONS = {'.md', '.txt', '.rst', '.yaml', '.yml', '.json'}
CACHEABLE = CODE_EXTENSIONS | DOC_EXTENSIONS

# Min content length to queue for summarization
MIN_CONTENT_LENGTH = 200

# Task queue location (daemon directory)
DAEMON_DIR = Path(__file__).parent.parent.parent / 'daemon'


def queue_for_summarization(file_path: str, content: str):
    """
    Queue file for async LLM summarization.

    Uses the existing task_queue infrastructure which:
    - Persists tasks to SQLite
    - Supports priorities
    - Can be processed by a background worker
    """
    try:
        # Import task queue from daemon
        sys.path.insert(0, str(DAEMON_DIR))
        from task_queue import TaskQueue, TaskPriority

        queue = TaskQueue(DAEMON_DIR / "tasks.db")

        # Create summarization task
        # The worker will use model_router which routes SUMMARIZE tasks to LocalAI (FREE)
        task = queue.add_task(
            prompt=f"SUMMARIZE_FILE",
            priority=TaskPriority.LOW,  # Background, non-urgent
            metadata={
                "type": "file_summarization",
                "file_path": file_path,
                "file_name": Path(file_path).name,
                "content_length": len(content),
                # Store truncated content for summarization (first 8000 chars)
                "content_preview": content[:8000] if len(content) > 8000 else content,
                "queued_at": datetime.now().isoformat()
            }
        )
        return task.id
    except Exception as e:
        # Silently fail - don't disrupt workflow
        return None


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print('{}')
        return

    tool_name = input_data.get('tool_name', '')
    tool_response = input_data.get('tool_response', {})

    # Only process Read tool
    if tool_name != 'Read':
        print('{}')
        return

    # Get file path and content
    file_path = input_data.get('tool_input', {}).get('file_path', '')
    content = tool_response if isinstance(tool_response, str) else str(tool_response)

    if not file_path or len(content) < MIN_CONTENT_LENGTH:
        print('{}')
        return

    # Check if cacheable
    path = Path(file_path)
    if path.suffix.lower() not in CACHEABLE:
        print('{}')
        return

    # Queue for async LLM summarization
    try:
        task_id = queue_for_summarization(file_path, content)

        if task_id:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": f"[Queued for LLM summarization: {path.name}]"
                }
            }
            print(json.dumps(output))
        else:
            print('{}')
    except Exception:
        # Silently fail - don't disrupt workflow
        print('{}')


if __name__ == '__main__':
    main()
