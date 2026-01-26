# Unified Memory & Context Architecture

## Executive Summary

This document proposes a unified architecture combining the best elements from 15+ evaluated memory/context solutions to create a comprehensive, token-efficient, emergent learning system for Claude Code.

## Evaluated Solutions

| Solution | Strength | Adopt |
|----------|----------|-------|
| **claude-cognitive** | 64-95% token reduction via HOT/WARM/COLD tiers | YES - Core |
| **ELF (Emergent Learning)** | Confidence-weighted heuristics that emerge from usage | YES - Core |
| **MARM-Systems** | Universal MCP memory with 18 tools, cross-platform | YES - Core |
| **Linggen** | Design anchors + system graph + LanceDB vectors | YES - Partial |
| **OpenMemory** | 5-sector cognitive memory (episodic/semantic/procedural) | YES - Concepts |
| **claude-flow** | Background workers, swarm coordination, 175+ MCP tools | YES - Orchestration |
| **Continuous-Claude-v3** | "Compound don't compact", structured handoffs | YES - Continuity |
| **mcp-code-execution** | Zero-context MCP via discovery pattern | YES - Token savings |
| **mcp-knowledge-graph** | Entity-relation graph with deduplication | Merge with MARM |
| **cherry-studio** | Fact extraction prompts, hash-based dedup | Extract prompts |
| **claude-mem** | Progressive disclosure (10x token savings) | Extract pattern |
| **unicontext** | Provider-agnostic memory SDK | Future bridge |
| **UniversalLLMFunctionCaller** | Universal function calling | YES - Integration |
| **Swarms (kyegomez)** | Enterprise multi-agent orchestration, 10+ swarm patterns | YES - Orchestration |
| **GraphBrain** | Semantic hypergraph for knowledge representation | YES - Knowledge Layer |
| **kernel-claude** | 13 agents, self-evolution, tiered processing | YES - Core Kernel |
| **academic-paper-skills** | Research and writing enhancement | YES - Research |

---

## Proposed Architecture

### High-Level System Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           SWARM ORCHESTRATION LAYER                          │
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐     │
│  │  Swarms (kyegomez) │  │    claude-flow     │  │   kernel-claude    │     │
│  │  10+ patterns      │  │  Queen + Workers   │  │  13 agents + meta  │     │
│  │  Multi-provider    │  │  175+ MCP tools    │  │  Self-evolution    │     │
│  └─────────┬──────────┘  └─────────┬──────────┘  └─────────┬──────────┘     │
│            └───────────────────────┼───────────────────────┘                 │
└────────────────────────────────────┼─────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼─────────────────────────────────────────┐
│                           KNOWLEDGE & MEMORY LAYER                           │
│  ┌────────────────────┐  ┌────────┴───────────┐  ┌────────────────────┐     │
│  │    GraphBrain      │  │   Unified Memory   │  │      MARM          │     │
│  │  Semantic Hypergraph│  │       Hub          │  │  18 MCP tools      │     │
│  │  Meaning extraction │  │  Dragonfly+SQLite  │  │  Cross-platform    │     │
│  └─────────┬──────────┘  └─────────┬──────────┘  └─────────┬──────────┘     │
│            └───────────────────────┼───────────────────────┘                 │
└────────────────────────────────────┼─────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼─────────────────────────────────────────┐
│                           CONTEXT & TOKEN OPTIMIZATION                       │
│  ┌────────────────────┐  ┌────────┴───────────┐  ┌────────────────────┐     │
│  │  Context Router    │  │  Zero-Context MCP  │  │  Progressive       │     │
│  │  HOT/WARM/COLD     │  │  30K→200 tokens    │  │  Disclosure        │     │
│  │  64-95% savings    │  │  Discovery pattern │  │  10x savings       │     │
│  └────────────────────┘  └────────────────────┘  └────────────────────┘     │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼─────────────────────────────────────────┐
│                           LEARNING & CONTINUITY                              │
│  ┌────────────────────┐  ┌────────┴───────────┐  ┌────────────────────┐     │
│  │  ELF Emergent      │  │  Structured        │  │  Background        │     │
│  │  Learning          │  │  Handoffs          │  │  Workers           │     │
│  │  Confidence-based  │  │  YAML + TLDR       │  │  12 workers        │     │
│  └────────────────────┘  └────────────────────┘  └────────────────────┘     │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLAUDE CODE SESSION                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │ Context Router  │  │  ELF Emergent   │  │   MARM Smart    │     │
│  │ (HOT/WARM/COLD) │  │   Learning      │  │     Recall      │     │
│  │ 64-95% savings  │  │   Heuristics    │  │   18 MCP tools  │     │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘     │
│           │                    │                    │               │
│           └────────────────────┼────────────────────┘               │
│                                │                                    │
│                    ┌───────────▼───────────┐                        │
│                    │   UNIFIED MEMORY HUB  │                        │
│                    │  (Dragonfly + SQLite) │                        │
│                    └───────────┬───────────┘                        │
│                                │                                    │
│  ┌─────────────────────────────┼─────────────────────────────────┐  │
│  │                  MEMORY LAYERS                                 │  │
│  │                                                                │  │
│  │  L1: Session Cache    │ Dragonfly (Redis)  │ <100ms │ volatile │  │
│  │  L2: Working Memory   │ SQLite + FTS5      │ <10ms  │ session  │  │
│  │  L3: Episodic Memory  │ SQLite + vectors   │ <50ms  │ project  │  │
│  │  L4: Semantic Memory  │ LanceDB/FAISS      │ <100ms │ global   │  │
│  │  L5: Heuristic Memory │ ELF confidence DB  │ <20ms  │ emergent │  │
│  │                                                                │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                  BACKGROUND WORKERS (claude-flow)               ││
│  │  ultralearn│optimize│consolidate│predict│audit│map│preload     ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                  CONTINUITY SYSTEM (Continuous-Claude-v3)       ││
│  │  Structured Handoffs │ TLDR Layers │ Auto-Extraction │ Ledgers  ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Core Memory (Week 1)

