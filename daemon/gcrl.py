#!/usr/bin/env python3
"""
Goal-Conditioned Reinforcement Learning (GCRL) Engine.

Phase 12.2: Implements GCRL patterns for:
1. Goal-conditioned policy learning
2. Hindsight Experience Replay (HER) - learn from failures
3. Virtual experience generation
4. Causal factor extraction

Based on:
- "GCHR: Goal-Conditioned Hindsight Regularization"
- "Generalizing Goal-Conditioned RL with Variational Causal Reasoning"

Usage:
    python gcrl.py --relabel trajectory.json
    python gcrl.py --policy state goal
    python gcrl.py --stats
"""

import os
import json
import sqlite3
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ============================================================================
# Configuration
# ============================================================================

DB_PATH = Path(__file__).parent / "gcrl.db"

# GCRL parameters
HINDSIGHT_RATIO = 0.5  # Fraction of failed trajectories to relabel
SIMILARITY_THRESHOLD = 0.5  # Goal similarity for relabeling
MAX_TRAJECTORY_LENGTH = 100  # Maximum steps in trajectory

# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class Goal:
    """Structured goal representation."""
    goal_id: str
    description: str
    success_criteria: List[str]  # What defines success
    causal_factors: List[str] = field(default_factory=list)  # What causes success
    preconditions: List[str] = field(default_factory=list)  # Required starting conditions
    goal_type: str = "task"  # task, constraint, preference
    priority: float = 1.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class State:
    """State in a trajectory."""
    state_id: str
    features: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class Trajectory:
    """Sequence of state-action-reward tuples."""
    trajectory_id: str
    states: List[Dict[str, Any]]
    actions: List[str]
    rewards: List[float]
    intended_goal: str
    achieved_goal: Optional[str] = None  # For hindsight relabeling
    success: bool = False
    causal_factors: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class Policy:
    """Learned policy for goal achievement."""
    policy_id: str
    goal_pattern: str  # Pattern this policy applies to
    action_sequence: List[str]  # Recommended actions
    success_rate: float
    sample_count: int
    causal_factors: List[str] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class CausalFactor:
    """Factor that influences goal achievement."""
    factor_id: str
    name: str
    effect_type: str  # necessary, sufficient, contributing
    strength: float  # 0-1, how strongly it influences outcome
    goals_affected: List[str] = field(default_factory=list)
    evidence_count: int = 0

# ============================================================================
# Database
# ============================================================================

def init_db():
    """Initialize GCRL database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            goal_id TEXT PRIMARY KEY,
            description TEXT,
            success_criteria TEXT,
            causal_factors TEXT,
            preconditions TEXT,
            goal_type TEXT,
            priority REAL,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trajectories (
            trajectory_id TEXT PRIMARY KEY,
            states TEXT,
            actions TEXT,
            rewards TEXT,
            intended_goal TEXT,
            achieved_goal TEXT,
            success INTEGER,
            causal_factors TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS policies (
            policy_id TEXT PRIMARY KEY,
            goal_pattern TEXT,
            action_sequence TEXT,
            success_rate REAL,
            sample_count INTEGER,
            causal_factors TEXT,
            updated_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS causal_factors (
            factor_id TEXT PRIMARY KEY,
            name TEXT,
            effect_type TEXT,
            strength REAL,
            goals_affected TEXT,
            evidence_count INTEGER
        )
    """)

    conn.commit()
    conn.close()

# ============================================================================
# GCRL Engine
# ============================================================================

