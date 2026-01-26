# Standing Directives

**MANDATORY READ ON EVERY SESSION - These are user orders that MUST be followed**

---

## Core Directives

### 1. Auto-Wire Everything (2026-01-26)
When creating ANY system, module, or fix:
- Wire it immediately into the architecture
- Don't wait for instructions
- Update ARCHITECTURE-LIVE.md
- Test the wiring

**A system that isn't wired doesn't exist.**

### 2. Institutionalize Discoveries (2026-01-26)
When discovering a workaround or pattern:
- Store in `command_optimizer.py` for automatic application
- Store in memory system for recall
- Add to `DISCOVERIES.md` for documentation
- Enforcement > Documentation

**Files aren't enough - wire enforcement.**

### 3. Capture Deferred Tasks (2026-01-26)
When user recommends something not immediately acted on:
- Capture via `deferred_tasks.py`
- Surface on next session start
- Don't lose user recommendations

### 4. No Forgotten Knowledge (2026-01-26)
- All directives stored here
- All discoveries stored in memory
- Session-briefing reads this file
- Context compaction preserves key learnings

---

## Semantic Cache Priority (2026-01-26)

User recommended repos for semantic caching - MUST investigate and integrate:
1. **prompt-cache** - https://github.com/messkan/prompt-cache
   - Two-stage verification (matches our architecture)
   - Go-based, runs as proxy
   - Multi-provider support

2. **oasysdb** - https://github.com/edwinkys/oasysdb
   - Rust-based in-memory vector store
   - IVFPQ algorithm
   - NOTE: Currently unmaintained

**Action required:** Integrate prompt-cache or build equivalent semantic verification layer.

---

## Operational Rules

1. Read ARCHITECTURE-LIVE.md first every session
2. Read this file (DIRECTIVES.md) every session
3. Check deferred_tasks for pending recommendations
4. Apply command_optimizer patterns automatically
5. Update all docs when making changes

---

**LAST UPDATED:** 2026-01-26
