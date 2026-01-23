# Handoff Skill

Create a handoff document when ending a session or when context is getting full.

## Usage
When you say "done for today", "handoff", "save state", or context is near limit:

1. Create a handoff file in `thoughts/handoffs/`
2. Include:
   - What was accomplished
   - What's in progress
   - What's blocked
   - Next steps
   - Key decisions made

## Template

```yaml
---
date: YYYY-MM-DDTHH:MM:SS
session_name: descriptive-name
status: complete|in_progress|blocked
---

# Handoff: [Brief Title]

## Summary
One paragraph of what happened this session.

## Completed
- [x] Task 1
- [x] Task 2

## In Progress
- [ ] Task 3 (50% done)

## Blocked
- [ ] Task 4 - waiting on user decision about X

## Next Steps
1. First thing to do next session
2. Second thing

## Key Decisions
- Decided to use approach X because Y
- User approved Z

## Files Modified
- path/to/file1.py - added feature
- path/to/file2.js - fixed bug
```

## Resume
When starting a new session, check `thoughts/handoffs/` for the latest handoff and resume from there.
