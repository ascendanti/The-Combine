#!/usr/bin/env python3
"""Telegram Polling - Check for user responses.

Non-blocking check for Telegram messages. Use this to get user's choice
after sending options.

Usage:
    python telegram-poll.py          # Check once
    python telegram-poll.py --wait   # Wait up to 30s for response
"""

import sys
import json
import time
import urllib.request
from pathlib import Path

BOT_TOKEN = "8031397990:AAEr6hUi1XKEJWTM1HLgKTriSfssBAJzLZI"
CHAT_ID = "8266225191"
OFFSET_FILE = Path(__file__).parent.parent.parent / "daemon" / ".telegram_offset"


def get_offset() -> int:
    """Get last processed update ID."""
    if OFFSET_FILE.exists():
        try:
            return int(OFFSET_FILE.read_text().strip())
        except:
            pass
    return 0


def save_offset(offset: int):
    """Save last processed update ID."""
    OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
    OFFSET_FILE.write_text(str(offset))


def poll_once(timeout: int = 1) -> dict:
    """Poll for updates once."""
    offset = get_offset()
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset + 1}&timeout={timeout}&allowed_updates=[\"message\"]"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout + 5) as resp:
            data = json.loads(resp.read())
            if not data.get("ok"):
                return {"error": "API error"}

            updates = data.get("result", [])
            if not updates:
                return {"message": None}

            # Process updates from our chat only
            for update in updates:
                update_id = update.get("update_id", 0)
                msg = update.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))

                # Always update offset
                save_offset(update_id)

                if chat_id == CHAT_ID:
                    text = msg.get("text", "")
                    if text and not text.startswith("/"):
                        return {
                            "message": text,
                            "from": msg.get("from", {}).get("first_name", "User"),
                            "update_id": update_id
                        }

            return {"message": None}

    except Exception as e:
        return {"error": str(e)}


def poll_wait(max_wait: int = 30) -> dict:
    """Wait for a message up to max_wait seconds."""
    start = time.time()
    while time.time() - start < max_wait:
        result = poll_once(timeout=5)
        if result.get("message"):
            return result
        if result.get("error"):
            time.sleep(2)
    return {"message": None, "timeout": True}


if __name__ == "__main__":
    wait_mode = "--wait" in sys.argv

    if wait_mode:
        print("Waiting for Telegram response...", file=sys.stderr)
        result = poll_wait(30)
    else:
        result = poll_once()

    print(json.dumps(result, indent=2))
