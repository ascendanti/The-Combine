#!/usr/bin/env python3
"""
MAPE Controller - Adaptive Control Loop for Learning Systems

Implements Monitor-Analyze-Plan-Execute feedback loop for:
- Comprehension quality optimization
- Token efficiency tuning
- Strategy adaptation
- Chunk size control

Based on control theory principles + Confucius introspection pattern.

Usage:
    from controller import MAPEController
    ctrl = MAPEController()
    ctrl.monitor(metrics)
    action = ctrl.analyze_and_plan()
    ctrl.execute(action)
    ctrl.feedback(outcome)
"""

import json
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from enum import Enum
import statistics

CONTROLLER_DB = Path(__file__).parent / "controller.db"

# ============================================================================
# Data Models
# ============================================================================

class MetricType(str, Enum):
    COMPREHENSION = "comprehension"      # Quality of understanding (0-1)
    TOKEN_EFFICIENCY = "token_efficiency"  # Comprehension per token
    CHUNK_QUALITY = "chunk_quality"       # How well chunks preserve meaning
    RETRIEVAL_ACCURACY = "retrieval_accuracy"  # Semantic search precision
    PROCESSING_TIME = "processing_time"   # Latency metrics

class ActionType(str, Enum):
    ADJUST_CHUNK_SIZE = "adjust_chunk_size"
    CHANGE_OVERLAP = "change_overlap"
    SWITCH_STRATEGY = "switch_strategy"
    MODIFY_PROMPT = "modify_prompt"
    ENABLE_CACHING = "enable_caching"
    ADJUST_RETRIEVAL_K = "adjust_retrieval_k"

@dataclass
class Metric:
    """A measured performance metric."""
    type: MetricType
    value: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    context: Dict[str, Any] = field(default_factory=dict)
    book_id: Optional[str] = None

@dataclass
class ControlState:
    """Current control system state."""
    chunk_size: int = 500          # Target tokens per chunk
    chunk_overlap: int = 50        # Overlap tokens between chunks
    retrieval_k: int = 5           # Number of chunks to retrieve
    strategy: str = "semantic"     # retrieval strategy
    prompt_template: str = "default"
    caching_enabled: bool = True

@dataclass
class Action:
    """A control action to execute."""
    type: ActionType
    parameters: Dict[str, Any]
    rationale: str
    predicted_improvement: float = 0.0

@dataclass
class Outcome:
    """Result of an executed action."""
    action_id: str
    success: bool
    metrics_before: Dict[str, float]
    metrics_after: Dict[str, float]
    improvement: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

# ============================================================================
# Database
# ============================================================================

def init_db() -> sqlite3.Connection:
    """Initialize controller database."""
    conn = sqlite3.connect(CONTROLLER_DB)
    c = conn.cursor()

    # Metrics history
    c.execute('''CREATE TABLE IF NOT EXISTS metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        value REAL,
        timestamp TEXT,
        context TEXT,
        book_id TEXT
    )''')

    # Control state history
    c.execute('''CREATE TABLE IF NOT EXISTS state_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        state TEXT,
        timestamp TEXT
    )''')

    # Actions taken
    c.execute('''CREATE TABLE IF NOT EXISTS actions (
        id TEXT PRIMARY KEY,
        type TEXT,
        parameters TEXT,
        rationale TEXT,
        predicted_improvement REAL,
        timestamp TEXT
    )''')

    # Outcomes (for learning)
    c.execute('''CREATE TABLE IF NOT EXISTS outcomes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action_id TEXT,
        success INTEGER,
        metrics_before TEXT,
        metrics_after TEXT,
        improvement REAL,
        timestamp TEXT,
        FOREIGN KEY (action_id) REFERENCES actions(id)
    )''')

    # Strategy effectiveness (Confucius pattern)
    c.execute('''CREATE TABLE IF NOT EXISTS strategy_effectiveness (
        strategy TEXT PRIMARY KEY,
        total_uses INTEGER DEFAULT 0,
        successes INTEGER DEFAULT 0,
        avg_improvement REAL DEFAULT 0.0,
        last_used TEXT
    )''')

    conn.commit()
    return conn

# ============================================================================
# MAPE Controller
# ============================================================================

