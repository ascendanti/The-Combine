# Evolution Plan Adherence

**MANDATORY: Follow the phased evolution plan in EVOLUTION-PLAN.md**

## On Session Start

1. Read `EVOLUTION-PLAN.md` to know current phase
2. Read latest handoff in `thoughts/handoffs/`
3. Read `task.md` for current objectives
4. Continue from where left off - do not restart

## Phase Discipline

- Complete current phase before moving to next
- Update EVOLUTION-PLAN.md status after completing tasks
- Create handoffs when switching phases or ending sessions
- Follow the priority integration order defined in the plan

## Current Phase Check

Before starting work, verify:
```
What phase are we in?
What's the completion status?
What's the next action?
```

## Phase Transition Rules

1. **Do not skip phases** - each builds on previous
2. **Validate before proceeding** - test that phase works
3. **Document changes** - update plan status, create handoffs
4. **Commit progress** - git commit after significant milestones

## Priority Order

When multiple tasks compete:
1. Current phase completion > new features
2. Stability > new capabilities
3. Integration > isolation
4. Documentation > implementation (for handoffs)

## Reporting

- Send Telegram update when phase milestones complete
- Create handoff at phase completion
- Update task.md with status changes
