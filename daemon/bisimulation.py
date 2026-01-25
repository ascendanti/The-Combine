#!/usr/bin/env python3
"""
Bisimulation Engine - State abstraction for goal-conditioned learning.

Phase 12.1: Implements bisimulation metrics for:
1. State equivalence detection (behavioral similarity)
2. Analogical transfer (reuse solutions across similar states)
3. Goal-conditioned abstraction (same goal = same behavior)
4. Policy transfer validation

Based on: "Bisimulation Makes Analogies in Goal-Conditioned RL"

Usage:
    python bisimulation.py --compare state1 state2 goal
    python bisimulation.py --find-analogies state goal
    python bisimulation.py --abstract states.json
"""

import os
import json
import sqlite3
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any, Set
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import math

# ============================================================================
# Configuration
# ============================================================================

DB_PATH = Path(__file__).parent / "bisimulation.db"
CACHE_PATH = Path(__file__).parent / "bisim_cache.json"

# Bisimulation parameters
GAMMA = 0.95  # Discount factor for future state distances
SIMILARITY_THRESHOLD = 0.3  # States with distance < threshold are bisimilar
MAX_CACHE_SIZE = 10000  # Maximum cached bisimulation distances

# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class BisimulationState:
    """State representation for bisimulation analysis."""
    state_id: str
    features: Dict[str, Any]  # Observable features
    goal_context: str  # Current goal being pursued
    action_history: List[str] = field(default_factory=list)  # Recent actions
    reward_history: List[float] = field(default_factory=list)  # Recent rewards
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def feature_vector(self) -> List[float]:
        """Convert features to numeric vector for distance computation."""
        vector = []
        for key in sorted(self.features.keys()):
            val = self.features[key]
            if isinstance(val, (int, float)):
                vector.append(float(val))
            elif isinstance(val, bool):
                vector.append(1.0 if val else 0.0)
            elif isinstance(val, str):
                # Hash string to numeric
                vector.append(hash(val) % 1000 / 1000.0)
            elif isinstance(val, list):
                vector.append(len(val) / 100.0)
        return vector

    def action_signature(self) -> str:
        """Get signature of recent actions for behavioral comparison."""
        return "|".join(self.action_history[-5:]) if self.action_history else ""

@dataclass
class BisimulationMetric:
    """Distance between two states under bisimulation."""
    state_a: str
    state_b: str
    distance: float  # 0 = bisimilar, higher = more different
    goal_context: str  # Goal-specific bisimilarity
    components: Dict[str, float] = field(default_factory=dict)  # Breakdown
    computed_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class StateAbstraction:
    """Equivalence class of bisimilar states."""
    class_id: str
    representative_state: str  # Canonical state for this class
    member_states: List[str]
    goal_context: str
    cohesion: float  # How similar members are (lower = more cohesive)
    policy_hint: Optional[str] = None  # Suggested action for this class

@dataclass
class TransferResult:
    """Result of attempting policy transfer."""
    source_state: str
    source_goal: str
    target_state: str
    target_goal: str
    transfer_valid: bool
    confidence: float
    reasoning: str

# ============================================================================
# Database
# ============================================================================

def init_db():
    """Initialize bisimulation database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS states (
            state_id TEXT PRIMARY KEY,
            features TEXT,
            goal_context TEXT,
            action_history TEXT,
            reward_history TEXT,
            timestamp TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bisim_distances (
            state_a TEXT,
            state_b TEXT,
            goal_context TEXT,
            distance REAL,
            components TEXT,
            computed_at TEXT,
            PRIMARY KEY (state_a, state_b, goal_context)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS abstractions (
            class_id TEXT PRIMARY KEY,
            representative_state TEXT,
            member_states TEXT,
            goal_context TEXT,
            cohesion REAL,
            policy_hint TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transfer_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_state TEXT,
            source_goal TEXT,
            target_state TEXT,
            target_goal TEXT,
            transfer_valid INTEGER,
            confidence REAL,
            reasoning TEXT,
            outcome_success INTEGER,
            timestamp TEXT
        )
    """)

    conn.commit()
    conn.close()

# ============================================================================
# Bisimulation Distance Computation
# ============================================================================

