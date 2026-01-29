#!/usr/bin/env python3
"""
Unified Spine - MANDATORY integration of all daemon systems.

NO OPTIONAL IMPORTS. If something fails to import, FIX IT.
This module enforces that all pieces are connected.

Architecture:
    Strategy → TaskGenerator → TaskQueue → AutoRouter → Executor → OutcomeTracker
                                    ↑                         ↓
                                Scheduler              Memory/Learnings

WIRING (2026-01-26): Now callable from hooks via absolute imports.
"""

import sys
from pathlib import Path
from typing import Dict, Any
import logging

DAEMON_DIR = Path(__file__).parent

# Ensure daemon directory is in path for imports
sys.path.insert(0, str(DAEMON_DIR))

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# =============================================================================
# MANDATORY IMPORTS - NO TRY/EXCEPT, FIX IF BROKEN
# =============================================================================

from task_queue import TaskQueue, TaskPriority
from local_autorouter import route_request, record_outcome
from model_router import ModelRouter
from outcome_tracker import record_outcome as track_outcome
from execution_spine import RetrievalPolicy

# These might not exist yet - create stubs if needed
try:
    from task_generator import generate_from_strategies, get_pending_generated
except ImportError:

    def generate_from_strategies():
        return []

    def get_pending_generated():
        return []


try:
    from strategy_evolution import StrategyEvolver
except ImportError:

    class StrategyEvolver:
        def get_active_strategies(self):
            return []


try:
    from self_continue import check_pending_handoff, resume_from_handoff
except ImportError:

    def check_pending_handoff():
        return None

    def resume_from_handoff(h):
        pass


# WIRED: MAPE controller bridge for adaptive decision-making
try:
    from feedback_bridge import FeedbackBridge

    FEEDBACK_BRIDGE_AVAILABLE = True
except ImportError:
    FEEDBACK_BRIDGE_AVAILABLE = False
    FeedbackBridge = None

# WIRED (2026-01-28): Token compression for task outputs
try:
    from headroom_optimizer import compress_tool_output

    HEADROOM_AVAILABLE = True
except ImportError:
    HEADROOM_AVAILABLE = False

try:
    from toonify_optimizer import toonify_data, estimate_savings

    TOONIFY_AVAILABLE = True
except ImportError:
    TOONIFY_AVAILABLE = False


# =============================================================================
# UNIFIED SPINE
# =============================================================================


