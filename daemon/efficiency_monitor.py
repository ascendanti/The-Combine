#!/usr/bin/env python3
"""
Efficiency Monitor - Self-aware analytics for detecting declining efficiency.

WIRING: Called by Stop hook to analyze session efficiency.
Alerts when:
- Context usage is bloating (tokens increasing without progress)
- Same errors repeat (indicates not learning)
- Too many iterations without task completion
- Tool use patterns indicate thrashing

Auto-stores alerts in deferred_tasks for review.
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

DAEMON_DIR = Path(__file__).parent
DB_PATH = DAEMON_DIR / "efficiency.db"

# Thresholds for alerting
REPEATED_ERROR_THRESHOLD = 2  # Same error pattern N times = alert
TOOL_ITERATION_THRESHOLD = 5  # Same tool N times without progress = alert
TOKEN_BLOAT_RATIO = 1.5  # Token use 50% higher than needed = alert


@dataclass
class EfficiencyMetrics:
    """Metrics for a session/turn."""
    tool_calls: int
    unique_tools: int
    errors_count: int
    repeated_errors: int
    tokens_used: int  # Approximate
    tasks_completed: int
    timestamp: str


class EfficiencyMonitor:
    """
    Monitors efficiency and alerts on declining performance.

    Tracks:
    - Error repetition (not learning from mistakes)
    - Tool thrashing (same tool repeatedly without progress)
    - Context bloat (excessive token use)
    """

    def __init__(self):
        self._init_db()
        self._session_errors: Dict[str, int] = {}  # error_pattern -> count
        self._session_tool_calls: List[str] = []

    def _init_db(self):
        """Initialize efficiency database."""
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS efficiency_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                tool_calls INTEGER,
                unique_tools INTEGER,
                errors_count INTEGER,
                repeated_errors INTEGER,
                tokens_estimate INTEGER,
                tasks_completed INTEGER,
                alerts TEXT,
                timestamp TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS error_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT NOT NULL,
                count INTEGER DEFAULT 1,
                last_seen TEXT,
                resolved INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

    def record_tool_call(self, tool_name: str, success: bool, error_msg: str = ""):
        """Record a tool call for analysis."""
        self._session_tool_calls.append(tool_name)

        if not success and error_msg:
            # Normalize error pattern
            pattern = self._normalize_error(error_msg)
            self._session_errors[pattern] = self._session_errors.get(pattern, 0) + 1

            # Check for repeated errors
            if self._session_errors[pattern] >= REPEATED_ERROR_THRESHOLD:
                self._store_alert(
                    f"REPEATED_ERROR: '{pattern[:50]}...' occurred {self._session_errors[pattern]} times",
                    priority=4
                )

    def _normalize_error(self, error_msg: str) -> str:
        """Normalize error message to pattern."""
        # Remove specific values, keep structure
        import re
        # Remove file paths, numbers, quotes content
        pattern = re.sub(r'[\'"].*?[\'"]', '""', error_msg)
        pattern = re.sub(r'\d+', 'N', pattern)
        pattern = re.sub(r'[A-Za-z]:\\[^\s]+', 'PATH', pattern)
        return pattern[:100]

    def check_tool_thrashing(self) -> Optional[str]:
        """Check if same tool is being called repeatedly without progress."""
        if len(self._session_tool_calls) < TOOL_ITERATION_THRESHOLD:
            return None

        # Check last N calls
        recent = self._session_tool_calls[-TOOL_ITERATION_THRESHOLD:]
        if len(set(recent)) == 1:
            tool = recent[0]
            return f"TOOL_THRASHING: {tool} called {TOOL_ITERATION_THRESHOLD} times consecutively"

        return None

    def analyze_session(self, session_data: Dict = None) -> Dict:
        """
        Analyze session efficiency and return alerts.

        Returns dict with:
        - alerts: List of efficiency alerts
        - metrics: EfficiencyMetrics
        - recommendations: List of suggestions
        """
        alerts = []
        recommendations = []

        # Get token usage from token_monitor
        token_stats = self._get_token_stats()
        total_tokens = token_stats.get("total_tokens", 0)
        avg_per_turn = token_stats.get("avg_per_turn", 0)

        # Check for token bloat (high avg tokens per turn)
        if avg_per_turn > 50000:  # 50k tokens per turn is concerning
            alerts.append(f"TOKEN_BLOAT: {avg_per_turn:.0f} avg tokens/turn (target <30k)")
            recommendations.append("Consider more focused queries or context pruning")

        # Check cache efficiency
        cache_read = token_stats.get("total_cache_read", 0)
        if total_tokens > 100000 and cache_read < total_tokens * 0.3:
            alerts.append(f"LOW_CACHE_HIT: Only {cache_read/total_tokens*100:.1f}% cache utilization")
            recommendations.append("Reuse file reads, batch similar operations")

        # Check repeated errors
        for pattern, count in self._session_errors.items():
            if count >= REPEATED_ERROR_THRESHOLD:
                alerts.append(f"Error pattern repeated {count} times: {pattern[:50]}")
                recommendations.append("Check command_optimizer for stored workarounds")

        # Check tool thrashing
        thrashing = self.check_tool_thrashing()
        if thrashing:
            alerts.append(thrashing)
            recommendations.append("Consider different approach or ask for clarification")

        # Check if making progress
        unique_tools = len(set(self._session_tool_calls))
        total_calls = len(self._session_tool_calls)
        if total_calls > 10 and unique_tools < 3:
            alerts.append(f"LOW_VARIETY: {total_calls} calls using only {unique_tools} unique tools")
            recommendations.append("May be stuck - try different strategy")

        # Store metrics
        metrics = EfficiencyMetrics(
            tool_calls=total_calls,
            unique_tools=unique_tools,
            errors_count=sum(self._session_errors.values()),
            repeated_errors=sum(1 for c in self._session_errors.values() if c >= REPEATED_ERROR_THRESHOLD),
            tokens_used=total_tokens,
            tasks_completed=0,  # Would need integration with task system
            timestamp=datetime.now().isoformat()
        )

        # Persist to efficiency_log
        self._persist_metrics(metrics, alerts)

        return {
            "alerts": alerts,
            "metrics": metrics,
            "recommendations": recommendations,
            "efficiency_score": self._calculate_score(metrics, alerts)
        }

    def _persist_metrics(self, metrics: EfficiencyMetrics, alerts: List[str]):
        """Persist session metrics to efficiency_log table."""
        try:
            import os
            session_id = os.environ.get("CLAUDE_SESSION_ID", datetime.now().strftime("%Y%m%d_%H%M"))
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute("""
                INSERT INTO efficiency_log
                (session_id, tool_calls, unique_tools, errors_count, repeated_errors,
                 tokens_estimate, tasks_completed, alerts, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                metrics.tool_calls,
                metrics.unique_tools,
                metrics.errors_count,
                metrics.repeated_errors,
                metrics.tokens_used,
                metrics.tasks_completed,
                json.dumps(alerts),
                metrics.timestamp
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass  # Silent failure

    def _calculate_score(self, metrics: EfficiencyMetrics, alerts: List[str]) -> float:
        """Calculate efficiency score 0-1."""
        score = 1.0

        # Penalize for repeated errors
        score -= metrics.repeated_errors * 0.1

        # Penalize for low tool variety (potential thrashing)
        if metrics.tool_calls > 5:
            variety_ratio = metrics.unique_tools / metrics.tool_calls
            if variety_ratio < 0.2:
                score -= 0.2

        # Penalize for alerts
        score -= len(alerts) * 0.1

        return max(0.0, min(1.0, score))

    def _store_alert(self, alert: str, priority: int = 3):
        """Store alert in deferred_tasks for review."""
        try:
            import sys
            sys.path.insert(0, str(DAEMON_DIR))
            from deferred_tasks import DeferredTaskCapture
            capture = DeferredTaskCapture()
            capture.capture(
                content=f"EFFICIENCY ALERT: {alert}",
                source="efficiency_monitor",
                priority=priority,
                tags=["efficiency", "alert", "auto-generated"]
            )
        except Exception:
            pass  # Silent failure

    def reset_session(self):
        """Reset session tracking."""
        self._session_errors = {}
        self._session_tool_calls = []

    def _get_token_stats(self) -> Dict:
        """Get token usage stats from token_monitor."""
        try:
            from token_monitor import get_current_session_tokens
            return get_current_session_tokens()
        except ImportError:
            return {"total_tokens": 0, "avg_per_turn": 0}
        except Exception:
            return {"total_tokens": 0, "avg_per_turn": 0}


# Singleton instance
_monitor = None

def get_monitor() -> EfficiencyMonitor:
    """Get or create monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = EfficiencyMonitor()
    return _monitor


def record_tool(tool_name: str, success: bool = True, error: str = ""):
    """Convenience function to record tool call."""
    get_monitor().record_tool_call(tool_name, success, error)


def analyze() -> Dict:
    """Convenience function to analyze current session."""
    return get_monitor().analyze_session()


# CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Efficiency Monitor")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("analyze", help="Analyze current session")
    subparsers.add_parser("reset", help="Reset session tracking")

    record_parser = subparsers.add_parser("record", help="Record a tool call")
    record_parser.add_argument("tool", help="Tool name")
    record_parser.add_argument("--error", default="", help="Error message if failed")

    args = parser.parse_args()
    monitor = get_monitor()

    if args.command == "analyze":
        result = monitor.analyze_session()
        print(json.dumps({
            "alerts": result["alerts"],
            "efficiency_score": result["efficiency_score"],
            "recommendations": result["recommendations"],
            "tool_calls": result["metrics"].tool_calls,
            "repeated_errors": result["metrics"].repeated_errors
        }, indent=2))

    elif args.command == "reset":
        monitor.reset_session()
        print("Session tracking reset")

    elif args.command == "record":
        success = not args.error
        monitor.record_tool_call(args.tool, success, args.error)
        print(f"Recorded: {args.tool} ({'success' if success else 'error'})")

    else:
        parser.print_help()
