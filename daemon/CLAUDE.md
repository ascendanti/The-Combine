# Daemon - Atlas Autonomous Execution System

## Purpose

The daemon directory contains the **autonomous execution infrastructure** for Atlas. It's a collection of 98 Python modules and 56 SQLite databases that work together to enable:

- **Autonomous task execution** without human intervention
- **Multi-model routing** (LocalAI, Codex, Claude, Haiku)
- **Self-improvement** through outcome tracking and strategy evolution
- **Memory persistence** across sessions

## Architecture

```
                    ┌─────────────────┐
                    │deterministic_   │  ← Layer 1: Pattern matching
                    │    router.py    │     (80%+ requests routed here)
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ orchestrator.py │  ← Layer 2: Intent classification
                    │  (fast_classify)│     + strategy selection
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
    ┌──────▼──────┐  ┌───────▼───────┐  ┌──────▼──────┐
    │ LocalAI     │  │   Codex       │  │   Claude    │
    │ (FREE)      │  │   (cheap)     │  │   (quality) │
    └─────────────┘  └───────────────┘  └─────────────┘
```

### Core Modules (WIRED)

| Module | Purpose | Wire Point |
|--------|---------|------------|
| `unified_spine.py` | Backbone coordinator | SessionStart hook |
| `orchestrator.py` | Central brain, fast_classify | Via deterministic_router |
| `deterministic_router.py` | Query routing without LLM | UserPromptSubmit hook |
| `memory_router.py` | Unified memory interface | Via session-briefing.py |
| `context_router.py` | HOT/WARM/COLD file tiering | Via auto-cache-pre.py |
| `feedback_loop.py` | Analytics cycle | Stop hook |
| `outcome_tracker.py` | Result tracking | Via unified_spine |
| `strategy_evolution.py` | Approach optimization | Via unified_spine |
| `model_router.py` | Provider abstraction | Via orchestrator |
| `local_autorouter.py` | Rule-based routing | Via unified_spine |

### Support Modules

| Module | Purpose |
|--------|---------|
| `task_queue.py` | SQLite-backed task management |
| `task_generator.py` | Strategy-driven task creation |
| `execution_spine.py` | Retrieval + execution |
| `memory.py` | SQLite persistence for learnings |
| `feedback_bridge.py` | MAPE controller integration |
| `self_continue.py` | Handoff resume system |
| `continuous_executor.py` | Long-running daemon process |

### Database Schema

All state is persisted in SQLite databases:

| Database | Contents |
|----------|----------|
| `tasks.db` | Task queue (pending, in_progress, completed) |
| `outcomes.db` | Action results with success/failure |
| `strategies.db` | Evolved approaches with fitness scores |
| `memory.db` | Learnings and decisions |
| `router.db` | Routing decisions and costs |
| `orchestrator.db` | Classification history |
| `analytics.db` | Component health metrics |
| `context_router.db` | File access patterns (HOT/WARM/COLD) |

## Design Patterns

### 1. Graceful Degradation

Every import is wrapped in try/except with fallback stubs:

```python
try:
    from swarms import Agent
    SWARMS_AVAILABLE = True
except ImportError:
    SWARMS_AVAILABLE = False
    Agent = None
```

### 2. Path-Safe Imports

All modules add daemon directory to sys.path:

```python
DAEMON_DIR = Path(__file__).parent
sys.path.insert(0, str(DAEMON_DIR))
```

### 3. Centralized Configuration

Use `config.py` for all paths:

```python
from config import cfg
db_path = cfg.DAEMON_DIR / "mydb.db"
```

### 4. Outcome Recording

Every action should record its outcome:

```python
from outcome_tracker import record_outcome
record_outcome("action_name", "success", {"context": "details"})
```

### 5. Strategy Pattern

Strategies evolve through natural selection:

```python
# Strategies with higher success rates get higher fitness
# Low-fitness strategies are eventually deprecated
```

## Key Flows

### Task Execution Flow

```
1. Check pending handoffs (resume interrupted work)
2. Check strategies for generated tasks
3. Check scheduler for due tasks
4. Check task queue for pending work
5. Route via LocalAI autorouter (FREE classification)
6. Execute via appropriate provider
7. Track outcomes
8. Update learnings
```

### Memory Flow

```
Query → L1 Dragonfly (fast cache)
     → L2 SQLite daemon memory
     → L3 Knowledge Graph (entities)
```

### Routing Flow

```
Query → deterministic_router (patterns)
     → orchestrator.fast_classify (intent)
     → model_router (provider selection)
     → Execute with fallback cascade
```

## Running the System

### Status Check
```bash
python daemon/unified_spine.py status
```

### Daemon Mode
```bash
python daemon/unified_spine.py daemon --interval 60
```

### Feedback Cycle
```bash
python -X utf8 daemon/feedback_loop.py
```

### MCP Health
```bash
python daemon/mcp_health.py warmup
```

## Common Issues

### Windows Unicode Errors

Use UTF-8 mode for scripts with Unicode output:

```bash
python -X utf8 daemon/feedback_loop.py
```

### Import Errors

Ensure daemon is in path before importing:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
```

### Database Locks

SQLite can lock under concurrent access. Use WAL mode:

```python
conn.execute("PRAGMA journal_mode=WAL")
```

## Reliable Templates

Per feedback_loop analysis, these modules have 100% health (15+ successes):

- `feedback_loop.py` - Use as template for analytics modules
- `feedback_cycle.py` - Use as template for cycle operations

## Adding New Modules

1. Follow graceful degradation pattern for imports
2. Use `config.py` for paths
3. Record outcomes for all actions
4. Add database schema to module docstring
5. Wire into appropriate hook if needed

---

**Last Updated:** 2026-01-27
**Modules:** 98 Python files
**Databases:** 56 SQLite files
