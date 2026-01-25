# Critical Patterns

*Must-know patterns that apply across all work. Always check before implementing.*

---

## HIGH SEVERITY - Token Efficiency

### PATTERN-001: Grep Before Read
**Problem:** Reading full files wastes tokens on irrelevant content.
**Solution:** Use grep to find candidates, then read only matching files.
```bash
# Bad: Read everything
Read: daemon/*.py

# Good: Grep first, read matches
Grep: pattern="class.*Router" path=daemon/ output_mode=files_with_matches
Read: [only matching files]
```
**Impact:** 50-70% token reduction

### PATTERN-002: Use Smart Tools
**Problem:** Native Read/Grep/Glob return full content every time.
**Solution:** Use MCP token-optimizer variants.
```
mcp__token-optimizer__smart_read  # Cached, compressed
mcp__token-optimizer__smart_grep  # Indexed search
mcp__token-optimizer__smart_glob  # Cached patterns
```
**Impact:** 70-80% token reduction

### PATTERN-003: Delta Handoffs
**Problem:** Full handoffs repeat unchanged context.
**Solution:** Use delta_handoff.py for incremental state transfer.
```python
from daemon.delta_handoff import DeltaHandoff
handoff = DeltaHandoff()
delta = handoff.create_delta(previous_hash, current_state)
```
**Impact:** 50-70% handoff reduction

---

## HIGH SEVERITY - Reliability

### PATTERN-004: Check LocalAI Before Routing
**Problem:** LocalAI timeout causes cascade failures.
**Solution:** Health check before routing, with fallback.
```python
if not router.localai.available():
    # Skip LocalAI tier, go to Codex
    result = router.route(task, force_provider=Provider.CODEX)
```
**Impact:** Prevents 30+ second timeouts

### PATTERN-005: Database Connection Pooling
**Problem:** 19 SQLite files create connection overhead.
**Solution:** Use connection context managers, close promptly.
```python
# Bad
conn = sqlite3.connect(db)
# ... operations ...
# forgot to close

# Good
with sqlite3.connect(db) as conn:
    # ... operations ...
    # auto-closed
```
**Impact:** Prevents file lock issues

### PATTERN-006: Hook Error Isolation
**Problem:** One hook failure can break the entire chain.
**Solution:** Wrap each hook in try/catch, log but continue.
```python
try:
    result = hook.execute()
except Exception as e:
    log_error(e)
    return {"continue": True}  # Don't block
```
**Impact:** Prevents cascade failures

---

## MEDIUM SEVERITY - Code Quality

### PATTERN-007: Claim Verification
**Problem:** 80% false claim rate when grep results trusted without reading.
**Solution:** Always read the actual file before asserting existence.
```
# Bad: grep found "try.*catch" → "file has error handling"
# Good: Read file, verify actual try/catch block exists
```
**Impact:** Prevents false assertions

### PATTERN-008: Authority-Based Updates
**Problem:** Content duplicated across files becomes stale.
**Solution:** Single source of truth per content type (see QUICK.md).
```
# Bad: Update task.md AND EVOLUTION-PLAN.md with same info
# Good: task.md has tasks, EVOLUTION-PLAN.md has roadmap
```
**Impact:** Eliminates stale references

---

## LOW SEVERITY - Performance

### PATTERN-009: Parallel Agent Spawning
**Problem:** Sequential agent calls waste time.
**Solution:** Spawn independent agents in parallel.
```python
# Bad: Sequential
result1 = Task(agent1)
result2 = Task(agent2)

# Good: Parallel
results = Task([agent1, agent2])  # Single message, multiple agents
```
**Impact:** 2-5x faster for independent tasks

### PATTERN-010: L-RAG Gating
**Problem:** Retrieval overhead on simple queries.
**Solution:** Use LazyRAG to skip retrieval when context suffices.
```python
from daemon.lazy_rag import LazyRAG
rag = LazyRAG()
decision = rag.should_retrieve(query, existing_context)
if not decision.should_retrieve:
    # Skip vector search
```
**Impact:** 26% retrieval reduction
