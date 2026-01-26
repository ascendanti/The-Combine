# Tripartite AI Integration Plan (Claude CLI + OpenAI + LocalAI)

**Goal:** unify the existing agents/skills/hooks/rules with deterministic routing and tiered model selection so the system defaults to low‑cost local inference, escalates to Claude/OpenAI only when needed, and remains coherent across time. This plan builds on the current architecture and already‑implemented plumbing while addressing the “capability amnesia” and autorouter failures noted in the repo. It explicitly aligns the daemon, hooks, and atlas_spine so that agent/skill invocation becomes automatic instead of manual.

---

## 1) What already exists (to reuse, not rebuild)

**Key wiring already in place**
- A structured architecture with clear input/processing/context/output layers and a defined role for `.claude/agents`, `.claude/skills`, and `.claude/hooks`.【F:specs/INTEGRATION-ARCHITECTURE.md†L1-L200】
- A resource map that already describes which agent, hook, or script should be used for common tasks (e.g., `oracle` for research, `scout` for exploration, `kraken` for implementation).【F:.claude/RESOURCE-MAP.md†L1-L200】
- A LocalAI offload plan for ingestion, summarization, and embedding that reduces Claude token usage.【F:thoughts/LOCALAI-INTEGRATION-PLAN.md†L1-L200】
- A system audit showing that hooks and skills exist but daemon modules and integration loops are not fully wired (many idle modules).【F:specs/SYSTEM-AUDIT.md†L1-L200】
- Optimization guidance already captured: lazy RAG gating, delta handoffs, model routing tiers, and Dragonfly caching are present but need tighter enforcement across the query path.【F:SYSTEM-OPTIMIZATION-REVIEW.md†L1-L200】
- A deterministic router (atlas_spine) that can handle 80%+ of routing without LLM usage and already defines operator categories for LOOKUP/OPEN/DIAGNOSE/TEST/THINK/PATCH.【F:.claude/RESOURCE-MAP.md†L115-L160】

**Interpretation:** most of the infrastructure exists, but the “capability registry + router” layer is missing, leading to manual invocation and a tendency for LLMs to forget or bypass tools, skills, agents, and hooks.

---

## 2) Root causes of current friction

1. **Capability amnesia:** agent/skill metadata is not centralized or machine‑queryable. The router can’t reliably select a tool without a canonical registry to consult.【F:.claude/RESOURCE-MAP.md†L1-L200】
2. **Routing is mostly implicit:** current hooks are rich, but routing logic depends on the model’s memory of rules rather than a deterministic classifier path.【F:.claude/RESOURCE-MAP.md†L1-L200】
3. **LocalAI underutilized:** LocalAI is positioned for bulk processing, but is not enforced as the default tier for triage, chunking, or summarization workflows.【F:thoughts/LOCALAI-INTEGRATION-PLAN.md†L1-L200】
4. **Feedback loops not wired:** many built daemon modules are idle, and outputs aren’t fed back into strategy, outcome tracking, or planning docs.【F:specs/SYSTEM-AUDIT.md†L1-L200】

---

## 3) Integration blueprint (the “Contract Spine”)

### 3.1 Capability Registry (single source of truth)
**Deliverable:** a generated registry (JSON + markdown) that lists all agents, skills, hooks, and rules with their triggers, domains, costs, and preferred model tier.

**Why it solves the problem:** the router only needs to consult a structured registry to decide *which agent/skill/tool* to invoke. This makes auto‑summoning deterministic.

**Implementation details**
- Create a generator that scans:
  - `.claude/agents/*` (agent name, description, specialization)
  - `.claude/skills/*` (skill name, usage examples, dependencies)
  - `.claude/hooks/*` (trigger, pre/post actions)
  - `.claude/rules/*` (behavioral constraints)
- Output:
  - `.claude/config/capabilities.json` (machine‑readable)
  - `.claude/config/capabilities.md` (human‑readable)
- Include tags like `domain`, `risk_level`, `token_cost`, `default_model_tier`, `preferred_router`.

**Reference alignment:** the repo already uses indexed resource maps and repository indices for automation; this registry formalizes those into an input for routing logic.【F:.claude/RESOURCE-MAP.md†L1-L200】【F:.claude/REPOSITORY-INDEX.md†L1-L200】

---

### 3.2 Router Stack (deterministic first, LLM as fallback)
**Target routing order:**
1. **atlas_spine router** (rule‑based classification) → 2. **LocalAI intent classifier** → 3. **Claude/OpenAI escalation**.