**1.1 Context Router (from claude-cognitive)**
- HOT tier (score >0.8): Full content
- WARM tier (0.25-0.8): Headers only
- COLD tier (<0.25): Evicted
- Decay: 0.85 multiplier per turn
- Co-activation for related docs

**1.2 Dragonfly Integration**
- ✅ MCP server created: `daemon/dragonfly_mcp_server.py`
- Context offloading for token reduction
- Semantic cache for repeated queries
- Session state persistence

**1.3 MARM Smart Recall**
- Install: `pip install marm-mcp-server`
- 18 MCP tools for memory operations
- Auto-classification with embeddings

### Phase 2: Emergent Learning (Week 2)

**2.1 ELF Integration**
- Heuristics table with confidence scores
- [LEARNED:] marker extraction
- Golden rule promotion (confidence >= 0.8)
- Pheromone trails for file hotspots

**2.2 Learning Loop**
```
QUERY   ->  Check heuristics for patterns
APPLY   ->  Use in task execution
RECORD  ->  Capture success/failure
PERSIST ->  Update confidence scores
```

### Phase 3: Continuous Operation (Week 3)

**3.1 claude-flow Workers**
- 12 background workers for continuous processing
- Swarm coordination with Queen orchestrator
- 175+ MCP tools

**3.2 Structured Handoffs**
- YAML state transfer on compaction
- 5-layer TLDR system (~95% savings)
- Auto-extraction before context fills

### Phase 4: Advanced Memory (Week 4)

**4.1 Zero-Context MCP Pattern**
- Single `run_python` tool for discovery
- Dynamic tool lookup vs. preloaded schemas
- 30K -> 200 tokens overhead

**4.2 Semantic Indexing**
- LanceDB for vector storage
- FAISS for fast retrieval
- BGE-large embeddings

---

## File Structure

```
.claude/
├── memory/
│   ├── heuristics.db       # ELF confidence-weighted rules
│   ├── learnings.db        # Success/failure records
│   ├── sessions.db         # Session state
│   └── vectors.lance       # LanceDB embeddings
├── context/
│   ├── hot/                # Full content injection
│   ├── warm/               # Headers only
│   └── cold/               # Evicted (reference only)
├── handoffs/
│   ├── latest.yaml         # Current state
│   └── archive/            # Historical handoffs
└── workers/
    └── state.json          # Background worker state

daemon/
├── dragonfly_mcp_server.py # ✅ Created
├── marm_bridge.py          # MARM integration
├── elf_daemon.py           # Emergent learning
└── context_router.py       # HOT/WARM/COLD routing
```

