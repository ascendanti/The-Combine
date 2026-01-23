#!/usr/bin/env python3
"""Memory integration module for persistent learnings and decisions.

Designed for easy swap to OpenMemory SDK later.
Currently uses SQLite with JSON storage.
"""

import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class Learning:
    """A stored learning/insight."""
    id: str
    content: str
    context: str
    tags: List[str]
    confidence: str  # "high", "medium", "low"
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> 'Learning':
        return cls(
            id=row['id'],
            content=row['content'],
            context=row['context'],
            tags=json.loads(row['tags']),
            confidence=row['confidence'],
            created_at=row['created_at']
        )


@dataclass
class Decision:
    """A stored decision with rationale."""
    id: str
    decision: str
    rationale: str
    topic: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> 'Decision':
        return cls(
            id=row['id'],
            decision=row['decision'],
            rationale=row['rationale'],
            topic=row['topic'],
            created_at=row['created_at']
        )


# =============================================================================
# Abstract Backend (for future OpenMemory swap)
# =============================================================================

class MemoryBackend(ABC):
    """Abstract memory backend - implement for different storage systems."""

    @abstractmethod
    def store_learning(self, content: str, context: str, tags: List[str], confidence: str) -> Learning:
        pass

    @abstractmethod
    def recall_learnings(self, query: str, k: int = 5) -> List[Learning]:
        pass

    @abstractmethod
    def store_decision(self, decision: str, rationale: str, topic: str) -> Decision:
        pass

    @abstractmethod
    def recall_decisions(self, topic: str) -> List[Decision]:
        pass


# =============================================================================
# SQLite Backend Implementation
# =============================================================================

