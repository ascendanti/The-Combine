#!/usr/bin/env python3
"""Stop hook - triggers memory sync when dirty files exist.

At end of turn, checks for modified files and outputs sync reminder.
Based on claude-code-auto-memory pattern.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime


def main():
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        project_dir = os.getcwd()

    dirty_file = Path(project_dir) / ".claude" / "auto-memory" / "dirty-files"

    # No dirty files = nothing to do
    if not dirty_file.exists() or dirty_file.stat().st_size == 0:
        return

    # Read unique files (max 20)
    with open(dirty_file) as f:
        files = sorted(set(line.strip() for line in f if line.strip()))[:20]

    if not files:
        return

    # Log to session file
    session_log = Path(project_dir) / ".claude" / "auto-memory" / "session-log.txt"
    with open(session_log, "a") as f:
        f.write(f"\n[{datetime.now().isoformat()}] Files modified this turn:\n")
        for file in files:
            f.write(f"  - {file}\n")

    # Clear dirty files
    dirty_file.write_text("")

    # Output summary (minimal tokens)
    file_count = len(files)
    print(f"[AutoMemory] {file_count} file(s) tracked this turn. Session log updated.")


if __name__ == "__main__":
    main()
