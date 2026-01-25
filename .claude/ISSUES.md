# Known Issues & Development Opportunities

## Critical Issues (Fix Soon)

### 1. SQLite Schema Drift
**Location:** `daemon/utf_knowledge.db`, `daemon/autonomous_ingest.py`
**Issue:** Schema in `init_utf_db()` differs from actual table (had to ALTER TABLE multiple times)
**Fix:** Add schema migration system or version check on startup

### 2. No GPU Acceleration
**Location:** `docker-compose.yaml`, LocalAI config
**Issue:** Running on CPU-only (Intel laptop), limits LLM throughput
**Fix:** Deploy to GPU-enabled machine or use cloud GPU

### 3. MCP Server Instability
**Location:** `.mcp.json`, global MCP config
**Issue:** MCP servers sometimes fail to start (npx cold start issues)
**Fix:** Pre-install MCP servers globally, add health checks

---

## Performance Issues

### 4. LLM Response Time
**Location:** `daemon/utf_extractor.py`
**Issue:** 5-10 minutes per paper due to CPU-only inference
**Mitigation Applied:** Dragonfly caching, reduced chunk sizes
**Future Fix:** Smaller model (Phi-3-mini) or GPU acceleration

### 5. Context Window Bloat
**Location:** Claude sessions
**Issue:** Sessions hit token limits due to large tool outputs
**Mitigation:** FewWord plugin, smart tool redirect hook
**Future Fix:** Phase 14 Semantic Router with context compression

### 6. No Outcome Tracking (Until Now)
**Location:** N/A (was missing)
**Issue:** No way to learn from success/failure
**Fix:** Created `daemon/outcome_tracker.py` (DONE)

---

## Code Quality Issues

### 7. Duplicate Hook Files
**Location:** `.claude/hooks/`
**Issue:** Both `post-tool-use-tracker.py` and `post_tool_use_tracker.py` exist
**Fix:** Consolidate and remove duplicate

### 8. Inconsistent Error Handling
**Location:** `daemon/*.py`
**Issue:** Some modules use try/except with pass, losing error info
**Fix:** Add proper logging to all error handlers

### 9. Hard-coded Paths
**Location:** Various files
**Issue:** Some paths are hard-coded instead of using env vars
**Fix:** Use `settings.local.json` env vars consistently

### 10. No Type Hints
**Location:** Most Python files
**Issue:** Missing type hints make code harder to maintain
**Fix:** Add type hints incrementally (low priority)

---

## Architecture Gaps

### 11. No Intent Classification
**Location:** Request handling
**Issue:** All routing is manual, no automatic skill/agent selection
**Fix:** Phase 14 Semantic Router

### 12. No Cross-Paper Synthesis
**Location:** `daemon/claim_similarity.py`
**Issue:** Can find similar claims but doesn't synthesize novel insights
**Fix:** Phase 15 Knowledge Synthesis

### 13. No Proactive Task Generation
**Location:** N/A (missing capability)
**Issue:** System waits for user input, doesn't initiate tasks
**Fix:** Phase 18 Emergent Autonomy

### 14. Agent Communication is Serial
**Location:** Task tool usage
**Issue:** Agents run sequentially, not in parallel mesh
**Fix:** Phase 17 Agentic Mesh (gRPC bus)

---

## Integration Gaps

### 15. Obsidian Sync One-Way
**Location:** `.claude/scripts/kg-obsidian-sync.py`
**Issue:** KG → Obsidian only, changes in Obsidian not synced back
**Fix:** Add bidirectional sync

### 16. Telegram Polling Only
**Location:** `.claude/scripts/telegram-inbox.py`
**Issue:** Must manually check inbox, no webhook for instant notification
**Fix:** Add Telegram webhook handler

### 17. No GitHub PR Integration
**Location:** `daemon/github_webhook.py`
**Issue:** Webhook exists but not fully integrated with workflows
**Fix:** Wire webhook to skill:review-pr

---

## Documentation Gaps

### 18. No API Documentation
**Location:** `daemon/api.py`
**Issue:** REST endpoints undocumented
**Fix:** Add OpenAPI/Swagger spec or at least README

### 19. Skill Descriptions Incomplete
**Location:** `.claude/skills/`
**Issue:** Many skills lack usage examples
**Fix:** Audit and update skill files

### 20. Handoff Format Not Standardized
**Location:** `thoughts/handoffs/`
**Issue:** Handoff structure varies between files
**Fix:** Create strict YAML schema, validate on creation

---

## Priority Matrix

| Issue | Impact | Effort | Priority |
|-------|--------|--------|----------|
| #6 Outcome Tracking | High | Low | ✅ DONE |
| #11 Intent Classification | High | Medium | Phase 14 |
| #1 Schema Drift | Medium | Low | Next |
| #4 LLM Response Time | High | High | Needs GPU |
| #5 Context Bloat | High | Medium | Phase 14 |
| #7 Duplicate Hooks | Low | Low | Quick win |
| #8 Error Handling | Medium | Medium | Incremental |

---

## Quick Wins (< 1 hour each)

1. [ ] Delete duplicate hook file
2. [ ] Add logging to error handlers in top 5 daemon modules
3. [ ] Create OpenAPI stub for api.py
4. [ ] Standardize handoff YAML schema
5. [ ] Add health check endpoints to containers

---

## Future Development Tracks

### Track A: Token Efficiency
- Phase 14: Semantic Router
- Context compression
- Smart caching strategies

### Track B: Knowledge Growth
- Phase 15: Knowledge Synthesis
- Contradiction detection
- Hypothesis generation

### Track C: Autonomy
- Phase 16-18: Adaptive Learning → Agentic Mesh → Emergent Autonomy
- Outcome-driven strategy evolution
- Self-directed task generation

---

*Last Updated: 2026-01-24*
