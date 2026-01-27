"""
UTF v2 Extractor - Collapsed 2-call extraction pipeline.

Codex recommendation: Replace 4-pass (13+ calls) with 2-call architecture:
- Call A: Optional triage/span selection (cheap/heuristic)
- Call B: Structured extraction over selected spans

Expected: 4-8x speedup, 80-95% cache hit rate.
"""

import hashlib
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

try:
    from document_model import DocumentModel, Span
    from span_selector import select_spans
except ImportError:
    DocumentModel = None
    Span = None


# ============================================================================
# Cache Key Computation
# ============================================================================

TEMPLATE_VERSION = "v2.0"
EXTRACTION_MODE = "structured_spans"

def compute_cache_key(
    spans: List['Span'],
    model_id: str = "mistral-7b",
    template_id: str = "utf_extraction_v2"
) -> str:
    """
    Codex recommendation: Cache key = sha256(
        template_id + template_version + model_id + sorted([span_hash for spans])
    )

    This survives prompt tweaks without poisoning cache.
    """
    span_hashes = sorted([s.span_hash for s in spans])
    combined = f"{template_id}:{TEMPLATE_VERSION}:{model_id}:{':'.join(span_hashes)}:{EXTRACTION_MODE}"
    return hashlib.sha256(combined.encode()).hexdigest()[:24]


# ============================================================================
# Extraction Result
# ============================================================================

@dataclass
class ExtractionResult:
    """Result of structured extraction."""
    source_id: str
    title: str
    metadata: Dict[str, Any]  # authors, year, domain, etc.
    excerpts: List[Dict[str, Any]]  # each linked to span_id
    claims: List[Dict[str, Any]]    # each linked to excerpt + span
    concepts: List[Dict[str, Any]]  # each linked to span
    assumptions: List[Dict[str, Any]]  # with scope
    limitations: List[Dict[str, Any]]  # with severity
    extraction_time: float
    cache_hit: bool
    spans_processed: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# Prompt Builder
# ============================================================================

def build_structured_prompt(doc: 'DocumentModel', spans: List['Span']) -> str:
    """
    Build single-call extraction prompt over selected spans.

    Returns all extraction artifacts in one JSON response.
    """
    # Combine span texts with markers
    span_blocks = []
    for i, span in enumerate(spans, 1):
        span_blocks.append(f"""
[SPAN_{i}] ({span.section_path})
{span.text}
""")

    combined_text = "\n".join(span_blocks)

    prompt = f"""# UTF Research OS - Structured Knowledge Extraction

You are extracting structured knowledge from an academic paper. The document has been pre-selected into high-signal spans covering:
- Abstract
- Key contributions
- Methods and assumptions
- Results and findings
- Limitations
- Figure/table captions

## Document Metadata
Title: {doc.title}
Total spans: {len(spans)}

## Selected Spans
{combined_text}

## Task
Extract knowledge into this JSON schema:

```json
{{
  "metadata": {{
    "title": "Paper title",
    "authors": ["Author 1", "Author 2"],
    "year": 2024,
    "domain": "machine learning | NLP | computer vision | etc.",
    "abstract_summary": "One-sentence summary"
  }},
  "excerpts": [
    {{
      "excerpt_id": "unique_id",
      "span_id": "SPAN_1",
      "text": "Original text from span",
      "significance": "why this matters",
      "excerpt_type": "contribution | method | result | limitation"
    }}
  ],
  "claims": [
    {{
      "claim_id": "unique_id",
      "text": "Atomic factual claim",
      "claim_type": "empirical | definition | causal | comparative",
      "evidence_span_ids": ["SPAN_1", "SPAN_3"],
      "excerpt_id": "links to excerpt above",
      "confidence": "high | medium | low",
      "scope": "when/where this applies"
    }}
  ],
  "concepts": [
    {{
      "concept_id": "unique_id",
      "name": "Canonical concept name",
      "definition": "What it means",
      "aliases": ["alternative names"],
      "span_id": "SPAN_1",
      "domain": "specific field"
    }}
  ],
  "assumptions": [
    {{
      "assumption_id": "unique_id",
      "text": "What is assumed",
      "span_id": "SPAN_2",
      "criticality": "high | medium | low",
      "scope": "where it applies"
    }}
  ],
  "limitations": [
    {{
      "limitation_id": "unique_id",
      "text": "What doesn't work / isn't handled",
      "span_id": "SPAN_4",
      "severity": "high | medium | low",
      "mitigation": "possible workarounds if any"
    }}
  ]]
}}
```

## Guidelines
1. Be atomic: One claim per claim object
2. Link everything to span_id for provenance
3. Prefer canonical names for concepts (avoid synonyms)
4. Extract quantitative results with numbers/units
5. Focus on HIGH-SIGNAL content only - skip background/related work
6. Mark confidence/severity honestly

Return ONLY valid JSON, no commentary.
"""

    return prompt


# ============================================================================
# LLM Call (with caching)
# ============================================================================