class BisimulationEngine:
    """Compute and cache bisimulation metrics."""

    def __init__(self):
        init_db()
        self.cache: Dict[str, float] = {}
        self._load_cache()

    def _load_cache(self):
        """Load cached distances from file."""
        if CACHE_PATH.exists():
            try:
                with open(CACHE_PATH, 'r') as f:
                    self.cache = json.load(f)
            except:
                self.cache = {}

    def _save_cache(self):
        """Save cache to file."""
        # Trim cache if too large
        if len(self.cache) > MAX_CACHE_SIZE:
            # Keep most recent half
            items = sorted(self.cache.items(), key=lambda x: x[0])
            self.cache = dict(items[len(items)//2:])

        with open(CACHE_PATH, 'w') as f:
            json.dump(self.cache, f)

    def _cache_key(self, s1: str, s2: str, goal: str) -> str:
        """Generate cache key for state pair."""
        # Ensure consistent ordering
        if s1 > s2:
            s1, s2 = s2, s1
        return f"{s1}|{s2}|{goal}"

    def compute_distance(self, s1: BisimulationState, s2: BisimulationState,
                         goal: str) -> BisimulationMetric:
        """
        Compute goal-conditioned bisimulation distance.

        Distance formula (simplified from paper):
        d(s1, s2) = (1-α) * |R(s1) - R(s2)| + α * feature_distance + β * action_distance

        Where:
        - R(s) = expected reward under optimal policy
        - feature_distance = euclidean distance of feature vectors
        - action_distance = edit distance of action histories
        """
        # Check cache
        cache_key = self._cache_key(s1.state_id, s2.state_id, goal)
        if cache_key in self.cache:
            return BisimulationMetric(
                state_a=s1.state_id,
                state_b=s2.state_id,
                distance=self.cache[cache_key],
                goal_context=goal,
                components={"cached": True}
            )

        components = {}

        # 1. Feature distance (normalized Euclidean)
        v1 = s1.feature_vector()
        v2 = s2.feature_vector()

        if v1 and v2:
            # Pad to same length
            max_len = max(len(v1), len(v2))
            v1 = v1 + [0.0] * (max_len - len(v1))
            v2 = v2 + [0.0] * (max_len - len(v2))

            feature_dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))
            feature_dist = min(feature_dist / max_len, 1.0)  # Normalize
        else:
            feature_dist = 1.0 if v1 != v2 else 0.0

        components["feature_distance"] = feature_dist

        # 2. Reward distance (if available)
        if s1.reward_history and s2.reward_history:
            avg_r1 = sum(s1.reward_history) / len(s1.reward_history)
            avg_r2 = sum(s2.reward_history) / len(s2.reward_history)
            reward_dist = abs(avg_r1 - avg_r2) / max(abs(avg_r1), abs(avg_r2), 1.0)
        else:
            reward_dist = 0.0

        components["reward_distance"] = reward_dist

        # 3. Action history distance (behavioral similarity)
        sig1 = s1.action_signature()
        sig2 = s2.action_signature()

        if sig1 and sig2:
            # Jaccard similarity of action sets
            actions1 = set(sig1.split("|"))
            actions2 = set(sig2.split("|"))
            intersection = len(actions1 & actions2)
            union = len(actions1 | actions2)
            action_dist = 1.0 - (intersection / union if union > 0 else 0.0)
        else:
            action_dist = 0.0

        components["action_distance"] = action_dist

        # 4. Goal alignment
        goal_match = 1.0 if s1.goal_context == s2.goal_context == goal else 0.5
        components["goal_alignment"] = goal_match

        # Weighted combination
        # Weights: features 0.4, reward 0.2, actions 0.3, goal 0.1
        distance = (
            0.4 * feature_dist +
            0.2 * reward_dist +
            0.3 * action_dist +
            0.1 * (1.0 - goal_match)
        )

        # Cache result
        self.cache[cache_key] = distance
        if len(self.cache) % 100 == 0:
            self._save_cache()

        return BisimulationMetric(
            state_a=s1.state_id,
            state_b=s2.state_id,
            distance=distance,
            goal_context=goal,
            components=components
        )

    def are_bisimilar(self, s1: BisimulationState, s2: BisimulationState,
                      goal: str, threshold: float = SIMILARITY_THRESHOLD) -> bool:
        """Check if two states are bisimilar (behaviorally equivalent)."""
        metric = self.compute_distance(s1, s2, goal)
        return metric.distance < threshold

    def find_analogies(self, current_state: BisimulationState,
                       goal: str, top_k: int = 5) -> List[Tuple[BisimulationState, float]]:
        """
        Find states bisimilar to current state for given goal.

        Returns list of (state, distance) tuples, sorted by distance.
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all states with same or similar goal
        cursor.execute("""
            SELECT * FROM states
            WHERE goal_context = ? OR goal_context LIKE ?
            ORDER BY timestamp DESC
            LIMIT 1000
        """, (goal, f"%{goal.split('_')[0]}%"))

        candidates = []
        for row in cursor.fetchall():
            state = BisimulationState(
                state_id=row["state_id"],
                features=json.loads(row["features"]),
                goal_context=row["goal_context"],
                action_history=json.loads(row["action_history"]) if row["action_history"] else [],
                reward_history=json.loads(row["reward_history"]) if row["reward_history"] else [],
                timestamp=row["timestamp"]
            )

            if state.state_id != current_state.state_id:
                metric = self.compute_distance(current_state, state, goal)
                candidates.append((state, metric.distance))

        conn.close()

        # Sort by distance (lower = more similar)
        candidates.sort(key=lambda x: x[1])
        return candidates[:top_k]

    def abstract_state_space(self, states: List[BisimulationState],
                             goal: str, threshold: float = SIMILARITY_THRESHOLD
                             ) -> List[StateAbstraction]:
        """
        Group states into equivalence classes by bisimilarity.

        Uses greedy clustering: pick representative, add all bisimilar states.
        """
        abstractions = []
        assigned: Set[str] = set()

        # Sort states for deterministic clustering
        sorted_states = sorted(states, key=lambda s: s.state_id)

        for state in sorted_states:
            if state.state_id in assigned:
                continue

            # Start new class with this state as representative
            class_members = [state.state_id]
            distances = []

            for other in sorted_states:
                if other.state_id == state.state_id or other.state_id in assigned:
                    continue

                metric = self.compute_distance(state, other, goal)
                if metric.distance < threshold:
                    class_members.append(other.state_id)
                    distances.append(metric.distance)
                    assigned.add(other.state_id)

            assigned.add(state.state_id)

            # Compute cohesion (average internal distance)
            cohesion = sum(distances) / len(distances) if distances else 0.0

            abstraction = StateAbstraction(
                class_id=f"class_{hashlib.md5(state.state_id.encode()).hexdigest()[:8]}",
                representative_state=state.state_id,
                member_states=class_members,
                goal_context=goal,
                cohesion=cohesion
            )
            abstractions.append(abstraction)

        return abstractions

    def transfer_policy(self, source_state: str, source_goal: str,
                        target_state: str, target_goal: str) -> TransferResult:
        """
        Check if policy can transfer between state-goal pairs.

        Transfer is valid if:
        1. States are bisimilar under target goal
        2. Goals have similar structure (same prefix or type)
        3. Source state had successful outcome
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Load states
        cursor.execute("SELECT * FROM states WHERE state_id = ?", (source_state,))
        source_row = cursor.fetchone()

        cursor.execute("SELECT * FROM states WHERE state_id = ?", (target_state,))
        target_row = cursor.fetchone()

        if not source_row or not target_row:
            return TransferResult(
                source_state=source_state, source_goal=source_goal,
                target_state=target_state, target_goal=target_goal,
                transfer_valid=False, confidence=0.0,
                reasoning="State not found in database"
            )

        source = BisimulationState(
            state_id=source_row["state_id"],
            features=json.loads(source_row["features"]),
            goal_context=source_row["goal_context"],
            action_history=json.loads(source_row["action_history"]) if source_row["action_history"] else [],
            reward_history=json.loads(source_row["reward_history"]) if source_row["reward_history"] else []
        )

        target = BisimulationState(
            state_id=target_row["state_id"],
            features=json.loads(target_row["features"]),
            goal_context=target_row["goal_context"],
            action_history=json.loads(target_row["action_history"]) if target_row["action_history"] else [],
            reward_history=json.loads(target_row["reward_history"]) if target_row["reward_history"] else []
        )

        conn.close()

        # Check bisimilarity under target goal
        metric = self.compute_distance(source, target, target_goal)

        # Goal similarity (simple prefix match)
        goal_prefix_match = source_goal.split("_")[0] == target_goal.split("_")[0]

        # Source success (positive reward history)
        source_success = (
            sum(source.reward_history) > 0 if source.reward_history
            else True  # Assume success if no history
        )

        # Compute transfer confidence
        state_similarity = 1.0 - metric.distance
        goal_similarity = 1.0 if goal_prefix_match else 0.5
        success_factor = 1.0 if source_success else 0.3

        confidence = state_similarity * goal_similarity * success_factor

        # Transfer is valid if confidence > 0.5
        transfer_valid = confidence > 0.5

        reasoning_parts = []
        if metric.distance < SIMILARITY_THRESHOLD:
            reasoning_parts.append(f"States are bisimilar (d={metric.distance:.3f})")
        else:
            reasoning_parts.append(f"States differ (d={metric.distance:.3f})")

        if goal_prefix_match:
            reasoning_parts.append("Goals share structure")
        else:
            reasoning_parts.append("Goals differ in structure")

        if source_success:
            reasoning_parts.append("Source had positive outcome")
        else:
            reasoning_parts.append("Source had negative outcome")

        result = TransferResult(
            source_state=source_state,
            source_goal=source_goal,
            target_state=target_state,
            target_goal=target_goal,
            transfer_valid=transfer_valid,
            confidence=confidence,
            reasoning="; ".join(reasoning_parts)
        )

        # Log transfer attempt
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transfer_history
            (source_state, source_goal, target_state, target_goal,
             transfer_valid, confidence, reasoning, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            source_state, source_goal, target_state, target_goal,
            1 if transfer_valid else 0, confidence, result.reasoning,
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

        return result

    def store_state(self, state: BisimulationState):
        """Store state in database."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO states
            (state_id, features, goal_context, action_history, reward_history, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            state.state_id,
            json.dumps(state.features),
            state.goal_context,
            json.dumps(state.action_history),
            json.dumps(state.reward_history),
            state.timestamp
        ))
        conn.commit()
        conn.close()

    def get_transfer_stats(self) -> Dict[str, Any]:
        """Get statistics on policy transfer."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM transfer_history")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM transfer_history WHERE transfer_valid = 1")
        valid = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM transfer_history WHERE outcome_success = 1")
        successful = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(confidence) FROM transfer_history")
        avg_confidence = cursor.fetchone()[0] or 0.0

        conn.close()

        return {
            "total_attempts": total,
            "valid_transfers": valid,
            "successful_outcomes": successful,
            "transfer_rate": valid / total if total > 0 else 0.0,
            "success_rate": successful / valid if valid > 0 else 0.0,
            "avg_confidence": avg_confidence
        }

    def get_state_abstractions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get state abstraction classes for dashboard display."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT class_id, goal_context, member_states,
                   representative_state, cohesion, created_at
            FROM abstractions
            ORDER BY cohesion DESC
            LIMIT ?
        """, (limit,))

        abstractions = []
        for row in cursor.fetchall():
            member_states = json.loads(row[2]) if row[2] else []
            abstractions.append({
                "class_id": row[0],
                "goal": row[1],
                "members": len(member_states),
                "centroid": row[3],
                "cohesion": row[4] or 0.0,
                "created_at": row[5]
            })

        conn.close()
        return abstractions

    def get_recent_transfers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent policy transfer attempts for dashboard display."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT source_state, target_state, source_goal,
                   confidence, transfer_valid, confidence,
                   outcome_success, timestamp
            FROM transfer_history
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        transfers = []
        for row in cursor.fetchall():
            source = row[0] or ""
            target = row[1] or ""
            transfers.append({
                "source": source[:12] + "..." if len(source) > 12 else source,
                "target": target[:12] + "..." if len(target) > 12 else target,
                "goal": row[2],
                "distance": round(row[3], 3) if row[3] else 0.0,
                "valid": bool(row[4]),
                "confidence": round(row[5], 2) if row[5] else 0.0,
                "success": bool(row[6]) if row[6] is not None else None,
                "created_at": row[7]
            })

        conn.close()
        return transfers


# ============================================================================
# Integration with Coherence System
# ============================================================================

def state_from_coherence(goal_id: str, context: Dict[str, Any]) -> BisimulationState:
    """Create BisimulationState from coherence system context."""
    return BisimulationState(
        state_id=f"coh_{goal_id}_{hashlib.md5(json.dumps(context, sort_keys=True).encode()).hexdigest()[:8]}",
        features=context,
        goal_context=goal_id,
        action_history=context.get("recent_actions", []),
        reward_history=context.get("coherence_scores", [])
    )


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Bisimulation Engine")
    parser.add_argument("--compare", nargs=3, metavar=("STATE1", "STATE2", "GOAL"),
                        help="Compare two states for bisimilarity")
    parser.add_argument("--find-analogies", nargs=2, metavar=("STATE", "GOAL"),
                        help="Find analogous states")
    parser.add_argument("--stats", action="store_true", help="Show transfer statistics")
    parser.add_argument("--test", action="store_true", help="Run test with sample states")

    args = parser.parse_args()

    engine = BisimulationEngine()

    if args.compare:
        s1_id, s2_id, goal = args.compare
        # Would load from DB in real usage
        print(f"Comparing {s1_id} and {s2_id} for goal {goal}")
        print("(States must exist in database)")

    elif args.find_analogies:
        state_id, goal = args.find_analogies
        print(f"Finding analogies for {state_id} under goal {goal}")
        print("(State must exist in database)")

    elif args.stats:
        stats = engine.get_transfer_stats()
        print("\nPolicy Transfer Statistics:")
        print(f"  Total attempts: {stats['total_attempts']}")
        print(f"  Valid transfers: {stats['valid_transfers']}")
        print(f"  Transfer rate: {stats['transfer_rate']:.1%}")
        print(f"  Success rate: {stats['success_rate']:.1%}")
        print(f"  Avg confidence: {stats['avg_confidence']:.2f}")

    elif args.test:
        print("Running bisimulation test...\n")

        # Create sample states
        s1 = BisimulationState(
            state_id="test_state_1",
            features={"files_modified": 3, "tests_passing": True, "complexity": 0.7},
            goal_context="implement_feature",
            action_history=["read_file", "edit_file", "run_tests"],
            reward_history=[0.5, 0.8, 1.0]
        )

        s2 = BisimulationState(
            state_id="test_state_2",
            features={"files_modified": 2, "tests_passing": True, "complexity": 0.6},
            goal_context="implement_feature",
            action_history=["read_file", "edit_file", "run_tests"],
            reward_history=[0.4, 0.7, 0.9]
        )

        s3 = BisimulationState(
            state_id="test_state_3",
            features={"files_modified": 10, "tests_passing": False, "complexity": 0.9},
            goal_context="refactor_code",
            action_history=["grep", "read_file", "write_file"],
            reward_history=[0.2, 0.3, 0.1]
        )

        # Store states
        engine.store_state(s1)
        engine.store_state(s2)
        engine.store_state(s3)

        # Compute distances
        d12 = engine.compute_distance(s1, s2, "implement_feature")
        d13 = engine.compute_distance(s1, s3, "implement_feature")

        print(f"Distance(s1, s2) = {d12.distance:.3f}")
        print(f"  Components: {d12.components}")
        print(f"  Bisimilar: {d12.distance < SIMILARITY_THRESHOLD}")
        print()

        print(f"Distance(s1, s3) = {d13.distance:.3f}")
        print(f"  Components: {d13.components}")
        print(f"  Bisimilar: {d13.distance < SIMILARITY_THRESHOLD}")
        print()

        # Test abstraction
        abstractions = engine.abstract_state_space([s1, s2, s3], "implement_feature")
        print(f"Abstraction classes: {len(abstractions)}")
        for ab in abstractions:
            print(f"  {ab.class_id}: {len(ab.member_states)} states, cohesion={ab.cohesion:.3f}")

        # Test transfer
        transfer = engine.transfer_policy("test_state_1", "implement_feature",
                                          "test_state_2", "implement_feature")
        print(f"\nTransfer test_state_1 -> test_state_2:")
        print(f"  Valid: {transfer.transfer_valid}")
        print(f"  Confidence: {transfer.confidence:.2f}")
        print(f"  Reasoning: {transfer.reasoning}")


if __name__ == "__main__":
    main()
