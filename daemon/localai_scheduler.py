#!/usr/bin/env python3
"""
LocalAI Task Scheduler - Prioritizes interactive tasks over background ingest.

Rule: Ingest only runs when LocalAI has no other tasks queued.
"""

import sqlite3
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum

DB_PATH = Path(__file__).parent / "localai_scheduler.db"

class TaskPriority(int, Enum):
    INTERACTIVE = 0   # User-facing, immediate
    ROUTING = 1       # Orchestrator decisions
    SYNTHESIS = 2     # Background synthesis
    INGEST = 3        # Book ingestion (lowest)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS task_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            priority INTEGER,
            task_type TEXT,
            payload TEXT,
            created_at TEXT,
            started_at TEXT,
            completed_at TEXT,
            status TEXT DEFAULT 'pending'
        );
        CREATE INDEX IF NOT EXISTS idx_queue_priority ON task_queue(priority, created_at);
        CREATE INDEX IF NOT EXISTS idx_queue_status ON task_queue(status);
    """)
    conn.commit()
    conn.close()

init_db()

def queue_task(task_type: str, payload: str, priority: TaskPriority = TaskPriority.ROUTING) -> int:
    """Add task to queue. Returns task ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        INSERT INTO task_queue (priority, task_type, payload, created_at)
        VALUES (?, ?, ?, ?)
    """, (priority.value, task_type, payload, datetime.now().isoformat()))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id

def get_next_task() -> Optional[dict]:
    """Get highest priority pending task."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT id, priority, task_type, payload
        FROM task_queue
        WHERE status = 'pending'
        ORDER BY priority ASC, created_at ASC
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()

    if row:
        return {"id": row[0], "priority": row[1], "type": row[2], "payload": row[3]}
    return None

def can_run_ingest() -> bool:
    """Check if ingest can run (no higher priority tasks pending)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT COUNT(*) FROM task_queue
        WHERE status = 'pending' AND priority < ?
    """, (TaskPriority.INGEST.value,))
    count = cursor.fetchone()[0]
    conn.close()
    return count == 0

def mark_started(task_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        UPDATE task_queue SET status = 'running', started_at = ?
        WHERE id = ?
    """, (datetime.now().isoformat(), task_id))
    conn.commit()
    conn.close()

def mark_completed(task_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        UPDATE task_queue SET status = 'completed', completed_at = ?
        WHERE id = ?
    """, (datetime.now().isoformat(), task_id))
    conn.commit()
    conn.close()

def get_queue_stats() -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT priority, status, COUNT(*)
        FROM task_queue
        WHERE created_at > datetime('now', '-1 hour')
        GROUP BY priority, status
    """)
    stats = {}
    for priority, status, count in cursor.fetchall():
        key = f"p{priority}_{status}"
        stats[key] = count
    conn.close()
    return stats

def cleanup_old_tasks(hours: int = 24):
    """Remove completed tasks older than N hours."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        DELETE FROM task_queue
        WHERE status = 'completed'
        AND completed_at < datetime('now', '-' || ? || ' hours')
    """, (hours,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "stats":
            print(get_queue_stats())
        elif sys.argv[1] == "can-ingest":
            print("yes" if can_run_ingest() else "no")
        elif sys.argv[1] == "cleanup":
            cleanup_old_tasks()
            print("Cleaned up old tasks")
    else:
        print(f"Queue stats: {get_queue_stats()}")
        print(f"Can run ingest: {can_run_ingest()}")
