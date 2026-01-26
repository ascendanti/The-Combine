# Integration Wiring Plan

## Principle: EXTEND, DON'T LAYER

All new capabilities wire INTO existing components, not on top of them.

---

## Existing Architecture Map

```
                           ┌─────────────────────────┐
                           │    unified_spine.py     │
                           │  (Backbone Coordinator) │
                           └───────────┬─────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         │                             │                             │
         ▼                             ▼                             ▼
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│  orchestrator.py │         │ memory_router.py │         │   emergent.py   │
│ (Central Brain)  │         │ (Unified Memory) │         │(Pattern/Learning)│
└────────┬────────┘         └────────┬────────┘         └────────┬────────┘
         │                           │                           │
         ▼                           ▼                           ▼
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│  model_router.py │         │    memory.py    │         │  coherence.db   │
│ (Route to LLMs)  │         │   (SQLite DB)   │         │  decisions.db   │
└─────────────────┘         └─────────────────┘         └─────────────────┘
```

---

## Integration Points for New Tools

### 1. Dragonfly Cache → Wire into `memory_router.py`

**Current**: `MemoryRouter` routes to daemon memory + knowledge-graph
**Add**: Dragonfly as L1 cache layer BEFORE hitting SQLite

```python
# memory_router.py enhancement
class MemoryRouter:
    def __init__(self):
        self._daemon_memory = Memory(backend="auto")
        self._kg_path = KNOWLEDGE_GRAPH_PATH
        self._cache = DragonflyCache()  # ADD THIS

    def search(self, query: str, k: int = 10):
        # Check cache first
        cached = self._cache.get(f"search:{query}")  # ADD THIS
        if cached:
            return cached

        # Existing search logic...
        results = self._search_daemon_and_kg(query, k)

        # Cache results
        self._cache.set(f"search:{query}", results, ttl=300)  # ADD THIS
        return results
```

**Wire point**: `daemon/memory_router.py:53` (in `__init__`)

---

### 2. MARM → Wire into `memory_router.py` as additional backend

**Current**: Two backends (daemon SQLite, knowledge-graph JSONL)
**Add**: MARM as third backend with semantic search

```python
# memory_router.py enhancement
class MemoryRouter:
    @property
    def active_backends(self) -> List[str]:
        backends = [f"daemon:{self._daemon_memory.backend_name}"]
        if self._kg_path.exists():
            backends.append("knowledge_graph")
        if self._marm_available:
            backends.append("marm")  # ADD THIS
        return backends

    def search(self, query: str, k: int = 10, sources: Optional[List[str]] = None):
        # Existing daemon + kg search...

        # Add MARM semantic search
        if "marm" in sources and self._marm_available:
            marm_results = self._marm_client.smart_recall(query, k)
            results.extend(marm_results)  # ADD THIS
```

**Wire point**: `daemon/memory_router.py:124` (in `search` method)

---

### 3. ELF Emergent Learning → Merge into `emergent.py`

**Current**: `emergent.py` has patterns, generated tasks, goal refinement, learning targets
**Add**: ELF's confidence scoring and golden rule promotion

```python
# emergent.py enhancement - ADD to Pattern dataclass
@dataclass
class Pattern:
    pattern_id: str
    pattern_type: str
    description: str
    frequency: int
    confidence: float
    first_seen: str
    last_seen: str
    suggested_action: Optional[str] = None
    is_golden_rule: bool = False  # ADD: ELF concept
    validation_count: int = 0      # ADD: ELF concept
    violation_count: int = 0       # ADD: ELF concept

# ADD: Golden rule promotion logic
def maybe_promote_to_golden(pattern: Pattern) -> bool:
    """ELF-style: Promote high-confidence patterns to golden rules."""
    if pattern.confidence >= 0.8 and pattern.validation_count >= 5:
        pattern.is_golden_rule = True
        return True
    return False
```

**Wire point**: `daemon/emergent.py:37` (Pattern dataclass)

---

### 4. Swarms → Wire into `orchestrator.py` as swarm router

**Current**: `Orchestrator` has `fast_classify()` and routes to agent/skill/localai/codex/claude
**Add**: Swarm patterns for multi-agent tasks

