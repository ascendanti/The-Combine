#!/usr/bin/env python3
"""
Pre-Create Check Hook - Surfaces directives before creating new files.

WIRING: PreToolUse hook for Write operations.

When about to create a new file, this hook reminds about:
- Auto-wire requirement (update settings.local.json)
- Architecture update requirement (ARCHITECTURE-LIVE.md)
- Enforcement > Documentation principle
"""

import json
import sys
from pathlib import Path

DAEMON_DIR = Path(__file__).parent.parent.parent / "daemon"
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(DAEMON_DIR))


def main():
    try:
        hook_input = json.load(sys.stdin)
    except:
        print(json.dumps({"continue": True}))
        return

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Only check Write operations
    if tool_name != "Write":
        print(json.dumps({"continue": True}))
        return

    file_path = tool_input.get("file_path", "")

    # Check if this is a NEW file (not an edit)
    if file_path and not Path(file_path).exists():
        # This is creating a new file - surface directive
        is_hook = "/hooks/" in file_path or "\\hooks\\" in file_path
        is_daemon = "/daemon/" in file_path or "\\daemon\\" in file_path
        is_system = is_hook or is_daemon or file_path.endswith(".py")

        if is_system:
            print(json.dumps({
                "continue": True,
                "message": "[DIRECTIVE] Creating new system file. Remember: 1) Wire in settings.local.json 2) Update ARCHITECTURE-LIVE.md"
            }))
            return

    print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
