#!/usr/bin/env python3
"""Clean session start hook - consolidates startup tasks."""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add daemon to path
daemon_path = Path(__file__).parent.parent.parent / "daemon"
sys.path.insert(0, str(daemon_path))

def get_latest_handoff():
    """Find most recent handoff file."""
    handoffs_dir = Path(__file__).parent.parent.parent / "thoughts" / "handoffs"
    if not handoffs_dir.exists():
        return None

    files = sorted(handoffs_dir.glob("*.yaml"), key=lambda f: f.stat().st_mtime, reverse=True)
    return files[0].name if files else None

def main():
    output = {"continue": True, "stopReason": None}
    messages = []

    # Check for handoffs
    latest = get_latest_handoff()
    if latest:
        messages.append(f"Handoff: {latest}")

    # Try memory recall
    try:
        from memory import Memory
        mem = Memory()
        learnings = mem.recall_learnings("session", k=2)
        if learnings:
            messages.append(f"Memory: {len(learnings)} relevant items")
    except:
        pass

    # Compose output
    if messages:
        output["message"] = " | ".join(messages)

    print(json.dumps(output))

if __name__ == "__main__":
    main()
