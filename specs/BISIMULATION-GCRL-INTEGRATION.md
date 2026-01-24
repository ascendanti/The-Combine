# Bisimulation & Goal-Conditioned RL Integration Spec

## Executive Summary

This specification outlines how findings from research papers on bisimulation, goal-conditioned reinforcement learning (GCRL), and behavior-based state abstraction will be integrated into the Claude autonomous system architecture.

---

## 1. Bisimulation for Goal-Conditioned Learning

### 1.1 Core Concept

**Bisimulation** defines when two states are behaviorally equivalent - they produce the same observations and transitions under any policy. In GCRL, this enables:

1. **Analogical Transfer**: If state A is bisimilar to state B relative to goal G, apply the same policy
2. **State Abstraction**: Group bisimilar states to reduce complexity
3. **Goal Similarity**: Measure distance between goals based on required behavior changes

### 1.2 Mathematical Foundation

For MDP M = (S, A, P, R, γ), bisimulation metric d:

```
d(s1, s2) = max_a [ |R(s1,a) - R(s2,a)| + γ * W(P(s1,a), P(s2,a), d) ]
```

Where W is the Wasserstein distance over next-state distributions.

### 1.3 Implementation: daemon/bisimulation.py

```python
@dataclass
class BisimulationState:
    """State representation for bisimulation analysis."""
    state_id: str
    features: Dict[str, Any]  # Observable features
    goal_context: str         # Current goal being pursued
    action_history: List[str] # Recent actions taken

@dataclass
class BisimulationMetric:
    """Distance between two states under bisimulation."""
    state_a: str
    state_b: str
    distance: float           # 0 = bisimilar, higher = more different
    goal_context: str         # Goal-specific bisimilarity

class BisimulationEngine:
    """Compute and cache bisimulation metrics."""

    def compute_distance(self, s1: BisimulationState, s2: BisimulationState,
                         goal: str) -> float:
        """Compute goal-conditioned bisimulation distance."""

    def find_analogies(self, current_state: BisimulationState,
                       goal: str) -> List[Tuple[BisimulationState, float]]:
        """Find states bisimilar to current state for given goal."""

    def abstract_state_space(self, states: List[BisimulationState],
                             threshold: float) -> Dict[str, List[str]]:
        """Group states into equivalence classes by bisimilarity."""

    def transfer_policy(self, source_state: str, source_goal: str,
                        target_state: str, target_goal: str) -> Optional[str]:
        """Check if policy can transfer between state-goal pairs."""
```

### 1.4 Integration Points

| Existing Component | Integration |
|--------------------|-------------|
| daemon/coherence.py | Goal hierarchy provides goal contexts for bisimulation |
| daemon/decisions.py | Use bisimulation to find similar past decisions |
| daemon/memory.py | Store bisimulation-based state abstractions |
| continuous-learning skill | Learn bisimulation metrics from experience |

---

## 2. Goal-Conditioned Reinforcement Learning (GCRL)

### 2.1 Core Concepts from Papers

#### From "Bisimulation Makes Analogies in GCRL":
- Goals can be treated as part of state for bisimulation
- State-goal pairs are bisimilar if they require same behavior
- Enables zero-shot transfer to new goals

#### From "GCHR - Hindsight Regularization":
- When goal is missed, relabel trajectory with achieved goal
- Regularize policy to be consistent across similar goals
- Improves sample efficiency

#### From "Variational Causal Reasoning":
- Extract causal factors that determine goal achievement
- Use causal structure for generalization
- Identify necessary vs. sufficient conditions

#### From "Virtual Experiences":
- Augment learning with imagined goal-reaching trajectories
- Use world model to generate synthetic experiences
- Particularly useful for rare goals

### 2.2 Implementation: daemon/gcrl.py

```python
@dataclass
class Goal:
    """Structured goal representation."""
    goal_id: str
    description: str
    success_criteria: List[str]     # What defines success
    causal_factors: List[str]       # What causes success
    preconditions: List[str]        # Required starting conditions

@dataclass
class Trajectory:
    """Sequence of state-action-reward tuples."""
    trajectory_id: str
    states: List[Dict]
    actions: List[str]
    rewards: List[float]
    intended_goal: str
    achieved_goal: Optional[str]    # For hindsight relabeling

class GoalConditionedLearner:
    """Goal-conditioned learning with hindsight and virtual experiences."""

    def hindsight_relabel(self, trajectory: Trajectory) -> Trajectory:
        """
        If trajectory failed to reach intended goal, find what goal
        it DID achieve and relabel accordingly.
        """

    def extract_causal_factors(self, successful_trajectories: List[Trajectory],
                                goal: Goal) -> List[str]:
        """
        Identify causal factors that led to goal achievement.
        Uses variational inference over action sequences.
        """

    def generate_virtual_experience(self, goal: Goal,
                                     world_model: Any) -> Trajectory:
        """
        Generate imagined trajectory to goal using world model.
        Used to augment learning for rare goals.
        """

    def policy_for_goal(self, current_state: Dict, goal: Goal) -> str:
        """
        Return action recommendation for achieving goal from state.
        Uses learned goal-conditioned policy.
        """
```

### 2.3 Hindsight Relabeling Algorithm

```
Algorithm: Hindsight Experience Relabeling (HER)
Input: Failed trajectory T reaching state s_final instead of goal g
Output: Relabeled trajectory T' for goal g' = s_final

1. Compute bisimulation distance d = bisim(g, s_final)
2. If d < threshold:
   - T' = T with goal relabeled to g' = s_final
   - Store (T', reward=success) in memory
3. Else:
   - Find intermediate state s_i in T closest to g
   - T' = T[:i] with goal relabeled to s_i
   - Store (T', reward=partial_success)
4. Return T'
```

