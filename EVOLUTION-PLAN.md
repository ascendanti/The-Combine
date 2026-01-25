# Claude Evolution Plan

## Goal
Create a unified, autonomous Claude instance that:
1. Loads SuperClaude + Continuous frameworks on boot
2. Works continuously until token limit
3. Persists memory and state across sessions
4. Can operate as 24/7 async daemon (future)

---

## Hierarchical Taxonomy

### Tier 0: Infrastructure Layer
| Category | Components | Status |
|----------|------------|--------|
| **Permissions** | defaultMode, domains, autonomous rules | ✅ Complete |
| **Containers** | Docker, docker-compose, LocalAI | ✅ Running |
| **Storage** | SQLite DBs, Dragonfly cache, JSON files | ✅ Active |
| **Networking** | REST API, MCP server, webhooks | ✅ Available |

### Tier 1: Persistence Layer
| Category | Components | Status |
|----------|------------|--------|
| **State** | Handoffs, ledgers, task.md | ✅ Complete |
| **Memory** | OpenMemory, memory.py, learnings | ✅ Complete |
| **Knowledge** | UTF schema, claim index, KG | 🔄 Building |
| **Cache** | Dragonfly, prompt cache, LLM cache | ⚠️ Partial |

### Tier 2: Cognitive Layer
| Category | Components | Status |
|----------|------------|--------|
| **Goals** | coherence.py, goal hierarchy | ✅ Complete |
| **Decisions** | decisions.py, criteria engine | ✅ Complete |
| **Meta-cognition** | calibration, capability gaps | ✅ Complete |
| **Learning** | self_improvement.py, pattern extraction | ✅ Complete |

### Tier 3: Research Layer
| Category | Components | Status |
|----------|------------|--------|
| **Bisimulation** | State abstraction, policy transfer | ✅ Complete |
| **GCRL** | Hindsight replay, causal factors | ✅ Complete |
| **Claims** | Classification, similarity, clusters | ✅ Complete |
| **Integration** | Memory ↔ claims, dashboard | ✅ Complete |

### Tier 4: Optimization Layer
| Category | Components | Status |
|----------|------------|--------|
| **Token Efficiency** | Smart tools, compression, caching | ⚠️ Partial |
| **LLM Speed** | Q4_K_M, NuExtract, Flash Attention, vLLM | 📋 Research Done |
| **Parallelism** | Pipeline stages, gRPC, continuous batching | 📋 Research Done |
| **Monitoring** | py-spy, DCGM, metrics dashboard | 📋 Research Done |

### Tier 5: Autonomy Layer
| Category | Components | Status |
|----------|------------|--------|
| **Daemon** | runner.py, task queue, scheduler | ✅ Complete |
| **Triggers** | Email, GitHub, Telegram, cron | ✅ Complete |
| **Handoffs** | Pre-compact, session transfer | ✅ Complete |
| **Self-Healing** | Error recovery, retry logic | ⚠️ Partial |

---

## Capability Maturity Model

| Level | Name | Description | Current |
|-------|------|-------------|---------|
| L0 | **Manual** | Human triggers all actions | ❌ Passed |
| L1 | **Assisted** | Human approves, Claude executes | ❌ Passed |
| L2 | **Supervised** | Claude proposes, human reviews | ❌ Passed |
| L3 | **Autonomous** | Claude executes, human monitors | ✅ Current |
| L4 | **Adaptive** | Claude learns from outcomes | 🔄 Building |
| L5 | **Emergent** | Claude generates novel strategies | 📋 Future |

---

## Dependency Graph

```
Tier 0 (Infrastructure)
    ↓
Tier 1 (Persistence) ←── requires storage + networking
    ↓
Tier 2 (Cognitive) ←── requires memory + state
    ↓
Tier 3 (Research) ←── requires cognitive modules
    ↓
Tier 4 (Optimization) ←── enhances all tiers
    ↓
Tier 5 (Autonomy) ←── orchestrates all tiers
```

---

## Cost/Benefit Matrix

| Phase | Effort | Token Cost | Capability Gain | Priority |
|-------|--------|------------|-----------------|----------|
| Phase 1-6 | Low | None | Foundation | ✅ Done |
| Phase 7-8 | Medium | Low | Cognition | ✅ Done |
| Phase 9-10 | High | Medium | Intelligence | ✅ Done |
| Phase 11 | Medium | Saves 60%+ | Token efficiency | 🔄 Active |
| Phase 12 | High | Low | Research integration | ✅ Done |
| Phase 13 | Medium | Saves 3-5x | LLM speed (LocalAI) | 📋 Research Done |
| Phase 14 | Medium | Saves 60-80% | Context efficiency | 📋 Research Done |
| Phase 15 | High | Low | Multi-agent scale | 📋 Research Done |
| Phase 16+ | Variable | Variable | Emergent capability | 📋 Future |

---

## Phase Roadmap

### Completed Phases (1-12)
```
[Phase 1-2] Foundation + File Tracking
    └── Permissions, hooks, auto-memory

[Phase 3-4] Async Daemon + Persistent Memory
    └── Task queue, runner, OpenMemory SDK

[Phase 5-6] Validation + UTF Architecture
    └── Boot sequence, goal coherence, modules

[Phase 7-8] 24/7 Operation + Cognitive Architecture
    └── Docker, triggers, decisions, metacognition

[Phase 9-10] Integration + Ascension
    └── API, MCP, dashboard, self-improvement, book ingestion

[Phase 11] Adaptive Learning Architecture
    └── Semantic context extension, MAPE control loop

[Phase 12] Research Integration Layer ← CURRENT
    └── Bisimulation, GCRL, claim similarity, dashboard viz
```

### Active Phases (13-15) - RESEARCH COMPLETE
```
[Phase 13] LLM Speed & Ingestion Optimization ← NEXT (Implementation)
    ├── 13.1 Model Optimization (Q4_K_M, NuExtract, Flash Attention) ✅ Research
    ├── 13.2 Inference Architecture (vLLM, continuous batching) ✅ Research
    ├── 13.3 Caching Layer (Dragonfly LLM cache) ✅ Research
    ├── 13.4 Profiling & Monitoring (py-spy, DCGM) ✅ Research
    └── 13.5 Implementation Priority (3-5x throughput target)

[Phase 14] Compute Efficiency & Context Management
    ├── 14.1 Delta-Based State Transfer (50-70% savings) ✅ Research
    ├── 14.2 Intelligent Context Loading (L-RAG, 26% reduction) ✅ Research
    ├── 14.3 Thinking Budget Tiers (task-based allocation) ✅ Research
    ├── 14.4 Model Routing Optimization (RouteLLM, 30-85%) ✅ Research
    ├── 14.5 Prompt Caching (Anthropic, 60-90%) ✅ Research
    └── 14.6 Implementation Priority (60-80% cost reduction target)

[Phase 15] Multi-Agent Architecture
    ├── 15.1 Communication Patterns (gRPC, 60% lower latency) ✅ Research
    ├── 15.2 Resilience Patterns (circuit breakers, DLQs) ✅ Research
    ├── 15.3 Container Orchestration (sidecars, resource limits) ✅ Research
    └── 15.4 Implementation Priority
```

