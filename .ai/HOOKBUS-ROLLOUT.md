# HookBus Rollout Plan

**Created:** 2026-01-29 | **Status:** Ready for Gradual Rollout

## Summary

HookBus provides standardized infrastructure for hook execution:
- Correlation IDs for distributed tracing
- Guard wrappers for exception-safe execution
- Bounded logging with 200KB payload cap
- Idempotency via SQLite-backed dedupe
- Metrics collection (P50/P95/P99 latency)

## Files Created

| File | Purpose |
|------|---------|
| `daemon/hook_bus.py` | Core library (540 lines) |
| `daemon/hook_bus.db` | SQLite storage (auto-created) |
| `daemon/tests/test_hook_bus.py` | 36 unit tests |
| `scripts/smoke_hooks.sh` | Smoke test script |
| `.ai/HOOK-FLOW.md` | Discovery documentation |
| `.ai/HOOKBUS-ROLLOUT.md` | This file |

## Feature Flags

All flags default to SAFE (disabled):

| Flag | Default | Purpose |
|------|---------|---------|
| `HOOKBUS_ENABLED` | 0 | Master switch |
| `HOOKBUS_MAX_BYTES` | 200000 | Payload cap (200KB) |
| `HOOKBUS_COMPRESS` | 0 | Enable zlib compression |
| `HOOKBUS_STORE_RAW` | 0 | Store payload in logs |
| `HOOKBUS_DEDUPE_TTL` | 3600 | Dedupe key TTL (1 hour) |
| `HOOKBUS_RETENTION_DAYS` | 7 | Log retention |

## Gradual Rollout Stages

### Stage 1: Silent Monitoring (Week 1)

```bash
# Enable logging only, no behavior changes
export HOOKBUS_ENABLED=1
export HOOKBUS_STORE_RAW=0
```

**Actions:**
1. Add HookBus import to one low-traffic hook (e.g., `post-integration-analyze.py`)
2. Monitor `hook_bus.db` for entries
3. Check P95 latency < 10ms

**Rollback:** `unset HOOKBUS_ENABLED`

### Stage 2: Dedupe on PostToolUse (Week 2)

```python
# In unified-post-tool-tracker.py, add:
from hook_bus import guarded_execution, generate_dedupe_key, is_enabled

if is_enabled():
    dedupe = generate_dedupe_key("tool_track", tool_name, timestamp[:10])
    with guarded_execution("post-tool-tracker", "PostToolUse", tool_name, dedupe) as ctx:
        if not ctx.skipped:
            # existing logic
```

**Metrics to Watch:**
- `dedupe_hits` > 0 indicates duplicate prevention
- `failures` should stay at 0

### Stage 3: Full Integration (Week 3)

```bash
export HOOKBUS_ENABLED=1
export HOOKBUS_STORE_RAW=1  # Enable payload storage
```

Wrap remaining high-traffic hooks:
- `auto-cache-pre.py` (PreToolUse)
- `task-sync-post.py` (PostToolUse)
- `continuous-learning-stop.py` (Stop)

### Stage 4: Production (Week 4+)

Add to session startup:
```bash
export HOOKBUS_ENABLED=1
export HOOKBUS_STORE_RAW=0  # Disable payload storage in prod
```

## Integration Pattern

### Decorator Pattern (Simplest)

```python
from hook_bus import guard, is_enabled

@guard("hook-name", "EventType", "ToolName")
def hook_main(input_data):
    # Your existing logic
    return result

if __name__ == "__main__":
    if is_enabled():
        result = hook_main(sys.stdin.read())
        print(result.output if result.success else "")
    else:
        # Original code path
```

### Context Manager Pattern (More Control)

```python
from hook_bus import guarded_execution, generate_dedupe_key, is_enabled

if is_enabled():
    dedupe = generate_dedupe_key("category", "identifier")
    with guarded_execution("hook-name", "EventType", dedupe_key=dedupe) as ctx:
        if not ctx.skipped:
            result = do_work()
            ctx.set_output(result)
else:
    result = do_work()  # Original path
```

## Monitoring

### CLI Commands

```bash
# Check status
python daemon/hook_bus.py status

# View metrics (last 24h)
python daemon/hook_bus.py metrics

# View metrics (last 1h)
python daemon/hook_bus.py metrics 1

# Cleanup old logs
python daemon/hook_bus.py cleanup
```

### SQL Queries

```sql
-- Recent hook executions
SELECT hook_name, status, duration_ms, created_at
FROM hook_logs ORDER BY created_at DESC LIMIT 20;

-- Failures
SELECT hook_name, error, created_at
FROM hook_logs WHERE status = 'error'
ORDER BY created_at DESC;

-- Dedupe effectiveness
SELECT hook_name,
       SUM(CASE WHEN status = 'dedupe_skip' THEN 1 ELSE 0 END) as deduped,
       COUNT(*) as total
FROM hook_logs GROUP BY hook_name;

-- P95 latency per hook
SELECT hook_name,
       AVG(duration_ms) as avg_ms,
       MAX(duration_ms) as max_ms
FROM hook_logs
WHERE status = 'success'
GROUP BY hook_name;
```

## Performance Targets

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| P50 latency | < 2ms | > 5ms |
| P95 latency | < 10ms | > 15ms |
| P99 latency | < 25ms | > 50ms |
| Failure rate | 0% | > 1% |
| Dedupe hit rate | varies | < 0% (none working) |

## Rollback Procedure

### Quick Rollback (Instant)

```bash
# Disable HookBus entirely
export HOOKBUS_ENABLED=0
# Or unset
unset HOOKBUS_ENABLED
```

### Full Rollback

1. Remove HookBus imports from modified hooks
2. Delete database: `rm daemon/hook_bus.db`
3. Revert hook changes in git

### Data Cleanup

```sql
-- Clear all HookBus data
DELETE FROM hook_logs;
DELETE FROM dedupe_keys;
DELETE FROM hook_metrics;
```

## Known Limitations

1. **No real-time metrics** - Metrics are computed on query, not stored
2. **No distributed tracing** - Correlation IDs are local-only
3. **Dedupe is per-process** - Multiple Claude instances have separate dedupe
4. **Context manager body runs** - Must check `ctx.skipped` manually

## Future Enhancements

- [ ] Export metrics to Prometheus/StatsD
- [ ] Add distributed tracing headers
- [ ] Cross-process dedupe via Dragonfly
- [ ] Real-time alerting on failure spikes
- [ ] Auto-disable hooks with high failure rates

## Sign-off Checklist

- [x] Unit tests pass (36/36)
- [x] Smoke test passes
- [x] Feature flags documented
- [x] Rollback procedure documented
- [x] Performance targets defined
- [x] Integration patterns documented
- [ ] Week 1 deployment scheduled
- [ ] Monitoring dashboard created

---

**Owner:** Atlas System
**Review:** Required before Stage 2
