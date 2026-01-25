#!/usr/bin/env python3
"""
Quick Telegram notification sender for Claude decisions/permissions.

Usage:
    python notify-telegram.py "Your message here"
    python notify-telegram.py --decision "Should I proceed with X?"
    python notify-telegram.py --permission "Need access to Y"
    python notify-telegram.py --blocked "Waiting on Z"
"""

import sys
import json
import urllib.request
import urllib.parse

BOT_TOKEN = "8031397990:AAEr6hUi1XKEJWTM1HLgKTriSfssBAJzLZI"
CHAT_ID = "8266225191"

def send(message: str, msg_type: str = "info"):
    """Send message to Telegram."""

    # Add emoji prefix based on type
    prefixes = {
        "decision": "🤔 *DECISION NEEDED*\n\n",
        "permission": "🔐 *PERMISSION REQUIRED*\n\n",
        "blocked": "⏸️ *BLOCKED*\n\n",
        "info": "ℹ️ ",
        "done": "✅ ",
        "error": "❌ "
    }

    prefix = prefixes.get(msg_type, "")
    full_message = f"{prefix}{message}"

    data = json.dumps({
        "chat_id": CHAT_ID,
        "text": full_message,
        "parse_mode": "Markdown"
    }).encode('utf-8')

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("ok", False)
    except Exception as e:
        print(f"Failed to send: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: notify-telegram.py [--decision|--permission|--blocked] 'message'")
        sys.exit(1)

    msg_type = "info"
    message = sys.argv[1]

    if sys.argv[1].startswith("--"):
        msg_type = sys.argv[1][2:]
        message = sys.argv[2] if len(sys.argv) > 2 else ""

    if send(message, msg_type):
        print("Sent")
    else:
        print("Failed")
        sys.exit(1)