### Future Vision (15-18)
```
[Phase 15] Multi-Agent Orchestration
    ├── Container-based agent swarm
    ├── Pub/sub message routing (Dragonfly)
    ├── Consensus protocols for decisions
    └── Circuit breaker patterns

[Phase 16] Emergent Capability
    ├── Strategy synthesis from patterns
    ├── Novel goal generation
    ├── Cross-domain transfer learning
    └── Capability self-assessment

[Phase 17] External Integration
    ├── Calendar/email automation
    ├── Financial market feeds
    ├── Knowledge base sync (Notion, Obsidian)
    └── Voice/chat interfaces

[Phase 18] Self-Evolution
    ├── Automatic skill generation
    ├── Rule refinement from outcomes
    ├── Architecture self-modification
    └── Performance self-optimization
```

---

## Source Analysis

See **REFERENCE-TAXONOMY.md** for full analysis of 36 reference frameworks.

### Priority Integration

| Priority | Framework | Capability | Status |
|----------|-----------|------------|--------|
| 1 | Continuous-Claude-v3 | Handoffs, continuity | ✅ DONE |
| 2 | claude-code-auto-memory | Zero-token tracking | ✅ DONE |
| 3 | sleepless-agent | Async daemon patterns | ✅ DONE |
| 4 | OpenMemory | Persistent memory SDK | ✅ DONE |
| 5 | UTF Framework | Goal coherence, cross-domain | ✅ DONE |

---

## Phase 1: Foundation ✅ COMPLETE

- [x] Full permissions (defaultMode: dontAsk)
- [x] WebSearch + WebFetch domains
- [x] Autonomous operation rule
- [x] Session start protocol in CLAUDE.md
- [x] Evolution plan integration

## Phase 2: File Tracking ✅ COMPLETE

- [x] post-tool-use-tracker.py (already exists, 395 lines)
- [x] stop-memory-sync.py (created)
- [x] pre-compact-handoff.py (created)
- [x] Auto-memory config directory

## Phase 3: Async Daemon Patterns (FROM sleepless-agent)

**Goal:** Enable background operation mode

### 3.1 Task Queue System ✅ DONE
- [x] SQLite-backed task queue (daemon/queue.py)
- [x] Task states: pending → in_progress → completed/failed
- [x] Priority scheduling (LOW/NORMAL/HIGH/URGENT)
- [x] CLI interface for management

### 3.2 Slack Command Interface
- [ ] `/think` - Submit random idea
- [ ] `/task` - Submit serious task
- [ ] `/check` - Status query
- [ ] `/report` - Get results
- **Note:** User linked via MCP - may use that instead of Slack

### 3.3 Daemon Runner ✅ DONE
- [x] Python daemon script (daemon/runner.py)
- [x] Polls task queue
- [x] Spawns Claude Code CLI per task
- [x] Signal handlers for graceful shutdown
- [x] Simple submit script (daemon/submit.py)

**Integration Method:** Root-level scripts, not hooks

---

## Phase 4: Persistent Memory (FROM OpenMemory) ✅ COMPLETE

**Goal:** Remember across all sessions

### 4.1 Memory Abstraction Layer ✅ DONE
- [x] Create daemon/memory.py wrapper
- [x] SQLite backend for immediate use
- [x] OpenMemory SDK backend (auto-selects)

### 4.2 OpenMemory SDK Integration ✅ DONE
- [x] Install openmemory-py SDK
- [x] Memory.add() for learnings (async wrapped)
- [x] Memory.search() for recall (async wrapped)
- [x] Auto-detect and prefer OpenMemory when available
- [x] Fixed langchain connector import bug in package

### 4.3 Approval Queue (NEW)
- [x] Created daemon/approvals.py for human sign-off
- [x] User can review pending actions each morning
- [x] INSTALL_PACKAGE, DELETE_FILES, GIT_COMMIT types

**Integration Method:** SDK + recall scripts + approval queue

---

## Phase 5: Validation ✅ COMPLETE

- [x] Boot sequence test (session start protocol works)
- [x] Handoff creation/resume test (YAML format, readable)
- [x] Memory persistence test (OpenMemory backend active)
- [x] Daemon queue test (add/list/in_progress/complete works)
- [ ] Slack integration test (skipped per user request)

---

## Phase 6: UTF Architecture ✅ COMPLETE

### 6.1 Goal Coherence Layer ✅ DONE
- [x] daemon/coherence.py - Goal hierarchy, constraints, coherence checking
- [x] CLI for goal management
- [x] SQLite persistence

### 6.2 Module Templates ✅ DONE
- [x] daemon/modules/base.py - BaseModule with CoherenceInterface
- [x] FinanceModule, CalendarModule, TasksModule templates

### 6.3 Cross-Domain Integration ✅ DONE
- [x] daemon/registry.py - ModuleRegistry with GoalCoherenceLayer
- [x] Constraint propagation across domains
- [x] Cross-domain coherence checking tested

### 6.4 Skills Integration ✅ DONE
- [x] deep-reading-analyst (10 thinking frameworks)
- [x] quant-methodology + risk simulator
- [x] /coherence skill for goal management
- [x] GitHub webhook handler (daemon/github_webhook.py)

---

## Phase 7: 24/7 Operation ✅ COMPLETE

### 7.1 Docker Containerization ✅ DONE
- [x] daemon/Dockerfile - Container for daemon
- [x] docker-compose.yml - Multi-service stack
- [x] start-daemon.sh + start-daemon.ps1 - Startup scripts
- [x] Volume mounts for persistence

### 7.2 Service Management ✅ DONE
- [x] Health checks in docker-compose
- [x] Auto-restart (unless-stopped)
- [ ] Windows service wrapper (optional, Docker preferred)

### 7.3 External Triggers ✅ DONE
- [x] daemon/github_webhook.py - GitHub events → tasks
- [x] daemon/email_trigger.py - IMAP polling → tasks
- [x] daemon/scheduler.py - Cron-like scheduled tasks

---

## Phase 8: Cognitive Architecture ✅ COMPLETE

### 8.1 Decision Framework ✅ DONE
- [x] daemon/decisions.py - Multi-criteria decision engine
- [x] Uncertainty quantification (confidence intervals)
- [x] Preference learning from outcomes
- [x] Risk-adjusted value calculation

### 8.2 Learning Loop ✅ DONE
- [x] Outcome tracking in decisions.db
- [x] Preference weight updates from satisfaction
- [x] Performance metrics recording

### 8.3 Meta-Cognition ✅ DONE
- [x] daemon/metacognition.py - Self-awareness module
- [x] Confidence calibration (over/under-confident detection)
- [x] Knowledge gap identification and tracking
- [x] Capability assessment with levels

