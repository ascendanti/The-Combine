#!/usr/bin/env python3
"""
Emergent Behaviors Module - Phase 10.3

Implements:
1. Proactive Task Generation - Generate tasks from pattern analysis
2. Autonomous Goal Refinement - Evolve goals based on outcomes
3. Self-Directed Learning - Identify and fill capability gaps

Based on:
- Systems Thinking framework (feedback loops, leverage points)
- Continual Learning research (knowledge retention, transfer)
- Bounded Rationality (satisficing under constraints)
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict

# Database paths
DB_PATH = Path(__file__).parent / "emergent.db"
COHERENCE_DB = Path(__file__).parent / "coherence.db"
DECISIONS_DB = Path(__file__).parent / "decisions.db"
MEMORY_DB = Path(__file__).parent / "memory.db"
TASKS_DB = Path(__file__).parent / "tasks.db"

# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class Pattern:
    """Detected pattern from session analysis."""
    pattern_id: str
    pattern_type: str  # recurring_failure, success_factor, bottleneck, opportunity
    description: str
    frequency: int
    confidence: float
    first_seen: str
    last_seen: str
    suggested_action: Optional[str] = None

@dataclass
class GeneratedTask:
    """Task generated from pattern analysis."""
    task_id: str
    source_pattern: str
    title: str
    description: str
    priority: str  # low, medium, high, urgent
    category: str  # improvement, research, maintenance, exploration
    estimated_value: float  # expected benefit
    created_at: str

@dataclass
class GoalRefinement:
    """Proposed refinement to a goal."""
    goal_id: str
    refinement_type: str  # increase_ambition, decompose, drop, pivot
    reason: str
    new_target: Optional[str] = None
    confidence: float = 0.5

@dataclass
class LearningTarget:
    """Identified capability gap to address."""
    target_id: str
    capability: str
    current_level: float  # 0-1
    target_level: float
    importance: float  # how much this matters
    learning_resources: List[str]
    created_at: str

# ============================================================================
# Database
# ============================================================================

def init_db() -> sqlite3.Connection:
    """Initialize emergent behaviors database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Patterns table
    c.execute('''CREATE TABLE IF NOT EXISTS patterns (
        pattern_id TEXT PRIMARY KEY,
        pattern_type TEXT,
        description TEXT,
        frequency INTEGER DEFAULT 1,
        confidence REAL,
        first_seen TEXT,
        last_seen TEXT,
        suggested_action TEXT
    )''')

    # Generated tasks table
    c.execute('''CREATE TABLE IF NOT EXISTS generated_tasks (
        task_id TEXT PRIMARY KEY,
        source_pattern TEXT,
        title TEXT,
        description TEXT,
        priority TEXT,
        category TEXT,
        estimated_value REAL,
        created_at TEXT,
        status TEXT DEFAULT 'pending',
        completed_at TEXT
    )''')

    # Goal refinements table
    c.execute('''CREATE TABLE IF NOT EXISTS goal_refinements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        goal_id TEXT,
        refinement_type TEXT,
        reason TEXT,
        new_target TEXT,
        confidence REAL,
        proposed_at TEXT,
        status TEXT DEFAULT 'pending',
        applied_at TEXT
    )''')

    # Learning targets table
    c.execute('''CREATE TABLE IF NOT EXISTS learning_targets (
        target_id TEXT PRIMARY KEY,
        capability TEXT,
        current_level REAL,
        target_level REAL,
        importance REAL,
        learning_resources TEXT,
        created_at TEXT,
        status TEXT DEFAULT 'active',
        completed_at TEXT
    )''')

    conn.commit()
    return conn

# ============================================================================
# Pattern Detection
# ============================================================================

