#!/usr/bin/env python3
"""Decision Framework - Multi-criteria decision engine with uncertainty.

Implements:
- Multi-criteria decision analysis (MCDA)
- Uncertainty quantification (confidence intervals)
- Preference learning from outcomes
- Expected value with risk adjustment

Usage:
    python decisions.py evaluate "Buy laptop" --criteria "price:0.3,quality:0.4,support:0.3"
    python decisions.py compare "Option A" "Option B" --context "laptop purchase"
"""

import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import math


class ConfidenceLevel(str, Enum):
    VERY_LOW = "very_low"    # <20% - Highly uncertain
    LOW = "low"              # 20-40% - Significant uncertainty
    MEDIUM = "medium"        # 40-60% - Moderate confidence
    HIGH = "high"            # 60-80% - Good confidence
    VERY_HIGH = "very_high"  # >80% - High certainty


@dataclass
class Criterion:
    name: str
    weight: float           # 0-1, sum should = 1
    score: float            # 0-10 rating
    confidence: float       # 0-1 confidence in score
    reasoning: str = ""


@dataclass
class Decision:
    id: str
    title: str
    context: str
    criteria: List[Criterion]
    expected_value: float        # Weighted sum
    risk_adjusted_value: float   # EV adjusted for uncertainty
    confidence_level: ConfidenceLevel
    recommendation: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['criteria'] = [asdict(c) for c in self.criteria]
        d['confidence_level'] = self.confidence_level.value
        return d


@dataclass
class Outcome:
    decision_id: str
    actual_result: str
    satisfaction: float      # 0-10 how satisfied with decision
    lessons: str
    recorded_at: str


