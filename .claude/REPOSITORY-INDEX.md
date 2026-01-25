# Repository Index

**Auto-updated by Stop hook**

## Core Files
| File | Purpose |
|------|---------|
| .mcp.json | MCP server config |
| .claude/settings.local.json | Hooks & permissions |
| .claude/CLAUDE.md | Project instructions |
| task.md | Current objectives |
| EVOLUTION-PLAN.md | Phase roadmap |

## Daemon Workers
| Module | Purpose | Trigger |
|--------|---------|---------|
| autonomous_ingest.py | PDF/book deep extraction (HiRAG+LeanRAG) | Watches GateofTruth |
| kg_summary_worker.py | Code file summaries | Claude file reads |
| synthesis_worker.py | KG consolidation + patterns | Periodic (24h) |
| token_monitor.py | Spike detection + optimization logging | Manual/watch |
| book_watcher.py | File watcher for GateofTruth | Daemon |
| controller.py | MAPE adaptive control | Manual/periodic |
| feedback_bridge.py | Decision-informed control | With controller |
| model_router.py | LocalAI/Codex/Claude tiering | All workers |

## Daemon Core
| Module | Purpose |
|--------|---------|
| memory.py | Persistent memory |
| self_improvement.py | Pattern analysis |
| decisions.py | Multi-criteria eval |
| metacognition.py | Self-awareness |
| coherence.py | Goal alignment |
| task_queue.py | Async task queue |
| api.py | FastAPI endpoints |
| runner.py | Workflow execution |
| scheduler.py | Cron scheduling |

## Scripts (.claude/scripts/)
| Script | Purpose | Command |
|--------|---------|---------|
| token-tracker.py | Token usage reports | `python .claude/scripts/token-tracker.py --today` |
| kg-obsidian-sync.py | KG to Obsidian vault | `python .claude/scripts/kg-obsidian-sync.py --watch` |
| book-ingest.py | Manual book ingestion | `python .claude/scripts/book-ingest.py <file>` |
| book-query.py | Query ingested books | `python .claude/scripts/book-query.py "query"` |
| pool-query.py | Session state query | `python .claude/scripts/pool-query.py` |
| pool-loader.py | Load session context | Hook: SessionStart |
| pool-extractor.py | Save session context | Hook: Stop |
| context-router-v2.py | HOT/WARM/COLD routing | Hook: UserPromptSubmit |
| history.py | Attention tracking | Manual |

## Hooks (.claude/hooks/)
| Hook | Trigger | Purpose |
|------|---------|---------|
| context-router-v2.py | UserPromptSubmit | Skill/agent routing |
| pool-loader.py | SessionStart | Load session state |
| pool-extractor.py | Stop | Save state + update index |
| cleanup-mcp.py | SessionStart | Kill orphan nodes |
| auto-cache-pre.py | PreToolUse | Cache check |
| auto-cache-post.py | PostToolUse | Cache store |
| kg-context-gate.py | PreToolUse:Read | Inject KG context |
| kg-context-store.py | PostToolUse:Read | Queue for summary |

## Storage
| File/DB | Contents |
|---------|----------|
| ~/.claude/memory/knowledge-graph.jsonl | All KG entities |
| daemon/ingest.db | Processed files tracking |
| daemon/synthesis.db | Patterns + meta-learnings |
| daemon/token_monitor.db | Spike logs |
| daemon/router.db | Model routing stats |

## Watch Folders
| Path | Purpose |
|------|---------|
| ~/Documents/GateofTruth/ | Drop PDFs for auto-ingestion |
| ~/Documents/Obsidian/ClaudeKnowledge/ | KG as Obsidian vault |

## Quick Commands
```bash
# Token tracking
python .claude/scripts/token-tracker.py --today
python daemon/token_monitor.py --analyze

# Book ingestion
python daemon/autonomous_ingest.py --watch
python .claude/scripts/book-query.py "concept"

# KG management
python .claude/scripts/kg-obsidian-sync.py --watch
python daemon/synthesis_worker.py --cycle

# Control systems
python daemon/controller.py --status
python daemon/feedback_bridge.py --cycle
```

## MCP Servers
| Server | Status |
|--------|--------|
| knowledge-graph | Active |

## Reference Frameworks
| Repo | Purpose |
|------|---------|
| claudelytics | Token analytics (Rust) |
| claude-context-extender | RAG patterns |
| claude-modular | Token optimization |

---
Updated: 2026-01-23 17:30
