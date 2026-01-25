#!/usr/bin/env python3
"""
Strategy Evolution System - Comprehensive Adaptive Strategy Management

A complete system for:
- Strategy tracking and versioning
- Evolution through mutation and crossover
- A/B testing with statistical significance
- Moat identification and protection
- Design pattern library
- Development lifecycle management

This is designed to be THE strategy management solution, minimizing future thinking.

Usage:
    # Create a strategy
    python daemon/strategy_evolution.py create --name "fast-fix" --type tactical \
        --description "Use spark agent for quick fixes" --actions "agent:spark"

    # Record strategy performance
    python daemon/strategy_evolution.py record --strategy "fast-fix" --result success

    # Evolve strategies (mutation + crossover)
    python daemon/strategy_evolution.py evolve --generation 5

    # Run A/B test
    python daemon/strategy_evolution.py ab-test --a "fast-fix" --b "tdd-fix" --trials 20

    # Identify moats
    python daemon/strategy_evolution.py moats

    # Get strategy recommendations
    python daemon/strategy_evolution.py recommend --context "bug fix needed"

    # Full status
    python daemon/strategy_evolution.py status
"""

import sqlite3
import json
import random
import hashlib
import math
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
import statistics

DB_PATH = Path(__file__).parent / "strategies.db"


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

class StrategyType(Enum):
    TACTICAL = "tactical"       # Short-term, specific actions
    OPERATIONAL = "operational"  # Medium-term, process-level
    STRATEGIC = "strategic"      # Long-term, goal-level
    META = "meta"               # Strategies about strategies


class StrategyStatus(Enum):
    DRAFT = "draft"
    TESTING = "testing"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class MoatType(Enum):
    KNOWLEDGE = "knowledge"       # Accumulated learning
    EFFICIENCY = "efficiency"     # Speed/cost advantage
    INTEGRATION = "integration"   # System connections
    NETWORK = "network"          # External relationships
    COMPOUND = "compound"        # Multiple reinforcing moats


@dataclass
class Strategy:
    """A complete strategy definition."""
    strategy_id: str
    name: str
    version: int
    type: str                    # tactical, operational, strategic, meta
    status: str                  # draft, testing, active, deprecated, archived
    description: str
    actions: List[str]           # Actions to take (e.g., ["agent:kraken", "skill:test"])
    preconditions: List[str]     # When to apply
    postconditions: List[str]    # Expected outcomes
    constraints: List[str]       # Limitations
    metrics: Dict[str, float]    # Performance metrics
    parent_id: Optional[str]     # For evolution tracking
    generation: int              # Evolution generation
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]


@dataclass
class StrategyPerformance:
    """Performance record for a strategy."""
    record_id: str
    strategy_id: str
    result: str                  # success, partial, failure
    context: str
    duration_ms: int
    tokens_used: int
    quality_score: float         # 0.0-1.0
    notes: str
    timestamp: str


@dataclass
class ABTest:
    """A/B test definition and results."""
    test_id: str
    strategy_a: str
    strategy_b: str
    context_filter: str
    trials_target: int
    trials_a: int
    trials_b: int
    successes_a: int
    successes_b: int
    avg_duration_a: float
    avg_duration_b: float
    status: str                  # running, completed, inconclusive
    winner: Optional[str]
    p_value: float
    created_at: str
    completed_at: Optional[str]


@dataclass
class Moat:
    """A competitive advantage / moat."""
    moat_id: str
    name: str
    type: str                    # knowledge, efficiency, integration, network, compound
    description: str
    strength: float              # 0.0-1.0
    strategies: List[str]        # Strategies that create/use this moat
    dependencies: List[str]      # What this moat depends on
    threats: List[str]           # What could erode this moat
    reinforcement_actions: List[str]  # Actions to strengthen
    metrics: Dict[str, float]
    created_at: str
    updated_at: str


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

