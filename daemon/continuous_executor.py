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
import re
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass
import logging

# MANDATORY: LocalAI autorouter for intelligent routing (the orchestrator)
# No fallback - if this fails, fix it don't ignore it
from local_autorouter import route_request, record_outcome, get_best_agent

# MANDATORY: Model router for provider abstraction
from model_router import ModelRouter

DAEMON_DIR = Path(__file__).parent
PROJECT_DIR = DAEMON_DIR.parent

# MANDATORY: Shared task queue for unified task management
from task_queue import TaskQueue, TaskStatus, TaskPriority
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

# Sequential tool mode (avoids parallel tool_use conflicts by handling tools ourselves)
SEQUENTIAL_TOOL_MODE = True
MAX_TOOL_STEPS = 6
TOOL_TIMEOUT = 120  # seconds per tool invocation
MAX_TOOL_OUTPUT_CHARS = 4000

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
        self._tool_registry = {
            "bash": self._tool_bash,
            "read_file": self._tool_read_file,
            "write_file": self._tool_write_file,
            "append_file": self._tool_append_file,
            "list_dir": self._tool_list_dir,
        }
        # Initialize model router for intelligent provider selection
        self.router = ModelRouter()  # MANDATORY - no fallback

    def _tool_bash(self, payload: Dict[str, Any]) -> str:
        """Execute a shell command."""
        command = payload.get("command")
        if not command:
            return "Error: missing command"
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=TOOL_TIMEOUT,
                cwd=str(PROJECT_DIR),
                env={**os.environ, "CLAUDE_PROJECT_DIR": str(PROJECT_DIR)},
            )
        except subprocess.TimeoutExpired:
            return f"Error: command timed out after {TOOL_TIMEOUT}s"

        output = result.stdout or ""
        if result.stderr:
            output = f"{output}\n[stderr]\n{result.stderr}"
        output = output.strip() or "(no output)"
        if len(output) > MAX_TOOL_OUTPUT_CHARS:
            output = output[:MAX_TOOL_OUTPUT_CHARS] + "\n...[truncated]"
        return f"exit_code={result.returncode}\n{output}"

    def _tool_read_file(self, payload: Dict[str, Any]) -> str:
        """Read a file from disk."""
        path = payload.get("path")
        if not path:
            return "Error: missing path"
        target = (PROJECT_DIR / path).resolve() if not os.path.isabs(path) else Path(path).resolve()
        if not target.exists():
            return f"Error: file not found: {target}"
        try:
            content = target.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return f"Error reading file: {exc}"
        if len(content) > MAX_TOOL_OUTPUT_CHARS:
            content = content[:MAX_TOOL_OUTPUT_CHARS] + "\n...[truncated]"
        return content

    def _tool_write_file(self, payload: Dict[str, Any]) -> str:
        """Write content to a file."""
        path = payload.get("path")
        content = payload.get("content", "")
        if not path:
            return "Error: missing path"
        target = (PROJECT_DIR / path).resolve() if not os.path.isabs(path) else Path(path).resolve()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        except Exception as exc:
            return f"Error writing file: {exc}"
        return f"Wrote {len(content)} chars to {target}"

    def _tool_append_file(self, payload: Dict[str, Any]) -> str:
        """Append content to a file."""
        path = payload.get("path")
        content = payload.get("content", "")
        if not path:
            return "Error: missing path"
        target = (PROJECT_DIR / path).resolve() if not os.path.isabs(path) else Path(path).resolve()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("a", encoding="utf-8") as handle:
                handle.write(content)
        except Exception as exc:
            return f"Error appending file: {exc}"
        return f"Appended {len(content)} chars to {target}"

    def _tool_list_dir(self, payload: Dict[str, Any]) -> str:
        """List a directory."""
        path = payload.get("path", ".")
        target = (PROJECT_DIR / path).resolve() if not os.path.isabs(path) else Path(path).resolve()
        if not target.exists():
            return f"Error: path not found: {target}"
        if not target.is_dir():
            return f"Error: not a directory: {target}"
        entries = sorted(p.name for p in target.iterdir())
        listing = "\n".join(entries) if entries else "(empty)"
        if len(listing) > MAX_TOOL_OUTPUT_CHARS:
            listing = listing[:MAX_TOOL_OUTPUT_CHARS] + "\n...[truncated]"
        return listing

    def _execute_via_router(self, task: ContinuousTask) -> Optional[bool]:
        """Execute task via LocalAI autorouter (the orchestrator).

        LocalAI classifies and routes mechanically:
        - Simple → LocalAI handles (FREE)
        - Code → Codex handles (cheap)
        - Complex → Claude sequential mode
        - agent:* → Spawn agent
        - skill:* → Run skill

        Returns:
            True if completed successfully
            False if failed
            None if should fallback to Claude sequential mode
        """
        # Autorouter is MANDATORY - no fallback check needed

        try:
            # Get routing decision from LocalAI autorouter (mechanical classification)
            routing = route_request(task.prompt, use_localai=False)  # Fast keyword-based

            route = routing.get("route", "claude")
            decision_id = routing.get("decision_id")

            logger.info(f"AutoRouter decision: {route} (confidence: {routing.get('confidence', 0):.0%})")

            # Handle agent routes - spawn the agent
            if route.startswith("agent:"):
                agent_name = route.replace("agent:", "")
                logger.info(f"Routing to agent: {agent_name}")
                # Queue as agent task (let the spine handle it)
                self._queue_agent_task(task, agent_name)
                record_outcome(decision_id, "success", tokens_used=0)
                self._complete_task(task.id, f"Delegated to {agent_name} agent")
                return True

            # Handle skill routes - run the skill
            if route.startswith("skill:"):
                skill_name = route.replace("skill:", "")
                logger.info(f"Routing to skill: {skill_name}")
                self._complete_task(task.id, f"Run /{skill_name} skill")
                record_outcome(decision_id, "success", tokens_used=0)
                return True

            # LocalAI can handle simple tasks (FREE)
            if route == "localai" and self.router and self.router.localai.available():
                try:
                    result = self.router.route(task=task.prompt, content="", force_provider="localai")
                    if result.get("response"):
                        response = result["response"]
                        cache_response(task.prompt, response)
                        self._complete_task(task.id, response)
                        record_outcome(decision_id, "success", tokens_used=100)
                        self._log_event("task_complete", task.id, {"provider": "localai", "free": True})
                        return True
                except Exception as e:
                    logger.warning(f"LocalAI execution failed: {e}, falling back")

            # Codex can handle code tasks (cheap)
            if route == "codex" and self.router and self.router.openai_client.available():
                try:
                    result = self.router.route(task=task.prompt, content="", force_provider="codex")
                    if result.get("response"):
                        response = result["response"]
                        cache_response(task.prompt, response)
                        self._complete_task(task.id, response)
                        record_outcome(decision_id, "success", tokens_used=500)
                        self._log_event("task_complete", task.id, {"provider": "codex"})
                        return True
                except Exception as e:
                    logger.warning(f"Codex execution failed: {e}, falling back")

            # Claude needed for complex reasoning - but fallback if unavailable
            if route == "claude":
                # Check if Claude CLI is available (has auth)
                claude_available = self._check_claude_available()

                if claude_available:
                    logger.info("Complex task - routing to Claude sequential mode")
                    task.decision_id = decision_id if hasattr(task, '__dict__') else None
                    return None  # Let Claude handle it
                else:
                    # Fallback: try Codex for code tasks, LocalAI for others
                    logger.warning("Claude CLI unavailable - falling back to alternative providers")

                    if self.router and self.router.openai_client.available():
                        try:
                            result = self.router.route(task=task.prompt, content="", force_provider="codex")
                            if result.get("response"):
                                self._complete_task(task.id, result["response"])
                                record_outcome(decision_id, "success", tokens_used=500)
                                self._log_event("task_complete", task.id, {"provider": "codex", "fallback": True})
                                return True
                        except Exception as e:
                            logger.warning(f"Codex fallback failed: {e}")

                    if self.router and self.router.localai.available():
                        try:
                            result = self.router.route(task=task.prompt, content="", force_provider="localai")
                            if result.get("response"):
                                self._complete_task(task.id, result["response"])
                                record_outcome(decision_id, "success", tokens_used=100)
                                self._log_event("task_complete", task.id, {"provider": "localai", "fallback": True})
                                return True
                        except Exception as e:
                            logger.warning(f"LocalAI fallback failed: {e}")

                    # No providers available - mark task as blocked
                    self._fail_task(task.id, "No AI providers available (Claude, Codex, LocalAI)")
                    record_outcome(decision_id, "failure", tokens_used=0)
                    return True  # Handled (as failure)

            # Unknown route - try available providers
            if self.router and self.router.localai.available():
                try:
                    result = self.router.route(task=task.prompt, content="", force_provider="localai")
                    if result.get("response"):
                        self._complete_task(task.id, result["response"])
                        return True
                except Exception:
                    pass

            return None  # Last resort: try Claude CLI

        except Exception as e:
            logger.error(f"AutoRouter exception: {e}")
            return None  # Fallback to Claude

    def _check_claude_available(self) -> bool:
        """Check if Claude CLI is available and authenticated."""
        try:
            resolved = shutil.which("claude") or shutil.which("claude.exe")
            if not resolved:
                return False
            # Quick check - just verify the binary exists and runs
            result = subprocess.run(
                [resolved, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def _queue_agent_task(self, task: ContinuousTask, agent_name: str):
        """Queue a task for a specific agent."""
        import hashlib
        agent_task_id = f"agent_{agent_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hashlib.md5(task.prompt.encode()).hexdigest()[:8]}"

        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO continuous_tasks (id, prompt, source, priority, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
        """, (agent_task_id, f"[AGENT:{agent_name}] {task.prompt}", 'agent', task.priority, datetime.now().isoformat()))
        conn.commit()
        conn.close()

        logger.info(f"Queued agent task: {agent_task_id}")

    def _debug_log(self, msg):
        """Write debug message to file (for detached process debugging)."""
        if os.environ.get("CONTINUOUS_EXECUTOR_CHILD"):
            debug_log = DAEMON_DIR / "daemon_debug.log"
            try:
                with open(debug_log, "a") as f:
                    f.write(f"[{datetime.now()}] {msg}\n")
            except:
                pass

    def start(self):
        """Start the daemon loop."""
        self._debug_log(f"start() called, PID={os.getpid()}")

        # Check if already running
        if PID_FILE.exists():
            pid = int(PID_FILE.read_text().strip())
            try:
                os.kill(pid, 0)  # Check if process exists
                logger.error(f"Daemon already running (PID {pid})")
                self._debug_log(f"Already running as PID {pid}, exiting")
                return
            except OSError:
                self._debug_log(f"Stale PID file for {pid}, continuing")
                pass  # Process not running, stale PID file

        # Write PID
        PID_FILE.write_text(str(os.getpid()))
        self._debug_log(f"Wrote PID file: {os.getpid()}")

        # Register signal handlers
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)
        self._debug_log("Signal handlers registered")

        logger.info("Continuous Executor started")
        self._log_event("daemon_start", None, {"pid": os.getpid()})
        self.running = True
        self._debug_log("About to enter main loop")

        try:
            self._main_loop()
        except Exception as e:
            self._debug_log(f"Exception in main_loop: {e}")
            raise
        finally:
            self._debug_log("Exiting start(), running cleanup")
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
        self._debug_log(f"Entered _main_loop, self.running={self.running}")
        iteration = 0
        while self.running:
            iteration += 1
            self._debug_log(f"Loop iteration {iteration}, running={self.running}")
            try:
                # Check for pending tasks
                task = self._get_next_task()
                self._debug_log(f"Got task: {task}")

                if task:
                    self._execute_task(task)
                    self.last_activity = datetime.now()
                else:
                    # Check if we should run background tasks
                    idle_time = (datetime.now() - self.last_activity).total_seconds()
                    if idle_time > IDLE_THRESHOLD:
                        self._run_background_tasks()

                self._debug_log(f"About to sleep {POLL_INTERVAL}s")
                time.sleep(POLL_INTERVAL)

            except Exception as e:
                self._debug_log(f"Exception in loop: {e}")
                logger.error(f"Error in main loop: {e}")
                time.sleep(POLL_INTERVAL)
        self._debug_log(f"Exited main loop, self.running={self.running}")

    def _get_next_task(self) -> Optional[ContinuousTask]:
        """Get next pending task from UNIFIED queue (checks both DBs)."""
        # 1. First check shared task queue (tasks.db) - where strategies push
        shared_queue = TaskQueue()
        shared_task = shared_queue.get_next_pending()
        if shared_task:
            # Mark as in progress in shared queue
            shared_queue.mark_in_progress(shared_task.id)
            return ContinuousTask(
                id=shared_task.id,
                prompt=shared_task.prompt,
                source='shared_queue',
                priority=shared_task.priority.value,
                created_at=shared_task.created_at,
                status='pending'
            )

        # 2. Fallback to local continuous_tasks table
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

    def _run_claude_prompt(self, prompt: str, session_id: str, system_prompt: str) -> subprocess.CompletedProcess:
        """Invoke Claude CLI with a single prompt."""
        import tempfile
        temp_dir = tempfile.gettempdir()

        claude_cmd = CLAUDE_CMD
        run_env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(PROJECT_DIR),
            "CLAUDE_DISABLE_PARALLEL_TOOL_USE": "1",
        }

        # Resolve full path to Claude CLI to ensure DLLs can be found on Windows
        resolved_cmd = shutil.which(claude_cmd, path=run_env.get("PATH"))
        if not resolved_cmd and os.name == "nt" and not claude_cmd.lower().endswith(".exe"):
            resolved_cmd = shutil.which(f"{claude_cmd}.exe", path=run_env.get("PATH"))
        if resolved_cmd:
            claude_cmd = resolved_cmd
            claude_dir = str(Path(resolved_cmd).parent)
            run_env["PATH"] = os.pathsep.join([claude_dir, run_env.get("PATH", "")])
        else:
            logger.warning("Claude CLI not found on PATH; using raw command: %s", claude_cmd)

        cmd = [
            claude_cmd,
            "--print",
            "--permission-mode", "bypassPermissions",
            "--no-session-persistence",
            "--session-id", session_id,
            "--system-prompt", system_prompt,
            "--mcp-config", "{}",
            "--strict-mcp-config",
            "--",
            prompt,
        ]

        # On Windows, suppress console window creation
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=MAX_TASK_DURATION,
            cwd=temp_dir,
            encoding="utf-8",
            errors="replace",
            env=run_env,
            creationflags=creation_flags,
        )

    def _extract_json_payload(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON object from model output."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    def _execute_task_sequential(self, task: ContinuousTask) -> Tuple[bool, str, bool]:
        """Execute a task with sequential tool handling (no parallel tool_use)."""
        import uuid
        session_id = str(uuid.uuid4())
        system_prompt = (
            "You are a helpful assistant running in sequential tool mode. "
            "Do NOT call built-in tools. Respond ONLY with a JSON object. "
            "Use {\"type\":\"tool_call\",\"tool\":\"<name>\",\"input\":{...}} to request a tool. "
            "Use {\"type\":\"final\",\"content\":\"...\"} to finish."
        )

        tool_history: List[str] = []
        tool_used = False

        for step in range(1, MAX_TOOL_STEPS + 1):
            history_block = ""
            if tool_history:
                history_block = "\n\nPrevious tool results:\n" + "\n\n".join(tool_history)

            prompt = (
                f"Task:\n{task.prompt}\n"
                f"{history_block}\n\n"
                "Remember: respond ONLY with JSON."
            )

            result = self._run_claude_prompt(prompt, session_id, system_prompt)

            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip() or f"exit_code: {result.returncode}"
                return False, error_msg, tool_used

            response_text = (result.stdout or "").strip()
            payload = self._extract_json_payload(response_text)
            if not payload:
                # No JSON response: treat as final content fallback
                return True, response_text, tool_used

            if payload.get("type") == "final":
                return True, str(payload.get("content", "")).strip(), tool_used

            if payload.get("type") != "tool_call":
                return True, response_text, tool_used

            tool_name = payload.get("tool")
            tool_input = payload.get("input") or {}
            tool_func = self._tool_registry.get(tool_name)
            if not tool_func:
                tool_history.append(f"[tool:{tool_name}] Error: unknown tool")
                continue

            tool_used = True
            try:
                tool_result = tool_func(tool_input)
            except Exception as exc:
                tool_result = f"Error running tool {tool_name}: {exc}"

            tool_history.append(
                f"[tool:{tool_name} step:{step}]\nInput: {json.dumps(tool_input)}\nResult:\n{tool_result}"
            )

        return False, "Exceeded maximum sequential tool steps", tool_used

    def _execute_task(self, task: ContinuousTask):
        """Execute a task using intelligent routing (LocalAI first, Claude for complex)."""
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

        # Use LocalAI autorouter for mechanical routing (FREE classification)
        # LocalAI decides: simple→LocalAI, code→Codex, complex→Claude, agent:*→spawn
        result = self._execute_via_router(task)
        if result is not None:
            return  # Handled by LocalAI/Codex/agent - no Claude tokens used

        # Fallback to sequential tool mode for Claude-only execution
        try:
            if SEQUENTIAL_TOOL_MODE:
                success, output, tool_used = self._execute_task_sequential(task)
                if success:
                    if output and not tool_used:
                        cache_response(task.prompt, output)
                    self._complete_task(task.id, output)
                    self._log_event(
                        "task_complete",
                        task.id,
                        {"output_len": len(output), "cached": not tool_used, "sequential": True},
                    )
                    self._check_continuation(output, task)
                    return

                error_msg = output or "Unknown failure in sequential tool mode"
                logger.error(f"Task failed: {error_msg[:500]}")

                retryable = any(
                    x in error_msg.lower()
                    for x in ["timeout", "connection", "rate limit", "503", "502", "overloaded"]
                )
                retry_count = self._get_retry_count(task.id)

                if retryable and retry_count < MAX_RETRIES:
                    logger.info(f"Retryable error, attempt {retry_count + 1}/{MAX_RETRIES}")
                    self._increment_retry(task.id)
                    self._update_task_status(task.id, 'pending')
                    time.sleep(5)
                else:
                    self._fail_task(task.id, error_msg)
                    self._log_event("task_failed", task.id, {"error": error_msg[:500], "sequential": True})
                return

            import uuid
            session_id = str(uuid.uuid4())
            result = self._run_claude_prompt(
                task.prompt,
                session_id,
                "You are a helpful assistant. Use only ONE tool per response. Work step by step.",
            )

            logger.info(f"Return code: {result.returncode}")
            if result.stdout:
                logger.info(f"stdout ({len(result.stdout)} chars): {result.stdout[:200]}...")
            if result.stderr:
                logger.warning(f"stderr ({len(result.stderr)} chars): {result.stderr[:500]}")

            if result.returncode == 0 and result.stdout:
                cache_response(task.prompt, result.stdout)
                self._complete_task(task.id, result.stdout)
                self._log_event("task_complete", task.id, {"output_len": len(result.stdout), "cached": False})
                self._check_continuation(result.stdout, task)
            else:
                error_parts = []
                if result.stderr and result.stderr.strip():
                    error_parts.append(f"stderr: {result.stderr.strip()}")
                if result.stdout and result.stdout.strip() and result.returncode != 0:
                    error_parts.append(f"stdout: {result.stdout.strip()}")
                error_parts.append(f"exit_code: {result.returncode}")

                error_msg = " | ".join(error_parts) if error_parts else f"Unknown failure (code {result.returncode})"
                logger.error(f"Task failed: {error_msg[:500]}")

                retryable = any(x in error_msg.lower() for x in ["timeout", "connection", "rate limit", "503", "502", "overloaded"])
                retry_count = self._get_retry_count(task.id)

                if retryable and retry_count < MAX_RETRIES:
                    logger.info(f"Retryable error, attempt {retry_count + 1}/{MAX_RETRIES}")
                    self._increment_retry(task.id)
                    self._update_task_status(task.id, 'pending')
                    time.sleep(5)
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

        # Auto-approve and queue generated tasks when execution queue is empty
        try:
            from task_generator import generate_tasks, get_pending_tasks, approve_task
            from task_queue import TaskQueue
            tq = TaskQueue()
            if tq.count_pending() == 0:
                # Check for pending generated tasks - auto-approve them
                pending_generated = get_pending_tasks()
                if pending_generated:
                    # Auto-approve up to 3 tasks per cycle
                    for task in pending_generated[:3]:
                        approve_task(task["task_id"])
                        logger.info(f"Auto-approved task: {task['title'][:50]}")
                    self.last_activity = datetime.now()
                else:
                    # No pending generated tasks - run detectors
                    task_ids = generate_tasks()
                    if task_ids:
                        logger.info(f"Generated {len(task_ids)} tasks from detectors")
                        self.last_activity = datetime.now()
        except Exception as e:
            logger.debug(f"Task generation failed: {e}")

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

        # Run unified_spine cycle for full workflow
        try:
            from unified_spine import UnifiedSpine
            spine = UnifiedSpine()
            results = spine.run_cycle()
            if results.get("tasks_executed", 0) > 0:
                logger.info(f"Spine cycle: {results['tasks_executed']} tasks executed")
                self.last_activity = datetime.now()
        except Exception as e:
            logger.debug(f"Unified spine cycle failed: {e}")

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
    def _is_process_running(pid: int) -> bool:
        """Check if process is running (Windows-compatible)."""
        if os.name == "nt":
            # Windows: os.kill(pid, 0) doesn't work reliably
            # Use tasklist instead
            try:
                result = subprocess.run(
                    ["tasklist", "/fi", f"PID eq {pid}", "/nh"],
                    capture_output=True, text=True, timeout=5
                )
                return str(pid) in result.stdout
            except Exception:
                return False
        else:
            # Unix: signal 0 works
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False

    @staticmethod
    def get_status() -> Dict:
        """Get daemon status."""
        status = {"running": False, "pid": None, "tasks": {}, "recent_events": []}

        # Check if running
        if PID_FILE.exists():
            pid = int(PID_FILE.read_text().strip())
            if ContinuousExecutor._is_process_running(pid):
                status["running"] = True
                status["pid"] = pid

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
        # Windows: Detach daemon to survive parent process termination
        if os.name == "nt" and not os.environ.get("CONTINUOUS_EXECUTOR_CHILD"):
            env = os.environ.copy()
            env["CONTINUOUS_EXECUTOR_CHILD"] = "1"
            proc = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "start"],
                cwd=str(DAEMON_DIR),
                env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
            print(f"Daemon started (PID {proc.pid}, detached)")
            return

        # Debug: Log to file for detached process debugging
        if os.environ.get("CONTINUOUS_EXECUTOR_CHILD"):
            debug_log = DAEMON_DIR / "daemon_debug.log"
            with open(debug_log, "a") as f:
                f.write(f"\n=== {datetime.now()} PID {os.getpid()} ===\n")
                f.write("Child process starting\n")

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