def llm_call(
    prompt: str,
    cache_key: str,
    model_id: str = "mistral-7b",
    timeout: int = 600,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Make LLM call with L2 cache support.

    Returns parsed JSON response.
    """
    import requests
    from pathlib import Path
    import sys

    # Import cache (will implement llm_cache_l2.py next)
    try:
        daemon_dir = Path(__file__).parent
        sys.path.insert(0, str(daemon_dir))
        from llm_cache_l2 import LLMCacheL2
        cache = LLMCacheL2()
    except ImportError:
        cache = None

    # Check L2 cache
    if use_cache and cache:
        cached = cache.get(cache_key)
        if cached:
            print(f"[Cache HIT] {cache_key[:12]}...")
            return {'response': cached, 'cache_hit': True}

    # Make LocalAI request
    localai_url = "http://localhost:8080/v1/chat/completions"

    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 4096
    }

    try:
        resp = requests.post(localai_url, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        response_text = data['choices'][0]['message']['content']

        # Store in L2 cache
        if cache:
            cache.set(cache_key, response_text, ttl_days=30)

        return {'response': response_text, 'cache_hit': False}

    except Exception as e:
        print(f"[LLM Error] {e}")
        return {'response': None, 'cache_hit': False, 'error': str(e)}


def parse_structured_response(response_text: str, spans: List['Span']) -> Dict[str, Any]:
    """
    Parse JSON response from LLM.

    Returns dict matching ExtractionResult structure.
    """
    # Extract JSON from markdown code blocks if present
    if '```json' in response_text:
        start = response_text.index('```json') + 7
        end = response_text.rindex('```')
        response_text = response_text[start:end].strip()
    elif '```' in response_text:
        start = response_text.index('```') + 3
        end = response_text.rindex('```')
        response_text = response_text[start:end].strip()

    try:
        data = json.loads(response_text)
        return data
    except json.JSONDecodeError as e:
        print(f"[Parse Error] {e}")
        print(f"Response preview: {response_text[:200]}...")
        return {}


# ============================================================================
# Main Extraction Function
# ============================================================================

def extract_document(
    doc: 'DocumentModel',
    spans: Optional[List['Span']] = None,
    model_id: str = "mistral-7b",
    use_cache: bool = True
) -> ExtractionResult:
    """
    Extract knowledge from document using UTF v2 2-call pipeline.

    Args:
        doc: Parsed document model
        spans: Pre-selected spans (if None, will auto-select)
        model_id: LLM model to use
        use_cache: Whether to use L2 cache

    Returns:
        ExtractionResult with all extracted knowledge
    """
    import time

    start_time = time.time()

    # Step 1: Span selection (if not provided)
    if spans is None:
        spans = select_spans(doc)
        print(f"[Span Selection] Selected {len(spans)} spans from {doc.total_chars} chars")

    # Step 2: Build prompt
    prompt = build_structured_prompt(doc, spans)

    # Step 3: Compute cache key
    cache_key = compute_cache_key(spans, model_id, template_id="utf_extraction_v2")

    # Step 4: LLM call
    print(f"[Extraction] Processing {len(spans)} spans...")
    llm_result = llm_call(prompt, cache_key, model_id, use_cache=use_cache)

    if not llm_result.get('response'):
        # Return empty result on error
        return ExtractionResult(
            source_id=doc.source_id,
            title=doc.title,
            metadata={},
            excerpts=[],
            claims=[],
            concepts=[],
            assumptions=[],
            limitations=[],
            extraction_time=time.time() - start_time,
            cache_hit=False,
            spans_processed=len(spans)
        )

    # Step 5: Parse response
    parsed = parse_structured_response(llm_result['response'], spans)

    # Step 6: Build result
    result = ExtractionResult(
        source_id=doc.source_id,
        title=doc.title,
        metadata=parsed.get('metadata', {}),
        excerpts=parsed.get('excerpts', []),
        claims=parsed.get('claims', []),
        concepts=parsed.get('concepts', []),
        assumptions=parsed.get('assumptions', []),
        limitations=parsed.get('limitations', []),
        extraction_time=time.time() - start_time,
        cache_hit=llm_result.get('cache_hit', False),
        spans_processed=len(spans)
    )

    print(f"[Extraction Complete] {len(result.excerpts)} excerpts, {len(result.claims)} claims, {len(result.concepts)} concepts")
    print(f"[Time] {result.extraction_time:.1f}s (cache: {result.cache_hit})")

    return result


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python extractor_v2.py <file.txt|file.md|file.pdf>")
        print("       python extractor_v2.py --test")
        sys.exit(1)

    if sys.argv[1] == "--test":
        # Test with sample text
        sample = """
# Abstract

This paper presents a novel approach to knowledge extraction achieving 95% accuracy.

# 1. Introduction

Our main contributions are:
1. A new extraction algorithm
2. Evaluation on 10 datasets

# 2. Methods

We use transformer-based models with LoRA fine-tuning.

## 2.1 Assumptions

We assume clean UTF-8 encoded text input.

# 3. Results

Our method achieves 95.2% accuracy, outperforming baselines by 12%.

Table 1: Performance comparison across datasets.

# 4. Limitations

Our approach does not handle multi-modal input or real-time streaming.

# 5. Conclusion

We presented an effective knowledge extraction approach.
"""
        from document_model import DocumentModel

        doc = DocumentModel.from_text(sample, "test.md", "Test Paper")
        result = extract_document(doc)

        print("\n=== Extraction Result ===")
        print(json.dumps(result.to_dict(), indent=2))

    else:
        from document_model import DocumentModel
        filepath = Path(sys.argv[1])

        if not filepath.exists():
            print(f"File not found: {filepath}")
            sys.exit(1)

        text = filepath.read_text(encoding='utf-8', errors='replace')
        doc = DocumentModel.from_text(text, filepath.name)

        result = extract_document(doc)

        # Save result
        output_path = filepath.parent / f"{filepath.stem}_extracted.json"
        output_path.write_text(json.dumps(result.to_dict(), indent=2), encoding='utf-8')

        print(f"\n=== Saved to: {output_path} ===")
