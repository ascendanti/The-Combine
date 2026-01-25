#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Stop Hook: Auto-sync documentation after each response."""

import json
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

DB = Path(__file__).parent.parent.parent / "daemon" / "doc_updates.db"

def record(action, category="auto"):
    conn = sqlite3.connect(DB)
    conn.execute("CREATE TABLE IF NOT EXISTS doc_updates (id INTEGER PRIMARY KEY, timestamp TEXT, document TEXT, action TEXT, category TEXT, details TEXT)")
    conn.execute("INSERT INTO doc_updates (timestamp, document, action, category, details) VALUES (?, ?, ?, ?, ?)",
                 (datetime.now().isoformat(), "all", action, category, None))
    conn.commit()
    conn.close()

def main():
    input_data = json.loads(sys.stdin.read())
    # Record that a response was completed
    record("Response completed", "session")
    print(json.dumps({"continue": True}))

if __name__ == "__main__":
    main()
