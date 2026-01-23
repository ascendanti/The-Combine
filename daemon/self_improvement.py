#!/usr/bin/env python3
"""
Self-Improvement Engine for Phase 10

Uses thinking frameworks from deep-reading-analyst to:
1. Analyze session logs for patterns
2. Apply First Principles to strip assumptions
3. Use Inversion Thinking to identify failure modes
4. Map feedback loops with Systems Thinking
5. Generate improvement suggestions

This enables the daemon to reflect on its own performance
and evolve strategies over time.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Database path
DB_PATH = Path(__file__).parent / "self_improvement.db"


class AnalysisFramework(Enum):
    """Available thinking frameworks"""
    SCQA = "scqa"  # Situation-Complication-Question-Answer
    FIVE_W_TWO_H = "5w2h"  # What, Why, Who, When, Where, How, How much
    CRITICAL = "critical"  # Argument evaluation
    INVERSION = "inversion"  # Risk identification
    MENTAL_MODELS = "mental_models"  # Multi-discipline perspective
    FIRST_PRINCIPLES = "first_principles"  # Strip assumptions
    SYSTEMS = "systems"  # Relationship mapping
    SIX_HATS = "six_hats"  # Structured creativity


class AnalysisDepth(Enum):
    """Analysis depth levels"""
    QUICK = "quick"  # 15 min - SCQA + 5W2H
    STANDARD = "standard"  # 30 min - + Critical + Inversion
    DEEP = "deep"  # 60 min - + Mental Models + First Principles + Systems
    RESEARCH = "research"  # 120 min+ - + Cross-session comparison


@dataclass
class Assumption:
    """A discovered assumption"""
    id: str
    content: str
    source: str  # Where it came from (session_id, strategy, etc.)
    verified: bool
    is_fundamental: bool
    discovered_at: str
    invalidated_at: Optional[str] = None


@dataclass
class FailureMode:
    """A potential failure mode from Inversion Thinking"""
    id: str
    description: str
    trigger_conditions: List[str]
    impact: str  # low, medium, high, critical
    mitigation: str
    observed_count: int
    last_observed: Optional[str] = None


@dataclass
class FeedbackLoop:
    """A feedback loop from Systems Thinking"""
    id: str
    name: str
    loop_type: str  # reinforcing or balancing
    variables: List[str]
    direction: str  # growth, decline, stability
    leverage_point: str
    description: str


@dataclass
class Insight:
    """An insight from self-analysis"""
    id: str
    content: str
    framework_used: str
    confidence: float  # 0.0 - 1.0
    actionable: bool
    action_item: Optional[str]
    discovered_at: str
    applied: bool = False
    outcome: Optional[str] = None


@dataclass
class SessionAnalysis:
    """Analysis of a session's performance"""
    session_id: str
    analyzed_at: str
    depth: str
    assumptions_found: int
    failure_modes_found: int
    feedback_loops_found: int
    insights_generated: int
    summary: str
    recommendations: List[str]


def init_db():
    """Initialize the self-improvement database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assumptions (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            source TEXT NOT NULL,
            verified INTEGER DEFAULT 0,
            is_fundamental INTEGER DEFAULT 0,
            discovered_at TEXT NOT NULL,
            invalidated_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS failure_modes (
            id TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            trigger_conditions TEXT NOT NULL,  -- JSON array
            impact TEXT NOT NULL,
            mitigation TEXT NOT NULL,
            observed_count INTEGER DEFAULT 0,
            last_observed TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback_loops (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            loop_type TEXT NOT NULL,
            variables TEXT NOT NULL,  -- JSON array
            direction TEXT NOT NULL,
            leverage_point TEXT NOT NULL,
            description TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS insights (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            framework_used TEXT NOT NULL,
            confidence REAL NOT NULL,
            actionable INTEGER DEFAULT 0,
            action_item TEXT,
            discovered_at TEXT NOT NULL,
            applied INTEGER DEFAULT 0,
            outcome TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS session_analyses (
            session_id TEXT PRIMARY KEY,
            analyzed_at TEXT NOT NULL,
            depth TEXT NOT NULL,
            assumptions_found INTEGER,
            failure_modes_found INTEGER,
            feedback_loops_found INTEGER,
            insights_generated INTEGER,
            summary TEXT,
            recommendations TEXT  -- JSON array
        )
    """)

    conn.commit()
    conn.close()


