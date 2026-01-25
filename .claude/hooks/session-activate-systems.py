#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Session Start: Activate all cognitive systems and check for unused capabilities."""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime

DAEMON_DIR = Path(__file__).parent.parent.parent / "daemon"

def run_cmd(cmd, timeout=5):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(DAEMON_DIR.parent), shell=True)
        return r.stdout.strip()
    except:
        return ""

def main():
    input_data = json.loads(sys.stdin.read())
    checks = []
    
    # Check pending tasks
    out = run_cmd("python daemon/task_generator.py pending 2>nul")
    if "Pending tasks" in out and "(" in out:
        count = out.split("(")[1].split(")")[0]
        checks.append(f"Tasks: {count} pending")
    
    # Check auto-router
    out = run_cmd("python daemon/local_autorouter.py stats 2>nul")
    if "Total decisions: 0" in out:
        checks.append("AutoRouter: UNUSED")
    
    # Check strategies
    out = run_cmd("python daemon/strategy_evolution.py list 2>nul")
    zeros = out.count("fitness: 0.000")
    if zeros > 0:
        checks.append(f"Strategies: {zeros} unevaluated")
    
    if checks:
        msg = " | ".join(checks)
        print(f"[ACTIVATE] {msg}", file=sys.stderr)
    
    print(json.dumps({"continue": True}))

if __name__ == "__main__":
    main()