---

## 3. Behavior-Based State Abstraction

### 3.1 Core Concept

Instead of abstracting states by features, abstract by behavior:
- Two states are equivalent if optimal behavior is the same
- Allows more aggressive compression than feature-based abstraction
- Naturally goal-conditioned (behavior depends on goal)

### 3.2 Implementation Strategy

```python
class BehaviorAbstraction:
    """Abstract states by behavioral equivalence."""

    def behavioral_signature(self, state: Dict, goal: str) -> str:
        """
        Compute behavioral signature for state-goal pair.
        Signature encodes what actions would be taken.
        """
        policy = self.gcrl.policy_for_goal(state, goal)
        return f"{policy.action}|{policy.confidence}|{goal}"

    def abstract_to_behavior_class(self, states: List[Dict],
                                    goal: str) -> Dict[str, List[Dict]]:
        """Group states by behavioral signature."""
        classes = defaultdict(list)
        for state in states:
            sig = self.behavioral_signature(state, goal)
            classes[sig].append(state)
        return classes
```

---

## 4. MDP Formalization for Claude System

### 4.1 State Space

Claude's state includes:
- Current task/goal being pursued
- Context window contents (abstracted)
- Tool usage history
- User preferences learned
- Session state (files modified, commits made, etc.)

### 4.2 Action Space

Actions are tool invocations:
- Read/Write/Edit files
- Bash commands
- Task delegation to agents
- Memory operations
- Goal updates

### 4.3 Reward Signal

Derived from:
- Task completion (explicit)
- User feedback (explicit)
- Coherence scores (implicit)
- Decision outcome tracking (implicit)

### 4.4 Goal Space

Goals from daemon/coherence.py:
- Hierarchical (root → sub-goals)
- Time-bounded (immediate, session, long-term)
- Constraint-aware (resources, permissions)

---

## 5. Integration Architecture

```
                    ┌─────────────────────────────────┐
                    │      User Goals (coherence.py)   │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │   Bisimulation State Abstraction │
                    │        (bisimulation.py)         │
                    └──────────────┬──────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
    ┌─────────▼─────────┐ ┌───────▼────────┐ ┌────────▼────────┐
    │ Find Analogies    │ │ Policy Lookup  │ │ Transfer Check  │
    │ (similar states)  │ │ (memory.py)    │ │ (can reuse?)    │
    └─────────┬─────────┘ └───────┬────────┘ └────────┬────────┘
              │                    │                    │
              └────────────────────┼────────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │   Goal-Conditioned Policy       │
                    │         (gcrl.py)               │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │      Action Selection           │
                    │      (decisions.py)             │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │   Outcome → Hindsight Learning  │
                    │   (update bisimulation metrics) │
                    └─────────────────────────────────┘
```

---

## 6. Implementation Phases

### Phase 12.1.1: Bisimulation Foundation (Week 1-2)
- [ ] Create daemon/bisimulation.py with BisimulationState and metrics
- [ ] Integrate with coherence.py goal hierarchy
- [ ] Add state serialization for bisimulation computation
- [ ] Unit tests for bisimulation distance

### Phase 12.1.2: Analogy Finding (Week 2-3)
- [ ] Implement find_analogies() with memory.py integration
- [ ] Add caching for computed bisimulation metrics
- [ ] Create CLI for testing analogy queries
- [ ] Integration tests with real goal scenarios

### Phase 12.1.3: Policy Transfer (Week 3-4)
- [ ] Implement transfer_policy() logic
- [ ] Add transfer success tracking to decisions.py
- [ ] Measure transfer effectiveness metrics
- [ ] Dashboard visualization of transfer rates

### Phase 12.2.1: GCRL Core (Week 4-5)
- [ ] Create daemon/gcrl.py with Goal and Trajectory classes
- [ ] Implement hindsight_relabel() algorithm
- [ ] Integrate with memory.py for trajectory storage
- [ ] Add goal achievement detection

### Phase 12.2.2: Virtual Experiences (Week 5-6)
- [ ] Implement generate_virtual_experience() with world model
- [ ] Add virtual experience validation
- [ ] Integrate with learning loop
- [ ] Measure sample efficiency improvements

---

## 7. Evaluation Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| Transfer Rate | % of goals where prior solution transferred | >30% |
| Abstraction Ratio | # abstract states / # concrete states | >5:1 |
| Hindsight Improvement | Learning speed with vs. without HER | >2x |
| Goal Success Rate | % of stated goals achieved | >80% |
| Analogy Precision | % of suggested analogies that helped | >50% |

---

## 8. Research Paper References

1. **Bisimulation Makes Analogies in Goal-Conditioned Reinforcement Learning**
   - Key: Goal-conditioned bisimulation metrics enable analogical transfer

2. **GCHR: Goal-Conditioned Hindsight Regularization**
   - Key: Regularize policies to be consistent across similar goals

3. **Generalizing Goal-Conditioned RL with Variational Causal Reasoning**
   - Key: Extract causal factors for goal achievement

4. **Goal-Conditioned RL: Problems and Solutions**
   - Key: Survey of GCRL challenges and approaches

5. **Bounded Rationality, Abstraction, and Hierarchical Decision-Making**
   - Key: Information-theoretic foundation for abstraction

---

## 9. Dependencies

- daemon/coherence.py (goal hierarchy)
- daemon/decisions.py (outcome tracking)
- daemon/memory.py (trajectory storage)
- daemon/metacognition.py (capability assessment)
- specs/UTF-RESEARCH-OS-SPEC.md (knowledge extraction)
