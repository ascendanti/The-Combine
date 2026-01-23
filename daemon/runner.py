#!/usr/bin/env python3
"""Daemon runner that polls task queue and spawns Claude Code CLI.

Simple Python daemon (not Windows service - learned from ATLAS-CLAUDE failure).
Runs in foreground or background via `pythonw` / `start /b`.
"""

import os
import sys
import time
import signal
import subprocess
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from queue import TaskQueue, Task, TaskStatus

# Configuration
POLL_INTERVAL = 10  # seconds between queue checks
MAX_RETRIES = 3     # retries for failed tasks
CLAUDE_TIMEOUT = 1800  # 30 minutes max per task

# Paths
PROJECT_DIR = Path(__file__).parent.parent
LOG_DIR = PROJECT_DIR / "daemon" / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "runner.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ClaudeRunner:
    """Runs Claude Code CLI for tasks."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.queue = TaskQueue()
        self.running = True
        self.current_task: Optional[Task] = None

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

        # Mark current task as failed if interrupted
        if self.current_task:
            self.queue.mark_failed(
                self.current_task.id,
                "Interrupted by shutdown signal"
            )

    def execute_task(self, task: Task) -> tuple[bool, str]:
        """Execute a task using Claude Code CLI.

        Returns:
            (success: bool, output: str)
        """
        logger.info(f"Executing task {task.id[:8]}...")

        # Build Claude command
        # Using --print for non-interactive output
        # Using --dangerously-skip-permissions since we have full permissions
        cmd = [
            "claude",
            "--print",
            "--dangerously-skip-permissions",
            task.prompt
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=CLAUDE_TIMEOUT,
                env={
                    **os.environ,
                    "CLAUDE_PROJECT_DIR": str(self.project_dir)
                }
            )

            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, f"Exit code {result.returncode}: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, f"Task timed out after {CLAUDE_TIMEOUT}s"
        except FileNotFoundError:
            return False, "Claude CLI not found. Is it installed and in PATH?"
        except Exception as e:
            return False, f"Execution error: {str(e)}"

    def process_next_task(self) -> bool:
        """Process the next pending task.

        Returns:
            True if a task was processed, False if queue empty.
        """
        task = self.queue.get_next_pending()
        if not task:
            return False

        self.current_task = task
        logger.info(f"Starting task: {task.id[:8]} | {task.prompt[:50]}...")

        # Mark as in progress
        if not self.queue.mark_in_progress(task.id):
            logger.warning(f"Could not mark task {task.id[:8]} as in progress")
            self.current_task = None
            return True  # Still processed (skip it)

        # Execute
        success, output = self.execute_task(task)

        # Update status
        if success:
            self.queue.mark_completed(task.id, output)
            logger.info(f"Completed task: {task.id[:8]}")
        else:
            self.queue.mark_failed(task.id, output)
            logger.error(f"Failed task: {task.id[:8]} | {output[:100]}")

        self.current_task = None
        return True

    def run(self):
        """Main daemon loop."""
        logger.info("=" * 50)
        logger.info("Claude Runner daemon starting...")
        logger.info(f"Project dir: {self.project_dir}")
        logger.info(f"Poll interval: {POLL_INTERVAL}s")
        logger.info("=" * 50)

        while self.running:
            try:
                # Check for pending tasks
                pending = self.queue.get_pending_tasks(limit=1)

                if pending:
                    self.process_next_task()
                else:
                    # No tasks, wait before checking again
                    time.sleep(POLL_INTERVAL)

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"Runner error: {e}")
                time.sleep(POLL_INTERVAL)

        logger.info("Claude Runner daemon stopped")

    def run_once(self):
        """Process one task and exit (useful for testing)."""
        logger.info("Running single task mode...")
        pending = self.queue.get_pending_tasks(limit=1)

        if pending:
            self.process_next_task()
        else:
            logger.info("No pending tasks")


def notify_completion(task: Task, result: str):
    """Send notification about task completion.

    Uses Slack if available, otherwise logs only.
    """
    try:
        slack_script = PROJECT_DIR / ".claude" / "hooks" / "slack-send.py"
        if slack_script.exists():
            status = "completed" if task.status == TaskStatus.COMPLETED else "failed"
            message = f"Task {task.id[:8]} {status}: {task.prompt[:50]}..."

            subprocess.run(
                ["python", str(slack_script), message],
                cwd=str(PROJECT_DIR),
                capture_output=True,
                timeout=10
            )
    except Exception as e:
        logger.warning(f"Could not send notification: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Claude Runner Daemon")
    parser.add_argument("--once", action="store_true",
                       help="Process one task and exit")
    parser.add_argument("--poll-interval", type=int, default=POLL_INTERVAL,
                       help=f"Seconds between queue checks (default: {POLL_INTERVAL})")
    args = parser.parse_args()

    if args.poll_interval:
        POLL_INTERVAL = args.poll_interval

    runner = ClaudeRunner(PROJECT_DIR)

    if args.once:
        runner.run_once()
    else:
        runner.run()