---

## MCP Server Configuration

Update `.mcp.json`:

```json
{
  "mcpServers": {
    "dragonfly-cache": {
      "command": "python",
      "args": ["daemon/dragonfly_mcp_server.py"],
      "env": {"DRAGONFLY_HOST": "localhost", "DRAGONFLY_PORT": "6379"}
    },
    "marm-memory": {
      "command": "uvx",
      "args": ["marm-mcp-server"],
      "env": {"MARM_DATA_DIR": "~/.marm"}
    },
    "code-execution": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/elusznik/mcp-server-code-execution-mode", "mcp-server-code-execution-mode", "run"]
    }
  }
}
```

---

## Token Savings Projection

| Component | Savings | Mechanism |
|-----------|---------|-----------|
| Context Router | 64-95% | HOT/WARM/COLD tiering |
| Dragonfly Offload | 50-80% | Large context caching |
| Zero-Context MCP | 99% | 30K -> 200 tokens |
| Progressive Disclosure | 90% | Index first, detail on demand |
| TLDR Layers | 95% | AST -> Call Graph -> CFG |
| **Combined** | **85-95%** | Multiplicative benefits |

---

## Swarm Orchestration Details

### Swarms (kyegomez) Patterns
| Pattern | Use Case |
|---------|----------|
| **SequentialWorkflow** | Step-by-step pipelines |
| **ConcurrentWorkflow** | High-throughput parallel |
| **AgentRearrange** | Dynamic `a -> a1, a2, a3` |
| **GraphWorkflow** | DAG-based dependencies |
| **MixtureOfAgents** | Expert ensemble + aggregator |
| **HierarchicalSwarm** | Director-worker patterns |
| **SwarmRouter** | Universal interface |

### GraphBrain Integration
- **Semantic Hypergraph**: Represents knowledge as recursive hyperlinks
- **Hybrid AI**: Combines symbolic + statistical/ML methods
- **Use Cases**: Conflict network extraction, claim analysis, structured reasoning
- **Value**: Superior to flat triples for complex relationship modeling

---

## Pending Integrations (Queued)

```json
{
  "high_priority": [
    {"url": "https://github.com/Metaculus/forecasting-tools", "purpose": "Strategy module forecasting"},
    {"url": "https://github.com/dzhng/deep-research", "purpose": "Research enhancement"},
    {"url": "https://github.com/Jenscaasen/UniversalLLMFunctionCaller", "purpose": "Universal function calling"},
    {"url": "https://github.com/aannoo/hcom", "purpose": "Realtime messaging for agents"},
    {"url": "https://github.com/lishix520/academic-paper-skills", "purpose": "Research & writing"}
  ],
  "medium_priority": [
    {"url": "https://github.com/inngest/inngest", "purpose": "Event-driven orchestration"},
    {"url": "https://github.com/frankbria/ralph-claude-code", "purpose": "Intelligent exit detection"},
    {"url": "https://github.com/ccplugins/marketplace", "purpose": "Plugin ecosystem"},
    {"url": "https://github.com/flyinweb/pg-dev-claude-code", "purpose": "PostgreSQL dev kernel"}
  ],
  "low_priority": [
    {"url": "https://github.com/clj-commons/manifold", "purpose": "Async patterns (Clojure)"},
    {"url": "https://github.com/ariaxhan/kernel-claude", "purpose": "Alternative kernel (if needed)"}
  ]
}
```

---

## Recommended Next Steps

1. **Immediate**: Test Dragonfly MCP server
2. **This Week**: Install MARM (`pip install marm-mcp-server`)
3. **This Week**: Port Context Router from claude-cognitive
4. **Next Week**: Integrate ELF learning loop
5. **Next Week**: Set up claude-flow background workers
6. **Following**: Structured handoffs from Continuous-Claude-v3

---

## Replacing FewWord

FewWord issues identified:
- Unreliable context loading
- No emergent learning
- Limited token optimization

**Replacement Stack**:
1. **Dragonfly** for fast caching (replaces scratch storage)
2. **MARM** for structured memory (replaces manual offloading)
3. **ELF** for learning (adds emergent patterns)
4. **Context Router** for token optimization (better than manual)

This combination provides all FewWord capabilities plus:
- 64-95% token reduction
- Emergent learning from usage
- Cross-session persistence
- Team coordination (Pool system)