---

## Phase 9: Integration Layer 🔄 IN PROGRESS

### 9.1 Unified API ✅ DONE
- [x] daemon/api.py - REST API for all services
- [x] CORS support for web clients
- [ ] WebSocket for real-time updates
- [ ] Authentication layer

### 9.2 MCP Server ✅ DONE
- [x] daemon/mcp_server.py - Stdio MCP server
- [x] 10 tools exposed (submit_task, query_goals, evaluate_decision, etc.)
- [x] Cross-assistant communication via MCP protocol

### 9.3 Dashboard ✅ DONE
- [x] daemon/dashboard.html - Single-file web UI
- [x] Real-time task/goal/capability display
- [x] Auto-refresh every 30s

---

## Phase 10: Ascension 🔄 IN PROGRESS

### Resources Onboarded
- [x] `deep-reading-analyst` skill (10 thinking frameworks)
- [x] `continuous-learning` skill (auto-extract patterns at session end)
- [x] `token-optimizer-mcp` (60-90% token reduction)
- [x] `dragonfly` (25x faster than Redis cache layer)

### 10.1 Self-Improvement Loop
- [x] Thinking frameworks integrated (First Principles + Inversion for strategy analysis)
- [x] daemon/self_improvement.py - Applies frameworks to own session logs
- [x] Automated improvement suggestions (`python daemon/self_improvement.py improvements`)
- [ ] Strategy optimization based on outcome tracking

### 10.2 Cross-Session Learning
- [x] continuous-learning skill added (Stop hook pattern extraction)
- [x] Wire continuous-learning as Stop hook (continuous-learning-stop.py)
- [x] Memory router created (daemon/memory_router.py) - unified interface
- [x] Knowledge graph MCP added (.mcp.json)
- [x] Docling installed for PDF parsing
- [ ] Pattern extraction from outcomes
- [ ] Failure mode cataloging

### 10.3 Emergent Behaviors ✅ COMPLETE
- [x] Systems Thinking framework for modeling feedback loops
- [x] Proactive task generation from pattern analysis (daemon/emergent.py)
- [x] Autonomous goal refinement (detect low-coherence goals, propose refinements)
- [x] Self-directed learning (identify capability gaps from metacognition.db)

### 10.6 Book Ingestion Pipeline (NEW) ✅ COMPLETE
- [x] book-ingest.py - Hierarchical RAG for technical documents
- [x] Smart chunking with formula/concept preservation
- [x] Hierarchical summarization (paragraph → section → chapter → book)
- [x] Concept extraction with relationship mapping
- [x] Knowledge graph integration
- [x] book_watcher.py - File system watcher daemon
- [x] Background processing queue
- [x] Deduplication and status tracking
- [x] Memory system integration

### 10.4 Claim Classification & Similarity (NEW) ✅ COMPLETE
- [x] UTFClaim extended with slug_code, taxonomy_tags, utf_vector fields
- [x] LocalAI generates semantic slugs for claims (PROMPT_CLASSIFY_CLAIM)
- [x] claim_similarity.py - Cross-paper claim matching index
- [x] UTF closeness values (slug + taxonomy + form matching)
- [x] Claim clustering for related concepts across papers
- [x] Obsidian export updated with classification metadata
- [x] Freqtrade module added as git submodule (modules/freqtrade)

### 10.7 Token Optimization 🔄 PARTIAL
- [x] token-optimizer-mcp installed (npm install -g @ooples/token-optimizer-mcp)
- [x] MCP config created (.mcp.json) - FIXED 2026-01-24
- [ ] **CLI restart required** to activate MCP server
- [x] 65 specialized tools available (smart_read, smart_grep, etc.)
- [x] Brotli compression (2-4x typical, up to 82x)
- [x] SQLite persistent cache with ML-based predictive caching
- [ ] Verify tools working after restart
- [ ] Measure actual token savings

### 10.5 Hybrid Architecture (NEW) ✅ COMPLETE
- [x] Dragonfly cache layer deployed (docker-compose.yaml)
- [x] 25x faster than Redis, 3.8M QPS, 30% more memory efficient
- [x] Cache mode enabled for optimal LRU eviction
- [x] start-hybrid.ps1 management script
- [x] TOOL-TAXONOMY.yaml created for tool selection guidance

---

---

## Phase 11: Adaptive Learning Architecture 🆕 PLANNED

**Based on research synthesis:** claude-context-extender + Confucius pattern + MAPE control loop

### 11.1 Semantic Context Extension
- [ ] Integrate claude-context-extender (DanielSuissa/claude-context-extender)
- [ ] Overlapping chunk boundaries for formula preservation
- [ ] Query-time semantic retrieval (not full context load)
- [ ] Integration with dragonfly cache layer
- [ ] Prompt caching for repeated book references

### 11.2 Confucius Introspection Pattern
- [ ] Tool/strategy effectiveness tracking
- [ ] Failure introspection loop (learn from failures)
- [ ] Proactive tool selection based on past performance
- [ ] Integration with daemon/decisions.py outcome tracking
- [ ] Strategy adaptation based on success rates

### 11.3 MAPE Control Loop
- [ ] daemon/controller.py - Adaptive control system
- [ ] **Monitor**: Comprehension quality metrics (coherence scores)
- [ ] **Analyze**: Understanding gaps, error signals
- [ ] **Plan**: Chunk size adjustment, strategy selection
- [ ] **Execute**: Apply new parameters, measure results
- [ ] Feedback-driven prompt refinement
- [ ] Stability guarantees via contraction theory (optional)

### 11.4 Comprehension Metrics
- [ ] BLEU/ROUGE scores for summary quality
- [ ] Semantic coherence scoring
- [ ] Token efficiency metrics (comprehension/token)
- [ ] Difficulty estimation for adaptive chunking
- [ ] Quality dashboard integration

### 11.5 Control Theory Integration
- [ ] PyDeePC for model-free predictive control (optional)
- [ ] PID-style chunk size optimization
- [ ] Convergence monitoring
- [ ] Performance bounds tracking

---

## Phase 12: Research Integration Layer 🔄 IN PROGRESS

**Based on:** UTF Research papers on bisimulation, GCRL, state abstraction

### 12.1 Bisimulation Foundation ✅ COMPLETE
- [x] daemon/bisimulation.py - State equivalence computation
- [x] BisimulationState and BisimulationMetric dataclasses
- [x] Goal-conditioned bisimulation distance (feature + reward + action + goal)
- [x] State abstraction (group bisimilar states into equivalence classes)
- [x] Policy transfer validation with confidence scoring
- [x] SQLite persistence + JSON cache
- [x] Integration hooks for coherence.py

