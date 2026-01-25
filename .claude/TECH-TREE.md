# Technology Tree - Emergent Development Pathways

## Current Foundation (Unlocked)

```
                    ┌─────────────────────────────────────┐
                    │       TIER 5: AUTONOMY              │
                    │  daemon, triggers, handoffs ✅      │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────┴───────────────────┐
                    │       TIER 4: OPTIMIZATION          │
                    │  token efficiency, LLM speed ⚠️     │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────┴───────────────────┐
                    │       TIER 3: RESEARCH              │
                    │  bisimulation, GCRL, claims ✅      │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────┴───────────────────┐
                    │       TIER 2: COGNITIVE             │
                    │  goals, decisions, learning ✅      │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────┴───────────────────┐
                    │       TIER 1: PERSISTENCE           │
                    │  memory, KG, cache ✅               │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────┴───────────────────┐
                    │       TIER 0: INFRASTRUCTURE        │
                    │  containers, storage, API ✅        │
                    └─────────────────────────────────────┘
```

---

## 5 Emergent Development Pathways

### Pathway 1: Semantic Router (Token Efficiency)
```
CURRENT                 NEXT                    FUTURE
───────                 ────                    ──────
model_router.py    →    MCP Auto-Router    →    Intent-Aware Dispatch
     │                       │                        │
     ↓                       ↓                        ↓
Manual routing         Skill/Agent/Hook         Context-sensitive
by task type           auto-selection           model selection
                                                     │
                                                     ↓
                                              Predictive routing
                                              (learn from outcomes)
```

**Unlocks:**
- [ ] `semantic-router.py` - Intent classification → route to skill/agent/model
- [ ] `cost-optimizer.py` - Track cost per query, auto-adjust routing
- [ ] `context-compressor.py` - Compress context before expensive models

### Pathway 2: Agentic Mesh (Multi-Agent)
```
CURRENT                 NEXT                    FUTURE
───────                 ────                    ──────
Task tool          →    gRPC Agent Bus     →    Swarm Coordination
     │                       │                        │
     ↓                       ↓                        ↓
Sequential             Parallel agents          Emergent behavior
sub-agents             with contracts           self-organizing
                                                     │
                                                     ↓
                                              Agent specialization
                                              (evolve new agents)
```

**Unlocks:**
- [ ] `agent-bus.py` - gRPC communication between agents
- [ ] `agent-registry.py` - Dynamic agent discovery + capabilities
- [ ] `swarm-coordinator.py` - Emergent multi-agent patterns

### Pathway 3: Knowledge Synthesis (Research)
```
CURRENT                 NEXT                    FUTURE
───────                 ────                    ──────
UTF claims         →    Cross-Paper Links  →    Novel Hypothesis
     │                       │                        │
     ↓                       ↓                        ↓
Extract claims         Find contradictions      Generate new claims
from papers            & agreements             from synthesis
                                                     │
                                                     ↓
                                              Auto-research loops
                                              (identify gaps → fill)
```

**Unlocks:**
- [ ] `contradiction-finder.py` - Identify conflicting claims across papers
- [ ] `hypothesis-generator.py` - Synthesize novel claims from patterns
- [ ] `research-loop.py` - Autonomous gap identification + filling

### Pathway 4: Adaptive Learning (Self-Improvement)
```
CURRENT                 NEXT                    FUTURE
───────                 ────                    ──────
self_improvement.py →  Outcome Tracking   →    Strategy Evolution
     │                       │                        │
     ↓                       ↓                        ↓
Extract patterns       Record success/fail     Generate new strategies
from sessions          for each approach       from successful patterns
                                                     │
                                                     ↓
                                              Self-modifying prompts
                                              (optimize own behavior)
```

**Unlocks:**
- [ ] `outcome-tracker.py` - Track success rate per strategy
- [ ] `strategy-evolver.py` - Generate new strategies from successful ones
- [ ] `prompt-optimizer.py` - Self-modify prompts based on outcomes

### Pathway 5: External Integration (Automation)
```
CURRENT                 NEXT                    FUTURE
───────                 ────                    ──────
Telegram/Email     →    Webhook Mesh       →    Proactive Outreach
     │                       │                        │
     ↓                       ↓                        ↓
Receive triggers       Connect to any          Initiate actions
respond to queries     external service        without triggers
                                                     │
                                                     ↓
                                              Autonomous workflows
                                              (schedule own tasks)
```

**Unlocks:**
- [ ] `webhook-mesh.py` - Universal webhook handler
- [ ] `proactive-scheduler.py` - Self-schedule tasks based on patterns
- [ ] `workflow-composer.py` - Create new workflows dynamically

---

## MCP Auto-Router Architecture

### Three-Tier Model Routing

