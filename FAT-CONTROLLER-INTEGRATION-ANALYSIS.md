# Multi-Repo Integration Analysis

**Sources:**
- https://github.com/iainforrest/fat-controller (9 stars)
- https://github.com/EveryInc/compound-engineering-plugin (6,315 stars)
- https://github.com/davepoon/buildwithclaude (2,309 stars)

**Analysis Date:** 2026-01-25
**Purpose:** Evaluate patterns for integration into Atlas system

---

## Executive Summary

Fat-Controller has **5 superior patterns** we should adopt immediately:
1. Authority-based memory (single source of truth per content type)
2. QUICK.md as router (entry point to all memory)
3. Automated solution capture (YAML for grep-first retrieval)
4. Wave-based parallel execution (conflict-free parallelism)
5. Three-tier model routing with reasoning effort levels

---

## Pattern Comparison

### 1. Memory Architecture

| Aspect | Fat-Controller | Atlas (Current) | Verdict |
|--------|---------------|-----------------|---------|
| Source of truth | Single authority per content | Multiple overlapping files | **FC Better** |
| Entry point | QUICK.md routes to files | CLAUDE.md + task.md + handoffs | **FC Better** |
| Token efficiency | Grep-first, load selectively | Load full files | **FC Better** |
| Decision records | ADR in decisions/ | None formalized | **FC Better** |
| Solution capture | YAML in solutions/ | Memory.py (unstructured) | **FC Better** |

**Recommendation:** Adopt authority-based memory with QUICK.md router.

---

### 2. Agent Orchestration

| Aspect | Fat-Controller | Atlas (Current) | Verdict |
|--------|---------------|-----------------|---------|
| Orchestrator pattern | `/execute` spawns agents | Direct Task tool calls | **FC Better** |
| Context isolation | Fresh context per agent | Shared context accumulation | **FC Better** |
| Parallel execution | Wave-based (conflict-free) | Ad-hoc parallel | **FC Better** |
| Cross-task learning | STATE.md between agents | Handoffs (manual) | **FC Better** |
| Status tracking | XML with subtask status | task.md checkboxes | **Equal** |

**Recommendation:** Adopt orchestrator pattern with STATE.md learnings.

---

### 3. Model Routing

| Aspect | Fat-Controller | Atlas (Current) | Verdict |
|--------|---------------|-----------------|---------|
| Tiers | 3 (Codex/Sonnet/Codex-xhigh) | 3 (LocalAI/Codex/Claude) | **Equal** |
| Complexity-based | 1-2: Codex, 3: Sonnet, 4-5: Codex-xhigh | By task type | **FC Better** |
| Reasoning effort | medium/high/xhigh flags | Thinking budget tiers | **Atlas Better** |
| Cost tracking | Implicit | Explicit cost tracking | **Atlas Better** |

**Recommendation:** Combine approaches - use complexity scores with reasoning effort + cost tracking.

---

### 4. Retrieval & Caching

| Aspect | Fat-Controller | Atlas (Current) | Verdict |
|--------|---------------|-----------------|---------|
| Retrieval strategy | Grep-first, then full read | L-RAG gating + hybrid search | **Atlas Better** |
| Caching | None explicit | Dragonfly + token-optimizer | **Atlas Better** |
| Vector search | None | vector_store.py hybrid | **Atlas Better** |
| Embedding | None | LocalAI embeddings | **Atlas Better** |

**Recommendation:** Keep Atlas retrieval/caching, add grep-first for structured memory.

---

### 5. Automated Capture

