# Hook Flow Map

**Created:** 2026-01-29 | **Purpose:** HookBus PHASE 0 Discovery

## Hook Entry Points (settings.local.json)

| Event | Count | Scripts |
|-------|-------|---------|
| SessionStart | 7 | cleanup-mcp, session-briefing, fewword-init, telegram-inbox, utf-session-prime, cd-auto-init, self_continue |
| UserPromptSubmit | 2 | deterministic_router, utf-query-injection |
| PreToolUse | 4 | auto-cache-pre (Read/Grep/Glob), Agentica redirects |
| PostToolUse | 4 | unified-post-tool-tracker, post-integration-analyze, task-sync-post, fewword-post-tool |
| Stop | 6 | pool-extractor, continuous-learning-stop, stop-memory-sync, memory-store-stop, pre-compact-handoff |
| PreCompact | 1 | pre-compact-handoff |
| SubagentStart/Stop | 2 | fewword-subagent |

## Critical Path Hooks (Block Tool Execution)

### PreToolUse: auto-cache-pre.py
- **Triggers:** Read, Grep, Glob
- **Side Effects:**
  - Reads context_router.db (file scores)
  - Reads Dragonfly cache (cache_client.py)
- **Output:** JSON with tier (HOT/WARM/COLD), cached content if hit
- **Failure Mode:** Pass-through (returns empty)

### PostToolUse: unified-post-tool-tracker.py
- **Triggers:** Read, Grep, Glob, Edit, Write
- **Side Effects:**
  - WRITE: tool_tracking.db → tool_uses table (INSERT per call)
  - WRITE: tool_tracking.db → cache_hits table (on cache hit)
- **Dedup Risk:** HIGH - every tool call = 1 INSERT

### PostToolUse: task-sync-post.py
- **Triggers:** TaskCreate
- **Side Effects:**
  - WRITE: daemon/task_injection.db → task_queue table
  - Calls auto_task_injection.queue_task()
- **Dedup Risk:** MEDIUM - if TaskCreate retried, duplicate task

## Background Hooks (Session End)

### Stop: continuous-learning-stop.py
- **Side Effects:**
  - CALL: daemon/emergent.py run_cycle()
  - CALL: daemon/feedback_loop.py run_full_cycle()
  - CALL: daemon/efficiency_monitor.py analyze()
  - WRITE: emergent.db → patterns, tasks tables
  - WRITE: strategies.db → fitness updates
  - WRITE: analytics.db → health snapshots
- **Dedup Risk:** LOW - runs once per session stop

### Stop: pool-extractor.py
- **Side Effects:**
  - WRITE: Extracts learnings from session
  - Stores to memory.db
- **Dedup Risk:** LOW - once per session

## Write Points (Duplication Candidates)

| Module | DB/File | Table | Frequency | Dedupe Key |
|--------|---------|-------|-----------|------------|
| unified-post-tool-tracker | tool_tracking.db | tool_uses | Every tool call | tool_name+timestamp |
| task-sync-post | task_injection.db | task_queue | Per TaskCreate | task_hash |
| continuous-learning-stop | emergent.db | patterns | Per session | pattern_hash |
| auto-cache-pre | context_router.db | file_scores | Per read | file_path |

## Data Flow Per Hook Event

```
PreToolUse (Read/Grep/Glob)
├── auto-cache-pre.py
│   ├── READ context_router.db (get_file_tier)
│   ├── READ Dragonfly cache
│   └── OUTPUT: {tier, content?, cached}

PostToolUse (Read/Grep/Glob/Edit/Write)
├── unified-post-tool-tracker.py
│   └── WRITE tool_tracking.db (tool_uses)
├── post-integration-analyze.py (only .claude/ writes)
│   └── CALL integration_analyzer.py
└── task-sync-post.py (only TaskCreate)
    └── WRITE task_injection.db

Stop
├── continuous-learning-stop.py
│   ├── CALL emergent.run_cycle()
│   ├── CALL feedback_loop.run_full_cycle()
│   └── CALL efficiency_monitor.analyze()
└── pool-extractor.py
    └── WRITE memory.db (learnings)
```

## Race Condition Points

1. **tool_tracking.db** - Multiple PostToolUse hooks could fire near-simultaneously
   - Mitigation: WAL mode + busy_timeout already in place

2. **task_injection.db** - TaskCreate + manual daemon task add
   - Mitigation: task_gate.py idempotency (PHASE 1 complete)

3. **Dragonfly cache** - Multiple PreToolUse reading same key
   - Mitigation: Redis is atomic

4. **emergent.db** - Stop hooks run concurrently
   - Mitigation: Currently sequential; needs mutex if parallel

## Correlation ID Derivation

Proposed formula for HookBus:
```python
correlation_id = sha256(f"{session_id}:{tool_name}:{tool_call_index}")[:16]
```

Components available in hook context:
- `session_id`: From Claude runtime (implicit)
- `tool_name`: From hook input JSON
- `tool_call_index`: Sequential counter (needs tracking)

## Payload Size Analysis

| Hook | Typical Payload | Max Observed |
|------|-----------------|--------------|
| PreToolUse | 2-10 KB | 50 KB (large file path) |
| PostToolUse | 5-50 KB | 500 KB (tool output) |
| Stop | 1-5 KB | 20 KB |

**Recommendation:** 200 KB cap with truncation, optional zlib compression.

## Critical vs Background Classification

**Critical Path (latency-sensitive):**
- auto-cache-pre.py - Directly affects tool response
- All PreToolUse hooks

**Background (can fail silently):**
- unified-post-tool-tracker.py - Analytics only
- task-sync-post.py - Async queue
- All Stop hooks
- All PostToolUse analytics

## HookBus Integration Points

```
┌─────────────────┐
│  Claude Runtime │
└────────┬────────┘
         │ hook_event
         ▼
┌─────────────────┐
│    HookBus      │ ← PHASE 1: daemon/hook_bus.py
│  - correlation  │
│  - guard()      │
│  - log_bounded()│
│  - dedupe()     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Existing Hook  │ ← Wrapped, not replaced
│    Scripts      │
└─────────────────┘
```

## Metrics to Track

- hook_duration_ms (P50, P95, P99)
- hook_failures (count by hook name)
- dedupe_hits (count by dedupe_key pattern)
- payload_bytes (histogram)
- compression_ratio (if enabled)

---

**Lines:** 168 | **Status:** PHASE 0 Complete
