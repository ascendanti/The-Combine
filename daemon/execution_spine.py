#!/usr/bin/env python3
"""
Execution Spine - Unified orchestration pipeline.

Flow: TaskGenerator → RetrievalPolicy → Executor → OutcomeTracker → MemoryStore → DeltaHandoff

This is the backbone that ties all autonomous systems together.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

DAEMON_DIR = Path(__file__).parent
SPINE_DB = DAEMON_DIR / "spine.db"

@dataclass
class SpineTask:
    id: str
    source: str  # 'autonomous' or 'interactive'
    task_type: str
    content: str
    status: str  # 'pending', 'retrieving', 'executing', 'storing', 'complete', 'failed'
    created_at: str
    context: Dict = None
    result: Dict = None

def init_db():
    conn = sqlite3.connect(SPINE_DB)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS spine_tasks (
            id TEXT PRIMARY KEY,
            source TEXT,
            task_type TEXT,
            content TEXT,
            status TEXT,
            created_at TEXT,
            updated_at TEXT,
            context TEXT,
            result TEXT
        );

        CREATE TABLE IF NOT EXISTS spine_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            stage TEXT,
            task_id TEXT,
            latency_ms INTEGER,
            success INTEGER,
            details TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_spine_status ON spine_tasks(status);
        CREATE INDEX IF NOT EXISTS idx_spine_source ON spine_tasks(source);
    """)
    conn.commit()
    conn.close()

init_db()

class RetrievalPolicy:
    """Unified retrieval entry point - LazyRAG gating + routing."""

    def __init__(self):
        self.lazy_rag_enabled = True
        self.vector_threshold = 0.4

    def should_retrieve(self, task: str, context: Dict = None) -> bool:
        """Apply LazyRAG gating."""
        # Simple heuristics - can be enhanced
        if len(task) < 50:
            return False  # Short tasks don't need retrieval

        retrieval_keywords = ['find', 'search', 'what', 'how', 'explain', 'recall']
        if any(kw in task.lower() for kw in retrieval_keywords):
            return True

        return False

    def retrieve(self, query: str, k: int = 5) -> List[Dict]:
        """Route to appropriate retrieval backend."""
        results = []

        # Try vector store first
        try:
            from vector_store import VectorStore
            vs = VectorStore()
            results = vs.hybrid_search(query, k=k)
        except:
            pass

        # Fallback to memory FTS
        if not results:
            try:
                from memory import MemoryManager
                mm = MemoryManager()
                results = mm.search(query, k=k)
            except:
                pass

        return results