def detect_patterns(lookback_days: int = 7) -> List[Pattern]:
    """
    Analyze recent activity to detect patterns.

    Patterns detected:
    - Recurring failures (same error 2+ times)
    - Success factors (what preceded successful outcomes)
    - Bottlenecks (operations that slow things down)
    - Opportunities (underutilized capabilities)
    """
    patterns = []
    cutoff = (datetime.now() - timedelta(days=lookback_days)).isoformat()

    # Check decisions database for outcome patterns
    if DECISIONS_DB.exists():
        conn = sqlite3.connect(DECISIONS_DB)
        c = conn.cursor()

        # Recurring failures
        try:
            c.execute("""
                SELECT decision_id, COUNT(*) as count, AVG(satisfaction) as avg_sat
                FROM outcomes
                WHERE recorded_at > ?
                GROUP BY decision_id
                HAVING COUNT(*) >= 2 AND AVG(satisfaction) < 0.4
            """, (cutoff,))
        except sqlite3.OperationalError:
            c.execute("SELECT 1 WHERE 0")  # Empty result

        for row in c.fetchall():
            patterns.append(Pattern(
                pattern_id=f"fail_{hash(row[0]) % 10000}",
                pattern_type="recurring_failure",
                description=f"Low satisfaction ({row[2]:.2f}) on: {row[0]}",
                frequency=row[1],
                confidence=0.7,
                first_seen=cutoff,
                last_seen=datetime.now().isoformat(),
                suggested_action=f"Investigate and improve {row[0]} handling"
            ))

        # Success factors
        try:
            c.execute("""
                SELECT decision_id, COUNT(*) as count, AVG(satisfaction) as avg_sat
                FROM outcomes
                WHERE recorded_at > ? AND satisfaction > 0.8
                GROUP BY decision_id
                HAVING COUNT(*) >= 2
            """, (cutoff,))
        except sqlite3.OperationalError:
            c.execute("SELECT 1 WHERE 0")  # Empty result

        for row in c.fetchall():
            patterns.append(Pattern(
                pattern_id=f"success_{hash(row[0]) % 10000}",
                pattern_type="success_factor",
                description=f"High satisfaction ({row[2]:.2f}) on: {row[0]}",
                frequency=row[1],
                confidence=0.8,
                first_seen=cutoff,
                last_seen=datetime.now().isoformat(),
                suggested_action=f"Replicate {row[0]} approach elsewhere"
            ))

        conn.close()

    # Check tasks database for bottlenecks
    if TASKS_DB.exists():
        conn = sqlite3.connect(TASKS_DB)
        c = conn.cursor()

        # Long-running tasks (bottlenecks)
        try:
            c.execute("""
                SELECT description,
                       julianday(completed_at) - julianday(created_at) as duration
                FROM tasks
                WHERE completed_at IS NOT NULL
                AND julianday(completed_at) - julianday(created_at) > 0.5
                ORDER BY duration DESC
                LIMIT 5
            """)

            for row in c.fetchall():
                if row[0]:
                    patterns.append(Pattern(
                        pattern_id=f"bottleneck_{hash(row[0]) % 10000}",
                        pattern_type="bottleneck",
                        description=f"Slow task ({row[1]:.1f} days): {row[0][:50]}",
                        frequency=1,
                        confidence=0.6,
                        first_seen=cutoff,
                        last_seen=datetime.now().isoformat(),
                        suggested_action="Optimize or parallelize this task type"
                    ))
        except sqlite3.OperationalError:
            pass  # Table structure different

        conn.close()

    return patterns


def store_pattern(pattern: Pattern):
    """Store or update a pattern in the database."""
    conn = init_db()
    c = conn.cursor()

    c.execute("""
        INSERT INTO patterns (pattern_id, pattern_type, description, frequency,
                              confidence, first_seen, last_seen, suggested_action)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(pattern_id) DO UPDATE SET
            frequency = frequency + 1,
            last_seen = excluded.last_seen,
            confidence = (confidence + excluded.confidence) / 2
    """, (pattern.pattern_id, pattern.pattern_type, pattern.description,
          pattern.frequency, pattern.confidence, pattern.first_seen,
          pattern.last_seen, pattern.suggested_action))

    conn.commit()
    conn.close()

