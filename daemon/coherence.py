#!/usr/bin/env python3
"""Goal Coherence Layer - UTF-based unified framework for personal AI.

Implements:
- Goal hierarchy management
- Cross-domain coherence checking
- Module coherence interface
- Constraint propagation
"""

import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Protocol
from dataclasses import dataclass, asdict
from enum import Enum


class GoalTimeframe(str, Enum):
    LONG = "long"      # Life objectives (years)
    MEDIUM = "medium"  # Quarterly/monthly
    SHORT = "short"    # Daily/weekly
    TASK = "task"      # Individual actions


class GoalStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


@dataclass
class Goal:
    id: str
    title: str
    description: str
    timeframe: GoalTimeframe
    status: GoalStatus
    parent_id: Optional[str]  # Hierarchical link
    domains: List[str]        # Affected domains (finance, health, etc.)
    constraints: Dict[str, Any]  # Propagated constraints
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['timeframe'] = self.timeframe.value
        d['status'] = self.status.value
        return d


@dataclass
class Constraint:
    """A constraint that propagates across domains."""
    id: str
    source_goal: str
    domain: str
    type: str  # budget, time, preference, etc.
    value: Any
    priority: int  # Higher = more important
    active: bool


class CoherenceInterface(Protocol):
    """Interface that all domain modules must implement."""

    def get_constraints(self) -> List[Constraint]:
        """Return active constraints from this domain."""
        ...

    def validate_action(self, action: Dict[str, Any]) -> tuple[bool, str]:
        """Validate if action is coherent with goals. Returns (valid, reason)."""
        ...

    def get_context_for(self, domain: str) -> Dict[str, Any]:
        """Return context relevant to another domain."""
        ...


