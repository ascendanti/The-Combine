# Missing Layers Analysis

*What the system needs to be truly self-sustaining*

---

## Current Layers (What Exists)

```
Layer 5: OVERSIGHT     │ system_overseer.py (just created)
Layer 4: STRATEGY      │ strategy_evolution, outcome_tracker
Layer 3: COGNITIVE     │ decisions, coherence, metacognition, memory
Layer 2: PROCESSING    │ autonomous_ingest, synthesis, kg_summary
Layer 1: INFRASTRUCTURE│ LocalAI, Dragonfly, Docker, PostgreSQL
```

---

## Missing Layers

### Layer 6: SELF-HEALING (Missing)

**What it does:** Automatically fixes detected issues

**Current gap:**
- system_overseer DETECTS but doesn't FIX
- Errors are logged but not resolved
- Human intervention required for every issue

**Needs:**
```python
# auto_healer.py
def heal(issue: ReviewResult):
    if issue.category == "spec_linking":
        # Auto-add spec to RESOURCE-MAP.md
        add_to_resource_map(issue.data["spec_name"])

    elif issue.category == "db_fragmentation":
        # Auto-archive old DBs
        archive_old_databases(days=30)

    elif issue.category == "task_staleness":
        # Auto-update task.md with last activity
        refresh_task_md()
```

---

### Layer 7: GOAL MEASUREMENT (Missing)

**What it does:** Tracks progress against PRIME-DIRECTIVE goals

**Current gap:**
- PRIME-DIRECTIVE exists but not measured
- No KPIs being tracked
- No feedback on whether we're succeeding

**Needs:**
```python
# goal_tracker.py

GOALS = {
    "business": {"target": "revenue_pipeline", "kpi": "leads_generated"},
    "knowledge": {"target": "papers_processed", "kpi": "claims_extracted"},
    "insight": {"target": "patterns_found", "kpi": "cross_doc_connections"},
    "strategy": {"target": "strategies_evolved", "kpi": "success_rate"},
}

def measure_progress():
    for domain, config in GOALS.items():
        current = get_metric(config["kpi"])
        target = get_target(config["target"])
        progress = current / target if target else 0
        log_progress(domain, progress)
```

---

### Layer 8: RESOURCE ACCOUNTING (Missing)

**What it does:** Tracks cost/benefit of every operation

**Current gap:**
- No cost tracking (API calls, tokens, compute)
- No benefit measurement (value generated)
- Can't optimize ROI

**Needs:**
```python
# resource_accountant.py

def track_operation(operation: str, cost: dict, benefit: dict):
    """
    cost = {"tokens": 1000, "api_calls": 1, "compute_sec": 5}
    benefit = {"claims_extracted": 10, "patterns_found": 2}
    """
    roi = calculate_roi(cost, benefit)
    if roi < THRESHOLD:
        suggest_optimization(operation)
```

---

### Layer 9: DEPENDENCY GRAPH (Missing)

**What it does:** Knows which modules depend on which

**Current gap:**
- Modules are independent silos
- Changes can break other modules unknowingly
- No impact analysis before changes

**Needs:**
```python
# dependency_graph.py

DEPENDENCIES = {
    "autonomous_ingest": ["utf_extractor", "telegram_notify", "model_router"],
    "strategy_evolution": ["outcome_tracker", "model_router"],
    "synthesis_worker": ["kg_summary_worker", "claim_similarity"],
}

def impact_analysis(module: str) -> List[str]:
    """Return all modules affected by changing this module."""
    return get_dependents(module, recursive=True)
```

---

### Layer 10: DRIFT DETECTION (Missing)

**What it does:** Detects when modules diverge from intended behavior

**Current gap:**
- No baseline behavior defined
- No alerts when behavior changes
- Silent failures

**Needs:**
```python
# drift_detector.py

BASELINES = {
    "autonomous_ingest": {"avg_time": 30, "success_rate": 0.95},
    "model_router": {"localai_ratio": 0.7, "claude_ratio": 0.1},
}

def check_drift():
    for module, baseline in BASELINES.items():
        current = get_current_metrics(module)
        drift = calculate_drift(current, baseline)
        if drift > THRESHOLD:
            alert(f"{module} drifting: {drift}")
```

---

## Missing Processes

### 1. Feedback Consolidation Loop

**Gap:** Outcomes don't flow back to inform strategy

```
Current:  Action → Outcome → (logged but ignored)
Needed:   Action → Outcome → Pattern Analysis → Strategy Update → Better Actions
```

**Needs:**
```python
# Every N outcomes, run:
patterns = outcome_tracker.analyze_patterns()
strategy_evolution.incorporate_patterns(patterns)
coherence.update_goals(patterns)
```

---

### 2. Cross-Module Learning

**Gap:** Modules don't share what they learn

```
Current:  Module A learns X, Module B doesn't know
Needed:   Module A learns X → Broadcast → All modules know
```

**Needs:**
```python
# Learning bus
class LearningBus:
    def broadcast(self, learning: dict):
        for module in self.subscribers:
            module.incorporate(learning)
```

---

### 3. Automatic Optimization Loop

**Gap:** System doesn't optimize itself

```
Current:  Detect inefficiency → Log → Wait for human
Needed:   Detect → Analyze → Propose → (Auto-approve if safe) → Apply
```

**Needs:**
```python
# optimization_loop.py
def optimize():
    issues = system_overseer.get_issues()
    for issue in issues:
        if issue.auto_fixable and issue.risk < SAFE_THRESHOLD:
            apply_fix(issue)
        else:
            queue_for_approval(issue)
```

---

## Missing Moats (Defensive Advantages)

### 1. Knowledge Moat (Partial)

**What it is:** Accumulated knowledge that's hard to replicate

**Current:** UTF schemas, claims, KG entities
**Missing:** Cross-document insights, temporal patterns, prediction accuracy tracking

### 2. Learning Moat (Missing)

**What it is:** Self-improving capabilities that compound

**Current:** outcome_tracker, strategy_evolution (built but not wired)
**Missing:** Actual compounding - strategies getting measurably better over time

### 3. Integration Moat (Weak)

**What it is:** Deep integration that's hard to switch from

**Current:** 43 modules (fragmented)
**Missing:** Tight coupling where everything reinforces everything else

### 4. Efficiency Moat (Partial)

**What it is:** Doing more with less than alternatives

**Current:** LocalAI ($0), Dragonfly cache, token optimization
**Missing:** Measurement proving we're actually more efficient

---

## Priority Implementation Order

### Phase 1: Close Feedback Loop (This Week)
1. Wire outcome_tracker → strategy_evolution
2. Wire self_improvement → memory (store learnings)
3. Start system_overseer in Docker

### Phase 2: Add Measurement (Next Week)
4. Create goal_tracker.py (measure PRIME-DIRECTIVE)
5. Create resource_accountant.py (track costs)
6. Dashboard showing all metrics

### Phase 3: Add Self-Healing (Week 3)
7. auto_healer.py for safe auto-fixes
8. dependency_graph.py for impact analysis
9. drift_detector.py for behavior monitoring

### Phase 4: Compound Learning (Week 4)
10. LearningBus for cross-module sharing
11. Baseline establishment for all modules
12. Optimization loop with approval workflow

---

## Single Most Important Missing Piece

**The feedback loop is open.**

Everything else works in isolation. Nothing learns from anything else.

```
Fix this FIRST:
outcome_tracker → analyze → strategy_evolution → better_decisions → better_outcomes
     ↑                                                                    │
     └────────────────────────────────────────────────────────────────────┘
```

---

*A system that doesn't learn from its own outputs is just a fancy script.*