class DecisionEngine:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(__file__).parent / "decisions.db"
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                context TEXT,
                criteria TEXT NOT NULL,
                expected_value REAL,
                risk_adjusted_value REAL,
                confidence_level TEXT,
                recommendation TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS outcomes (
                id TEXT PRIMARY KEY,
                decision_id TEXT NOT NULL,
                actual_result TEXT,
                satisfaction REAL,
                lessons TEXT,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY (decision_id) REFERENCES decisions(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                id TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                criterion TEXT NOT NULL,
                learned_weight REAL,
                sample_count INTEGER DEFAULT 0,
                last_updated TEXT
            )
        """)
        conn.commit()
        conn.close()

    def evaluate(
        self,
        title: str,
        criteria: List[Criterion],
        context: str = "",
        risk_aversion: float = 0.5  # 0=risk-neutral, 1=very risk-averse
    ) -> Decision:
        """Evaluate a decision based on weighted criteria."""
        # Normalize weights
        total_weight = sum(c.weight for c in criteria)
        for c in criteria:
            c.weight /= total_weight

        # Calculate expected value (weighted sum)
        expected_value = sum(c.weight * c.score for c in criteria)

        # Calculate uncertainty-adjusted value
        # Lower confidence = higher uncertainty = penalize more if risk-averse
        weighted_confidence = sum(c.weight * c.confidence for c in criteria)
        uncertainty = 1 - weighted_confidence

        # Risk-adjusted value: EV - (risk_aversion * uncertainty * volatility)
        volatility = self._calculate_volatility(criteria)
        risk_penalty = risk_aversion * uncertainty * volatility
        risk_adjusted_value = max(0, expected_value - risk_penalty)

        # Determine confidence level
        confidence_level = self._map_confidence(weighted_confidence)

        # Generate recommendation
        recommendation = self._generate_recommendation(
            expected_value, risk_adjusted_value, confidence_level, criteria
        )

        decision = Decision(
            id=str(uuid.uuid4()),
            title=title,
            context=context,
            criteria=criteria,
            expected_value=round(expected_value, 2),
            risk_adjusted_value=round(risk_adjusted_value, 2),
            confidence_level=confidence_level,
            recommendation=recommendation,
            created_at=datetime.now().isoformat()
        )

        self._save_decision(decision)
        return decision

    def compare(
        self,
        options: List[Tuple[str, List[Criterion]]],
        context: str = ""
    ) -> List[Decision]:
        """Compare multiple options and rank them."""
        decisions = []
        for title, criteria in options:
            decision = self.evaluate(title, criteria, context)
            decisions.append(decision)

        # Sort by risk-adjusted value
        decisions.sort(key=lambda d: d.risk_adjusted_value, reverse=True)
        return decisions

    def record_outcome(
        self,
        decision_id: str,
        actual_result: str,
        satisfaction: float,
        lessons: str = ""
    ) -> None:
        """Record outcome for learning."""
        outcome = Outcome(
            decision_id=decision_id,
            actual_result=actual_result,
            satisfaction=satisfaction,
            lessons=lessons,
            recorded_at=datetime.now().isoformat()
        )

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO outcomes (id, decision_id, actual_result, satisfaction, lessons, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), outcome.decision_id, outcome.actual_result,
              outcome.satisfaction, outcome.lessons, outcome.recorded_at))
        conn.commit()
        conn.close()

        # Update learned preferences
        self._update_preferences(decision_id, satisfaction)

    def get_learned_weights(self, domain: str) -> Dict[str, float]:
        """Get learned criterion weights for a domain."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT criterion, learned_weight FROM preferences
            WHERE domain = ? AND sample_count >= 3
        """, (domain,)).fetchall()
        conn.close()
        return {r['criterion']: r['learned_weight'] for r in rows}

    def _calculate_volatility(self, criteria: List[Criterion]) -> float:
        """Calculate score volatility (variance indicator)."""
        if len(criteria) < 2:
            return 1.0
        scores = [c.score for c in criteria]
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        return math.sqrt(variance)

    def _map_confidence(self, confidence: float) -> ConfidenceLevel:
        if confidence < 0.2:
            return ConfidenceLevel.VERY_LOW
        elif confidence < 0.4:
            return ConfidenceLevel.LOW
        elif confidence < 0.6:
            return ConfidenceLevel.MEDIUM
        elif confidence < 0.8:
            return ConfidenceLevel.HIGH
        else:
            return ConfidenceLevel.VERY_HIGH

    def _generate_recommendation(
        self,
        ev: float,
        rav: float,
        confidence: ConfidenceLevel,
        criteria: List[Criterion]
    ) -> str:
        # Find strongest and weakest criteria
        sorted_criteria = sorted(criteria, key=lambda c: c.score, reverse=True)
        strongest = sorted_criteria[0].name if sorted_criteria else "N/A"
        weakest = sorted_criteria[-1].name if sorted_criteria else "N/A"

        if confidence in [ConfidenceLevel.VERY_LOW, ConfidenceLevel.LOW]:
            return f"Gather more information. High uncertainty on key criteria. Strongest: {strongest}."
        elif ev < 5:
            return f"Not recommended. Low expected value ({ev}/10). Weakest: {weakest}."
        elif rav < ev * 0.7:
            return f"Proceed with caution. Significant risk adjustment. Consider {weakest}."
        elif ev >= 7:
            return f"Recommended. Strong expected value ({ev}/10). Leverage: {strongest}."
        else:
            return f"Acceptable option. Moderate value ({ev}/10)."

    def _save_decision(self, decision: Decision):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO decisions (id, title, context, criteria, expected_value,
                                  risk_adjusted_value, confidence_level, recommendation, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (decision.id, decision.title, decision.context,
              json.dumps([asdict(c) for c in decision.criteria]),
              decision.expected_value, decision.risk_adjusted_value,
              decision.confidence_level.value, decision.recommendation,
              decision.created_at))
        conn.commit()
        conn.close()

    def _update_preferences(self, decision_id: str, satisfaction: float):
        """Update learned preferences based on outcome."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # Get decision criteria
        row = conn.execute("SELECT criteria, context FROM decisions WHERE id = ?",
                          (decision_id,)).fetchone()
        if not row:
            conn.close()
            return

        criteria = json.loads(row['criteria'])
        domain = row['context'] or "general"

        # Adjust weights based on satisfaction
        # High satisfaction = criteria weights were good
        # Low satisfaction = need to adjust weights
        satisfaction_factor = (satisfaction - 5) / 5  # -1 to 1

        for c in criteria:
            name = c['name']
            weight = c['weight']

            # Get or create preference
            pref = conn.execute("""
                SELECT * FROM preferences WHERE domain = ? AND criterion = ?
            """, (domain, name)).fetchone()

            if pref:
                # Running average update
                count = pref['sample_count']
                old_weight = pref['learned_weight']
                new_weight = (old_weight * count + weight * (1 + satisfaction_factor * 0.1)) / (count + 1)

                conn.execute("""
                    UPDATE preferences SET learned_weight = ?, sample_count = ?, last_updated = ?
                    WHERE domain = ? AND criterion = ?
                """, (new_weight, count + 1, datetime.now().isoformat(), domain, name))
            else:
                conn.execute("""
                    INSERT INTO preferences (id, domain, criterion, learned_weight, sample_count, last_updated)
                    VALUES (?, ?, ?, ?, 1, ?)
                """, (str(uuid.uuid4()), domain, name, weight, datetime.now().isoformat()))

        conn.commit()
        conn.close()


# --- CLI ---

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Decision Engine CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Evaluate
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate a decision")
    eval_parser.add_argument("title", help="Decision title")
    eval_parser.add_argument("--criteria", required=True,
                            help="Criteria as name:weight:score:confidence,...")
    eval_parser.add_argument("--context", default="", help="Decision context")
    eval_parser.add_argument("--risk", type=float, default=0.5,
                            help="Risk aversion (0-1)")

    # Compare
    cmp_parser = subparsers.add_parser("compare", help="Compare options")
    cmp_parser.add_argument("options", nargs="+", help="Options as title|criteria")

    # Record outcome
    out_parser = subparsers.add_parser("outcome", help="Record decision outcome")
    out_parser.add_argument("decision_id", help="Decision ID")
    out_parser.add_argument("--satisfaction", type=float, required=True,
                           help="Satisfaction 0-10")
    out_parser.add_argument("--result", default="", help="What happened")
    out_parser.add_argument("--lessons", default="", help="What was learned")

    # Get preferences
    pref_parser = subparsers.add_parser("preferences", help="Show learned preferences")
    pref_parser.add_argument("domain", help="Domain to check")

    args = parser.parse_args()
    engine = DecisionEngine()

    if args.command == "evaluate":
        # Parse criteria: "price:0.3:7:0.8,quality:0.4:8:0.9"
        criteria = []
        for part in args.criteria.split(","):
            fields = part.strip().split(":")
            if len(fields) >= 3:
                name = fields[0]
                weight = float(fields[1])
                score = float(fields[2])
                confidence = float(fields[3]) if len(fields) > 3 else 0.7
                criteria.append(Criterion(name, weight, score, confidence))

        decision = engine.evaluate(args.title, criteria, args.context, args.risk)
        print(f"Decision: {decision.title}")
        print(f"Expected Value: {decision.expected_value}/10")
        print(f"Risk-Adjusted: {decision.risk_adjusted_value}/10")
        print(f"Confidence: {decision.confidence_level.value}")
        print(f"Recommendation: {decision.recommendation}")
        print(f"ID: {decision.id[:8]}...")

    elif args.command == "compare":
        options = []
        for opt in args.options:
            title, crit_str = opt.split("|")
            criteria = []
            for part in crit_str.split(","):
                fields = part.strip().split(":")
                if len(fields) >= 3:
                    criteria.append(Criterion(
                        fields[0], float(fields[1]), float(fields[2]),
                        float(fields[3]) if len(fields) > 3 else 0.7
                    ))
            options.append((title.strip(), criteria))

        decisions = engine.compare(options)
        print("Ranking:")
        for i, d in enumerate(decisions, 1):
            print(f"{i}. {d.title} (RAV: {d.risk_adjusted_value}/10)")

    elif args.command == "outcome":
        engine.record_outcome(args.decision_id, args.result, args.satisfaction, args.lessons)
        print("Outcome recorded. Preferences updated.")

    elif args.command == "preferences":
        prefs = engine.get_learned_weights(args.domain)
        if prefs:
            print(f"Learned weights for {args.domain}:")
            for criterion, weight in sorted(prefs.items(), key=lambda x: -x[1]):
                print(f"  {criterion}: {weight:.3f}")
        else:
            print(f"No learned preferences for {args.domain} yet")

    else:
        parser.print_help()
