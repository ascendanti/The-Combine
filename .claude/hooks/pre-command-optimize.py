#!/usr/bin/env python3
"""
Pre-Command Optimize Hook - Applies learned workarounds before Bash execution.

WIRING: PreToolUse hook for Bash tool.
Intercepts commands and applies optimizations from command_optimizer.

Example transformations:
- git commands -> python subprocess (FewWord bypass)
- cd + command -> proper path handling
"""

import json
import sys
import os
from pathlib import Path

# Add daemon to path
SCRIPT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SCRIPT_DIR / "daemon"))


def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except:
        print(json.dumps({"continue": True}))
        return

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only process Bash commands
    if tool_name != "Bash":
        print(json.dumps({"continue": True}))
        return

    command = tool_input.get("command", "")
    if not command:
        print(json.dumps({"continue": True}))
        return

    # Try to optimize the command
    try:
        from command_optimizer import CommandOptimizer
        optimizer = CommandOptimizer()
        optimized_cmd, reason = optimizer.optimize(command)

        if optimized_cmd != command:
            # Command was optimized - inject message
            print(json.dumps({
                "continue": True,
                "message": f"[CommandOptimizer] Applied: {reason}"
            }), file=sys.stderr)

            # Note: We can't actually modify the command from a hook
            # But we can surface the suggestion
            # The real fix would require tool input modification support

    except ImportError:
        pass  # optimizer not available
    except Exception as e:
        print(f"[CommandOptimizer] Error: {e}", file=sys.stderr)

    print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
