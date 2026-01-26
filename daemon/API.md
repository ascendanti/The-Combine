# Daemon API Documentation

This document provides API reference for all daemon modules.

## Table of Contents

1. [Core Infrastructure](#core-infrastructure)
2. [Cognitive Layer](#cognitive-layer)
3. [Strategic Layer](#strategic-layer)
4. [Operational Layer](#operational-layer)
5. [Execution Layer](#execution-layer)
6. [Integration Layer](#integration-layer)

---

## Core Infrastructure

### config.py

Central configuration management.

```python
from daemon.config import cfg

# Access configuration
cfg.DAEMON_DIR       # Path to daemon directory
cfg.PROJECT_DIR      # Path to project root
cfg.LOCALAI_URL      # LocalAI endpoint (default: http://localhost:8080)
cfg.DRAGONFLY_URL    # Dragonfly/Redis endpoint (default: redis://localhost:6379)
```

### schema_migrations.py

Versioned database migrations.

```python
from daemon.schema_migrations import ensure_schema, init_migrations_table

# Define migrations
MIGRATIONS = [
    (1, "Create users table", "CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT)"),
    (2, "Add email column", "ALTER TABLE users ADD COLUMN email TEXT"),
]

# Apply migrations
conn = sqlite3.connect("database.db")
applied = ensure_schema(conn, "my_database", MIGRATIONS, verbose=True)
print(f"Applied {applied} migrations")
```

### error_handler.py

Unified error handling with database tracking.

```python
from daemon.error_handler import ErrorHandler, ErrorSeverity

handler = ErrorHandler()

# Log an error
handler.log_error(
    error=exception,
    context={"task_id": "123", "operation": "file_read"},
    severity=ErrorSeverity.HIGH
)

# Query errors
recent = handler.get_recent_errors(hours=24, severity="high")
patterns = handler.get_error_patterns()
```

### mcp_health.py

MCP server health monitoring.

```python
from daemon.mcp_health import check_all_servers, warmup_servers, ServerHealth

# Check health of all MCP servers
health = check_all_servers()
for name, status in health.items():
    print(f"{name}: {status.status}")  # healthy/degraded/unhealthy

# Warm up servers to reduce cold-start latency
warmup_servers()
```

---

## Cognitive Layer

### coherence.py

Goal alignment and coherence checking.

```python
from daemon.coherence import CoherenceEngine

engine = CoherenceEngine()

# Add a goal
engine.add_goal("Maximize code quality", priority=1)

# Check if an action aligns with goals
score = engine.check_action("Refactor authentication module")
# Returns alignment score 0-1

# Get coherence report
report = engine.get_report()
```

### metacognition.py

Self-awareness and capability assessment.

```python
from daemon.metacognition import Metacognition

meta = Metacognition()

# Assess capability for a task
assessment = meta.assess_capability("Write Python async code")
# Returns confidence level and reasoning

# Get calibration stats
calibration = meta.get_calibration()
# Shows prediction accuracy over time
```

### self_improvement.py

Pattern analysis and improvement suggestions.

```python
from daemon.self_improvement import SelfImprovement

improver = SelfImprovement()

# Analyze with first principles
analysis = improver.analyze_first_principles("Why do tests keep failing?")

# Generate improvement suggestions
improvements = improver.generate_improvements()
for imp in improvements:
    print(f"{imp.category}: {imp.suggestion}")
```

---

## Strategic Layer

### strategy_evolution.py

Strategy management and evolution.

```python
from daemon.strategy_evolution import StrategyEvolution

evolution = StrategyEvolution()

# List strategies
strategies = evolution.list_strategies()

# Evolve strategies
evolved = evolution.evolve(generations=3)

# A/B test strategies
result = evolution.test(strategy_a="S001", strategy_b="S002")

# Identify moats
moats = evolution.identify_moats()
```

### strategy_ops.py

Strategy operationalization.

```python
from daemon.strategy_ops import StrategyOps

ops = StrategyOps()

# Deploy a strategy
ops.deploy(strategy_id="S001", environment="staging")

# Measure KPIs
kpis = ops.measure(strategy_id="S001")

# Check for drift
drift = ops.check_drift(threshold=0.1)

# Get health dashboard
health = ops.health()
```

### local_autorouter.py

Token-minimizing routing to LocalAI/Claude.

```python
from daemon.local_autorouter import LocalAutoRouter

router = LocalAutoRouter()

# Route a request
result = router.route("Summarize this document")
# Returns: model used, response, cost

# Get routing stats
stats = router.stats()
print(f"LocalAI utilization: {stats['localai_percent']}%")
```

---

## Operational Layer

### outcome_tracker.py

Record and analyze action outcomes.

```python
from daemon.outcome_tracker import OutcomeTracker

tracker = OutcomeTracker()

# Record an outcome
tracker.record(
    action="agent:kraken",
    result="success",
    context={"task": "TDD implementation"},
    duration_ms=5000
)

# Query outcomes
outcomes = tracker.query(action_type="agent:*")

# Find patterns
patterns = tracker.find_patterns(min_success=0.7)

# Get recommendations
recs = tracker.recommend(action_type="agent:*")
```

### self_continue.py

Self-continuation after context compaction.

```python
from daemon.self_continue import SelfContinue

sc = SelfContinue()

# Create a checkpoint
sc.checkpoint(phase="Phase 15", task="Integration", notes="In progress")

# Queue a continuation
sc.queue(source="user", action="Continue with testing")

# Resume from checkpoint
context = sc.resume()
print(context)  # Returns continuation context
```

### task_generator.py

Proactive task generation.

```python
from daemon.task_generator import TaskGenerator

gen = TaskGenerator()

# Generate tasks from opportunities
tasks = gen.generate()
for task in tasks:
    print(f"{task.source}: {task.description}")

# Get pending tasks
pending = gen.pending()

# Approve a task
gen.approve(task_id="T001")

# Run in daemon mode
gen.daemon(interval=3600)  # Check every hour
```

---

## Execution Layer

### continuous_executor.py

Autonomous execution daemon.

```python
from daemon.continuous_executor import ContinuousExecutor

# Submit a task
task_id = ContinuousExecutor.submit(
    prompt="Generate a summary",
    source="user",
    priority=5
)

# Check status
status = ContinuousExecutor.get_status()
print(f"Running: {status['running']}")
print(f"Tasks: {status['tasks']}")

# Start daemon (blocking)
executor = ContinuousExecutor()
executor.start()

# Stop daemon
ContinuousExecutor.stop()
```

### sequential_executor.py

Sequential tool execution (avoids tool_use ID bug).

```python
from daemon.sequential_executor import SequentialExecutor

executor = SequentialExecutor()

# Execute with sequential tool handling
result = executor.execute("Read and summarize file.txt")
print(result)

# Check execution status
# See daemon/sequential_executor.db for logs
```

### model_router.py

Intelligent model routing with cost tracking.

```python
from daemon.model_router import ModelRouter

router = ModelRouter()

# Route a request
response = router.route(
    prompt="Simple calculation: 2+2",
    context={"complexity": "low"}
)

# Get routing statistics
stats = router.get_stats()
print(f"Total cost: ${stats['total_cost']}")
```

---

## Integration Layer

### telegram_notify.py

Send notifications to Telegram.

```python
from daemon.telegram_notify import send_message, send_file

# Send a message
send_message("Task completed successfully")

# Send a file
send_file("report.pdf", caption="Daily report")
```

### gdrive_setup.py / rclone_sync.py

Google Drive integration.

```python
from daemon.rclone_sync import sync_to_drive, sync_from_drive

# Sync local folder to Drive
sync_to_drive("thoughts/handoffs", "Atlas/Backup/Handoffs")

# Sync from Drive to local
sync_from_drive("Atlas/Models", "local_models/")
```

### mcp_server.py

MCP server for Claude integration.

```python
# Run as MCP server
python daemon/mcp_server.py

# Available tools:
# - daemon.submit_task
# - daemon.get_status
# - daemon.query_memory
# - daemon.route_request
```

---

## CLI Quick Reference

```bash
# Continuous executor
python daemon/continuous_executor.py start|stop|status|submit|once
python daemon/continuous_executor.py submit -p "Your task here"

# Sequential executor
python daemon/sequential_executor.py run -p "Your task"
python daemon/sequential_executor.py test
python daemon/sequential_executor.py status

# Task generator
python daemon/task_generator.py generate|pending|approve|daemon

# Strategy operations
python daemon/strategy_evolution.py list|evolve|test|moats
python daemon/strategy_ops.py deploy|measure|drift|health

# Self-improvement
python daemon/self_improvement.py improvements
python daemon/self_improvement.py insights --actionable

# Outcome tracking
python daemon/outcome_tracker.py record|query|patterns|stats|recommend

# Memory operations
python daemon/memory.py add|search|list

# Model routing
python daemon/model_router.py route "prompt"
python daemon/model_router.py stats
```

---

## Database Files

| Database | Purpose | Location |
|----------|---------|----------|
| `tasks.db` | Task queue | daemon/tasks.db |
| `continuous_executor.db` | Execution logs | daemon/continuous_executor.db |
| `sequential_executor.db` | Sequential execution logs | daemon/sequential_executor.db |
| `errors.db` | Error tracking | daemon/errors.db |
| `outcomes.db` | Outcome tracking | daemon/outcomes.db |
| `strategies.db` | Strategy evolution | daemon/strategies.db |
| `router.db` | Model routing stats | daemon/router.db |
| `mcp_health.db` | MCP server health | daemon/mcp_health.db |

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LOCALAI_URL` | LocalAI endpoint | http://localhost:8080 |
| `DRAGONFLY_URL` | Dragonfly/Redis | redis://localhost:6379 |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | (required for notifications) |
| `TELEGRAM_CHAT_ID` | Telegram chat ID | (required for notifications) |
| `ANTHROPIC_API_KEY` | Anthropic API key | (optional, for API mode) |

---

*Generated: 2026-01-25*
