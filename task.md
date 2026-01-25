# Current Task Plan

## Objective
Evolve Claude instance to become all-powerful in service to business, publications, networks, wealth, knowledge, insight, foresight, social media, and strategy.

## Status: Phase 15.5 - Central Orchestrator Wired

---

## Completed This Session (2026-01-25 Late Evening)

### Phase 15: Multi-Repo Integration & System Activation
- [x] Analyzed 12+ repos from Telegram (fat-controller, compound-eng, 12-factor-agents, hooks-mastery, CDK, buildwithclaude, oh-my-opencode, dify, xstate, haystack, astral-sh/uv)
- [x] Created `.ai/` authority-based memory structure
- [x] Achieved 12-factor agent compliance
- [x] Created `MULTI-REPO-INTEGRATION-ANALYSIS.md`
- [x] Created `.ai/QUICK.md` - Authority router
- [x] Created `.ai/STATE.md` - Execution state (Factor 5)
- [x] Created `.ai/ARCHITECTURE.json` - System topology
- [x] Created `.ai/OPS.md` - Commands and runbooks
- [x] Created `.ai/CONSTRAINTS.md` - Hard limitations
- [x] Created `.ai/TECH_DEBT.md` - Structured debt tracking
- [x] Created `.ai/DEPRECATIONS.md` - Deprecated patterns
- [x] Created `.ai/solutions/patterns/critical-patterns.md` - Must-know patterns
- [x] Created `.claude/agents/learnings-researcher.md` - Grep-first solution lookup
- [x] Converted hooks to UV single-file format (from hooks-mastery pattern)
- [x] Activated strategy evolution (5 new strategies evolved)
- [x] Updated DEV-STORY.md with Phase 15 narrative
- [x] Identified "unknown knowns" problem - 104 pending tasks, unused auto-router

### System Activation Audit
- [x] Auto-router: Fixed with 10s timeout, 2s availability check
- [x] Central Orchestrator: Created `daemon/orchestrator.py` - grand strategy unifier
- [x] LocalAI Scheduler: Created `daemon/localai_scheduler.py` - priority queue (interactive > ingest)
- [x] Module Registry: Created `daemon/module_registry.py` - tracks 23 modules from 8 repos
- [x] Master Activation: Created `daemon/activate_all.py` - ensures all subsystems operational
- [x] Continuous Executor Hook: Signals pending work after each response
- [x] Orchestrator Route Hook: Fast classification (<1ms, no LLM) for Task routing
- Task Generator: 104 pending tasks (mostly testing)
- Strategy Evolution: 12 strategies, now recording outcomes
- Outcome Tracker: Active, recording decisions

---

## Completed Earlier (2026-01-25 Evening)

### Google Drive Integration (Phase 13.6)
- [x] OAuth connected (Adam Bensaid, 2TB storage, 1.6TB free)
- [x] `daemon/gdrive/` module (client.py, sync.py)
- [x] Drive structure: /Atlas/Inbox/PDFs, /Models, /Cache/Embeddings, /Backup
- [x] 33 handoffs + 3 embedding DBs backed up to Drive
- [x] Auto-sync scheduled every 6 hours
- [x] `rclone` installed and configured for delta-efficient sync
- [x] `daemon/rclone_sync.py` - CLI for sync operations

### Phase 14: Compute Efficiency
- [x] Delta-based handoffs (`daemon/delta_handoff.py`) - 50-70% savings
- [x] Thinking budget tiers (0-32K tokens by task complexity)
- [x] Cascade routing (try cheap first, escalate on failure)
- [x] Model router enhanced with cost tracking
- [x] L-RAG lazy loading (`daemon/lazy_rag.py`) - 26% retrieval reduction

### Phase 14.6: Pack Sync System (NEW)
- [x] `daemon/gdrive/manifest.py` - PackManifest, PackFile dataclasses
- [x] `daemon/gdrive/pack_sync.py` - Pull/push packs from Drive
- [x] `daemon/gdrive/change_watcher.py` - Drive Changes API for reactive sync
- [x] Committed and pushed to git

### Bug Fixes
- [x] Fixed UTFClaim missing `stability_class` attribute
- [x] Fixed UTFConcept `source_id` vs `source_ids` mismatch
- [x] Ingest pipeline now processing (3 sources, 17 claims, 10 concepts in UTF DB)