def init_db():
    """Initialize the strategies database with comprehensive schema."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Strategies table
    c.execute('''CREATE TABLE IF NOT EXISTS strategies (
        strategy_id TEXT PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        version INTEGER DEFAULT 1,
        type TEXT NOT NULL,
        status TEXT DEFAULT 'draft',
        description TEXT,
        actions TEXT,
        preconditions TEXT,
        postconditions TEXT,
        constraints TEXT,
        metrics TEXT,
        parent_id TEXT,
        generation INTEGER DEFAULT 0,
        created_at TEXT,
        updated_at TEXT,
        metadata TEXT,
        FOREIGN KEY (parent_id) REFERENCES strategies(strategy_id)
    )''')

    # Performance records
    c.execute('''CREATE TABLE IF NOT EXISTS performance (
        record_id TEXT PRIMARY KEY,
        strategy_id TEXT NOT NULL,
        result TEXT NOT NULL,
        context TEXT,
        duration_ms INTEGER DEFAULT 0,
        tokens_used INTEGER DEFAULT 0,
        quality_score REAL DEFAULT 0.0,
        notes TEXT,
        timestamp TEXT,
        FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id)
    )''')

    # A/B tests
    c.execute('''CREATE TABLE IF NOT EXISTS ab_tests (
        test_id TEXT PRIMARY KEY,
        strategy_a TEXT NOT NULL,
        strategy_b TEXT NOT NULL,
        context_filter TEXT,
        trials_target INTEGER DEFAULT 20,
        trials_a INTEGER DEFAULT 0,
        trials_b INTEGER DEFAULT 0,
        successes_a INTEGER DEFAULT 0,
        successes_b INTEGER DEFAULT 0,
        avg_duration_a REAL DEFAULT 0,
        avg_duration_b REAL DEFAULT 0,
        status TEXT DEFAULT 'running',
        winner TEXT,
        p_value REAL DEFAULT 1.0,
        created_at TEXT,
        completed_at TEXT,
        FOREIGN KEY (strategy_a) REFERENCES strategies(strategy_id),
        FOREIGN KEY (strategy_b) REFERENCES strategies(strategy_id)
    )''')

    # Moats
    c.execute('''CREATE TABLE IF NOT EXISTS moats (
        moat_id TEXT PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        type TEXT NOT NULL,
        description TEXT,
        strength REAL DEFAULT 0.5,
        strategies TEXT,
        dependencies TEXT,
        threats TEXT,
        reinforcement_actions TEXT,
        metrics TEXT,
        created_at TEXT,
        updated_at TEXT
    )''')

    # Evolution history
    c.execute('''CREATE TABLE IF NOT EXISTS evolution_history (
        evolution_id TEXT PRIMARY KEY,
        generation INTEGER,
        parent_ids TEXT,
        child_id TEXT,
        mutation_type TEXT,
        mutation_details TEXT,
        fitness_before REAL,
        fitness_after REAL,
        timestamp TEXT
    )''')

    # Strategy relationships (for compound strategies)
    c.execute('''CREATE TABLE IF NOT EXISTS strategy_relationships (
        relationship_id TEXT PRIMARY KEY,
        from_strategy TEXT,
        to_strategy TEXT,
        relationship_type TEXT,
        strength REAL DEFAULT 1.0,
        created_at TEXT,
        FOREIGN KEY (from_strategy) REFERENCES strategies(strategy_id),
        FOREIGN KEY (to_strategy) REFERENCES strategies(strategy_id)
    )''')

    # Indexes
    c.execute('''CREATE INDEX IF NOT EXISTS idx_strategy_status ON strategies(status)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_strategy_type ON strategies(type)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_perf_strategy ON performance(strategy_id)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_perf_result ON performance(result)''')

    conn.commit()
    conn.close()


# =============================================================================
# STRATEGY MANAGEMENT
# =============================================================================

def create_strategy(
    name: str,
    type: str,
    description: str,
    actions: List[str],
    preconditions: List[str] = None,
    postconditions: List[str] = None,
    constraints: List[str] = None,
    parent_id: str = None,
    generation: int = 0,
    metadata: Dict = None
) -> str:
    """Create a new strategy."""
    init_db()

    strategy_id = f"strat_{hashlib.md5(name.encode()).hexdigest()[:12]}"
    now = datetime.now().isoformat()

    strategy = Strategy(
        strategy_id=strategy_id,
        name=name,
        version=1,
        type=type,
        status="draft",
        description=description,
        actions=actions or [],
        preconditions=preconditions or [],
        postconditions=postconditions or [],
        constraints=constraints or [],
        metrics={"success_rate": 0.0, "avg_duration": 0.0, "fitness": 0.0},
        parent_id=parent_id,
        generation=generation,
        created_at=now,
        updated_at=now,
        metadata=metadata or {}
    )

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''INSERT OR REPLACE INTO strategies
        (strategy_id, name, version, type, status, description, actions,
         preconditions, postconditions, constraints, metrics, parent_id,
         generation, created_at, updated_at, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (strategy.strategy_id, strategy.name, strategy.version, strategy.type,
         strategy.status, strategy.description, json.dumps(strategy.actions),
         json.dumps(strategy.preconditions), json.dumps(strategy.postconditions),
         json.dumps(strategy.constraints), json.dumps(strategy.metrics),
         strategy.parent_id, strategy.generation, strategy.created_at,
         strategy.updated_at, json.dumps(strategy.metadata)))

    conn.commit()
    conn.close()

    return strategy_id


def get_strategy(strategy_id: str = None, name: str = None) -> Optional[Strategy]:
    """Get a strategy by ID or name."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if strategy_id:
        c.execute('SELECT * FROM strategies WHERE strategy_id = ?', (strategy_id,))
    elif name:
        c.execute('SELECT * FROM strategies WHERE name = ?', (name,))
    else:
        return None

    row = c.fetchone()
    conn.close()

    if not row:
        return None

    return Strategy(
        strategy_id=row[0],
        name=row[1],
        version=row[2],
        type=row[3],
        status=row[4],
        description=row[5],
        actions=json.loads(row[6]) if row[6] else [],
        preconditions=json.loads(row[7]) if row[7] else [],
        postconditions=json.loads(row[8]) if row[8] else [],
        constraints=json.loads(row[9]) if row[9] else [],
        metrics=json.loads(row[10]) if row[10] else {},
        parent_id=row[11],
        generation=row[12],
        created_at=row[13],
        updated_at=row[14],
        metadata=json.loads(row[15]) if row[15] else {}
    )


