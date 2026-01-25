#!/usr/bin/env python3
"""
KG Context Gate - PreToolUse Hook (Revised)

Based on claude-context-extender pattern:
- Don't BLOCK reads - inject cached summary as ADDITIONAL context
- Use LLM-generated summaries stored in KG
- Falls back gracefully if no cache

This doesn't limit understanding - it AUGMENTS with prior context.

Part of token efficiency architecture (Phase 11).
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Cache validity (hours)
CACHE_TTL_HOURS = 24

# File extensions worth caching
CACHEABLE = {'.py', '.ts', '.tsx', '.js', '.jsx', '.go', '.rs', '.md', '.txt'}


def query_kg_summary(file_name: str) -> dict | None:
    """Query knowledge graph for a file summary."""
    try:
        kg_path = Path.home() / '.claude' / 'memory' / 'knowledge-graph.jsonl'
        if not kg_path.exists():
            return None

        entity_name = f"file:{file_name}"

        with open(kg_path, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get('type') == 'entity' and entry.get('name') == entity_name:
                        return entry
                except json.JSONDecodeError:
                    continue
        return None
    except Exception:
        return None


def extract_observation(entity: dict, prefix: str) -> str | None:
    """Extract observation value by prefix."""
    if not entity:
        return None

    for obs in entity.get('observations', []):
        if isinstance(obs, str) and obs.startswith(f'{prefix}:'):
            return obs[len(prefix) + 1:].strip()
    return None


def is_cache_fresh(entity: dict) -> bool:
    """Check if cached entry is still valid."""
    cached_at = extract_observation(entity, 'CACHED')
    if not cached_at:
        return False

    try:
        cached_time = datetime.fromisoformat(cached_at)
        return datetime.now() - cached_time < timedelta(hours=CACHE_TTL_HOURS)
    except (ValueError, TypeError):
        return False


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print('{}')
        return

    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})

    # Only process Read tool
    if tool_name != 'Read':
        print('{}')
        return

    file_path = tool_input.get('file_path', '')
    if not file_path:
        print('{}')
        return

    path = Path(file_path)

    # Check if cacheable file type
    if path.suffix.lower() not in CACHEABLE:
        print('{}')
        return

    # Query KG for cached summary
    entity = query_kg_summary(path.name)

    if entity and is_cache_fresh(entity):
        summary = extract_observation(entity, 'SUMMARY')
        keywords = extract_observation(entity, 'KEYWORDS')

        if summary:
            # INJECT context, don't block
            # This AUGMENTS understanding rather than limiting it
            context = f"""[KG Prior Context for {path.name}]
Summary: {summary}
"""
            if keywords:
                context += f"Keywords: {keywords}\n"

            context += "(Full file content follows - summary from prior session)"

            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    # additionalContext gets injected into Claude's view
                    "additionalContext": context
                }
            }
            print(json.dumps(output))
            return

    # No cache - allow read normally
    print('{}')


if __name__ == '__main__':
    main()
