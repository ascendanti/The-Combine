#!/usr/bin/env python3
"""
Send a custom message to Slack.
Usage: python slack-send.py "Your message here"

This allows Claude to proactively send updates or ask questions.
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

def send_slack_message(webhook_url: str, message: str, is_question: bool = False):
    """Send a message to Slack via webhook."""
    timestamp = datetime.now().strftime("%H:%M:%S")

    icon = ":question:" if is_question else ":robot_face:"
    prefix = "*Question*" if is_question else "*Claude Update*"

    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{icon} {prefix} `{timestamp}`\n{message}"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"_Project: {Path.cwd().name}_"
                    }
                ]
            }
        ]
    }

    if is_question:
        payload["blocks"].append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "_Reply in the Claude terminal to respond_"
            }
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

def main():
    load_env()

    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("Error: SLACK_WEBHOOK_URL not configured in .env", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: python slack-send.py \"message\" [--question]")
        sys.exit(1)

    message = sys.argv[1]
    is_question = "--question" in sys.argv or "-q" in sys.argv

    if send_slack_message(webhook_url, message, is_question):
        print("Message sent to Slack")
    else:
        print("Failed to send message", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
