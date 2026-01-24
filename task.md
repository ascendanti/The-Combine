# Current Task Plan

## Objective
Evolve Claude instance with autonomous async daemon capabilities + adaptive learning architecture.

## Status: Phase 12 Complete, Phase 13 Planned

## Completed This Session (2026-01-24)

### Phase 12.4 Completion
- [x] **Memory Integration** (daemon/memory.py)
  - recall_similar_claims() with UTF closeness scoring
  - get_cross_paper_insights() for multi-paper concepts
  - get_related_claims() by claim ID
  - get_claim_clusters() for semantic groupings
  - CLI: claims, cross-paper, clusters, refresh-claims

- [x] **SQLite Save Fix** (daemon/autonomous_ingest.py)
  - Added store_utf_to_sqlite() - saves claims to utf_knowledge.db
  - init_utf_db() creates proper tables
  - Container rebuilt with fix

- [x] **Dashboard Visualization**
  - api.py: 5 new endpoints (/abstractions, /transfers, /claims/*)
  - bisimulation.py: get_state_abstractions(), get_recent_transfers()
  - dashboard.html: 3 new cards (State Abstractions, Transfers, Clusters)

### Phase 13 Planning
- [x] Assessed Telegram proposal (Multi-Agent Swarm with GA)
- [x] Counter-proposed simpler solution targeting actual bottleneck (LLM speed)
- [x] Added Phase 13 to EVOLUTION-PLAN

### Research Synthesis Complete (2026-01-24)
- 5 research agents completed with comprehensive findings
- Reports saved to `.claude/cache/agents/oracle/`
- EVOLUTION-PLAN.md updated with Phase 13-15 implementation details

**Key Research Findings:**
| Area | Technique | Impact |
|------|-----------|--------|
| LocalAI Speed | Q4_K_M + NuExtract + Flash Attention | 3-5x throughput |
| Context Efficiency | Delta handoffs + L-RAG | 50-70% savings |
| Token Cost | Prompt caching + model routing | 60-90% reduction |
| Multi-Agent | gRPC + circuit breakers | 60% lower latency |
| Profiling | vLLM PagedAttention + py-spy | 85-92% GPU util |

### Phase 13 Implementation Applied (2026-01-24)

**13.1 CPU Optimization:**
- docker-compose THREADS: 4 → 10 (2.5x CPU utilization)
- LocalAI restarted with optimized config

**13.3 Dragonfly LLM Cache:**
- Added redis client to autonomous_ingest.py
- 3 LLM call sites now check cache before calling LocalAI
- Cache TTL: 24 hours (LLM_CACHE_TTL = 86400)
- Dockerfile updated with redis dependency
- Container rebuilt and restarted

### Phase 13 Complete (2026-01-24)

**Ingestion Pipeline:**
- [x] 45 papers processed (all complete)
- [x] 0 papers remaining in watch folder
- [x] SQLite schema fixes (abstract, quality_status, created_at, content, page_num)
- [x] UTFExcerpt attribute mapping fixed (text/location vs content/page_num)
- [x] Logging updated to handle both UTF and legacy modes

**Infrastructure:**
- [x] Dragonfly LLM cache: 41 keys cached
- [x] All containers healthy (autonomous-ingest, localai, kg-summary-worker, synthesis-worker, dragonfly-cache)

### Telegram Proposal Response (2026-01-24)

Received local agents architecture proposal. Assessment:

| Proposed | Already Have | Status |
|----------|--------------|--------|
| explorer/ | utf_extractor + memory.py | Done |
| historian/ | thoughts/handoffs/ + hooks | Done |
| research_documenter/ | autonomous_ingest + synthesis_worker | Done |
| Local model rules | model_router.py | Done |

**New addition from proposal:**
- [x] Created `.claude/hooks/git-post-commit.py` - Historian checkpoint on commits

---

## Phase 10 Complete (Ascension) - 2026-01-23

## Completed This Session (2026-01-23)

### Phase 10.4: Claim Classification & Similarity ✅ NEW
- [x] UTFClaim extended with slug_code, taxonomy_tags, utf_vector fields
- [x] LocalAI generates semantic slugs (PROMPT_CLASSIFY_CLAIM in utf_extractor.py)
- [x] claim_similarity.py created - Cross-paper claim matching index
  - UTF closeness values (slug + taxonomy + form matching)
  - Claim clustering for related concepts across papers
  - find_similar(), find_similar_by_id(), get_cross_paper_links()
- [x] Obsidian export updated with classification metadata
- [x] Freqtrade module added as git submodule (modules/freqtrade)
- [x] UTF DB schema updated with slug_code, taxonomy_tags columns
- [x] EVOLUTION-PLAN.md updated to 95%

### Phase 12: Research Integration Layer ✅ COMPLETE
- [x] **12.1 Bisimulation Foundation** (daemon/bisimulation.py)
  - BisimulationState and BisimulationMetric dataclasses
  - Goal-conditioned bisimulation distance computation
  - State abstraction (group bisimilar states)
  - Policy transfer validation with confidence scoring
  - SQLite persistence + JSON cache
- [x] **12.2 Goal-Conditioned RL** (daemon/gcrl.py)
  - Goal and Trajectory dataclasses
  - Hindsight Experience Replay (HER) - relabel failed trajectories
  - Causal factor extraction from successful trajectories
  - Policy learning and recommendation
  - Virtual experience generation
- [x] **12.4 Integration Wiring**
  - coherence.py: find_similar_goals(), suggest_policy_transfer()
  - decisions.py: get_policy_guided_decision(), record_outcome_with_trajectory()
  - decisions.py: find_similar_decisions() using bisimulation

### KG Token Efficiency (Phase 11 Foundation) ✅
- [x] Fixed all TypeScript hook compilation errors
- [x] Created `kg-context-gate.py` - PreToolUse hook that AUGMENTS reads with cached KG context
  - Based on claude-context-extender pattern (inject, don't block)
  - Checks KG for prior summaries, adds as additionalContext
- [x] Created `kg-context-store.py` - PostToolUse hook for async LLM summarization
  - Queues files to task_queue (non-blocking)
  - Uses existing daemon infrastructure
- [x] Created `daemon/kg_summary_worker.py` - Background worker
  - Processes summarization queue
  - Routes to LocalAI (FREE) via model_router
  - Stores LLM-generated summaries to KG (not heuristic extraction)
- [x] Registered hooks in settings.local.json
- [x] Verified integration works (tasks queue correctly)

### Infrastructure Optimization ✅
- [x] Dragonfly cache increased to 8GB (from 4GB)
- [x] MCP stability improved:
  - Created global `~/.claude/.mcp.json`
  - Installed `mcp-knowledge-graph` globally (no more npx cold starts)
  - Updated project `.mcp.json` to use global install
- [x] Reference frameworks cloned:
  - `reference-frameworks/claude-context-extender` - RAG for large docs
  - `reference-frameworks/claude-modular` - Token optimization patterns
- [x] Container cleanup (removed orphan gallant_bhabha)

### Previously Completed This Session

### Book Ingestion Pipeline ✅
- [x] `book-ingest.py` - Hierarchical RAG for technical documents
  - Smart chunking preserving formulas/concepts
  - Multi-level summarization (paragraph → section → chapter → book)
  - Concept extraction with relationship mapping
  - Knowledge graph integration
- [x] `book-query.py` - Query interface for ingested books
- [x] `book_watcher.py` - File system watcher daemon
  - Watchdog-based monitoring
  - Background processing queue
  - Deduplication via file hashing
  - Memory system integration

### MAPE Controller Foundation ✅
- [x] `daemon/controller.py` - Adaptive control system
  - Monitor-Analyze-Plan-Execute cycle
  - Metric tracking and trending
  - Gap analysis (actual vs target)
  - Action planning with predicted outcomes
  - Confucius-style strategy introspection
  - Feedback loop for learning

### Hook Cleanup ✅
- [x] Consolidated SessionStart hooks into `session-start-clean.py`

## Phase 11 Planning (Approved Stack)

Based on research synthesis - integrating:
1. **claude-context-extender** - Semantic chunking + retrieval ✅ Adapted for KG hooks
2. **Confucius pattern** - Tool/strategy introspection
3. **MAPE control loop** - Adaptive optimization

### Completed
- [x] KG hooks follow claude-context-extender's LLM summarization pattern
- [x] Async summarization via task_queue + model_router (LocalAI = FREE)
- [x] TypeScript hooks compilation fixed
- [x] **Controller wired to book-ingest.py**:
  - `get_adaptive_settings()` - Gets chunk_size/overlap from MAPEController
  - `report_metrics_to_controller()` - Reports comprehension, chunk_quality, token_efficiency
  - Runs MAPE cycle after each ingestion for adaptive learning
- [x] Fixed Unicode encoding issues (replaced emojis with ASCII)

### Completed This Session (continued)
- [x] Fixed Unicode encoding error in kg_summary_worker.py
- [x] Added semantic coherence scoring to book-query.py
  - `compute_coherence_score()` - TF-based similarity scoring
  - `report_retrieval_metrics()` - Reports to MAPE controller
  - `--scored` flag for queries with coherence metrics
- [x] Created `daemon/feedback_bridge.py` - Decision-informed control
  - Bridges MAPE controller + DecisionEngine for strategic learning
  - Multi-criteria action selection (improvement, confidence, risk)
  - Preference learning from outcomes

### LocalAI + Codex Token-Precious Architecture ✅ NEW
- [x] LocalAI installed and running (Mistral 7B, 4.1GB)
- [x] Enhanced `model_router.py` with tiered routing:
  - LocalAI ($0): summarize, embed, translate, simple Q&A
  - Codex ($): code generation, code review, routine tasks
  - Claude ($$$): architecture, complex reasoning only
- [x] Added complexity estimation for smart escalation
- [x] Created `token-benchmark.py` for efficiency measurement
- [x] Created `synthesis_worker.py` for periodic knowledge growth via Codex
- [x] Cloned `claudelytics` for token analytics

### Continuous Learning Pipeline Architecture
```
PHASE 1: LocalAI (FREE) - Persistent PDF Processing
  PDFs -> Chunks -> Summaries -> Knowledge Graph
  Runs continuously in background

PHASE 2: Codex ($) - Periodic Synthesis (daily/weekly)
  Cross-reference entries -> Find patterns -> Meta-learnings
  Propose connections -> Update capabilities

PHASE 3: Claude ($$$) - Premium Reasoning
  Query pre-processed KG (200 tokens vs 5000)
  Complex architecture + novel problems only
```

### Token Analytics + Self-Improvement ✅ NEW
- [x] Created `.claude/scripts/token-tracker.py` - Python port of claudelytics
  - Daily/session token usage reports
  - Cost tracking with current pricing (Opus/Sonnet/Haiku)
  - Real-time watch mode
  - CSV export optional
- [x] Created `daemon/token_monitor.py` - Spike detection + logging
  - Detects >2 std dev spikes in token usage
  - Logs spike context to SQLite + KG for learning
  - Pattern analysis for optimization recommendations
  - Continuous watch mode
- [x] Created `.claude/scripts/kg-obsidian-sync.py` - KG to Obsidian
  - Each entity becomes a markdown note
  - Relations become [[wikilinks]]
  - Continuous sync mode
  - Vault: `~/Documents/Obsidian/ClaudeKnowledge/`

### Next Actions
1. [x] LocalAI running with Mistral 7B
2. [x] Autonomous PDF ingestion pipeline (LocalAI - FREE)
3. [x] OpenAI API key configured for Codex synthesis
4. [x] KG consolidation added to synthesis worker
5. [x] Token analytics + spike monitoring
6. [x] KG-Obsidian permanence layer
7. [x] UTF Research OS Specification created (`specs/UTF-RESEARCH-OS-SPEC.md`)
8. [x] UTF Iterative Ingest tool (`.claude/scripts/utf-ingest.py`)
9. [x] UTF Context Filter hook (`.claude/hooks/utf-context-filter.py`)
10. [ ] Test end-to-end UTF extraction pipeline
11. [x] Wire UTF context filter into settings.local.json
12. [ ] Build scaffold completion worker (fill 7-slot gaps iteratively)

### Weekend Priority: Token Efficiency Fix
**Target: 60-90% reduction in context usage**

1. [ ] **Activate token-optimizer-mcp** for all sessions
   - Primary compression + caching layer
   - 60-90% reduction potential

2. [ ] **Integrate claude-context-extender**
   - Smart chunking + retrieval
   - Targets the 51% "Messages" bloat

3. [ ] **Move bulk ingestion to LocalAI + LocalRecall**
   - 70-90% reduction on PDF/book processing
   - Keep heavy lifting off Claude context

4. [ ] **Lazy-load skills** (wshobson/agents pattern)
   - Reduce baseline token overhead

5. [ ] **Enable UTF semantic RAG**
   - Pre-processed claims replace raw reads
   - 200 tokens vs 5000 raw

6. [ ] **Tune FewWord thresholds**
   - Aggressive offloading to scratch

### Worker Separation (No Overlap)
| Worker | Purpose | Content Type | Trigger |
|--------|---------|--------------|---------|
| `autonomous_ingest` | PDF/book ingestion | Books, papers | Watches GateofTruth |
| `kg_summary_worker` | Code file summaries | Source code | Claude file reads (hooks) |
| `synthesis_worker` | Pattern synthesis + KG consolidation | Existing KG | Periodic (24h) via Codex |

## Book Watch Folder
```
C:\Users\New Employee\Documents\GateofTruth\
```
Drop PDFs here → auto-ingested → queryable via `book-query.py`

## Quick Commands

```bash
# Start book watcher daemon
python daemon/book_watcher.py

# Manually ingest a book
python .claude/scripts/book-ingest.py "path/to/book.pdf"

# Query books
python .claude/scripts/book-query.py "gradient descent"
python .claude/scripts/book-query.py --summary <book_id>
python .claude/scripts/book-query.py --concepts

# Run MAPE controller cycle
python daemon/controller.py --cycle
python daemon/controller.py --status

# Check watcher status
python daemon/book_watcher.py --status
python daemon/book_watcher.py --list-books

# KG Summary Worker (process queued file summaries)
python daemon/kg_summary_worker.py            # Process once
python daemon/kg_summary_worker.py --watch    # Continuous mode
python daemon/kg_summary_worker.py --stats    # Check queue

# Feedback Bridge (decision-informed control)
python daemon/feedback_bridge.py --status     # Show bridge status
python daemon/feedback_bridge.py --cycle      # Run MAPE with decisions
python daemon/feedback_bridge.py --decide     # Show what action would be selected

# Query with coherence scoring
python .claude/scripts/book-query.py --scored "query"  # Reports to controller

# Token Analytics
python .claude/scripts/token-tracker.py --today       # Today's usage
python .claude/scripts/token-tracker.py --daily       # Daily breakdown
python .claude/scripts/token-tracker.py --watch       # Real-time monitoring

# Token Spike Monitor (for optimization learning)
python daemon/token_monitor.py                        # Scan for recent spikes
python daemon/token_monitor.py --watch                # Continuous monitoring
python daemon/token_monitor.py --analyze              # Pattern analysis + recommendations

# KG to Obsidian Sync
python .claude/scripts/kg-obsidian-sync.py            # One-time sync
python .claude/scripts/kg-obsidian-sync.py --watch    # Continuous sync
```

## Architecture Overview

```
+-------------------------------------------------------------+
|  AUTONOMOUS WORKERS (Run 24/7 in Docker - Zero Claude Cost) |
+-------------------------------------------------------------+
|                                                             |
|  [autonomous_ingest.py] - PDF/Book Processing               |
|    Watches: GateofTruth folder                              |
|    Uses: PyMuPDF (text) + LocalAI (summaries)               |
|    Output: Structured KG entities with concepts/keywords    |
|    Cost: $0 (LocalAI)                                       |
|                                                             |
|  [kg_summary_worker.py] - Code File Summaries               |
|    Trigger: Claude reads a file (via hooks)                 |
|    Uses: LocalAI summarization                              |
|    Output: File summaries for context augmentation          |
|    Cost: $0 (LocalAI)                                       |
|    Interval: Every 2 hours                                  |
|                                                             |
|  [synthesis_worker.py] - Knowledge Growth + Consolidation   |
|    Trigger: Periodic (every 24h)                            |
|    Uses: Codex (gpt-4o-mini) for pattern synthesis          |
|    Tasks:                                                   |
|      - KG consolidation (merge duplicates, prevent bloat)   |
|      - Cross-reference concepts                             |
|      - Generate meta-learnings                              |
|      - Identify knowledge gaps                              |
|    Cost: ~$0.01/cycle (Codex)                               |
|                                                             |
+-------------------------------------------------------------+
|  HOOKS (Augment Claude Sessions)                            |
|  PreToolUse: kg-context-gate (inject cached KG context)     |
|  PostToolUse: kg-context-store (queue files for summary)    |
+-------------------------------------------------------------+
|  STORAGE LAYER                                              |
|  - knowledge-graph.jsonl (ALL knowledge: books, code, etc)  |
|  - ingest.db (processed files tracking)                     |
|  - synthesis.db (patterns, meta-learnings, connections)     |
+-------------------------------------------------------------+
|  QUERY (When Claude Needs Information)                      |
|  Claude queries pre-processed KG -> 200 tokens vs 5000      |
+-------------------------------------------------------------+
|  SELF-IMPROVEMENT LOOP                                      |
|  [token_monitor.py] - Spike detection + logging             |
|    - Detects anomalies in token usage                       |
|    - Logs spikes to DB + KG for pattern learning            |
|    - Generates optimization recommendations                 |
|  [kg-obsidian-sync.py] - Permanence layer                   |
|    - Syncs KG to Obsidian vault as markdown                 |
|    - Creates neural-cluster-like note structure             |
+-------------------------------------------------------------+
```

### Cost Flow
```
PDF drops in GateofTruth
    |
    v
autonomous_ingest (LocalAI) --> KG         [FREE]
    |
    v (daily)
synthesis_worker (Codex) --> Patterns      [$0.01]
    |
    v (on demand)
Claude queries KG --> Answer               [$$$ only for reasoning]
```

## Dependencies to Install

```bash
# Required
pip install watchdog docling

# Already installed
# token-optimizer-mcp, dragonfly (docker), sqlite3
```
