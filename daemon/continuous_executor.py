#!/usr/bin/env python3
"""
Continuous Executor - True autonomous execution loop.

This solves the "Claude stops after each response" problem by:
1. Running as external daemon process
2. Monitoring task queue for pending work
3. Auto-invoking Claude CLI with continuation prompts
4. Processing results and queueing follow-up tasks

Architecture:
```
[continuous_executor.py] (daemon)
    |
    v
[Task Queue] --pending--> [Claude CLI] --result--> [Outcome Tracker]
    ^                                                    |
    |_____________ new tasks generated __________________|
```

Usage:
    # Start daemon
    python daemon/continuous_executor.py start

    # Check status
    python daemon/continuous_executor.py status

    # Stop daemon
    python daemon/continuous_executor.py stop

    # Run single iteration (for testing)
    python daemon/continuous_executor.py once
"""

import os
import sys
import time
import json
import signal
import sqlite3
import subprocess
import threading
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
import logging

DAEMON_DIR = Path(__file__).parent
PROJECT_DIR = DAEMON_DIR.parent
CACHE_DB = DAEMON_DIR / "prompt_cache.db"
DRAGONFLY_URL = os.environ.get("DRAGONFLY_URL", "redis://localhost:6379")
CACHE_TTL = 86400 * 7  # 7 days

# Try to import redis, fallback to SQLite if unavailable
try:
    import redis
    _redis_client = redis.from_url(DRAGONFLY_URL, decode_responses=True)
    _redis_client.ping()
    USE_DRAGONFLY = True
except Exception:
    USE_DRAGONFLY = False
    _redis_client = None