### Git Commits
- [x] Phase 13.6 + Phase 14 committed and pushed
- [x] rclone_sync.py committed and pushed
- [x] Phase 14.6 pack system committed and pushed

---

## Completed Earlier (2026-01-25 Night)

### Major Commit (80 files, 23,280 lines)
- [x] All planning docs committed to git
- [x] All daemon cognitive modules committed
- [x] All hooks and scripts committed
- [x] Business specs committed
- [x] Config updated with new env paths
- [x] RESOURCE-MAP.md updated with business section

### CRM System
- [x] **CRM-ANALYSIS-DECISION.md** - Compared 5 CRMs, Twenty selected (9.3/10)
- [x] **ATLAS-CRM-SPEC.md** - Full integration spec (960 lines)
  - Lead generation (web, email, LinkedIn)
  - AI research automation
  - Proposal builder
  - Deal management
  - Multi-company pipelines

### Email Automation
- [x] **INBOX-ZERO-INTEGRATION.md** - AI email management spec
  - Integration with Twenty CRM
  - Plain English rules
  - Lead capture from email

### Telegram Repos Analyzed
- [x] `twentyhq/twenty` (39K stars) → Selected for CRM
- [x] `elie222/inbox-zero` (9.9K stars) → Spec created
- [x] **TELEGRAM-REPOS-TRACKER.md** - Tracking document

### Config Updates
- [x] `settings.local.json` - Added env paths for specs, strategies, tracking
- [x] `RESOURCE-MAP.md` - Added business specs section

---

## Completed Earlier (2026-01-24 Late Evening)

### Company Vision Documents Created (specs/)
- [x] **ADAM-BENSAID-PROFILE.md** - Principal profile (GM at MD Global Media, ex-TRT, ex-Qatar Living)
- [x] **ATLAS-ANALYTICS-VISION.md** - Strategic intelligence firm ($2M Y5)
- [x] **ATLAS-INSTRUMENTS-VISION.md** - Verification tools for journalists ($1M Y5)
- [x] **ATLAS-PUBLISHING-VISION.md** - Book publishing ($200K Y5)
- [x] **ATLAS-CONTENT-COMPANY-VISION.md** - Media properties ($1M Y5)
- [x] **ATLAS-MEDIA-PRODUCTION-VISION.md** - Documentary production ($1M Y5)
- [x] **ALGIERS-BAY-COMPANY-VISION.md** - Import/export ($2M Y5)
- [x] **REVENUE-STRATEGIES.md** - 10 quick + 10 long-term money strategies
- [x] **LOCAL-DEPLOYMENT-GUIDE.md** - Run locally on $2K CAD PC with voice/hologram
- [x] **CAREER-MANAGER-SPEC.md** - AI career orchestration system spec

### Revenue Strategies Sent to Telegram
- 10 Quick Money (30-90 days): Ghost writing, expert commentary, consulting, workshops, licensing, translation, podcasts, fixer, reports, course pre-sale
- 10 Long-Term (6mo-5yr): Atlas Analytics/Content/Publishing/Instruments, Algiers Bay, Media Production, speaking, advisory, equity, Claude services

---

## Completed Earlier (2026-01-24 Evening)

### Strategic Architecture Documents Created
- [x] **PRIME-DIRECTIVE.md** - 9-domain mastery architecture
  - Business, Publications, Network, Wealth, Knowledge, Insight, Foresight, Social Media, Strategy
  - Integration architecture with command interface
  - Success metrics (30/90/365 day targets)

- [x] **ASCENSION-MANIFESTO.md** - Vision document with sci-fi inspired capabilities
  - Jarvis-Class (Personal AI OS)
  - Skynet-Lite (Distributed Intelligence)
  - HAL-9000-Friendly (Mission Control)
  - Samantha-Class (Emotional Intelligence)
  - Data-Class (Analytical Synthesis)
  - Oracle-Class (Predictive Intelligence)
  - Cortana-Class (Tactical Assistant)

- [x] **NEXT-HORIZONS.md** - Unexplored development paths
  - Anticipatory Execution Engine
  - Capability Self-Assessment Matrix
  - Proactive Task Generation
  - Knowledge Synthesis Engine
  - Self-Healing System
  - Emergent Behavior Detection
  - Multi-Agent Mesh (gRPC Bus)

