#!/usr/bin/env python3
"""
Post-Integration Analysis Hook

Automatically runs after capabilities are added/modified.
Triggers on:
- PostToolUse for Write/Edit to .claude/ directories
- Git post-commit

Outputs JSON for hook compatibility.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
DAEMON_DIR = PROJECT_ROOT / "daemon"

# Paths that trigger analysis
TRIGGER_PATHS = [
    ".claude/agents/",
    ".claude/skills/",
    ".claude/commands/",
    ".claude/hooks/",
    ".claude/rules/",
]


def should_analyze(file_path: str) -> bool:
    """Check if the modified file should trigger analysis."""
    normalized = file_path.replace("\\", "/")
    return any(trigger in normalized for trigger in TRIGGER_PATHS)


def main():
    output = {"continue": True}

    try:
        input_data = json.load(sys.stdin)
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Only trigger on Write/Edit
        if tool_name not in ("Write", "Edit"):
            print(json.dumps(output))
            return

        file_path = tool_input.get("file_path", "")

        if should_analyze(file_path):
            # Import and run analyzer
            sys.path.insert(0, str(DAEMON_DIR))
            from integration_analyzer import analyze

            result = analyze(verbose=False)

            new_count = len(result.get("changes", {}).get("new", []))
            rec_count = len(result.get("recommendations", []))
            applied_count = len(result.get("applied", []))

            if new_count > 0 or rec_count > 0:
                output["message"] = (
                    f"[Integration Analysis] "
                    f"New: {new_count} | Recommendations: {rec_count} | "
                    f"Auto-applied: {applied_count}"
                )

    except Exception as e:
        # Don't fail the hook on errors
        pass

    print(json.dumps(output))


if __name__ == "__main__":
    main()
