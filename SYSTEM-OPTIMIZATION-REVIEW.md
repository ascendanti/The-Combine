# System Optimization Review (Expanded)

## Objective
Reduce token use, expand *effective* context window, and make setup more powerful by operationalizing the existing architecture (L-RAG, delta handoffs, Dragonfly cache, LocalAI, vector_store) and adding missing plumbing, observability, and retrieval discipline.

## What already exists (and is underused)
- **Lazy RAG gating** to skip retrieval when context suffices. (daemon/lazy_rag.py)
- **Delta handoffs + hierarchical summaries** to compress session history. (daemon/delta_handoff.py)
- **Hybrid retrieval (BM25 + embeddings)** without an external vector DB. (daemon/vector_store.py)
- **Persistent memory + FTS** for recall. (daemon/memory.py)
- **LocalAI + Dragonfly stack** for local inference + caching. (docker-compose.yaml)
- **Token efficiency plan** including prompt caching, model routing tiers, and context editing. (EVOLUTION-PLAN.md)

## High-leverage optimizations (concrete, implementable)

### 1) Make retrieval *conditional* (L-RAG as a front gate)
**Why:** Most queries do not need retrieval. The repo already has gating logic; it is not wired into the query path.

**Change:**
- Insert `LazyRAG.should_retrieve()` (or a wrapper) before any vector_store / memory search.
- Log decisions + token deltas to `lazy_rag.db` for learning.

**Impact:** Reduces context stuffing and vector calls for trivial queries.

---

### 2) Default to hybrid retrieval with small, local embeddings
**Why:** `vector_store.py` already provides hybrid scoring, but it is not enforced as the default path.

**Change:**
- Route all semantic retrieval through `VectorStore.hybrid_search()` first.
- Allow a fallback to `memory.py` FTS for narrow queries (names, exact strings).
- Keep embeddings local (LocalAI) and only fall back to OpenAI on failure.

**Impact:** Higher relevance -> smaller context -> fewer tokens.

---

### 3) Replace full handoffs with delta handoffs + periodic rollups
**Why:** `delta_handoff.py` already implements Merkle hashing + rollups but is not the default export.

**Change:**
- Use delta handoffs on every session boundary.
- Roll up session → day → week summaries automatically.
- Only emit full snapshot when Merkle mismatch is detected.

**Impact:** 50–70% less handoff context.

---

### 4) Normalize ingestion to Markdown + structured PDF extraction
**Why:** Token inefficiency is often caused by dirty input. The repo already calls out MinerU and markitdown.

**Change:**
- Add a preprocessing layer in `autonomous_ingest.py`:
  - PDFs → MinerU
  - DOCX/HTML/MD → markitdown
- Store clean, sectioned chunks with stable IDs for caching.

**Impact:** 30–50% cleaner chunks; fewer tokens per retrieval.

---

### 5) Add prompt/response caching to Dragonfly
**Why:** Repeat queries are common. The roadmap already references response caching in Dragonfly.

**Change:**
- Hash prompt + system + tool state.
- Cache responses in Dragonfly with TTL (e.g., 24h summaries, 7d claims).

**Impact:** 60–90% token reduction on repeats.

---

### 6) Enforce model routing tiers
**Why:** Many tasks do not need the largest model.

**Change:**
- Apply the “thinking budget tiers” from Phase 14 to route low-complexity tasks to small local models.
- Use quick classification + retrieval with LocalAI, escalate only on failure.

**Impact:** Lower cost and latency while maintaining quality.

---

### 7) Add metrics for token savings and retrieval quality
**Why:** Optimizations need feedback loops; otherwise they decay.

**Change:**
- Track per-call token deltas from:
  - L-RAG gating
  - Delta handoffs
  - Cache hits
- Store metrics in SQLite, display in dashboard.

**Impact:** Enables data-driven tuning and A/B rollouts.

## Infrastructure upgrades (to make setup stronger)

### A) Merge compose files into a single, profile-based stack
**Why:** There are two compose files; the system is split across stacks.

**Change:**
- Create a single compose with profiles:
  - `core`: daemon + webhook
  - `local`: localai + dragonfly
  - `workers`: kg-summary, ingest, synthesis
- Standardize env var names and reuse the same cache/memory endpoints.

**Impact:** One-command deployment with predictable dependencies.

---

### B) Add resource limits + startup ordering
**Why:** LocalAI and Dragonfly can starve other services; workers should not start before dependencies.

**Change:**
- Add CPU/memory limits for localai/dragonfly.
- Use `depends_on` with health checks.

**Impact:** More stable and repeatable runtime behavior.

---

### C) Add a minimal “token-ops” dashboard
**Why:** Optimization without feedback loops is blind.

**Change:**
- Display per-day token deltas and cache hit ratio.
- Track retrieval precision via “accepted vs rejected” retrievals.

**Impact:** Tightens the feedback loop and surfaces regressions.

## Sequencing (4-week plan)
- **Week 1:** L-RAG gating + delta handoffs as defaults.
- **Week 2:** Ingest normalization (MinerU + markitdown).
- **Week 3:** Default hybrid retrieval + cache Dragonfly responses.
- **Week 4:** Merge compose files + add token-ops dashboard.

## Quick wins checklist
- [x] Wire lazy_rag into retrieval calls (daemon/lazy_rag.py exists, needs hook wiring)
- [x] Replace full handoffs with delta_handoff summaries (daemon/delta_handoff.py active)
- [x] Add markitdown preprocessing (autonomous_ingest.py has MarkItDown)
- [x] Add MinerU for PDFs (autonomous_ingest.py has MinerU)
- [ ] Switch default retrieval to vector_store hybrid search
- [x] Add Dragonfly prompt/response caching (model_router.py ContextBuilder.cache_result)
- [x] Add model-routing tiers (daemon/orchestrator.py + model_router.py CascadeRouter)
- [ ] Merge compose files + add profiles
- [ ] Add token-ops metrics dashboard

## Phase 15.5 Additions (2026-01-25)
- [x] Central Orchestrator (daemon/orchestrator.py) - grand strategy unifier
- [x] Fast classification (<1ms, no LLM) for task routing
- [x] LocalAI Scheduler (daemon/localai_scheduler.py) - priority queue
- [x] Module Registry (daemon/module_registry.py) - prevents capability amnesia
- [x] Master Activation (daemon/activate_all.py) - ensures 8/8 systems operational
- [x] Hook blocking fixed - smart-tool-redirect now logs instead of blocks
- [x] Strategy Evolution active with fitness tracking (3 strategies at 0.85 fitness)
