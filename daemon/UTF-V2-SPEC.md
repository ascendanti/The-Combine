# UTF v2 Specification
## Unified Theory of Facts - Research OS Upgrade

**Goal:** 10-30× improvement in effectiveness, efficiency, depth, context, and applied knowledge.

---

## Current Architecture (v1)

```
Document → 4 passes → 13+ LLM calls/doc → 2-4 min/call on CPU

Pass 1: Metadata extraction (1 call)
Pass 2: Excerpt extraction (3 calls - first 3 chunks)
Pass 3: Claim/concept atomization (N calls per excerpt)
Pass 4: Synthesis (assumptions, limitations, contradictions)
```

**Problems:**
- Systematically misses: contributions (end of intro), limitations (end), results tables
- "Chunk first 3" is arbitrary, not structural
- Cache keys too coarse (prompt hash)
- No addressable spans for provenance
- O(all claims) synthesis cost

---

## v2 Architecture

```
Document → Structural Parse → Span Selection → 2 LLM calls → Indexed Storage

Call A: Triage (optional cheap model)
Call B: Structured extraction over selected spans
```

**Expected gains:**
- 4-8× speedup (13 calls → 2-3)
- 80-95% cache hit rate (vs 40-60%)
- 10-100× synthesis cost reduction (neighbor-based)
- True provenance (claim → span → page)

---

## Module Specifications

### 1. document_model.py

Hierarchical document representation with stable IDs.

```python
@dataclass
class Span:
    span_id: str           # Deterministic hash
    section_path: str      # e.g., "introduction/contributions"
    page: int
    start_char: int
    end_char: int
    text: str
    span_hash: str         # Content hash for caching

@dataclass
class Section:
    heading: str
    level: int             # 1=chapter, 2=section, 3=subsection
    spans: List[Span]
    children: List['Section']

@dataclass
class DocumentModel:
    source_id: str
    title: str
    sections: List[Section]

    def get_span(self, span_id: str) -> Span
    def find_sections(self, pattern: str) -> List[Section]
    def high_signal_spans(self) -> List[Span]
```

### 2. span_selector.py

Deterministic selection of high-ROI spans.

```python
HIGH_SIGNAL_SECTIONS = [
    "abstract",
    "introduction/contributions",
    "introduction/problem",
    "method",
    "assumptions",
    "results",
    "findings",
    "limitations",
    "conclusion",
    "figure_captions",
    "table_captions"
]

def select_spans(doc: DocumentModel) -> List[Span]:
    """
    Select spans using:
    1. Section heading matching (regex)
    2. Layout hints (bold, numbered lists)
    3. Length thresholds (skip trivial sections)
    4. Caption detection (Figure X:, Table Y:)
    """
    pass

def parse_headings(text: str) -> List[Section]:
    """Extract section hierarchy from markdown/text."""
    pass
```

### 3. extractor_v2.py

Collapsed 2-call extraction.

```python
def extract_document(doc: DocumentModel, spans: List[Span]) -> ExtractionResult:
    """
    Single LLM call returns:
    - metadata (title, authors, year, domain)
    - excerpts (each linked to span_id)
    - claims (each linked to excerpt + span)
    - concepts (each linked to span)
    - assumptions (with scope)
    - limitations (with severity)
    """

    prompt = build_structured_prompt(doc, spans)
    response = llm_call(prompt, cache_key=compute_cache_key(spans))

    return parse_structured_response(response, spans)

def compute_cache_key(spans: List[Span]) -> str:
    """
    cache_key = sha256(
        template_id +
        template_version +
        model_id +
        sorted([s.span_hash for s in spans]) +
        extraction_mode
    )
    """
    pass
```

### 4. llm_cache_l2.py

Persistent semantic compute artifacts.

