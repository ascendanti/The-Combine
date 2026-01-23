#!/usr/bin/env python3
"""Session stop hook: Store session learnings.

Runs on session end to persist important learnings.
Reads from environment or stdin for session summary.
"""

import sys
import json
import os
from pathlib import Path

# Add daemon to path
daemon_path = Path(__file__).parent.parent.parent / "daemon"
sys.path.insert(0, str(daemon_path))

def main():
    try:
        # Read hook input
        hook_input = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else {}

        # Check for learnings marker in transcript
        transcript = hook_input.get("transcript_summary", "")
        stop_reason = hook_input.get("stop_reason", "")

        # Only store if session had meaningful work
        if len(transcript) < 100:
            print(json.dumps({"continue": True}))
            return

        from memory import Memory
        mem = Memory()

        # Auto-extract and store key learnings
        # In practice, this would parse the transcript for [LEARNING] markers
        # For now, we store a session summary

        session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")

        mem.store_learning(
            content=f"Session completed: {transcript[:200]}...",
            context=f"Session {session_id}, stop_reason: {stop_reason}",
            tags=["session", "auto-captured"],
            confidence="medium"
        )

        print(json.dumps({
            "continue": True,
            "message": "[Memory] Session learning stored"
        }))

    except Exception as e:
        # Don't block on errors
        print(json.dumps({"continue": True}))

if __name__ == "__main__":
    main()