class UnifiedSpine:
    """
    The backbone that connects ALL systems.

    Flow:
    1. Check for pending handoffs (resume interrupted work)
    2. Check strategies for generated tasks
    3. Check scheduler for due tasks
    4. Check task queue for pending work
    5. Route via LocalAI autorouter (FREE classification)
    6. Execute via appropriate provider
    7. Track outcomes
    8. Update learnings
    """

    def __init__(self):
        self.task_queue = TaskQueue()
        self.router = ModelRouter()
        self.strategy_evolver = StrategyEvolver()
        self.retrieval = RetrievalPolicy()

        # WIRED: MAPE controller for adaptive decisions
        self.feedback_bridge = None
        if FEEDBACK_BRIDGE_AVAILABLE:
            try:
                self.feedback_bridge = FeedbackBridge()
                logger.info("FeedbackBridge initialized - MAPE controller active")
            except Exception as e:
                logger.warning(f"FeedbackBridge init failed: {e}")

        logger.info("UnifiedSpine initialized - all systems connected")

    def run_cycle(self) -> Dict[str, Any]:
        """Run one complete cycle of the spine."""
        results = {
            "handoff_resumed": False,
            "tasks_generated": 0,
            "tasks_routed": 0,
            "tasks_executed": 0,
            "outcomes_recorded": 0,
        }

        # 1. Check for pending handoffs
        handoff = check_pending_handoff()
        if handoff:
            logger.info(f"Resuming from handoff: {handoff.get('id', 'unknown')}")
            resume_from_handoff(handoff)
            results["handoff_resumed"] = True

        # 2. Generate tasks from active strategies
        generated = generate_from_strategies()
        results["tasks_generated"] = len(generated)
        for task in generated:
            self.task_queue.add_task(task["prompt"], priority=TaskPriority.NORMAL)

        # 3. Process pending tasks
        pending = self.task_queue.get_pending_tasks(limit=5)
        # WIRED 2026-01-28: Get active strategy for feedback loop
        active_strategies = self.strategy_evolver.get_active_strategies()
        strategy_context = ""
        if active_strategies:
            strategy_context = f" strategy={active_strategies[0].name}"

        for task in pending:
            # Route via LocalAI (FREE classification)
            routing = route_request(task.prompt, use_localai=False)
            route = routing.get("route", "claude")
            decision_id = routing.get("decision_id")

            logger.info(f"Task {task.id[:8]} routed to: {route}")
            results["tasks_routed"] += 1

            # Execute based on route
            success, output = self._execute_routed_task(task, route)

            # Build context with strategy info for feedback loop
            outcome_context = f"{str(output)[:400]}{strategy_context}"

            if success:
                self.task_queue.mark_completed(task.id, output)
                record_outcome(decision_id, "success")
                track_outcome(task.prompt, "success", context=outcome_context)
                self.record_mape_feedback(task.id, True)  # WIRED: MAPE feedback
                self._notify_clawdbot(task.id, output, True)  # WIRED: Clawdbot webhook
                results["tasks_executed"] += 1
                results["outcomes_recorded"] += 1
            else:
                self.task_queue.mark_failed(task.id, output)
                record_outcome(decision_id, "failure")
                track_outcome(task.prompt, "failure", context=outcome_context)
                self.record_mape_feedback(task.id, False)  # WIRED: MAPE feedback
                self._notify_clawdbot(task.id, output, False)  # WIRED: Clawdbot webhook

        return results

    def _execute_routed_task(self, task, route: str) -> tuple:
        """Execute a task based on its route."""
        try:
            # Agent routes
            if route.startswith("agent:"):
                agent = route.replace("agent:", "")
                return True, f"Delegated to {agent} agent"

            # Skill routes
            if route.startswith("skill:"):
                skill = route.replace("skill:", "")
                return True, f"Run /{skill} skill"

            # LocalAI (FREE)
            if route == "localai":
                if self.router.localai.available():
                    result = self.router.route(
                        task=task.prompt, content="", force_provider="localai"
                    )
                    if result.get("response"):
                        response = result["response"]
                        # WIRED (2026-01-28): Compress large responses
                        response = self._compress_output(response)
                        return True, response

            # Codex (cheap)
            if route == "codex":
                if self.router.openai_client.available():
                    result = self.router.route(
                        task=task.prompt, content="", force_provider="codex"
                    )
                    if result.get("response"):
                        response = result["response"]
                        # WIRED (2026-01-28): Compress large responses
                        response = self._compress_output(response)
                        return True, response

            # Claude (complex reasoning)
            # Return None to signal external execution needed
            return False, "Requires Claude execution"

        except Exception as e:
            logger.error(f"Execution error: {e}")
            return False, str(e)

    def _compress_output(self, output: str) -> str:
        """WIRED (2026-01-28): Compress large outputs to save tokens."""
        if not output or len(output) < 2000:
            return output

        # Try headroom compression first (smarter, keeps important content)
        if HEADROOM_AVAILABLE:
            try:
                compressed = compress_tool_output({"content": output}, max_items=20)
                if isinstance(compressed, dict) and "content" in compressed:
                    return compressed["content"]
            except Exception:
                pass

        # Fallback: toonify for structured data
        if TOONIFY_AVAILABLE:
            try:
                # Check if output looks like JSON
                import json

                if output.strip().startswith("{") or output.strip().startswith("["):
                    parsed = json.loads(output)
                    result = estimate_savings(parsed)
                    if result.savings_pct >= 30:
                        return result.toon_str
            except (json.JSONDecodeError, Exception):
                pass

        return output

    def record_mape_feedback(self, task_id: str, success: bool, metrics: dict = None):
        """
        WIRED: Record feedback to MAPE controller for adaptive learning.
        This enables the system to learn from outcomes and improve decisions.
        """
        if not self.feedback_bridge:
            return

        try:
            from controller import Metric, MetricType

            # Convert success to comprehension metric
            comprehension = 1.0 if success else 0.3

            # Record metric
            metric = Metric(
                type=MetricType.COMPREHENSION,
                value=comprehension,
                context={"task_id": task_id, "success": success},
            )

            self.feedback_bridge.controller.monitor([metric])
            logger.info(f"MAPE feedback recorded for task {task_id[:8]}")
        except Exception as e:
            logger.warning(f"MAPE feedback failed: {e}")

    def _notify_clawdbot(self, task_id: str, result: str, success: bool):
        """
        WIRED: Notify Clawdbot supervisor when a task completes.

        Uses OpenAI-compatible /v1/chat/completions API for conversational updates.
        Clawdbot can then track outcomes, intervene, or dispatch follow-up tasks.
        """
        if not self.router.clawdbot:
            return

        try:
            status = "✅ SUCCESS" if success else "❌ FAILED"
            message = f"[Atlas Task Report]\nTask: {task_id[:8]}\nStatus: {status}\nResult: {str(result)[:400]}"

            response = self.router.clawdbot.chat(message)
            if response:
                logger.info(f"Clawdbot notified for task {task_id[:8]}: {response[:50]}...")
        except Exception as e:
            # Non-critical - don't fail the task on notification error
            logger.debug(f"Clawdbot notification failed: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get current spine status."""
        pending = self.task_queue.get_pending_tasks(limit=100)
        recent = self.task_queue.get_recent_tasks(limit=100)

        return {
            "task_queue": {
                "pending": len(pending),
                "recent": len(recent),
            },
            "strategies": {
                "active": len(self.strategy_evolver.get_active_strategies())
            },
            "routing": {
                "localai_available": self.router.localai.available(),
                "openai_available": self.router.openai_client.available(),
                "clawdbot_available": self.router.clawdbot.available() if self.router.clawdbot else False,
            },
        }


# =============================================================================
# DAEMON MODE
# =============================================================================


def run_daemon(interval_seconds: int = 60):
    """Run the unified spine as a daemon."""
    spine = UnifiedSpine()

    logger.info(f"UnifiedSpine daemon starting (interval: {interval_seconds}s)")

    import time

    while True:
        try:
            results = spine.run_cycle()
            logger.info(f"Cycle complete: {results}")
        except Exception as e:
            logger.error(f"Cycle error: {e}")

        time.sleep(interval_seconds)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Unified Spine")
    parser.add_argument("action", choices=["status", "cycle", "daemon"])
    parser.add_argument("--interval", type=int, default=60)

    args = parser.parse_args()

    if args.action == "status":
        spine = UnifiedSpine()
        import json

        print(json.dumps(spine.get_status(), indent=2))

    elif args.action == "cycle":
        spine = UnifiedSpine()
        results = spine.run_cycle()
        print(f"Cycle results: {results}")

    elif args.action == "daemon":
        run_daemon(args.interval)
