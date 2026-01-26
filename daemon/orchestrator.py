#!/usr/bin/env python3
"""
Central Orchestrator - Grand Strategy Unifier

Unifies all subsystems under a single optimization loop:
- Model Router (cost optimization)
- Strategy Evolution (approach optimization)
- Task Generator (work identification)
- Memory System (learning retention)
- Outcome Tracker (feedback loop)

This is the BRAIN that coordinates everything automatically.
"""

import os
import sys
import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

# Add daemon to path
DAEMON_DIR = Path(__file__).parent
sys.path.insert(0, str(DAEMON_DIR))

from model_router import ModelRouter, classify_task, TaskType, Provider, CascadeRouter

# WIRED: Swarms for multi-agent orchestration
try:
    from swarms import Agent
    from swarms.structs import SequentialWorkflow, ConcurrentWorkflow
    SWARMS_AVAILABLE = True
except ImportError:
    SWARMS_AVAILABLE = False
    Agent = None
    SequentialWorkflow = None
    ConcurrentWorkflow = None

DB_PATH = DAEMON_DIR / "orchestrator.db"

# ============================================================================
# Configuration
# ============================================================================

class Priority(str, Enum):
    CRITICAL = "critical"   # Do immediately
    HIGH = "high"           # Do soon
    MEDIUM = "medium"       # Do when convenient
    LOW = "low"             # Do when idle
    BACKGROUND = "background"  # Only when nothing else

@dataclass
class OrchestratorConfig:
    """Central configuration for orchestration."""
    # Routing
    prefer_local: bool = True           # Prefer LocalAI when possible
    cascade_enabled: bool = True        # Use cascade routing
    max_concurrent_tasks: int = 3       # Parallel task limit

    # Learning
    auto_learn: bool = True             # Auto-extract learnings
    memory_recall_k: int = 3            # Top-k memories to recall

    # Strategy
    strategy_evolution: bool = True     # Evolve strategies automatically
    min_strategy_fitness: float = 0.3   # Minimum fitness to use

    # Self-optimization
    optimize_interval_hours: int = 1    # Run optimization every N hours
    token_budget_daily: int = 100000    # Daily token budget

    # Timeouts (fast)
    classification_timeout: float = 2.0
    routing_timeout: float = 10.0

# ============================================================================
# Database
# ============================================================================

