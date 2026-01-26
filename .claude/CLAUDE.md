# Project Instructions

## Session Start Protocol

**MANDATORY on every session start:**

1. **Read ARCHITECTURE-LIVE.md** - Your brain map. Shows what's ACTIVE vs UNUSED.
2. **Read latest handoff** in `thoughts/handoffs/` (most recent file)
3. **Read task.md** - Current objectives
4. **Continue from where left off** - Don't restart, iterate

```
Priority order:
ARCHITECTURE-LIVE.md → handoffs/ → task.md → KNOWN-ISSUES.md
```

**CRITICAL:** Before proposing ANY new system, check ARCHITECTURE-LIVE.md. Most features already exist - they just need WIRING, not building.

---

## Routing Priority (How Decisions Are Made)

The system uses a 4-layer routing architecture:

```
Layer 1: deterministic_router.py → Decides WHAT (agent/skill/tool)
         ↳ Pattern matching, slash commands, operator detection
         ↳ Falls back to orchestrator.fast_classify()

Layer 2: orchestrator.py → Intent classification + strategy selection
         ↳ Routes to localai/codex/claude based on complexity
         ↳ Triggers Swarms for complexity >= 7

Layer 3: context_router.py → Decides HOW MUCH of files to load
         ↳ HOT (>0.8): Full content
         ↳ WARM (0.25-0.8): Headers only (90% savings)
         ↳ COLD (<0.25): Reference only

Layer 4: memory_router.py → Unified memory with L1 Dragonfly cache
         ↳ Two-stage semantic matching (0.5-0.85 thresholds)
         ↳ Caches search results for 5 minutes
```

---

## Active Hook Lifecycle

These hooks run automatically:

| Event | Hooks | Purpose |
|-------|-------|---------|
| SessionStart | `cleanup-mcp.py`, `session-briefing.py`, `self_continue.py` | Initialize session, load architecture awareness, run unified_spine |
| UserPromptSubmit | `deterministic_router.py` | Route to agent/skill/tool via pattern + orchestrator |
| PreToolUse | `auto-cache-pre.py` | Check Dragonfly cache + context_router tiering |
| PostToolUse | `unified-post-tool-tracker.py`, `post-integration-analyze.py` | Track tool use, analyze changes |
| Stop | `pool-extractor.py`, `stop-memory-sync.py`, `memory-store-stop.py`, `continuous-learning-stop.py` | Extract learnings, run emergent cycle, feedback analytics |
| PreCompact | `pre-compact-handoff.py` | Save state before context compaction |

---

## Context Router (Token Savings)

The context router achieves **90%+ token savings** on frequently accessed files:

### Tiers

| Tier | Score | Content | Token Savings |
|------|-------|---------|---------------|
| HOT | >0.8 | Full file content | 0% |
| WARM | 0.25-0.8 | Headers/signatures only | 64-95% |
| COLD | <0.25 | Reference path only | 99% |

### Score Mechanics

- Each file access adds +0.3 to score
- Each turn applies 0.85 decay factor
- Frequent access keeps files HOT
- Unused files naturally decay to COLD

### Usage

The context router is automatically used by `auto-cache-pre.py` for Read operations.

---

## Semantic Cache (memory_router)

The memory router uses two-stage semantic matching:

| Similarity | Action |
|------------|--------|
| >0.85 (HIGH) | Return cached immediately (high confidence) |
| 0.5-0.85 (GRAY) | Accept cached match (good enough) |
| <0.5 (LOW) | Bypass cache (too different) |

This uses Jaccard similarity on normalized word sets - lightweight, no embeddings required.

---

## Swarms Multi-Agent Workflows

For complex tasks (complexity >= 7), the orchestrator can use Swarms:

```python
# Sequential - agents run in order, output feeds forward
orchestrator.run_swarm_workflow(tasks, workflow_type="sequential")

# Concurrent - agents run in parallel
orchestrator.run_swarm_workflow(tasks, workflow_type="concurrent")
```

**Triggers:**
- Complexity score >= 7
- Multi-step intents detected
- Explicit user request for multi-agent

---

## Daemon Modules (daemon/)

### Core Systems (WIRED)

| Module | Status | Purpose | Wire Point |
|--------|--------|---------|------------|
| `deterministic_router.py` | **ACTIVE** | Query routing without LLM | UserPromptSubmit hook |
| `orchestrator.py` | **WIRED** | Central brain, fast_classify, Swarms | Via deterministic_router |
| `memory_router.py` | **WIRED** | Unified memory + L1 cache | Via session-briefing.py |
| `unified_spine.py` | **WIRED** | Backbone coordinator | Via session-briefing.py |
| `context_router.py` | **WIRED** | HOT/WARM/COLD tiering | Via auto-cache-pre.py |
| `emergent.py` | **WIRED** | Pattern detection, learning | Via Stop hook |
| `feedback_loop.py` | **WIRED** | Analytics cycle | Via Stop hook |
| `feedback_bridge.py` | **WIRED** | MAPE controller | Via unified_spine |
| `strategy_evolution.py` | **WIRED** | Approach optimization | Via unified_spine |
| `outcome_tracker.py` | **WIRED** | Feedback tracking | Via unified_spine |

### Support Systems (USED)

| Module | Purpose |
|--------|---------|
| `memory.py` | SQLite persistence for learnings/decisions |
| `model_router.py` | Routes to LocalAI/Codex/Claude |
| `local_autorouter.py` | Rule-based routing |
| `task_queue.py` | Task management |
| `execution_spine.py` | Retrieval + execution |

### Deferred (UNUSED - needs daemon mode)

