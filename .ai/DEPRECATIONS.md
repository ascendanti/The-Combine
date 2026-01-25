# Deprecations

*Deprecated modules, APIs, and patterns*

---

## Deprecated Modules

### daemon/queue.py
**Deprecated:** 2026-01-23
**Replaced By:** daemon/task_queue.py
**Reason:** Renamed for clarity, added async support
**Remove After:** 2026-02-01
**Migration:** Update imports to `from daemon.task_queue import TaskQueue`

---

## Deprecated Patterns

### Native Read/Grep/Glob
**Deprecated:** 2026-01-25
**Replaced By:** MCP token-optimizer smart_* tools
**Reason:** 70-80% token savings with smart tools
**Enforcement:** smart-tool-redirect.py hook blocks native tools
**Migration:** Use mcp__token-optimizer__smart_read instead of Read

---

### Full Handoffs
**Deprecated:** 2026-01-20
**Replaced By:** Delta handoffs via delta_handoff.py
**Reason:** 50-70% handoff size reduction
**Migration:** Use `DeltaHandoff.create_delta()` instead of full state dumps

---

## Deprecated APIs

*None currently*

---

## Adding Deprecations

```markdown
### [Module/Pattern Name]
**Deprecated:** [Date]
**Replaced By:** [New approach]
**Reason:** [Why deprecated]
**Remove After:** [Target date]
**Migration:** [How to migrate]
```
