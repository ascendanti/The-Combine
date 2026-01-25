# Efficiency Stack - Priority Deployments

*Focus: Memory, Tokens, Speed, Architecture*

---

## Filter Criteria

Only tools that directly improve:
- **Memory** - Better knowledge retention/retrieval
- **Tokens** - Reduce context usage
- **Speed** - Faster processing
- **Architecture** - Better system design

---

## Tier 1: Deploy Immediately

### 1. MinerU ⭐⭐⭐⭐⭐
**URL:** https://github.com/opendatalab/MinerU
**Impact:** MEMORY + TOKENS

| Improvement | Mechanism |
|-------------|-----------|
| Better PDF extraction | Structured data vs raw text |
| Cleaner chunks | Less noise in RAG retrieval |
| Table/figure handling | Preserve semantic structure |

**Token Savings:** 30-50% (cleaner extraction = less garbage)

**Deploy:**
```bash
pip install mineru
# Replace autonomous_ingest.py PDF handling
```

---

### 2. markitdown ⭐⭐⭐⭐⭐
**URL:** https://github.com/microsoft/markitdown
**Impact:** TOKENS + SPEED

| Improvement | Mechanism |
|-------------|-----------|
| Standardized format | All docs → markdown |
| Consistent parsing | No format-specific code |
| Better chunking | Markdown structure preserved |

**Token Savings:** 20-30% (consistent format = predictable chunking)

**Deploy:**
```bash
pip install markitdown
# Pre-process all documents before RAG
```

---

### 3. ragflow ⭐⭐⭐⭐⭐
**URL:** https://github.com/infiniflow/ragflow
**Impact:** MEMORY + TOKENS + SPEED

| Improvement | Mechanism |
|-------------|-----------|
| Deep document understanding | Better semantic chunking |
| Multi-modal RAG | Images, tables, text together |
| Hybrid search | BM25 + vector = better recall |
| Caching | Repeated queries are instant |

**Token Savings:** 40-60% (better retrieval = less context stuffing)

**Architecture Change:**
```
Current: Read file → dump to context → hope Claude finds it
New: Query ragflow → get precisely relevant chunks → minimal context
```

**Deploy:**
```bash
docker pull infiniflow/ragflow
# Replace UTF pipeline with ragflow
```

---

### 4. khoj ⭐⭐⭐⭐
**URL:** https://github.com/khoj-ai/khoj
**Impact:** MEMORY + SPEED

| Improvement | Mechanism |
|-------------|-----------|
| Unified search | One interface for all data |
| Incremental indexing | Only re-index changes |
| Semantic search | Find by meaning, not keywords |
| Chat interface | Natural language queries |

**Speed Improvement:** 10x faster than grep-based search

**Deploy:**
```bash
docker pull khoj/khoj
# Point at knowledge directories
```

---

### 5. Smithery MCP Tools ⭐⭐⭐⭐
**URL:** https://github.com/smithery-ai/mcp-servers
**Impact:** ARCHITECTURE

| Improvement | Mechanism |
|-------------|-----------|
| Pre-built MCP servers | Don't reinvent wheels |
| Standardized interfaces | Consistent tool patterns |
| Community maintained | Bug fixes, improvements |

**Deploy:**
```bash
npx @anthropic-ai/mcp-manager install @smithery/mcp-*
```

---

## Tier 2: High Impact

### 6. dashy ⭐⭐⭐
**URL:** https://github.com/Lissy93/dashy
**Impact:** SPEED (human efficiency)

| Improvement | Mechanism |
|-------------|-----------|
| Single pane of glass | All services in one view |
| Health monitoring | Know when things break |
| Quick access | Reduce context switching |

---

### 7. novu ⭐⭐⭐
**URL:** https://github.com/novuhq/novu
**Impact:** ARCHITECTURE

| Improvement | Mechanism |
|-------------|-----------|
| Unified notifications | One API for all channels |
| Template management | Don't rebuild notification logic |
| Delivery tracking | Know what got delivered |

---

## Integration Order (Efficiency Focus)

```
Week 1: Document Pipeline
├── Deploy markitdown (standardize inputs)
├── Deploy MinerU (better PDF extraction)
└── Integrate with autonomous_ingest.py

Week 2: Knowledge System
├── Deploy ragflow (replace UTF RAG)
├── Migrate existing knowledge
└── Update hooks to use ragflow API

Week 3: Search & Access
├── Deploy khoj (unified search)
├── Index all data sources
└── Create search MCP server

Week 4: Operations
├── Deploy dashy (operations dashboard)
├── Add health checks
└── Deploy novu (notifications)
```

---

## Token Savings Projection

| Current System | Tokens/Day | After Optimization |
|----------------|------------|-------------------|
| File reads (full) | ~50K | ~15K (smart chunking) |
| RAG retrieval | ~30K | ~10K (better relevance) |
| Search results | ~20K | ~5K (semantic search) |
| **Total** | **~100K** | **~30K** |

**Projected Savings: 70%**

---

## Architecture Evolution

### Current (Inefficient)
```
User query
    → Grep/Glob for files
    → Read entire files
    → Dump to context
    → Claude processes
    → Often misses relevant info
```

### Target (Efficient)
```
User query
    → ragflow semantic search
    → Returns precise chunks
    → Minimal context (relevant only)
    → Claude processes
    → High accuracy
```

---

## Quick Wins (Today)

### 1. Add markitdown pre-processing
```python
# In autonomous_ingest.py
from markitdown import MarkItDown

def preprocess(file_path):
    md = MarkItDown()
    result = md.convert(file_path)
    return result.text_content
```

### 2. Use MinerU for PDFs
```python
from mineru import PDFParser

def extract_pdf(path):
    parser = PDFParser()
    return parser.parse(path)  # Structured extraction
```

### 3. Add ragflow for queries
```python
import requests

def semantic_search(query, top_k=5):
    response = requests.post(
        "http://ragflow:9380/api/search",
        json={"query": query, "top_k": top_k}
    )
    return response.json()["chunks"]
```

---

## Skip for Now

These don't directly improve efficiency:
- CRM tools (Twenty already selected)
- Sales automation (business, not efficiency)
- Content tools (strapi, etc.)
- Home automation (gladys, grocy)

Focus on the knowledge/document pipeline first.

---

*Efficiency > Features. Fix the foundation before adding capabilities.*
*Generated: 2026-01-25*