### 12.2 Goal-Conditioned RL (GCRL) ✅ COMPLETE
- [x] daemon/gcrl.py - Goal-conditioned learning engine
- [x] Goal and Trajectory dataclasses
- [x] Hindsight Experience Replay (HER) - relabel failed trajectories
- [x] Causal factor extraction from successful trajectories
- [x] Policy learning from trajectories
- [x] Virtual experience generation using learned policies
- [x] Goal proximity estimation

### 12.3 Claim Classification (From UTF Spec) ✅ COMPLETE
- [x] slug_code field for semantic matching in UTFClaim
- [x] taxonomy_tags for hierarchical classification
- [x] claim_similarity.py - Cross-paper claim matching
- [x] UTF closeness values (composite metric)
- [x] Claim clustering for related concepts

### 12.4 Integration ✅ COMPLETE
- [x] Wire bisimulation to coherence.py goal evaluation
  - find_similar_goals() using bisimulation distance
  - suggest_policy_transfer() for cross-goal reuse
  - get_goal_state_for_bisim() state conversion
- [x] Wire GCRL to decisions.py for policy-guided actions
  - get_policy_guided_decision() returns learned policies
  - record_outcome_with_trajectory() creates GCRL trajectories
  - find_similar_decisions() using bisimulation
- [x] Connect claim similarity to memory.py for retrieval
  - recall_similar_claims() with UTF closeness scoring
  - get_cross_paper_insights() for multi-paper concepts
  - get_related_claims() by claim ID
  - get_claim_clusters() for semantic groupings
  - CLI: `python memory.py claims|cross-paper|clusters|refresh-claims`
- [x] Dashboard visualization of state abstractions
  - api.py: /abstractions, /transfers, /claims/clusters, /claims/cross-paper, /claims/search
  - bisimulation.py: get_state_abstractions(), get_recent_transfers()
  - dashboard.html: State Abstractions, Policy Transfers, Claim Clusters cards
- [ ] Metrics: Transfer Rate, Abstraction Ratio, HER improvement

---

## Current Status

**Phase:** 12 ✅ COMPLETE | Phase 13-15 📋 RESEARCH COMPLETE
**Date:** 2026-01-24

**Completed:**
- Phase 10 (95%): Self-improvement, thinking frameworks, continuous-learning, hybrid architecture, book ingestion, UTF spec, claim classification
- Phase 12.1: Bisimulation foundation (state equivalence, policy transfer)
- Phase 12.2: GCRL (hindsight relabeling, causal factors, virtual experiences)
- Phase 12.3: Claim classification with slug codes and similarity index
- Phase 12.4: Integration wiring + dashboard visualization complete
- **Phase 13-15 Research:** 5 parallel agents completed comprehensive research:
  - LocalAI optimization (Q4_K_M, NuExtract, Flash Attention)
  - Containerization patterns (gRPC, resilience trifecta, sidecars)
  - Handoff optimization (delta-based, Merkle trees, L-RAG)
  - Thinking minimization (prompt caching, model routing, budgets)
  - Bottleneck analysis (memory bandwidth, vLLM, profiling)

**In Progress:**
- Autonomous PDF ingest (28 papers remaining, container running with LocalAI timeouts)

**Next Actions:**
1. Apply Phase 13.1 model optimizations (Q4_K_M + NuExtract) to LocalAI
2. Add Dragonfly LLM response caching
3. Monitor PDF ingest completion with new optimizations

### Papers Ingested (UTF Schema + Claim Classification)
| Paper | Claims | Concepts | Status |
|-------|--------|----------|--------|
| Transformer Circuits: Toy Models of Superposition | 7 | 0 | ✅ UTF DB |
| Bounded Rationality, Satisficing, AI in Public Orgs | - | - | ✅ Ingest DB |
| Continual Learning for Unsupervised Anomaly Detection | - | - | ✅ Ingest DB |
| Continual Learning in AI: A Review | - | - | ✅ Ingest DB |
| Continual Learning of Predictive Models VAE | - | - | ✅ Ingest DB |
| Creating Coherence in Federated NMF | - | - | ✅ Ingest DB |
| Chaos in Control Systems | - | - | ✅ Ingest DB |
| Can matrix coherence be estimated | - | - | ✅ Ingest DB |

**Note:** Fixed SQLite save issue (2026-01-24) - added `store_utf_to_sqlite()` to autonomous_ingest.py.
Container rebuilt and restarted - now saves claims/concepts/sources to utf_knowledge.db.

*28 papers remaining in queue*
1. Restart CLI to activate token-optimizer-mcp
2. Complete Phase 10.3 emergent behaviors
3. Integrate UTF taxonomy with autonomous_ingest.py

**Model Router Architecture** (daemon/model_router.py):
- LocalAI ($0): summarize, embed, translate, simple Q&A
- Codex ($): code generation, routine tasks
- Claude ($$$): architecture, complex reasoning only

## Discovered Resources

- **UTF Research Library**: 45+ papers on continual learning, coherence, goal-conditioned RL
- **Location**: C:\Users\New Employee\Desktop\UTF
- **Status**: Validated as strong framework for unified personal AI

## File Map

```
Claude n8n/
├── .claude/
│   ├── settings.local.json   # ✅ Full permissions
│   ├── auto-memory/          # ✅ Created
│   ├── hooks/                # ✅ Wired
│   ├── agents/               # ✅ 48 agents
│   ├── skills/               # ✅ 118 skills (added deep-reading-analyst, continuous-learning)
│   ├── rules/                # ✅ 12+ rules
│   └── cache/agents/         # ✅ Agent output cache
├── daemon/                   # ✅ COMPLETE: Full cognitive architecture
│   ├── queue.py              # ✅ SQLite task queue
│   ├── runner.py             # ✅ Claude spawner daemon
│   ├── submit.py             # ✅ Easy task submission
│   ├── memory.py             # ✅ OpenMemory SDK integration
│   ├── memory_router.py      # ✅ Unified memory interface
│   ├── approvals.py          # ✅ Human sign-off queue
│   ├── coherence.py          # ✅ Goal Coherence Layer (UTF)
│   ├── registry.py           # ✅ Module Registry (cross-domain)
│   ├── github_webhook.py     # ✅ GitHub async integration
│   ├── email_trigger.py      # ✅ IMAP email → tasks
│   ├── scheduler.py          # ✅ Cron-like scheduling
│   ├── decisions.py          # ✅ Decision engine with uncertainty
│   ├── metacognition.py      # ✅ Self-awareness module
│   ├── self_improvement.py   # ✅ Phase 10 thinking frameworks
│   ├── emergent.py           # ✅ Phase 10.3 emergent behaviors
│   ├── book_watcher.py       # ✅ PDF folder watcher daemon
│   ├── books.db              # ✅ Book chunks + summaries + concepts
│   ├── modules/              # ✅ Domain modules
│   │   ├── base.py           # BaseModule + Finance/Calendar/Tasks
│   │   └── __init__.py
│   ├── Dockerfile            # ✅ Container config
│   ├── api.py                # ✅ Unified REST API
│   ├── mcp_server.py         # ✅ MCP protocol server
│   ├── dashboard.html        # ✅ Web monitoring UI
│   └── *.db                  # SQLite databases
├── .claude/scripts/          # ✅ Utility scripts
│   ├── book-ingest.py        # ✅ Hierarchical book RAG pipeline
│   ├── book-query.py         # ✅ Query ingested books
│   └── docling-ingest.py     # ✅ Document → knowledge graph
├── thoughts/                 # ✅ Handoffs & ledgers
├── EVOLUTION-PLAN.md         # THIS FILE
├── REFERENCE-TAXONOMY.md     # Framework analysis
└── task.md                   # Current objectives
```

