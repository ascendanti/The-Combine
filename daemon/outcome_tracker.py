#!/usr/bin/env python3
"""
Outcome Tracker - Foundation for Adaptive Learning

This is the NEAREST NEXT ACTION toward emergent autonomy.
Every other adaptive capability depends on knowing what worked and what failed.

Usage:
    # Record an outcome
    python daemon/outcome_tracker.py record --action "used kraken for TDD" --result success --context "implementing feature"

    # Query success rates
    python daemon/outcome_tracker.py query --action-type "agent:*" --min-count 3

    # Get recommendations
    python daemon/outcome_tracker.py recommend --context "implementing feature"

    # Export patterns
    python daemon/outcome_tracker.py patterns --min-success 0.7
"""

import sqlite3
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import hashlib

DB_PATH = Path(__file__).parent / "outcomes.db"


@dataclass
class Outcome:
    """A recorded outcome from an action."""
    outcome_id: str
    action: str           # What was done (e.g., "agent:kraken", "skill:commit", "model:localai")
    action_type: str      # Category (agent, skill, model, hook, manual)
    context: str          # Situation when action was taken
    context_hash: str     # For finding similar contexts
    result: str           # success, partial, failure
    duration_ms: int      # How long it took
    tokens_used: int      # Token cost (if applicable)
    notes: str            # Additional observations
    timestamp: str


@dataclass
class Pattern:
    """A discovered success pattern."""
    action: str
    success_rate: float
    total_count: int
    avg_duration_ms: float
    contexts: List[str]   # Contexts where this works well