```
┌─────────────────────────────────────────────────────────────┐
│                    INCOMING REQUEST                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                  SEMANTIC CLASSIFIER                         │
│  Intent: summarize | search | reason | code | extract       │
│  Complexity: low | medium | high                            │
│  Context size: small | medium | large                       │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ↓               ↓               ↓
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  LOCAL AI   │   │   CODEX     │   │   CLAUDE    │
│  (FREE)     │   │   ($0.01)   │   │   ($$$)     │
├─────────────┤   ├─────────────┤   ├─────────────┤
│ summarize   │   │ code gen    │   │ architecture│
│ embed       │   │ code review │   │ complex     │
│ translate   │   │ synthesis   │   │ reasoning   │
│ simple Q&A  │   │ analysis    │   │ novel tasks │
│ extraction  │   │ formatting  │   │ judgment    │
└─────────────┘   └─────────────┘   └─────────────┘
```

### Hook/Skill/Agent Router

```python
# MCP Auto-Router Logic

def route_request(request):
    intent = classify_intent(request)  # summarize|search|code|reason
    complexity = estimate_complexity(request)  # low|medium|high

    # HOOKS (pre/post processing)
    if intent == "file_read":
        return "kg-context-gate.py"  # Inject cached context
    if intent == "file_write":
        return "post-edit-diagnostics.mjs"  # Validate changes

    # SKILLS (workflows)
    if intent == "commit":
        return "skill:commit"
    if intent == "research":
        return "skill:research-external"
    if intent == "fix_bug":
        return "skill:fix"

    # AGENTS (complex tasks)
    if complexity == "high" and intent == "explore":
        return "agent:scout"
    if complexity == "high" and intent == "implement":
        return "agent:kraken"
    if intent == "external_research":
        return "agent:oracle"

    # MODELS (by cost)
    if complexity == "low":
        return "model:localai"  # FREE
    if intent == "code":
        return "model:codex"  # $0.01
    return "model:claude"  # $$$
```

### Router Configuration

```yaml
# .claude/config/router.yaml

routing_rules:
  # Intent → Resource mapping
  intents:
    summarize: {model: localai, skill: null, agent: null}
    search: {model: null, skill: search-router, agent: scout}
    code: {model: codex, skill: null, agent: kraken}
    reason: {model: claude, skill: null, agent: null}
    research: {model: null, skill: research-external, agent: oracle}

  # Complexity thresholds
  complexity:
    low: {max_tokens: 500, prefer: localai}
    medium: {max_tokens: 2000, prefer: codex}
    high: {max_tokens: 8000, prefer: claude}

  # Cost optimization
  cost_limits:
    per_query: 0.05
    per_session: 2.00
    daily: 10.00

  # Fallbacks
  fallbacks:
    localai_unavailable: codex
    codex_unavailable: claude
    claude_rate_limited: localai
```

---

## Next 5 Phases of Growth

### Phase 14: Semantic Router (2 weeks)
```
Prerequisites: Phase 13 ✅
Unlocks: Token efficiency, cost tracking
Components:
  - [ ] Intent classifier (local model)
  - [ ] Complexity estimator
  - [ ] Cost tracker with alerts
  - [ ] Auto-route to skill/agent/model
```

### Phase 15: Knowledge Synthesis (2 weeks)
```
Prerequisites: Phase 12 (claims) ✅, Phase 14
Unlocks: Cross-paper insights, novel hypotheses
Components:
  - [ ] Contradiction finder
  - [ ] Agreement strengthener
  - [ ] Hypothesis generator
  - [ ] Research gap identifier
```

### Phase 16: Adaptive Learning (3 weeks)
```
Prerequisites: Phase 15
Unlocks: Self-improving strategies
Components:
  - [ ] Outcome tracker per strategy
  - [ ] Success pattern extractor
  - [ ] Strategy mutation engine
  - [ ] A/B testing framework
```

### Phase 17: Agentic Mesh (3 weeks)
```
Prerequisites: Phase 16
Unlocks: Multi-agent coordination
Components:
  - [ ] gRPC agent bus
  - [ ] Agent capability registry
  - [ ] Contract-based communication
  - [ ] Swarm coordination patterns
```

### Phase 18: Emergent Autonomy (4 weeks)
```
Prerequisites: Phase 17
Unlocks: Self-directed behavior
Components:
  - [ ] Proactive task generation
  - [ ] Goal evolution engine
  - [ ] Workflow composer
  - [ ] Self-monitoring + correction
```

---

## Dependency Tree (Visual)

```
Phase 18: Emergent Autonomy
    │
    ├── Phase 17: Agentic Mesh
    │       │
    │       ├── Phase 16: Adaptive Learning
    │       │       │
    │       │       ├── Phase 15: Knowledge Synthesis
    │       │       │       │
    │       │       │       ├── Phase 14: Semantic Router
    │       │       │       │       │
    │       │       │       │       └── Phase 13: LLM Caching ✅
    │       │       │       │
    │       │       │       └── Phase 12: Research Layer ✅
    │       │       │
    │       │       └── Phase 11: UTF Architecture ✅
    │       │
    │       └── Phase 10: Cognitive Architecture ✅
    │
    └── Phases 1-9: Foundation ✅
```

---

## Quick Commands

```bash
# Check current phase
cat EVOLUTION-PLAN.md | grep -A5 "Current Phase"

# View tech tree
cat .claude/TECH-TREE.md

# Check resource map
cat .claude/RESOURCE-MAP.md

# View codebase index
cat .claude/CODEBASE-INDEX.md
```
