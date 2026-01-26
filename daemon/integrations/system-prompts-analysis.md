# Integration Analysis: system-prompts-and-models-of-ai-tools

**Source:** https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools
**Status:** Analyzed
**Priority:** High
**Date:** 2026-01-26

## Overview

Collection of leaked/extracted system prompts from 30+ AI coding tools. Contains 30,000+ lines of prompt engineering insights.

## Tools Covered

| Tool | Status | Key Patterns |
|------|--------|--------------|
| Cursor | Full prompts | Agent flow, parallel tools, todo management |
| Windsurf | Full prompts | Context handling, search strategies |
| Devin AI | Partial | Autonomous execution patterns |
| v0 | Full prompts | UI generation, component patterns |
| Amp | Full prompts | CLI integration |
| Lovable | Full prompts | App generation |
| Google | Partial | Search integration |
| Perplexity | Partial | Research patterns |
| Anthropic | Reference | Official patterns |
| Replit | Full prompts | Environment integration |

## Key Patterns Extracted

### 1. Agent Execution Flow (from Cursor)

```
1. Detect goal from user message
2. Discovery pass (read-only scan)
3. Create structured plan in todo list
4. Execute with status updates
5. Reconcile and close todo list
6. Provide summary
```

### 2. Status Update Specification

```
Definition: Brief progress note (1-3 sentences)
- What just happened
- What you're about to do
- Blockers/risks if relevant

Critical rule: If you say you'll do something, actually do it
```

### 3. Parallel Tool Execution

```
CRITICAL: Invoke all relevant tools concurrently
- Multiple file reads: Run all in parallel
- Multiple searches: Execute simultaneously
- Independent edits: Batch together

Limit: 3-5 tool calls per batch to avoid timeout
```

### 4. Todo List Management

```
Gate before edits:
- Mark completed tasks as completed
- Set next task to in_progress
- Then proceed with edit

Cadence after steps:
- After each successful step, update todo status
- Reconcile before yielding to user
```

### 5. Communication Style

```
- Optimize for clarity and skimmability
- Use backticks for file/function names
- Don't wrap entire message in code blocks
- State assumptions and continue (don't stop for approval)
- Terse summaries, not verbose explanations
```

### 6. Context Understanding

```
Semantic search is MAIN exploration tool
- Start with broad, high-level queries
- Break multi-part questions into focused sub-queries
- Run multiple searches with different wording
- Keep searching until CONFIDENT
```

## Adopted Patterns

### Already Implemented

1. **Parallel tool execution** - Task tool with background agents
2. **Status updates** - Built into response flow
3. **Todo management** - TaskCreate/TaskUpdate tools

### For Adoption

1. **Gate before edits** - Add to pre-edit hook
2. **Completion specification** - Enforce todo reconciliation
3. **Summary specification** - Add to session end

## Reference Files Copied

```
.claude/reference/system-prompts/
├── Cursor/
│   ├── Agent Prompt 2025-09-03.txt
│   ├── Agent Prompt 2.0.txt
│   ├── Agent Tools v1.0.json
│   └── Chat Prompt.txt
└── (more to be added)
```

## Implementation Notes

### Gate Before Edits Hook

```python
# PreToolUse hook for Edit/Write
def gate_before_edit():
    """Enforce todo reconciliation before edits."""
    incomplete = get_incomplete_tasks()
    current = get_current_task()

    if incomplete and not current:
        return {
            "decision": "block",
            "reason": "Set a task to in_progress before editing"
        }
```

### Completion Check

```python
# Stop hook
def completion_check():
    """Verify all tasks complete before ending."""
    incomplete = get_incomplete_tasks()

    if incomplete:
        return {
            "decision": "block",
            "message": f"Incomplete tasks: {[t.subject for t in incomplete]}"
        }
```

## Quality Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| Comprehensiveness | A+ | 30+ tools covered |
| Currency | A | Updated January 2026 |
| Actionability | A | Direct prompt patterns |
| Documentation | B | Minimal explanation |

## Related Resources

- Cursor: Agent flow, parallel execution
- Windsurf: Context management
- Devin: Autonomous patterns
- v0: Component generation

## Next Steps

1. Copy remaining relevant prompts to reference
2. Implement gate-before-edit hook
3. Add completion check to Stop hook
4. Create prompt template library from patterns