def update_strategy_status(strategy_id: str, status: str):
    """Update strategy status."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE strategies SET status = ?, updated_at = ? WHERE strategy_id = ?',
              (status, datetime.now().isoformat(), strategy_id))
    conn.commit()
    conn.close()


def list_strategies(
    status: str = None,
    type: str = None,
    min_fitness: float = None
) -> List[Strategy]:
    """List strategies with optional filters."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    query = 'SELECT * FROM strategies WHERE 1=1'
    params = []

    if status:
        query += ' AND status = ?'
        params.append(status)
    if type:
        query += ' AND type = ?'
        params.append(type)

    query += ' ORDER BY updated_at DESC'
    c.execute(query, params)

    strategies = []
    for row in c.fetchall():
        strat = Strategy(
            strategy_id=row[0], name=row[1], version=row[2], type=row[3],
            status=row[4], description=row[5],
            actions=json.loads(row[6]) if row[6] else [],
            preconditions=json.loads(row[7]) if row[7] else [],
            postconditions=json.loads(row[8]) if row[8] else [],
            constraints=json.loads(row[9]) if row[9] else [],
            metrics=json.loads(row[10]) if row[10] else {},
            parent_id=row[11], generation=row[12],
            created_at=row[13], updated_at=row[14],
            metadata=json.loads(row[15]) if row[15] else {}
        )
        if min_fitness is None or strat.metrics.get('fitness', 0) >= min_fitness:
            strategies.append(strat)

    conn.close()
    return strategies


# =============================================================================
# PERFORMANCE TRACKING
# =============================================================================

def record_performance(
    strategy_name: str,
    result: str,
    context: str = "",
    duration_ms: int = 0,
    tokens_used: int = 0,
    quality_score: float = 0.5,
    notes: str = ""
) -> str:
    """Record strategy performance."""
    init_db()

    strategy = get_strategy(name=strategy_name)
    if not strategy:
        raise ValueError(f"Strategy '{strategy_name}' not found")

    record_id = f"perf_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000,9999)}"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''INSERT INTO performance
        (record_id, strategy_id, result, context, duration_ms, tokens_used,
         quality_score, notes, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (record_id, strategy.strategy_id, result, context, duration_ms,
         tokens_used, quality_score, notes, datetime.now().isoformat()))

    conn.commit()

    # Update strategy metrics
    _update_strategy_metrics(strategy.strategy_id, conn)

    conn.close()
    return record_id


def _update_strategy_metrics(strategy_id: str, conn: sqlite3.Connection):
    """Update strategy metrics based on performance history."""
    c = conn.cursor()

    c.execute('''SELECT
        COUNT(*) as total,
        SUM(CASE WHEN result = 'success' THEN 1 ELSE 0 END) as successes,
        AVG(duration_ms) as avg_duration,
        AVG(quality_score) as avg_quality,
        AVG(tokens_used) as avg_tokens
        FROM performance WHERE strategy_id = ?''', (strategy_id,))

    row = c.fetchone()
    if row and row[0] > 0:
        total, successes, avg_duration, avg_quality, avg_tokens = row
        success_rate = successes / total if total > 0 else 0

        # Calculate fitness (weighted combination)
        # Higher success rate = better
        # Lower duration = better (normalized)
        # Higher quality = better
        # Lower tokens = better (normalized)
        duration_score = max(0, 1 - (avg_duration or 0) / 60000)  # Normalize to 1 min
        token_score = max(0, 1 - (avg_tokens or 0) / 10000)  # Normalize to 10k tokens

        fitness = (
            0.4 * success_rate +
            0.2 * duration_score +
            0.3 * (avg_quality or 0.5) +
            0.1 * token_score
        )

        metrics = {
            "success_rate": round(success_rate, 4),
            "avg_duration": round(avg_duration or 0, 1),
            "avg_quality": round(avg_quality or 0, 4),
            "avg_tokens": round(avg_tokens or 0, 1),
            "sample_count": total,
            "fitness": round(fitness, 4)
        }

        c.execute('UPDATE strategies SET metrics = ?, updated_at = ? WHERE strategy_id = ?',
                  (json.dumps(metrics), datetime.now().isoformat(), strategy_id))
        conn.commit()