class ExecutionSpine:
    """Main orchestration pipeline."""

    def __init__(self):
        self.retrieval = RetrievalPolicy()
        self._import_modules()

    def _import_modules(self):
        """Lazy import to avoid circular dependencies."""
        self.orchestrator = None
        self.outcome_tracker = None
        self.memory_router = None
        self.delta_handoff = None

        try:
            from orchestrator import Orchestrator
            self.orchestrator = Orchestrator()
        except:
            pass

        try:
            from outcome_tracker import OutcomeTracker
            self.outcome_tracker = OutcomeTracker()
        except:
            pass

    def submit(self, task: str, source: str = 'interactive',
               task_type: str = 'unknown', context: Dict = None) -> str:
        """Submit task to the spine."""
        import hashlib
        task_id = f"spine_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hashlib.md5(task.encode()).hexdigest()[:8]}"

        conn = sqlite3.connect(SPINE_DB)
        conn.execute("""
            INSERT INTO spine_tasks (id, source, task_type, content, status, created_at, updated_at, context)
            VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)
        """, (task_id, source, task_type, task, datetime.now().isoformat(),
              datetime.now().isoformat(), json.dumps(context or {})))
        conn.commit()
        conn.close()

        return task_id

    def execute(self, task_id: str) -> Dict[str, Any]:
        """Execute task through the full pipeline."""
        import time

        conn = sqlite3.connect(SPINE_DB)
        cursor = conn.execute("SELECT * FROM spine_tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            return {"error": "Task not found"}

        task = SpineTask(
            id=row[0], source=row[1], task_type=row[2], content=row[3],
            status=row[4], created_at=row[5], context=json.loads(row[7] or '{}'),
            result=None
        )

        result = {"task_id": task_id, "stages": {}}

        # Stage 1: Retrieval
        start = time.time()
        self._update_status(conn, task_id, 'retrieving')

        context_items = []
        if self.retrieval.should_retrieve(task.content, task.context):
            context_items = self.retrieval.retrieve(task.content)

        result["stages"]["retrieval"] = {
            "latency_ms": int((time.time() - start) * 1000),
            "items_found": len(context_items)
        }
        self._log_metric(conn, "retrieval", task_id, result["stages"]["retrieval"]["latency_ms"], True)

        # Stage 2: Execution (via orchestrator)
        start = time.time()
        self._update_status(conn, task_id, 'executing')

        exec_result = {"success": False}
        if self.orchestrator:
            try:
                exec_result = self.orchestrator.process(task.content, context=task.context)
                exec_result["success"] = not exec_result.get("result", {}).get("error")
            except Exception as e:
                exec_result = {"error": str(e), "success": False}

        result["stages"]["execution"] = {
            "latency_ms": int((time.time() - start) * 1000),
            "success": exec_result.get("success", False)
        }
        self._log_metric(conn, "execution", task_id, result["stages"]["execution"]["latency_ms"],
                        exec_result.get("success", False))

        # Stage 3: Outcome tracking
        start = time.time()
        self._update_status(conn, task_id, 'storing')

        if self.outcome_tracker and exec_result.get("success"):
            try:
                self.outcome_tracker.record(
                    action=f"spine:{task.task_type}",
                    result="success" if exec_result.get("success") else "failure",
                    context=task.content[:200]
                )
            except:
                pass

        result["stages"]["outcome"] = {
            "latency_ms": int((time.time() - start) * 1000),
            "recorded": True
        }

        # Stage 4: Complete
        self._update_status(conn, task_id, 'complete')
        conn.execute("""
            UPDATE spine_tasks SET result = ?, updated_at = ? WHERE id = ?
        """, (json.dumps(result), datetime.now().isoformat(), task_id))
        conn.commit()
        conn.close()

        result["status"] = "complete"
        return result

    def _update_status(self, conn, task_id: str, status: str):
        conn.execute("UPDATE spine_tasks SET status = ?, updated_at = ? WHERE id = ?",
                    (status, datetime.now().isoformat(), task_id))
        conn.commit()

    def _log_metric(self, conn, stage: str, task_id: str, latency_ms: int, success: bool):
        conn.execute("""
            INSERT INTO spine_metrics (timestamp, stage, task_id, latency_ms, success)
            VALUES (?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), stage, task_id, latency_ms, 1 if success else 0))
        conn.commit()

    def get_stats(self) -> Dict:
        """Get spine execution statistics."""
        conn = sqlite3.connect(SPINE_DB)

        # Task counts
        cursor = conn.execute("""
            SELECT status, source, COUNT(*) FROM spine_tasks
            GROUP BY status, source
        """)
        by_status_source = {}
        for status, source, count in cursor.fetchall():
            key = f"{status}_{source}"
            by_status_source[key] = count

        # Stage metrics
        cursor = conn.execute("""
            SELECT stage, AVG(latency_ms), SUM(success), COUNT(*)
            FROM spine_metrics
            WHERE timestamp > datetime('now', '-24 hours')
            GROUP BY stage
        """)
        stages = {}
        for stage, avg_latency, successes, total in cursor.fetchall():
            stages[stage] = {
                "avg_latency_ms": round(avg_latency or 0, 1),
                "success_rate": round((successes or 0) / (total or 1), 2),
                "total": total
            }

        conn.close()

        return {
            "by_status_source": by_status_source,
            "stages_24h": stages
        }

    def process_pending(self, limit: int = 5) -> List[Dict]:
        """Process pending tasks from the queue."""
        conn = sqlite3.connect(SPINE_DB)
        cursor = conn.execute("""
            SELECT id FROM spine_tasks WHERE status = 'pending'
            ORDER BY created_at ASC LIMIT ?
        """, (limit,))
        task_ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        results = []
        for task_id in task_ids:
            result = self.execute(task_id)
            results.append(result)

        return results

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Execution Spine')
    parser.add_argument('action', choices=['submit', 'execute', 'process', 'stats'])
    parser.add_argument('--task', type=str, help='Task content')
    parser.add_argument('--id', type=str, help='Task ID')
    parser.add_argument('--source', type=str, default='interactive')
    parser.add_argument('--limit', type=int, default=5)

    args = parser.parse_args()
    spine = ExecutionSpine()

    if args.action == 'submit':
        if not args.task:
            print("Error: --task required")
            return
        task_id = spine.submit(args.task, source=args.source)
        print(f"Submitted: {task_id}")

    elif args.action == 'execute':
        if not args.id:
            print("Error: --id required")
            return
        result = spine.execute(args.id)
        print(json.dumps(result, indent=2))

    elif args.action == 'process':
        results = spine.process_pending(limit=args.limit)
        print(f"Processed {len(results)} tasks")
        for r in results:
            print(f"  {r.get('task_id')}: {r.get('status')}")

    elif args.action == 'stats':
        stats = spine.get_stats()
        print(json.dumps(stats, indent=2))

if __name__ == "__main__":
    main()
