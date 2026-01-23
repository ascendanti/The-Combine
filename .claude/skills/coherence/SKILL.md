# Coherence - Goal Management Skill

Manage goals, constraints, and cross-domain coherence for unified personal AI.

## Invocation

```
/coherence <command> [options]
```

## Commands

### Goal Management

```bash
# Add a goal
python daemon/coherence.py add "Goal title" --timeframe medium --domains "finance,tasks"

# List goals
python daemon/coherence.py list

# View constraints for domain
python daemon/coherence.py constraints finance
```

### Cross-Domain Operations

```bash
# List registered modules
python daemon/registry.py list

# Get unified context from all domains
python daemon/registry.py context

# Check action coherence
python daemon/registry.py check finance --action '{"cost": 500}'
```

## Goal Timeframes

| Timeframe | Scope | Examples |
|-----------|-------|----------|
| `long` | Years | Career goals, life objectives |
| `medium` | Months | Quarterly targets, projects |
| `short` | Weeks | Weekly plans, sprints |
| `task` | Hours | Individual actions |

## Constraint Types

| Type | Domain | Effect |
|------|--------|--------|
| `budget_max` | finance | Blocks actions exceeding amount |
| `time_window` | calendar | Restricts to available slots |
| `preference` | any | Guides option selection |
| `energy` | tasks | Matches task to capacity |

## Example Workflow

```bash
# 1. Create high-level goal
python daemon/coherence.py add "Reduce monthly expenses" \
  --timeframe medium \
  --domains "finance,tasks" \
  --desc "Cut spending by 20%"

# 2. Check if action is coherent
python daemon/registry.py check finance --action '{"cost": 200, "category": "dining"}'

# 3. Get context for planning
python daemon/registry.py context
```

## Integration with Other Skills

- **/build**: Check coherence before implementation
- **/plan-agent**: Include goal constraints in plans
- **/premortem**: Validate against goal hierarchy

## Architecture

```
GoalCoherenceLayer
├── Goals (SQLite: coherence.db)
│   ├── Hierarchy (parent_id links)
│   ├── Domains (affected areas)
│   └── Constraints (propagated rules)
│
└── ModuleRegistry
    ├── FinanceModule → budget checks
    ├── CalendarModule → time checks
    └── TasksModule → energy checks
```

## Coherence Checking

When an action is proposed:

1. **Domain validation**: Module's own rules
2. **Constraint check**: Goals that apply to domain
3. **Cross-domain**: Other modules that might be affected

Returns: `(valid: bool, issues: List[str])`
