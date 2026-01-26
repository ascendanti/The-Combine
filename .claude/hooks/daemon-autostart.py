#!/usr/bin/env python3
"""
Daemon Auto-Start Hook - Ensures continuous_executor runs on session start.

WIRING: SessionStart hook in settings.local.json
Starts the daemon if not already running. Silent on success.
"""

import subprocess
import sys
import json
from pathlib import Path

DAEMON_DIR = Path(__file__).parent.parent.parent / "daemon"
SCRIPT = DAEMON_DIR / "continuous_executor.py"


def is_daemon_running() -> bool:
    """Check if daemon is already running."""
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "status"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(DAEMON_DIR)
        )
        if result.stdout:
            status = json.loads(result.stdout)
            return status.get("running", False)
    except Exception:
        pass
    return False


def start_daemon():
    """Start the daemon if not running."""
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "start"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(DAEMON_DIR)
        )
        if "started" in result.stdout.lower() or "running" in result.stdout.lower():
            return True, result.stdout.strip()
        return False, result.stderr or result.stdout
    except Exception as e:
        return False, str(e)


def main():
    if is_daemon_running():
        # Already running - silent success
        return

    success, msg = start_daemon()
    if success:
        print(f"[daemon-autostart] {msg}", file=sys.stderr)
    else:
        print(f"[daemon-autostart] Failed to start: {msg}", file=sys.stderr)


if __name__ == "__main__":
    main()