class MAPEController:
    """
    Monitor-Analyze-Plan-Execute controller for adaptive learning.

    Implements feedback control with:
    - Metric monitoring and trending
    - Gap analysis (actual vs target)
    - Action planning with predicted outcomes
    - Execution and outcome tracking
    - Confucius-style strategy introspection
    """

    def __init__(self):
        self.conn = init_db()
        self.state = self._load_state()
        self.targets = {
            MetricType.COMPREHENSION: 0.8,
            MetricType.TOKEN_EFFICIENCY: 0.001,  # comprehension per token
            MetricType.CHUNK_QUALITY: 0.7,
            MetricType.RETRIEVAL_ACCURACY: 0.8,
        }

    def _load_state(self) -> ControlState:
        """Load current control state from DB."""
        c = self.conn.cursor()
        c.execute('SELECT state FROM state_history ORDER BY id DESC LIMIT 1')
        row = c.fetchone()
        if row:
            data = json.loads(row[0])
            return ControlState(**data)
        return ControlState()

    def _save_state(self):
        """Persist current state."""
        c = self.conn.cursor()
        c.execute('INSERT INTO state_history (state, timestamp) VALUES (?, ?)',
                  (json.dumps(asdict(self.state)), datetime.now().isoformat()))
        self.conn.commit()

    # ========================================================================
    # MONITOR - Collect and store metrics
    # ========================================================================

    def monitor(self, metrics: List[Metric]):
        """Record metrics from the system."""
        c = self.conn.cursor()
        for m in metrics:
            c.execute('''INSERT INTO metrics (type, value, timestamp, context, book_id)
                VALUES (?, ?, ?, ?, ?)''',
                (m.type.value, m.value, m.timestamp, json.dumps(m.context), m.book_id))
        self.conn.commit()

    def get_recent_metrics(self, metric_type: MetricType, limit: int = 10) -> List[float]:
        """Get recent values for a metric type."""
        c = self.conn.cursor()
        c.execute('''SELECT value FROM metrics WHERE type = ?
            ORDER BY timestamp DESC LIMIT ?''', (metric_type.value, limit))
        return [row[0] for row in c.fetchall()]

    def get_metric_trend(self, metric_type: MetricType) -> Dict[str, float]:
        """Analyze trend for a metric."""
        values = self.get_recent_metrics(metric_type, 20)
        if len(values) < 2:
            return {"trend": 0, "mean": values[0] if values else 0, "variance": 0}

        # Simple trend: compare recent to older
        recent = values[:5]
        older = values[5:10] if len(values) > 5 else values[5:]

        recent_mean = statistics.mean(recent)
        older_mean = statistics.mean(older) if older else recent_mean

        return {
            "trend": recent_mean - older_mean,
            "mean": recent_mean,
            "variance": statistics.variance(values) if len(values) > 1 else 0,
            "improving": recent_mean > older_mean
        }

    # ========================================================================
    # ANALYZE - Identify gaps and issues
    # ========================================================================

    def analyze(self) -> Dict[str, Any]:
        """Analyze current state vs targets, identify gaps."""
        analysis = {
            "gaps": {},
            "issues": [],
            "opportunities": []
        }

        for metric_type, target in self.targets.items():
            trend = self.get_metric_trend(metric_type)
            current = trend["mean"]
            gap = target - current

            analysis["gaps"][metric_type.value] = {
                "target": target,
                "current": current,
                "gap": gap,
                "trend": trend["trend"],
                "improving": trend.get("improving", False)
            }

            # Identify issues
            if gap > 0.1:  # Significant underperformance
                if not trend.get("improving"):
                    analysis["issues"].append({
                        "metric": metric_type.value,
                        "severity": "high" if gap > 0.2 else "medium",
                        "message": f"{metric_type.value} is {gap:.2f} below target and not improving"
                    })

            # Identify opportunities
            if trend.get("improving") and gap > 0:
                analysis["opportunities"].append({
                    "metric": metric_type.value,
                    "message": f"{metric_type.value} is improving, could accelerate"
                })

        return analysis

    # ========================================================================
    # PLAN - Generate control actions
    # ========================================================================

    def plan(self, analysis: Dict[str, Any]) -> List[Action]:
        """Generate actions to address identified gaps."""
        actions = []

        for issue in analysis.get("issues", []):
            metric = issue["metric"]

            if metric == MetricType.COMPREHENSION.value:
                # Low comprehension → try larger chunks with more context
                if self.state.chunk_size < 800:
                    actions.append(Action(
                        type=ActionType.ADJUST_CHUNK_SIZE,
                        parameters={"delta": 100},
                        rationale="Increase chunk size for better context preservation",
                        predicted_improvement=0.05
                    ))

            elif metric == MetricType.TOKEN_EFFICIENCY.value:
                # Low efficiency → reduce chunk size, better retrieval
                if self.state.chunk_size > 300:
                    actions.append(Action(
                        type=ActionType.ADJUST_CHUNK_SIZE,
                        parameters={"delta": -100},
                        rationale="Reduce chunk size for better token efficiency",
                        predicted_improvement=0.02
                    ))

            elif metric == MetricType.RETRIEVAL_ACCURACY.value:
                # Poor retrieval → increase overlap, adjust k
                if self.state.chunk_overlap < 100:
                    actions.append(Action(
                        type=ActionType.CHANGE_OVERLAP,
                        parameters={"delta": 25},
                        rationale="Increase overlap to improve retrieval continuity",
                        predicted_improvement=0.03
                    ))

        # Consult strategy effectiveness (Confucius pattern)
        best_strategy = self._get_best_strategy()
        if best_strategy and best_strategy != self.state.strategy:
            actions.append(Action(
                type=ActionType.SWITCH_STRATEGY,
                parameters={"strategy": best_strategy},
                rationale=f"Switch to {best_strategy} based on past performance",
                predicted_improvement=0.05
            ))

        return actions

    def _get_best_strategy(self) -> Optional[str]:
        """Get best performing strategy based on history (Confucius)."""
        c = self.conn.cursor()
        c.execute('''SELECT strategy, avg_improvement, total_uses
            FROM strategy_effectiveness
            WHERE total_uses > 3
            ORDER BY avg_improvement DESC LIMIT 1''')
        row = c.fetchone()
        return row[0] if row else None

    # ========================================================================
    # EXECUTE - Apply control actions
    # ========================================================================

    def execute(self, actions: List[Action]) -> List[str]:
        """Execute planned actions, return action IDs."""
        action_ids = []
        c = self.conn.cursor()

        for action in actions:
            action_id = f"act_{datetime.now().strftime('%Y%m%d%H%M%S')}_{action.type.value[:4]}"

            # Apply action to state
            if action.type == ActionType.ADJUST_CHUNK_SIZE:
                self.state.chunk_size += action.parameters.get("delta", 0)
                self.state.chunk_size = max(200, min(1000, self.state.chunk_size))

            elif action.type == ActionType.CHANGE_OVERLAP:
                self.state.chunk_overlap += action.parameters.get("delta", 0)
                self.state.chunk_overlap = max(0, min(200, self.state.chunk_overlap))

            elif action.type == ActionType.SWITCH_STRATEGY:
                self.state.strategy = action.parameters.get("strategy", self.state.strategy)

            elif action.type == ActionType.ADJUST_RETRIEVAL_K:
                new_k = action.parameters.get("k", self.state.retrieval_k)
                self.state.retrieval_k = max(1, min(20, new_k))

            elif action.type == ActionType.ENABLE_CACHING:
                self.state.caching_enabled = action.parameters.get("enabled", True)

            # Record action
            c.execute('''INSERT INTO actions (id, type, parameters, rationale, predicted_improvement, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (action_id, action.type.value, json.dumps(action.parameters),
                 action.rationale, action.predicted_improvement, datetime.now().isoformat()))

            action_ids.append(action_id)

        self._save_state()
        self.conn.commit()
        return action_ids

    # ========================================================================
    # FEEDBACK - Learn from outcomes
    # ========================================================================

    def feedback(self, action_id: str, metrics_before: Dict[str, float],
                 metrics_after: Dict[str, float], success: bool):
        """Record outcome of an action for learning."""
        c = self.conn.cursor()

        # Calculate improvement
        improvements = []
        for key in metrics_after:
            if key in metrics_before:
                improvements.append(metrics_after[key] - metrics_before[key])
        avg_improvement = statistics.mean(improvements) if improvements else 0

        # Store outcome
        c.execute('''INSERT INTO outcomes
            (action_id, success, metrics_before, metrics_after, improvement, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)''',
            (action_id, 1 if success else 0, json.dumps(metrics_before),
             json.dumps(metrics_after), avg_improvement, datetime.now().isoformat()))

        # Update strategy effectiveness (Confucius learning)
        c.execute('SELECT type FROM actions WHERE id = ?', (action_id,))
        action_row = c.fetchone()
        if action_row and action_row[0] == ActionType.SWITCH_STRATEGY.value:
            self._update_strategy_effectiveness(self.state.strategy, success, avg_improvement)

        self.conn.commit()

    def _update_strategy_effectiveness(self, strategy: str, success: bool, improvement: float):
        """Update strategy effectiveness tracking (Confucius pattern)."""
        c = self.conn.cursor()

        c.execute('SELECT total_uses, successes, avg_improvement FROM strategy_effectiveness WHERE strategy = ?',
                  (strategy,))
        row = c.fetchone()

        if row:
            total = row[0] + 1
            successes = row[1] + (1 if success else 0)
            # Running average of improvement
            avg_imp = (row[2] * row[0] + improvement) / total
            c.execute('''UPDATE strategy_effectiveness
                SET total_uses = ?, successes = ?, avg_improvement = ?, last_used = ?
                WHERE strategy = ?''',
                (total, successes, avg_imp, datetime.now().isoformat(), strategy))
        else:
            c.execute('''INSERT INTO strategy_effectiveness
                (strategy, total_uses, successes, avg_improvement, last_used)
                VALUES (?, 1, ?, ?, ?)''',
                (strategy, 1 if success else 0, improvement, datetime.now().isoformat()))

        self.conn.commit()

    # ========================================================================
    # Full MAPE Cycle
    # ========================================================================

    def run_cycle(self, new_metrics: List[Metric] = None) -> Dict[str, Any]:
        """Run a complete MAPE cycle."""
        result = {"timestamp": datetime.now().isoformat()}

        # Monitor
        if new_metrics:
            self.monitor(new_metrics)
            result["metrics_recorded"] = len(new_metrics)

        # Analyze
        analysis = self.analyze()
        result["analysis"] = analysis

        # Plan
        actions = self.plan(analysis)
        result["planned_actions"] = [asdict(a) for a in actions]

        # Execute
        if actions:
            action_ids = self.execute(actions)
            result["executed_actions"] = action_ids

        result["new_state"] = asdict(self.state)
        return result

    def get_status(self) -> Dict[str, Any]:
        """Get current controller status."""
        return {
            "state": asdict(self.state),
            "targets": {k.value: v for k, v in self.targets.items()},
            "recent_analysis": self.analyze(),
            "strategy_rankings": self._get_strategy_rankings()
        }

    def _get_strategy_rankings(self) -> List[Dict]:
        """Get strategy effectiveness rankings."""
        c = self.conn.cursor()
        c.execute('''SELECT strategy, total_uses, successes, avg_improvement
            FROM strategy_effectiveness ORDER BY avg_improvement DESC''')
        return [{"strategy": r[0], "uses": r[1], "successes": r[2], "avg_improvement": r[3]}
                for r in c.fetchall()]

# ============================================================================
# CLI Interface
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description='MAPE Controller')
    parser.add_argument('--status', action='store_true', help='Show controller status')
    parser.add_argument('--cycle', action='store_true', help='Run MAPE cycle')
    parser.add_argument('--analyze', action='store_true', help='Run analysis only')
    parser.add_argument('--reset', action='store_true', help='Reset to default state')

    args = parser.parse_args()
    ctrl = MAPEController()

    if args.status:
        print(json.dumps(ctrl.get_status(), indent=2))
    elif args.cycle:
        result = ctrl.run_cycle()
        print(json.dumps(result, indent=2))
    elif args.analyze:
        analysis = ctrl.analyze()
        print(json.dumps(analysis, indent=2))
    elif args.reset:
        ctrl.state = ControlState()
        ctrl._save_state()
        print("Controller reset to defaults")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