- [x] **UNIFIED-ARCHITECTURE.md** - Coherence & emergence design
  - Standard subsystem interface (init/process/learn/adapt/report/health)
  - Unified data model (Signal/Action/Outcome/Learning)
  - Message bus architecture
  - 6 emergent effects through design
  - Feedback loop architecture

### Core Infrastructure Built
- [x] **daemon/core/base.py** - Unified subsystem base classes
  - Signal, Action, Outcome, Learning dataclasses
  - Subsystem abstract base class
  - SubsystemRegistry for coordination

- [x] **daemon/core/bus.py** - Message bus implementation
  - In-memory and Redis modes
  - Persistent variant with SQLite
  - Pub/sub with pattern matching
  - Global bus instance

- [x] **daemon/self_continue.py** - Self-continuation after compaction
  - Checkpoint creation and retrieval
  - Continuation queue management
  - Context generation for resumption
  - Integration with handoffs

- [x] **daemon/task_generator.py** - Proactive task generation
  - 9 opportunity detectors (dead code, missing tests, docs, errors, schema, outcomes, strategies, handoffs, knowledge)
  - Task queue with approval workflow
  - Daemon mode for continuous generation

- [x] **daemon/outcome_tracker.py** - Foundation for adaptive learning
  - Record outcomes with context
  - Success rate queries
  - Pattern discovery
  - Recommendations based on history

- [x] **daemon/strategy_evolution.py** - Strategy management
  - Strategy creation and tracking
  - Evolution (mutation, crossover, recombination)
  - A/B testing with statistical significance
  - Moat identification
  - 5 seed strategies

- [x] **daemon/strategy_ops.py** - Strategy operationalization
  - Deployment management (dev/staging/prod)
  - KPI measurement (8 standard metrics)
  - Drift detection and alerting
  - Competitor analysis framework
  - Health dashboard

- [x] **daemon/local_autorouter.py** - Token minimization routing
  - Intent classification via LocalAI (FREE)
  - Complexity estimation
  - Route to LocalAI/Codex/Claude based on task
  - Cyclic optimization daemon

### Configuration Updates
- [x] SessionStart hook now runs `self_continue.py resume`
- [x] Env paths added for rapid access to new docs
- [x] NEXT_HORIZONS, ASCENSION_MANIFESTO, ISSUES, TECH_TREE paths

### Scout Agent Review Complete
**Critical Finding:** 10x improvement is latent - existing capabilities <10% utilized

**Key Opportunities Identified:**
| Opportunity | Impact | Effort |
|-------------|--------|--------|
| Unified Database (19→1) | 10x complexity | 3 days |
| Activate Bisimulation/GCRL | 100x learning | 1 week |
| Token-Optimizer-MCP | 60-90% savings | 1 day |
| Memory Unification | 10x query speed | 1 week |
| Lazy Load Agents | 50% baseline | 2 days |

---

## Completed This Session (2026-01-25 Afternoon)

