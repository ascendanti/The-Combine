#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Stop Hook: Continuous Execution Architecture

This hook runs after every assistant response. It checks if there's pending work
and injects a continuation prompt if needed.

Architecture fix: Claude stops because each response is discrete. This hook
creates continuity by checking pending state and signaling continuation.
"""

import json
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

DAEMON_DIR = Path(__file__).parent.parent.parent / "daemon"
ORCHESTRATOR_DB = DAEMON_DIR / "orchestrator.db"
TASK_DB = DAEMON_DIR / "tasks.db"

def get_pending_work() -> dict:
    """Check all sources for pending work."""
    pending = {"tasks": 0, "optimizations": 0, "queue": 0}

    # Check task generator queue
    if TASK_DB.exists():
        try:
            conn = sqlite3.connect(TASK_DB)
            cursor = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
            pending["tasks"] = cursor.fetchone()[0]
            conn.close()
        except:
            pass

    # Check orchestrator for stale optimizations
    if ORCHESTRATOR_DB.exists():
        try:
            conn = sqlite3.connect(ORCHESTRATOR_DB)
            cursor = conn.execute("""
                SELECT COUNT(*) FROM optimization_runs
                WHERE timestamp > datetime('now', '-1 hour')
            """)
            recent = cursor.fetchone()[0]
            if recent == 0:
                pending["optimizations"] = 1
            conn.close()
        except:
            pass

    # Check LocalAI scheduler queue
    scheduler_db = DAEMON_DIR / "localai_scheduler.db"
    if scheduler_db.exists():
        try:
            conn = sqlite3.connect(scheduler_db)
            cursor = conn.execute("SELECT COUNT(*) FROM task_queue WHERE status = 'pending'")
            pending["queue"] = cursor.fetchone()[0]
            conn.close()
        except:
            pass

    return pending

def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except:
        print(json.dumps({"continue": True}))
        return

    # Check for pending work
    pending = get_pending_work()
    total_pending = sum(pending.values())

    if total_pending > 0:
        items = []
        if pending["tasks"]: items.append(f"{pending['tasks']} tasks")
        if pending["optimizations"]: items.append("optimization due")
        if pending["queue"]: items.append(f"{pending['queue']} queued")

        # Signal continuation needed
        print(f"[CONTINUE] Pending: {', '.join(items)}", file=sys.stderr)

    print(json.dumps({"continue": True}))

if __name__ == "__main__":
    main()
