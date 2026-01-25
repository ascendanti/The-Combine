#!/usr/bin/env python3
"""
SessionStart hook: Cleans up orphaned MCP node processes.
Prevents process accumulation across sessions.
"""
import subprocess
import json
import sys

MAX_NODE_PROCESSES = 5  # Alert threshold

def get_node_count():
    """Count running node processes."""
    try:
        result = subprocess.run(
            ['powershell', '-Command', '(Get-Process node -ErrorAction SilentlyContinue).Count'],
            capture_output=True, text=True, timeout=5
        )
        return int(result.stdout.strip() or 0)
    except:
        return 0

def kill_excess_nodes():
    """Kill node processes if too many are running."""
    try:
        subprocess.run(
            ['powershell', '-Command', 'Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force'],
            capture_output=True, timeout=10
        )
        return True
    except:
        return False

def main():
    count = get_node_count()

    if count > MAX_NODE_PROCESSES:
        kill_excess_nodes()
        print(json.dumps({
            "continue": True,
            "message": f"⚠️ Cleaned up {count} orphaned node processes"
        }))
    else:
        print(json.dumps({"continue": True}))

if __name__ == "__main__":
    main()