**Why:** avoid token burn on “where is X” and “open Y” tasks. Use atlas_spine for deterministic operations, and use LocalAI for cheap classification before escalation.

**Implementation detail:**
- **Stage 1:** atlas_spine handles LOOKUP/OPEN/DIAGNOSE/TEST/PATCH requests directly. (Already defined in atlas_spine routing and operator patterns.)【F:.claude/RESOURCE-MAP.md†L115-L160】
- **Stage 2:** LocalAI classifier predicts `{agent|skill|hook|script}` to invoke for complex requests.
- **Stage 3:** Claude/OpenAI invoked only if LocalAI classifier confidence < threshold or if request tags require high‑capability reasoning.

**Measurable outcome:** reduce token usage while still guaranteeing correctness by escalation on low confidence.

---

### 3.3 Agent/Skill Invocation Protocol (auto‑summon)
**Deliverable:** a strict invocation protocol that maps intent → agent/skill without relying on prompt memory.

**How to implement:**
- Update the existing context router hook to read from the capability registry and return a *forced routing decision* instead of a suggestion.
- If agent/skill is not found, fall back to the `architect` agent (plan) or `scout` (explore) based on intent tag.

**Why:** this solves “Claude CLI forgets where things are” and prevents token‑wasteful iterations. The router becomes the source of truth, not the model’s recollection of rules.

---

### 3.4 LocalAI Workload Allocation (what it *should* do)
Based on the current LocalAI integration plan, LocalAI is best suited for bulk and deterministic tasks, freeing Claude for high‑value reasoning.【F:thoughts/LOCALAI-INTEGRATION-PLAN.md†L1-L200】

**Default LocalAI workloads**
- PDF chunking/summarization + concept extraction (ingestion).
- Intent classification and skill/agent routing.
- Embedding generation and semantic search.
- Document normalization and taxonomy classification (PDF naming/organization).

**Escalate to Claude/OpenAI when:**
- Multi‑step planning, architectural decisions, or deep synthesis required.
- LocalAI confidence < threshold.
- Output must be high‑precision, client‑facing text (public docs, scripts, investor content).

---

### 3.5 Claude/OpenAI Role (high‑value only)
Claude/OpenAI become *executive reasoning layers* rather than “do everything” engines. They should:
- Review, fuse, and refine summaries produced by LocalAI.
- Handle high‑stakes decisions, creative output, or cross‑domain synthesis.
- Author final specs, strategy, or product deliverables.

This aligns with existing guidance on model routing tiers and L‑RAG gating.【F:SYSTEM-OPTIMIZATION-REVIEW.md†L1-L200】

---

## 4) Practical integration fixes (dev paths)

### A) Build the registry + router
**Path:**
1. Add `capability_registry.py` (scanner) in `daemon/` or `.claude/scripts/`.
2. Auto‑generate `.claude/config/capabilities.json` and `.claude/config/capabilities.md`.
3. Modify `context-router`/`orchestrator-route` hooks to call the registry.
4. Route to atlas_spine for deterministic actions, otherwise run LocalAI classifier.

**Outcome:** deterministic auto‑summon, reduced token use, no “forgotten tools.”

---

### B) Make LocalAI the default tier for bulk tasks
**Path:**
1. In ingestion pipeline, default to LocalAI for summary + chunk extraction.
2. Use LocalAI for “labeling” tasks like PDF taxonomy classification.
3. Reserve Claude/OpenAI for long‑form synthesis.

**Outcome:** immediate token savings and scalable ingestion.

---

### C) Consolidate feedback loops and run idle modules
**Path:**
1. Add missing daemon modules to docker‑compose (strategy_evolution, outcome_tracker, self_improvement, coherence, metacognition).
2. Wire outcomes from task execution into `outcome_tracker` and `strategy_ops`.
3. Auto‑update `task.md` and `EVOLUTION-PLAN.md` when phases complete.

**Why:** the system audit shows most modules are idle even though built; wiring them closes the learning loop.【F:specs/SYSTEM-AUDIT.md†L1-L200】

---

### D) Obsidian + PDF organization (taxonomy + ingestion)
**Path:**
1. Use LocalAI classification to apply the repo’s reference taxonomy (rename + foldering).
2. Store normalized metadata in the UTF DB and OpenMemory before export to Obsidian.
3. Use delta handoffs and embeddings to minimize retrieval context in Obsidian workflows.

