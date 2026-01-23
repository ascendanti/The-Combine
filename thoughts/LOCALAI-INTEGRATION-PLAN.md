# LocalAI Stack Integration Plan

**Goal:** Offload bulk processing (book ingestion, summarization, routine tasks) to local LLMs → reduce Claude token usage by 70-90%

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER DROPS PDF                               │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BOOK WATCHER (daemon/book_watcher.py)                              │
│  Detects new files → queues for processing                          │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  DOCLING (PDF → Markdown)                                           │
│  Layout, tables, formulas extraction                                │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LOCAL PROCESSING LAYER (NEW)                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │  LocalAI    │    │ LocalRecall │    │  LocalAGI   │             │
│  │  (LLM API)  │◄──►│ (Vector DB) │◄──►│  (Agents)   │             │
│  └─────────────┘    └─────────────┘    └─────────────┘             │
│        │                   │                  │                     │
│        ▼                   ▼                  ▼                     │
│  • Summarization    • Chunk storage     • Concept extraction       │
│  • Q&A on chunks    • Semantic search   • Formula parsing          │
│  • Translation      • Embedding gen     • Relationship mapping     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  KNOWLEDGE LAYER                                                    │
├─────────────────────────────────────────────────────────────────────┤
│  • books.db (chunks, summaries, concepts)                           │
│  • knowledge-graph.jsonl (entities, relations)                      │
│  • daemon/memory.py (learnings)                                     │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  CLAUDE LAYER (High-value only)                                     │
├─────────────────────────────────────────────────────────────────────┤
│  Receives:                                                          │
│  • Distilled summaries (not raw text)                               │
│  • Extracted concepts + formulas                                    │
│  • Semantic search results (top-k chunks)                           │
│                                                                     │
│  Does:                                                              │
│  • Complex reasoning                                                │
│  • Architecture decisions                                           │
│  • Novel problem solving                                            │
│  • Multi-step planning                                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. LocalAI
**Repo:** https://github.com/mudler/LocalAI
**Purpose:** OpenAI-compatible API for local LLMs

**Installation:**
```bash
# Docker (recommended)
docker run -p 8080:8080 --name localai -v $PWD/models:/models localai/localai

# Or with GPU
docker run --gpus all -p 8080:8080 localai/localai:latest-cublas-cuda12
```

**Models to use:**
| Task | Model | Size | Quality |
|------|-------|------|---------|
| Summarization | Mistral-7B-Instruct | 4GB | Good |
| Embeddings | all-MiniLM-L6-v2 | 80MB | Fast |
| Complex reasoning | Mixtral-8x7B | 26GB | Excellent |
| Code | CodeLlama-7B | 4GB | Good |

**API (OpenAI-compatible):**
```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="mistral-7b-instruct",
    messages=[{"role": "user", "content": "Summarize this chapter..."}]
)
```

### 2. LocalRecall
**Repo:** https://github.com/mudler/LocalRecall
**Purpose:** Vector memory store for LocalAI

**Features:**
- Semantic search over documents
- Persistent memory across sessions
- Integrates directly with LocalAI

**Usage:**
```python
from localrecall import Memory

mem = Memory(
    localai_url="http://localhost:8080",
    embedding_model="all-MiniLM-L6-v2"
)

# Store chunks
mem.add("chunk content here", metadata={"book_id": "xyz", "page": 42})

# Recall
results = mem.search("gradient descent optimization", k=5)
```

### 3. LocalAGI
**Repo:** https://github.com/mudler/LocalAGI
**Purpose:** Agentic capabilities on top of LocalAI

**Features:**
- Function calling
- Tool use
- Multi-step reasoning
- Memory integration

---

## Integration with Our Pipeline

### Modified book_watcher.py flow:

```python
# Current: book_watcher → book-ingest → Claude (expensive)
# New:     book_watcher → book-ingest → LocalAI (cheap) → Claude (summaries only)

class LocalAIProcessor:
    def __init__(self):
        self.client = openai.OpenAI(
            base_url="http://localhost:8080/v1",
            api_key="not-needed"
        )
        self.recall = LocalRecall(...)

    def process_chunk(self, chunk: str) -> dict:
        """Local summarization + embedding."""
        # Generate summary locally
        summary = self.client.chat.completions.create(
            model="mistral-7b-instruct",
            messages=[{
                "role": "user",
                "content": f"Summarize this section in 2-3 sentences. Extract key concepts and any formulas:\n\n{chunk}"
            }]
        ).choices[0].message.content

        # Store in local vector DB
        self.recall.add(chunk, metadata={"summary": summary})

        return {"chunk": chunk, "summary": summary}

    def query(self, question: str) -> str:
        """Semantic search + local answer."""
        # Get relevant chunks
        results = self.recall.search(question, k=5)

        # Generate answer locally
        context = "\n\n".join([r.content for r in results])
        answer = self.client.chat.completions.create(
            model="mistral-7b-instruct",
            messages=[{
                "role": "user",
                "content": f"Based on this context:\n{context}\n\nAnswer: {question}"
            }]
        ).choices[0].message.content

        return answer
```

### When to escalate to Claude:

```python
def should_escalate_to_claude(task: str, local_confidence: float) -> bool:
    """Decide if task needs Claude's capabilities."""

    # Always escalate
    escalation_triggers = [
        "architectural decision",
        "multi-step planning",
        "novel problem",
        "code generation",
        "complex debugging"
    ]

    if any(trigger in task.lower() for trigger in escalation_triggers):
        return True

    # Escalate if local model is uncertain
    if local_confidence < 0.7:
        return True

    return False
```

---

## Docker Compose Addition

Add to existing `docker-compose.yaml`:

```yaml
services:
  # ... existing dragonfly service ...

  localai:
    image: localai/localai:latest-cublas-cuda12  # or :latest for CPU
    ports:
      - "8080:8080"
    volumes:
      - ./models:/models
      - localai-data:/data
    environment:
      - MODELS_PATH=/models
      - DEBUG=true
    restart: unless-stopped

  localrecall:
    image: mudler/localrecall:latest
    ports:
      - "8081:8081"
    volumes:
      - localrecall-data:/data
    environment:
      - LOCALAI_URL=http://localai:8080
    depends_on:
      - localai
    restart: unless-stopped

volumes:
  localai-data:
  localrecall-data:
```

---

## Token Savings Estimate

| Task | Without LocalAI | With LocalAI | Savings |
|------|-----------------|--------------|---------|
| Ingest 50-page PDF | ~100K tokens | ~5K tokens (summaries) | 95% |
| Query book content | ~10K tokens/query | ~500 tokens/query | 95% |
| Research synthesis | ~50K tokens | ~8K tokens | 84% |
| Routine Q&A | ~2K tokens | 0 tokens (local) | 100% |

**Overall estimated savings: 70-90%**

---

## Implementation Steps

### Step 1: Install LocalAI
```bash
# Create models directory
mkdir -p models

# Pull LocalAI
docker pull localai/localai:latest

# Download models
# Option A: Use built-in model gallery
# Option B: Download manually from HuggingFace
```

### Step 2: Create local_processor.py
```bash
# New daemon module
daemon/local_processor.py
```

### Step 3: Modify book-ingest.py
- Add LocalAI summarization step
- Store embeddings via LocalRecall
- Only send distilled output to Claude

### Step 4: Create escalation rules
- Define when local is sufficient
- Define when Claude is needed
- Track accuracy to tune thresholds

### Step 5: Wire to MAPE controller
- Monitor local vs Claude usage
- Optimize escalation thresholds
- Track cost savings

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Local model quality | Use Mixtral for complex tasks, validate outputs |
| GPU requirements | CPU-only mode works, just slower |
| Storage for models | 10-30GB needed, use smallest sufficient model |
| Integration complexity | Start with summarization only, expand gradually |

---

## Success Metrics

1. **Token reduction**: Target 80% reduction in Claude API usage
2. **Quality maintenance**: Local summaries should be 90%+ accurate
3. **Latency**: Local processing should be <10s per chunk
4. **Cost**: Near-zero for local, only Claude for high-value tasks

---

## Next Steps After Agent Research Completes

1. Validate LocalAI setup works on your hardware
2. Choose optimal models for your GPU/RAM
3. Implement local_processor.py
4. Test end-to-end with sample PDF
5. Measure actual token savings
