# Integration Analysis: create-claude

**Source:** https://github.com/ramonclaudio/create-claude
**Status:** Integrated
**Priority:** High
**Date:** 2026-01-26

## Overview

`create-claude` is a zero-dependency Claude Code bootstrap tool that sets up production-ready configuration with slash commands, subagents, hooks, and smart permissions.

## Key Patterns

### 1. Slash Commands (8 total)

| Command | Purpose | Model |
|---------|---------|-------|
| `/commit` | Git commits with conventional format | Haiku (cost-efficient) |
| `/explain` | Code explanations | Default |
| `/fix` | Structured bug fixing | Default |
| `/optimize` | Performance improvements | Default |
| `/pr` | Pull request creation | Default |
| `/review` | Brutal code reviews | Default |
| `/test` | Test runner with patterns | Default |
| `/validate` | Lint, typecheck, format | Default |

**Pattern:** Commands use inline shell execution with `!` syntax:
```markdown
## Context
- Status: !`git status --short`
- Staged changes: !`git diff --cached --stat`
```

### 2. Subagents (3 specialized)

#### pre-commit
- **Purpose:** Ruthless pre-commit validation
- **Tools:** Bash, Read, Edit, Grep
- **Key pattern:** 5-step validation checklist
- **Output:** READY ✓ or BLOCKED ✗

#### refactor
- **Purpose:** Aggressive complexity reduction
- **Tools:** Read, Edit, MultiEdit, Grep, Glob
- **Key pattern:** Delete-first approach
- **Decision criteria:**
  - Can't explain in one sentence = too complex
  - Abstraction without 3+ uses = delete
  - Nested beyond 2 levels = flatten

#### debugger
- **Purpose:** Root cause analysis
- **Tools:** Read, Edit, Bash, Grep, Glob
- **Key pattern:** Error → Reproduce → Isolate → Fix → Verify
- **Output:** ROOT CAUSE, FIX, VERIFIED

### 3. Safety Hook (PreToolUse)

**File:** `safety.cjs`

**Dangerous patterns blocked:**
- `rm -rf /` (root paths)
- `sudo rm`
- `dd` to devices
- `mkfs.` filesystem formatting
- `curl|sudo`, `wget|sudo` pipe attacks

**Sensitive files protected:**
- `/etc/passwd`, `/etc/shadow`
- `.ssh/id_*`, `.aws/credentials`
- `.env`, `secrets`, `.pem`, `.key`

### 4. Terse Output Style

**Pattern:** Minimal responses
```
Good: "Fixed parser.js:23"
Bad: "I have successfully identified and resolved..."
```

### 5. Advanced Statusline

Three modular helpers:
- `statusline.cjs` - Main status display
- `statusline-git.cjs` - Git operations
- `statusline-detect.cjs` - Framework detection

## Adopted Patterns

### Files Copied

```
.claude/agents/production/
  - pre-commit.md
  - refactor.md
  - debugger.md

.claude/output-styles/
  - terse.md

.claude/hooks/
  - safety.cjs
  - format.cjs
  - session-end.cjs
```

### Integration Points

1. **Command Router:** Add /commit, /review, /validate activation
2. **Subagent Registry:** Register pre-commit, refactor, debugger
3. **Hook Pipeline:** Wire safety.cjs into PreToolUse
4. **Output Mode:** Add terse.md to available styles

## Deferred Patterns

- **bypassPermissions mode:** Risky for production use
- **Import-based memory:** Requires @import support in CLAUDE.md

## Implementation Notes

### Command Format
```markdown
---
description: Create git commit with message
argument-hint: [commit-message]
allowed-tools: Bash(git:*)
model: claude-3-5-haiku-20241022
---
```

### Subagent Format
```markdown
---
name: pre-commit
description: Pre-commit validation specialist...
tools: Bash, Read, Edit, Grep
---
```

## Quality Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| Code Quality | A | Clean, minimal, production-ready |
| Documentation | B+ | Good inline docs, could use more examples |
| Architecture | A | Zero dependencies, modular design |
| Maintainability | A | Simple structure, easy to extend |

## Related Tasks

- #13: Command Router implementation
- #14: Adopt slash commands and subagents (this integration)

## Next Steps

1. Activate commands in deterministic router
2. Register subagents in capability registry
3. Test safety hook with existing pipeline
4. Enable terse output style option
