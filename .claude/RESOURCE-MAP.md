# Resource Map - When to Use What

## Quick Reference

| Need | Resource | Command/Usage |
|------|----------|---------------|
| **Search code** | Grep/Glob | `Grep pattern path` |
| **Understand structure** | tldr | `tldr structure .` |
| **Find callers** | tldr impact | `tldr impact func_name` |
| **External research** | oracle agent | `Task subagent_type=oracle` |
| **Explore codebase** | scout agent | `Task subagent_type=scout` |
| **Quick fix** | spark agent | `Task subagent_type=spark` |
| **Implementation** | kraken agent | `Task subagent_type=kraken` |
| **Memory recall** | memory.py | `python daemon/memory.py search "topic"` |
| **Check telegram** | telegram-inbox.py | `python .claude/scripts/telegram-inbox.py` |

---

## Daemon Modules (daemon/)

### Core Workers (Run 24/7 in Docker)

| Module | Purpose | When to Use |
|--------|---------|-------------|
| `autonomous_ingest.py` | PDF/paper processing | Drop files in GateofTruth folder |
| `kg_summary_worker.py` | Code file summaries | Auto-triggered by file reads |
| `synthesis_worker.py` | Pattern synthesis | Runs daily, cross-references KG |
| `utf_extractor.py` | UTF schema extraction | Called by autonomous_ingest |

### Cognitive Architecture

| Module | Purpose | When to Use |
|--------|---------|-------------|
| `memory.py` | Semantic memory | Store/recall learnings |
| `decisions.py` | Multi-criteria decisions | Complex choices |
| `coherence.py` | Goal alignment | Check if action fits goals |
| `metacognition.py` | Self-assessment | Capability gaps |
| `self_improvement.py` | Pattern analysis | Generate improvements |
| `bisimulation.py` | State abstraction | Policy transfer |
| `gcrl.py` | Goal-conditioned RL | Learn from trajectories |

### Strategy & Evolution (NEW - 2026-01-24)

| Module | Purpose | When to Use |
|--------|---------|-------------|
| `outcome_tracker.py` | Record action outcomes | After any task completes |
| `strategy_evolution.py` | Evolve strategies | Improve approaches over time |
| `strategy_ops.py` | Operationalize strategies | Deploy, measure, detect drift |
| `local_autorouter.py` | Token-minimizing routing | Route to cheapest capable model |
| `self_continue.py` | Auto-resume after compaction | Session continuation |
| `task_generator.py` | Proactive task generation | Identify opportunities |
| `evolution_tracker.py` | Link strategy→plan→scifi | Sync progress documents |
| `seed_strategies.py` | Seed initial strategies | One-time setup |

### Core Infrastructure (NEW - 2026-01-24)

| Module | Purpose | When to Use |
|--------|---------|-------------|
| `core/base.py` | Signal/Action/Outcome types | Build coherent modules |
| `core/bus.py` | Message bus (pub/sub) | Inter-module communication |

### Infrastructure

| Module | Purpose | When to Use |
|--------|---------|-------------|
| `api.py` | REST API + dashboard | `http://localhost:8787` |
| `model_router.py` | Route to LocalAI/Claude | Auto-selects model by task |
| `controller.py` | MAPE control loop | Adaptive optimization |
| `claim_similarity.py` | Cross-paper matching | Find related claims |
| `task_queue.py` | Background task queue | Async processing |

### Bridges/Integrations

| Module | Purpose | When to Use |
|--------|---------|-------------|
| `telegram_notify.py` | Send telegram messages | Status updates |
| `email_trigger.py` | Email monitoring | External triggers |
| `github_webhook.py` | GitHub events | PR/issue automation |
| `freqtrade_bridge.py` | Trading integration | Freqtrade signals |
| `mcp_server.py` | MCP tool server | Custom MCP tools |

---

## Hooks (.claude/hooks/)

### Session Lifecycle

