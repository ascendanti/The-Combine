#!/usr/bin/env python3
"""SQLite-backed task queue for async Claude operations.

Based on sleepless-agent patterns but simplified.
No over-engineering - just what we need.
"""

import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class Task:
    id: str
    prompt: str
    status: TaskStatus
    priority: TaskPriority
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['status'] = self.status.value
        d['priority'] = self.priority.value
        return d

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> 'Task':
        return cls(
            id=row['id'],
            prompt=row['prompt'],
            status=TaskStatus(row['status']),
            priority=TaskPriority(row['priority']),
            created_at=row['created_at'],
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            result=row['result'],
            error=row['error'],
            metadata=json.loads(row['metadata']) if row['metadata'] else None
        )


class TaskQueue:
    """Simple SQLite-backed task queue."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            # Default to daemon directory
            db_path = Path(__file__).parent / "tasks.db"

        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                prompt TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                priority INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                result TEXT,
                error TEXT,
                metadata TEXT
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status
            ON tasks(status)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_priority
            ON tasks(priority DESC, created_at ASC)
        """)

        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def add_task(
        self,
        prompt: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Task:
        """Add a new task to the queue."""
        task = Task(
            id=str(uuid.uuid4()),
            prompt=prompt,
            status=TaskStatus.PENDING,
            priority=priority,
            created_at=datetime.now().isoformat(),
            metadata=metadata
        )

        conn = self._get_conn()
        conn.execute("""
            INSERT INTO tasks (id, prompt, status, priority, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            task.id,
            task.prompt,
            task.status.value,
            task.priority.value,
            task.created_at,
            json.dumps(task.metadata) if task.metadata else None
        ))
        conn.commit()
        conn.close()

        return task

    def get_next_pending(self) -> Optional[Task]:
        """Get the next pending task (highest priority, oldest first)."""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT * FROM tasks
            WHERE status = 'pending'
            ORDER BY priority DESC, created_at ASC
            LIMIT 1
        """).fetchone()
        conn.close()

        return Task.from_row(row) if row else None

    def get_pending_tasks(self, limit: int = 10) -> List[Task]:
        """Get all pending tasks."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT * FROM tasks
            WHERE status = 'pending'
            ORDER BY priority DESC, created_at ASC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()

        return [Task.from_row(row) for row in rows]

    def mark_in_progress(self, task_id: str) -> bool:
        """Mark a task as in progress."""
        conn = self._get_conn()
        cursor = conn.execute("""
            UPDATE tasks
            SET status = 'in_progress', started_at = ?
            WHERE id = ? AND status = 'pending'
        """, (datetime.now().isoformat(), task_id))
        conn.commit()
        affected = cursor.rowcount
        conn.close()

        return affected > 0

    def mark_completed(self, task_id: str, result: str) -> bool:
        """Mark a task as completed."""
        conn = self._get_conn()
        cursor = conn.execute("""
            UPDATE tasks
            SET status = 'completed', completed_at = ?, result = ?
            WHERE id = ? AND status = 'in_progress'
        """, (datetime.now().isoformat(), result, task_id))
        conn.commit()
        affected = cursor.rowcount
        conn.close()

        return affected > 0

    def mark_failed(self, task_id: str, error: str) -> bool:
        """Mark a task as failed."""
        conn = self._get_conn()
        cursor = conn.execute("""
            UPDATE tasks
            SET status = 'failed', completed_at = ?, error = ?
            WHERE id = ? AND status = 'in_progress'
        """, (datetime.now().isoformat(), error, task_id))
        conn.commit()
        affected = cursor.rowcount
        conn.close()

        return affected > 0

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a specific task by ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,)
        ).fetchone()
        conn.close()

        return Task.from_row(row) if row else None

    def get_recent_tasks(self, limit: int = 20) -> List[Task]:
        """Get recent tasks regardless of status."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT * FROM tasks
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()

        return [Task.from_row(row) for row in rows]

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task."""
        conn = self._get_conn()
        cursor = conn.execute("""
            UPDATE tasks
            SET status = 'cancelled', completed_at = ?
            WHERE id = ? AND status = 'pending'
        """, (datetime.now().isoformat(), task_id))
        conn.commit()
        affected = cursor.rowcount
        conn.close()

        return affected > 0

    def cleanup_old_tasks(self, days: int = 30) -> int:
        """Remove completed/failed tasks older than N days."""
        conn = self._get_conn()
        cursor = conn.execute("""
            DELETE FROM tasks
            WHERE status IN ('completed', 'failed', 'cancelled')
            AND datetime(completed_at) < datetime('now', ? || ' days')
        """, (f"-{days}",))
        conn.commit()
        affected = cursor.rowcount
        conn.close()

        return affected


# CLI interface for manual task management
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task Queue CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Add task
    add_parser = subparsers.add_parser("add", help="Add a new task")
    add_parser.add_argument("prompt", help="Task prompt")
    add_parser.add_argument("--priority", choices=["low", "normal", "high", "urgent"],
                           default="normal", help="Task priority")

    # List tasks
    list_parser = subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument("--status", choices=["pending", "in_progress", "completed", "failed"],
                            help="Filter by status")
    list_parser.add_argument("--limit", type=int, default=10, help="Max tasks to show")

    # Get task
    get_parser = subparsers.add_parser("get", help="Get task details")
    get_parser.add_argument("task_id", help="Task ID")

    # Cancel task
    cancel_parser = subparsers.add_parser("cancel", help="Cancel a pending task")
    cancel_parser.add_argument("task_id", help="Task ID")

    args = parser.parse_args()
    queue = TaskQueue()

    if args.command == "add":
        priority_map = {
            "low": TaskPriority.LOW,
            "normal": TaskPriority.NORMAL,
            "high": TaskPriority.HIGH,
            "urgent": TaskPriority.URGENT
        }
        task = queue.add_task(args.prompt, priority_map[args.priority])
        print(f"Created task: {task.id}")

    elif args.command == "list":
        tasks = queue.get_recent_tasks(args.limit)
        if args.status:
            tasks = [t for t in tasks if t.status.value == args.status]

        for task in tasks:
            print(f"[{task.status.value:12}] {task.id[:8]}... | {task.prompt[:50]}")

    elif args.command == "get":
        task = queue.get_task(args.task_id)
        if task:
            print(json.dumps(task.to_dict(), indent=2))
        else:
            print(f"Task not found: {args.task_id}")

    elif args.command == "cancel":
        if queue.cancel_task(args.task_id):
            print(f"Cancelled: {args.task_id}")
        else:
            print(f"Could not cancel (not pending or not found): {args.task_id}")

    else:
        parser.print_help()