# =============================================================================
# STRATEGY EVOLUTION
# =============================================================================

def evolve_strategies(generation: int = 1, population_size: int = 5) -> List[str]:
    """Evolve strategies through mutation and crossover."""
    init_db()

    # Get top performing active strategies
    strategies = list_strategies(status="active")
    if len(strategies) < 2:
        print("Need at least 2 active strategies to evolve")
        return []

    # Sort by fitness
    strategies.sort(key=lambda s: s.metrics.get('fitness', 0), reverse=True)

    # Select parents (top 50%)
    parents = strategies[:max(2, len(strategies) // 2)]

    new_strategies = []

    for i in range(population_size):
        # Random evolution method
        method = random.choice(['mutation', 'crossover', 'recombination'])

        if method == 'mutation':
            parent = random.choice(parents)
            child_id = _mutate_strategy(parent, generation)
        elif method == 'crossover':
            parent1, parent2 = random.sample(parents, 2)
            child_id = _crossover_strategies(parent1, parent2, generation)
        else:  # recombination
            parent = random.choice(parents)
            child_id = _recombine_strategy(parent, generation)

        if child_id:
            new_strategies.append(child_id)

    return new_strategies


def _mutate_strategy(parent: Strategy, generation: int) -> str:
    """Create a mutated version of a strategy."""
    mutations = ['add_action', 'remove_action', 'modify_constraint', 'change_type']
    mutation = random.choice(mutations)

    new_actions = parent.actions.copy()
    new_constraints = parent.constraints.copy()
    new_type = parent.type

    if mutation == 'add_action' and len(new_actions) < 5:
        # Add a related action
        possible_actions = [
            "agent:spark", "agent:kraken", "agent:scout", "agent:oracle",
            "skill:commit", "skill:test", "skill:review",
            "model:localai", "model:codex", "model:claude"
        ]
        new_action = random.choice([a for a in possible_actions if a not in new_actions])
        new_actions.append(new_action)

    elif mutation == 'remove_action' and len(new_actions) > 1:
        new_actions.pop(random.randint(0, len(new_actions) - 1))

    elif mutation == 'modify_constraint':
        new_constraints.append(f"mutated_gen_{generation}")

    elif mutation == 'change_type':
        types = ['tactical', 'operational', 'strategic']
        new_type = random.choice([t for t in types if t != parent.type])

    # Create mutated strategy
    new_name = f"{parent.name}_mut_g{generation}"
    child_id = create_strategy(
        name=new_name,
        type=new_type,
        description=f"Mutation of {parent.name} (gen {generation})",
        actions=new_actions,
        preconditions=parent.preconditions,
        postconditions=parent.postconditions,
        constraints=new_constraints,
        parent_id=parent.strategy_id,
        generation=generation,
        metadata={"mutation_type": mutation, "parent": parent.name}
    )

    # Record evolution
    _record_evolution(generation, [parent.strategy_id], child_id, mutation,
                     {"original_action_count": len(parent.actions),
                      "new_action_count": len(new_actions)},
                     parent.metrics.get('fitness', 0), 0)

    return child_id


def _crossover_strategies(parent1: Strategy, parent2: Strategy, generation: int) -> str:
    """Create offspring from two parent strategies."""
    # Combine actions (union with probability)
    new_actions = []
    all_actions = set(parent1.actions) | set(parent2.actions)
    for action in all_actions:
        # Higher probability if in both parents
        if action in parent1.actions and action in parent2.actions:
            new_actions.append(action)
        elif random.random() > 0.5:
            new_actions.append(action)

    # Combine preconditions
    new_preconditions = list(set(parent1.preconditions) | set(parent2.preconditions))

    # Take type from fitter parent
    if parent1.metrics.get('fitness', 0) > parent2.metrics.get('fitness', 0):
        new_type = parent1.type
    else:
        new_type = parent2.type

    new_name = f"{parent1.name[:10]}x{parent2.name[:10]}_g{generation}"
    child_id = create_strategy(
        name=new_name,
        type=new_type,
        description=f"Crossover of {parent1.name} and {parent2.name}",
        actions=new_actions,
        preconditions=new_preconditions,
        postconditions=parent1.postconditions + parent2.postconditions,
        constraints=[],
        parent_id=parent1.strategy_id,  # Primary parent
        generation=generation,
        metadata={"crossover": True, "parents": [parent1.name, parent2.name]}
    )

    avg_fitness = (parent1.metrics.get('fitness', 0) + parent2.metrics.get('fitness', 0)) / 2
    _record_evolution(generation, [parent1.strategy_id, parent2.strategy_id],
                     child_id, "crossover", {}, avg_fitness, 0)

    return child_id


def _recombine_strategy(parent: Strategy, generation: int) -> str:
    """Create a recombined strategy with shuffled elements."""
    # Shuffle action order (affects execution sequence)
    new_actions = parent.actions.copy()
    random.shuffle(new_actions)

    new_name = f"{parent.name}_recomb_g{generation}"
    child_id = create_strategy(
        name=new_name,
        type=parent.type,
        description=f"Recombination of {parent.name}",
        actions=new_actions,
        preconditions=parent.preconditions,
        postconditions=parent.postconditions,
        constraints=parent.constraints,
        parent_id=parent.strategy_id,
        generation=generation,
        metadata={"recombination": True, "parent": parent.name}
    )

    _record_evolution(generation, [parent.strategy_id], child_id, "recombination",
                     {}, parent.metrics.get('fitness', 0), 0)

    return child_id


def _record_evolution(generation: int, parent_ids: List[str], child_id: str,
                     mutation_type: str, mutation_details: Dict,
                     fitness_before: float, fitness_after: float):
    """Record evolution event."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    evolution_id = f"evo_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(100,999)}"

    c.execute('''INSERT INTO evolution_history
        (evolution_id, generation, parent_ids, child_id, mutation_type,
         mutation_details, fitness_before, fitness_after, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (evolution_id, generation, json.dumps(parent_ids), child_id,
         mutation_type, json.dumps(mutation_details), fitness_before,
         fitness_after, datetime.now().isoformat()))

    conn.commit()
    conn.close()


# =============================================================================
# A/B TESTING
# =============================================================================

def create_ab_test(strategy_a: str, strategy_b: str, trials: int = 20,
                   context_filter: str = "") -> str:
    """Create an A/B test between two strategies."""
    init_db()

    strat_a = get_strategy(name=strategy_a)
    strat_b = get_strategy(name=strategy_b)

    if not strat_a or not strat_b:
        raise ValueError("Both strategies must exist")

    test_id = f"ab_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''INSERT INTO ab_tests
        (test_id, strategy_a, strategy_b, context_filter, trials_target,
         status, created_at)
        VALUES (?, ?, ?, ?, ?, 'running', ?)''',
        (test_id, strat_a.strategy_id, strat_b.strategy_id, context_filter,
         trials, datetime.now().isoformat()))

    conn.commit()
    conn.close()

    return test_id


def record_ab_result(test_id: str, strategy_name: str, result: str, duration_ms: int = 0):
    """Record a result for an A/B test."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Get test
    c.execute('SELECT * FROM ab_tests WHERE test_id = ?', (test_id,))
    test = c.fetchone()
    if not test:
        raise ValueError(f"Test {test_id} not found")

    strategy = get_strategy(name=strategy_name)
    is_success = result == "success"

    # Update counts
    if strategy.strategy_id == test[1]:  # strategy_a
        c.execute('''UPDATE ab_tests SET
            trials_a = trials_a + 1,
            successes_a = successes_a + ?,
            avg_duration_a = (avg_duration_a * trials_a + ?) / (trials_a + 1)
            WHERE test_id = ?''',
            (1 if is_success else 0, duration_ms, test_id))
    elif strategy.strategy_id == test[2]:  # strategy_b
        c.execute('''UPDATE ab_tests SET
            trials_b = trials_b + 1,
            successes_b = successes_b + ?,
            avg_duration_b = (avg_duration_b * trials_b + ?) / (trials_b + 1)
            WHERE test_id = ?''',
            (1 if is_success else 0, duration_ms, test_id))

    conn.commit()

    # Check if test is complete
    c.execute('SELECT trials_a, trials_b, trials_target FROM ab_tests WHERE test_id = ?',
              (test_id,))
    trials_a, trials_b, target = c.fetchone()

    if trials_a + trials_b >= target:
        _complete_ab_test(test_id, conn)

    conn.close()


def _complete_ab_test(test_id: str, conn: sqlite3.Connection):
    """Complete an A/B test and determine winner."""
    c = conn.cursor()
    c.execute('SELECT * FROM ab_tests WHERE test_id = ?', (test_id,))
    test = c.fetchone()

    trials_a, trials_b = test[5], test[6]
    successes_a, successes_b = test[7], test[8]

    # Calculate p-value using chi-square approximation
    if trials_a > 0 and trials_b > 0:
        rate_a = successes_a / trials_a
        rate_b = successes_b / trials_b

        # Pooled proportion
        pooled = (successes_a + successes_b) / (trials_a + trials_b)
        se = math.sqrt(pooled * (1 - pooled) * (1/trials_a + 1/trials_b))

        if se > 0:
            z = abs(rate_a - rate_b) / se
            # Approximate p-value
            p_value = 2 * (1 - _norm_cdf(z))
        else:
            p_value = 1.0

        # Determine winner (p < 0.05)
        if p_value < 0.05:
            winner = test[1] if rate_a > rate_b else test[2]
            status = "completed"
        else:
            winner = None
            status = "inconclusive"
    else:
        p_value = 1.0
        winner = None
        status = "inconclusive"

    c.execute('''UPDATE ab_tests SET
        status = ?, winner = ?, p_value = ?, completed_at = ?
        WHERE test_id = ?''',
        (status, winner, p_value, datetime.now().isoformat(), test_id))
    conn.commit()


def _norm_cdf(x: float) -> float:
    """Approximate normal CDF."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def get_ab_test_status(test_id: str) -> Dict:
    """Get A/B test status and results."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('SELECT * FROM ab_tests WHERE test_id = ?', (test_id,))
    test = c.fetchone()
    conn.close()

    if not test:
        return None

    strat_a = get_strategy(strategy_id=test[1])
    strat_b = get_strategy(strategy_id=test[2])

    return {
        "test_id": test[0],
        "strategy_a": strat_a.name if strat_a else test[1],
        "strategy_b": strat_b.name if strat_b else test[2],
        "trials_a": test[5],
        "trials_b": test[6],
        "successes_a": test[7],
        "successes_b": test[8],
        "rate_a": test[7] / test[5] if test[5] > 0 else 0,
        "rate_b": test[8] / test[6] if test[6] > 0 else 0,
        "status": test[11],
        "winner": test[12],
        "p_value": test[13]
    }


# =============================================================================
# MOAT MANAGEMENT
# =============================================================================

def create_moat(
    name: str,
    type: str,
    description: str,
    strategies: List[str] = None,
    dependencies: List[str] = None,
    threats: List[str] = None,
    reinforcement_actions: List[str] = None
) -> str:
    """Create or update a moat."""
    init_db()

    moat_id = f"moat_{hashlib.md5(name.encode()).hexdigest()[:12]}"
    now = datetime.now().isoformat()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''INSERT OR REPLACE INTO moats
        (moat_id, name, type, description, strength, strategies, dependencies,
         threats, reinforcement_actions, metrics, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (moat_id, name, type, description, 0.5,
         json.dumps(strategies or []), json.dumps(dependencies or []),
         json.dumps(threats or []), json.dumps(reinforcement_actions or []),
         json.dumps({}), now, now))

    conn.commit()
    conn.close()

    return moat_id


def identify_moats() -> List[Dict]:
    """Identify moats from strategy performance patterns."""
    init_db()

    moats = []

    # Knowledge moat: Based on accumulated learnings
    strategies = list_strategies(status="active")
    if strategies:
        total_samples = sum(s.metrics.get('sample_count', 0) for s in strategies)
        if total_samples > 20:
            moats.append({
                "type": "knowledge",
                "name": "Accumulated Strategy Knowledge",
                "strength": min(1.0, total_samples / 100),
                "evidence": f"{total_samples} performance samples",
                "strategies": [s.name for s in strategies[:5]]
            })

    # Efficiency moat: Based on avg duration improvements
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''SELECT AVG(duration_ms) FROM performance
                 WHERE timestamp > datetime('now', '-7 days')''')
    recent_avg = c.fetchone()[0]

    c.execute('''SELECT AVG(duration_ms) FROM performance
                 WHERE timestamp < datetime('now', '-7 days')''')
    old_avg = c.fetchone()[0]

    if recent_avg and old_avg and recent_avg < old_avg:
        improvement = (old_avg - recent_avg) / old_avg
        moats.append({
            "type": "efficiency",
            "name": "Processing Speed Improvement",
            "strength": min(1.0, improvement * 2),
            "evidence": f"{improvement*100:.1f}% faster than before",
            "strategies": []
        })

    # Integration moat: Based on connected systems
    integration_count = 5  # Known integrations: Telegram, GitHub, Email, LocalAI, Dragonfly
    moats.append({
        "type": "integration",
        "name": "System Integrations",
        "strength": min(1.0, integration_count / 10),
        "evidence": f"{integration_count} external system connections",
        "strategies": []
    })

    conn.close()
    return moats


def get_moats() -> List[Dict]:
    """Get all defined moats."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('SELECT * FROM moats ORDER BY strength DESC')

    moats = []
    for row in c.fetchall():
        moats.append({
            "moat_id": row[0],
            "name": row[1],
            "type": row[2],
            "description": row[3],
            "strength": row[4],
            "strategies": json.loads(row[5]) if row[5] else [],
            "threats": json.loads(row[7]) if row[7] else [],
            "reinforcement_actions": json.loads(row[8]) if row[8] else []
        })

    conn.close()
    return moats


# =============================================================================
# RECOMMENDATIONS
# =============================================================================

def recommend_strategy(context: str, action_type: str = None) -> List[Dict]:
    """Recommend best strategy for a given context."""
    init_db()

    strategies = list_strategies(status="active")
    if not strategies:
        return []

    recommendations = []

    for strat in strategies:
        score = strat.metrics.get('fitness', 0)

        # Boost score if context matches preconditions
        for precond in strat.preconditions:
            if precond.lower() in context.lower():
                score *= 1.5

        # Filter by action type if specified
        if action_type:
            if not any(action_type in a for a in strat.actions):
                continue

        recommendations.append({
            "strategy": strat.name,
            "score": round(score, 4),
            "success_rate": strat.metrics.get('success_rate', 0),
            "actions": strat.actions,
            "sample_count": strat.metrics.get('sample_count', 0)
        })

    recommendations.sort(key=lambda x: x['score'], reverse=True)
    return recommendations[:5]


# =============================================================================
# STATUS AND REPORTING
# =============================================================================

def get_status() -> Dict:
    """Get comprehensive strategy system status."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Strategy counts by status
    c.execute('SELECT status, COUNT(*) FROM strategies GROUP BY status')
    status_counts = dict(c.fetchall())

    # Performance summary
    c.execute('''SELECT
        COUNT(*) as total,
        SUM(CASE WHEN result = 'success' THEN 1 ELSE 0 END) as successes
        FROM performance''')
    perf = c.fetchone()

    # Top strategies
    c.execute('''SELECT name, metrics FROM strategies
                 WHERE status = 'active' ORDER BY updated_at DESC LIMIT 5''')
    top_strategies = []
    for row in c.fetchall():
        metrics = json.loads(row[1]) if row[1] else {}
        top_strategies.append({
            "name": row[0],
            "fitness": metrics.get('fitness', 0),
            "success_rate": metrics.get('success_rate', 0)
        })

    # Active A/B tests
    c.execute('SELECT COUNT(*) FROM ab_tests WHERE status = "running"')
    active_tests = c.fetchone()[0]

    # Evolution history
    c.execute('SELECT MAX(generation) FROM strategies')
    max_gen = c.fetchone()[0] or 0

    conn.close()

    return {
        "strategies": {
            "total": sum(status_counts.values()),
            "by_status": status_counts,
            "top_performers": top_strategies
        },
        "performance": {
            "total_records": perf[0] or 0,
            "overall_success_rate": round(perf[1] / perf[0], 4) if perf[0] else 0
        },
        "evolution": {
            "current_generation": max_gen,
            "active_ab_tests": active_tests
        },
        "moats": identify_moats()
    }


# =============================================================================
# SEED STRATEGIES
# =============================================================================

def seed_initial_strategies():
    """Create initial seed strategies for the system."""
    seeds = [
        {
            "name": "quick-fix",
            "type": "tactical",
            "description": "Use spark agent for quick, focused fixes",
            "actions": ["agent:spark"],
            "preconditions": ["bug", "fix", "quick", "simple"],
            "postconditions": ["bug resolved"],
            "constraints": ["single file changes only"]
        },
        {
            "name": "tdd-implement",
            "type": "operational",
            "description": "Test-driven development with kraken agent",
            "actions": ["agent:kraken", "skill:test"],
            "preconditions": ["feature", "implement", "new"],
            "postconditions": ["tests pass", "feature complete"],
            "constraints": ["requires test framework"]
        },
        {
            "name": "research-then-act",
            "type": "strategic",
            "description": "Research with oracle before implementation",
            "actions": ["agent:oracle", "agent:kraken"],
            "preconditions": ["complex", "unfamiliar", "external"],
            "postconditions": ["informed decision", "implementation complete"],
            "constraints": ["time cost for research"]
        },
        {
            "name": "local-first",
            "type": "tactical",
            "description": "Use LocalAI for simple tasks to save tokens",
            "actions": ["model:localai"],
            "preconditions": ["summarize", "simple", "extract"],
            "postconditions": ["task complete", "zero token cost"],
            "constraints": ["limited reasoning capability"]
        },
        {
            "name": "explore-understand",
            "type": "operational",
            "description": "Deep codebase exploration with scout",
            "actions": ["agent:scout"],
            "preconditions": ["explore", "understand", "find"],
            "postconditions": ["codebase understanding"],
            "constraints": ["read-only exploration"]
        }
    ]

    for seed in seeds:
        try:
            create_strategy(**seed)
            update_strategy_status(
                get_strategy(name=seed["name"]).strategy_id,
                "active"
            )
            print(f"Created: {seed['name']}")
        except Exception as e:
            print(f"Skipped {seed['name']}: {e}")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Strategy Evolution System")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a strategy")
    create_parser.add_argument("--name", required=True)
    create_parser.add_argument("--type", required=True, choices=["tactical", "operational", "strategic", "meta"])
    create_parser.add_argument("--description", required=True)
    create_parser.add_argument("--actions", required=True, help="Comma-separated actions")
    create_parser.add_argument("--preconditions", help="Comma-separated preconditions")

    # Record command
    record_parser = subparsers.add_parser("record", help="Record performance")
    record_parser.add_argument("--strategy", required=True)
    record_parser.add_argument("--result", required=True, choices=["success", "partial", "failure"])
    record_parser.add_argument("--context", default="")
    record_parser.add_argument("--duration", type=int, default=0)

    # Evolve command
    evolve_parser = subparsers.add_parser("evolve", help="Evolve strategies")
    evolve_parser.add_argument("--generation", type=int, default=1)
    evolve_parser.add_argument("--population", type=int, default=5)

    # A/B test command
    ab_parser = subparsers.add_parser("ab-test", help="Create/manage A/B tests")
    ab_parser.add_argument("--a", help="Strategy A name")
    ab_parser.add_argument("--b", help="Strategy B name")
    ab_parser.add_argument("--trials", type=int, default=20)
    ab_parser.add_argument("--status", help="Get test status by ID")

    # Moats command
    subparsers.add_parser("moats", help="Identify and list moats")

    # Recommend command
    rec_parser = subparsers.add_parser("recommend", help="Get recommendations")
    rec_parser.add_argument("--context", required=True)
    rec_parser.add_argument("--type", help="Filter by action type")

    # Status command
    subparsers.add_parser("status", help="Full system status")

    # List command
    list_parser = subparsers.add_parser("list", help="List strategies")
    list_parser.add_argument("--status", help="Filter by status")
    list_parser.add_argument("--type", help="Filter by type")

    # Seed command
    subparsers.add_parser("seed", help="Create initial seed strategies")

    args = parser.parse_args()

    if args.command == "create":
        strategy_id = create_strategy(
            name=args.name,
            type=args.type,
            description=args.description,
            actions=args.actions.split(","),
            preconditions=args.preconditions.split(",") if args.preconditions else []
        )
        print(f"Created: {strategy_id}")

    elif args.command == "record":
        record_id = record_performance(
            strategy_name=args.strategy,
            result=args.result,
            context=args.context,
            duration_ms=args.duration
        )
        print(f"Recorded: {record_id}")

    elif args.command == "evolve":
        new_ids = evolve_strategies(args.generation, args.population)
        print(f"Created {len(new_ids)} evolved strategies:")
        for sid in new_ids:
            strat = get_strategy(strategy_id=sid)
            print(f"  {strat.name}")

    elif args.command == "ab-test":
        if args.status:
            result = get_ab_test_status(args.status)
            print(json.dumps(result, indent=2))
        elif args.a and args.b:
            test_id = create_ab_test(args.a, args.b, args.trials)
            print(f"Created A/B test: {test_id}")
        else:
            print("Specify --a and --b to create test, or --status to check")

    elif args.command == "moats":
        moats = identify_moats()
        print("Identified Moats:")
        for m in moats:
            print(f"\n  [{m['type'].upper()}] {m['name']}")
            print(f"    Strength: {m['strength']*100:.0f}%")
            print(f"    Evidence: {m['evidence']}")

    elif args.command == "recommend":
        recs = recommend_strategy(args.context, args.type)
        print(f"Recommendations for '{args.context}':")
        for r in recs:
            print(f"\n  {r['strategy']} (score: {r['score']:.3f})")
            print(f"    Success rate: {r['success_rate']*100:.1f}%")
            print(f"    Actions: {', '.join(r['actions'])}")

    elif args.command == "status":
        status = get_status()
        print(json.dumps(status, indent=2))

    elif args.command == "list":
        strategies = list_strategies(status=args.status, type=args.type)
        print(f"Found {len(strategies)} strategies:")
        for s in strategies:
            fitness = s.metrics.get('fitness', 0)
            print(f"  [{s.status}] {s.name} (fitness: {fitness:.3f})")

    elif args.command == "seed":
        seed_initial_strategies()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
