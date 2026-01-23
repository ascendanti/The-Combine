#!/usr/bin/env python3
"""
n8n webhook notification hook for Claude Code.
Sends updates to an n8n workflow which can then forward to Slack, Discord, email, etc.

This is more flexible than direct Slack - you can customize the workflow in n8n.

Requires: N8N_WEBHOOK_URL environment variable or .env file
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

def load_env():
    """Load environment variables from .env file if present."""
    env_paths = [
        Path(__file__).parent.parent.parent / ".env",
        Path.cwd() / ".env",
    ]
    for env_file in env_paths:
        if env_file.exists():
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ.setdefault(key.strip(), value.strip().strip('"\''))

def send_n8n_webhook(webhook_url: str, data: dict):
    """Send data to n8n webhook."""
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status == 200
    except urllib.error.URLError as e:
        print(f"n8n notification failed: {e}", file=sys.stderr)
        return False

def get_hook_context():
    """Parse hook context from stdin."""
    try:
        if not sys.stdin.isatty():
            input_data = sys.stdin.read()
            if input_data.strip():
                return json.loads(input_data)
    except (json.JSONDecodeError, IOError):
        pass
    return {}

def main():
    load_env()

    webhook_url = os.environ.get("N8N_WEBHOOK_URL")
    if not webhook_url:
        sys.exit(0)  # Silent exit if not configured

    context = get_hook_context()
    hook_event = os.environ.get("CLAUDE_HOOK_EVENT", "Stop")

    # Prepare payload for n8n
    payload = {
        "timestamp": datetime.now().isoformat(),
        "event": hook_event,
        "project": Path.cwd().name,
        "session_id": os.environ.get("CLAUDE_SESSION_ID", ""),
        "tool_name": context.get("tool_name", ""),
        "tool_input": context.get("tool_input", {}),
        "tool_output": context.get("tool_output", "")[:500] if context.get("tool_output") else "",
        "working_directory": str(Path.cwd()),
    }

    # Add summary based on event type
    if hook_event == "Stop":
        payload["summary"] = "Claude finished responding"
    elif hook_event == "SessionStart":
        payload["summary"] = "Claude session started"
    elif hook_event == "SessionEnd":
        payload["summary"] = "Claude session ended"
    elif context.get("tool_name"):
        tool = context.get("tool_name")
        tool_input = context.get("tool_input", {})
        if tool == "Edit":
            payload["summary"] = f"Edited {tool_input.get('file_path', 'file')}"
        elif tool == "Write":
            payload["summary"] = f"Created {tool_input.get('file_path', 'file')}"
        elif tool == "Bash":
            cmd = tool_input.get("command", "")[:50]
            payload["summary"] = f"Ran: {cmd}..."
        else:
            payload["summary"] = f"Used {tool} tool"
    else:
        payload["summary"] = "Claude iteration completed"

    send_n8n_webhook(webhook_url, payload)

if __name__ == "__main__":
    main()