```python
# orchestrator.py enhancement
class Orchestrator:
    def __init__(self, config: OrchestratorConfig = None):
        self.config = config or OrchestratorConfig()
        self.router = ModelRouter()
        self.cascade = CascadeRouter(self.router) if self.config.cascade_enabled else None
        self.swarm_router = None  # ADD THIS

        # Initialize swarms if available
        try:
            from swarms import SwarmRouter
            self.swarm_router = SwarmRouter()  # ADD THIS
        except ImportError:
            pass

    def process(self, task: str, content: str = "", context: Dict = None):
        classification = fast_classify(task)

        # ADD: Route complex multi-step tasks to swarm
        if classification["complexity"] >= 8 and self.swarm_router:
            return self._process_with_swarm(task, classification)

        # Existing logic...
```

**Wire point**: `daemon/orchestrator.py:199` (in `__init__`)

---

### 5. GraphBrain → Wire into knowledge graph operations

**Current**: `memory_router.py` stores entities/relations in JSONL
**Add**: GraphBrain semantic hypergraph for richer relationships

```python
# memory_router.py enhancement
class MemoryRouter:
    def __init__(self):
        # ... existing ...
        self._graphbrain = None
        try:
            import graphbrain
            self._graphbrain = graphbrain.hgraph()  # ADD THIS
        except ImportError:
            pass

    def _store_relation(self, from_entity: str, to_entity: str, relation_type: str):
        # Existing JSONL storage...

        # ADD: Store in GraphBrain hypergraph for semantic reasoning
        if self._graphbrain:
            edge = self._graphbrain.add((from_entity, relation_type, to_entity))
```

**Wire point**: `daemon/memory_router.py:207` (in `_store_relation`)

---

### 6. Context Router (HOT/WARM/COLD) → Wire into hooks system

**Current**: `auto-cache-pre.py` runs on Read/Grep/Glob
**Add**: Tiered context injection based on relevance scores

```python
# .claude/hooks/auto-cache-pre.py enhancement
def route_context(file_path: str, context_scores: Dict[str, float]):
    """Route context based on HOT/WARM/COLD tiers."""
    score = context_scores.get(file_path, 0.5)

    if score > 0.8:  # HOT - full content
        return {"mode": "full", "content": read_file(file_path)}
    elif score > 0.25:  # WARM - headers only
        return {"mode": "headers", "content": read_headers(file_path)}
    else:  # COLD - evicted
        return {"mode": "reference", "content": f"[File: {file_path}]"}
```

**Wire point**: `.claude/hooks/auto-cache-pre.py`

---

### 7. claude-flow Workers → Wire into `unified_spine.py`

**Current**: `unified_spine.py` runs cycles with handoff resume
**Add**: Background workers from claude-flow

```python
# unified_spine.py enhancement
class UnifiedSpine:
    def __init__(self):
        # ... existing ...
        self.workers = []  # ADD THIS
        self._init_background_workers()

    def _init_background_workers(self):
        """Initialize claude-flow style background workers."""
        worker_configs = [
            {"name": "ultralearn", "interval": 300},
            {"name": "consolidate", "interval": 600},
            {"name": "optimize", "interval": 900},
        ]
        for config in worker_configs:
            self.workers.append(BackgroundWorker(**config))
```

**Wire point**: `daemon/unified_spine.py:75` (in `__init__`)

---

## Wiring Summary Table

| New Tool | Wires Into | File | Line/Method |
|----------|-----------|------|-------------|
| **Dragonfly** | L1 cache layer | `memory_router.py` | `__init__`, `search` |
| **MARM** | Backend #3 | `memory_router.py` | `active_backends`, `search` |
| **ELF** | Pattern confidence | `emergent.py` | `Pattern`, `store_pattern` |
| **Swarms** | Complex task router | `orchestrator.py` | `__init__`, `process` |
| **GraphBrain** | Semantic relations | `memory_router.py` | `_store_relation` |
| **Context Router** | Pre-tool injection | `auto-cache-pre.py` | hook handler |
| **claude-flow** | Background workers | `unified_spine.py` | `__init__` |

---

## What NOT To Do

❌ Create new `marm_memory.py` alongside existing `memory_router.py`
❌ Create new `swarm_orchestrator.py` alongside existing `orchestrator.py`
❌ Create new `elf_learning.py` alongside existing `emergent.py`
❌ Add new hooks that duplicate existing hook functionality

✅ Extend existing classes with new backends/methods
✅ Add imports to existing files
✅ Use dependency injection to add capabilities
✅ Keep single source of truth for each function
