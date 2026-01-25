# System Audit - What's Wired vs What's Built

*Generated: 2026-01-25*

---

## Summary

| Category | Built | Running | Gap |
|----------|-------|---------|-----|
| Daemon Modules | 43 | 4 | **39 idle** |
| Docker Services | 6 | 5 | 1 (strategy-evolution new) |
| Hooks | 15+ | Active | OK |
| Skills | 116 | On-demand | OK |

---

## Daemon Modules Status

### ✅ RUNNING (in Docker)

| Module | Service | Interval | Purpose |
|--------|---------|----------|---------|
| `autonomous_ingest.py` | autonomous-ingest | 5m | Document ingestion |
| `kg_summary_worker.py` | kg-summary-worker | 2h | KG summarization |
| `synthesis_worker.py` | synthesis-worker | 24h | Cross-doc synthesis |
| `localai` | localai | Always | LLM inference |
| `dragonfly` | dragonfly-cache | Always | Caching |

### ⚠️ BUILT BUT NOT RUNNING

#### Critical (Should be running)

| Module | Purpose | Why Not Running |
|--------|---------|-----------------|
| `strategy_evolution.py` | Evolve strategies | Not in docker-compose (added now) |
| `strategy_ops.py` | Operationalize strategies | Not in docker-compose |
| `outcome_tracker.py` | Track outcomes | Not in docker-compose |
| `self_improvement.py` | Extract patterns | Not in docker-compose |
| `evolution_tracker.py` | Sync planning docs | Not in docker-compose (added now) |
| `coherence.py` | Goal alignment | Not automated |
| `metacognition.py` | Self-awareness | Not automated |

#### Integration (Need triggers)

| Module | Purpose | Trigger Needed |
|--------|---------|----------------|
| `bisimulation.py` | State similarity | Hook into decisions.py |
| `gcrl.py` | Goal-conditioned RL | Hook into decisions.py |
| `claim_similarity.py` | Compare claims | Hook into ingest |
| `decisions.py` | Multi-criteria | Needs callers |
| `emergent.py` | Detect emergence | Needs scheduler |

#### API/External (Run on demand)

| Module | Purpose | When to Use |
|--------|---------|-------------|
| `api.py` | REST API | If exposing externally |
| `mcp_server.py` | MCP interface | Already via npx |
| `email_trigger.py` | Email automation | Needs IMAP setup |
| `email_sender.py` | Send emails | Called by triggers |
| `github_webhook.py` | GitHub events | Needs webhook setup |
| `telegram_notify.py` | Notifications | Called by workers |
| `freqtrade_bridge.py` | Trading bridge | Not configured |

#### Utility (Helpers)

| Module | Purpose | Status |
|--------|---------|--------|
| `model_router.py` | Route to LLMs | Used by workers |
| `memory.py` | Persistent memory | Used by workers |
| `memory_router.py` | Memory search | Needs integration |
| `vector_store.py` | Embeddings | Partially used |
| `utf_extractor.py` | UTF schema | Used by ingest |
| `utf_enhancer.py` | Enhance UTFs | Not called |
| `task_queue.py` | Task management | Used by workers |
| `task_generator.py` | Generate tasks | Not automated |
| `token_monitor.py` | Track tokens | Not automated |

---

## Integration Gaps

### 1. Feedback Loop NOT Wired

```
Current:
  Ingest → Store → Done (dead end)

Should be:
  Ingest → Store → Analyze → Learn → Improve → Ingest (cycle)
```

**Missing connections:**
- outcome_tracker not recording results
- strategy_evolution not running
- self_improvement not extracting patterns
- No feedback from outputs back to inputs

### 2. Cognitive Modules NOT Called

| Module | Should Connect To |
|--------|-------------------|
| `bisimulation.py` | `decisions.py` (check similar states) |
| `gcrl.py` | `decisions.py` (transfer policies) |
| `coherence.py` | All actions (check alignment) |
| `metacognition.py` | All modules (self-assess) |

### 3. Planning Docs NOT Auto-Updated

| Doc | Should Update When |
|-----|-------------------|
| `EVOLUTION-PLAN.md` | Phase completes |
| `SCI-FI-TECHNICAL-ROADMAP.md` | Capability unlocked |
| `task.md` | Task completes |

---

## Efficiency Analysis

### What's Working Well

| Component | Efficiency |
|-----------|------------|
| Dragonfly cache | 25x faster than Redis |
| LocalAI | $0 token cost |
| MinerU extraction | 30-50% better than raw |
| MarkItDown | 20-30% token savings |

### What's Inefficient

| Issue | Impact | Fix |
|-------|--------|-----|
| 43 modules, 4 running | 90% idle | Add to docker-compose |
| No feedback loop | Linear not cyclic | Wire strategy services |
| Manual doc updates | Stale docs | Auto-update on events |
| Scattered DBs | Query overhead | Consolidate to PostgreSQL |
| Native tools used | +70% tokens | Enforce smart_* redirect |

---

## Action Plan

### Immediate (Today)

1. [x] Add strategy-evolution service to docker-compose
2. [x] Add evolution-tracker service to docker-compose
3. [ ] Rebuild and start new services
4. [ ] Verify feedback loop activates

### Short-term (This Week)

5. [ ] Wire bisimulation into decisions.py
6. [ ] Wire gcrl into decisions.py
7. [ ] Add coherence checks to action hooks
8. [ ] Consolidate DBs to PostgreSQL

### Medium-term (Next 2 Weeks)

9. [ ] Auto-update planning docs on events
10. [ ] Add emergent behavior detection
11. [ ] Full MAPE-K loop implementation
12. [ ] Dashboard for monitoring all modules

---

## Quick Start New Services

```bash
# Rebuild with new services
cd "C:\Users\New Employee\Downloads\Atlas-OS-main\Claude n8n"
docker-compose build strategy-evolution evolution-tracker

# Start new services
docker-compose up -d strategy-evolution evolution-tracker

# Check logs
docker-compose logs -f strategy-evolution
docker-compose logs -f evolution-tracker
```

---

*The system has powerful capabilities but they're not wired together. Focus on closing the feedback loops.*
