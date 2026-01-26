#!/usr/bin/env python3
"""
Deferred Task Capture - Captures recommendations/tasks that weren't immediately acted on.

When the user recommends something but it's not done due to priority, this module
captures it for later action. On session start, pending deferred tasks are surfaced.

WIRING:
- Called by deterministic_router.py when detecting recommendations
- Surfaced by session-briefing.py on session start
- Can be cleared via CLI or after completion

Triggers for capture:
- "check out", "look at", "investigate", "consider"
- "you should", "we should", "might want to"
- URLs mentioned but not fetched
- Explicit "later", "when you have time", "todo"
"""

import json
import sqlite3
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

DAEMON_DIR = Path(__file__).parent
DB_PATH = DAEMON_DIR / "deferred_tasks.db"

# Patterns that indicate a deferred recommendation
RECOMMENDATION_PATTERNS = [
    r'\b(check out|look at|investigate|consider)\s+',
    r'\b(you should|we should|might want to)\b',
    r'\b(later|when you have time|todo|to-?do)\b',
    r'\b(recommend|suggesting|try)\s+',
    r'https?://[^\s]+',  # URLs
]


@dataclass
class DeferredTask:
    """A captured deferred task/recommendation."""
    id: int
    content: str
    source: str  # user, system, url
    context: str  # What was being discussed
    priority: int  # 1-5, higher = more important
    captured_at: str
    completed: bool
    completed_at: Optional[str]
    tags: List[str]