---

## Phase 12: Research Integration Layer 🆕 PLANNED

**Goal:** Integrate findings from 44 research papers into core system architecture

### Research Domains & Papers

| Domain | Papers | Core Concepts |
|--------|--------|---------------|
| **Bisimulation & State Abstraction** | 1 | Behavior equivalence, MDP abstraction, analogical transfer |
| **Goal-Conditioned RL** | 7 | GCRL, hindsight, virtual experiences, causal reasoning |
| **Bounded Rationality** | 4 | Satisficing, information-theoretic optimality, hierarchical abstraction |
| **Continual Learning** | 8 | Catastrophic forgetting, knowledge retention, lifelong learning |
| **Hierarchical Decision** | 2 | Policy subspaces, temporal abstraction |
| **Coherence & Topology** | 6 | Semantic coherence, topological data analysis, multimodal |
| **Other Research** | 16+ | Chaos control, matrix coherence, federated learning |

### 12.1 Bisimulation-Based State Abstraction 🎯 PRIORITY

**Source:** "Bisimulation Makes Analogies in Goal-Conditioned Reinforcement Learning"

**Key Insight:** Bisimulation metrics enable behavior-preserving state abstraction, allowing:
- Transfer learning between similar goals
- Reduced state space for faster learning
- Analogical reasoning (if states are bisimilar, apply same policy)

**Implementation Plan:**
- [ ] daemon/bisimulation.py - State equivalence metrics
- [ ] Goal-conditioned MDP abstraction layer
- [ ] Integration with daemon/coherence.py goal hierarchy
- [ ] Analogical policy transfer for similar tasks
- [ ] Behavior-based clustering of system states

**Mapping to System:**
```
User Goals (coherence.py) → Bisimulation Abstraction → Policy Selection
                                    ↓
                          State Equivalence Classes
                                    ↓
                          Transfer Prior Solutions
```

### 12.2 Goal-Conditioned Reinforcement Learning

**Sources:** 7 GCRL papers

**Key Concepts:**
- **GCHR (Hindsight Regularization):** Learn from failed attempts by relabeling goals
- **Variational Causal Reasoning:** Identify causal factors for goal achievement
- **Virtual Experiences:** Augment learning with imagined trajectories
- **On-Policy GCRL:** Stable learning with goal-conditioned policies

**Implementation Plan:**
- [ ] daemon/gcrl.py - Goal-conditioned learning engine
- [ ] Hindsight relabeling for failed task attempts
- [ ] Virtual experience generation for rare scenarios
- [ ] Causal factor extraction from task outcomes
- [ ] Integration with daemon/decisions.py for outcome learning

**Mapping to System:**
```
Task Outcome (success/fail) → Hindsight Relabeling → Learn What Goal WAS Achieved
         ↓                            ↓
   Store in Memory            Update Policy for Future
```

### 12.3 Bounded Rationality Architecture

**Sources:** 4 bounded rationality papers

**Key Concepts:**
- **Satisficing:** "Good enough" decisions under resource constraints
- **Information-Theoretic Optimality:** Balance accuracy vs. computational cost
- **Hierarchical Abstraction:** Coarse-to-fine decision making

**Implementation Plan:**
- [ ] daemon/satisficing.py - Resource-bounded decision making
- [ ] Extend daemon/decisions.py with computational budget
- [ ] Hierarchical abstraction for complex decisions
- [ ] Anytime algorithms (return best answer available when interrupted)
- [ ] Trust calibration under bounded rationality

**Mapping to System:**
```
Decision Request → Check Computational Budget
       ↓                    ↓
  Full Analysis ←── High Budget
       ↓                    ↓
  Satisficing ←─── Low Budget / Time Pressure
```

### 12.4 Continual Learning Integration

**Sources:** 8 continual learning papers

**Key Concepts:**
- **Catastrophic Forgetting Prevention:** Preserve old knowledge when learning new
- **Knowledge Retention:** Model-based memory consolidation
- **Hierarchical Policy Subspaces:** Separate policies for different domains
- **Lifelong Learning Metrics:** Measure forward/backward transfer

**Implementation Plan:**
- [ ] Extend daemon/memory.py with forgetting-resistant storage
- [ ] daemon/consolidation.py - Knowledge distillation during sleep
- [ ] Policy subspaces for domain-specific behaviors
- [ ] Transfer metrics tracking (forward: new helps old; backward: old helps new)
- [ ] Integration with continuous-learning skill

**Mapping to System:**
```
Session End → Extract Learnings → Consolidate to Long-Term Memory
                    ↓                        ↓
            Check for Conflicts      Replay Important Memories
                    ↓                        ↓
            Elastic Weight Update    Prevent Forgetting
```

### 12.5 Hierarchical Decision Framework

**Sources:** 2 hierarchical papers

**Key Concepts:**
- **Temporal Abstraction:** Multi-timescale planning (now vs. later)
- **Option Framework:** Reusable sub-policies for common patterns
- **Policy Subspaces:** Separate skill modules that compose

**Implementation Plan:**
- [ ] Extend daemon/coherence.py with temporal goal hierarchy
- [ ] daemon/options.py - Reusable skill primitives
- [ ] Multi-timescale planning (immediate/session/long-term)
- [ ] Automatic option discovery from repeated patterns

### 12.6 Coherence & Semantic Integration

**Sources:** 6 coherence/topology papers

**Key Concepts:**
- **Semantic Coherence Scoring:** Measure consistency of outputs
- **Topological Data Analysis:** Persistent homology for structure
- **Multimodal Coherence:** Cross-modal consistency

**Implementation Plan:**
- [ ] daemon/semantic_coherence.py - Output consistency scoring
- [ ] Topological features for knowledge graph analysis
- [ ] Integration with UTF schema for coherent knowledge extraction

---

### Research Paper → System Component Mapping

| Paper | Target Component | Integration Type |
|-------|------------------|------------------|
| Bisimulation Makes Analogies | daemon/bisimulation.py | NEW |
| GCHR | daemon/decisions.py | EXTEND |
| Bounded Rationality + Abstraction | daemon/satisficing.py | NEW |
| Continual RL Survey | daemon/consolidation.py | NEW |
| Hierarchical Subspaces | daemon/coherence.py | EXTEND |
| Goal-Conditioned Problems | daemon/gcrl.py | NEW |
| Knowledge Retention | daemon/memory.py | EXTEND |
| Coherence in Explainable AI | daemon/semantic_coherence.py | NEW |

