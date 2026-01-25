#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Unified Post Tool Use Tracker - Consolidates all post-tool tracking.

Replaces:
- auto-cache-post.py (caching)
- kg-context-store.py (knowledge graph)
- post-tool-use-tracker.py (general tracking)

Single entry point for all post-tool-use operations.
"""

import json
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

DAEMON_DIR = Path(__file__).parent.parent.parent / "daemon"
TRACKER_DB = DAEMON_DIR / "tool_tracking.db"

def init_db():
    conn = sqlite3.connect(TRACKER_DB)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tool_uses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            tool_name TEXT,
            file_path TEXT,
            input_size INTEGER,
            output_size INTEGER,
            duration_ms INTEGER,
            cached INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS cache_hits (
            path TEXT PRIMARY KEY,
            hit_count INTEGER DEFAULT 0,
            last_hit TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_tool_uses_tool ON tool_uses(tool_name);
        CREATE INDEX IF NOT EXISTS idx_tool_uses_time ON tool_uses(timestamp);
    """)
    conn.commit()
    conn.close()

def track_tool_use(tool_name: str, file_path: str = None,
                   input_size: int = 0, output_size: int = 0,
                   duration_ms: int = 0, cached: bool = False):
    """Track a tool use event."""
    try:
        init_db()
        conn = sqlite3.connect(TRACKER_DB)
        conn.execute("""
            INSERT INTO tool_uses (timestamp, tool_name, file_path,
                                   input_size, output_size, duration_ms, cached)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), tool_name, file_path,
              input_size, output_size, duration_ms, 1 if cached else 0))

        if cached and file_path:
            conn.execute("""
                INSERT INTO cache_hits (path, hit_count, last_hit)
                VALUES (?, 1, ?)
                ON CONFLICT(path) DO UPDATE SET
                    hit_count = hit_count + 1,
                    last_hit = excluded.last_hit
            """, (file_path, datetime.now().isoformat()))

        conn.commit()
        conn.close()
    except Exception:
        pass  # Silent fail for tracking

def update_kg_context(file_path: str, content_summary: str = None):
    """Store context in knowledge graph (if available)."""
    try:
        # Try MCP knowledge graph
        # This is a placeholder - actual KG integration varies
        pass
    except Exception:
        pass

def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except:
        print(json.dumps({"continue": True}))
        return

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    tool_output = input_data.get("tool_output", {})

    # Extract relevant info
    file_path = tool_input.get("file_path") or tool_input.get("path", "")
    output_content = str(tool_output.get("content", ""))[:1000] if tool_output else ""

    # Track the tool use
    track_tool_use(
        tool_name=tool_name,
        file_path=file_path,
        input_size=len(str(tool_input)),
        output_size=len(output_content),
        cached=tool_output.get("cached", False) if tool_output else False
    )

    # For Read operations, optionally update KG context
    if tool_name == "Read" and file_path:
        update_kg_context(file_path, output_content[:500])

    print(json.dumps({"continue": True}))

if __name__ == "__main__":
    main()
