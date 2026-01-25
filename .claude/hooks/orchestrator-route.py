#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""PreToolUse Hook: Route tasks through central orchestrator for optimization."""

import json
import sys
import os
from pathlib import Path

DAEMON_DIR = Path(__file__).parent.parent.parent / "daemon"
sys.path.insert(0, str(DAEMON_DIR))

def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except:
        print(json.dumps({"continue": True}))
        return

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only intercept Task tool calls for routing optimization
    if tool_name != "Task":
        print(json.dumps({"continue": True}))
        return

    prompt = tool_input.get("prompt", "")
    if not prompt or len(prompt) < 20:
        print(json.dumps({"continue": True}))
        return

    try:
        from orchestrator import fast_classify

        # Fast classify (no LLM, <1ms)
        classification = fast_classify(prompt)

        # Log routing decision
        decision_id = f"dec_{os.getpid()}_{hash(prompt) % 10000:04d}"
        route_info = (
            f"Route: agent:{classification['agent']}\n"
            f"  Intent: {classification['intent']}\n"
            f"  Complexity: {classification['complexity']}/10\n"
            f"  Confidence: {classification['confidence']*100:.1f}%\n"
            f"  Est. Cost: ${0.01 * classification['complexity']:.3f}\n"
            f"\n  Decision ID: {decision_id}"
        )

        print(f"\nRouting Decision:\n{route_info}\n", file=sys.stderr)

    except Exception as e:
        print(f"[Orchestrator] Classification skipped: {e}", file=sys.stderr)

    print(json.dumps({"continue": True}))

if __name__ == "__main__":
    main()