# ============================================================================
# Proactive Task Generation
# ============================================================================

def generate_tasks_from_patterns(patterns: List[Pattern]) -> List[GeneratedTask]:
    """
    Generate actionable tasks from detected patterns.

    Task categories:
    - improvement: Fix recurring failures
    - research: Investigate unknowns
    - maintenance: Prevent degradation
    - exploration: Try new approaches
    """
    tasks = []
    now = datetime.now().isoformat()

    for pattern in patterns:
        if pattern.pattern_type == "recurring_failure":
            tasks.append(GeneratedTask(
                task_id=f"task_{pattern.pattern_id}",
                source_pattern=pattern.pattern_id,
                title=f"Fix: {pattern.description[:50]}",
                description=f"""
Recurring failure detected (frequency: {pattern.frequency}).

Pattern: {pattern.description}

Suggested action: {pattern.suggested_action}

Steps:
1. Analyze recent failures matching this pattern
2. Identify root cause
3. Implement fix
4. Add test/monitoring to prevent recurrence
                """.strip(),
                priority="high" if pattern.frequency >= 3 else "medium",
                category="improvement",
                estimated_value=pattern.confidence * pattern.frequency * 0.3,
                created_at=now
            ))

        elif pattern.pattern_type == "success_factor":
            tasks.append(GeneratedTask(
                task_id=f"task_{pattern.pattern_id}",
                source_pattern=pattern.pattern_id,
                title=f"Replicate: {pattern.description[:50]}",
                description=f"""
Success factor identified (frequency: {pattern.frequency}).

Pattern: {pattern.description}

Suggested action: {pattern.suggested_action}

Steps:
1. Document the successful approach
2. Identify other areas where it could apply
3. Create template/automation for reuse
                """.strip(),
                priority="medium",
                category="improvement",
                estimated_value=pattern.confidence * 0.5,
                created_at=now
            ))

        elif pattern.pattern_type == "bottleneck":
            tasks.append(GeneratedTask(
                task_id=f"task_{pattern.pattern_id}",
                source_pattern=pattern.pattern_id,
                title=f"Optimize: {pattern.description[:50]}",
                description=f"""
Bottleneck detected.

Pattern: {pattern.description}

Steps:
1. Profile the slow operation
2. Identify optimization opportunities
3. Consider parallelization or caching
4. Implement and measure improvement
                """.strip(),
                priority="low",
                category="maintenance",
                estimated_value=0.2,
                created_at=now
            ))

    return tasks


