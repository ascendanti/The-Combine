# Claude Evolution Plan

## Goal
Create a unified, autonomous Claude instance that:
1. Loads SuperClaude + Continuous frameworks on boot
2. Works continuously until token limit
3. Persists memory and state across sessions
4. Can operate as 24/7 async daemon (future)

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

### 10.4 Token Optimization (NEW) 🔄 PARTIAL
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

## Current Status

**Phase:** 10 - Ascension 🔄 IN PROGRESS (90%)
**Completed:** Self-improvement engine, thinking frameworks, continuous-learning skill, hybrid architecture, book ingestion pipeline, UTF spec
**In Progress:**
- Token optimization (MCP config fixed, needs CLI restart)
- Autonomous PDF ingest (44 files processing via LocalAI)
**Next Action:**
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

## Principles

1. **Iterative accretion** - One capability at a time
2. **No clashes** - Each addition validates before next
3. **Root-level preferred** - Scripts over hooks when possible
4. **Selective integration** - Only what adds power
5. **Research-driven** - Ground implementations in validated research