def init_db():
    """Initialize the outcomes database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS outcomes (
        outcome_id TEXT PRIMARY KEY,
        action TEXT NOT NULL,
        action_type TEXT NOT NULL,
        context TEXT,
        context_hash TEXT,
        result TEXT NOT NULL,
        duration_ms INTEGER DEFAULT 0,
        tokens_used INTEGER DEFAULT 0,
        notes TEXT,
        timestamp TEXT NOT NULL
    )''')

    c.execute('''CREATE INDEX IF NOT EXISTS idx_action ON outcomes(action)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_action_type ON outcomes(action_type)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_context_hash ON outcomes(context_hash)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_result ON outcomes(result)''')

    # Patterns table - discovered success patterns
    c.execute('''CREATE TABLE IF NOT EXISTS patterns (
        pattern_id TEXT PRIMARY KEY,
        action TEXT NOT NULL,
        context_pattern TEXT,
        success_rate REAL,
        sample_count INTEGER,
        avg_duration_ms REAL,
        last_updated TEXT,
        metadata TEXT
    )''')

    conn.commit()
    conn.close()


def hash_context(context: str) -> str:
    """Create a hash for context similarity matching."""
    # Simple hash - in production, use embeddings
    normalized = ' '.join(sorted(context.lower().split()))
    return hashlib.md5(normalized.encode()).hexdigest()[:16]


def record_outcome(
    action: str,
    result: str,
    context: str = "",
    duration_ms: int = 0,
    tokens_used: int = 0,
    notes: str = ""
) -> str:
    """Record an outcome from an action."""
    init_db()

    # Determine action type
    if action.startswith("agent:"):
        action_type = "agent"
    elif action.startswith("skill:"):
        action_type = "skill"
    elif action.startswith("model:"):
        action_type = "model"
    elif action.startswith("hook:"):
        action_type = "hook"
    else:
        action_type = "manual"

    outcome = Outcome(
        outcome_id=f"out_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash_context(action)[:8]}",
        action=action,
        action_type=action_type,
        context=context,
        context_hash=hash_context(context),
        result=result,
        duration_ms=duration_ms,
        tokens_used=tokens_used,
        notes=notes,
        timestamp=datetime.now().isoformat()
    )

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''INSERT INTO outcomes
        (outcome_id, action, action_type, context, context_hash, result,
         duration_ms, tokens_used, notes, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (outcome.outcome_id, outcome.action, outcome.action_type, outcome.context,
         outcome.context_hash, outcome.result, outcome.duration_ms, outcome.tokens_used,
         outcome.notes, outcome.timestamp))

    conn.commit()
    conn.close()

    # Update patterns
    update_patterns(action)

    # WIRED 2026-01-28: Update strategy fitness if strategy was used
    _update_strategy_feedback(action, result, context, duration_ms, tokens_used)

    return outcome.outcome_id


def _update_strategy_feedback(action: str, result: str, context: str, duration_ms: int, tokens_used: int):
    """Update strategy fitness based on outcome.

    WIRED: Closes the feedback loop between outcomes and strategy evolution.
    """
    try:
        from strategy_evolution import record_performance, get_strategy, evolve_strategies

        # Check if action contains strategy reference (e.g., "strategy:optimize_queries")
        strategy_name = None
        if action.startswith("strategy:"):
            strategy_name = action.replace("strategy:", "")
        elif "strategy=" in context:
            # Extract from context like "strategy=optimize_queries"
            import re
            match = re.search(r'strategy=(\w+)', context)
            if match:
                strategy_name = match.group(1)

        if strategy_name:
            # Map result to quality score
            quality_map = {"success": 1.0, "partial": 0.5, "failure": 0.0}
            quality = quality_map.get(result, 0.5)

            record_performance(
                strategy_name=strategy_name,
                result=result,
                context=context[:500],
                duration_ms=duration_ms,
                tokens_used=tokens_used,
                quality_score=quality
            )

            # Check if evolution should be triggered (every 10 outcomes)
            from strategy_evolution import DB_PATH as STRATEGY_DB
            import sqlite3
            conn = sqlite3.connect(STRATEGY_DB)
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM performance')
            perf_count = c.fetchone()[0]
            conn.close()

            if perf_count > 0 and perf_count % 10 == 0:
                # Trigger evolution
                evolve_strategies(generation=1, population_size=3)

    except ImportError:
        pass  # strategy_evolution not available
    except Exception:
        pass  # Don't fail outcome recording if strategy update fails


def update_patterns(action: str):
    """Update success patterns after recording an outcome."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Calculate stats for this action
    c.execute('''SELECT
        COUNT(*) as total,
        SUM(CASE WHEN result = 'success' THEN 1 ELSE 0 END) as successes,
        AVG(duration_ms) as avg_duration
        FROM outcomes WHERE action = ?''', (action,))

    row = c.fetchone()
    if row and row[0] > 0:
        total, successes, avg_duration = row
        success_rate = successes / total if total > 0 else 0

        # Get successful contexts
        c.execute('''SELECT DISTINCT context FROM outcomes
            WHERE action = ? AND result = 'success' LIMIT 10''', (action,))
        contexts = [r[0] for r in c.fetchall()]

        pattern_id = f"pat_{hash_context(action)}"

        c.execute('''INSERT OR REPLACE INTO patterns
            (pattern_id, action, context_pattern, success_rate, sample_count,
             avg_duration_ms, last_updated, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (pattern_id, action, json.dumps(contexts), success_rate, total,
             avg_duration or 0, datetime.now().isoformat(), "{}"))

    conn.commit()
    conn.close()


def query_success_rates(
    action_type: Optional[str] = None,
    min_count: int = 3
) -> List[Dict]:
    """Query success rates for actions."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if action_type:
        if action_type.endswith("*"):
            # Wildcard match
            prefix = action_type[:-1]
            c.execute('''SELECT action,
                COUNT(*) as total,
                SUM(CASE WHEN result = 'success' THEN 1 ELSE 0 END) as successes,
                AVG(duration_ms) as avg_duration,
                AVG(tokens_used) as avg_tokens
                FROM outcomes
                WHERE action LIKE ?
                GROUP BY action
                HAVING total >= ?
                ORDER BY (successes * 1.0 / total) DESC''',
                (prefix + "%", min_count))
        else:
            c.execute('''SELECT action,
                COUNT(*) as total,
                SUM(CASE WHEN result = 'success' THEN 1 ELSE 0 END) as successes,
                AVG(duration_ms) as avg_duration,
                AVG(tokens_used) as avg_tokens
                FROM outcomes
                WHERE action_type = ?
                GROUP BY action
                HAVING total >= ?
                ORDER BY (successes * 1.0 / total) DESC''',
                (action_type, min_count))
    else:
        c.execute('''SELECT action,
            COUNT(*) as total,
            SUM(CASE WHEN result = 'success' THEN 1 ELSE 0 END) as successes,
            AVG(duration_ms) as avg_duration,
            AVG(tokens_used) as avg_tokens
            FROM outcomes
            GROUP BY action
            HAVING total >= ?
            ORDER BY (successes * 1.0 / total) DESC''',
            (min_count,))

    results = []
    for row in c.fetchall():
        action, total, successes, avg_duration, avg_tokens = row
        results.append({
            "action": action,
            "success_rate": round(successes / total, 3) if total > 0 else 0,
            "total": total,
            "successes": successes,
            "avg_duration_ms": round(avg_duration or 0, 1),
            "avg_tokens": round(avg_tokens or 0, 1)
        })

    conn.close()
    return results


def recommend_action(context: str, action_type: Optional[str] = None) -> List[Dict]:
    """Recommend best action for a given context."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    context_hash = hash_context(context)

    # Find actions that worked in similar contexts
    query = '''SELECT action,
        COUNT(*) as total,
        SUM(CASE WHEN result = 'success' THEN 1 ELSE 0 END) as successes,
        AVG(duration_ms) as avg_duration
        FROM outcomes
        WHERE context_hash = ?'''

    params = [context_hash]

    if action_type:
        if action_type.endswith("*"):
            query += " AND action LIKE ?"
            params.append(action_type[:-1] + "%")
        else:
            query += " AND action_type = ?"
            params.append(action_type)

    query += " GROUP BY action HAVING total >= 1 ORDER BY (successes * 1.0 / total) DESC LIMIT 5"

    c.execute(query, params)

    results = []
    for row in c.fetchall():
        action, total, successes, avg_duration = row
        results.append({
            "action": action,
            "success_rate": round(successes / total, 3) if total > 0 else 0,
            "sample_count": total,
            "avg_duration_ms": round(avg_duration or 0, 1),
            "confidence": "high" if total >= 5 else "medium" if total >= 3 else "low"
        })

    conn.close()

    # If no context matches, fall back to global success rates
    if not results:
        return query_success_rates(action_type, min_count=2)[:5]

    return results


def get_patterns(min_success_rate: float = 0.7, min_count: int = 3) -> List[Dict]:
    """Get discovered success patterns."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''SELECT action, success_rate, sample_count, avg_duration_ms, context_pattern
        FROM patterns
        WHERE success_rate >= ? AND sample_count >= ?
        ORDER BY success_rate DESC, sample_count DESC''',
        (min_success_rate, min_count))

    patterns = []
    for row in c.fetchall():
        action, success_rate, count, avg_duration, contexts_json = row
        patterns.append({
            "action": action,
            "success_rate": round(success_rate, 3),
            "sample_count": count,
            "avg_duration_ms": round(avg_duration, 1),
            "good_contexts": json.loads(contexts_json) if contexts_json else []
        })

    conn.close()
    return patterns


