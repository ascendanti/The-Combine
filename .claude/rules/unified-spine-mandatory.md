# Unified Spine Mandatory

**ALWAYS use the unified_spine.py for autonomous execution.**

## Location
`daemon/unified_spine.py`

## What It Connects
- TaskQueue (tasks.db) - Shared task queue
- LocalAI AutoRouter - Mechanical classification (FREE)
- ModelRouter - Provider abstraction
- OutcomeTracker - Record results
- StrategyEvolver - Active strategies
- Handoff System - Resume interrupted work

## Never Bypass
Do NOT:
- Call Claude directly without routing through autorouter
- Use continuous_executor.py standalone
- Ignore failed imports (fix them!)
- Create parallel task systems

## Auto Mode Command
```bash
python daemon/unified_spine.py daemon --interval 60
```

## Status Check
```bash
python daemon/unified_spine.py status
```

## Flow
```
Strategy → TaskGenerator → TaskQueue → AutoRouter → Execute → OutcomeTracker
                               ↑                          ↓
                           Scheduler                 Learnings
```

LocalAI handles routing (FREE). Claude only for complex tasks.
