# Reference Frameworks Taxonomy

Analysis of 36 folders in `Reverse Engineer/` for capability extraction.

## Tier 1: High-Value Integration Candidates

### sleepless-agent-main
**Capability:** 24/7 daemon that works while you sleep
- Slack integration for task submission
- Isolated workspaces for parallel execution
- SQLite-backed task queue
- Claude Code Python Agent SDK
- Auto-PR creation
- **Integration Method:** Root-level scripts + daemon service
- **Complexity:** Medium
- **Value:** Enables true autonomous async operation

### OpenMemory-main
**Capability:** Real long-term memory (not RAG)
- Self-hosted (SQLite/Postgres)
- Python + Node SDKs
- Explainable traces
- Integrations: LangChain, CrewAI, MCP, VS Code
- **Integration Method:** SDK import or MCP server
- **Complexity:** Medium
- **Value:** Persistent learning across sessions

### Continuous-Claude-v3-main
**Capability:** Session continuity and handoffs (ALREADY INTEGRATED)
- 30+ hooks for lifecycle events
- TLDR code analysis
- Memory awareness
- Pre-compact handoffs
- **Integration Method:** Hooks + settings.json
- **Complexity:** Low (already done)
- **Value:** ✅ Core continuity

### claude-code-auto-memory-main
**Capability:** Zero-token file tracking
- Auto CLAUDE.md sync
- Dirty file tracking
- Stop hook triggers
- **Integration Method:** Hooks + auto-memory directory
- **Complexity:** Low (partially done)
- **Value:** Tracks changes without context cost

---

## Tier 2: Useful Extensions

### SuperClaude_Framework-master
**Capability:** 30 commands, 16 agents, 7 modes, 8 MCP servers
- Structured development lifecycle
- Available on PyPI/npm
- **Integration Method:** Install via pip/npm
- **Complexity:** Low
- **Value:** More agents and commands (may overlap current)

### personal-os-main
**Capability:** Personal assistant OS
- Task management
- Knowledge base
- Integrations (Granola, etc.)
- **Integration Method:** Skills + workflows
- **Complexity:** Medium
- **Value:** Life management capabilities

### claude-flow-main
**Capability:** Workflow orchestration
- Task flow management
- **Status:** Needs further analysis
- **Value:** Potentially useful for multi-step automation

### mcp-desktop-agent-main
**Capability:** Desktop automation via MCP
- Screen control, file operations
- **Integration Method:** MCP server
- **Complexity:** Medium
- **Value:** GUI automation

---

## Tier 3: Specialty/Niche

| Framework | Focus | Use Case |
|-----------|-------|----------|
| claude-quant-main | Quantitative analysis | Finance |
| claude-equity-research-main | Equity research | Finance |
| claude-data-analysis-ultra-main | Data analysis | Analytics |
| deep-reading-analyst-skill-main | Document analysis | Research |
| marketingskills-main | Marketing automation | Marketing |
| ui-ux-pro-max-skill-main | UI/UX design | Design |
| obsidian-skills-main | Obsidian integration | PKM |
| vibe-kanban-main | Kanban boards | Project mgmt |

---

## Tier 4: Infrastructure/Reference

| Framework | Purpose |
|-----------|---------|
| n8n-mcp-main | n8n workflow MCP (lower priority per user) |
| LocalAI-master | Local LLM hosting |
| humanlayer-main | Human-in-the-loop |
| quanta-app-master | App framework |
| cherry-studio-main | Studio tooling |
| bytebot-main | Bot framework |

---

## ATLAS-CLAUDE (Your Creation)
**Status:** Failed attempt - learn from, don't replicate
- Windows service via nssm.exe
- AtlasHarmony.ps1 script
- Over-engineered daemon approach
- **Lesson:** Keep it simple, modular

---

## Recommended Integration Order

1. **sleepless-agent patterns** → Async daemon capability (highest value)
2. **OpenMemory SDK** → Persistent memory across sessions
3. **SuperClaude commands** → More agents (selective, non-overlapping)
4. **personal-os workflows** → Life management (optional)

## Integration Principle

**Iterative accretion:** Add one capability at a time, validate it works, then add next.
**No clashes:** Each addition must not break existing functionality.
**Selective:** Only integrate what makes the system more powerful.
