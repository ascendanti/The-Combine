#!/usr/bin/env python3
"""
Context Router - HOT/WARM/COLD context management

Implements progressive disclosure:
- HOT: Always injected (task.md, CLAUDE.md)
- WARM: Injected when keywords detected
- COLD: Referenced only, load on explicit request

Based on claude-cognitive and claude-modular patterns.
"""

import json
import sys
import re
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.parent

# Context tiers
HOT_FILES = ["task.md", ".claude/CLAUDE.md"]

WARM_TRIGGERS = {
    "evolution|phase|progress": ["EVOLUTION-PLAN.md"],
    "handoff|continue|resume": ["thoughts/handoffs"],
    "memory|learning|recall": ["daemon/memory.py"],
    "book|pdf|ingest": [".claude/scripts/book-ingest.py", "daemon/book_watcher.py"],
}

def get_relevant_warm_files(query: str) -> list:
    """Find WARM files relevant to the query."""
    relevant = []
    query_lower = query.lower()

    for pattern, files in WARM_TRIGGERS.items():
        if re.search(pattern, query_lower):
            relevant.extend(files)

    return relevant

def main():
    try:
        hook_input = json.load(sys.stdin)

        # Get user message if available
        messages = hook_input.get("messages", [])
        last_user_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break

        # Find relevant WARM files
        warm_files = get_relevant_warm_files(last_user_msg)

        if warm_files:
            # Suggest loading these files
            suggestions = ", ".join(warm_files[:3])
            print(json.dumps({
                "continue": True,
                "message": f"📂 Context hint: Consider loading {suggestions}"
            }))
        else:
            print(json.dumps({"continue": True}))

    except Exception as e:
        print(json.dumps({"continue": True}))

if __name__ == "__main__":
    main()
