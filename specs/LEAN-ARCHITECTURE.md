# Lean Architecture - Efficient Module Design

*Stop building, start integrating*

---

## Problem

- 43 modules built
- 4 services running
- No feedback loop
- Waste of development effort

---

## Lean Principle

**One unified worker** that orchestrates modules, not separate services per module.

---

## Target Architecture

### Services (3 total)

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   LocalAI       │    │   Dragonfly     │    │  Unified Worker │
│   (LLM)         │    │   (Cache)       │    │  (Orchestrator) │
│   $0/token      │    │   25x faster    │    │   ALL MODULES   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Unified Worker - Scheduled Tasks

```python
# unified_worker.py - One process, all tasks

SCHEDULE = {
    # High frequency (minutes)
    "ingest": {"interval": 300, "module": "autonomous_ingest"},
    "token_monitor": {"interval": 600, "module": "token_monitor"},

    # Medium frequency (hours)
    "synthesis": {"interval": 3600, "module": "synthesis_worker"},
    "kg_summary": {"interval": 7200, "module": "kg_summary_worker"},
    "evolution_sync": {"interval": 3600, "module": "evolution_tracker"},

    # Low frequency (daily)
    "strategy_evolve": {"interval": 86400, "module": "strategy_evolution"},
    "self_improve": {"interval": 86400, "module": "self_improvement"},
    "outcome_analyze": {"interval": 86400, "module": "outcome_tracker"},
}
```

---

## Module Classification

### Core (Always Loaded)

| Module | Purpose | Called By |
|--------|---------|-----------|
| `model_router.py` | Route LLM calls | All modules |
| `memory.py` | Persistent storage | All modules |
| `telegram_notify.py` | Notifications | All modules |

### Scheduled (Run Periodically)

| Module | Frequency | Purpose |
|--------|-----------|---------|
| `autonomous_ingest.py` | 5m | Process new docs |
| `synthesis_worker.py` | 1h | Cross-doc patterns |
| `kg_summary_worker.py` | 2h | KG updates |
| `evolution_tracker.py` | 1h | Sync planning docs |
| `strategy_evolution.py` | 24h | Evolve strategies |
| `self_improvement.py` | 24h | Extract learnings |
| `outcome_tracker.py` | 24h | Analyze outcomes |

### On-Demand (Called When Needed)

| Module | Trigger | Purpose |
|--------|---------|---------|
| `decisions.py` | User decision | Evaluate options |
| `bisimulation.py` | decisions.py | Check similar states |
| `gcrl.py` | decisions.py | Transfer policies |
| `coherence.py` | Before actions | Check goal alignment |
| `claim_similarity.py` | After ingest | Compare claims |
| `utf_extractor.py` | autonomous_ingest | Extract UTF schema |

### Dormant (Not Needed Yet)

| Module | Why Dormant |
|--------|-------------|
| `freqtrade_bridge.py` | Trading not configured |
| `email_trigger.py` | Email automation not set up |
| `github_webhook.py` | Webhooks not configured |
| `api.py` | No external API needed |
| `parallel_ingest.py` | Single-threaded sufficient |

---

## Implementation

### unified_worker.py

```python
#!/usr/bin/env python3
"""
Unified Worker - One process, all scheduled tasks.
Replaces: kg-summary-worker, synthesis-worker, autonomous-ingest, strategy-evolution
"""

import time
import importlib
import schedule
from datetime import datetime

# Task registry
TASKS = {
    "ingest": {
        "module": "autonomous_ingest",
        "function": "scan_and_process",
        "interval_minutes": 5,
    },
    "synthesis": {
        "module": "synthesis_worker",
        "function": "run_synthesis",
        "interval_minutes": 60,
    },
    "kg_summary": {
        "module": "kg_summary_worker",
        "function": "summarize_pending",
        "interval_minutes": 120,
    },
    "evolution": {
        "module": "evolution_tracker",
        "function": "sync_documents",
        "interval_minutes": 60,
    },
    "strategy": {
        "module": "strategy_evolution",
        "function": "evolve_once",
        "interval_minutes": 1440,  # 24h
    },
    "improve": {
        "module": "self_improvement",
        "function": "analyze_and_store",
        "interval_minutes": 1440,  # 24h
    },
}

def run_task(name: str, config: dict):
    """Execute a scheduled task."""
    try:
        print(f"[{datetime.now().isoformat()}] Running: {name}")
        module = importlib.import_module(config["module"])
        func = getattr(module, config["function"])
        func()
    except Exception as e:
        print(f"[ERROR] {name}: {e}")

def main():
    print("Unified Worker starting...")

    # Schedule all tasks
    for name, config in TASKS.items():
        schedule.every(config["interval_minutes"]).minutes.do(
            run_task, name=name, config=config
        )
        # Run once immediately
        run_task(name, config)

    # Main loop
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
```

---

## Docker Compose (Lean)

```yaml
version: '3.8'

services:
  dragonfly-cache:
    image: docker.dragonflydb.io/dragonflydb/dragonfly:latest
    ports: ["6379:6379"]
    restart: unless-stopped

  localai:
    image: localai/localai:latest
    ports: ["8080:8080"]
    environment:
      - THREADS=10
    restart: unless-stopped

  unified-worker:
    build: ./daemon
    command: python unified_worker.py
    volumes:
      - ./daemon:/app
      - ~/.claude/memory:/root/.claude/memory
    environment:
      - LOCALAI_URL=http://localai:8080/v1
      - DRAGONFLY_URL=redis://dragonfly-cache:6379
    depends_on:
      - localai
      - dragonfly-cache
    restart: unless-stopped
```

---

## Cost Analysis

### Before (5 separate services)
- 5 Python processes × ~100MB = 500MB RAM
- 5 container overhead
- No coordination between tasks

### After (1 unified worker)
- 1 Python process ~150MB = 150MB RAM
- 1 container
- Coordinated scheduling

**Savings: 70% RAM, simpler ops**

---

## Migration Steps

1. [ ] Create `unified_worker.py` with scheduler
2. [ ] Add wrapper functions to each module
3. [ ] Update docker-compose to single worker
4. [ ] Test all tasks run on schedule
5. [ ] Remove old service definitions

---

## LLM Cost Routing

### Current Routing Policy

| Task Type | Provider | Cost |
|-----------|----------|------|
| Summarization | LocalAI | $0 |
| Embeddings | LocalAI | $0 |
| Simple extraction | LocalAI | $0 |
| Code generation | Codex (gpt-4o-mini) | $ |
| Complex reasoning | Claude | $$$ |

### Enforcement

```python
# In model_router.py - already implemented

def route(self, task: str, content: str) -> str:
    complexity = self.estimate_complexity(task, content)

    if complexity < 0.3:
        return self.call_localai(task, content)  # FREE
    elif complexity < 0.7:
        return self.call_codex(task, content)    # $
    else:
        return self.call_claude(task, content)   # $$$
```

---

*Build less, integrate more. Run one worker, not ten.*