class GoalCoherenceLayer:
    """Central coherence management."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(__file__).parent / "coherence.db"
        self._init_db()
        self._modules: Dict[str, CoherenceInterface] = {}

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        conn.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                timeframe TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                parent_id TEXT,
                domains TEXT NOT NULL,
                constraints TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (parent_id) REFERENCES goals(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS constraints (
                id TEXT PRIMARY KEY,
                source_goal TEXT NOT NULL,
                domain TEXT NOT NULL,
                type TEXT NOT NULL,
                value TEXT NOT NULL,
                priority INTEGER DEFAULT 1,
                active INTEGER DEFAULT 1,
                FOREIGN KEY (source_goal) REFERENCES goals(id)
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_goals_timeframe ON goals(timeframe)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_goals_parent ON goals(parent_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_constraints_domain ON constraints(domain)
        """)

        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # --- Goal Management ---

    def add_goal(
        self,
        title: str,
        description: str = "",
        timeframe: GoalTimeframe = GoalTimeframe.MEDIUM,
        parent_id: Optional[str] = None,
        domains: List[str] = None,
        constraints: Dict[str, Any] = None
    ) -> Goal:
        goal = Goal(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            timeframe=timeframe,
            status=GoalStatus.ACTIVE,
            parent_id=parent_id,
            domains=domains or [],
            constraints=constraints or {},
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

        conn = self._get_conn()
        conn.execute("""
            INSERT INTO goals (id, title, description, timeframe, status,
                             parent_id, domains, constraints, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            goal.id, goal.title, goal.description, goal.timeframe.value,
            goal.status.value, goal.parent_id, json.dumps(goal.domains),
            json.dumps(goal.constraints), goal.created_at, goal.updated_at
        ))
        conn.commit()
        conn.close()

        # Propagate constraints to affected domains
        if constraints:
            for domain in goal.domains:
                self._propagate_constraints(goal.id, domain, constraints)

        return goal

    def get_goal_hierarchy(self, root_id: Optional[str] = None) -> List[Goal]:
        """Get goal tree starting from root (or all top-level if None)."""
        conn = self._get_conn()

        if root_id:
            rows = conn.execute("""
                WITH RECURSIVE tree AS (
                    SELECT * FROM goals WHERE id = ?
                    UNION ALL
                    SELECT g.* FROM goals g JOIN tree t ON g.parent_id = t.id
                )
                SELECT * FROM tree ORDER BY timeframe, created_at
            """, (root_id,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM goals WHERE parent_id IS NULL
                ORDER BY timeframe, created_at
            """).fetchall()

        conn.close()
        return [self._row_to_goal(r) for r in rows]

    def get_active_constraints(self, domain: str) -> List[Constraint]:
        """Get all active constraints affecting a domain."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT * FROM constraints
            WHERE domain = ? AND active = 1
            ORDER BY priority DESC
        """, (domain,)).fetchall()
        conn.close()

        return [Constraint(
            id=r['id'],
            source_goal=r['source_goal'],
            domain=r['domain'],
            type=r['type'],
            value=json.loads(r['value']),
            priority=r['priority'],
            active=bool(r['active'])
        ) for r in rows]

    def _propagate_constraints(self, goal_id: str, domain: str, constraints: Dict[str, Any]):
        """Propagate constraints from goal to domain."""
        conn = self._get_conn()
        for ctype, value in constraints.items():
            conn.execute("""
                INSERT INTO constraints (id, source_goal, domain, type, value, priority)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (str(uuid.uuid4()), goal_id, domain, ctype, json.dumps(value), 1))
        conn.commit()
        conn.close()

    def _row_to_goal(self, row: sqlite3.Row) -> Goal:
        return Goal(
            id=row['id'],
            title=row['title'],
            description=row['description'] or "",
            timeframe=GoalTimeframe(row['timeframe']),
            status=GoalStatus(row['status']),
            parent_id=row['parent_id'],
            domains=json.loads(row['domains']),
            constraints=json.loads(row['constraints']) if row['constraints'] else {},
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    # --- Module Registration ---

    def register_module(self, name: str, module: CoherenceInterface):
        """Register a domain module."""
        self._modules[name] = module

    def get_cross_domain_context(self, requesting_domain: str) -> Dict[str, Any]:
        """Gather context from all modules for a requesting domain."""
        context = {}
        for name, module in self._modules.items():
            if name != requesting_domain:
                context[name] = module.get_context_for(requesting_domain)
        return context

    # --- Coherence Checking ---

    def check_coherence(self, domain: str, action: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Check if action is coherent with all goals and constraints."""
        issues = []

        # Check domain-specific constraints
        constraints = self.get_active_constraints(domain)
        for c in constraints:
            if not self._constraint_satisfied(c, action):
                issues.append(f"Violates {c.type} constraint from goal")

        # Check cross-domain coherence
        if domain in self._modules:
            valid, reason = self._modules[domain].validate_action(action)
            if not valid:
                issues.append(reason)

        return len(issues) == 0, issues

    def _constraint_satisfied(self, constraint: Constraint, action: Dict[str, Any]) -> bool:
        """Check if action satisfies constraint."""
        ctype = constraint.type
        value = constraint.value

        if ctype == "budget_max" and "cost" in action:
            return action["cost"] <= value
        if ctype == "time_window" and "time" in action:
            return value["start"] <= action["time"] <= value["end"]
        if ctype == "preference" and "option" in action:
            return action["option"] in value.get("allowed", [action["option"]])

        return True  # Unknown constraint types pass by default

    # --- Bisimulation Integration (Phase 12) ---

    def find_similar_goals(self, goal_id: str, threshold: float = 0.3) -> List[Dict[str, Any]]:
        """Find goals similar to given goal using bisimulation state abstraction."""
        try:
            from bisimulation import BisimulationEngine, BisimulationState
        except ImportError:
            return []

        engine = BisimulationEngine()
        conn = self._get_conn()

        # Get target goal
        row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
        if not row:
            conn.close()
            return []

        target = self._row_to_goal(row)

        # Create bisimulation state from goal
        target_state = BisimulationState(
            state_id=f"goal_{target.id[:8]}",
            features={
                "timeframe": target.timeframe.value,
                "domains": len(target.domains),
                "constraints": len(target.constraints),
                "status": target.status.value
            },
            goal_context=target.title,
            action_history=[],
            reward_history=[]
        )

        # Compare with all other goals
        similar = []
        rows = conn.execute("SELECT * FROM goals WHERE id != ?", (goal_id,)).fetchall()
        conn.close()

        for r in rows:
            other = self._row_to_goal(r)
            other_state = BisimulationState(
                state_id=f"goal_{other.id[:8]}",
                features={
                    "timeframe": other.timeframe.value,
                    "domains": len(other.domains),
                    "constraints": len(other.constraints),
                    "status": other.status.value
                },
                goal_context=other.title,
                action_history=[],
                reward_history=[]
            )

            metric = engine.compute_distance(target_state, other_state, target.title)
            if metric.distance < threshold:
                similar.append({
                    "goal_id": other.id,
                    "title": other.title,
                    "distance": metric.distance,
                    "bisimilar": metric.distance < 0.3
                })

        return sorted(similar, key=lambda x: x["distance"])

    def suggest_policy_transfer(self, from_goal_id: str, to_goal_id: str) -> Dict[str, Any]:
        """Check if learned policy can transfer between goals."""
        try:
            from bisimulation import BisimulationEngine
            from gcrl import GoalConditionedLearner
        except ImportError:
            return {"valid": False, "reason": "Modules not available"}

        bisim = BisimulationEngine()
        gcrl = GoalConditionedLearner()

        # Get goals
        conn = self._get_conn()
        from_row = conn.execute("SELECT * FROM goals WHERE id = ?", (from_goal_id,)).fetchone()
        to_row = conn.execute("SELECT * FROM goals WHERE id = ?", (to_goal_id,)).fetchone()
        conn.close()

        if not from_row or not to_row:
            return {"valid": False, "reason": "Goal not found"}

        from_goal = self._row_to_goal(from_row)
        to_goal = self._row_to_goal(to_row)

        # Check bisimulation transfer validity
        transfer = bisim.transfer_policy(
            f"goal_{from_goal.id[:8]}", from_goal.title,
            f"goal_{to_goal.id[:8]}", to_goal.title
        )

        # Get policy if available
        policy = gcrl.policy_for_goal({}, type('Goal', (), {
            'goal_id': to_goal.id,
            'description': to_goal.description,
            'success_criteria': [],
            'goal_type': to_goal.timeframe.value
        })())

        return {
            "valid": transfer.transfer_valid,
            "confidence": transfer.confidence,
            "reasoning": transfer.reasoning,
            "suggested_actions": policy.action_sequence if policy else [],
            "from_goal": from_goal.title,
            "to_goal": to_goal.title
        }

    def get_goal_state_for_bisim(self, goal_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Convert goal + context to bisimulation state representation."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
        conn.close()

        if not row:
            return {}

        goal = self._row_to_goal(row)

        state = {
            "goal_id": goal.id,
            "goal_title": goal.title,
            "timeframe": goal.timeframe.value,
            "status": goal.status.value,
            "domain_count": len(goal.domains),
            "constraint_count": len(goal.constraints),
            "has_parent": goal.parent_id is not None
        }

        if context:
            state.update(context)

        return state


# --- CLI ---

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Goal Coherence CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Add goal
    add_parser = subparsers.add_parser("add", help="Add a goal")
    add_parser.add_argument("title", help="Goal title")
    add_parser.add_argument("--desc", default="", help="Description")
    add_parser.add_argument("--timeframe", choices=["long", "medium", "short", "task"],
                           default="medium")
    add_parser.add_argument("--domains", default="", help="Comma-separated domains")
    add_parser.add_argument("--parent", help="Parent goal ID")

    # List goals
    list_parser = subparsers.add_parser("list", help="List goals")
    list_parser.add_argument("--timeframe", help="Filter by timeframe")

    # Show constraints
    const_parser = subparsers.add_parser("constraints", help="Show constraints")
    const_parser.add_argument("domain", help="Domain to check")

    args = parser.parse_args()
    gcl = GoalCoherenceLayer()

    if args.command == "add":
        domains = [d.strip() for d in args.domains.split(",") if d.strip()]
        goal = gcl.add_goal(
            title=args.title,
            description=args.desc,
            timeframe=GoalTimeframe(args.timeframe),
            domains=domains,
            parent_id=args.parent
        )
        print(f"Created goal: {goal.id[:8]}... | {goal.title}")

    elif args.command == "list":
        goals = gcl.get_goal_hierarchy()
        for g in goals:
            prefix = "  " * (0 if g.parent_id is None else 1)
            print(f"{prefix}[{g.timeframe.value:6}] {g.id[:8]}... | {g.title}")

    elif args.command == "constraints":
        constraints = gcl.get_active_constraints(args.domain)
        for c in constraints:
            print(f"[{c.type}] {c.value} (priority: {c.priority})")

    else:
        parser.print_help()