| Hook | Trigger | Purpose |
|------|---------|---------|
| `memory-recall-start.py` | SessionStart | Load relevant memories |
| `memory-store-stop.py` | Stop | Save session learnings |
| `auto-handoff-stop.py` | Stop | Create handoff if needed |
| `pre-compact-handoff.py` | PreCompact | Save state before compact |

### Tool Augmentation

| Hook | Trigger | Purpose |
|------|---------|---------|
| `kg-context-gate.py` | PreToolUse:Read | Inject cached KG context |
| `kg-context-store.py` | PostToolUse:Read | Queue files for summarization |
| `smart-tool-redirect.py` | PreToolUse | Route to MCP smart tools |

### Notifications

| Hook | Trigger | Purpose |
|------|---------|---------|
| `n8n-notify.py` | Stop | Send n8n webhook |
| `git-post-commit.py` | Git commit | Historian checkpoint |

---

## Scripts (.claude/scripts/)

### Knowledge Management

| Script | Purpose | Usage |
|--------|---------|-------|
| `book-ingest.py` | Manual book ingestion | `python .claude/scripts/book-ingest.py "path.pdf"` |
| `book-query.py` | Query ingested books | `python .claude/scripts/book-query.py "query"` |
| `kg-obsidian-sync.py` | Sync KG to Obsidian | `python .claude/scripts/kg-obsidian-sync.py` |
| `utf-ingest.py` | UTF iterative ingest | `python .claude/scripts/utf-ingest.py` |

### Analytics

| Script | Purpose | Usage |
|--------|---------|-------|
| `token-tracker.py` | Token usage tracking | `python .claude/scripts/token-tracker.py --today` |
| `history.py` | Session history | `python .claude/scripts/history.py` |

### Communication

| Script | Purpose | Usage |
|--------|---------|-------|
| `telegram-inbox.py` | Check telegram | `python .claude/scripts/telegram-inbox.py` |
| `notify-telegram.py` | Send telegram | `python .claude/scripts/notify-telegram.py "msg"` |

---

## Containers (Docker)

| Container | Service | Health Check |
|-----------|---------|--------------|
| `autonomous-ingest` | Paper processing | Watches /watch folder |
| `localai` | Free LLM (Mistral 7B) | `http://localai:8080/v1` |
| `kg-summary-worker` | Code summarization | Processes task_queue |
| `synthesis-worker` | Daily synthesis | 24h cycle |
| `dragonfly-cache` | Redis-compatible cache | 41+ LLM response keys |

---

## Databases

| Database | Location | Purpose |
|----------|----------|---------|
| `utf_knowledge.db` | daemon/ | Claims, excerpts, concepts |
| `ingest.db` | daemon/ | Processed files tracking |
| `memory.db` | daemon/ | Semantic memory |
| `decisions.db` | daemon/ | Decision history |
| `coherence.db` | daemon/ | Goals and alignment |
| `synthesis.db` | daemon/ | Patterns and meta-learnings |
| `tasks.db` | daemon/ | Background task queue |

---

## Key Paths

| Path | Purpose |
|------|---------|
| `thoughts/handoffs/` | Session state transfers |
| `thoughts/ledgers/` | Continuity tracking |
| `.claude/cache/agents/oracle/` | Research agent outputs |
| `GateofTruth/` | PDF drop folder for ingestion |
| `~/.claude/memory/knowledge-graph.jsonl` | Main knowledge graph |

---

## Decision Tree: What to Use When

```
Need to find code?
├─ Know exact pattern → Grep
├─ Know file pattern → Glob
├─ Need to understand structure → tldr structure
└─ Complex exploration → scout agent

Need external info?
├─ Web search → oracle agent
├─ Past learnings → memory.py search
└─ Check telegram → telegram-inbox.py

Need to implement?
├─ Quick fix → spark agent
├─ Complex feature → kraken agent
└─ Need planning first → architect agent

Need to communicate?
├─ Telegram update → telegram_notify.py
├─ Session handoff → create_handoff skill
└─ Store learning → memory.py add

Running containers?
├─ Check status → docker ps
├─ View logs → docker logs <name>
├─ Restart → docker compose restart <name>
```

