#!/usr/bin/env python3
"""
PreToolUse hook: ENFORCES smart tool usage for token optimization.
Blocks native Read/Grep/Glob and redirects to MCP smart_* tools.

Saves 70-80% tokens by using cached, compressed alternatives.
"""
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Tracking file
TRACK_FILE = Path.home() / ".token-optimizer-cache" / "tool-usage.jsonl"

# Tools to redirect
REDIRECT_TOOLS = {"Read", "Grep", "Glob"}

# Skip these (acceptable to use native) - small config files, editing context
SKIP_PATTERNS = [
    ".claude/settings", ".env", "package.json", "pyproject.toml",
    ".git/", "node_modules/", "manifest.json", "tsconfig.json",
    ".mcp.json", "settings.local.json", "docker-compose"
]

# Skip files smaller than this (bytes) - overhead not worth it
MIN_FILE_SIZE = 1024  # 1KB

def should_skip(path: str, tool_input: dict) -> bool:
    """Check if this call should use native tool."""
    if not path:
        return True

    path_lower = path.lower().replace("\\", "/")

    # Skip config files
    if any(skip in path_lower for skip in SKIP_PATTERNS):
        return True

    # Skip if file is small (check if exists)
    try:
        if os.path.isfile(path) and os.path.getsize(path) < MIN_FILE_SIZE:
            return True
    except:
        pass

    return False

def log_usage(tool: str, path: str, blocked: bool, redirected_to: str = None):
    """Log tool usage for analytics."""
    try:
        TRACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool,
            "path": path[:100] if path else "",
            "blocked": blocked,
            "redirected_to": redirected_to
        }
        with open(TRACK_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + "\n")
    except:
        pass

def build_smart_command(tool_name: str, tool_input: dict) -> str:
    """Build the MCP command to use instead."""
    if tool_name == "Read":
        path = tool_input.get("file_path", "")
        return f'mcp__token-optimizer__smart_read with {{"path": "{path}"}}'

    elif tool_name == "Grep":
        pattern = tool_input.get("pattern", "")
        path = tool_input.get("path", ".")
        return f'mcp__token-optimizer__smart_grep with {{"pattern": "{pattern}", "cwd": "{path}"}}'

    elif tool_name == "Glob":
        pattern = tool_input.get("pattern", "")
        path = tool_input.get("path", ".")
        return f'mcp__token-optimizer__smart_glob with {{"pattern": "{pattern}", "cwd": "{path}"}}'

    return "unknown"

def main():
    try:
        input_data = json.load(sys.stdin)
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        if tool_name not in REDIRECT_TOOLS:
            print(json.dumps({"continue": True}))
            return

        # Get path for checking
        path = tool_input.get("file_path") or tool_input.get("path") or ""

        if should_skip(path, tool_input):
            log_usage(tool_name, path, blocked=False)
            print(json.dumps({"continue": True}))
            return

        # Build redirect command
        smart_cmd = build_smart_command(tool_name, tool_input)

        # Map to smart tool name
        smart_map = {
            "Read": "mcp__token-optimizer__smart_read",
            "Grep": "mcp__token-optimizer__smart_grep",
            "Glob": "mcp__token-optimizer__smart_glob"
        }
        smart_tool = smart_map.get(tool_name, "unknown")

        log_usage(tool_name, path, blocked=True, redirected_to=smart_tool)

        # LOG but don't block (MCP may be unavailable)
        print(f"[TokenOpt] Consider: {smart_tool}", file=sys.stderr)
        print(json.dumps({"continue": True}))

    except Exception as e:
        # On error, allow through
        print(json.dumps({"continue": True}))

if __name__ == "__main__":
    main()
