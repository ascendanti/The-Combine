# Integration Analysis: oh-my-opencode

**Source:** https://github.com/code-yeongyu/oh-my-opencode
**Status:** Analyzed
**Priority:** High
**Date:** 2026-01-26

## Overview

oh-my-opencode is a comprehensive plugin for OpenCode that provides multi-model orchestration, background agents, and the "Sisyphus" autonomous coding pattern. Built on the philosophy that human intervention during agentic work is a failure signal.

## Core Philosophy (Ultrawork Manifesto)

1. **Human intervention = failure signal**
2. **Code should be indistinguishable from senior engineer output**
3. **Higher token usage acceptable for 10x productivity gains**
4. **Minimize human cognitive load**
5. **Predictable, Continuous, Delegatable execution**

## Key Patterns

### 1. Ultrawork Magic Keyword

**Pattern:** Type `ultrawork` or `ulw` in any prompt to trigger full autonomous mode.

What happens:
- Parallel agents research context
- LSP for surgical refactoring
- Todo continuation enforcement
- Work continues until complete

### 2. Todo Continuation Enforcer

**Purpose:** Forces agent to complete work, prevents "I'm done" lies.

**Implementation approach:**
```python
# Hook that checks TODO list on Stop/PreCompact
if incomplete_todos:
    force_resume()
```

### 3. Comment Checker

**Purpose:** Prevents AI from adding excessive comments.

**Rule:** Code generated should be indistinguishable from human-written code.
- Comments only for critical warnings
- Remove excessive documentation
- No AI slop

### 4. Multi-Model Orchestration

| Agent | Model | Purpose |
|-------|-------|---------|
| Sisyphus | Opus 4.5 High | Main orchestrator |
| Oracle | GPT 5.2 Medium | Design, debugging |
| Frontend Engineer | Gemini 3 Pro | Frontend development |
| Librarian | Sonnet 4.5 | Docs/code search |
| Explore | Grok Code | Fast codebase exploration |

### 5. Background Agents

**Pattern:** Run multiple agents in parallel for context gathering.

```
Main agent stays lean
↓
Background tasks to faster/cheaper models
↓
Results aggregated
↓
Main agent continues with full context
```

### 6. Category System

Route tasks to optimal models based on domain:
- `visual` → Gemini 3 Pro
- `business-logic` → Opus
- `debugging` → GPT 5.2
- Custom categories supported

### 7. Prometheus Interview Mode

**Alternative to ultrawork:** Structured interview before execution.
- Researches codebase
- Asks clarifying questions
- Surfaces edge cases
- Documents decisions
- Generates complete work plan

### 8. Wisdom Accumulation

Learn from work across sessions:
- Cache learnings
- Avoid redundant exploration
- Stop research when sufficient context gathered

## Curated MCPs

1. **Exa** - Web search
2. **Context7** - Official documentation
3. **Grep.app** - GitHub code search

## Hooks (25+ built-in)

All configurable via `disabled_hooks`:
- Todo Enforcer
- Comment Checker
- LSP Integration
- Ralph Loop (continuous execution)
- Background task coordination

## Adopted Patterns

### For Immediate Integration

1. **ultrawork keyword detection**
   - Add to UserPromptSubmit hook
   - Trigger extended autonomous mode

2. **Todo Continuation Enforcer**
   - Add to Stop/PreCompact hooks
   - Verify TaskList completion

3. **Comment Checker**
   - Add to PostToolUse for Edit/Write
   - Flag excessive comments

4. **Background Agents pattern**
   - Already have Task tool
   - Add parallel execution tracking

### Deferred

1. **Full multi-model orchestration** - Requires model switching support
2. **Prometheus interview mode** - Complex UX flow
3. **Category-based routing** - Need model cost analysis first

## Implementation Notes

### ultrawork Detection

```python
# In UserPromptSubmit hook
if "ultrawork" in prompt.lower() or "ulw" in prompt.lower():
    inject_context({
        "mode": "ultrawork",
        "continue_until_complete": True,
        "parallel_research": True,
        "minimal_comments": True
    })
```

### Todo Enforcer

```python
# In Stop hook
from task_list import get_incomplete_tasks
incomplete = get_incomplete_tasks()
if incomplete:
    return {
        "continue": False,
        "decision": "block",
        "reason": f"Incomplete tasks: {[t.subject for t in incomplete]}"
    }
```

## Quality Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| Philosophy | A+ | Strong principles, well-articulated |
| Implementation | B+ | Complex but powerful |
| Documentation | A | Excellent manifesto and guides |
| Portability | B | Tied to OpenCode, needs adaptation |

## Related Tasks

- #15: Integrate ultrawork pattern
- #9: Parallel agent mesh (related to background agents)

## Files to Reference

```
oh-my-opencode/
├── docs/ultrawork-manifesto.md      # Philosophy
├── docs/guide/overview.md           # Getting started
├── sisyphus-prompt.md               # Main agent prompt
├── src/features/builtin-skills/     # Skills implementation
└── src/hooks/                       # Hook implementations
```

## Next Steps

1. Implement ultrawork keyword detection
2. Add Todo Continuation Enforcer to Stop hook
3. Create Comment Checker PostToolUse hook
4. Test with existing Task tool parallelism
