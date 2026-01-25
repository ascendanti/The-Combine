# Integration Architecture

*How the repo's files, processes, and folders work together*

---

## Folder Hierarchy

```
Claude n8n/
├── daemon/              # BACKEND - Python services & cognitive modules
├── modules/             # INPUT - Sources for ingestion (git repos, references)
├── thoughts/            # STATE - Session continuity (handoffs, ledgers)
├── specs/               # PLANNING - Business specs, visions, strategies
├── .claude/             # AI TOOLING - Agents, skills, hooks, rules
├── .fewword/            # CONTEXT - Memory management, scratch
└── .local_agents/       # LOCAL AI - Agent configurations
```

---

## Data Flow Architecture

```
                    ┌──────────────────────────────────────────┐
                    │              INPUT LAYER                  │
                    │  Telegram │ Email │ Folder │ Git Repos   │
                    └─────────────────┬────────────────────────┘
                                      │
                    ┌─────────────────▼────────────────────────┐
                    │           INGESTION LAYER                 │
                    │  modules/git ingest → daemon/ingest.py   │
                    │  GateofTruth/ → daemon/autonomous_ingest │
                    └─────────────────┬────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌───────────────┐         ┌───────────────────┐         ┌───────────────┐
│  KNOWLEDGE    │         │    PROCESSING     │         │    CONTEXT    │
│  daemon/      │         │    daemon/        │         │    .claude/   │
│  - memory.py  │◄───────►│  - synthesis      │◄───────►│  - skills/    │
│  - kg_summary │         │  - coherence      │         │  - agents/    │
│  - utf_*      │         │  - metacognition  │         │  - hooks/     │
└───────┬───────┘         └─────────┬─────────┘         └───────┬───────┘
        │                           │                           │
        └───────────────────────────┼───────────────────────────┘
                                    │
                    ┌───────────────▼───────────────────────────┐
                    │            OUTPUT LAYER                    │
                    │  specs/ (plans) │ thoughts/ (state)       │
                    │  Telegram (alerts) │ Obsidian (notes)     │
                    └───────────────────────────────────────────┘
```

---

## Component Responsibilities

### 1. daemon/ (Backend Services)

| File | Purpose | Connects To |
|------|---------|-------------|
| `autonomous_ingest.py` | Document processing | modules/, Obsidian |
| `synthesis_worker.py` | Cross-doc synthesis | UTF DB, KG |
| `kg_summary_worker.py` | Knowledge graph updates | OpenMemory |
| `memory.py` | Persistent memory | PostgreSQL |
| `coherence.py` | Goal alignment | decisions.py |
| `metacognition.py` | Self-awareness | self_improvement.py |
| `decisions.py` | Multi-criteria decisions | outcomes.db |
| `model_router.py` | Route to LocalAI/Claude | All modules |
| `telegram_notify.py` | Send notifications | Telegram API |

### 2. modules/ (Input Sources)

| File | Purpose |
|------|---------|
| `git ingest` | List of GitHub repos to analyze |

### 3. thoughts/ (Session State)

| Folder | Purpose |
|--------|---------|
| `handoffs/` | Session state transfers (YAML) |
| `ledgers/` | Ongoing continuity tracking (MD) |

### 4. specs/ (Planning)

| File | Purpose |
|------|---------|
| `ADAM-BENSAID-PROFILE.md` | Principal profile |
| `ATLAS-*-VISION.md` | Company vision docs |
| `ATLAS-CRM-SPEC.md` | CRM integration spec |
| `EFFICIENCY-STACK.md` | Token/memory optimization plan |
| `REVENUE-STRATEGIES.md` | Business strategies |

### 5. .claude/ (AI Tooling)

| Folder | Purpose |
|--------|---------|
| `agents/` | 48 specialized agents |
| `skills/` | 116 skills |
| `rules/` | Behavioral guidelines |
| `hooks/` | Lifecycle hooks |
| `scripts/` | Utility scripts |

---

## Integration Points

### A. Input → Processing

```
1. User sends repo via Telegram
   → modules/git ingest (manual add)
   → daemon reads file
   → WebFetch analyzes repo
   → specs/TELEGRAM-REPOS-TRACKER.md updated

2. PDF dropped in GateofTruth/
   → daemon/autonomous_ingest.py detects
   → MinerU/MarkItDown extracts
   → UTF schema extraction
   → Obsidian export
   → KG update
```

### B. Processing → State

```
1. Session work completes
   → thoughts/handoffs/YYYY-MM-DD_topic.yaml created
   → Next session reads handoff, continues

2. Long-running goal
   → thoughts/ledgers/CONTINUITY_main.md updated
   → Progress tracked across sessions
```

### C. Processing → Output

```
1. Analysis complete
   → specs/*.md created
   → task.md updated
   → Telegram notification sent

2. Knowledge synthesized
   → daemon/utf_knowledge.db updated
   → Obsidian notes exported
   → OpenMemory entities stored
```

---

## Workflow Patterns

### Pattern 1: Document Ingestion
```
GateofTruth/ → autonomous_ingest.py → utf_extractor.py
    → UTF DB (claims, concepts)
    → Obsidian (markdown notes)
    → KG JSONL (entities)
```

### Pattern 2: Session Continuity
```
Session start → Read thoughts/handoffs/latest
    → Continue from where left off
    → Update task.md
Session end → Create handoff → Update ledger
```

### Pattern 3: Planning Workflow
```
User request → specs/NEW-SPEC.md created
    → .claude/agents/* assist
    → task.md tracks progress
    → thoughts/handoffs/ preserves state
```

### Pattern 4: Memory Retrieval
```
Query → daemon/memory.py search()
    → OpenMemory (entities)
    → UTF DB (claims)
    → Dragonfly cache (fast)
```

---

## Integration Gaps (To Fix)

| Gap | Current | Target |
|-----|---------|--------|
| Unified search | Multiple DBs | Single search() API |
| Spec linking | Manual refs | Auto-link specs ↔ tasks |
| Module → Daemon | Manual trigger | Watch mode auto-detect |
| Thoughts → Specs | Separate | Bi-directional linking |
| Agent memory | Per-session | Persistent across sessions |

---

## Quick Commands

### Check System Health
```bash
# Daemon services
docker ps --format "table {{.Names}}\t{{.Status}}"

# Ingestion status
python daemon/autonomous_ingest.py --status

# Memory stats
python daemon/memory.py stats
```

### Session Workflow
```bash
# Start: Read latest state
cat thoughts/handoffs/$(ls -t thoughts/handoffs/ | head -1)

# Work: Track progress
cat task.md

# End: Create handoff
# (Use create_handoff skill)
```

---

## Architecture Principles

1. **Input → Processing → State → Output** - Clear data flow
2. **Stateless processing** - Session state in thoughts/, not in daemon/
3. **Single source of truth** - Each type of data has one home
4. **Observable** - All significant actions logged/notified
5. **Resumable** - Any session can continue from handoff

---

*Updated: 2026-01-25*
