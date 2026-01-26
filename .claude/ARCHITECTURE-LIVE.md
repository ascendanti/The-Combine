# ARCHITECTURE-LIVE.md
## MANDATORY READ ON EVERY SESSION - This is your brain map

---

## CRITICAL: What Actually Runs vs What Exists

### ACTIVE (Wired into hooks):
```
SessionStart     → cleanup-mcp.py, daemon-autostart.py, mcp_health.py warmup, init_spine.py, session-briefing.py, self_continue.py
UserPromptSubmit → deterministic_router.py (NOW WIRED TO orchestrator.fast_classify!)
PreToolUse       → auto-cache-pre.py, pre-create-check.py (Write), pre-command-optimize.py (Bash)
PostToolUse      → unified-post-tool-tracker.py, post-integration-analyze.py, auto-learn-errors.py (Bash)
SubagentStart    → subagent-start.js (AGENTICA: 11 multi-agent patterns)
SubagentStop     → subagent-stop.js (agent completion + pattern coordination)
Stop             → stop-swarm-coordinator.js, pool-extractor.py, stop-memory-sync.py, memory-store-stop.py, continuous-learning-stop.py, session-end-cleanup-swarms.js
PreCompact       → pre-compact-handoff.py
```

### NEWLY WIRED (as of 2026-01-26 - MAJOR UPDATE):
```
session-briefing.py        → Architecture awareness + memory_router + unified_spine
deterministic_router.py    → orchestrator.fast_classify() as Stage 5
continuous-learning-stop   → emergent.run_emergent_cycle() + feedback_loop analytics
memory_router.py           → L1 Dragonfly + EMBEDDINGS semantic cache (sentence-transformers, cosine similarity)
unified_spine.py           → SessionStart trigger + MAPE controller bridge
strategy_evolution.py      → Auto-wired via unified_spine
outcome_tracker.py         → Auto-wired via unified_spine
feedback_loop.py           → Stop hook analytics
feedback_bridge.py         → MAPE controller in unified_spine
context_router.py          → NEW - HOT/WARM/COLD tiering (90%+ token savings)
auto-cache-pre.py          → Uses context_router for file access
orchestrator.py            → SWARMS multi-agent (run_swarm_workflow, should_use_swarm)
command_optimizer.py       → NEW - Auto-applies discovered workarounds
deferred_tasks.py          → NEW - Captures recommendations for later action
session-briefing.py        → NOW reads DIRECTIVES.md + surfaces deferred tasks
DIRECTIVES.md              → NEW - Standing user orders (read every session)
auto-learn-errors.py       → NEW - PostToolUse hook for Bash, auto-captures CLI errors
pre-create-check.py        → NEW - PreToolUse hook for Write, surfaces directives before creating files
efficiency_monitor.py      → NEW - Auto-tracks efficiency, alerts on decline (via PostToolUse + Stop hooks)
unified-post-tool-tracker  → NOW records to efficiency_monitor
continuous-learning-stop   → NOW runs efficiency analysis at session end
subagent-start.js          → SubagentStart: Agentica 11-pattern orchestration (swarm, jury, hierarchical, etc.)
subagent-stop.js           → SubagentStop: agent completion tracking + pattern-specific coordination
stop-swarm-coordinator.js  → Stop: blocks session end until all swarm agents complete
session-end-cleanup.js     → Stop: orphan agent cleanup for Agentica patterns
```

### STILL NEEDS WIRING:
```
metacognition.py           - Self-awareness (DEFER - nice to have)
coherence.py               - Goal alignment (DEFER - nice to have)
vector_store.py            - Embeddings (needs MARM first)
```

### NEWLY WIRED (2026-01-26 session):
```
daemon-autostart.py        → SessionStart: Auto-starts continuous_executor daemon
mcp_health.py warmup       → SessionStart: Pre-warm MCP servers (cold-start fix)
init_spine.py              → SessionStart: Initialize Atlas infrastructure
pre-command-optimize.py    → PreToolUse (Bash): Apply command_optimizer workarounds
efficiency_monitor.py      → NOW PERSISTS to efficiency_log + token tracking
token_monitor.py           → get_current_session_tokens() for efficiency integration
```

**DO NOT propose building systems that duplicate these. WIRE THEM IN instead.**

---

## Layer 1: Daemon Core (daemon/)

### ROUTING & ORCHESTRATION
| File | Status | Purpose | Wire Point |
|------|--------|---------|------------|
| `deterministic_router.py` | ACTIVE | Routes queries without LLM | UserPromptSubmit hook |
| `orchestrator.py` | **WIRED** | Central brain, fast_classify, strategy | **Via deterministic_router Stage 5** |
| `unified_spine.py` | UNUSED | Backbone connecting all systems | Needs daemon mode |
| `model_router.py` | USED | Routes to LocalAI/Codex/Claude | Via orchestrator |
| `local_autorouter.py` | USED | Rule-based routing | Via unified_spine |