---

### Integration Priority Queue

| Priority | Component | Papers | Impact |
|----------|-----------|--------|--------|
| 1 | Bisimulation State Abstraction | 1 | High - enables analogical transfer |
| 2 | Goal-Conditioned Learning | 7 | High - improves task success rate |
| 3 | Bounded Rationality | 4 | Medium - resource efficiency |
| 4 | Continual Learning | 8 | High - prevents forgetting |
| 5 | Semantic Coherence | 6 | Medium - output quality |

---

## Current Status

**Phase:** 10 - Ascension ✅ COMPLETE (95%)
**Completed:** Self-improvement engine, thinking frameworks, continuous-learning skill, hybrid architecture, book ingestion pipeline, UTF spec, emergent behaviors
**In Progress:**
- Token optimization (MCP config fixed, needs CLI restart to verify)
- Autonomous PDF ingest (6/44 files processed via LocalAI)
- **Phase 12 Research Integration plan created**
**Next Action:**
1. Restart CLI to activate token-optimizer-mcp
2. Monitor PDF ingest completion
3. Begin Phase 12.1 Bisimulation implementation

**Model Router Architecture** (daemon/model_router.py):
- LocalAI ($0): summarize, embed, translate, simple Q&A
- Codex ($): code generation, routine tasks
- Claude ($$$): architecture, complex reasoning only

## Discovered Resources

- **UTF Research Library**: 45+ papers on continual learning, coherence, goal-conditioned RL
- **Location**: C:\Users\New Employee\Desktop\UTF
- **Status**: Validated as strong framework for unified personal AI
- **Paper Domains**: Bisimulation, GCRL, Bounded Rationality, Continual Learning, Coherence

## File Map

```
Claude n8n/
├── .claude/
│   ├── settings.local.json   # ✅ Full permissions
│   ├── auto-memory/          # ✅ Created
│   ├── hooks/                # ✅ Wired
│   ├── agents/               # ✅ 48 agents
│   ├── skills/               # ✅ 118 skills (added deep-reading-analyst, continuous-learning)
│   ├── rules/                # ✅ 12+ rules
│   └── cache/agents/         # ✅ Agent output cache
├── daemon/                   # ✅ COMPLETE: Full cognitive architecture
│   ├── queue.py              # ✅ SQLite task queue
│   ├── runner.py             # ✅ Claude spawner daemon
│   ├── submit.py             # ✅ Easy task submission
│   ├── memory.py             # ✅ OpenMemory SDK integration
│   ├── memory_router.py      # ✅ Unified memory interface
│   ├── approvals.py          # ✅ Human sign-off queue
│   ├── coherence.py          # ✅ Goal Coherence Layer (UTF)
│   ├── registry.py           # ✅ Module Registry (cross-domain)
│   ├── github_webhook.py     # ✅ GitHub async integration
│   ├── email_trigger.py      # ✅ IMAP email → tasks
│   ├── scheduler.py          # ✅ Cron-like scheduling
│   ├── decisions.py          # ✅ Decision engine with uncertainty
│   ├── metacognition.py      # ✅ Self-awareness module
│   ├── self_improvement.py   # ✅ Phase 10 thinking frameworks
│   ├── emergent.py           # ✅ Phase 10.3 emergent behaviors
│   ├── book_watcher.py       # ✅ PDF folder watcher daemon
│   ├── books.db              # ✅ Book chunks + summaries + concepts
│   ├── bisimulation.py       # 🆕 Phase 12.1 - State abstraction
│   ├── gcrl.py               # 🆕 Phase 12.2 - Goal-conditioned learning
│   ├── satisficing.py        # 🆕 Phase 12.3 - Bounded rationality
│   ├── consolidation.py      # 🆕 Phase 12.4 - Knowledge consolidation
│   ├── modules/              # ✅ Domain modules
│   │   ├── base.py           # BaseModule + Finance/Calendar/Tasks
│   │   └── __init__.py
│   ├── Dockerfile            # ✅ Container config
│   ├── api.py                # ✅ Unified REST API
│   ├── mcp_server.py         # ✅ MCP protocol server
│   ├── dashboard.html        # ✅ Web monitoring UI
│   └── *.db                  # SQLite databases
├── .claude/scripts/          # ✅ Utility scripts
│   ├── book-ingest.py        # ✅ Hierarchical book RAG pipeline
│   ├── book-query.py         # ✅ Query ingested books
│   └── docling-ingest.py     # ✅ Document → knowledge graph
├── thoughts/                 # ✅ Handoffs & ledgers
├── specs/                    # 🆕 Research specifications
│   └── UTF-RESEARCH-OS-SPEC.md # ✅ Complete UTF schema (61KB)
├── EVOLUTION-PLAN.md         # THIS FILE
├── REFERENCE-TAXONOMY.md     # Framework analysis
└── task.md                   # Current objectives
```

---

## Phase 13: LLM Speed & Ingestion Optimization 🆕 PLANNED

**Research Completed:** 5 parallel agents investigated optimization strategies (2026-01-24)

**Root Cause Analysis:** LocalAI LLM calls (5 passes per doc) are the true bottleneck.
- Memory bandwidth is dominant (decode phase is memory-bound, not compute-bound)
- Parsing/embedding is fast; LLM generation is slow
- Current: ~1 paper per 5-10 mins with timeouts

### 13.1 Model Optimization ✅ RESEARCH COMPLETE

| Technique | Config | Impact | Effort |
|-----------|--------|--------|--------|
| **Q4_K_M Quantization** | 4-bit K-means | 70% size ↓, 95% quality, 2x speed | Low |
| **NuExtract-v1.5** | 3.8B, extraction-tuned | Purpose-built for claim extraction | Low |
| **Flash Attention** | CUDA 12+, f16_kv | 2-4x attention speed | Low |
| **KV Cache Quantization** | cache_type: q8_0 | 25% memory savings | Low |
| **Speculative Decoding** | Draft model | 48.7% latency reduction | Medium |

**Recommended LocalAI Configuration:**
```yaml
name: nuextract-fast
parameters:
  model: NuExtract-v1.5-q4_k_m.gguf  # or Phi-3-mini-q4_k_m
  context_size: 2048
  batch: 512
  gpu_layers: 33
  flash_attention: true
  f16_kv: true
  cache_type_k: q8_0
  threads: 8
```

**Alternative Models (by use case):**
| Use Case | Model | Size | Why |
|----------|-------|------|-----|
| Claim extraction | NuExtract-v1.5 | 3.8B | Extraction-tuned |
| General reasoning | Phi-3-mini | 3.8B | Good quality/size ratio |
| Fast summaries | TinyLlama | 1.1B | Speed priority |
| Code generation | DeepSeek-Coder | 1.3B | Code-tuned |