**Outcome:** low‑token retrieval + structured knowledge graph.

---

## 5) Model tiering for current hardware (16GB RAM, CPU)

**Current hardware constraints** (16GB RAM, CPU‑only) mean large models are not feasible locally. Recommended default local configuration:

| Task | LocalAI model class | Reason |
|------|---------------------|--------|
| Intent classification / routing | 3B–7B instruct (4‑bit) | CPU‑friendly, fast inference |
| Summarization / extraction | 7B instruct (4‑bit) | Good enough for chunk‑level summaries |
| Embeddings | MiniLM / BGE‑small | Low‑latency + low RAM |

**Strategy:** keep the local tier deterministic and cheap. Use Claude/OpenAI for reasoning‑heavy tasks or final polish.

---

## 6) Suggested roadmap (90‑day path)

### Phase 1 (Week 1–2): Registry + Router MVP
- Generate capabilities registry.
- Hook `context-router` into registry + atlas_spine.
- Add LocalAI intent classifier for non‑deterministic requests.

### Phase 2 (Week 3–5): LocalAI task re‑allocation
- Make ingestion and PDF classification default to LocalAI.
- Add Dragonfly caching for repeat summaries. (Aligned with optimization review.)【F:SYSTEM-OPTIMIZATION-REVIEW.md†L1-L200】

### Phase 3 (Week 6–8): Feedback loop + observability
- Run idle strategy modules in Docker.
- Connect outcome_tracker → strategy_ops → evolution_tracker.
- Auto‑update key planning docs on events.

### Phase 4 (Week 9–12): Productization
- Expose a thin API (daemon/api.py) for the future dashboard.
- Build the “media company management dashboard” as a separate UI that consumes the API.
- Prepare for GPU‑enabled home box by adding GPU profiles to docker compose.

---

## 7) Definition of “integrated and efficient” (success criteria)

- **Token savings:** LocalAI handles 60%+ of requests; Claude/OpenAI handle <40%.
- **Auto‑summon:** 90% of tasks invoke a specific agent/skill without manual prompting.
- **Latency:** deterministic atlas_spine routes respond in <2 seconds for lookup/open/diagnose.
- **Coherence:** handoff + delta summaries reduce context bloat, while strategy evolution updates plans automatically.

These targets align with the optimization and architecture documentation already in the repo and provide measurable acceptance criteria for a production‑grade system.【F:SYSTEM-OPTIMIZATION-REVIEW.md†L1-L200】【F:specs/INTEGRATION-ARCHITECTURE.md†L1-L200】

---

## 8) Immediate next actions (lowest effort, highest leverage)

1. Generate capability registry (agents/skills/hooks/rules).
2. Route deterministic tasks through atlas_spine, then LocalAI classifier.
3. Move PDF taxonomy classification and foldering to LocalAI.
4. Wire outcome_tracker/strategy_evolution into the daemon loop.

These steps directly address the “forgotten tools/skills,” local AI underuse, and lack of coherent routing.

---

## 9) Immediate implementation details (repo wiring)

To resolve the “Claude can’t find things” issue, wire a session briefing into SessionStart so core docs are injected into context on boot:

- Add a SessionStart script that prints a condensed briefing (task.md, EVOLUTION-PLAN.md, latest handoff) to stdout so Claude Code auto-ingests it.
- Keep the briefing short to avoid context bloat and rely on the capability registry + router for deeper routing.

This is a pragmatic bridge until the capability registry and deterministic router take full control of task dispatch.

---

## 10) Alignment with repo architecture

This plan does not add a parallel system; it operationalizes what the repo already includes:
- The architecture already assumes `.claude/agents`, `.claude/skills`, `.claude/hooks`, and local agents should interlock.【F:specs/INTEGRATION-ARCHITECTURE.md†L1-L200】
- The resource map already encodes routing intent and agent roles; the registry formalizes it for deterministic routing.【F:.claude/RESOURCE-MAP.md†L1-L200】
- The LocalAI plan already describes the right workloads for local inference; this plan enforces it by default.【F:thoughts/LOCALAI-INTEGRATION-PLAN.md†L1-L200】

---

**Bottom line:** implement a formal capability registry + deterministic router layer, then enforce LocalAI as the default tier for bulk tasks. Escalate to Claude/OpenAI only for high‑value reasoning. This turns the system into a coherent tripartite stack with predictable routing, lower token usage, and higher operational reliability.