### MEMORY & LEARNING
| File | Status | Purpose | Wire Point |
|------|--------|---------|------------|
| `memory_router.py` | **WIRED** | Unified interface to all memory | **Via SessionStart (session-briefing.py)** |
| `memory.py` | PARTIAL | SQLite persistence | Via memory_router |
| `emergent.py` | **WIRED** | Pattern detection, task gen, learning | **Via Stop hook (continuous-learning-stop.py)** |
| `vector_store.py` | UNUSED | Vector embeddings | Via memory_router |

### STRATEGY & EVOLUTION
| File | Status | Purpose | Wire Point |
|------|--------|---------|------------|
| `strategy_evolution.py` | UNUSED | Approach optimization | Via orchestrator |
| `strategy_ops.py` | UNUSED | Strategy operations | Via evolution |
| `outcome_tracker.py` | PARTIAL | Feedback loop | Via unified_spine |

### EXECUTION
| File | Status | Purpose | Wire Point |
|------|--------|---------|------------|
| `execution_spine.py` | PARTIAL | Retrieval + execution | Via unified_spine |
| `continuous_executor.py` | UNUSED | Long-running tasks | Needs daemon |
| `sequential_executor.py` | UNUSED | Step-by-step execution | Via continuous |
| `task_queue.py` | USED | Task management | Via unified_spine |
| `task_generator.py` | UNUSED | Generate tasks from patterns | Via emergent |

### SELF-IMPROVEMENT
| File | Status | Purpose | Wire Point |
|------|--------|---------|------------|
| `self_improvement.py` | PARTIAL | Pattern analysis | Manual CLI |
| `metacognition.py` | PARTIAL | Self-awareness | Manual CLI |
| `coherence.py` | PARTIAL | Goal alignment | Manual CLI |
| `decisions.py` | PARTIAL | Multi-criteria decisions | Manual CLI |

### INTEGRATION & EXTERNAL
| File | Status | Purpose |
|------|--------|---------|
| `dragonfly_mcp_server.py` | NEW | Redis cache MCP |
| `mcp_server.py` | ACTIVE | Core MCP |
| `n8n_notify.py` | ACTIVE | n8n integration |
| `telegram_notify.py` | ACTIVE | Telegram |
| `github_webhook.py` | ACTIVE | GitHub |
| `freqtrade_bridge.py` | UNUSED | Trading |

---

## Layer 2: MCP Servers (.mcp.json)

### ENABLED:
- `knowledge-graph` - Entity/relation memory (JSONL)
- `token-optimizer` - Token compression
- `tooluniverse` - 700+ scientific tools
- `sequential-thinking` - Chain-of-thought
- `memory` - MCP persistent memory
- `context7` - Live documentation
- `dragonfly-cache` - Redis cache (NEW)

### CONFIGURED BUT NOT ENABLED:
- `filesystem` - File operations
- `github` - GitHub API
- `n8n-workflow` - n8n execution

---

## Layer 3: Hooks (.claude/hooks/)

### SESSION LIFECYCLE:
- `session-briefing.py` - Minimal context on start
- `cleanup-mcp.py` - MCP cleanup
- `session-start-clean.py` - Clean start

### ROUTING:
- `deterministic_router.py` (in daemon/) - Main router
- `orchestrator-route.py` - Uses fast_classify (RARELY CALLED)
- `context-router.py` - Context routing

### MEMORY:
- `memory-recall-start.py` - Load memories
- `memory-store-stop.py` - Store on stop
- `stop-memory-sync.py` - Sync memories
- `auto-cache-pre.py` - Pre-cache
- `auto-cache-post.py` - Post-cache

### TRACKING:
- `unified-post-tool-tracker.py` - Track tool use
- `post-integration-analyze.py` - Analyze changes

### CONTINUITY:
- `pre-compact-handoff.py` - Save state before compact
- `continuous-learning-stop.py` - Extract learnings

---

## Layer 4: Agents (.claude/agents/) - 48 total

### CORE AGENTS:
- `kraken` - TDD implementation
- `architect` - Planning + API design
- `scout` - Codebase exploration
- `sleuth` - Bug investigation
- `arbiter` - Test validation
- `oracle` - External research
- `phoenix` - Refactoring
- `spark` - Quick tasks
- `scribe` - Documentation

### SPECIALIZED:
- `aegis` - Security
- `maestro` - Orchestration
- `profiler` - Performance
- `sentinel` - Monitoring
- `warden` - Access control
- `pathfinder` - Navigation

---

## Layer 5: Skills (.claude/skills/) - 116 total

### KEY SKILLS:
- `build` - Feature development
- `fix` - Bug fixing
- `create_handoff` - Save session state
- `continuity_ledger` - Track work
- `premortem` - Risk analysis
- `tldr-code` - Token-efficient analysis
- `confidence-check` - Pre-execution check

---

## Layer 6: Databases (daemon/*.db)

| Database | Purpose | Used By |
|----------|---------|---------|
| `strategies.db` | Strategy storage | strategy_evolution |
| `outcomes.db` | Outcome tracking | outcome_tracker |
| `memory.db` | Learnings/decisions | memory.py |
| `coherence.db` | Goal alignment | coherence.py |
| `decisions.db` | Decision records | decisions.py |
| `emergent.db` | Patterns/tasks | emergent.py |
| `metacognition.db` | Self-assessment | metacognition.py |
| `orchestrator.db` | Routing decisions | orchestrator.py |
| `tasks.db` | Task queue | task_queue.py |