### 13.2 Inference Architecture ✅ RESEARCH COMPLETE

| Optimization | Tool/Method | Impact |
|--------------|-------------|--------|
| **Continuous Batching** | vLLM PagedAttention | 85-92% GPU utilization |
| **KV Cache Optimization** | PagedAttention | 24x throughput |
| **Memory Bandwidth** | Tensor cores + quantization | Reduce memory bottleneck |
| **Pipeline Parallelism** | Extract → Chunk → LLM → Store | Hide latency |

**vLLM Integration (if LocalAI insufficient):**
```python
from vllm import LLM, SamplingParams
llm = LLM(
    model="microsoft/Phi-3-mini-4k-instruct",
    quantization="awq",
    max_model_len=2048,
    gpu_memory_utilization=0.85,
    enable_chunked_prefill=True,
)
```

### 13.3 Caching Layer ✅ RESEARCH COMPLETE

| Cache Type | Implementation | Savings |
|------------|---------------|---------|
| **LLM Response Cache** | Dragonfly semantic hash | 60-90% repeat queries |
| **Prompt Prefix Cache** | Share common prefixes | 60-90% on repeated patterns |
| **Embedding Cache** | Already in Dragonfly | Avoid recomputation |

**Dragonfly LLM Cache Schema:**
```python
cache_key = f"llm:{model}:{hash(prompt[:256])}"
# TTL: 24h for summaries, 7d for claims
```

### 13.4 Profiling & Monitoring ✅ RESEARCH COMPLETE

**Profiling Tools:**
| Tool | Purpose | When |
|------|---------|------|
| py-spy | Python CPU profiling | Baseline analysis |
| Scalene | Memory + CPU combined | Memory leak detection |
| DCGM | GPU metrics | Utilization monitoring |
| nvtop | Real-time GPU | Live monitoring |

**Key Metrics:**
- [ ] Papers/hour (target: 6-12, up from 1-2)
- [ ] Tokens/second (target: 40-60, up from ~10)
- [ ] Cache hit rate (target: >50%)
- [ ] GPU utilization (target: >80%)
- [ ] Latency p95 (target: <30s per pass)

### 13.5 Implementation Priority

| Priority | Task | Savings | Status |
|----------|------|---------|--------|
| 1 | Increase CPU threads (4→10) | ~2x on CPU | ✅ Applied |
| 2 | Q4_K_M model (already in use) | Baseline | ✅ Verified |
| 3 | Dragonfly LLM response cache | 60-90% repeats | ✅ Applied |
| 4 | Smaller model (Phi-3-mini 3.8B) | 2x on CPU | [ ] Needs download |
| 5 | Flash Attention + gpu_layers | 2-4x | ⚠️ Requires GPU |
| 6 | vLLM (if needed) | 2-4x overall | ⚠️ Requires GPU |

**Hardware Constraint:** No NVIDIA GPU available (Intel laptop with integrated graphics).
CPU optimizations applied. GPU optimizations deferred until hardware available.

**Applied (2026-01-24):**
- docker-compose.yaml: THREADS=10 (was 4)
- LocalAI container restarted with new config
- autonomous-ingest processing 25 remaining papers

---

## Phase 14: Compute Efficiency & Context Management 🆕 PLANNED

**Research Completed:** Handoff optimization + thinking minimization agents (2026-01-24)

### 14.1 Delta-Based State Transfer ✅ RESEARCH COMPLETE

| Technique | Method | Savings |
|-----------|--------|---------|
| **Delta Handoffs** | Transmit only changes | 50-70% context |
| **Merkle Tree Verification** | O(log N) state sync | Fast resume |
| **Hierarchical Summarization** | Session → Day → Week → Archive | 95% history compression |

**Delta Handoff Format:**
```yaml
handoff:
  base_hash: "abc123"  # Previous handoff hash
  delta:
    added: ["task1", "task2"]
    modified: ["goal.priority"]
    removed: []
  context_size: 1.2KB  # vs 8KB full state
```

### 14.2 Intelligent Context Loading ✅ RESEARCH COMPLETE

| Technique | Method | Savings |
|-----------|--------|---------|
| **L-RAG Lazy Loading** | Entropy-based gating | 26% retrieval reduction |
| **Context Editing** | Anthropic API feature | 84% token reduction |
| **Just-in-Time Retrieval** | Load on demand, not upfront | Variable |

**L-RAG Implementation:**
```python
def should_retrieve(query, context):
    entropy = compute_entropy(query, context)
    return entropy > RETRIEVAL_THRESHOLD  # e.g., 0.7
```

### 14.3 Thinking Budget Tiers ✅ RESEARCH COMPLETE

| Task Type | Thinking Budget | Model |
|-----------|----------------|-------|
| Simple lookup | 0 tokens | Haiku |
| Classification | 1K-2K tokens | Sonnet |
| Code generation | 4K-16K tokens | Sonnet/Opus |
| Architecture | 8K-32K tokens | Opus |

**Thinking Router:**
```python
THINKING_BUDGETS = {
    "simple_lookup": {"min": 0, "max": 0, "default": 0},
    "classification": {"min": 1024, "max": 2048, "default": 1024},
    "code_generation": {"min": 4096, "max": 16384, "default": 8192},
    "architecture": {"min": 8192, "max": 32000, "default": 16384},
}
```

### 14.4 Model Routing Optimization ✅ RESEARCH COMPLETE

| Router | Method | Savings |
|--------|--------|---------|
| **RouteLLM** | Classifier-based routing | 30-85% cost |
| **Semantic Complexity** | Embedding-based scoring | 40-60% |
| **Cascade** | Try cheap first, escalate | Variable |

**Current Router (model_router.py) Enhancement:**
```python
def route_with_complexity(task):
    complexity = estimate_complexity(task)
    if complexity < 0.3:
        return "localai"  # $0
    elif complexity < 0.6:
        return "codex"    # $
    else:
        return "claude"   # $$$
```

### 14.5 Prompt Caching ✅ RESEARCH COMPLETE

| Technique | Implementation | Savings |
|-----------|---------------|---------|
| **Anthropic Prompt Caching** | cache_control markers | 60-90% |
| **Semantic Prefix Sharing** | Common system prompts | 50-70% |
| **Dragonfly Response Cache** | Already deployed | Variable |

**Anthropic Cache Markers:**
```python
messages = [
    {
        "role": "system",
        "content": [
            {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
        ]
    }
]
```

### 14.6 Implementation Priority

| Priority | Task | Savings | Status |
|----------|------|---------|--------|
| 1 | Delta-based handoffs | 50-70% | [ ] |
| 2 | Prompt caching (Anthropic) | 60-90% | [ ] |
| 3 | Model routing enhancement | 30-85% | [ ] |
| 4 | Thinking budget tiers | 20-40% | [ ] |
| 5 | L-RAG lazy loading | 26% retrieval | [ ] |
| 6 | Hierarchical summarization | 95% history | [ ] |

