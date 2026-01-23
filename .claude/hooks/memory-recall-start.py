#!/usr/bin/env python3
"""Session start hook: Recall relevant memories.

Runs on session start to load context from previous sessions.
"""

import sys
import json
from pathlib import Path

# Add daemon to path
daemon_path = Path(__file__).parent.parent.parent / "daemon"
sys.path.insert(0, str(daemon_path))

def main():
    try:
        from memory import Memory
        mem = Memory()

        # Get recent learnings to prime context
        learnings = mem.recall_learnings("session context preferences patterns", k=5)
        decisions = mem.recall_decisions("architecture")

        output = {
            "continue": True,
            "stopReason": None
        }

        if learnings or decisions:
            memories = []
            for l in learnings[:3]:
                memories.append(f"- [{l.confidence}] {l.content}")
            for d in decisions[:2]:
                memories.append(f"- [decision] {d.decision}")

            if memories:
                output["message"] = "[Memory] Recalled from previous sessions:\n" + "\n".join(memories)

        print(json.dumps(output))

    except Exception as e:
        # Don't block on errors
        print(json.dumps({
            "continue": True,
            "stopReason": None
        }))

if __name__ == "__main__":
    main()
