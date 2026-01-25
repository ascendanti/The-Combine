#!/usr/bin/env python3
"""
Telegram Inbox - Check for pending messages/instructions.

I (Claude) call this to check if you've sent instructions via Telegram.

Usage:
    python telegram-inbox.py          # Get latest unread message
    python telegram-inbox.py --all    # Get all recent messages
    python telegram-inbox.py --clear  # Mark all as read
"""

import sys
import json
import urllib.request
from pathlib import Path

BOT_TOKEN = "8031397990:AAEr6hUi1XKEJWTM1HLgKTriSfssBAJzLZI"
CHAT_ID = "8266225191"
OFFSET_FILE = Path(__file__).parent.parent.parent / "daemon" / ".telegram_offset"

def get_offset() -> int:
    """Get last processed update ID."""
    if OFFSET_FILE.exists():
        return int(OFFSET_FILE.read_text().strip())
    return 0

def save_offset(offset: int):
    """Save last processed update ID."""
    OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
    OFFSET_FILE.write_text(str(offset))

def get_updates(offset: int = 0) -> list:
    """Fetch updates from Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=1"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            if data.get("ok"):
                return data.get("result", [])
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
    return []

def check_inbox(show_all: bool = False, clear: bool = False) -> dict:
    """Check for new messages from authorized chat."""
    offset = get_offset()
    updates = get_updates(offset + 1 if offset else 0)

    messages = []
    latest_offset = offset

    for update in updates:
        latest_offset = max(latest_offset, update.get("update_id", 0))

        msg = update.get("message", {})
        chat_id = str(msg.get("chat", {}).get("id", ""))

        # Only accept from authorized chat
        if chat_id == CHAT_ID:
            text = msg.get("text", "")
            if text and not text.startswith("/"):  # Skip commands
                messages.append({
                    "text": text,
                    "from": msg.get("from", {}).get("first_name", "User"),
                    "date": msg.get("date", 0)
                })

    # Update offset if clearing or processing
    if clear or messages:
        save_offset(latest_offset)

    if clear:
        return {"cleared": True, "count": len(messages)}

    if show_all:
        return {"messages": messages}

    # Return latest message only
    if messages:
        return {"instruction": messages[-1]["text"], "from": messages[-1]["from"]}

    return {"instruction": None}

if __name__ == "__main__":
    show_all = "--all" in sys.argv
    clear = "--clear" in sys.argv

    result = check_inbox(show_all=show_all, clear=clear)
    print(json.dumps(result, indent=2))
