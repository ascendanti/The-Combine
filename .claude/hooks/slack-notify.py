#!/usr/bin/env python3
"""
Slack notification hook for Claude Code.
Sends a one-line summary to Slack after each Claude iteration/response.

Usage: Add to .claude/settings.local.json hooks section
Requires: SLACK_WEBHOOK_URL environment variable or .env file
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
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip().strip('"\''))

def send_slack_message(webhook_url: str, message: str, context: dict = None):
    """Send a message to Slack via webhook."""
    timestamp = datetime.now().strftime("%H:%M:%S")

    # Build the message payload
    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Claude Update* `{timestamp}`\n{message}"
                }
            }
        ]
    }

    # Add context fields if provided
    if context:
        fields = []
        for key, value in context.items():
            if value:
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*{key}:* {value}"
                })
        if fields:
            payload["blocks"].append({
                "type": "section",
                "fields": fields[:10]  # Slack limit
            })

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status == 200
    except urllib.error.URLError as e:
        print(f"Slack notification failed: {e}", file=sys.stderr)
        return False

def get_hook_context():
    """Parse hook context from stdin (Claude Code passes JSON)."""
    try:
        if not sys.stdin.isatty():
            input_data = sys.stdin.read()
            if input_data.strip():
                return json.loads(input_data)
    except (json.JSONDecodeError, IOError):
        pass
    return {}

def summarize_tool_use(context: dict) -> str:
    """Create a one-line summary of what Claude just did."""
    tool_name = context.get("tool_name", "unknown")
    tool_input = context.get("tool_input", {})

    summaries = {
        "Read": lambda: f"Read `{tool_input.get('file_path', 'file')}`",
        "Edit": lambda: f"Edited `{tool_input.get('file_path', 'file')}`",
        "Write": lambda: f"Created `{tool_input.get('file_path', 'file')}`",
        "Bash": lambda: f"Ran: `{tool_input.get('command', 'command')[:50]}...`" if len(tool_input.get('command', '')) > 50 else f"Ran: `{tool_input.get('command', 'command')}`",
        "Grep": lambda: f"Searched for `{tool_input.get('pattern', 'pattern')}`",
        "Glob": lambda: f"Found files matching `{tool_input.get('pattern', 'pattern')}`",
        "Task": lambda: f"Spawned agent: {tool_input.get('description', 'task')[:40]}",
        "WebFetch": lambda: f"Fetched `{tool_input.get('url', 'url')[:40]}...`",
        "WebSearch": lambda: f"Searched: `{tool_input.get('query', 'query')[:40]}`",
    }

    if tool_name in summaries:
        return summaries[tool_name]()
    return f"Used `{tool_name}` tool"

def get_recent_activity():
    """Try to summarize recent activity from task.md or other sources."""
    task_file = Path.cwd() / "task.md"
    if task_file.exists():
        try:
            content = task_file.read_text()
            # Find "In Progress" section
            if "## In Progress" in content:
                lines = content.split("## In Progress")[1].split("##")[0].strip().split("\n")
                for line in lines:
                    if line.strip().startswith("- ["):
                        return line.strip()[6:].strip()  # Remove "- [ ] "
        except:
            pass
    return None

def main():
    load_env()

    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        # Silent exit if not configured - don't block Claude
        sys.exit(0)

    context = get_hook_context()

    # Determine hook type and create appropriate message
    hook_event = os.environ.get("CLAUDE_HOOK_EVENT", "PostToolUse")

    if hook_event == "Stop":
        # Try to get meaningful context
        recent = get_recent_activity()
        if recent:
            message = f"Completed: {recent}"
        else:
            message = "Claude iteration complete"
        extra_context = {
            "Project": Path.cwd().name
        }
    elif hook_event == "SessionStart":
        message = "Claude session started"
        extra_context = {"Project": Path.cwd().name}
    elif hook_event == "SessionEnd":
        message = "Claude session ended"
        extra_context = {"Project": Path.cwd().name}
    else:
        # PostToolUse - summarize the tool action
        message = summarize_tool_use(context)
        extra_context = None

    send_slack_message(webhook_url, message, extra_context)

if __name__ == "__main__":
    main()
