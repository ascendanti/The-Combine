#!/usr/bin/env python3
"""Receive files from Telegram and save them."""

import requests
import os
import sys
from pathlib import Path

def get_env():
    """Load Telegram credentials."""
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')

    if not bot_token:
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if line.startswith('TELEGRAM_BOT_TOKEN='):
                        bot_token = line.split('=', 1)[1].strip().strip('"')

    return bot_token

def receive_file(save_path: str = None):
    """Check for and download the latest file from Telegram."""
    bot_token = get_env()
    if not bot_token:
        print("ERROR: TELEGRAM_BOT_TOKEN not found")
        return False

    # Get updates
    url = f'https://api.telegram.org/bot{bot_token}/getUpdates'
    r = requests.get(url, params={'limit': 10, 'timeout': 1})

    if not r.ok:
        print(f"ERROR: Failed to get updates: {r.text}")
        return False

    updates = r.json().get('result', [])

    # Find latest document
    latest_doc = None
    for u in reversed(updates):
        msg = u.get('message', {})
        doc = msg.get('document')
        if doc:
            latest_doc = doc
            break

    if not latest_doc:
        print("No document found in recent messages.")
        print("Please send the JSON file to the Telegram bot.")
        return False

    file_name = latest_doc.get('file_name', 'unknown')
    file_id = latest_doc.get('file_id')

    print(f"Found file: {file_name}")

    # Get file path
    url = f'https://api.telegram.org/bot{bot_token}/getFile'
    r = requests.get(url, params={'file_id': file_id})

    if not r.ok:
        print(f"ERROR: Failed to get file info: {r.text}")
        return False

    file_path = r.json().get('result', {}).get('file_path')

    # Download file
    url = f'https://api.telegram.org/file/bot{bot_token}/{file_path}'
    r = requests.get(url)

    if not r.ok:
        print(f"ERROR: Failed to download file: {r.text}")
        return False

    # Determine save location
    if save_path:
        dest = Path(save_path)
    else:
        dest = Path.home() / '.atlas' / 'gdrive_credentials' / 'credentials.json'

    dest.parent.mkdir(parents=True, exist_ok=True)

    # Save file
    dest.write_bytes(r.content)
    print(f"✓ Saved to: {dest}")

    # Verify JSON
    try:
        import json
        data = json.loads(r.content)
        if 'installed' in data or 'web' in data:
            print("✓ Valid OAuth credentials file")
            return True
        else:
            print("⚠ File saved but doesn't look like OAuth credentials")
            return True
    except json.JSONDecodeError:
        print("⚠ File saved but is not valid JSON")
        return True

if __name__ == '__main__':
    save_path = sys.argv[1] if len(sys.argv) > 1 else None
    success = receive_file(save_path)
    sys.exit(0 if success else 1)