def init_cache_db():
    """Initialize SQLite cache (fallback)."""
    conn = sqlite3.connect(CACHE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prompt_cache (
            prompt_hash TEXT PRIMARY KEY,
            prompt TEXT,
            response TEXT,
            created_at TEXT,
            hit_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def get_cached_response(prompt: str) -> Optional[str]:
    """Check cache for existing response (Dragonfly first, SQLite fallback)."""
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:32]
    cache_key = f"executor:prompt:{prompt_hash}"

    # Try Dragonfly first
    if USE_DRAGONFLY and _redis_client:
        try:
            cached = _redis_client.get(cache_key)
            if cached:
                _redis_client.hincrby("executor:stats", "hits", 1)
                return cached
        except Exception:
            pass

    # Fallback to SQLite
    try:
        conn = sqlite3.connect(CACHE_DB)
        cursor = conn.execute(
            "SELECT response FROM prompt_cache WHERE prompt_hash = ?",
            (prompt_hash,)
        )
        row = cursor.fetchone()
        if row:
            conn.execute(
                "UPDATE prompt_cache SET hit_count = hit_count + 1 WHERE prompt_hash = ?",
                (prompt_hash,)
            )
            conn.commit()
            conn.close()
            return row[0]
        conn.close()
    except Exception:
        pass
    return None

def cache_response(prompt: str, response: str):
    """Cache a prompt-response pair (Dragonfly + SQLite)."""
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:32]
    cache_key = f"executor:prompt:{prompt_hash}"

    # Store in Dragonfly
    if USE_DRAGONFLY and _redis_client:
        try:
            _redis_client.setex(cache_key, CACHE_TTL, response)
            _redis_client.hincrby("executor:stats", "writes", 1)
        except Exception:
            pass

    # Also store in SQLite for persistence
    try:
        init_cache_db()
        conn = sqlite3.connect(CACHE_DB)
        conn.execute("""
            INSERT OR REPLACE INTO prompt_cache (prompt_hash, prompt, response, created_at, hit_count)
            VALUES (?, ?, ?, ?, 0)
        """, (prompt_hash, prompt[:1000], response, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_cache_stats() -> Dict:
    """Get cache statistics."""
    stats = {"dragonfly": USE_DRAGONFLY, "entries": 0, "hits": 0}

    if USE_DRAGONFLY and _redis_client:
        try:
            redis_stats = _redis_client.hgetall("executor:stats")
            stats["dragonfly_hits"] = int(redis_stats.get("hits", 0))
            stats["dragonfly_writes"] = int(redis_stats.get("writes", 0))
        except Exception:
            pass

    try:
        conn = sqlite3.connect(CACHE_DB)
        cursor = conn.execute("SELECT COUNT(*), SUM(hit_count) FROM prompt_cache")
        row = cursor.fetchone()
        conn.close()
        stats["entries"] = row[0] or 0
        stats["sqlite_hits"] = row[1] or 0
    except Exception:
        pass

    return stats
DB_PATH = DAEMON_DIR / "continuous_executor.db"
PID_FILE = DAEMON_DIR / "continuous_executor.pid"
LOG_FILE = DAEMON_DIR / "continuous_executor.log"

# Configuration
POLL_INTERVAL = 30  # seconds between checks
MAX_TASK_DURATION = 600  # 10 minutes max per task
IDLE_THRESHOLD = 300  # 5 minutes idle before background tasks
CLAUDE_CMD = "claude"  # CLI command
MAX_RETRIES = 2  # Retry failed tasks

# All tools enabled for full autonomous execution
ALLOWED_TOOLS = "default"  # "default" enables all built-in tools

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ContinuousTask:
    id: str
    prompt: str
    source: str  # 'user', 'spine', 'scheduled', 'continuation'
    priority: int
    created_at: str
    status: str  # 'pending', 'running', 'complete', 'failed'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS continuous_tasks (
            id TEXT PRIMARY KEY,
            prompt TEXT,
            source TEXT,
            priority INTEGER DEFAULT 5,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            started_at TEXT,
            completed_at TEXT,
            result TEXT,
            error TEXT
        );

        CREATE TABLE IF NOT EXISTS execution_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            event TEXT,
            task_id TEXT,
            details TEXT
        );

        CREATE TABLE IF NOT EXISTS daemon_state (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_tasks_status ON continuous_tasks(status, priority);
    """)
    conn.commit()
    conn.close()

init_db()

class ContinuousExecutor:
    """Main continuous execution daemon."""

    def __init__(self):
        self.running = False
        self.current_task: Optional[ContinuousTask] = None
        self.last_activity = datetime.now()

    def start(self):
        """Start the daemon loop."""
        # Check if already running
        if PID_FILE.exists():
            pid = int(PID_FILE.read_text().strip())
            try:
                os.kill(pid, 0)  # Check if process exists
                logger.error(f"Daemon already running (PID {pid})")
                return
            except OSError:
                pass  # Process not running, stale PID file

        # Write PID
        PID_FILE.write_text(str(os.getpid()))

        # Register signal handlers
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

        logger.info("Continuous Executor started")
        self._log_event("daemon_start", None, {"pid": os.getpid()})
        self.running = True

        try:
            self._main_loop()
        finally:
            self._cleanup()

    def _shutdown(self, signum, frame):
        """Handle shutdown signal."""
        logger.info(f"Shutdown signal received ({signum})")
        self.running = False

    def _cleanup(self):
        """Cleanup on exit."""
        if PID_FILE.exists():
            PID_FILE.unlink()
        self._log_event("daemon_stop", None, {})
        logger.info("Continuous Executor stopped")

    def _main_loop(self):
        """Main execution loop."""
        while self.running:
            try:
                # Check for pending tasks
                task = self._get_next_task()

                if task:
                    self._execute_task(task)
                    self.last_activity = datetime.now()
                else:
                    # Check if we should run background tasks
                    idle_time = (datetime.now() - self.last_activity).total_seconds()
                    if idle_time > IDLE_THRESHOLD:
                        self._run_background_tasks()

                time.sleep(POLL_INTERVAL)

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(POLL_INTERVAL)

    def _get_next_task(self) -> Optional[ContinuousTask]:
        """Get next pending task from queue."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("""
            SELECT id, prompt, source, priority, created_at
            FROM continuous_tasks
            WHERE status = 'pending'
            ORDER BY priority ASC, created_at ASC
            LIMIT 1
        """)
        row = cursor.fetchone()
        conn.close()

        if row:
            return ContinuousTask(
                id=row[0], prompt=row[1], source=row[2],
                priority=row[3], created_at=row[4], status='pending'
            )
        return None

    def _execute_task(self, task: ContinuousTask):
        """Execute a task using Claude CLI with caching."""
        logger.info(f"Executing task {task.id[:8]} from {task.source}")
        self._update_task_status(task.id, 'running')
        self._log_event("task_start", task.id, {"source": task.source})

        # Check cache first
        cached = get_cached_response(task.prompt)
        if cached:
            logger.info(f"Cache HIT for task {task.id[:8]}")
            self._complete_task(task.id, cached)
            self._log_event("task_complete", task.id, {"cached": True, "output_len": len(cached)})
            return

        try:
            import uuid
            session_id = str(uuid.uuid4())

            # Build Claude CLI command with full tool access
            # Run from temp directory to avoid project hooks/session conflicts
            import tempfile
            temp_dir = tempfile.gettempdir()

            # Minimal CLI invocation to avoid tool_use ID conflicts
            # Use explicit system prompt and disable MCP to minimize context
            cmd = [
                CLAUDE_CMD,
                "--print",
                "--permission-mode", "bypassPermissions",
                "--no-session-persistence",
                "--session-id", session_id,
                "--tools", ALLOWED_TOOLS,
                "--system-prompt", "You are a helpful assistant. Use only ONE tool per response. Work step by step.",
                "--mcp-config", "{}",
                "--strict-mcp-config",
                "--",
                task.prompt,
            ]

            logger.info(f"Executing with minimal context")

            logger.info(f"Cache MISS - calling Claude (session {session_id[:8]})")
            logger.debug(f"Command: {cmd[:8]}...")

            # Execute from temp dir to avoid project hooks causing tool_use ID conflicts
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=MAX_TASK_DURATION,
                cwd=temp_dir,  # Run outside project to avoid hooks
                encoding='utf-8',
                errors='replace'
            )

            # Comprehensive logging
            logger.info(f"Return code: {result.returncode}")
            if result.stdout:
                logger.info(f"stdout ({len(result.stdout)} chars): {result.stdout[:200]}...")
            if result.stderr:
                logger.warning(f"stderr ({len(result.stderr)} chars): {result.stderr[:500]}")

            # Process result
            if result.returncode == 0 and result.stdout:
                # Cache successful response
                cache_response(task.prompt, result.stdout)

                self._complete_task(task.id, result.stdout)
                self._log_event("task_complete", task.id, {"output_len": len(result.stdout), "cached": False})

                # Check for continuation signals in output
                self._check_continuation(result.stdout, task)
            else:
                # Build comprehensive error message
                error_parts = []
                if result.stderr and result.stderr.strip():
                    error_parts.append(f"stderr: {result.stderr.strip()}")
                if result.stdout and result.stdout.strip() and result.returncode != 0:
                    error_parts.append(f"stdout: {result.stdout.strip()}")
                error_parts.append(f"exit_code: {result.returncode}")

                error_msg = " | ".join(error_parts) if error_parts else f"Unknown failure (code {result.returncode})"
                logger.error(f"Task failed: {error_msg[:500]}")

                # Check if retryable error
                retryable = any(x in error_msg.lower() for x in ["timeout", "connection", "rate limit", "503", "502", "overloaded"])
                retry_count = self._get_retry_count(task.id)

                if retryable and retry_count < MAX_RETRIES:
                    logger.info(f"Retryable error, attempt {retry_count + 1}/{MAX_RETRIES}")
                    self._increment_retry(task.id)
                    self._update_task_status(task.id, 'pending')  # Re-queue
                    time.sleep(5)  # Brief delay before retry
                else:
                    self._fail_task(task.id, error_msg)
                    self._log_event("task_failed", task.id, {"error": error_msg[:500], "code": result.returncode})

        except subprocess.TimeoutExpired:
            self._fail_task(task.id, "Task timed out")
            self._log_event("task_timeout", task.id, {})
        except Exception as e:
            logger.error(f"Task execution error: {e}")
            self._fail_task(task.id, str(e))
            self._log_event("task_error", task.id, {"error": str(e)})

    def _get_retry_count(self, task_id: str) -> int:
        """Get current retry count for a task."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute(
            "SELECT COUNT(*) FROM execution_log WHERE task_id = ? AND event = 'task_retry'",
            (task_id,)
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def _increment_retry(self, task_id: str):
        """Record a retry attempt."""
        self._log_event("task_retry", task_id, {})

    def _check_continuation(self, output: str, task: ContinuousTask):
        """Check output for continuation signals and queue follow-up."""
        # Look for continuation markers
        continuation_markers = [
            "[CONTINUE]",
            "TODO:",
            "Next step:",
            "Continuing with",
        ]

        for marker in continuation_markers:
            if marker in output:
                # Extract continuation context
                lines = output.split('\n')
                for i, line in enumerate(lines):
                    if marker in line:
                        context = '\n'.join(lines[max(0, i-2):i+5])
                        self._queue_continuation(task, context)
                        break
                break

    def _queue_continuation(self, parent_task: ContinuousTask, context: str):
        """Queue a continuation task."""
        import hashlib
        task_id = f"cont_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hashlib.md5(context.encode()).hexdigest()[:8]}"

        prompt = f"Continue from previous task. Context:\n{context[:1000]}\n\nProceed with the next step."

        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO continuous_tasks (id, prompt, source, priority, status, created_at)
            VALUES (?, ?, 'continuation', ?, 'pending', ?)
        """, (task_id, prompt, parent_task.priority, datetime.now().isoformat()))
        conn.commit()
        conn.close()

        logger.info(f"Queued continuation task {task_id[:8]}")

    def _run_background_tasks(self):
        """Run background maintenance tasks when idle."""
        logger.debug("Running background tasks...")

        # Check execution spine for pending tasks
        try:
            from execution_spine import ExecutionSpine
            spine = ExecutionSpine()
            results = spine.process_pending(limit=1)
            if results:
                logger.info(f"Processed {len(results)} spine tasks")
                self.last_activity = datetime.now()
        except Exception as e:
            logger.debug(f"Spine check failed: {e}")

        # Run optimization if due
        try:
            from orchestrator import Orchestrator
            orch = Orchestrator()
            orch.optimize()
        except Exception as e:
            logger.debug(f"Optimization failed: {e}")

    def _update_task_status(self, task_id: str, status: str):
        conn = sqlite3.connect(DB_PATH)
        if status == 'running':
            conn.execute("UPDATE continuous_tasks SET status = ?, started_at = ? WHERE id = ?",
                        (status, datetime.now().isoformat(), task_id))
        else:
            conn.execute("UPDATE continuous_tasks SET status = ? WHERE id = ?", (status, task_id))
        conn.commit()
        conn.close()

    def _complete_task(self, task_id: str, result: str):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            UPDATE continuous_tasks SET status = 'complete', completed_at = ?, result = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), result[:10000], task_id))
        conn.commit()
        conn.close()

    def _fail_task(self, task_id: str, error: str):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            UPDATE continuous_tasks SET status = 'failed', completed_at = ?, error = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), error[:2000], task_id))
        conn.commit()
        conn.close()

    def _log_event(self, event: str, task_id: Optional[str], details: Dict):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO execution_log (timestamp, event, task_id, details)
            VALUES (?, ?, ?, ?)
        """, (datetime.now().isoformat(), event, task_id, json.dumps(details)))
        conn.commit()
        conn.close()

    @staticmethod
    def submit(prompt: str, source: str = 'user', priority: int = 5) -> str:
        """Submit a task to the queue."""
        import hashlib
        task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hashlib.md5(prompt.encode()).hexdigest()[:8]}"

        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO continuous_tasks (id, prompt, source, priority, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
        """, (task_id, prompt, source, priority, datetime.now().isoformat()))
        conn.commit()
        conn.close()

        return task_id

    @staticmethod
    def get_status() -> Dict:
        """Get daemon status."""
        status = {"running": False, "pid": None, "tasks": {}, "recent_events": []}

        # Check if running
        if PID_FILE.exists():
            pid = int(PID_FILE.read_text().strip())
            try:
                os.kill(pid, 0)
                status["running"] = True
                status["pid"] = pid
            except OSError:
                pass

        # Task counts
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("""
            SELECT status, COUNT(*) FROM continuous_tasks GROUP BY status
        """)
        status["tasks"] = {row[0]: row[1] for row in cursor.fetchall()}

        # Recent events
        cursor = conn.execute("""
            SELECT timestamp, event, task_id FROM execution_log
            ORDER BY id DESC LIMIT 10
        """)
        status["recent_events"] = [
            {"time": row[0], "event": row[1], "task": row[2]}
            for row in cursor.fetchall()
        ]
        conn.close()

        return status

    @staticmethod
    def stop():
        """Stop the daemon."""
        if PID_FILE.exists():
            pid = int(PID_FILE.read_text().strip())
            try:
                os.kill(pid, signal.SIGTERM)
                logger.info(f"Sent SIGTERM to PID {pid}")
                return True
            except OSError as e:
                logger.error(f"Failed to stop: {e}")
        return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Continuous Executor Daemon')
    parser.add_argument('action', choices=['start', 'stop', 'status', 'submit', 'once'])
    parser.add_argument('--prompt', '-p', type=str, help='Task prompt for submit')
    parser.add_argument('--source', '-s', type=str, default='user', help='Task source')
    parser.add_argument('--priority', type=int, default=5, help='Task priority (1=highest)')

    args = parser.parse_args()

    if args.action == 'start':
        executor = ContinuousExecutor()
        executor.start()

    elif args.action == 'stop':
        if ContinuousExecutor.stop():
            print("Daemon stopped")
        else:
            print("Daemon not running or stop failed")

    elif args.action == 'status':
        status = ContinuousExecutor.get_status()
        print(json.dumps(status, indent=2))

    elif args.action == 'submit':
        if not args.prompt:
            print("Error: --prompt required")
            sys.exit(1)
        task_id = ContinuousExecutor.submit(args.prompt, args.source, args.priority)
        print(f"Submitted: {task_id}")

    elif args.action == 'once':
        executor = ContinuousExecutor()
        task = executor._get_next_task()
        if task:
            executor._execute_task(task)
            print(f"Executed: {task.id}")
        else:
            print("No pending tasks")

if __name__ == "__main__":
    main()
