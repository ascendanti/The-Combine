#!/usr/bin/env python3
"""Meta-Cognition Module - Self-awareness and capability assessment.

Implements:
- Confidence calibration (am I over/under-confident?)
- Knowledge gap detection (what don't I know?)
- Capability boundaries (what can/can't I do?)
- Performance tracking (how well am I doing?)

Usage:
    python metacognition.py calibrate --domain "coding"
    python metacognition.py gaps --context "financial planning"
    python metacognition.py performance --period 30
"""

import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class CapabilityLevel(str, Enum):
    NONE = "none"           # Cannot do this
    BASIC = "basic"         # Can do with significant help
    INTERMEDIATE = "intermediate"  # Can do with some guidance
    ADVANCED = "advanced"   # Can do independently
    EXPERT = "expert"       # Can teach others


@dataclass
class PredictionRecord:
    """Record of a prediction for calibration."""
    id: str
    domain: str
    prediction: str         # What was predicted
    confidence: float       # 0-1 stated confidence
    actual_outcome: Optional[str]  # What actually happened
    was_correct: Optional[bool]    # Did prediction match reality?
    created_at: str
    resolved_at: Optional[str]


@dataclass
class KnowledgeGap:
    """Identified gap in knowledge."""
    id: str
    domain: str
    topic: str
    description: str
    importance: float       # 0-1 how important to fill
    identified_at: str
    filled: bool = False


@dataclass
class CapabilityAssessment:
    """Assessment of capability in an area."""
    id: str
    capability: str
    level: CapabilityLevel
    evidence: str           # Why this assessment
    limitations: List[str]  # Known limitations
    assessed_at: str


@dataclass
class PerformanceMetric:
    """Tracked performance metric."""
    id: str
    name: str
    value: float
    target: Optional[float]
    domain: str
    recorded_at: str