class SelfImprovementEngine:
    """
    Engine for self-analysis and improvement using thinking frameworks.

    Key capabilities:
    1. First Principles Analysis - Strip assumptions, find fundamentals
    2. Inversion Thinking - Identify failure modes
    3. Systems Thinking - Map feedback loops and leverage points
    4. Pattern Extraction - Learn from outcomes
    """

    def __init__(self):
        init_db()
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        self.conn.close()

    # ========== FIRST PRINCIPLES ANALYSIS ==========

    def analyze_first_principles(
        self,
        strategy: str,
        context: str,
        source: str = "manual"
    ) -> Dict[str, Any]:
        """
        Apply First Principles thinking to a strategy or approach.

        Steps:
        1. Identify all assumptions
        2. Verify which are fundamental truths
        3. Rebuild understanding from fundamentals
        4. Compare original to rebuilt
        """
        analysis = {
            "strategy": strategy,
            "context": context,
            "assumptions": [],
            "fundamentals": [],
            "rebuilt_understanding": "",
            "differences": [],
            "recommendations": []
        }

        # Step 1: Extract assumptions (heuristic patterns)
        assumption_patterns = [
            "always", "never", "must", "should", "obviously",
            "everyone knows", "it's clear that", "naturally",
            "of course", "traditionally", "the way to"
        ]

        strategy_lower = strategy.lower()
        found_assumptions = []

        for pattern in assumption_patterns:
            if pattern in strategy_lower:
                # Mark as potential assumption
                found_assumptions.append({
                    "trigger": pattern,
                    "context": strategy
                })

        # Step 2: Record assumptions in database
        for i, assumption_data in enumerate(found_assumptions):
            assumption = Assumption(
                id=f"{source}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}",
                content=f"Assumption detected via '{assumption_data['trigger']}'",
                source=source,
                verified=False,
                is_fundamental=False,
                discovered_at=datetime.now().isoformat()
            )
            self._save_assumption(assumption)
            analysis["assumptions"].append(asdict(assumption))

        # Step 3: Generate questions to verify fundamentals
        analysis["verification_questions"] = [
            "Why is this true?",
            "How do I know this is true?",
            "What if the opposite were true?",
            "What must be true for this to work?",
            "If I couldn't do it this way, what's another path?"
        ]

        return analysis

    def _save_assumption(self, assumption: Assumption):
        """Save an assumption to the database"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO assumptions
            (id, content, source, verified, is_fundamental, discovered_at, invalidated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            assumption.id,
            assumption.content,
            assumption.source,
            assumption.verified,
            assumption.is_fundamental,
            assumption.discovered_at,
            assumption.invalidated_at
        ))
        self.conn.commit()

    def get_assumptions(self, verified_only: bool = False) -> List[Dict]:
        """Get all recorded assumptions"""
        cursor = self.conn.cursor()
        if verified_only:
            cursor.execute("SELECT * FROM assumptions WHERE verified = 1")
        else:
            cursor.execute("SELECT * FROM assumptions")

        return [dict(row) for row in cursor.fetchall()]

    # ========== INVERSION THINKING ==========

    def analyze_inversion(
        self,
        goal: str,
        approach: str,
        domain: str = "general"
    ) -> Dict[str, Any]:
        """
        Apply Inversion Thinking - identify failure modes.

        Ask: "How could this fail?" then work backwards.
        """
        analysis = {
            "goal": goal,
            "approach": approach,
            "failure_modes": [],
            "pre_mortem": [],
            "mitigations": []
        }

        # Common failure mode categories
        failure_categories = {
            "assumption_failure": "What if key assumptions are wrong?",
            "resource_failure": "What if resources are insufficient?",
            "timing_failure": "What if timing is off?",
            "dependency_failure": "What if dependencies fail?",
            "scale_failure": "What if it doesn't scale?",
            "edge_case": "What edge cases could break this?",
            "human_error": "What human errors could occur?",
            "external_change": "What external changes could invalidate this?"
        }

        # Generate failure modes for each category
        for category, question in failure_categories.items():
            failure = FailureMode(
                id=f"fm_{domain}_{category}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                description=f"[{category}] {question}",
                trigger_conditions=[],
                impact="medium",  # Default, should be assessed
                mitigation="[To be determined]",
                observed_count=0
            )

            self._save_failure_mode(failure)
            analysis["failure_modes"].append(asdict(failure))

        # Pre-mortem template
        analysis["pre_mortem_template"] = {
            "scenario": f"It is 6 months from now. '{goal}' has completely failed. What happened?",
            "questions": [
                "What warning signs did we ignore?",
                "What risks did we underestimate?",
                "What resources were missing?",
                "What unexpected events occurred?",
                "What did we assume that turned out wrong?"
            ]
        }

        return analysis

    def _save_failure_mode(self, failure_mode: FailureMode):
        """Save a failure mode to the database"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO failure_modes
            (id, description, trigger_conditions, impact, mitigation, observed_count, last_observed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            failure_mode.id,
            failure_mode.description,
            json.dumps(failure_mode.trigger_conditions),
            failure_mode.impact,
            failure_mode.mitigation,
            failure_mode.observed_count,
            failure_mode.last_observed
        ))
        self.conn.commit()

    def record_failure_observation(self, failure_id: str):
        """Record that a failure mode was observed"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE failure_modes
            SET observed_count = observed_count + 1, last_observed = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), failure_id))
        self.conn.commit()

    def get_failure_modes(self, min_observations: int = 0) -> List[Dict]:
        """Get failure modes, optionally filtered by observation count"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM failure_modes WHERE observed_count >= ?",
            (min_observations,)
        )
        rows = cursor.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["trigger_conditions"] = json.loads(d["trigger_conditions"])
            result.append(d)
        return result

    # ========== SYSTEMS THINKING ==========

    def map_feedback_loop(
        self,
        name: str,
        variables: List[str],
        relationships: List[Tuple[str, str, str]],  # (from, to, effect: + or -)
        description: str = ""
    ) -> FeedbackLoop:
        """
        Map a feedback loop in the system.

        Args:
            name: Name of the loop
            variables: Variables in the loop
            relationships: List of (from, to, effect) tuples
            description: Description of the loop

        Returns:
            FeedbackLoop object
        """
        # Determine loop type by counting negative relationships
        negative_count = sum(1 for _, _, effect in relationships if effect == "-")
        loop_type = "balancing" if negative_count % 2 == 1 else "reinforcing"

        # Determine direction
        if loop_type == "reinforcing":
            direction = "growth" if relationships[0][2] == "+" else "decline"
        else:
            direction = "stability"

        # Find leverage point (variable with most connections)
        connection_count = {}
        for from_var, to_var, _ in relationships:
            connection_count[from_var] = connection_count.get(from_var, 0) + 1
            connection_count[to_var] = connection_count.get(to_var, 0) + 1

        leverage_point = max(connection_count, key=connection_count.get)

        loop = FeedbackLoop(
            id=f"loop_{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            name=name,
            loop_type=loop_type,
            variables=variables,
            direction=direction,
            leverage_point=leverage_point,
            description=description
        )

        self._save_feedback_loop(loop)
        return loop

    def _save_feedback_loop(self, loop: FeedbackLoop):
        """Save a feedback loop to the database"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO feedback_loops
            (id, name, loop_type, variables, direction, leverage_point, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            loop.id,
            loop.name,
            loop.loop_type,
            json.dumps(loop.variables),
            loop.direction,
            loop.leverage_point,
            loop.description
        ))
        self.conn.commit()

    def get_feedback_loops(self, loop_type: Optional[str] = None) -> List[Dict]:
        """Get feedback loops, optionally filtered by type"""
        cursor = self.conn.cursor()
        if loop_type:
            cursor.execute("SELECT * FROM feedback_loops WHERE loop_type = ?", (loop_type,))
        else:
            cursor.execute("SELECT * FROM feedback_loops")

        rows = cursor.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["variables"] = json.loads(d["variables"])
            result.append(d)
        return result

    # ========== INSIGHT GENERATION ==========

    def record_insight(
        self,
        content: str,
        framework: AnalysisFramework,
        confidence: float,
        actionable: bool = False,
        action_item: Optional[str] = None
    ) -> Insight:
        """Record an insight discovered through analysis"""
        insight = Insight(
            id=f"insight_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            content=content,
            framework_used=framework.value,
            confidence=confidence,
            actionable=actionable,
            action_item=action_item,
            discovered_at=datetime.now().isoformat()
        )

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO insights
            (id, content, framework_used, confidence, actionable, action_item, discovered_at, applied, outcome)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            insight.id,
            insight.content,
            insight.framework_used,
            insight.confidence,
            insight.actionable,
            insight.action_item,
            insight.discovered_at,
            insight.applied,
            insight.outcome
        ))
        self.conn.commit()

        return insight

    def apply_insight(self, insight_id: str, outcome: str):
        """Record that an insight was applied and its outcome"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE insights SET applied = 1, outcome = ? WHERE id = ?
        """, (outcome, insight_id))
        self.conn.commit()

    def get_insights(
        self,
        framework: Optional[AnalysisFramework] = None,
        actionable_only: bool = False,
        unapplied_only: bool = False
    ) -> List[Dict]:
        """Get insights with optional filters"""
        cursor = self.conn.cursor()
        query = "SELECT * FROM insights WHERE 1=1"
        params = []

        if framework:
            query += " AND framework_used = ?"
            params.append(framework.value)
        if actionable_only:
            query += " AND actionable = 1"
        if unapplied_only:
            query += " AND applied = 0"

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    # ========== SESSION ANALYSIS ==========

    def analyze_session(
        self,
        session_id: str,
        session_log: str,
        depth: AnalysisDepth = AnalysisDepth.STANDARD
    ) -> SessionAnalysis:
        """
        Perform comprehensive analysis of a session log.

        Uses multiple frameworks based on depth level.
        """
        analysis_results = {
            "assumptions": [],
            "failure_modes": [],
            "feedback_loops": [],
            "insights": []
        }

        # Level 1: Quick (SCQA + 5W2H)
        # Extract structure
        analysis_results["scqa"] = self._analyze_scqa(session_log)

        if depth in [AnalysisDepth.STANDARD, AnalysisDepth.DEEP, AnalysisDepth.RESEARCH]:
            # Level 2: Standard (+ Critical + Inversion)
            inv_analysis = self.analyze_inversion(
                goal=f"Session {session_id} objectives",
                approach=session_log[:500],
                domain="session"
            )
            analysis_results["failure_modes"] = inv_analysis["failure_modes"]

        if depth in [AnalysisDepth.DEEP, AnalysisDepth.RESEARCH]:
            # Level 3: Deep (+ Mental Models + First Principles + Systems)
            fp_analysis = self.analyze_first_principles(
                strategy=session_log[:1000],
                context="Session behavior",
                source=session_id
            )
            analysis_results["assumptions"] = fp_analysis["assumptions"]

        # Generate summary
        summary = f"Analyzed session {session_id} at {depth.value} depth."
        recommendations = [
            f"Review {len(analysis_results['assumptions'])} assumptions found",
            f"Address {len(analysis_results['failure_modes'])} potential failure modes"
        ]

        session_analysis = SessionAnalysis(
            session_id=session_id,
            analyzed_at=datetime.now().isoformat(),
            depth=depth.value,
            assumptions_found=len(analysis_results["assumptions"]),
            failure_modes_found=len(analysis_results["failure_modes"]),
            feedback_loops_found=len(analysis_results["feedback_loops"]),
            insights_generated=len(analysis_results["insights"]),
            summary=summary,
            recommendations=recommendations
        )

        # Save analysis
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO session_analyses
            (session_id, analyzed_at, depth, assumptions_found, failure_modes_found,
             feedback_loops_found, insights_generated, summary, recommendations)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_analysis.session_id,
            session_analysis.analyzed_at,
            session_analysis.depth,
            session_analysis.assumptions_found,
            session_analysis.failure_modes_found,
            session_analysis.feedback_loops_found,
            session_analysis.insights_generated,
            session_analysis.summary,
            json.dumps(session_analysis.recommendations)
        ))
        self.conn.commit()

        return session_analysis

    def _analyze_scqa(self, content: str) -> Dict[str, str]:
        """Extract SCQA structure from content"""
        return {
            "situation": "[Extract background context]",
            "complication": "[Extract problem/challenge]",
            "question": "[Extract core question addressed]",
            "answer": "[Extract main solution/conclusion]"
        }

    # ========== IMPROVEMENT SUGGESTIONS ==========

    def generate_improvements(self) -> List[Dict[str, Any]]:
        """
        Generate improvement suggestions based on all analysis.

        Combines insights from:
        - Recurring failure modes
        - Unverified assumptions
        - Feedback loop leverage points
        - Unapplied actionable insights
        """
        improvements = []

        # Check for recurring failures
        recurring_failures = self.get_failure_modes(min_observations=2)
        for failure in recurring_failures:
            improvements.append({
                "type": "recurring_failure",
                "priority": "high",
                "description": f"Recurring failure: {failure['description']}",
                "action": f"Address mitigation: {failure['mitigation']}",
                "observed_count": failure["observed_count"]
            })

        # Check for unverified assumptions
        assumptions = self.get_assumptions(verified_only=False)
        unverified = [a for a in assumptions if not a["verified"]]
        if unverified:
            improvements.append({
                "type": "unverified_assumptions",
                "priority": "medium",
                "description": f"{len(unverified)} assumptions need verification",
                "action": "Review and verify or invalidate each assumption"
            })

        # Check feedback loops for leverage points
        loops = self.get_feedback_loops()
        leverage_points = set(loop["leverage_point"] for loop in loops)
        if leverage_points:
            improvements.append({
                "type": "leverage_points",
                "priority": "high",
                "description": f"Found {len(leverage_points)} leverage points",
                "action": f"Focus interventions on: {', '.join(leverage_points)}"
            })

        # Check unapplied insights
        unapplied = self.get_insights(actionable_only=True, unapplied_only=True)
        for insight in unapplied[:5]:  # Top 5 by recency
            improvements.append({
                "type": "unapplied_insight",
                "priority": "medium",
                "description": insight["content"],
                "action": insight["action_item"]
            })

        return improvements


# ========== CLI Interface ==========

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Self-Improvement Engine")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # First Principles analysis
    fp_parser = subparsers.add_parser("first-principles", help="Analyze with First Principles")
    fp_parser.add_argument("--strategy", required=True, help="Strategy to analyze")
    fp_parser.add_argument("--context", default="", help="Additional context")

    # Inversion analysis
    inv_parser = subparsers.add_parser("inversion", help="Analyze with Inversion Thinking")
    inv_parser.add_argument("--goal", required=True, help="Goal to analyze")
    inv_parser.add_argument("--approach", required=True, help="Current approach")

    # Map feedback loop
    loop_parser = subparsers.add_parser("loop", help="Map a feedback loop")
    loop_parser.add_argument("--name", required=True, help="Loop name")
    loop_parser.add_argument("--variables", nargs="+", required=True, help="Variables in loop")

    # Get improvements
    imp_parser = subparsers.add_parser("improvements", help="Get improvement suggestions")

    # List insights
    list_parser = subparsers.add_parser("insights", help="List insights")
    list_parser.add_argument("--actionable", action="store_true", help="Actionable only")

    args = parser.parse_args()

    engine = SelfImprovementEngine()

    try:
        if args.command == "first-principles":
            result = engine.analyze_first_principles(args.strategy, args.context)
            print(json.dumps(result, indent=2))

        elif args.command == "inversion":
            result = engine.analyze_inversion(args.goal, args.approach)
            print(json.dumps(result, indent=2))

        elif args.command == "loop":
            # Simple demo loop
            loop = engine.map_feedback_loop(
                name=args.name,
                variables=args.variables,
                relationships=[(args.variables[i], args.variables[(i+1) % len(args.variables)], "+")
                              for i in range(len(args.variables))],
                description=f"Loop: {args.name}"
            )
            print(f"Created loop: {loop.name}")
            print(f"  Type: {loop.loop_type}")
            print(f"  Direction: {loop.direction}")
            print(f"  Leverage point: {loop.leverage_point}")

        elif args.command == "improvements":
            improvements = engine.generate_improvements()
            print(f"\n=== Improvement Suggestions ({len(improvements)}) ===\n")
            for imp in improvements:
                print(f"[{imp['priority'].upper()}] {imp['type']}")
                print(f"  {imp['description']}")
                print(f"  Action: {imp['action']}")
                print()

        elif args.command == "insights":
            insights = engine.get_insights(actionable_only=args.actionable if hasattr(args, 'actionable') else False)
            print(f"\n=== Insights ({len(insights)}) ===\n")
            for ins in insights:
                status = "[APPLIED]" if ins["applied"] else "[PENDING]"
                print(f"{status} [{ins['framework_used']}] {ins['content']}")
                if ins["action_item"]:
                    print(f"  Action: {ins['action_item']}")
                print()

        else:
            parser.print_help()

    finally:
        engine.close()


if __name__ == "__main__":
    main()