class DeferredTaskCapture:
    """
    Captures and manages deferred tasks/recommendations.

    Ensures user recommendations aren't lost when they can't be
    immediately acted upon.
    """

    def __init__(self):
        self._init_db()

    def _init_db(self):
        """Initialize database."""
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS deferred_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                source TEXT DEFAULT 'user',
                context TEXT,
                priority INTEGER DEFAULT 3,
                captured_at TEXT,
                completed INTEGER DEFAULT 0,
                completed_at TEXT,
                tags TEXT DEFAULT '[]'
            )
        """)
        conn.commit()
        conn.close()

    def capture(self, content: str, source: str = "user", context: str = "",
                priority: int = 3, tags: List[str] = None) -> int:
        """
        Capture a deferred task/recommendation.

        Returns the task ID.
        """
        tags = tags or []

        # Extract URLs if present
        urls = re.findall(r'https?://[^\s]+', content)
        if urls:
            tags.append("has_url")
            source = "url" if source == "user" else source

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.execute("""
            INSERT INTO deferred_tasks (content, source, context, priority, captured_at, tags)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (content, source, context, priority, datetime.now().isoformat(), json.dumps(tags)))
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return task_id

    def detect_and_capture(self, message: str, context: str = "") -> List[int]:
        """
        Detect recommendations in a message and capture them.

        Returns list of captured task IDs.
        """
        captured_ids = []

        for pattern in RECOMMENDATION_PATTERNS:
            matches = re.finditer(pattern, message, re.IGNORECASE)
            for match in matches:
                # Extract the recommendation context
                start = max(0, match.start() - 50)
                end = min(len(message), match.end() + 100)
                excerpt = message[start:end].strip()

                # Check if already captured (avoid duplicates)
                if not self._is_duplicate(excerpt):
                    # Determine priority based on pattern
                    priority = 3
                    if "should" in excerpt.lower():
                        priority = 4
                    if "http" in excerpt:
                        priority = 4  # URLs are actionable

                    task_id = self.capture(
                        content=excerpt,
                        source="detected",
                        context=context,
                        priority=priority
                    )
                    captured_ids.append(task_id)

        return captured_ids

    def _is_duplicate(self, content: str, threshold: float = 0.7) -> bool:
        """Check if similar task already exists."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.execute("""
            SELECT content FROM deferred_tasks
            WHERE completed = 0 AND captured_at > ?
        """, ((datetime.now() - timedelta(days=7)).isoformat(),))

        content_lower = content.lower()
        for row in cursor.fetchall():
            existing = row[0].lower()
            # Simple overlap check
            words1 = set(content_lower.split())
            words2 = set(existing.split())
            overlap = len(words1 & words2) / max(len(words1 | words2), 1)
            if overlap > threshold:
                conn.close()
                return True

        conn.close()
        return False

    def get_pending(self, limit: int = 10) -> List[DeferredTask]:
        """Get pending (incomplete) tasks, ordered by priority."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.execute("""
            SELECT * FROM deferred_tasks
            WHERE completed = 0
            ORDER BY priority DESC, captured_at DESC
            LIMIT ?
        """, (limit,))

        tasks = []
        for row in cursor.fetchall():
            tasks.append(DeferredTask(
                id=row[0],
                content=row[1],
                source=row[2],
                context=row[3],
                priority=row[4],
                captured_at=row[5],
                completed=bool(row[6]),
                completed_at=row[7],
                tags=json.loads(row[8]) if row[8] else []
            ))

        conn.close()
        return tasks

    def complete(self, task_id: int):
        """Mark a task as complete."""
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("""
            UPDATE deferred_tasks
            SET completed = 1, completed_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), task_id))
        conn.commit()
        conn.close()

    def get_urls(self) -> List[str]:
        """Get all pending URLs that were recommended but not fetched."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.execute("""
            SELECT content FROM deferred_tasks
            WHERE completed = 0 AND tags LIKE '%has_url%'
        """)

        urls = []
        for row in cursor.fetchall():
            found = re.findall(r'https?://[^\s]+', row[0])
            urls.extend(found)

        conn.close()
        return list(set(urls))

    def summary(self) -> Dict:
        """Get summary of deferred tasks."""
        conn = sqlite3.connect(str(DB_PATH))

        total = conn.execute("SELECT COUNT(*) FROM deferred_tasks").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM deferred_tasks WHERE completed = 0").fetchone()[0]
        with_urls = conn.execute("SELECT COUNT(*) FROM deferred_tasks WHERE completed = 0 AND tags LIKE '%has_url%'").fetchone()[0]
        high_priority = conn.execute("SELECT COUNT(*) FROM deferred_tasks WHERE completed = 0 AND priority >= 4").fetchone()[0]

        conn.close()

        return {
            "total": total,
            "pending": pending,
            "with_urls": with_urls,
            "high_priority": high_priority
        }


# =============================================================================
# CLI Interface
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Deferred Task Capture CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Add
    add_parser = subparsers.add_parser("add", help="Add a deferred task")
    add_parser.add_argument("content", help="Task content")
    add_parser.add_argument("--priority", type=int, default=3, help="Priority 1-5")
    add_parser.add_argument("--context", default="", help="Context")

    # List
    list_parser = subparsers.add_parser("list", help="List pending tasks")
    list_parser.add_argument("--limit", type=int, default=10, help="Max results")

    # Complete
    complete_parser = subparsers.add_parser("complete", help="Mark task complete")
    complete_parser.add_argument("task_id", type=int, help="Task ID")

    # URLs
    subparsers.add_parser("urls", help="List pending URLs")

    # Summary
    subparsers.add_parser("summary", help="Show summary")

    # Detect
    detect_parser = subparsers.add_parser("detect", help="Detect recommendations in text")
    detect_parser.add_argument("text", help="Text to analyze")

    args = parser.parse_args()
    capture = DeferredTaskCapture()

    if args.command == "add":
        task_id = capture.capture(args.content, priority=args.priority, context=args.context)
        print(f"Captured task #{task_id}")

    elif args.command == "list":
        tasks = capture.get_pending(args.limit)
        if not tasks:
            print("No pending tasks")
        for t in tasks:
            print(f"#{t.id} [P{t.priority}] {t.content[:80]}...")
            if t.tags:
                print(f"    tags: {', '.join(t.tags)}")

    elif args.command == "complete":
        capture.complete(args.task_id)
        print(f"Completed task #{args.task_id}")

    elif args.command == "urls":
        urls = capture.get_urls()
        if not urls:
            print("No pending URLs")
        for url in urls:
            print(url)

    elif args.command == "summary":
        s = capture.summary()
        print(f"Total: {s['total']}, Pending: {s['pending']}, URLs: {s['with_urls']}, High Priority: {s['high_priority']}")

    elif args.command == "detect":
        ids = capture.detect_and_capture(args.text, "CLI input")
        if ids:
            print(f"Captured {len(ids)} recommendations: {ids}")
        else:
            print("No recommendations detected")

    else:
        parser.print_help()