class GoalConditionedLearner:
    """Goal-conditioned learning with hindsight and virtual experiences."""

    def __init__(self):
        init_db()
        self.policies: Dict[str, Policy] = {}
        self._load_policies()

    def _load_policies(self):
        """Load policies from database."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM policies")
        for row in cursor.fetchall():
            policy = Policy(
                policy_id=row["policy_id"],
                goal_pattern=row["goal_pattern"],
                action_sequence=json.loads(row["action_sequence"]),
                success_rate=row["success_rate"],
                sample_count=row["sample_count"],
                causal_factors=json.loads(row["causal_factors"]) if row["causal_factors"] else [],
                updated_at=row["updated_at"]
            )
            self.policies[policy.goal_pattern] = policy
        conn.close()

    def store_goal(self, goal: Goal):
        """Store goal in database."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO goals
            (goal_id, description, success_criteria, causal_factors,
             preconditions, goal_type, priority, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            goal.goal_id, goal.description,
            json.dumps(goal.success_criteria),
            json.dumps(goal.causal_factors),
            json.dumps(goal.preconditions),
            goal.goal_type, goal.priority, goal.created_at
        ))
        conn.commit()
        conn.close()

    def store_trajectory(self, trajectory: Trajectory):
        """Store trajectory for learning."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO trajectories
            (trajectory_id, states, actions, rewards, intended_goal,
             achieved_goal, success, causal_factors, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trajectory.trajectory_id,
            json.dumps(trajectory.states),
            json.dumps(trajectory.actions),
            json.dumps(trajectory.rewards),
            trajectory.intended_goal,
            trajectory.achieved_goal,
            1 if trajectory.success else 0,
            json.dumps(trajectory.causal_factors),
            trajectory.created_at
        ))
        conn.commit()
        conn.close()

        # Update policy if successful
        if trajectory.success:
            self._update_policy(trajectory)

    def hindsight_relabel(self, trajectory: Trajectory) -> Optional[Trajectory]:
        """
        If trajectory failed to reach intended goal, find what goal
        it DID achieve and relabel accordingly.

        HER Algorithm:
        1. Detect failure (success=False)
        2. Analyze final state
        3. Find matching goal for achieved state
        4. Create relabeled trajectory with achieved goal
        """
        if trajectory.success:
            return None  # No relabeling needed

        if not trajectory.states:
            return None

        # Analyze final state to determine achieved goal
        final_state = trajectory.states[-1]
        achieved_goal = self._infer_achieved_goal(final_state, trajectory.actions)

        if not achieved_goal or achieved_goal == trajectory.intended_goal:
            return None  # Could not find different achieved goal

        # Create relabeled trajectory
        relabeled = Trajectory(
            trajectory_id=f"{trajectory.trajectory_id}_her",
            states=trajectory.states,
            actions=trajectory.actions,
            rewards=self._recompute_rewards(trajectory.states, achieved_goal),
            intended_goal=achieved_goal,  # Relabeled!
            achieved_goal=achieved_goal,
            success=True,  # Now it's a success!
            causal_factors=self._extract_causal_factors(trajectory, achieved_goal),
            created_at=datetime.now().isoformat()
        )

        return relabeled

    def _infer_achieved_goal(self, final_state: Dict[str, Any],
                             actions: List[str]) -> Optional[str]:
        """Infer what goal was achieved based on final state."""
        # Load all goals and check which ones match final state
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM goals")

        best_match = None
        best_score = 0.0

        for row in cursor.fetchall():
            criteria = json.loads(row["success_criteria"])
            score = self._check_criteria_match(final_state, criteria, actions)
            if score > best_score and score > 0.5:  # Threshold
                best_score = score
                best_match = row["goal_id"]

        conn.close()

        # If no existing goal matches, create synthetic goal from state
        if not best_match:
            best_match = self._create_synthetic_goal(final_state)

        return best_match

    def _check_criteria_match(self, state: Dict[str, Any],
                              criteria: List[str], actions: List[str]) -> float:
        """Check how well state matches success criteria."""
        if not criteria:
            return 0.0

        matches = 0
        for criterion in criteria:
            criterion_lower = criterion.lower()
            # Simple keyword matching
            for key, value in state.items():
                if key.lower() in criterion_lower:
                    matches += 1
                    break
            # Check if actions mention criterion
            for action in actions:
                if any(word in action.lower() for word in criterion_lower.split()):
                    matches += 0.5
                    break

        return matches / len(criteria)

    def _create_synthetic_goal(self, state: Dict[str, Any]) -> str:
        """Create synthetic goal from achieved state."""
        # Generate goal ID from state features
        state_hash = hashlib.md5(json.dumps(state, sort_keys=True).encode()).hexdigest()[:8]
        goal_id = f"synthetic_{state_hash}"

        # Create goal based on state features
        criteria = []
        for key, value in state.items():
            if isinstance(value, bool) and value:
                criteria.append(f"{key} is true")
            elif isinstance(value, (int, float)) and value > 0:
                criteria.append(f"{key} > 0")

        goal = Goal(
            goal_id=goal_id,
            description=f"Synthetic goal from state {state_hash}",
            success_criteria=criteria[:5],  # Limit criteria
            goal_type="synthetic"
        )

        self.store_goal(goal)
        return goal_id

    def _recompute_rewards(self, states: List[Dict[str, Any]],
                           new_goal: str) -> List[float]:
        """Recompute rewards for relabeled trajectory."""
        # Simple: reward 1.0 for reaching goal, 0 otherwise
        rewards = [0.0] * (len(states) - 1)
        rewards.append(1.0)  # Final state achieved the goal
        return rewards

    def _extract_causal_factors(self, trajectory: Trajectory,
                                goal: str) -> List[str]:
        """Extract causal factors from successful trajectory."""
        factors = []

        # Actions that appear in successful trajectories are potential causal factors
        action_counts = defaultdict(int)
        for action in trajectory.actions:
            action_counts[action] += 1

        # Frequent actions are more likely causal
        for action, count in sorted(action_counts.items(), key=lambda x: -x[1]):
            if count >= 2:
                factors.append(f"action:{action}")

        # State features that changed are potential causes
        if len(trajectory.states) >= 2:
            first_state = trajectory.states[0]
            last_state = trajectory.states[-1]
            for key in set(first_state.keys()) | set(last_state.keys()):
                if first_state.get(key) != last_state.get(key):
                    factors.append(f"state_change:{key}")

        return factors[:10]  # Limit factors

    def _update_policy(self, trajectory: Trajectory):
        """Update policy based on successful trajectory."""
        goal_pattern = trajectory.achieved_goal or trajectory.intended_goal

        if goal_pattern in self.policies:
            policy = self.policies[goal_pattern]
            # Update success rate with moving average
            policy.success_rate = (
                policy.success_rate * policy.sample_count + 1.0
            ) / (policy.sample_count + 1)
            policy.sample_count += 1

            # Merge causal factors
            existing_factors = set(policy.causal_factors)
            new_factors = set(trajectory.causal_factors)
            policy.causal_factors = list(existing_factors | new_factors)[:20]

            policy.updated_at = datetime.now().isoformat()
        else:
            # Create new policy
            policy = Policy(
                policy_id=f"policy_{goal_pattern}",
                goal_pattern=goal_pattern,
                action_sequence=trajectory.actions,
                success_rate=1.0,
                sample_count=1,
                causal_factors=trajectory.causal_factors
            )
            self.policies[goal_pattern] = policy

        # Save to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO policies
            (policy_id, goal_pattern, action_sequence, success_rate,
             sample_count, causal_factors, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            policy.policy_id, policy.goal_pattern,
            json.dumps(policy.action_sequence),
            policy.success_rate, policy.sample_count,
            json.dumps(policy.causal_factors),
            policy.updated_at
        ))
        conn.commit()
        conn.close()

    def policy_for_goal(self, current_state: Dict[str, Any],
                        goal: Goal) -> Optional[Policy]:
        """Return policy recommendation for achieving goal from state."""
        # Exact match
        if goal.goal_id in self.policies:
            return self.policies[goal.goal_id]

        # Pattern match (prefix)
        goal_prefix = goal.goal_id.split("_")[0]
        for pattern, policy in self.policies.items():
            if pattern.startswith(goal_prefix):
                return policy

        # Type match
        for pattern, policy in self.policies.items():
            if goal.goal_type in pattern:
                return policy

        return None

    def generate_virtual_experience(self, goal: Goal,
                                    start_state: Dict[str, Any]) -> Optional[Trajectory]:
        """
        Generate imagined trajectory to goal using learned policies.

        Virtual Experience Algorithm:
        1. Get policy for goal
        2. Simulate trajectory using policy actions
        3. Estimate rewards based on goal proximity
        """
        policy = self.policy_for_goal(start_state, goal)
        if not policy:
            return None

        # Generate virtual trajectory
        states = [start_state]
        actions = []
        rewards = []

        current_state = start_state.copy()
        for action in policy.action_sequence[:MAX_TRAJECTORY_LENGTH]:
            # Simulate action effect (simple: increment counter)
            actions.append(action)
            current_state = self._simulate_action(current_state, action)
            states.append(current_state)

            # Estimate reward (proximity to goal)
            reward = self._estimate_goal_proximity(current_state, goal)
            rewards.append(reward)

        trajectory = Trajectory(
            trajectory_id=f"virtual_{goal.goal_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            states=states,
            actions=actions,
            rewards=rewards,
            intended_goal=goal.goal_id,
            achieved_goal=goal.goal_id if rewards and rewards[-1] > 0.8 else None,
            success=rewards[-1] > 0.8 if rewards else False,
            causal_factors=policy.causal_factors
        )

        return trajectory

    def _simulate_action(self, state: Dict[str, Any], action: str) -> Dict[str, Any]:
        """Simulate effect of action on state."""
        new_state = state.copy()

        # Simple simulation: track action counts
        action_key = f"action_{action}_count"
        new_state[action_key] = new_state.get(action_key, 0) + 1

        # Update progress indicator
        new_state["progress"] = min(new_state.get("progress", 0) + 0.1, 1.0)

        return new_state

    def _estimate_goal_proximity(self, state: Dict[str, Any], goal: Goal) -> float:
        """Estimate how close state is to goal achievement."""
        if not goal.success_criteria:
            return state.get("progress", 0.0)

        matches = 0
        for criterion in goal.success_criteria:
            for key, value in state.items():
                if key.lower() in criterion.lower():
                    if isinstance(value, bool) and value:
                        matches += 1
                    elif isinstance(value, (int, float)) and value > 0:
                        matches += 0.5
                    break

        return min(matches / len(goal.success_criteria), 1.0)

    def get_stats(self) -> Dict[str, Any]:
        """Get GCRL learning statistics."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM goals")
        goal_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM trajectories")
        trajectory_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM trajectories WHERE success = 1")
        success_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM trajectories WHERE achieved_goal != intended_goal AND achieved_goal IS NOT NULL")
        relabeled_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM policies")
        policy_count = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(success_rate) FROM policies")
        avg_success_rate = cursor.fetchone()[0] or 0.0

        conn.close()

        return {
            "goals": goal_count,
            "trajectories": trajectory_count,
            "successful": success_count,
            "relabeled": relabeled_count,
            "policies": policy_count,
            "avg_policy_success_rate": avg_success_rate,
            "hindsight_ratio": relabeled_count / trajectory_count if trajectory_count > 0 else 0.0
        }


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="GCRL Engine")
    parser.add_argument("--stats", action="store_true", help="Show learning statistics")
    parser.add_argument("--test", action="store_true", help="Run test with sample data")
    parser.add_argument("--policies", action="store_true", help="List learned policies")

    args = parser.parse_args()

    learner = GoalConditionedLearner()

    if args.stats:
        stats = learner.get_stats()
        print("\nGCRL Statistics:")
        print(f"  Goals: {stats['goals']}")
        print(f"  Trajectories: {stats['trajectories']}")
        print(f"  Successful: {stats['successful']}")
        print(f"  Relabeled (HER): {stats['relabeled']}")
        print(f"  Policies: {stats['policies']}")
        print(f"  Avg Policy Success Rate: {stats['avg_policy_success_rate']:.1%}")
        print(f"  Hindsight Ratio: {stats['hindsight_ratio']:.1%}")

    elif args.policies:
        print("\nLearned Policies:")
        for pattern, policy in learner.policies.items():
            print(f"\n  {pattern}:")
            print(f"    Success Rate: {policy.success_rate:.1%}")
            print(f"    Samples: {policy.sample_count}")
            print(f"    Actions: {policy.action_sequence[:5]}...")
            if policy.causal_factors:
                print(f"    Causal Factors: {policy.causal_factors[:3]}...")

    elif args.test:
        print("Running GCRL test...\n")

        # Create test goal
        goal = Goal(
            goal_id="implement_feature",
            description="Implement a new feature",
            success_criteria=["tests passing", "code reviewed", "merged to main"],
            causal_factors=["write_tests", "refactor"],
            preconditions=["branch created"]
        )
        learner.store_goal(goal)

        # Create successful trajectory
        success_traj = Trajectory(
            trajectory_id="traj_001",
            states=[
                {"branch": "feature-1", "tests": 0, "files_changed": 0},
                {"branch": "feature-1", "tests": 5, "files_changed": 3},
                {"branch": "feature-1", "tests": 5, "files_changed": 5, "reviewed": True}
            ],
            actions=["write_code", "write_tests", "request_review"],
            rewards=[0.3, 0.6, 1.0],
            intended_goal="implement_feature",
            success=True
        )
        success_traj.causal_factors = learner._extract_causal_factors(success_traj, "implement_feature")
        learner.store_trajectory(success_traj)

        print(f"Stored successful trajectory: {success_traj.trajectory_id}")
        print(f"  Causal factors: {success_traj.causal_factors}")

        # Create failed trajectory for HER
        failed_traj = Trajectory(
            trajectory_id="traj_002",
            states=[
                {"branch": "feature-2", "tests": 0, "files_changed": 0},
                {"branch": "feature-2", "tests": 0, "files_changed": 10},
                {"branch": "feature-2", "tests": 0, "files_changed": 15, "refactored": True}
            ],
            actions=["write_code", "refactor", "more_refactor"],
            rewards=[0.1, 0.2, 0.3],
            intended_goal="implement_feature",
            success=False
        )

        print(f"\nAttempting hindsight relabeling for: {failed_traj.trajectory_id}")

        # Store a goal that matches the achieved state
        refactor_goal = Goal(
            goal_id="refactor_code",
            description="Refactor existing code",
            success_criteria=["refactored", "files_changed > 10"],
            goal_type="task"
        )
        learner.store_goal(refactor_goal)

        # Relabel
        relabeled = learner.hindsight_relabel(failed_traj)
        if relabeled:
            learner.store_trajectory(relabeled)
            print(f"  Relabeled as: {relabeled.achieved_goal}")
            print(f"  New success: {relabeled.success}")
        else:
            print("  Could not relabel")

        # Get policy recommendation
        policy = learner.policy_for_goal({}, goal)
        if policy:
            print(f"\nPolicy for {goal.goal_id}:")
            print(f"  Actions: {policy.action_sequence}")
            print(f"  Success rate: {policy.success_rate:.1%}")

        # Generate virtual experience
        print("\nGenerating virtual experience...")
        virtual = learner.generate_virtual_experience(goal, {"branch": "new-feature"})
        if virtual:
            print(f"  Trajectory: {virtual.trajectory_id}")
            print(f"  Actions: {virtual.actions}")
            print(f"  Final reward: {virtual.rewards[-1] if virtual.rewards else 0:.2f}")
            print(f"  Success: {virtual.success}")

        # Show stats
        stats = learner.get_stats()
        print(f"\nFinal stats: {stats}")


if __name__ == "__main__":
    main()