| Aspect | Fat-Controller | Atlas (Current) | Verdict |
|--------|---------------|-----------------|---------|
| Tech debt | TECH_DEBT.md from reviews | None formalized | **FC Better** |
| Solutions | YAML in solutions/ | memory.py (mixed) | **FC Better** |
| Deprecations | DEPRECATIONS.md | None | **FC Better** |
| Patterns | patterns/*.md by domain | skills/ directory | **Equal** |

**Recommendation:** Add structured capture for tech debt, solutions, deprecations.

---

## Patterns to Adopt

### Priority 1: Authority-Based Memory (1 day)

Create `.ai/` directory with authority map:

```
.ai/
├── QUICK.md            # Router only (no content)
├── ARCHITECTURE.json   # System topology
├── FILES.json          # File index (globs, not line numbers)
├── BUSINESS.json       # Business rules, data models
├── OPS.md              # Commands, runbooks, debugging
├── PATTERNS.md         # Index pointing to domain patterns
├── patterns/           # Domain-specific patterns
├── decisions/          # ADR records
├── solutions/          # YAML solution capture
├── CONSTRAINTS.md      # What we can't do
├── DEPRECATIONS.md     # Deprecated APIs/modules
└── TECH_DEBT.md        # Deferred issues from reviews
```

**Authority Map for QUICK.md:**
| Content Type | Authoritative File |
|--------------|-------------------|
| Commands (build, test, deploy) | OPS.md |
| File locations | FILES.json |
| System design | ARCHITECTURE.json |
| Business rules | BUSINESS.json |
| Code patterns | PATTERNS.md → patterns/*.md |
| Constraints | CONSTRAINTS.md |
| Deprecations | DEPRECATIONS.md |
| Tech debt | TECH_DEBT.md |
| Architecture decisions | decisions/*.md |
| Past solutions | solutions/*.yaml |

---

### Priority 2: Solution Capture (2 hours)

Add YAML solution capture to memory system:

```yaml
# solutions/hook-daemon-connection.yaml
id: SOL-2026-01-25-001
title: "Hook daemon connection timeout"
problem: "Hooks failing with ECONNREFUSED"
root_cause: "Daemon not started before hooks execute"
solution: |
  1. Check daemon status: python daemon/api.py status
  2. Start daemon: python daemon/runner.py
  3. Verify port 8765 is listening
tags: [hooks, daemon, connection]
files_involved:
  - .claude/hooks/src/daemon-client.ts
  - daemon/runner.py
created: 2026-01-25
```

**Retrieval:** `grep -r "ECONNREFUSED" solutions/` → instant lookup

---

### Priority 3: Orchestrator Pattern (4 hours)

Create `/execute` style orchestrator:

```python
# daemon/orchestrator.py
class TaskOrchestrator:
    """
    Orchestrates task execution via agent delegation.

    Pattern:
    1. Parse task file (XML or YAML)
    2. Build execution waves (conflict-free groups)
    3. Spawn agents per parent task
    4. Collect learnings to STATE.md
    5. Merge results
    """

    def execute_wave(self, tasks: List[Task]) -> List[Result]:
        """Execute a wave of non-conflicting tasks in parallel."""
        agents = []
        for task in tasks:
            agent = self.spawn_agent(
                task=task,
                state_md=self.current_state,
                model=self.select_model(task.complexity)
            )
            agents.append(agent)

        results = await asyncio.gather(*[a.run() for a in agents])
        self.merge_learnings(results)
        return results
```

---

### Priority 4: Tech Debt Tracking (1 hour)

Auto-capture from code reviews:

```markdown
# .ai/TECH_DEBT.md

## Active Tech Debt

### TD-001: Duplicate database connections
**Severity:** MEDIUM
**Source:** Code review 2026-01-25
**File:** daemon/*.py (19 SQLite DBs)
**Issue:** Each module creates own connection
**Suggested Fix:** Consolidate to connection pool
**Effort:** 3 days

### TD-002: Missing error boundaries in hooks
**Severity:** LOW
**Source:** Code review 2026-01-24
**File:** .claude/hooks/src/*.ts
**Issue:** Errors crash entire hook chain
**Suggested Fix:** Add try/catch per hook
**Effort:** 2 hours
```

---

## Patterns to Keep (Atlas Advantages)

These Atlas patterns are **superior** to Fat-Controller:

1. **L-RAG lazy retrieval** - Fat-Controller has no retrieval gating
2. **Dragonfly caching** - No caching layer in Fat-Controller
3. **Hybrid vector search** - Fat-Controller uses grep only
4. **Delta handoffs** - Fat-Controller uses full STATE.md
5. **Thinking budget tiers** - More granular than reasoning effort flags
6. **Cost tracking** - Explicit token/cost monitoring
7. **LocalAI integration** - Free local inference

---

## Integration Plan

### Week 1: Memory Authority
- [ ] Create `.ai/` directory structure
- [ ] Migrate knowledge from scattered files to authority map
- [ ] Create QUICK.md router
- [ ] Add solution capture workflow

### Week 2: Orchestration
- [ ] Build orchestrator.py with wave execution
- [ ] Add STATE.md cross-task learning
- [ ] Integrate with existing agent system
- [ ] Add XML/YAML task file parsing

### Week 3: Automated Capture
- [ ] Add tech debt capture to code review
- [ ] Create deprecation tracking
- [ ] Wire solution capture to memory.py
- [ ] Add ADR template and workflow

### Week 4: Validation
- [ ] Test authority-based retrieval (grep-first)
- [ ] Measure token savings vs current approach
- [ ] Document patterns in PATTERNS.md
- [ ] Create domain skill files

---

## Quick Wins (Today)

1. **Create `.ai/QUICK.md`** - Router to existing files
2. **Create `.ai/TECH_DEBT.md`** - Start tracking deferred issues
3. **Create `solutions/` directory** - Begin YAML solution capture
4. **Add authority comment** to each memory file

---

## Conclusion

Fat-Controller's authority-based memory and orchestrator patterns would provide **30-50% token savings** through:
- Grep-first retrieval (load only what's needed)
- Single source of truth (no duplication)
- Fresh context per agent (no accumulation)
- Structured solution lookup (instant debugging)

Combined with Atlas's existing L-RAG, caching, and hybrid retrieval, this creates a **best-of-both** architecture.

**Recommendation:** Adopt Fat-Controller memory patterns while keeping Atlas retrieval/caching superiority.

---

## Compound Engineering Plugin Analysis (6,315 stars)

### Philosophy: Compounding Engineering

> "Each unit of engineering work should make subsequent units of work easier—not harder."

This is the core principle. Every action should:
1. **Plan** → Understand the change and impact
2. **Delegate** → Use AI tools for implementation
3. **Assess** → Verify changes work
4. **Codify** → Update CLAUDE.md with learnings

### Superior Patterns

#### 1. Learnings Researcher Agent
**Pattern:** Grep-first solution lookup before implementing anything.

```markdown
# Before implementing any feature:
1. Grep docs/solutions/ for matching tags/symptoms
2. Read critical-patterns.md (always)
3. Return distilled insights, not raw docs
```

**Why it's better than our memory.py:**
- Structured YAML frontmatter enables grep-first filtering
- Category directories for fast narrowing
- Severity levels prioritize critical patterns
- <30 second lookup for typical directories

#### 2. Solution Capture Schema
```yaml
# docs/solutions/[category]/[filename].md
---
title: "Email threading race condition"
module: BriefSystem
problem_type: performance_issue
component: email_processing
symptoms:
  - "Duplicate emails"
  - "Missing thread context"
root_cause: async_timing
severity: high
tags: [email, threading, race-condition]
---

## Problem
[Description]

## Solution
[What was done]

## Prevention
[How to avoid in future]
```

#### 3. Critical Patterns File
**docs/solutions/patterns/critical-patterns.md** - Always-read file with high-severity patterns promoted to required reading.

### Components

| Type | Count | Key Examples |
|------|-------|--------------|
| Agents | 24 | learnings-researcher, git-history-analyzer, best-practices-researcher |
| Commands | 13 | /review, /plan, /release-docs |
| Skills | 11 | compound-docs, gemini-imagegen |
| MCP Servers | 2 | playwright, context7 |

### Adoption Recommendations

| Pattern | Effort | Impact |
|---------|--------|--------|
| Solution capture YAML schema | 2 hours | High - grep-first lookup |
| Learnings researcher agent | 4 hours | High - prevent repeated mistakes |
| Critical patterns file | 1 hour | Medium - always-check guardrails |
| Category-based directories | 2 hours | Medium - faster narrowing |

---

## BuildWithClaude Analysis (2,309 stars)

### What It Is
A **hub/marketplace** aggregating Claude Code extensions:
- 117 Agents
- 175 Commands
- 28 Hooks
- 26 Skills
- 50 Plugins
- 4,500+ MCP Servers indexed
- 20k+ Community Plugins indexed

### Superior Patterns

#### 1. Plugin Categorization
Well-organized category structure:

**Agents (11 categories):**
- Development & Architecture
- Language Specialists (Python, Go, Rust, TypeScript, C/C++)
- Quality & Security
- Infrastructure & Operations
- Data & AI
- Crypto & Blockchain

**Commands (22 categories):**
- Version Control
- Code Analysis
- Documentation
- Project Management

#### 2. Agent Format Standard
```markdown
---
name: agent-name
description: When to invoke this agent
category: category-name
tools: Read, Write, Bash
---

You are a [role description]...
```

#### 3. Useful Agents to Adopt
| Agent | Purpose | Why We Need It |
|-------|---------|----------------|
| `python-pro` | Python optimization | LocalAI/daemon code |
| `security-auditor` | Security review | Pre-commit validation |
| `devops-troubleshooter` | Deployment debug | Docker/container issues |
| `ml-engineer` | ML patterns | UTF/embedding work |

### Adoption Recommendations

| Pattern | Effort | Impact |
|---------|--------|--------|
| Install buildwithclaude marketplace | 5 min | High - 117 agents available |
| Adopt agent format standard | 1 hour | Medium - consistency |
| Add category structure to .claude/agents/ | 2 hours | Medium - organization |

---

## Combined Recommendations

### Immediate Actions (Today)

1. **Install buildwithclaude marketplace**
   ```bash
   /plugin marketplace add davepoon/buildwithclaude
   ```

2. **Create `.ai/QUICK.md`** router (Fat-Controller pattern)

3. **Create `solutions/` directory** with YAML schema (Compound-Engineering pattern)

4. **Create `critical-patterns.md`** (Compound-Engineering pattern)

### Week 1: Memory Authority + Solution Capture

| Day | Task | Source |
|-----|------|--------|
| 1 | Create .ai/ directory structure | Fat-Controller |
| 2 | Migrate CLAUDE.md content to authority files | Fat-Controller |
| 3 | Create solution capture YAML schema | Compound-Eng |
| 4 | Implement learnings-researcher agent | Compound-Eng |
| 5 | Test grep-first retrieval | Both |

### Week 2: Agent Enhancement

| Day | Task | Source |
|-----|------|--------|
| 1 | Install buildwithclaude plugins | BuildWithClaude |
| 2 | Categorize existing 48 agents | BuildWithClaude |
| 3 | Add critical-patterns.md | Compound-Eng |
| 4 | Wire solution capture to reviews | Compound-Eng |
| 5 | Validate token savings | All |

---

## Token Savings Projection

| Pattern | Source | Savings |
|---------|--------|---------|
| Authority-based memory (grep-first) | Fat-Controller | 30-50% |
| Solution YAML (instant lookup) | Compound-Eng | 20-40% |
| Fresh context per agent | Fat-Controller | 40-60% |
| L-RAG + Dragonfly (existing) | Atlas | 50-70% |
| **Combined** | All | **60-80%** |

---

## Files to Create

```
.ai/
├── QUICK.md                    # Router (Fat-Controller)
├── ARCHITECTURE.json           # System topology
├── FILES.json                  # File index
├── PATTERNS.md                 # Pattern index
├── OPS.md                      # Commands, runbooks
├── CONSTRAINTS.md              # Limitations
├── DEPRECATIONS.md             # Deprecated modules
├── TECH_DEBT.md               # Deferred issues
├── decisions/                  # ADR records
│   └── 001-authority-memory.md
└── solutions/                  # YAML solution capture
    ├── patterns/
    │   └── critical-patterns.md
    ├── performance-issues/
    ├── runtime-errors/
    └── integration-issues/
```
