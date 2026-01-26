#!/usr/bin/env python3
"""
Autonomous Executor - Direct API-based autonomous execution.

Uses Anthropic SDK instead of CLI to avoid tool_use ID conflicts and
provide full control over API requests.

Usage:
    python daemon/autonomous_executor.py start    # Start daemon
    python daemon/autonomous_executor.py submit "task"  # Submit task
    python daemon/autonomous_executor.py status   # Check status
"""

import os
import sys
import time
import json
import signal
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass
import logging

# Check for anthropic SDK
try:
    import anthropic
except ImportError:
    print("Error: anthropic SDK not installed. Run: pip install anthropic")
    sys.exit(1)

DAEMON_DIR = Path(__file__).parent
PROJECT_DIR = DAEMON_DIR.parent
DB_PATH = DAEMON_DIR / "autonomous_executor.db"
PID_FILE = DAEMON_DIR / "autonomous_executor.pid"
LOG_FILE = DAEMON_DIR / "autonomous_executor.log"
CACHE_DB = DAEMON_DIR / "prompt_cache.db"

# Configuration
POLL_INTERVAL = 30
MAX_TOKENS = 4096
MODEL = "claude-sonnet-4-20250514"  # Cost-effective for autonomous tasks

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
class Task:
    id: str
    prompt: str
    source: str
    priority: int
    status: str
    created_at: str

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            prompt TEXT,
            source TEXT,
            priority INTEGER DEFAULT 5,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            completed_at TEXT,
            result TEXT,
            error TEXT,
            tokens_used INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status, priority);
    """)
    conn.commit()
    conn.close()

def init_cache():
    conn = sqlite3.connect(CACHE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prompt_cache (
            hash TEXT PRIMARY KEY,
            response TEXT,
            created_at TEXT,
            hits INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def get_cached(prompt: str) -> Optional[str]:
    h = hashlib.sha256(prompt.encode()).hexdigest()[:32]
    try:
        conn = sqlite3.connect(CACHE_DB)
        cur = conn.execute("SELECT response FROM prompt_cache WHERE hash = ?", (h,))
        row = cur.fetchone()
        if row:
            conn.execute("UPDATE prompt_cache SET hits = hits + 1 WHERE hash = ?", (h,))
            conn.commit()
            conn.close()
            return row[0]
        conn.close()
    except:
        pass
    return None

def set_cached(prompt: str, response: str):
    h = hashlib.sha256(prompt.encode()).hexdigest()[:32]
    try:
        init_cache()
        conn = sqlite3.connect(CACHE_DB)
        conn.execute("""
            INSERT OR REPLACE INTO prompt_cache (hash, response, created_at, hits)
            VALUES (?, ?, ?, 0)
        """, (h, response, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except:
        pass

class AutonomousExecutor:
    def __init__(self):
        self.running = False
        self.client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var
        init_db()

    def start(self):
        if PID_FILE.exists():
            pid = int(PID_FILE.read_text().strip())
            try:
                os.kill(pid, 0)
                logger.error(f"Already running (PID {pid})")
                return
            except OSError:
                pass

        PID_FILE.write_text(str(os.getpid()))
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

        logger.info("Autonomous Executor started")
        self.running = True

        try:
            while self.running:
                task = self._get_next_task()
                if task:
                    self._execute_task(task)
                time.sleep(POLL_INTERVAL)
        finally:
            if PID_FILE.exists():
                PID_FILE.unlink()
            logger.info("Autonomous Executor stopped")

    def _shutdown(self, signum, frame):
        logger.info(f"Shutdown signal {signum}")
        self.running = False

    def _get_next_task(self) -> Optional[Task]:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute("""
            SELECT id, prompt, source, priority, status, created_at
            FROM tasks WHERE status = 'pending'
            ORDER BY priority ASC, created_at ASC LIMIT 1
        """)
        row = cur.fetchone()
        conn.close()
        if row:
            return Task(*row)
        return None

    def _execute_task(self, task: Task):
        logger.info(f"Executing {task.id[:12]} from {task.source}")
        self._update_status(task.id, 'running')

        # Check cache
        cached = get_cached(task.prompt)
        if cached:
            logger.info(f"Cache HIT")
            self._complete(task.id, cached, tokens=0)
            return

        try:
            # Call Anthropic API directly
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": task.prompt}]
            )

            result = response.content[0].text
            tokens = response.usage.input_tokens + response.usage.output_tokens

            # Cache response
            set_cached(task.prompt, result)

            logger.info(f"Success: {tokens} tokens, {len(result)} chars")
            self._complete(task.id, result, tokens)

        except anthropic.APIError as e:
            logger.error(f"API error: {e}")
            self._fail(task.id, str(e))
        except Exception as e:
            logger.error(f"Error: {e}")
            self._fail(task.id, str(e))

    def _update_status(self, task_id: str, status: str):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
        conn.commit()
        conn.close()

    def _complete(self, task_id: str, result: str, tokens: int):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            UPDATE tasks SET status = 'complete', completed_at = ?, result = ?, tokens_used = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), result, tokens, task_id))
        conn.commit()
        conn.close()

    def _fail(self, task_id: str, error: str):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            UPDATE tasks SET status = 'failed', completed_at = ?, error = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), error, task_id))
        conn.commit()
        conn.close()

    @staticmethod
    def submit(prompt: str, source: str = 'user', priority: int = 5) -> str:
        init_db()
        task_id = f"auto_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hashlib.md5(prompt.encode()).hexdigest()[:8]}"
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO tasks (id, prompt, source, priority, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
        """, (task_id, prompt, source, priority, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return task_id

    @staticmethod
    def get_status() -> Dict:
        init_db()
        status = {"running": False, "tasks": {}}

        if PID_FILE.exists():
            pid = int(PID_FILE.read_text().strip())
            try:
                os.kill(pid, 0)
                status["running"] = True
                status["pid"] = pid
            except OSError:
                pass

        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
        status["tasks"] = {row[0]: row[1] for row in cur.fetchall()}

        cur = conn.execute("SELECT SUM(tokens_used) FROM tasks WHERE status = 'complete'")
        row = cur.fetchone()
        status["total_tokens"] = row[0] or 0
        conn.close()

        return status

    @staticmethod
    def stop():
        if PID_FILE.exists():
            pid = int(PID_FILE.read_text().strip())
            try:
                os.kill(pid, signal.SIGTERM)
                return True
            except:
                pass
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: autonomous_executor.py [start|stop|status|submit <prompt>]")
        return

    cmd = sys.argv[1]

    if cmd == "start":
        AutonomousExecutor().start()
    elif cmd == "stop":
        if AutonomousExecutor.stop():
            print("Stopped")
        else:
            print("Not running")
    elif cmd == "status":
        print(json.dumps(AutonomousExecutor.get_status(), indent=2))
    elif cmd == "submit" and len(sys.argv) > 2:
        prompt = " ".join(sys.argv[2:])
        task_id = AutonomousExecutor.submit(prompt)
        print(f"Submitted: {task_id}")
    else:
        print("Unknown command")

if __name__ == "__main__":
    main()
