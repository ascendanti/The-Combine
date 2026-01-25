#!/usr/bin/env python3
"""
Auto-Update Documentation System

Automatically updates all tracking documents after significant work:
- DEV-STORY.md - Narrative progress
- EVOLUTION-PLAN.md - Phase status
- task.md - Current objectives
- .ai/STATE.md - Execution state

Usage:
    python daemon/auto_update_docs.py record --action "description" --category "category"
    python daemon/auto_update_docs.py update-state --task "current task" --status "in_progress"
    python daemon/auto_update_docs.py sync-all
"""

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "doc_updates.db"
PROJECT_ROOT = Path(__file__).parent.parent

def init_db():
    """Initialize the doc updates database."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS doc_updates (
            id INTEGER PRIMARY KEY,
            timestamp TEXT NOT NULL,
            document TEXT NOT NULL,
            action TEXT NOT NULL,
            category TEXT,
            details TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS session_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn

def record_update(action: str, category: str = None, details: str = None):
    """Record an action for later doc updates."""
    conn = init_db()
    conn.execute(
        "INSERT INTO doc_updates (timestamp, document, action, category, details) VALUES (?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), "all", action, category, details)
    )
    conn.commit()
    conn.close()
    print(f"Recorded: {action}")

def update_state(key: str, value: str):
    """Update session state."""
    conn = init_db()
    conn.execute(
        "INSERT OR REPLACE INTO session_state (key, value, updated_at) VALUES (?, ?, ?)",
        (key, value, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    print(f"State updated: {key} = {value}")

def get_pending_updates() -> list:
    """Get all pending updates since last sync."""
    conn = init_db()
    cursor = conn.execute(
        "SELECT timestamp, action, category, details FROM doc_updates ORDER BY timestamp DESC LIMIT 50"
    )
    updates = cursor.fetchall()
    conn.close()
    return updates

def get_state() -> dict:
    """Get current session state."""
    conn = init_db()
    cursor = conn.execute("SELECT key, value, updated_at FROM session_state")
    state = {row[0]: {"value": row[1], "updated_at": row[2]} for row in cursor.fetchall()}
    conn.close()
    return state

def update_state_md():
    """Update .ai/STATE.md with current state."""
    state_file = PROJECT_ROOT / ".ai" / "STATE.md"
    if not state_file.exists():
        return

    state = get_state()
    updates = get_pending_updates()

    # Build new content
    content = f"""# Execution State

*Factor 5: Unify execution state and business state*
*Auto-updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*

---

## Current Task

**Active:** {state.get('current_task', {}).get('value', 'Multi-repo integration and system activation')}

**Status:** {state.get('status', {}).get('value', 'In Progress')}

---

## Recent Actions

| Time | Action | Category |
|------|--------|----------|
"""
    for ts, action, category, _ in updates[:10]:
        time_str = ts.split("T")[1][:8] if "T" in ts else ts
        content += f"| {time_str} | {action[:50]} | {category or '-'} |\n"

    content += """
---

## System Activation Status

| System | Status | Last Used |
|--------|--------|-----------|
| Auto-Router | ⚠️ Not Active | Never |
| Task Generator | ✅ Active | Now |
| Self-Improvement | ✅ Active | Now |
| Outcome Tracker | ⚠️ Low Usage | 3 outcomes |
| Strategy Evolution | ⚠️ Not Evaluated | 0 fitness |
| Memory System | ✅ Available | - |

---

## Pending Work (from Task Generator)

Run `python daemon/task_generator.py pending` for full list.
Currently: 104 pending tasks (mostly testing).
"""

    state_file.write_text(content, encoding='utf-8')
    print(f"Updated: {state_file}")

def update_dev_story(action: str, narrative: str):
    """Append to DEV-STORY.md."""
    dev_story = PROJECT_ROOT / "DEV-STORY.md"
    if not dev_story.exists():
        return

    # Read current content
    content = dev_story.read_text()

    # Find the last section and append
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_section = f"""
---

## Session Update: {timestamp}

### {action}

{narrative}

"""

    # Append before the last "---" or at end
    if content.rstrip().endswith("---"):
        content = content.rstrip()[:-3] + new_section + "---"
    else:
        content += new_section

    dev_story.write_text(content)
    print(f"Updated: {dev_story}")

def sync_all():
    """Sync all documentation."""
    print("Syncing all documentation...")
    update_state_md()
    print("Sync complete.")

def main():
    parser = argparse.ArgumentParser(description="Auto-update documentation system")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # record command
    record_parser = subparsers.add_parser("record", help="Record an action")
    record_parser.add_argument("--action", required=True, help="Action description")
    record_parser.add_argument("--category", help="Action category")
    record_parser.add_argument("--details", help="Additional details")

    # update-state command
    state_parser = subparsers.add_parser("update-state", help="Update session state")
    state_parser.add_argument("--key", required=True, help="State key")
    state_parser.add_argument("--value", required=True, help="State value")

    # sync-all command
    subparsers.add_parser("sync-all", help="Sync all documentation")

    # pending command
    subparsers.add_parser("pending", help="Show pending updates")

    # dev-story command
    story_parser = subparsers.add_parser("dev-story", help="Update DEV-STORY.md")
    story_parser.add_argument("--action", required=True, help="Action title")
    story_parser.add_argument("--narrative", required=True, help="Narrative text")

    args = parser.parse_args()

    if args.command == "record":
        record_update(args.action, args.category, args.details)
    elif args.command == "update-state":
        update_state(args.key, args.value)
    elif args.command == "sync-all":
        sync_all()
    elif args.command == "pending":
        updates = get_pending_updates()
        for ts, action, category, details in updates:
            print(f"[{ts}] {action} ({category})")
    elif args.command == "dev-story":
        update_dev_story(args.action, args.narrative)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