class SQLiteMemoryBackend(MemoryBackend):
    """Simple SQLite backend with JSON storage and text search."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path(__file__).parent / "memory.db"

        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # Learnings table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS learnings (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                context TEXT NOT NULL,
                tags TEXT NOT NULL,
                confidence TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # Decisions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                decision TEXT NOT NULL,
                rationale TEXT NOT NULL,
                topic TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # Create FTS5 virtual tables for full-text search
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS learnings_fts USING fts5(
                id, content, context, tags,
                content='learnings',
                content_rowid='rowid'
            )
        """)

        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS decisions_fts USING fts5(
                id, decision, rationale, topic,
                content='decisions',
                content_rowid='rowid'
            )
        """)

        # Triggers to keep FTS in sync
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS learnings_ai AFTER INSERT ON learnings BEGIN
                INSERT INTO learnings_fts(id, content, context, tags)
                VALUES (new.id, new.content, new.context, new.tags);
            END
        """)

        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS decisions_ai AFTER INSERT ON decisions BEGIN
                INSERT INTO decisions_fts(id, decision, rationale, topic)
                VALUES (new.id, new.decision, new.rationale, new.topic);
            END
        """)

        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def store_learning(self, content: str, context: str, tags: List[str], confidence: str) -> Learning:
        """Store a new learning."""
        learning = Learning(
            id=str(uuid.uuid4()),
            content=content,
            context=context,
            tags=tags,
            confidence=confidence,
            created_at=datetime.now().isoformat()
        )

        conn = self._get_conn()
        conn.execute("""
            INSERT INTO learnings (id, content, context, tags, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            learning.id,
            learning.content,
            learning.context,
            json.dumps(learning.tags),
            learning.confidence,
            learning.created_at
        ))
        conn.commit()
        conn.close()

        return learning

    def recall_learnings(self, query: str, k: int = 5) -> List[Learning]:
        """Recall learnings matching query using FTS."""
        conn = self._get_conn()

        # Use FTS5 for search
        rows = conn.execute("""
            SELECT l.* FROM learnings l
            JOIN learnings_fts f ON l.id = f.id
            WHERE learnings_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, k)).fetchall()

        # Fallback to LIKE if FTS returns nothing
        if not rows:
            rows = conn.execute("""
                SELECT * FROM learnings
                WHERE content LIKE ? OR context LIKE ? OR tags LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", f"%{query}%", k)).fetchall()

        conn.close()
        return [Learning.from_row(row) for row in rows]

    def store_decision(self, decision: str, rationale: str, topic: str = "") -> Decision:
        """Store a new decision."""
        dec = Decision(
            id=str(uuid.uuid4()),
            decision=decision,
            rationale=rationale,
            topic=topic or self._extract_topic(decision),
            created_at=datetime.now().isoformat()
        )

        conn = self._get_conn()
        conn.execute("""
            INSERT INTO decisions (id, decision, rationale, topic, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            dec.id,
            dec.decision,
            dec.rationale,
            dec.topic,
            dec.created_at
        ))
        conn.commit()
        conn.close()

        return dec

    def recall_decisions(self, topic: str) -> List[Decision]:
        """Recall decisions for a topic."""
        conn = self._get_conn()

        # Try FTS first
        rows = conn.execute("""
            SELECT d.* FROM decisions d
            JOIN decisions_fts f ON d.id = f.id
            WHERE decisions_fts MATCH ?
            ORDER BY rank
        """, (topic,)).fetchall()

        # Fallback to LIKE
        if not rows:
            rows = conn.execute("""
                SELECT * FROM decisions
                WHERE topic LIKE ? OR decision LIKE ? OR rationale LIKE ?
                ORDER BY created_at DESC
            """, (f"%{topic}%", f"%{topic}%", f"%{topic}%")).fetchall()

        conn.close()
        return [Decision.from_row(row) for row in rows]

    def _extract_topic(self, decision: str) -> str:
        """Extract a simple topic from the decision text."""
        # Simple heuristic: first few words
        words = decision.split()[:3]
        return " ".join(words).rstrip(".,:")

    def list_all_learnings(self, limit: int = 50) -> List[Learning]:
        """List all learnings (for debugging/review)."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT * FROM learnings
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        return [Learning.from_row(row) for row in rows]

    def list_all_decisions(self, limit: int = 50) -> List[Decision]:
        """List all decisions (for debugging/review)."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT * FROM decisions
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        return [Decision.from_row(row) for row in rows]


# =============================================================================
# OpenMemory Backend Implementation
# =============================================================================

class OpenMemoryBackend(MemoryBackend):
    """
    OpenMemory SDK backend - persistent memory with semantic search.

    Uses openmemory-py SDK (pip install openmemory-py).
    Note: OpenMemory uses async API, we wrap with asyncio.run() for sync interface.
    """

    def __init__(self, user_id: str = "claude-daemon"):
        try:
            from openmemory.main import Memory as OMMemory
        except ImportError:
            raise ImportError("openmemory-py not installed. Run: pip install openmemory-py")

        import asyncio
        self._asyncio = asyncio
        self.user_id = user_id
        self._om = OMMemory(user=user_id)

    def _run_async(self, coro):
        """Run async coroutine synchronously."""
        try:
            loop = self._asyncio.get_running_loop()
            # Already in async context, use nest_asyncio or run in thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(self._asyncio.run, coro)
                return future.result()
        except RuntimeError:
            # No running loop, safe to use asyncio.run
            return self._asyncio.run(coro)

    def store_learning(self, content: str, context: str, tags: List[str], confidence: str) -> Learning:
        """Store a learning using OpenMemory (async wrapped)."""
        full_content = f"{content}\n\nContext: {context}" if context else content

        async def _store():
            return await self._om.add(
                full_content,
                user_id=self.user_id,
                tags=tags + [f"confidence:{confidence}", "type:learning"],
                meta={"confidence": confidence, "context": context}
            )

        result = self._run_async(_store())
        memory_id = result.get('id', str(uuid.uuid4())) if isinstance(result, dict) else str(uuid.uuid4())

        return Learning(
            id=str(memory_id),
            content=content,
            context=context,
            tags=tags,
            confidence=confidence,
            created_at=datetime.now().isoformat()
        )

    def recall_learnings(self, query: str, k: int = 5) -> List[Learning]:
        """Recall learnings using OpenMemory semantic search (async wrapped)."""
        async def _search():
            return await self._om.search(query, user_id=self.user_id, limit=k)

        results = self._run_async(_search())

        learnings = []
        for r in results:
            # Results are dicts
            content = r.get('content', str(r))
            meta = r.get('meta', {}) or {}
            tags = r.get('tags', []) or []

            # Filter to learnings only
            if not any('type:learning' in str(t) for t in tags):
                continue

            # Extract context from content
            context = meta.get('context', '')
            if '\n\nContext: ' in content:
                parts = content.split('\n\nContext: ', 1)
                content = parts[0]
                context = parts[1] if len(parts) > 1 else context

            learnings.append(Learning(
                id=r.get('id', str(uuid.uuid4())),
                content=content,
                context=context,
                tags=[t for t in tags if not str(t).startswith(('confidence:', 'type:'))],
                confidence=meta.get('confidence', 'medium'),
                created_at=r.get('created_at', datetime.now().isoformat())
            ))

        return learnings[:k]

    def store_decision(self, decision: str, rationale: str, topic: str = "") -> Decision:
        """Store a decision using OpenMemory (async wrapped)."""
        full_content = f"Decision: {decision}\n\nRationale: {rationale}"
        if topic:
            full_content += f"\n\nTopic: {topic}"

        async def _store():
            return await self._om.add(
                full_content,
                user_id=self.user_id,
                tags=[f"topic:{topic}", "type:decision"] if topic else ["type:decision"],
                meta={"decision": decision, "rationale": rationale, "topic": topic}
            )

        result = self._run_async(_store())
        memory_id = result.get('id', str(uuid.uuid4())) if isinstance(result, dict) else str(uuid.uuid4())

        return Decision(
            id=str(memory_id),
            decision=decision,
            rationale=rationale,
            topic=topic or self._extract_topic(decision),
            created_at=datetime.now().isoformat()
        )

    def recall_decisions(self, topic: str) -> List[Decision]:
        """Recall decisions using OpenMemory semantic search (async wrapped)."""
        async def _search():
            return await self._om.search(f"decision about {topic}", user_id=self.user_id, limit=10)

        results = self._run_async(_search())

        decisions = []
        for r in results:
            tags = r.get('tags', []) or []

            if not any('type:decision' in str(t) for t in tags):
                continue

            meta = r.get('meta', {}) or {}

            decisions.append(Decision(
                id=r.get('id', str(uuid.uuid4())),
                decision=meta.get('decision', r.get('content', '')),
                rationale=meta.get('rationale', ''),
                topic=meta.get('topic', topic),
                created_at=r.get('created_at', datetime.now().isoformat())
            ))

        return decisions

    def _extract_topic(self, decision: str) -> str:
        """Extract a simple topic from the decision text."""
        words = decision.split()[:3]
        return " ".join(words).rstrip(".,:")

    def close(self):
        """Close the OpenMemory connection."""
        pass  # OpenMemory handles its own cleanup


# =============================================================================
# Main Memory Interface
# =============================================================================

class Memory:
    """
    High-level memory interface.

    Auto-selects OpenMemory if available, falls back to SQLite.
    Use backend="sqlite" or backend="openmemory" to force choice.
    """

    def __init__(self, backend: str = "auto", **kwargs):
        if backend == "auto":
            # Try OpenMemory first, fall back to SQLite
            try:
                self._backend = OpenMemoryBackend(**kwargs)
                self._backend_name = "openmemory"
            except ImportError:
                self._backend = SQLiteMemoryBackend(**kwargs)
                self._backend_name = "sqlite"
        elif backend == "sqlite":
            self._backend = SQLiteMemoryBackend(**kwargs)
            self._backend_name = "sqlite"
        elif backend == "openmemory":
            self._backend = OpenMemoryBackend(**kwargs)
            self._backend_name = "openmemory"
        else:
            raise ValueError(f"Unknown backend: {backend}")

    @property
    def backend_name(self) -> str:
        """Return the active backend name."""
        return self._backend_name

    def store_learning(self, content: str, context: str, tags: List[str], confidence: str = "medium") -> Learning:
        """Store a learning/insight."""
        return self._backend.store_learning(content, context, tags, confidence)

    def recall_learnings(self, query: str, k: int = 5) -> List[Learning]:
        """Recall learnings matching a query."""
        return self._backend.recall_learnings(query, k)

    def store_decision(self, decision: str, rationale: str, topic: str = "") -> Decision:
        """Store a decision with rationale."""
        return self._backend.store_decision(decision, rationale, topic)

    def recall_decisions(self, topic: str) -> List[Decision]:
        """Recall decisions for a topic."""
        return self._backend.recall_decisions(topic)

    # Convenience methods for SQLite backend
    def list_learnings(self, limit: int = 50) -> List[Learning]:
        """List all learnings."""
        if hasattr(self._backend, 'list_all_learnings'):
            return self._backend.list_all_learnings(limit)
        return []

    def list_decisions(self, limit: int = 50) -> List[Decision]:
        """List all decisions."""
        if hasattr(self._backend, 'list_all_decisions'):
            return self._backend.list_all_decisions(limit)
        return []


# =============================================================================
# CLI Interface
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Memory CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Store learning
    store_learning_parser = subparsers.add_parser("store-learning", help="Store a new learning")
    store_learning_parser.add_argument("content", help="The learning content")
    store_learning_parser.add_argument("--context", default="", help="Context for the learning")
    store_learning_parser.add_argument("--tags", default="", help="Comma-separated tags")
    store_learning_parser.add_argument("--confidence", choices=["high", "medium", "low"],
                                       default="medium", help="Confidence level")

    # Recall learnings
    recall_learning_parser = subparsers.add_parser("recall-learning", help="Recall learnings")
    recall_learning_parser.add_argument("query", help="Search query")
    recall_learning_parser.add_argument("-k", type=int, default=5, help="Number of results")

    # Store decision
    store_decision_parser = subparsers.add_parser("store-decision", help="Store a decision")
    store_decision_parser.add_argument("decision", help="The decision made")
    store_decision_parser.add_argument("--rationale", default="", help="Why this decision")
    store_decision_parser.add_argument("--topic", default="", help="Topic/category")

    # Recall decisions
    recall_decision_parser = subparsers.add_parser("recall-decision", help="Recall decisions")
    recall_decision_parser.add_argument("topic", help="Topic to search")

    # List all
    list_parser = subparsers.add_parser("list", help="List all entries")
    list_parser.add_argument("type", choices=["learnings", "decisions"], help="What to list")
    list_parser.add_argument("--limit", type=int, default=20, help="Max entries")

    args = parser.parse_args()
    memory = Memory()

    if args.command == "store-learning":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        learning = memory.store_learning(
            content=args.content,
            context=args.context,
            tags=tags,
            confidence=args.confidence
        )
        print(f"Stored learning: {learning.id}")
        print(json.dumps(learning.to_dict(), indent=2))

    elif args.command == "recall-learning":
        learnings = memory.recall_learnings(args.query, args.k)
        if not learnings:
            print("No learnings found.")
        for l in learnings:
            print(f"\n--- {l.id[:8]} ({l.confidence}) ---")
            print(f"Content: {l.content}")
            print(f"Context: {l.context}")
            print(f"Tags: {', '.join(l.tags)}")

    elif args.command == "store-decision":
        decision = memory.store_decision(
            decision=args.decision,
            rationale=args.rationale,
            topic=args.topic
        )
        print(f"Stored decision: {decision.id}")
        print(json.dumps(decision.to_dict(), indent=2))

    elif args.command == "recall-decision":
        decisions = memory.recall_decisions(args.topic)
        if not decisions:
            print("No decisions found.")
        for d in decisions:
            print(f"\n--- {d.id[:8]} ({d.topic}) ---")
            print(f"Decision: {d.decision}")
            print(f"Rationale: {d.rationale}")

    elif args.command == "list":
        if args.type == "learnings":
            learnings = memory.list_learnings(args.limit)
            for l in learnings:
                print(f"[{l.confidence:6}] {l.id[:8]} | {l.content[:60]}...")
        else:
            decisions = memory.list_decisions(args.limit)
            for d in decisions:
                print(f"[{d.topic[:15]:15}] {d.id[:8]} | {d.decision[:50]}...")

    else:
        parser.print_help()