def store_generated_task(task: GeneratedTask):
    """Store a generated task."""
    conn = init_db()
    c = conn.cursor()

    c.execute("""
        INSERT OR IGNORE INTO generated_tasks
        (task_id, source_pattern, title, description, priority, category,
         estimated_value, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (task.task_id, task.source_pattern, task.title, task.description,
          task.priority, task.category, task.estimated_value, task.created_at))

    conn.commit()
    conn.close()


def get_pending_generated_tasks() -> List[Dict]:
    """Get all pending generated tasks."""
    conn = init_db()
    c = conn.cursor()

    c.execute("""
        SELECT task_id, title, description, priority, category, estimated_value, created_at
        FROM generated_tasks
        WHERE status = 'pending'
        ORDER BY
            CASE priority
                WHEN 'urgent' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                ELSE 4
            END,
            estimated_value DESC
    """)

    tasks = []
    for row in c.fetchall():
        tasks.append({
            "task_id": row[0],
            "title": row[1],
            "description": row[2],
            "priority": row[3],
            "category": row[4],
            "estimated_value": row[5],
            "created_at": row[6]
        })

    conn.close()
    return tasks

# ============================================================================
# Autonomous Goal Refinement
# ============================================================================

def analyze_goals_for_refinement() -> List[GoalRefinement]:
    """
    Analyze goals and propose refinements based on outcomes.

    Refinement types:
    - increase_ambition: Goal achieved too easily
    - decompose: Goal too complex, break down
    - drop: Goal consistently failing, low value
    - pivot: Goal valuable but approach wrong
    """
    refinements = []

    if not COHERENCE_DB.exists():
        return refinements

    conn = sqlite3.connect(COHERENCE_DB)
    c = conn.cursor()

    # Get goals with their coherence scores
    try:
        c.execute("""
            SELECT g.goal_id, g.description, g.priority, g.status,
                   AVG(h.coherence_score) as avg_coherence,
                   COUNT(h.id) as check_count
            FROM goals g
            LEFT JOIN coherence_history h ON g.goal_id = h.goal_id
            GROUP BY g.goal_id
        """)

        for row in c.fetchall():
            goal_id, desc, priority, status, avg_coherence, check_count = row

            # Skip if not enough data
            if check_count < 3:
                continue

            avg_coherence = avg_coherence or 0.5

            # Low coherence = goal may need rethinking
            if avg_coherence < 0.3:
                refinements.append(GoalRefinement(
                    goal_id=goal_id,
                    refinement_type="pivot" if avg_coherence > 0.1 else "drop",
                    reason=f"Low coherence score ({avg_coherence:.2f}) across {check_count} checks",
                    confidence=0.6
                ))

            # Very high coherence = maybe too easy
            elif avg_coherence > 0.9 and status == "active":
                refinements.append(GoalRefinement(
                    goal_id=goal_id,
                    refinement_type="increase_ambition",
                    reason=f"Consistently high coherence ({avg_coherence:.2f}), goal may be too easy",
                    confidence=0.5
                ))

    except sqlite3.OperationalError:
        pass  # Table structure different

    conn.close()
    return refinements


def store_goal_refinement(refinement: GoalRefinement):
    """Store a proposed goal refinement."""
    conn = init_db()
    c = conn.cursor()

    c.execute("""
        INSERT INTO goal_refinements
        (goal_id, refinement_type, reason, new_target, confidence, proposed_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (refinement.goal_id, refinement.refinement_type, refinement.reason,
          refinement.new_target, refinement.confidence, datetime.now().isoformat()))

    conn.commit()
    conn.close()

# ============================================================================
# Self-Directed Learning
# ============================================================================

def identify_learning_targets() -> List[LearningTarget]:
    """
    Identify capability gaps that should be addressed.

    Sources:
    - Metacognition database (capability assessments)
    - Decision outcomes (what went wrong)
    - Task failures (what couldn't be done)
    """
    targets = []
    now = datetime.now().isoformat()

    # Check metacognition for low capabilities
    metacog_db = Path(__file__).parent / "metacognition.db"
    if metacog_db.exists():
        conn = sqlite3.connect(metacog_db)
        c = conn.cursor()

        try:
            c.execute("""
                SELECT capability, level, domain
                FROM capabilities
                WHERE level < 0.5
                ORDER BY level ASC
                LIMIT 5
            """)

            for row in c.fetchall():
                cap, level, domain = row
                targets.append(LearningTarget(
                    target_id=f"learn_{hash(cap) % 10000}",
                    capability=cap,
                    current_level=level,
                    target_level=min(level + 0.3, 1.0),
                    importance=1.0 - level,  # Lower capability = higher importance
                    learning_resources=[
                        f"Research {cap} best practices",
                        f"Find examples of {cap} in codebase",
                        f"Practice {cap} on small tasks"
                    ],
                    created_at=now
                ))
        except sqlite3.OperationalError:
            pass

        conn.close()

    return targets


def store_learning_target(target: LearningTarget):
    """Store a learning target."""
    conn = init_db()
    c = conn.cursor()

    c.execute("""
        INSERT OR IGNORE INTO learning_targets
        (target_id, capability, current_level, target_level, importance,
         learning_resources, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (target.target_id, target.capability, target.current_level,
          target.target_level, target.importance,
          json.dumps(target.learning_resources), target.created_at))

    conn.commit()
    conn.close()

# ============================================================================
# Main Orchestration
# ============================================================================

def run_emergent_cycle() -> Dict[str, Any]:
    """
    Run one cycle of emergent behavior analysis.

    Returns summary of findings and generated tasks.
    """
    results = {
        "patterns_detected": 0,
        "tasks_generated": 0,
        "goal_refinements": 0,
        "learning_targets": 0,
        "details": []
    }

    # 1. Detect patterns
    patterns = detect_patterns(lookback_days=7)
    results["patterns_detected"] = len(patterns)

    for pattern in patterns:
        store_pattern(pattern)
        results["details"].append(f"Pattern: {pattern.pattern_type} - {pattern.description[:50]}")

    # 2. Generate tasks from patterns
    tasks = generate_tasks_from_patterns(patterns)
    results["tasks_generated"] = len(tasks)

    for task in tasks:
        store_generated_task(task)
        results["details"].append(f"Task: [{task.priority}] {task.title}")

    # 3. Analyze goals for refinement
    refinements = analyze_goals_for_refinement()
    results["goal_refinements"] = len(refinements)

    for ref in refinements:
        store_goal_refinement(ref)
        results["details"].append(f"Goal refinement: {ref.refinement_type} for {ref.goal_id}")

    # 4. Identify learning targets
    learning_targets = identify_learning_targets()
    results["learning_targets"] = len(learning_targets)

    for target in learning_targets:
        store_learning_target(target)
        results["details"].append(f"Learning: {target.capability} ({target.current_level:.1f} -> {target.target_level:.1f})")

    return results


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Emergent Behaviors Module")
    parser.add_argument("--run", action="store_true", help="Run emergent cycle")
    parser.add_argument("--patterns", action="store_true", help="Detect and show patterns")
    parser.add_argument("--tasks", action="store_true", help="Show generated tasks")
    parser.add_argument("--refinements", action="store_true", help="Show goal refinements")
    parser.add_argument("--learning", action="store_true", help="Show learning targets")

    args = parser.parse_args()

    if args.run:
        results = run_emergent_cycle()
        print(f"\n=== Emergent Cycle Results ===")
        print(f"Patterns detected: {results['patterns_detected']}")
        print(f"Tasks generated: {results['tasks_generated']}")
        print(f"Goal refinements: {results['goal_refinements']}")
        print(f"Learning targets: {results['learning_targets']}")
        print(f"\nDetails:")
        for detail in results["details"]:
            print(f"  - {detail}")

    elif args.patterns:
        patterns = detect_patterns()
        print(f"\n=== Detected Patterns ({len(patterns)}) ===")
        for p in patterns:
            print(f"\n[{p.pattern_type}] {p.description}")
            print(f"  Frequency: {p.frequency}, Confidence: {p.confidence:.2f}")
            if p.suggested_action:
                print(f"  Suggested: {p.suggested_action}")

    elif args.tasks:
        tasks = get_pending_generated_tasks()
        print(f"\n=== Generated Tasks ({len(tasks)}) ===")
        for t in tasks:
            print(f"\n[{t['priority']}] {t['title']}")
            print(f"  Category: {t['category']}, Value: {t['estimated_value']:.2f}")

    elif args.refinements:
        conn = init_db()
        c = conn.cursor()
        c.execute("SELECT * FROM goal_refinements WHERE status = 'pending'")
        print(f"\n=== Pending Goal Refinements ===")
        for row in c.fetchall():
            print(f"\n{row[1]}: {row[2]}")
            print(f"  Reason: {row[3]}")
        conn.close()

    elif args.learning:
        conn = init_db()
        c = conn.cursor()
        c.execute("SELECT * FROM learning_targets WHERE status = 'active'")
        print(f"\n=== Active Learning Targets ===")
        for row in c.fetchall():
            print(f"\n{row[1]}: {row[2]:.1f} -> {row[3]:.1f}")
            print(f"  Importance: {row[4]:.2f}")
        conn.close()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
