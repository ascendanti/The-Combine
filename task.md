# Current Task Plan

## Objective
Evolve Claude instance with autonomous async daemon capabilities + adaptive learning architecture.

## Status: Phase 10 - Ascension 🔄 IN PROGRESS (85%)

## Completed This Session (2026-01-23)

### Book Ingestion Pipeline ✅
- [x] `book-ingest.py` - Hierarchical RAG for technical documents
  - Smart chunking preserving formulas/concepts
  - Multi-level summarization (paragraph → section → chapter → book)
  - Concept extraction with relationship mapping
  - Knowledge graph integration
- [x] `book-query.py` - Query interface for ingested books
- [x] `book_watcher.py` - File system watcher daemon
  - Watchdog-based monitoring
  - Background processing queue
  - Deduplication via file hashing
  - Memory system integration

### MAPE Controller Foundation ✅
- [x] `daemon/controller.py` - Adaptive control system
  - Monitor-Analyze-Plan-Execute cycle
  - Metric tracking and trending
  - Gap analysis (actual vs target)
  - Action planning with predicted outcomes
  - Confucius-style strategy introspection
  - Feedback loop for learning

### Hook Cleanup ✅
- [x] Consolidated SessionStart hooks into `session-start-clean.py`

## Phase 11 Planning (Approved Stack)

Based on research synthesis - integrating:
1. **claude-context-extender** - Semantic chunking + retrieval
2. **Confucius pattern** - Tool/strategy introspection
3. **MAPE control loop** - Adaptive optimization

### Next Actions
1. [ ] Clone claude-context-extender, integrate with book pipeline
2. [ ] Wire controller.py to book-ingest.py for adaptive chunking
3. [ ] Add comprehension metrics (semantic coherence scoring)
4. [ ] Create feedback integration with daemon/decisions.py

## Book Watch Folder
```
~/Documents/Claude-Books/
```
Drop PDFs here → auto-ingested → queryable via `book-query.py`

## Quick Commands

```bash
# Start book watcher daemon
python daemon/book_watcher.py

# Manually ingest a book
python .claude/scripts/book-ingest.py "path/to/book.pdf"

# Query books
python .claude/scripts/book-query.py "gradient descent"
python .claude/scripts/book-query.py --summary <book_id>
python .claude/scripts/book-query.py --concepts

# Run MAPE controller cycle
python daemon/controller.py --cycle
python daemon/controller.py --status

# Check watcher status
python daemon/book_watcher.py --status
python daemon/book_watcher.py --list-books
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  FILE WATCHER (book_watcher.py)                             │
│  Monitors ~/Documents/Claude-Books/ for new PDFs            │
├─────────────────────────────────────────────────────────────┤
│  BOOK INGEST PIPELINE (book-ingest.py)                      │
│  Docling → Chunking → Summaries → Concepts → KG             │
├─────────────────────────────────────────────────────────────┤
│  MAPE CONTROLLER (controller.py)                            │
│  Monitor metrics → Analyze gaps → Plan actions → Execute    │
├─────────────────────────────────────────────────────────────┤
│  STORAGE LAYER                                              │
│  • books.db (chunks, summaries, concepts)                   │
│  • knowledge-graph.jsonl (entities, relations)              │
│  • daemon/memory.py (learnings, decisions)                  │
├─────────────────────────────────────────────────────────────┤
│  QUERY INTERFACE (book-query.py)                            │
│  FTS search → Semantic retrieval → Concept lookup           │
└─────────────────────────────────────────────────────────────┘
```

## Dependencies to Install

```bash
# Required
pip install watchdog docling

# Already installed
# token-optimizer-mcp, dragonfly (docker), sqlite3
```
