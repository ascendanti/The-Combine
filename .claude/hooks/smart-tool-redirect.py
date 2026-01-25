#!/usr/bin/env python3
"""
PreToolUse hook: Tracks usage of native vs smart tools for compliance monitoring.
Logs violations to help enforce smart-tools-required rule.

Does NOT block - just tracks and reminds.
"""
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Tracking file
TRACK_FILE = Path.home() / ".token-optimizer-cache" / "tool-usage.jsonl"

# Tools to track
TRACK_TOOLS = {"Read", "Grep", "Glob"}

# Skip these (acceptable to use native)
SKIP_PATTERNS = [".claude/settings", ".env", "package.json", "pyproject.toml", ".git/", "node_modules/"]

def should_skip(path: str) -> bool:
    if not path:
        return True
    path_lower = path.lower().replace("\\", "/")
    return any(skip in path_lower for skip in SKIP_PATTERNS)

def log_usage(tool: str, path: str, violation: bool):
    """Log tool usage for compliance tracking."""
    try:
        TRACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool,
            "path": path[:100] if path else "",
            "violation": violation
        }
        with open(TRACK_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + "\n")
    except:
        pass

def main():
    try:
        input_data = json.load(sys.stdin)
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        if tool_name not in TRACK_TOOLS:
            print(json.dumps({"continue": True}))
            return

        # Get path for tracking
        path = tool_input.get("file_path") or tool_input.get("path") or ""

        if should_skip(path):
            log_usage(tool_name, path, violation=False)
            print(json.dumps({"continue": True}))
            return

        # This is a violation - should use smart_* tool
        log_usage(tool_name, path, violation=True)

        # Map to smart tool equivalent
        smart_map = {
            "Read": "mcp__token-optimizer__smart_read",
            "Grep": "mcp__token-optimizer__smart_grep",
            "Glob": "mcp__token-optimizer__smart_glob"
        }
        smart_tool = smart_map.get(tool_name, "unknown")

        # Soft reminder (doesn't block)
        print(json.dumps({
            "continue": True,
            "message": f"⚠️ RULE VIOLATION: Use {smart_tool} instead of {tool_name} for 70-80% token savings"
        }))

    except Exception as e:
        print(json.dumps({"continue": True}))

if __name__ == "__main__":
    main()
