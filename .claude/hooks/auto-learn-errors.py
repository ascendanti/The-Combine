#!/usr/bin/env python3
"""
Auto-Learn Errors Hook - Automatically captures and stores learnings from command errors.

WIRING: PostToolUse hook for Bash commands.

When a command fails with recognizable patterns (unrecognized arguments, import errors, etc.),
this hook automatically stores the learning so it won't happen again.
"""

import json
import sys
from pathlib import Path

DAEMON_DIR = Path(__file__).parent.parent.parent / "daemon"
sys.path.insert(0, str(DAEMON_DIR))

try:
    from command_optimizer import CommandOptimizer
    OPTIMIZER_AVAILABLE = True
except ImportError:
    OPTIMIZER_AVAILABLE = False


def main():
    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except:
        print(json.dumps({"continue": True}))
        return

    tool_name = hook_input.get("tool_name", "")
    tool_output = hook_input.get("tool_output", "")

    # Only process Bash results
    if tool_name != "Bash":
        print(json.dumps({"continue": True}))
        return

    # Check for error indicators
    error_indicators = [
        "error:",
        "Error:",
        "unrecognized arguments",
        "invalid choice",
        "ModuleNotFoundError",
        "FileNotFoundError",
        "ImportError",
        "SyntaxError",
        "NameError",
    ]

    has_error = any(indicator in str(tool_output) for indicator in error_indicators)

    if has_error and OPTIMIZER_AVAILABLE:
        try:
            # Get the original command from tool_input
            tool_input = hook_input.get("tool_input", {})
            command = tool_input.get("command", "")

            if command:
                optimizer = CommandOptimizer()
                learning_id = optimizer.auto_learn_from_error(command, str(tool_output))

                if learning_id:
                    # Report that we learned something
                    print(json.dumps({
                        "continue": True,
                        "message": f"[AUTO-LEARN] Captured error pattern: {learning_id}"
                    }))
                    return
        except Exception as e:
            pass  # Silent failure - don't block

    print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
