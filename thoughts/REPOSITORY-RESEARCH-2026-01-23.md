# Repository Research Analysis
**Date:** 2026-01-23
**Purpose:** Evaluate 50+ repos for book/PDF RAG, token efficiency, and emergent growth

---

## Priority Tier: LOCAL AI STACK (User's Top 3)

| Repo | Purpose | Token Impact | Integration |
|------|---------|--------------|-------------|
| **mudler/LocalAI** | Local LLM inference (GPT4All, LLaMA, etc.) | ⬇️ HUGE - offloads from Claude | Medium |
| **mudler/LocalAGI** | Agentic layer on LocalAI | ⬇️ HIGH - local agent execution | Medium |
| **mudler/LocalRecall** | Vector memory for LocalAI | ⬇️ HIGH - local RAG | Low |

**Combined Value:** Run research ingestion, summarization, and routine tasks locally → only escalate to Claude for complex reasoning. Could reduce Claude tokens by 70-90% for bulk work.

---

## Category 1: SEMANTIC RETRIEVAL / RAG

### Tier A (Best for Academic Papers + Low Token)

| Repo | Approach | Strengths | Weaknesses |
|------|----------|-----------|------------|
| **khoj-ai/khoj** | Self-hosted AI + RAG | Full-featured, local, actively maintained | Complex setup |
| **Future-House/paper-qa** | Academic paper focused | Section-aware chunking, citation handling | Papers only |
| **OpenBMB/UltraRAG** | Efficient RAG | Claims token efficiency | Less documented |
| **deepset-ai/haystack** | Pipeline framework | Production-ready, modular | Learning curve |
| **oraios/serena** | Semantic retrieval | Clean API | Smaller community |

### Tier B (Good Alternatives)

| Repo | Best For |
|------|----------|
| **jerryjliu/llama_index** | Flexible indexing (graph/tree/summary) |
| **Wildcard-Official/deepcontext-mcp** | MCP integration |
| **AIDotNet/AntSK** | Full-stack RAG platform |

### Tier C (Specialized)

| Repo | Niche |
|------|-------|
| **docling-project/docling** | PDF parsing (already using) |
| **nige-n15/AI-book-buddy** | Book-specific ingestion |
| **adithya-s-k/omniparse** | Multi-format parsing |

---

## Category 2: CONTEXT MANAGEMENT / TOKEN EFFICIENCY

| Repo | Mechanism | Value |
|------|-----------|-------|
| **DanielSuissa/claude-context-extender** | Smart chunking + retrieval | ⭐ HIGH |
| **webdevtodayjason/context-forge** | CLAUDE.md generation | MEDIUM |
| **Xnhyacinth/Awesome-LLM-Long-Context-Modeling** | Research compilation | REFERENCE |
| **slopus/happy** | Use Claude from anywhere | CONVENIENCE |

---

## Category 3: SKILLS / AGENTS

| Repo | Type | Integrate? |
|------|------|-----------|
| **wshobson/agents** | Lazy-load skills (only when activated) | ✅ YES - matches our architecture |
| **OneWave-AI/claude-skills** | Skill marketplace | EVALUATE |
| **vanzan01/claude-code-sub-agent-collective** | Multi-agent | EVALUATE |
| **oxygen-fragment/claude-modular** | Modular Claude | EVALUATE |
| **ComposioHQ/awesome-claude-skills** | Curated list | REFERENCE |
| **anthropics/skills** | Official Anthropic skills | ✅ REFERENCE |

---

## Category 4: KNOWLEDGE GRAPHS / MEMORY

| Repo | Approach | Value |
|------|----------|-------|
| **shaneholloman/mcp-knowledge-graph** | Local KG via MCP | ✅ Already using similar |
| **ballred/obsidian-claude-pkm** | Obsidian integration | FUTURE (personal knowledge) |
| **memvid/claude-brain** | Persistent without DB | EVALUATE |
| **bytebase/dbhub** | Database capabilities | FUTURE |
| **julien040/anyquery** | Universal query | EVALUATE |