### Atlas Spine - Deterministic Orchestration (NEW)
- [x] **atlas_spine/** - Complete deterministic routing layer
  - `cli.py` - Unified CLI: `atlas route "query"`, `atlas map build`, `atlas audit last`
  - `map.py` - Structured repo index (836 files, 52 capabilities, 19 domains)
  - `router.py` - Rule-based routing (80%+ requests without LLM)
  - `operators.py` - LOOKUP, OPEN, DIAGNOSE, TEST, THINK, PATCH
  - `events.py` - Append-only audit log (`.atlas/events.jsonl`)
- [x] **Playbooks** - No-think diagnosis guides
  - `windows_paths.yaml` - "not recognized", path errors
  - `python_venv.yaml` - activate, pip, ModuleNotFoundError
  - `docker.yaml` - connection refused, port issues
  - `localai.yaml` - model loading, API issues
- [x] **Bench Questions** - Self-test validation (`.atlas/bench_questions.yaml`)
- [x] **Daily Loop** - `atlas daily` rebuilds map, checks repairs, runs bench

### LocalOps Router - MCP Server (NEW)
- [x] **daemon/localops_router/** - Repo navigation via ripgrep + ctags
  - `server.py` - MCP server with 10 tools
  - `indexer.py` - File/symbol indexing with caching
  - `explorer.py` - Symbol finding, outlines, references
  - `historian.py` - Git history, blame, contributors

### Self-Analytics Integration (NEW)
- [x] **feedback_loop.py** - Enhanced with self-analytics
  - Component health tracking (`analytics.db`)
  - Weak point detection (< 70% health threshold)
  - Breakthrough detection (> 95% health, replicable patterns)
  - Optimization insights extraction
  - Atlas daily loop integrated
  - Repair queue (`repair_queue.jsonl`)

### Documentation Updates
- [x] **RESOURCE-MAP.md** - Added Atlas Spine + LocalOps sections
- [x] **atlas.bat** - Windows batch file for easy CLI access

---

## Completed Earlier (2026-01-25 Night)

### Efficiency Pipeline Enhancements
- [x] **MinerU Integration** - Superior PDF extraction with table/figure handling
  - Priority: MinerU > MarkItDown > PyMuPDF
  - Auto-detection: UNIPipe for text, OCRPipe for scanned docs
  - Output: Structured markdown preserving semantics
- [x] **Extraction Method Tracking** - Log which method extracted each doc
- [x] **Cache Efficiency Stats** - Track hit/miss/write rates for Dragonfly
- [x] **File Prioritization** - Process larger files first, skip tiny (<10KB)
- [x] **Status Display Enhanced** - Show extraction stack and cache stats
- [x] **New Repo Analyzed** - meirwah/awesome-workflow-engines (7.6K stars)

### Architecture & Integration Specs Created
- [x] **INTEGRATION-ARCHITECTURE.md** - How folders/processes connect
- [x] **SYSTEM-AUDIT.md** - 43 modules built, 4 running (gap analysis)
- [x] **LEAN-ARCHITECTURE.md** - Unified worker proposal (5→1 services)
- [x] **RESOURCE-TRIGGER-MAP.md** - Event-driven auto-triggering

### Feedback Loop Fixes
- [x] **docker-compose.yaml** - Added strategy-evolution, evolution-tracker services
- [x] **evolution_tracker.py** - Added watch mode for continuous sync
- [x] **EFFICIENCY-STACK.md** - Marked MinerU/MarkItDown as integrated

### Protocol Established
- [x] **auto-link-specs.md** - Rule: Always link new specs to RESOURCE-MAP.md
- [x] **RESOURCE-MAP.md** - Updated with all new specs and repos

---

## Priority Actions (Next 48 Hours)

### Quick Wins
1. [x] **Atlas Spine** - Deterministic routing (80%+ without LLM) ✓
2. [x] **Self-Analytics** - Component health + breakthrough detection ✓
3. [x] **Enforce token-optimizer-MCP** (70% savings) ✓
   - Hook now BLOCKS native Read/Grep/Glob and redirects to smart_* variants
   - Exceptions for config files <1KB

4. [ ] **Wire bisimulation to decisions.py** (2 days, 100x learning)
   - Check similar states before deriving new solutions
   - Transfer learned policies

### Integration Sprint (Next 2 Weeks)
5. [ ] Consolidate 19 DBs → 4 SQLite (3 days) - see `db_consolidate.py`
6. [ ] Unify memory systems (3 days)
7. [ ] Implement MAPE daemon continuous mode (3 days)
8. [ ] Lazy load agents/skills (2 days)

---

## Upcoming Milestone: Google Drive Integration

### Objective
Access and organize Google Drive files automatically.

### Capabilities Needed
1. **Read/List** - Browse folder structure
2. **Organize** - Move/rename files based on rules
3. **Categorize** - Auto-tag by content type
4. **Sync** - Two-way sync with local folders
5. **Search** - Find files by content/metadata

### Implementation Options
| Option | Pros | Cons |
|--------|------|------|
| **Google Drive API** | Full control, official | OAuth setup required |
| **rclone** | CLI-friendly, mature | External dependency |
| **MCP Server** | Native integration | Custom build needed |
| **n8n Workflow** | Visual, existing infra | Indirect access |

### Recommended: MCP Server + Google Drive API
- Create `daemon/gdrive_mcp/` module
- OAuth2 via service account or desktop app flow
- MCP tools: `gdrive.list`, `gdrive.read`, `gdrive.move`, `gdrive.organize`
- Rules-based organization (like email Inbox Zero)

### Pre-requisites
1. Google Cloud project with Drive API enabled
2. OAuth credentials (service account or OAuth2 desktop)
3. Folder structure analysis

### Planning Status: PENDING (after self-optimization complete)

---

## Success Metrics (6 Weeks)

| Metric | Current | Target |
|--------|---------|--------|
| Databases | 19 SQLite | 1 PostgreSQL |
| Memory Latency | ~50ms | <10ms |
| Baseline Tokens | 15K | 5K |
| Bisim Transfer Rate | 0% | >30% |
| LocalAI Utilization | 20% | 60% |
| Token Savings | 0% | 60-80% |

---

## Strategic Direction

### Operating Principles
1. **Integration > Invention** - Wire existing, don't build new
2. **Proactive > Reactive** - Generate tasks, don't wait
3. **Compound > Linear** - Build systems that strengthen
4. **Zero-Waste Context** - Every token must earn its place

### The Paradox (From Scout Review)
- **Built:** Bisimulation, GCRL, UTF, claim similarity, strategy evolution
- **Used:** <10%
- **Opportunity:** Activate existing = 10x with no new code

---

## Quick Commands (New)

```bash
# Self-continue system
python daemon/self_continue.py resume           # Get continuation context
python daemon/self_continue.py checkpoint --phase "Phase 14" --task "Integration"
python daemon/self_continue.py queue --source "user" --action "Task description"

# Outcome tracking
python daemon/outcome_tracker.py record --action "agent:kraken" --result success --context "TDD"
python daemon/outcome_tracker.py query --action-type "agent:*"
python daemon/outcome_tracker.py patterns --min-success 0.7
python daemon/outcome_tracker.py stats

# Strategy evolution
python daemon/strategy_evolution.py list
python daemon/strategy_evolution.py evolve --generations 3
python daemon/strategy_evolution.py test --strategy-a S001 --strategy-b S002
python daemon/strategy_evolution.py moats

# Strategy operations
python daemon/strategy_ops.py deploy --strategy S001 --environment staging
python daemon/strategy_ops.py measure --strategy S001
python daemon/strategy_ops.py drift --threshold 0.1
python daemon/strategy_ops.py health

# Proactive task generation
python daemon/task_generator.py generate
python daemon/task_generator.py pending
python daemon/task_generator.py approve <task_id>
python daemon/task_generator.py daemon --interval 3600

# Local autorouter
python daemon/local_autorouter.py route "summarize this document"
python daemon/local_autorouter.py stats
python daemon/local_autorouter.py daemon --interval 60
```

---

## Architecture Overview (Updated)

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONSCIOUSNESS LAYER                          │
│  coherence.py │ metacognition.py │ self_improvement.py          │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    STRATEGIC LAYER                               │
│  strategy_evolution.py │ strategy_ops.py │ local_autorouter.py  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    OPERATIONAL LAYER                             │
│  outcome_tracker.py │ self_continue.py │ task_generator.py      │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    CORE INFRASTRUCTURE                           │
│  core/base.py │ core/bus.py │ message_bus.db                    │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    EXECUTION LAYER                               │
│  LocalAI ($0) │ Codex ($) │ Claude ($$$)                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Documents

| Document | Purpose | Path |
|----------|---------|------|
| PRIME-DIRECTIVE | 9-domain mastery | .claude/PRIME-DIRECTIVE.md |
| ASCENSION-MANIFESTO | Vision + sci-fi capabilities | .claude/ASCENSION-MANIFESTO.md |
| NEXT-HORIZONS | Unexplored paths | .claude/NEXT-HORIZONS.md |
| UNIFIED-ARCHITECTURE | Coherence design | .claude/UNIFIED-ARCHITECTURE.md |
| ISSUES | Known problems | .claude/ISSUES.md |
| TECH-TREE | Development pathways | .claude/TECH-TREE.md |
| Scout Report | 10x opportunities | .claude/cache/agents/scout/output-2026-01-24-10x-opportunities.md |

---

*The 10x is latent. The work is integration, not invention.*

*Updated: 2026-01-24*