def get_stats() -> Dict:
    """Get overall outcome statistics."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''SELECT
        COUNT(*) as total,
        SUM(CASE WHEN result = 'success' THEN 1 ELSE 0 END) as successes,
        SUM(CASE WHEN result = 'failure' THEN 1 ELSE 0 END) as failures,
        SUM(CASE WHEN result = 'partial' THEN 1 ELSE 0 END) as partials,
        COUNT(DISTINCT action) as unique_actions,
        SUM(tokens_used) as total_tokens
        FROM outcomes''')

    row = c.fetchone()
    total, successes, failures, partials, unique_actions, total_tokens = row

    stats = {
        "total_outcomes": total or 0,
        "successes": successes or 0,
        "failures": failures or 0,
        "partials": partials or 0,
        "overall_success_rate": round(successes / total, 3) if total else 0,
        "unique_actions": unique_actions or 0,
        "total_tokens": total_tokens or 0
    }

    # Top performing actions
    c.execute('''SELECT action,
        COUNT(*) as total,
        SUM(CASE WHEN result = 'success' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as rate
        FROM outcomes
        GROUP BY action
        HAVING total >= 3
        ORDER BY rate DESC
        LIMIT 5''')

    stats["top_actions"] = [{"action": r[0], "count": r[1], "success_rate": round(r[2], 3)}
                           for r in c.fetchall()]

    conn.close()
    return stats


def main():
    parser = argparse.ArgumentParser(description="Outcome Tracker - Foundation for Adaptive Learning")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Record command
    record_parser = subparsers.add_parser("record", help="Record an outcome")
    record_parser.add_argument("--action", required=True, help="Action taken (e.g., agent:kraken)")
    record_parser.add_argument("--result", required=True, choices=["success", "partial", "failure"])
    record_parser.add_argument("--context", default="", help="Context/situation")
    record_parser.add_argument("--duration", type=int, default=0, help="Duration in ms")
    record_parser.add_argument("--tokens", type=int, default=0, help="Tokens used")
    record_parser.add_argument("--notes", default="", help="Additional notes")

    # Query command
    query_parser = subparsers.add_parser("query", help="Query success rates")
    query_parser.add_argument("--action-type", help="Filter by action type (e.g., agent:*)")
    query_parser.add_argument("--min-count", type=int, default=3, help="Minimum sample count")

    # Recommend command
    rec_parser = subparsers.add_parser("recommend", help="Get recommendations")
    rec_parser.add_argument("--context", required=True, help="Current context")
    rec_parser.add_argument("--action-type", help="Filter by type")

    # Patterns command
    pat_parser = subparsers.add_parser("patterns", help="Show success patterns")
    pat_parser.add_argument("--min-success", type=float, default=0.7, help="Min success rate")
    pat_parser.add_argument("--min-count", type=int, default=3, help="Min sample count")

    # Stats command
    subparsers.add_parser("stats", help="Show overall statistics")

    args = parser.parse_args()

    if args.command == "record":
        outcome_id = record_outcome(
            action=args.action,
            result=args.result,
            context=args.context,
            duration_ms=args.duration,
            tokens_used=args.tokens,
            notes=args.notes
        )
        print(f"Recorded: {outcome_id}")

    elif args.command == "query":
        results = query_success_rates(args.action_type, args.min_count)
        print(json.dumps(results, indent=2))

    elif args.command == "recommend":
        results = recommend_action(args.context, args.action_type)
        print("Recommended actions:")
        for r in results:
            conf = r.get("confidence", "unknown")
            print(f"  {r['action']}: {r['success_rate']*100:.1f}% success ({conf})")

    elif args.command == "patterns":
        patterns = get_patterns(args.min_success, args.min_count)
        print(json.dumps(patterns, indent=2))

    elif args.command == "stats":
        stats = get_stats()
        print(f"Total outcomes: {stats['total_outcomes']}")
        print(f"Overall success rate: {stats['overall_success_rate']*100:.1f}%")
        print(f"Unique actions tracked: {stats['unique_actions']}")
        if stats['top_actions']:
            print("\nTop performing actions:")
            for a in stats['top_actions']:
                print(f"  {a['action']}: {a['success_rate']*100:.1f}% ({a['count']} samples)")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