| Module | Purpose | Why Deferred |
|--------|---------|--------------|
| `metacognition.py` | Self-awareness | Nice to have |
| `coherence.py` | Goal alignment | Nice to have |
| `continuous_executor.py` | Long-running tasks | Needs daemon process |
| `vector_store.py` | Embeddings | Needs MARM first |

---

## MCP Servers (.mcp.json)

### Enabled

- `knowledge-graph` - Entity/relation memory (JSONL)
- `token-optimizer` - Token compression
- `tooluniverse` - 700+ scientific tools
- `sequential-thinking` - Chain-of-thought
- `memory` - MCP persistent memory
- `context7` - Live documentation
- `dragonfly-cache` - Redis L1 cache

### Configured but Disabled

- `filesystem` - File operations
- `github` - GitHub API
- `n8n-workflow` - n8n execution

---

## Agents & Skills

### Key Agents (.claude/agents/) - 48 total

| Agent | Purpose |
|-------|---------|
| `kraken` | TDD implementation with checkpoints |
| `architect` | Feature planning + API design |
| `scout` | Codebase exploration |
| `sleuth` | Bug investigation |
| `arbiter` | Test validation |
| `oracle` | External research |
| `phoenix` | Refactoring planning |
| `spark` | Quick tasks |
| `maestro` | Multi-agent orchestration |

### Key Skills (.claude/skills/) - 116 total

| Skill | Purpose |
|-------|---------|
| `build` | Feature development workflow |
| `fix` | Bug fixing workflow |
| `create_handoff` | Save session state |
| `continuity_ledger` | Track ongoing work |
| `premortem` | Risk analysis |
| `tldr-code` | Token-efficient analysis |
| `confidence-check` | Pre-execution check |

---

## Known Issues

**Always check `.claude/KNOWN-ISSUES.md` for:**

- MARM numpy/pandas binary incompatibility (use Jaccard instead of embeddings)
- FewWord sed errors (use `python -X utf8`)
- Import path issues (use `sys.path.insert`)
- API thinking block modification errors (start fresh session)

---

## Continuity System

### Handoffs (thoughts/handoffs/)

When ending a session:
1. Create handoff in `thoughts/handoffs/YYYY-MM-DD_topic.yaml`
2. Include: completed, in-progress, blocked, next steps

### Ledgers (thoughts/ledgers/)

Track state in `thoughts/ledgers/CONTINUITY_*.md`:
- Current goals
- Key decisions
- Session history

### Resume Protocol

At session start:
1. Read ARCHITECTURE-LIVE.md (brain map)
2. Check `thoughts/handoffs/` for latest handoff
3. Check `thoughts/ledgers/` for continuity state
4. Check `task.md` for current plan

---

## Databases (daemon/*.db)

| Database | Purpose | Used By |
|----------|---------|---------|
| `strategies.db` | Strategy storage | strategy_evolution |
| `outcomes.db` | Outcome tracking | outcome_tracker |
| `memory.db` | Learnings/decisions | memory.py |
| `coherence.db` | Goal alignment | coherence.py |
| `decisions.db` | Decision records | decisions.py |
| `emergent.db` | Patterns/tasks | emergent.py |
| `orchestrator.db` | Routing decisions | orchestrator.py |
| `tasks.db` | Task queue | task_queue.py |

---

## Project Structure

```
Claude n8n/
├── .claude/
│   ├── ARCHITECTURE-LIVE.md    ← BRAIN MAP (read every session)
│   ├── CLAUDE.md               ← This file
│   ├── KNOWN-ISSUES.md         ← Dependency conflicts & fixes
│   ├── settings.local.json     ← Hooks config
│   ├── agents/                 ← 48 agents
│   ├── skills/                 ← 116 skills
│   ├── hooks/                  ← Lifecycle hooks
│   └── rules/                  ← Behavioral rules
├── daemon/
│   ├── deterministic_router.py ← ACTIVE router
│   ├── orchestrator.py         ← Central brain (WIRED)
│   ├── unified_spine.py        ← Backbone (WIRED)
│   ├── memory_router.py        ← Memory interface (WIRED)
│   ├── context_router.py       ← HOT/WARM/COLD (WIRED)
│   ├── emergent.py             ← Learning (WIRED)
│   └── [70+ more files]
├── .mcp.json                   ← MCP servers
└── thoughts/
    ├── handoffs/               ← Session state
    └── ledgers/                ← Continuity tracking
```

---

## Core Rules

1. **Read ARCHITECTURE-LIVE.md first** - It's your brain map
2. **Wire existing code** - Don't duplicate, integrate
3. **Update docs after changes** - Keep architecture current
4. **Check KNOWN-ISSUES.md** - Before debugging dependency issues
5. **Use context router** - Let HOT/WARM/COLD save tokens
6. **Counter-propose** - Suggest better approaches when they exist
7. **Create handoffs** - Save state before context fills

---

## Counter-Propose Protocol

If the user requests something and a better approach exists, counter-propose:

- Don't execute requests blindly
- Evaluate if there's a superior alternative
- Present the enhanced option with reasoning
- Let user choose between original and enhanced

---

## Self-Improvement Loop

### Pattern Extraction (End of Session)

1. **Error Resolution** - What errors did I solve? How?
2. **User Corrections** - What did the user correct?
3. **Workarounds** - What quirks did I work around?
4. **Project-Specific** - What conventions are unique here?

### Storage

- **Memory DB:** `python daemon/memory.py add "<learning>"`
- **Emergent DB:** Via continuous-learning-stop.py hook (automatic)

### Retrieval

```bash
python daemon/memory_router.py search "<topic>"
```

---

**LAST UPDATED:** 2026-01-26
**STATUS:** 14 systems wired. Core architecture operational.
