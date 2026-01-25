# Resource Trigger Map

*Automatic, seamless resource activation based on context*

---

## Principle

**Don't schedule. Trigger.**

Each module activates when its trigger condition is met - no commands needed.

---

## Trigger Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    EVENT BUS (Central)                       │
│  Watches: files, folders, DBs, APIs, messages, metrics      │
└─────────────────────────────┬───────────────────────────────┘
                              │
    ┌─────────────────────────┼─────────────────────────────┐
    ▼                         ▼                             ▼
┌────────┐              ┌────────┐                   ┌────────┐
│MONITORS│              │TRIGGERS│                   │MODULES │
│        │──event──────►│        │──activates───────►│        │
└────────┘              └────────┘                   └────────┘
```

---

## Resource Map with Automatic Triggers

### Ingestion Resources

| Resource | Trigger | Action |
|----------|---------|--------|
| `autonomous_ingest.py` | New file in GateofTruth/ | Extract, chunk, store |
| `utf_extractor.py` | PDF detected by ingest | Extract UTF schema |
| `claim_similarity.py` | New claim stored | Compare with existing |
| `kg_summary_worker.py` | KG entity count > threshold | Summarize cluster |

### Learning Resources

| Resource | Trigger | Action |
|----------|---------|--------|
| `outcome_tracker.py` | Task completed (success/fail) | Record outcome |
| `bisimulation.py` | Decision requested | Check similar past states |
| `gcrl.py` | Similar state found | Transfer learned policy |
| `self_improvement.py` | 10+ outcomes accumulated | Extract patterns |

### Strategy Resources

| Resource | Trigger | Action |
|----------|---------|--------|
| `strategy_evolution.py` | Strategy performance < threshold | Evolve variant |
| `strategy_ops.py` | New strategy created | Deploy to staging |
| `evolution_tracker.py` | Phase milestone reached | Sync planning docs |
| `coherence.py` | Action proposed | Check goal alignment |

### Routing Resources

| Resource | Trigger | Action |
|----------|---------|--------|
| `model_router.py` | LLM call requested | Route to cheapest capable |
| `local_autorouter.py` | Simple task detected | Route to LocalAI |
| `memory_router.py` | Query requested | Search all memory stores |

### Communication Resources

| Resource | Trigger | Action |
|----------|---------|--------|
| `telegram_notify.py` | Important event (error, completion) | Send notification |
| `email_trigger.py` | Email received (when configured) | Process and route |
| `email_sender.py` | Outbound email queued | Send via SMTP |

---

## Event-Driven Implementation

### Event Types

```python
class EventType(Enum):
    FILE_CREATED = "file.created"
    FILE_MODIFIED = "file.modified"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    DECISION_REQUESTED = "decision.requested"
    CLAIM_STORED = "claim.stored"
    THRESHOLD_EXCEEDED = "threshold.exceeded"
    PHASE_COMPLETED = "phase.completed"
    LLM_CALL_REQUESTED = "llm.call"
    ERROR_OCCURRED = "error"
```

### Trigger Registry

```python
TRIGGERS = {
    # File events
    EventType.FILE_CREATED: [
        {"pattern": "*.pdf", "handler": "autonomous_ingest.process_document"},
        {"pattern": "*.md", "handler": "autonomous_ingest.process_document"},
    ],

    # Task events
    EventType.TASK_COMPLETED: [
        {"handler": "outcome_tracker.record_success"},
        {"threshold": 10, "handler": "self_improvement.analyze"},
    ],
    EventType.TASK_FAILED: [
        {"handler": "outcome_tracker.record_failure"},
        {"handler": "telegram_notify.alert"},
    ],

    # Decision events
    EventType.DECISION_REQUESTED: [
        {"handler": "bisimulation.check_similar"},
        {"handler": "coherence.check_alignment"},
    ],

    # Learning events
    EventType.CLAIM_STORED: [
        {"handler": "claim_similarity.compare"},
    ],

    # Performance events
    EventType.THRESHOLD_EXCEEDED: [
        {"metric": "strategy_performance", "handler": "strategy_evolution.evolve"},
        {"metric": "kg_entity_count", "handler": "kg_summary_worker.summarize"},
    ],

    # Routing events
    EventType.LLM_CALL_REQUESTED: [
        {"handler": "model_router.route"},
    ],
}
```

---

## Seamless Integration Points

### 1. At Document Drop
```
User drops PDF in GateofTruth/
  → FILE_CREATED event fires
  → autonomous_ingest activates
    → MinerU extracts
    → utf_extractor creates schema
    → CLAIM_STORED events fire
      → claim_similarity compares
      → kg_summary updates if threshold
    → telegram_notify sends completion