class MetaCognitionEngine:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(__file__).parent / "metacognition.db"
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                prediction TEXT NOT NULL,
                confidence REAL NOT NULL,
                actual_outcome TEXT,
                was_correct INTEGER,
                created_at TEXT NOT NULL,
                resolved_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_gaps (
                id TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                topic TEXT NOT NULL,
                description TEXT,
                importance REAL DEFAULT 0.5,
                identified_at TEXT NOT NULL,
                filled INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS capabilities (
                id TEXT PRIMARY KEY,
                capability TEXT NOT NULL UNIQUE,
                level TEXT NOT NULL,
                evidence TEXT,
                limitations TEXT,
                assessed_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                value REAL NOT NULL,
                target REAL,
                domain TEXT,
                recorded_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    # --- Confidence Calibration ---

    def record_prediction(
        self,
        domain: str,
        prediction: str,
        confidence: float
    ) -> str:
        """Record a prediction with confidence for later calibration."""
        pred_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO predictions (id, domain, prediction, confidence, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (pred_id, domain, prediction, confidence, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return pred_id

    def resolve_prediction(
        self,
        prediction_id: str,
        actual_outcome: str,
        was_correct: bool
    ):
        """Resolve a prediction with actual outcome."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE predictions
            SET actual_outcome = ?, was_correct = ?, resolved_at = ?
            WHERE id = ?
        """, (actual_outcome, int(was_correct), datetime.now().isoformat(), prediction_id))
        conn.commit()
        conn.close()

    def get_calibration(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """Calculate calibration metrics for predictions."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        query = "SELECT * FROM predictions WHERE was_correct IS NOT NULL"
        if domain:
            query += f" AND domain = '{domain}'"

        rows = conn.execute(query).fetchall()
        conn.close()

        if not rows:
            return {"error": "No resolved predictions to analyze"}

        # Group by confidence buckets
        buckets = {i/10: {"count": 0, "correct": 0} for i in range(11)}

        for r in rows:
            bucket = round(r['confidence'], 1)
            bucket = min(1.0, max(0.0, bucket))
            buckets[bucket]["count"] += 1
            if r['was_correct']:
                buckets[bucket]["correct"] += 1

        # Calculate calibration
        calibration = {}
        for conf, data in buckets.items():
            if data["count"] > 0:
                actual_accuracy = data["correct"] / data["count"]
                calibration[conf] = {
                    "expected": conf,
                    "actual": actual_accuracy,
                    "count": data["count"],
                    "calibration_error": actual_accuracy - conf
                }

        # Overall metrics
        total = len(rows)
        correct = sum(1 for r in rows if r['was_correct'])
        avg_confidence = sum(r['confidence'] for r in rows) / total
        actual_accuracy = correct / total

        return {
            "total_predictions": total,
            "overall_accuracy": round(actual_accuracy, 3),
            "average_confidence": round(avg_confidence, 3),
            "calibration_error": round(actual_accuracy - avg_confidence, 3),
            "overconfident": avg_confidence > actual_accuracy + 0.1,
            "underconfident": avg_confidence < actual_accuracy - 0.1,
            "bucket_analysis": calibration
        }

    # --- Knowledge Gaps ---

    def identify_gap(
        self,
        domain: str,
        topic: str,
        description: str = "",
        importance: float = 0.5
    ) -> str:
        """Identify a knowledge gap."""
        gap_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO knowledge_gaps (id, domain, topic, description, importance, identified_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (gap_id, domain, topic, description, importance, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return gap_id

    def fill_gap(self, gap_id: str):
        """Mark a knowledge gap as filled."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("UPDATE knowledge_gaps SET filled = 1 WHERE id = ?", (gap_id,))
        conn.commit()
        conn.close()

    def get_gaps(self, domain: Optional[str] = None) -> List[KnowledgeGap]:
        """Get unfilled knowledge gaps."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        query = "SELECT * FROM knowledge_gaps WHERE filled = 0"
        if domain:
            query += f" AND domain = '{domain}'"
        query += " ORDER BY importance DESC"

        rows = conn.execute(query).fetchall()
        conn.close()

        return [KnowledgeGap(
            id=r['id'], domain=r['domain'], topic=r['topic'],
            description=r['description'] or "", importance=r['importance'],
            identified_at=r['identified_at'], filled=bool(r['filled'])
        ) for r in rows]

    # --- Capability Assessment ---

    def assess_capability(
        self,
        capability: str,
        level: CapabilityLevel,
        evidence: str = "",
        limitations: List[str] = None
    ):
        """Record or update capability assessment."""
        conn = sqlite3.connect(self.db_path)

        # Check if exists
        existing = conn.execute(
            "SELECT id FROM capabilities WHERE capability = ?",
            (capability,)
        ).fetchone()

        limitations_json = json.dumps(limitations or [])
        now = datetime.now().isoformat()

        if existing:
            conn.execute("""
                UPDATE capabilities
                SET level = ?, evidence = ?, limitations = ?, assessed_at = ?
                WHERE capability = ?
            """, (level.value, evidence, limitations_json, now, capability))
        else:
            conn.execute("""
                INSERT INTO capabilities (id, capability, level, evidence, limitations, assessed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (str(uuid.uuid4()), capability, level.value, evidence, limitations_json, now))

        conn.commit()
        conn.close()

    def get_capabilities(self) -> List[CapabilityAssessment]:
        """Get all capability assessments."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM capabilities ORDER BY level DESC, capability"
        ).fetchall()
        conn.close()

        return [CapabilityAssessment(
            id=r['id'], capability=r['capability'],
            level=CapabilityLevel(r['level']),
            evidence=r['evidence'] or "",
            limitations=json.loads(r['limitations']) if r['limitations'] else [],
            assessed_at=r['assessed_at']
        ) for r in rows]

    def can_do(self, capability: str, required_level: CapabilityLevel = CapabilityLevel.BASIC) -> Tuple[bool, str]:
        """Check if a capability meets required level."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM capabilities WHERE capability = ?",
            (capability,)
        ).fetchone()
        conn.close()

        if not row:
            return False, f"Unknown capability: {capability}"

        level_order = [CapabilityLevel.NONE, CapabilityLevel.BASIC,
                       CapabilityLevel.INTERMEDIATE, CapabilityLevel.ADVANCED,
                       CapabilityLevel.EXPERT]

        current = CapabilityLevel(row['level'])
        current_idx = level_order.index(current)
        required_idx = level_order.index(required_level)

        if current_idx >= required_idx:
            return True, f"Capability at {current.value} level"
        else:
            limitations = json.loads(row['limitations']) if row['limitations'] else []
            return False, f"Only at {current.value} level. Limitations: {', '.join(limitations)}"

    # --- Performance Metrics ---

    def record_metric(
        self,
        name: str,
        value: float,
        target: Optional[float] = None,
        domain: str = "general"
    ):
        """Record a performance metric."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO metrics (id, name, value, target, domain, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), name, value, target, domain, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def get_performance(self, period_days: int = 30) -> Dict[str, Any]:
        """Get performance summary over period."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        cutoff = (datetime.now() - timedelta(days=period_days)).isoformat()
        rows = conn.execute("""
            SELECT * FROM metrics WHERE recorded_at >= ?
            ORDER BY name, recorded_at
        """, (cutoff,)).fetchall()
        conn.close()

        if not rows:
            return {"error": "No metrics in period"}

        # Group by metric name
        by_name = {}
        for r in rows:
            name = r['name']
            if name not in by_name:
                by_name[name] = {"values": [], "targets": []}
            by_name[name]["values"].append(r['value'])
            if r['target']:
                by_name[name]["targets"].append(r['target'])

        # Calculate stats
        summary = {}
        for name, data in by_name.items():
            values = data["values"]
            summary[name] = {
                "count": len(values),
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "latest": values[-1],
                "trend": "up" if len(values) > 1 and values[-1] > values[0] else
                        "down" if len(values) > 1 and values[-1] < values[0] else "stable"
            }
            if data["targets"]:
                target = data["targets"][-1]
                summary[name]["target"] = target
                summary[name]["on_target"] = values[-1] >= target

        return {
            "period_days": period_days,
            "metrics": summary
        }


# --- CLI ---

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Meta-Cognition CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Calibration
    cal_parser = subparsers.add_parser("calibrate", help="Check confidence calibration")
    cal_parser.add_argument("--domain", help="Filter by domain")

    # Knowledge gaps
    gap_parser = subparsers.add_parser("gaps", help="View knowledge gaps")
    gap_parser.add_argument("--domain", help="Filter by domain")
    gap_parser.add_argument("--add", help="Add new gap as topic")
    gap_parser.add_argument("--importance", type=float, default=0.5)

    # Capabilities
    cap_parser = subparsers.add_parser("capabilities", help="View capabilities")
    cap_parser.add_argument("--assess", help="Assess capability")
    cap_parser.add_argument("--level", choices=["none", "basic", "intermediate", "advanced", "expert"])
    cap_parser.add_argument("--check", help="Check if can do")

    # Performance
    perf_parser = subparsers.add_parser("performance", help="View performance")
    perf_parser.add_argument("--period", type=int, default=30, help="Days to analyze")

    args = parser.parse_args()
    engine = MetaCognitionEngine()

    if args.command == "calibrate":
        result = engine.get_calibration(args.domain)
        if "error" in result:
            print(result["error"])
        else:
            print(f"Calibration Analysis ({result['total_predictions']} predictions)")
            print(f"  Overall accuracy: {result['overall_accuracy']:.1%}")
            print(f"  Average confidence: {result['average_confidence']:.1%}")
            print(f"  Calibration error: {result['calibration_error']:+.1%}")
            if result['overconfident']:
                print("  Warning: Overconfident (reduce stated confidence)")
            elif result['underconfident']:
                print("  Note: Underconfident (can trust yourself more)")

    elif args.command == "gaps":
        if args.add:
            gap_id = engine.identify_gap(
                args.domain or "general",
                args.add,
                importance=args.importance
            )
            print(f"Gap identified: {gap_id[:8]}...")
        else:
            gaps = engine.get_gaps(args.domain)
            if gaps:
                print("Knowledge Gaps:")
                for g in gaps:
                    print(f"  [{g.importance:.1f}] {g.topic} ({g.domain})")
            else:
                print("No knowledge gaps identified")

    elif args.command == "capabilities":
        if args.assess and args.level:
            engine.assess_capability(args.assess, CapabilityLevel(args.level))
            print(f"Assessed: {args.assess} = {args.level}")
        elif args.check:
            can, reason = engine.can_do(args.check)
            print(f"Can do '{args.check}': {can}")
            print(f"  {reason}")
        else:
            caps = engine.get_capabilities()
            if caps:
                print("Capabilities:")
                for c in caps:
                    print(f"  [{c.level.value:12}] {c.capability}")
            else:
                print("No capabilities assessed")

    elif args.command == "performance":
        result = engine.get_performance(args.period)
        if "error" in result:
            print(result["error"])
        else:
            print(f"Performance ({result['period_days']} days)")
            for name, stats in result['metrics'].items():
                trend = "^" if stats['trend'] == "up" else "v" if stats['trend'] == "down" else "="
                print(f"  {name}: {stats['latest']:.2f} ({trend}) [n={stats['count']}]")

    else:
        parser.print_help()
