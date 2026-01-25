# Quick Reference

*Agent entry point and router to authoritative memory files*

**Sources:** fat-controller, compound-engineering, 12-factor-agents, hooks-mastery

---

## Authority Map

**Single source of truth for each content type. Content lives in ONE file only.**

| Content Type | Authoritative File | Source of Truth For |
|--------------|-------------------|---------------------|
| Agent entry point | `.ai/QUICK.md` | This router |
| Execution state | `.ai/STATE.md` | Current task, agent states, errors (Factor 5) |
| Evolution plan | `EVOLUTION-PLAN.md` | Phase status, roadmap |
| Current tasks | `task.md` | Active objectives |
| System design | `.ai/ARCHITECTURE.json` | Topology, data flows |
| Operations | `.ai/OPS.md` | Commands, runbooks, debugging |
| Decisions | `.ai/decisions/*.md` | ADR records |
| Solutions | `.ai/solutions/*.yaml` | Resolved patterns |
| Critical patterns | `.ai/solutions/patterns/critical-patterns.md` | Must-know patterns (always read) |
| Constraints | `.ai/CONSTRAINTS.md` | What we CAN'T do |
| Deprecations | `.ai/DEPRECATIONS.md` | Deprecated modules |
| Tech debt | `.ai/TECH_DEBT.md` | Deferred issues |
| Handoffs | `thoughts/handoffs/` | Session transfers |
| Learnings | `daemon/memory.py` | Persistent memory |
| Integration analysis | `MULTI-REPO-INTEGRATION-ANALYSIS.md` | Pattern adoption from 12+ repos |

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

---

## Integration Wiring

**How patterns from different repos connect:**

```
Session Start
    │
    ├─→ Read .ai/QUICK.md (this file)
    │       └─→ Routes to authoritative files
    │
    ├─→ Read .ai/STATE.md (Factor 5)
    │       └─→ Resume from execution state
    │
    ├─→ Read .ai/solutions/patterns/critical-patterns.md
    │       └─→ Must-know patterns (compound-eng)
    │
    └─→ Check thoughts/handoffs/ for latest
            └─→ Delta format (12-factor Factor 6)

Before Implementation
    │
    ├─→ Use learnings-researcher agent
    │       └─→ Grep-first solution lookup (compound-eng)
    │
    ├─→ Check .ai/TECH_DEBT.md
    │       └─→ Known issues to avoid
    │
    └─→ Check .ai/DEPRECATIONS.md
            └─→ Patterns to NOT use

During Implementation
    │
    ├─→ Smart tools enforced by hook
    │       └─→ smart-tool-redirect.py blocks native Read/Grep/Glob
    │
    ├─→ Model routing via daemon/model_router.py
    │       └─→ LocalAI → Codex → Claude (cost-optimized)
    │
    └─→ Errors compacted into STATE.md (Factor 9)

After Implementation
    │
    ├─→ Update .ai/STATE.md with completion
    │
    ├─→ Add solution to .ai/solutions/ if reusable
    │       └─→ YAML frontmatter for grep-first lookup
    │
    └─→ Create handoff if session ending
            └─→ Delta format via delta_handoff.py
```

---

## Agent Integration

| Agent | Source | Purpose | Wires To |
|-------|--------|---------|----------|
| learnings-researcher | compound-eng | Solution lookup | .ai/solutions/ |
| scout | SuperClaude | Codebase exploration | ARCHITECTURE.json |
| kraken | SuperClaude | TDD implementation | STATE.md |
| oracle | SuperClaude | External research | OPS.md |

---

## Hook Integration

| Hook | Source | Purpose | Wires To |
|------|--------|---------|----------|
| smart-tool-redirect.py | hooks-mastery | Block native tools | MCP token-optimizer |
| tldr-context-inject.ts | local | Code analysis injection | tldr CLI |
| kg-context-gate.py | local | Retrieval gating | lazy_rag.py |

---

## 12-Factor Compliance

| Factor | Status | Implementation |
|--------|--------|----------------|
| 1. NL → Tool Calls | ✅ | Claude Code native |
| 2. Own prompts | ✅ | .claude/agents/, skills/ |
| 3. Own context | ✅ | smart tools, L-RAG |
| 4. Tools = outputs | ✅ | MCP tools |
| 5. Unify state | ✅ | STATE.md |
| 6. Pause/Resume | ✅ | delta_handoff.py |
| 7. Human contact | ✅ | Telegram, Slack |
| 8. Own control flow | ✅ | model_router.py |
| 9. Compact errors | ✅ | STATE.md error log |
| 10. Small agents | ✅ | 48 focused agents |
| 11. Trigger anywhere | ✅ | CLI/Telegram/Email/GitHub |
| 12. Stateless reducer | ✅ | Handoff pattern |