---

## Category 5: SPECIALIZED DOMAINS

### Research / Academic
| Repo | Use |
|------|-----|
| **thunlp/RCPapers** | Reading comprehension papers |
| **zechenzhangAGI/AI-research-SKILLs** | Research skills |
| **sebastianruder/NLP-progress** | NLP tracking |

### Business / Profit Potential
| Repo | Opportunity |
|------|-------------|
| **TheCraigHewitt/seomachine** | SEO automation |
| **quant-sentiment-ai/claude-equity-research** | Finance analysis |
| **fracabu/claude-kdp-agents** | Book publishing |
| **pipeshub-ai/pipeshub-ai** | Business automation |
| **jamditis/claude-skills-journalism** | Content/PR |

### Vision / Advanced
| Repo | Capability |
|------|------------|
| **ultralytics/ultralytics** | Object detection |
| **roboflow/supervision** | Video analysis |
| **open-mmlab/mmdetection** | Detection framework |

---

## Category 6: ANTHROPIC OFFICIAL (Reference)

| Repo | Purpose |
|------|---------|
| **anthropics/claude-code-monitoring-guide** | Best practices |
| **anthropics/skills** | Official skill patterns |
| **anthropics/claude-cookbooks** | Examples |
| **anthropics/prompt-eng-interactive-tutorial** | Prompt engineering |
| **anthropics/anthropic-retrieval-demo** | RAG patterns |
| **anthropics/evals** | Evaluation methods |

---

## RECOMMENDED INTEGRATION ORDER

### Phase 1: Local AI Stack (IMMEDIATE)
```
1. LocalAI → Run local LLM for bulk processing
2. LocalRecall → Local vector store for books
3. Integrate with existing book_watcher.py
```
**Token savings:** 70-90% for ingestion/summarization

### Phase 2: Enhanced RAG (NEXT)
```
1. khoj-ai/khoj OR paper-qa → Better semantic retrieval
2. claude-context-extender → Smart chunking
3. Wire to controller.py for adaptive optimization
```
**Quality improvement:** Semantic search over books

### Phase 3: Lazy-Load Skills (FUTURE)
```
1. Adopt wshobson/agents pattern
2. Skills load only when triggered
3. Reduces baseline token overhead
```

### Phase 4: Knowledge Synthesis (FUTURE)
```
1. Obsidian integration for persistent graphs
2. Cross-book concept linking
3. Emergent pattern discovery
```

---

## KEY INSIGHT: The Emergent Growth Strategy

User's vision:
> "The issue I have is feeding you cutting edge research so that you can evolve and ascend. That's very token heavy. If I can find a way to do it locally, we will grow very quickly."

**Solution Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│  LOCAL LAYER (LocalAI + LocalRecall)                        │
│  • Ingest PDFs/books (bulk, cheap)                          │
│  • Generate summaries                                       │
│  • Extract concepts, formulas, methods                      │
│  • Store in vector DB                                       │
├─────────────────────────────────────────────────────────────┤
│  KNOWLEDGE LAYER (Knowledge Graph + Memory)                 │
│  • Link concepts across books                               │
│  • Track which methods/formulas are relevant                │
│  • Build "curriculum" of learnings                          │
├─────────────────────────────────────────────────────────────┤
│  CLAUDE LAYER (High-value reasoning only)                   │
│  • Receives distilled knowledge (not raw PDFs)              │
│  • Applies methods to specific problems                     │
│  • Makes architectural decisions                            │
│  • Handles complex multi-step reasoning                     │
└─────────────────────────────────────────────────────────────┘
```

**Result:** Claude gets the *insight* without the *token cost* of raw ingestion.

---

## NEXT ACTIONS

1. [ ] Wait for oracle agents to complete research
2. [ ] Decide: khoj vs paper-qa vs haystack for RAG
3. [ ] Set up LocalAI stack
4. [ ] Integrate with book_watcher.py
5. [ ] Test end-to-end: PDF → Local summary → Claude insight