```sql
CREATE TABLE llm_cache (
    cache_key TEXT PRIMARY KEY,
    template_id TEXT,
    template_version TEXT,
    model_id TEXT,
    span_hashes TEXT,  -- JSON array
    response TEXT,
    tokens_used INTEGER,
    created_at TEXT,
    expires_at TEXT
);

CREATE INDEX idx_template ON llm_cache(template_id, template_version);
CREATE INDEX idx_expires ON llm_cache(expires_at);
```

```python
class LLMCacheL2:
    def get(self, key: str) -> Optional[str]
    def set(self, key: str, value: str, ttl_days: int = 30)
    def invalidate_template(self, template_id: str, version_before: str)
```

### 5. mcp_utf_server.py

MCP tools for Claude retrieval.

```python
@mcp_tool
def search_claims(query: str, top_k: int = 10, domain: str = None) -> List[Claim]:
    """
    Hybrid search: FTS5 exact + vector similarity.
    Returns claims with evidence chain.
    """

@mcp_tool
def get_evidence(claim_id: str) -> Evidence:
    """
    Returns: excerpts + source refs + span locations.
    """

@mcp_tool
def neighbors(claim_id: str, k: int = 5) -> List[Claim]:
    """
    Vector similarity search for related claims.
    Used for contradiction/support detection.
    """

@mcp_tool
def topic_brief(query: str, max_claims: int = 20) -> Brief:
    """
    Grounded synthesis with citations.
    Returns: summary + supporting claims + conflicts + gaps.
    """
```

### 6. Action Objects Schema

```sql
-- Procedures: how-to steps
CREATE TABLE utf_procedures (
    id TEXT PRIMARY KEY,
    title TEXT,
    preconditions TEXT,  -- JSON array
    steps TEXT,          -- JSON array with ordering
    failure_modes TEXT,  -- JSON array
    source_claims TEXT,  -- JSON array of claim_ids
    domain TEXT
);

-- Rules: if/then triggers
CREATE TABLE utf_rules (
    id TEXT PRIMARY KEY,
    condition TEXT,      -- When this is true...
    action TEXT,         -- ...do this
    thresholds TEXT,     -- JSON: numeric constraints
    exceptions TEXT,     -- JSON array
    source_claims TEXT
);

-- Recipes: parameterized templates
CREATE TABLE utf_recipes (
    id TEXT PRIMARY KEY,
    name TEXT,
    parameters TEXT,     -- JSON schema
    template TEXT,       -- With {{placeholders}}
    checklist TEXT,      -- JSON array of verification steps
    source_claims TEXT
);

-- Decisions: decision tree nodes
CREATE TABLE utf_decisions (
    id TEXT PRIMARY KEY,
    question TEXT,
    criteria TEXT,       -- JSON array
    options TEXT,        -- JSON array with evidence links
    recommended TEXT,    -- Option ID
    evidence_strength TEXT,
    source_claims TEXT
);
```

---

## Implementation Order

1. **span_selector.py** - Biggest single impact (Codex: "do tomorrow")
2. **document_model.py** - Required for span_selector
3. **extractor_v2.py** - Uses document_model + span_selector
4. **llm_cache_l2.py** - Improves cache hit rate
5. **embeddings index** - Enables neighbor retrieval
6. **mcp_utf_server.py** - Makes knowledge operational
7. **Action Objects** - Transforms facts into operators

---

## Migration Path

1. Keep v1 running for current documents
2. v2 processes new documents with new schema
3. Backfill high-value v1 documents through v2
4. Deprecate v1 when v2 proven stable

---

## Success Metrics

| Metric | v1 | v2 Target |
|--------|-----|-----------|
| Calls/document | 13+ | 2-3 |
| Cache hit rate | 40-60% | 80-95% |
| Extraction time | 20-40 min | 5-10 min |
| Provenance | None | Full span chain |
| Synthesis cost | O(all) | O(k neighbors) |
| Actionable outputs | Facts only | Facts + Procedures + Rules |

---

**Created:** 2026-01-27
**Status:** Specification complete - implementation starting
