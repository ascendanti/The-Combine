#!/usr/bin/env python3
"""
Windows-compatible daemon launcher.
Spawns continuous_executor as a detached process that survives shell exit.
"""

import subprocess
import sys
import os
from pathlib import Path

DAEMON_DIR = Path(__file__).parent
EXECUTOR = DAEMON_DIR / "continuous_executor.py"
PID_FILE = DAEMON_DIR / "continuous_executor.pid"

def launch():
    """Launch daemon as detached process."""
    # Windows-specific: CREATE_NEW_PROCESS_GROUP + DETACHED_PROCESS
    # These flags ensure the process survives after parent exits
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200

    python_exe = sys.executable

    # Use subprocess.Popen with proper Windows flags
    process = subprocess.Popen(
        [python_exe, str(EXECUTOR), "start"],
        cwd=str(DAEMON_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
        start_new_session=True
    )

    print(f"Daemon launched with PID {process.pid}")
    print(f"Check status: python continuous_executor.py status")
    return process.pid


def stop():
    """Stop the daemon."""
    if PID_FILE.exists():
        pid = int(PID_FILE.read_text().strip())
        try:
            os.kill(pid, 15)  # SIGTERM
            print(f"Sent stop signal to PID {pid}")
        except OSError as e:
            print(f"Could not stop PID {pid}: {e}")
    else:
        print("No PID file found - daemon may not be running")


def status():
    """Check daemon status."""
    os.system(f'python "{EXECUTOR}" status')


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python launch_daemon.py [start|stop|status]")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "start":
        launch()
    elif cmd == "stop":
        stop()
    elif cmd == "status":
        status()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