```

### 2. At Task Completion
```
Claude finishes task
  → TASK_COMPLETED event fires
  → outcome_tracker records result
  → If 10+ outcomes:
    → self_improvement extracts patterns
    → strategy_evolution checks performance
      → If below threshold: evolve strategy
```

### 3. At Decision Point
```
User asks for recommendation
  → DECISION_REQUESTED event fires
  → bisimulation checks: "Have I seen this before?"
    → If yes: gcrl transfers policy
    → If no: decisions.py evaluates
  → coherence checks goal alignment
  → model_router selects LLM
    → complexity < 0.3: LocalAI ($0)
    → complexity < 0.7: Codex ($)
    → complexity >= 0.7: Claude ($$$)
```

### 4. At Error
```
Any module throws error
  → ERROR_OCCURRED event fires
  → telegram_notify sends alert
  → outcome_tracker records failure
  → task.md updates with blocker
```

---

## Event Bus Implementation

```python
# daemon/event_bus.py

from typing import Callable, Dict, List
from dataclasses import dataclass
import asyncio

@dataclass
class Event:
    type: str
    data: dict
    timestamp: float

class EventBus:
    _handlers: Dict[str, List[Callable]] = {}

    @classmethod
    def on(cls, event_type: str, handler: Callable):
        """Register handler for event type."""
        if event_type not in cls._handlers:
            cls._handlers[event_type] = []
        cls._handlers[event_type].append(handler)

    @classmethod
    async def emit(cls, event_type: str, data: dict = None):
        """Emit event to all registered handlers."""
        event = Event(type=event_type, data=data or {}, timestamp=time.time())

        for handler in cls._handlers.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                # Emit error event (but don't recurse infinitely)
                if event_type != "error":
                    await cls.emit("error", {"source": event_type, "error": str(e)})

# Register all triggers at startup
def register_all_triggers():
    from autonomous_ingest import process_document
    from outcome_tracker import record_outcome
    from bisimulation import check_similar
    # ... etc

    EventBus.on("file.created", process_document)
    EventBus.on("task.completed", record_outcome)
    EventBus.on("decision.requested", check_similar)
    # ... etc
```

---

## File Watcher Integration

```python
# daemon/file_watcher.py

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from event_bus import EventBus

class IngestHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            EventBus.emit("file.created", {
                "path": event.src_path,
                "extension": Path(event.src_path).suffix
            })

def start_watcher(folder: str):
    observer = Observer()
    observer.schedule(IngestHandler(), folder, recursive=True)
    observer.start()
```

---

## Current Gap vs Target

| Aspect | Current | Target |
|--------|---------|--------|
| Scheduling | Cron-like intervals | Event-driven triggers |
| Coordination | None (isolated services) | Event bus connects all |
| Response time | 5-300 second delay | Immediate on event |
| Resource usage | 5 always-on processes | 1 process, on-demand handlers |
| Awareness | Modules don't know each other | Modules publish/subscribe |

---

## Migration Path

1. [ ] Create `event_bus.py` with pub/sub
2. [ ] Add `@trigger` decorators to modules
3. [ ] Create `file_watcher.py` for folder monitoring
4. [ ] Register all handlers at startup
5. [ ] Replace cron loops with event subscriptions
6. [ ] Single `orchestrator.py` runs event loop

---

*The system should KNOW when to act, not be TOLD when to act.*