---

## Model Routing (Automatic)

| Task Type | Model | Cost |
|-----------|-------|------|
| Summarization | LocalAI (Mistral 7B) | $0 |
| Embedding | LocalAI | $0 |
| Simple Q&A | LocalAI | $0 |
| Code generation | Codex (gpt-4o-mini) | $0.01 |
| Complex reasoning | Claude | $$$ |
| Architecture | Claude | $$$ |

The `model_router.py` automatically selects based on task complexity.

---

## Business Specs (specs/)

### Company Visions

| Document | Company | Revenue Target |
|----------|---------|----------------|
| `ATLAS-ANALYTICS-VISION.md` | Intelligence firm | $2M Y5 |
| `ATLAS-INSTRUMENTS-VISION.md` | Verification tools | $1M Y5 |
| `ATLAS-PUBLISHING-VISION.md` | Book publishing | $200K Y5 |
| `ATLAS-CONTENT-COMPANY-VISION.md` | Media properties | $1M Y5 |
| `ATLAS-MEDIA-PRODUCTION-VISION.md` | Documentary | $1M Y5 |
| `ALGIERS-BAY-COMPANY-VISION.md` | Import/export | $2M Y5 |

### Strategy & Operations

| Document | Purpose | Usage |
|----------|---------|-------|
| `ADAM-BENSAID-PROFILE.md` | Principal profile | Career analysis, leverage points |
| `REVENUE-STRATEGIES.md` | 10 quick + 10 long-term | Revenue roadmap |
| `CRM-ANALYSIS-DECISION.md` | CRM comparison | Twenty CRM selected |
| `ATLAS-CRM-SPEC.md` | CRM integration spec | Lead gen, proposals, deals |
| `INBOX-ZERO-INTEGRATION.md` | Email automation | AI email management |
| `CAREER-MANAGER-SPEC.md` | Career orchestration | Future implementation |
| `LOCAL-DEPLOYMENT-GUIDE.md` | Self-hosted setup | $2K PC + voice/hologram |

---

## Planning Documents (.claude/)

| Document | Purpose |
|----------|---------|
| `PRIME-DIRECTIVE.md` | 9-domain mastery architecture |
| `ASCENSION-MANIFESTO.md` | Sci-fi capability vision |
| `SCI-FI-TECHNICAL-ROADMAP.md` | Hierarchical capability matrix |
| `RUMSFELD-MATRIX.md` | Known/unknown analysis |
| `UNIFIED-ARCHITECTURE.md` | Coherent subsystem design |
| `NEXT-HORIZONS.md` | Unexplored development paths |
| `TECH-TREE.md` | Development pathways |

---

## Tracking Systems

| System | Database | Purpose |
|--------|----------|---------|
| Strategy Evolution | `strategies.db` | Track strategy fitness |
| Outcome Tracker | `outcomes.db` | Record action results |
| Evolution Tracker | `evolution_tracker.py` | Link strategy→plan→sci-fi |
| Self-Continue | `self_continue.py` | Resume after compaction |

### Commands

```bash
# Strategy tracking
python daemon/strategy_evolution.py list
python daemon/evolution_tracker.py status
python daemon/evolution_tracker.py progress

# Outcome tracking
python daemon/outcome_tracker.py stats
python daemon/outcome_tracker.py patterns

# Self-continue
python daemon/self_continue.py resume
python daemon/self_continue.py checkpoint --phase "X" --task "Y"
```

---

## Git Repos (Telegram Inbox History)

| Repo | Purpose | Status |
|------|---------|--------|
| `twentyhq/twenty` | CRM (39K stars) | Selected for deployment |
| `elie222/inbox-zero` | Email AI (9.9K stars) | Spec created |

---

## Quick Commands (Business)

```bash
# Check revenue strategies
cat specs/REVENUE-STRATEGIES.md

# View company visions
ls specs/ATLAS-*.md

# Check CRM spec
cat specs/ATLAS-CRM-SPEC.md

# Evolution progress
python daemon/evolution_tracker.py progress
```