---

## BEFORE PROPOSING ANY NEW SYSTEM:

1. **Check this file** - Does it already exist?
2. **Check if it's wired** - Is it ACTIVE or UNUSED?
3. **Wire existing code** - Don't duplicate, integrate
4. **Update this file** - Keep it current

---

## Integration Priorities

### COMPLETED (2026-01-26):
1. ✅ `deterministic_router.py` now imports and uses `orchestrator.fast_classify()`
2. ✅ `session-briefing.py` now injects mandatory ARCHITECTURE-LIVE.md awareness
3. ✅ `Stop` hook now triggers `emergent.run_emergent_cycle()`
4. ✅ `session-briefing.py` now calls `memory_router.search()` for context recall
5. ✅ `memory_router.py` now uses Dragonfly/Redis as L1 cache layer
6. ✅ `unified_spine.py` now runs on SessionStart (checks handoffs, processes tasks)
7. ✅ `strategy_evolution.py` auto-wired via unified_spine
8. ✅ `outcome_tracker.py` auto-wired via unified_spine
9. ✅ `feedback_loop.py` now triggers on Stop hook (analytics cycle)
10. ✅ `feedback_bridge.py` (MAPE controller) wired into unified_spine
11. ✅ `context_router.py` CREATED - HOT/WARM/COLD tiering (90% token savings!)
12. ✅ `auto-cache-pre.py` now uses context_router for tiered file access
13. ✅ `memory_router.py` now has TWO-STAGE semantic caching (0.5-0.85 thresholds)
14. ✅ `orchestrator.py` now has SWARMS multi-agent workflows (run_swarm_workflow, should_use_swarm)

### ROUTING PRIORITY (How decisions are made):
```
Layer 1: deterministic_router.py → Decides WHAT (agent/skill/tool)
         ↳ Uses pattern matching, slash commands, operator detection
         ↳ Falls back to orchestrator.fast_classify()

Layer 2: orchestrator.py → Provides intent classification + strategy selection
         ↳ Routes to localai/codex/claude based on complexity

Layer 3: context_router.py → Decides HOW MUCH of files to load
         ↳ HOT (>0.8): Full content
         ↳ WARM (0.25-0.8): Headers only (90% savings)
         ↳ COLD (<0.25): Reference only

Layer 4: memory_router.py → Unified memory with L1 Dragonfly cache
         ↳ Caches search results for 5 minutes
```

### IMMEDIATE (Next to wire):
1. Install MARM (`pip install marm-mcp-server`) as backend #3
2. Integrate Swarms patterns into orchestrator.py
3. Test full session lifecycle with all wiring

### NEXT (Operationalize):
1. Enable unified_spine daemon mode (background process)
2. Wire metacognition.py for self-awareness
3. Wire coherence.py for goal alignment

---

## File Locations Quick Reference

```
Claude n8n/
├── .claude/
│   ├── ARCHITECTURE-LIVE.md    ← YOU ARE HERE
│   ├── CLAUDE.md               ← Instructions (outdated)
│   ├── settings.local.json     ← Hooks config
│   ├── agents/                 ← 48 agents
│   ├── skills/                 ← 116 skills
│   ├── hooks/                  ← Lifecycle hooks
│   └── rules/                  ← Behavioral rules
├── daemon/
│   ├── deterministic_router.py ← ACTIVE router
│   ├── orchestrator.py         ← Central brain (wire this!)
│   ├── unified_spine.py        ← Backbone (unused!)
│   ├── memory_router.py        ← Memory interface (unused!)
│   ├── emergent.py             ← Learning (unused!)
│   └── [80+ more files]
├── .mcp.json                   ← MCP servers
└── thoughts/
    ├── handoffs/               ← Session state
    └── ledgers/                ← Continuity tracking
```

---

**LAST UPDATED:** 2026-01-26 (Session 5 - AGENTICA MULTI-AGENT WIRING)
**STATUS:** 24 SYSTEMS INTEGRATED. Added Agentica multi-agent pattern hooks (11 patterns), Windows daemon launcher.

**Recent Additions:**
- auto-learn-errors.py (PostToolUse for Bash - auto-captures CLI errors)
- pre-create-check.py (PreToolUse for Write - surfaces directives before creating files)
- memory_router embeddings (cosine similarity via sentence-transformers, fallback to Jaccard)
- efficiency_monitor.py (auto-tracks tool calls, detects thrashing, alerts on repeated errors)

**Key Capabilities:**
- Token Savings: Context Router achieves 90%+ on WARM files
- Semantic Cache: Two-stage matching (high/gray-zone/low)
- Multi-Agent: Swarms sequential/concurrent workflows
- Feedback Loop: MAPE controller + emergent learning

**Active Systems:** unified_spine, memory_router, context_router, orchestrator, emergent, feedback_loop, swarms
**Known Issues:** See .claude/KNOWN-ISSUES.md (MARM numpy conflict)