def init_db():
    """Initialize orchestrator database."""
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS decisions (
            id TEXT PRIMARY KEY,
            timestamp TEXT,
            task TEXT,
            task_type TEXT,
            provider TEXT,
            strategy_id TEXT,
            input_tokens INTEGER,
            output_tokens INTEGER,
            latency_ms INTEGER,
            success INTEGER,
            quality_score REAL,
            cost REAL
        );

        CREATE TABLE IF NOT EXISTS optimization_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            decisions_analyzed INTEGER,
            improvements_found INTEGER,
            actions_taken TEXT
        );

        CREATE TABLE IF NOT EXISTS active_strategies (
            id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            fitness REAL,
            uses INTEGER DEFAULT 0,
            last_used TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_decisions_timestamp ON decisions(timestamp);
        CREATE INDEX IF NOT EXISTS idx_decisions_task_type ON decisions(task_type);
    """)
    conn.commit()
    conn.close()

# ============================================================================
# Fast Classification (No LLM Call)
# ============================================================================

def fast_classify(task: str) -> Dict[str, Any]:
    """
    Ultra-fast task classification using rules only (no LLM).
    Returns classification in <1ms.
    """
    task_lower = task.lower()

    # Intent patterns (fast regex-free matching)
    intents = {
        "summarize": ["summarize", "summary", "tldr", "brief", "condense"],
        "code": ["implement", "write code", "create function", "fix bug", "refactor"],
        "research": ["research", "find", "search", "lookup", "what is", "how does"],
        "analyze": ["analyze", "review", "audit", "evaluate", "assess"],
        "plan": ["plan", "design", "architect", "structure", "organize"],
        "debug": ["debug", "fix", "broken", "error", "failing", "issue"],
        "test": ["test", "verify", "validate", "check", "confirm"],
        "document": ["document", "explain", "describe", "write docs"],
    }

    detected_intent = "unknown"
    for intent, keywords in intents.items():
        if any(kw in task_lower for kw in keywords):
            detected_intent = intent
            break

    # Complexity estimation (fast heuristics)
    complexity = 1
    if len(task) > 200:
        complexity += 2
    if any(w in task_lower for w in ["complex", "entire", "all", "complete", "comprehensive"]):
        complexity += 3
    if any(w in task_lower for w in ["simple", "quick", "just", "only"]):
        complexity -= 1
    complexity = max(1, min(10, complexity))

    # Route decision
    if detected_intent in ["summarize", "document"] and complexity < 5:
        route = "localai"
    elif detected_intent in ["code", "debug", "refactor"] and complexity < 7:
        route = "codex"
    elif detected_intent in ["plan", "architect"] or complexity >= 7:
        route = "claude"
    else:
        route = "codex"  # Default to middle tier

    # Agent mapping
    agent_map = {
        "research": "oracle",
        "code": "kraken",
        "debug": "sleuth",
        "analyze": "scout",
        "plan": "architect",
        "test": "arbiter",
    }

    return {
        "intent": detected_intent,
        "complexity": complexity,
        "route": route,
        "agent": agent_map.get(detected_intent, "spark"),
        "confidence": 0.8 if detected_intent != "unknown" else 0.4
    }

# ============================================================================
# Central Orchestrator
# ============================================================================

class Orchestrator:
    """
    Central brain that coordinates all subsystems.

    Flow:
    1. Receive task → fast_classify()
    2. Check memory for relevant learnings
    3. Select strategy from evolution pool
    4. Route to appropriate provider/agent
    5. Track outcome and update fitness
    6. Periodically optimize
    """

    def __init__(self, config: OrchestratorConfig = None):
        self.config = config or OrchestratorConfig()
        init_db()

        # Initialize subsystems
        self.router = ModelRouter()
        self.cascade = CascadeRouter(self.router) if self.config.cascade_enabled else None

        # WIRED: Swarms for multi-agent tasks
        self.swarms_enabled = SWARMS_AVAILABLE
        self._agent_cache = {}  # Cache created agents

        # State
        self.tokens_used_today = 0
        self.last_optimization = None

    def process(self, task: str, content: str = "", context: Dict = None) -> Dict[str, Any]:
        """
        Main entry point - process a task through the orchestration pipeline.
        """
        import time
        start = time.time()
        decision_id = f"dec_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hashlib.md5(task.encode()).hexdigest()[:8]}"

        # Step 1: Fast classification (no LLM)
        classification = fast_classify(task)

        # Step 2: Memory recall (if available)
        memories = []
        if self.config.auto_learn:
            memories = self._recall_memories(task, classification["intent"])

        # Step 3: Strategy selection
        strategy = self._select_strategy(classification["intent"])

        # Step 4: Route to provider
        if self.config.cascade_enabled and self.cascade:
            result = self.cascade.route_with_cascade(task, content)
        else:
            result = self.router.route(task, content)

        latency = int((time.time() - start) * 1000)

        # Step 5: Record decision
        self._record_decision(
            decision_id=decision_id,
            task=task[:500],
            classification=classification,
            strategy=strategy,
            result=result,
            latency=latency
        )

        # Step 6: Check if optimization needed
        self._maybe_optimize()

        return {
            "decision_id": decision_id,
            "classification": classification,
            "strategy": strategy,
            "result": result,
            "memories": memories,
            "latency_ms": latency
        }

    def _recall_memories(self, task: str, intent: str) -> List[str]:
        """Recall relevant memories from storage."""
        try:
            # Try to import and use memory system
            from memory import MemoryManager
            mm = MemoryManager()
            results = mm.search(f"{intent} {task[:100]}", k=self.config.memory_recall_k)
            return [r.get("content", "") for r in results if r.get("content")]
        except:
            return []

    def _select_strategy(self, intent: str) -> Optional[Dict]:
        """Select best strategy for this intent."""
        if not self.config.strategy_evolution:
            return None

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("""
            SELECT id, name, description, fitness, uses
            FROM active_strategies
            WHERE fitness >= ? AND name LIKE ?
            ORDER BY fitness DESC, uses ASC
            LIMIT 1
        """, (self.config.min_strategy_fitness, f"%{intent}%"))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "fitness": row[3],
                "uses": row[4]
            }
        return None

    def _record_decision(self, decision_id: str, task: str,
                         classification: Dict, strategy: Optional[Dict],
                         result: Dict, latency: int):
        """Record decision for learning."""
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO decisions (id, timestamp, task, task_type, provider,
                                   strategy_id, input_tokens, output_tokens,
                                   latency_ms, success, cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            decision_id,
            datetime.now().isoformat(),
            task,
            classification["intent"],
            result.get("provider", "unknown"),
            strategy["id"] if strategy else None,
            result.get("tokens_used", {}).get("input", 0),
            result.get("tokens_used", {}).get("output", 0),
            latency,
            1 if not result.get("error") else 0,
            result.get("cost", 0)
        ))
        conn.commit()
        conn.close()

        # Update token counter
        self.tokens_used_today += result.get("tokens_used", {}).get("input", 0)
        self.tokens_used_today += result.get("tokens_used", {}).get("output", 0)

    def _maybe_optimize(self):
        """Run optimization if enough time has passed."""
        now = datetime.now()
        if self.last_optimization:
            elapsed = (now - self.last_optimization).total_seconds() / 3600
            if elapsed < self.config.optimize_interval_hours:
                return

        self.optimize()
        self.last_optimization = now

    def optimize(self) -> Dict[str, Any]:
        """
        Run optimization loop:
        1. Analyze recent decisions
        2. Update strategy fitness
        3. Generate improvement suggestions
        """
        conn = sqlite3.connect(DB_PATH)

        # Get recent decisions
        cursor = conn.execute("""
            SELECT task_type, provider, success, latency_ms, cost
            FROM decisions
            WHERE timestamp > datetime('now', '-24 hours')
        """)
        decisions = cursor.fetchall()

        if not decisions:
            conn.close()
            return {"status": "no_data", "improvements": []}

        # Analyze patterns
        by_type = {}
        for task_type, provider, success, latency, cost in decisions:
            if task_type not in by_type:
                by_type[task_type] = {"total": 0, "success": 0, "latency": [], "cost": 0}
            by_type[task_type]["total"] += 1
            by_type[task_type]["success"] += success
            by_type[task_type]["latency"].append(latency)
            by_type[task_type]["cost"] += cost or 0

        # Generate improvements
        improvements = []
        for task_type, stats in by_type.items():
            success_rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0
            avg_latency = sum(stats["latency"]) / len(stats["latency"]) if stats["latency"] else 0

            if success_rate < 0.8:
                improvements.append({
                    "type": "success_rate",
                    "task_type": task_type,
                    "current": success_rate,
                    "suggestion": f"Consider routing {task_type} to a more capable provider"
                })

            if avg_latency > 5000:  # 5 seconds
                improvements.append({
                    "type": "latency",
                    "task_type": task_type,
                    "current": avg_latency,
                    "suggestion": f"Consider caching or pre-computing for {task_type} tasks"
                })

        # Record optimization run
        conn.execute("""
            INSERT INTO optimization_runs (timestamp, decisions_analyzed,
                                           improvements_found, actions_taken)
            VALUES (?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            len(decisions),
            len(improvements),
            json.dumps([i["suggestion"] for i in improvements])
        ))
        conn.commit()
        conn.close()

        return {
            "status": "completed",
            "decisions_analyzed": len(decisions),
            "by_type": by_type,
            "improvements": improvements
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        conn = sqlite3.connect(DB_PATH)

        # Total decisions
        cursor = conn.execute("SELECT COUNT(*) FROM decisions")
        total = cursor.fetchone()[0]

        # Success rate
        cursor = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(success) as successes,
                AVG(latency_ms) as avg_latency,
                SUM(cost) as total_cost
            FROM decisions
            WHERE timestamp > datetime('now', '-24 hours')
        """)
        row = cursor.fetchone()

        # By provider
        cursor = conn.execute("""
            SELECT provider, COUNT(*), SUM(cost)
            FROM decisions
            WHERE timestamp > datetime('now', '-24 hours')
            GROUP BY provider
        """)
        by_provider = {r[0]: {"calls": r[1], "cost": r[2] or 0} for r in cursor.fetchall()}

        conn.close()

        return {
            "total_decisions": total,
            "last_24h": {
                "total": row[0] or 0,
                "success_rate": (row[1] or 0) / (row[0] or 1),
                "avg_latency_ms": row[2] or 0,
                "total_cost": row[3] or 0
            },
            "by_provider": by_provider,
            "tokens_used_today": self.tokens_used_today,
            "token_budget_remaining": self.config.token_budget_daily - self.tokens_used_today,
            "swarms_enabled": self.swarms_enabled
        }

    # =========================================================================
    # WIRED: Swarms Multi-Agent Orchestration
    # =========================================================================

    def run_swarm_workflow(self, tasks: List[str], workflow_type: str = "sequential",
                           agent_configs: List[Dict] = None) -> Dict[str, Any]:
        """
        Run a multi-agent workflow using Swarms.

        Args:
            tasks: List of task prompts
            workflow_type: "sequential" or "concurrent"
            agent_configs: Optional agent configurations

        Returns:
            Dict with workflow results and metadata
        """
        if not self.swarms_enabled:
            return {"error": "Swarms not available", "results": []}

        try:
            # Create agents for each task
            agents = []
            for i, task in enumerate(tasks):
                agent_name = f"agent_{i}"
                if agent_name not in self._agent_cache:
                    # Create minimal agent (Swarms will use its default model)
                    agent = Agent(
                        agent_name=agent_name,
                        system_prompt=f"You are agent {i}. Complete tasks efficiently.",
                        max_loops=1
                    )
                    self._agent_cache[agent_name] = agent
                agents.append(self._agent_cache[agent_name])

            # Create workflow based on type
            if workflow_type == "concurrent":
                workflow = ConcurrentWorkflow(
                    agents=agents,
                    max_workers=min(len(agents), self.config.max_concurrent_tasks)
                )
            else:
                workflow = SequentialWorkflow(agents=agents)

            # Run workflow
            results = workflow.run(tasks[0] if len(tasks) == 1 else str(tasks))

            return {
                "workflow_type": workflow_type,
                "tasks_count": len(tasks),
                "agents_used": len(agents),
                "results": results,
                "success": True
            }

        except Exception as e:
            return {
                "error": str(e),
                "workflow_type": workflow_type,
                "success": False
            }

    def should_use_swarm(self, classification: Dict) -> bool:
        """
        Determine if task should use Swarms multi-agent workflow.

        Uses swarm for:
        - High complexity tasks (>= 7)
        - Tasks requiring multiple capabilities
        - Explicit multi-step tasks
        """
        if not self.swarms_enabled:
            return False

        complexity = classification.get("complexity", 1)
        intent = classification.get("intent", "")

        # High complexity tasks benefit from multi-agent
        if complexity >= 7:
            return True

        # Multi-step intents
        multi_step_intents = ["plan", "architect", "refactor", "analyze"]
        if intent in multi_step_intents:
            return True

        return False

# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Central Orchestrator')
    parser.add_argument('action', choices=['stats', 'optimize', 'process', 'classify'],
                        help='Action to perform')
    parser.add_argument('--task', type=str, help='Task to process/classify')
    parser.add_argument('--content', type=str, default='', help='Content for task')

    args = parser.parse_args()
    orch = Orchestrator()

    if args.action == 'stats':
        stats = orch.get_stats()
        print(json.dumps(stats, indent=2))

    elif args.action == 'optimize':
        result = orch.optimize()
        print(json.dumps(result, indent=2))

    elif args.action == 'classify':
        if not args.task:
            print("Error: --task required for classify")
            sys.exit(1)
        result = fast_classify(args.task)
        print(json.dumps(result, indent=2))

    elif args.action == 'process':
        if not args.task:
            print("Error: --task required for process")
            sys.exit(1)
        result = orch.process(args.task, args.content)
        print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    main()