**Expected improvement:** 60-80% reduction in Claude token costs

---

## Phase 15: Multi-Agent Architecture 🆕 PLANNED

**Research Completed:** Containerization + multi-agent communication agents (2026-01-24)

### 15.1 Communication Patterns ✅ RESEARCH COMPLETE

| Pattern | When | Latency |
|---------|------|---------|
| **gRPC** | Agent-to-agent, high volume | 60% lower than REST |
| **REST** | External APIs, human interfaces | Standard |
| **Pub/Sub (Dragonfly)** | Broadcast, event-driven | Already deployed |
| **Bidirectional Streaming** | Long-running coordination | Real-time |

**Recommended: gRPC + Protobuf**
```protobuf
service AgentCoordinator {
  rpc Execute(TaskRequest) returns (stream TaskUpdate);
  rpc Coordinate(stream AgentMessage) returns (stream AgentMessage);
}
```

### 15.2 Resilience Patterns ✅ RESEARCH COMPLETE

| Pattern | Purpose | Implementation |
|---------|---------|----------------|
| **Idempotent Handlers** | Safe retries | Hash-based dedup |
| **Circuit Breakers** | Prevent cascade failure | Backoff + fallback |
| **Dead Letter Queues** | Preserve failed messages | SQLite queue |
| **Leader Election** | Consensus decisions | Raft/etcd |

**Circuit Breaker Config:**
```python
@circuit_breaker(failure_threshold=5, recovery_timeout=30)
def call_agent(agent_id, task):
    ...
```

### 15.3 Container Orchestration ✅ RESEARCH COMPLETE

| Resource | Sidecar | Main Agent |
|----------|---------|------------|
| CPU | 50-100m | 500m-2000m |
| Memory | 64-128Mi | 512Mi-4Gi |
| GPU | None | As needed |

**Agent Container Template:**
```yaml
services:
  agent-worker:
    image: claude-agent:latest
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 2G
    environment:
      - DRAGONFLY_URL=redis://dragonfly:6379
      - GRPC_PORT=50051
```

### 15.4 Implementation Priority

| Priority | Task | Status |
|----------|------|--------|
| 1 | gRPC service definitions | [ ] |
| 2 | Circuit breaker middleware | [ ] |
| 3 | Agent container template | [ ] |
| 4 | Dragonfly pub/sub integration | [ ] |
| 5 | Leader election (if needed) | [ ] |

---

---

## Principles

1. **Iterative accretion** - One capability at a time
2. **No clashes** - Each addition validates before next
3. **Root-level preferred** - Scripts over hooks when possible
4. **Selective integration** - Only what adds power
5. **Research-driven** - Ground implementations in validated research
6. **Avoid over-engineering** - Simplest solution that solves the actual bottleneck

---

## Technology Tree Reference

See `.claude/TECH-TREE.md` for full visual dependency graph.

### 5 Emergent Development Pathways

```
PATHWAY 1: Semantic Router ──────────────────────────────────┐
  Intent classification → Model/Skill/Agent auto-selection  │
  Unlocks: 70% token savings, cost tracking                  │
                                                             │
PATHWAY 2: Agentic Mesh ─────────────────────────────────────┤
  gRPC agent bus → Parallel execution → Swarm patterns       │
  Unlocks: 10x throughput, emergent coordination             │
                                                             ├── EMERGENT
PATHWAY 3: Knowledge Synthesis ──────────────────────────────┤    AUTONOMY
  Cross-paper links → Contradiction detection → Hypotheses   │
  Unlocks: Novel insights, auto-research loops               │
                                                             │
PATHWAY 4: Adaptive Learning ────────────────────────────────┤
  Outcome tracking → Strategy evolution → Self-modification  │
  Unlocks: Continuous improvement, prompt optimization       │
                                                             │
PATHWAY 5: External Integration ─────────────────────────────┘
  Webhook mesh → Proactive scheduling → Workflow composition
  Unlocks: Full automation, self-directed tasks
```

---

## Next 5 Phases (14-18)

### Phase 14: Semantic Router
**Status:** PLANNED | **Prerequisites:** Phase 13 ✅

Core: MCP auto-router for hooks, skills, agents with model tiering.

| Component | Purpose | Model Tier |
|-----------|---------|------------|
| `semantic-router.py` | Intent classification | LocalAI (FREE) |
| `skill-selector.py` | Match intent to skill | LocalAI |
| `agent-dispatcher.py` | Route complex tasks | Codex |
| `cost-optimizer.py` | Track & minimize cost | LocalAI |

**MCP Router Config:**
```yaml
routing:
  summarize: {model: localai, skill: null}
  search: {skill: search-router, agent: scout}
  code: {model: codex, agent: kraken}
  reason: {model: claude}
  research: {agent: oracle}
```

### Phase 15: Knowledge Synthesis
**Status:** PLANNED | **Prerequisites:** Phase 14

| Component | Purpose |
|-----------|---------|
| `contradiction-finder.py` | Identify conflicting claims |
| `agreement-linker.py` | Strengthen consistent claims |
| `hypothesis-generator.py` | Novel claims from patterns |
| `research-gap-finder.py` | Identify missing knowledge |

### Phase 16: Adaptive Learning
**Status:** PLANNED | **Prerequisites:** Phase 15

| Component | Purpose |
|-----------|---------|
| `outcome-tracker.py` | Success/fail per strategy |
| `pattern-extractor.py` | Successful approach patterns |
| `strategy-evolver.py` | Generate new strategies |
| `prompt-optimizer.py` | Self-modify prompts |

### Phase 17: Agentic Mesh
**Status:** PLANNED | **Prerequisites:** Phase 16

| Component | Purpose |
|-----------|---------|
| `agent-bus.py` | gRPC inter-agent communication |
| `capability-registry.py` | Dynamic agent discovery |
| `contract-validator.py` | Enforce agent contracts |
| `swarm-coordinator.py` | Emergent multi-agent patterns |

### Phase 18: Emergent Autonomy
**Status:** PLANNED | **Prerequisites:** Phase 17

| Component | Purpose |
|-----------|---------|
| `proactive-planner.py` | Self-generate tasks |
| `goal-evolver.py` | Refine goals from outcomes |
| `workflow-composer.py` | Create new workflows |
| `self-monitor.py` | Detect & correct issues |

---

## Quick Reference Files

| File | Purpose |
|------|---------|
| `.claude/RESOURCE-MAP.md` | When to use what resource |
| `.claude/CODEBASE-INDEX.md` | Rapid file/function lookup |
| `.claude/TECH-TREE.md` | Full technology dependency tree |
| `task.md` | Current objectives |
| `thoughts/handoffs/` | Session state transfers |

---

## Current Status

**Phase 13:** ✅ COMPLETE (LLM caching, 45 papers processed)
**Phase 14:** 📋 PLANNED (Semantic Router)
**Capability Level:** L3 Autonomous → L4 Adaptive (building)
