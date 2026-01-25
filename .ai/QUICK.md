# Quick Reference

*Agent entry point and router to authoritative memory files*

---

## Authority Map

**Single source of truth for each content type. Content lives in ONE file only.**

| Content Type | Authoritative File | Source of Truth For |
|--------------|-------------------|---------------------|
| Agent entry point | `.ai/QUICK.md` | This router |
| Evolution plan | `EVOLUTION-PLAN.md` | Phase status, roadmap |
| Current tasks | `task.md` | Active objectives |
| System design | `.ai/ARCHITECTURE.json` | Topology, data flows |
| File locations | `.ai/FILES.json` | File index (globs) |
| Business rules | `specs/*.md` | Domain logic, schemas |
| Operations | `.ai/OPS.md` | Commands, runbooks |
| Decisions | `.ai/decisions/*.md` | ADR records |
| Solutions | `.ai/solutions/*.yaml` | Resolved patterns |
| Constraints | `.ai/CONSTRAINTS.md` | What we CAN'T do |
| Deprecations | `.ai/DEPRECATIONS.md` | Deprecated modules |
| Tech debt | `.ai/TECH_DEBT.md` | Deferred issues |
| Handoffs | `thoughts/handoffs/` | Session transfers |
| Learnings | `daemon/memory.py` | Persistent memory |

---

## Quick Start by Task Type

| Working On | Load First | Then |
|------------|------------|------|
| New feature | EVOLUTION-PLAN.md | task.md, handoffs/ |
| Bug fix | `.ai/solutions/` (grep) | `.ai/OPS.md` |
| Architecture | `.ai/ARCHITECTURE.json` | EVOLUTION-PLAN.md |
| Operations | `.ai/OPS.md` | docker-compose.yaml |
| Planning | task.md | EVOLUTION-PLAN.md |
| Debugging | `.ai/solutions/` | daemon/*.py |

---

## Critical Patterns (Always Check)

See `.ai/solutions/patterns/critical-patterns.md` for must-know patterns.

---

## Key Commands

```bash
# Memory recall
python daemon/memory.py search "<topic>"

# Self-improvement insights
python daemon/self_improvement.py improvements

# Routing stats
python daemon/model_router.py --stats

# Task queue
python daemon/runner.py status

# Google Drive sync
python daemon/gdrive/sync.py status
```

---

## Daemon Services

| Service | Port | Purpose |
|---------|------|---------|
| LocalAI | 8080 | Local LLM inference |
| Dragonfly | 6379 | Cache layer |
| API | 8765 | REST endpoints |
| MCP | stdio | Tool protocol |

---

## Token Efficiency

1. **Grep before Read** - Use `.ai/solutions/` YAML frontmatter
2. **L-RAG gating** - `daemon/lazy_rag.py` skips unnecessary retrieval
3. **Delta handoffs** - `daemon/delta_handoff.py` compresses state
4. **Smart tools** - `mcp__token-optimizer__smart_*` for 70-80% savings
5. **Model routing** - `daemon/model_router.py` routes cheap first
