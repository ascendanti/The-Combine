# Codebase Index - Rapid Retrieval

## Quick Lookup by Function

### Core Processing
| Need | File | Key Functions |
|------|------|---------------|
| PDF extraction | `daemon/autonomous_ingest.py` | `process_document()`, `extract_text()` |
| UTF schema | `daemon/utf_extractor.py` | `extract_utf_schema()`, `localai_complete()` |
| Claim similarity | `daemon/claim_similarity.py` | `find_similar()`, `get_cross_paper_links()` |
| Book ingestion | `.claude/scripts/book-ingest.py` | `ingest_book()`, `chunk_text()` |

### Memory & Knowledge
| Need | File | Key Functions |
|------|------|---------------|
| Store memory | `daemon/memory.py` | `add()`, `search()`, `recall_similar_claims()` |
| Decisions | `daemon/decisions.py` | `evaluate()`, `record_outcome()` |
| Goal alignment | `daemon/coherence.py` | `check_action()`, `add_goal()` |
| Self-improvement | `daemon/self_improvement.py` | `analyze_first_principles()` |

### Infrastructure
| Need | File | Key Functions |
|------|------|---------------|
| Model routing | `daemon/model_router.py` | `route_to_model()`, `estimate_complexity()` |
| API server | `daemon/api.py` | Flask app, `/claims/*`, `/abstractions` |
| Task queue | `daemon/task_queue.py` | `add_task()`, `process_queue()` |
| Controller | `daemon/controller.py` | `mape_cycle()`, `analyze_gaps()` |

### Hooks by Trigger
| Trigger | File | Purpose |
|---------|------|---------|
| SessionStart | `hooks/memory-recall-start.py` | Load memories |
| Stop | `hooks/memory-store-stop.py` | Save learnings |
| PreToolUse:Read | `hooks/kg-context-gate.py` | Inject KG context |
| PostToolUse:Read | `hooks/kg-context-store.py` | Queue for summary |
| PreCompact | `hooks/pre-compact-handoff.py` | Save state |

---

## File Categories

### daemon/ (Core Workers) - 30+ modules
```
autonomous_ingest.py  - PDF/paper processing (1117 lines)
utf_extractor.py      - UTF schema extraction (850 lines)
memory.py             - Semantic memory (400 lines)
model_router.py       - LLM routing (300 lines)
api.py                - REST API + dashboard (500 lines)
bisimulation.py       - State abstraction (350 lines)
gcrl.py               - Goal-conditioned RL (400 lines)
claim_similarity.py   - Cross-paper matching (250 lines)
coherence.py          - Goal alignment (300 lines)
decisions.py          - Multi-criteria (350 lines)
controller.py         - MAPE loop (400 lines)
```

### .claude/hooks/ (Lifecycle Hooks)
```
Python hooks:   15 files
TypeScript:     20+ files in src/
Patterns:       12 files in src/patterns/
```

### .claude/scripts/ (Utilities)
```
book-ingest.py      - Manual ingestion
book-query.py       - Query books
telegram-inbox.py   - Check messages
token-tracker.py    - Usage analytics
kg-obsidian-sync.py - KG to Obsidian
```

### .claude/agents/ (32 Agents)
```
kraken   - TDD implementation
scout    - Codebase exploration
oracle   - External research
spark    - Quick fixes
architect - Planning
phoenix  - Refactoring
sleuth   - Bug investigation
```

---

## Database Schema Quick Reference

### utf_knowledge.db
```sql
sources(source_id, title, authors, year, domain, abstract, quality_status)
claims(claim_id, source_id, statement, claim_form, grounding, confidence)
excerpts(excerpt_id, source_id, text, location, content, page_num)
concepts(concept_id, source_id, name, definition_1liner, domain)
```

### memory.db
```sql
memories(id, content, context, tags, embedding, created_at)
```

### decisions.db
```sql
decisions(id, context, options, chosen, outcome, timestamp)
```

---

## Pattern Files (Multi-Agent Architectures)
```
hooks/src/patterns/
├── adversarial.ts      - Red team/blue team
├── blackboard.ts       - Shared workspace
├── chain-of-responsibility.ts
├── circuit-breaker.ts  - Fault tolerance
├── event-driven.ts     - Pub/sub
├── generator-critic.ts - Create/evaluate
├── hierarchical.ts     - Tree structure
├── jury.ts             - Voting/consensus
├── map-reduce.ts       - Parallel processing
├── pipeline.ts         - Sequential stages
└── swarm.ts            - Emergent behavior
```

---

## Config Files
```
.claude/settings.local.json  - Local settings, paths
.mcp.json                    - MCP server config
docker-compose.yaml          - Container orchestration
.env                         - API keys, webhooks
```

---

## Search Shortcuts

```bash
# Find function definition
grep -r "def function_name" daemon/

# Find class
grep -r "class ClassName" .

# Find imports of module
grep -r "from daemon.module import" .

# Find all uses of a function
grep -r "function_name(" daemon/ .claude/

# Find config references
grep -r "VARIABLE_NAME" .
```
