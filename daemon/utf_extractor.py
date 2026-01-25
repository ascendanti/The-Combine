#!/usr/bin/env python3
"""
UTF Schema Extractor - Extract knowledge according to UTF Research OS Spec.

This module provides structured extraction of:
- Source metadata
- Excerpts with locations
- Claims (atomized assertions)
- Concepts
- Assumptions
- Limitations

Uses LocalAI for inference, optimized for Mistral 7B.

Reference: specs/UTF-RESEARCH-OS-SPEC.md
"""

import os
import re
import json
import hashlib
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from pathlib import Path

# Dragonfly/Redis cache (Phase 13.3)
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# ============================================================================
# Configuration
# ============================================================================

LOCALAI_URL = os.environ.get("LOCALAI_URL", "http://localhost:8080/v1")
LOCALAI_MODEL = "mistral-7b-instruct-v0.3"
DRAGONFLY_URL = os.environ.get("DRAGONFLY_URL", "redis://localhost:6379")
LLM_CACHE_TTL = 86400  # 24 hours

# ============================================================================
# Phase 13.3: Dragonfly LLM Cache
# ============================================================================

_dragonfly_client = None

def get_dragonfly():
    """Get or create Dragonfly connection."""
    global _dragonfly_client
    if _dragonfly_client is None and REDIS_AVAILABLE:
        try:
            _dragonfly_client = redis.from_url(DRAGONFLY_URL)
            _dragonfly_client.ping()
        except Exception:
            _dragonfly_client = None
    return _dragonfly_client

def make_prompt_hash(prompt: str) -> str:
    """Create deterministic hash for prompt caching."""
    key = f"{LOCALAI_MODEL}:{prompt[:1000]}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]

def cache_get(prompt_hash: str) -> Optional[str]:
    """Get cached LLM response."""
    client = get_dragonfly()
    if client:
        try:
            result = client.get(f"llm:utf:{prompt_hash}")
            if result:
                return result.decode()
        except Exception:
            pass
    return None

def cache_set(prompt_hash: str, response: str):
    """Cache LLM response."""
    client = get_dragonfly()
    if client:
        try:
            client.setex(f"llm:utf:{prompt_hash}", LLM_CACHE_TTL, response)
        except Exception:
            pass

# ============================================================================
# UTF Data Classes (MVP Node Types)
# ============================================================================

@dataclass
class UTFSource:
    """L0: Original document artifact."""
    source_id: str
    title: str
    authors: List[str]
    year: Optional[int]
    source_type: str  # Paper, Book, Report, etc.
    file_hash: str
    abstract: Optional[str] = None
    venue: Optional[str] = None
    domain: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    quality_status: str = "pending"  # pending, accepted, needs_review

@dataclass
class UTFExcerpt:
    """L1: Direct quote or paraphrase anchored to source."""
    excerpt_id: str
    source_id: str
    text: str
    location: str  # page/section reference
    excerpt_type: str = "direct_quote"  # direct_quote, paraphrase
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class UTFClaim:
    """L2: Atomic assertion extracted from source."""
    claim_id: str
    statement: str
    claim_form: str  # definition, measurement, causal_mechanism, etc.
    grounding: str  # anchored, hypothesis, conjecture
    confidence: float  # 0.0-1.0
    source_id: str
    excerpt_ids: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    validity_status: str = "valid"  # valid, needs_atomization, needs_grounding
    stability_class: str = "unknown"  # stable, evolving, contested, unknown
    evidence_grade: str = "ungraded"  # A (strong), B (moderate), C (weak), ungraded
    domain: Optional[str] = None  # research domain
    scope: str = "local"  # local, general, universal
    # Claim classification fields (Phase 10.4)
    slug_code: Optional[str] = None  # Unique semantic slug for similarity matching
    taxonomy_tags: List[str] = field(default_factory=list)  # Hierarchical classification
    utf_vector: Optional[List[float]] = None  # Embedding for closeness calculation

@dataclass
class UTFConcept:
    """L3: Abstract idea unifying multiple claims."""
    concept_id: str
    name: str
    definition_1liner: str
    domain: Optional[str] = None
    source_ids: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    maturity_status: str = "stub"  # stub, developing, mature

@dataclass
class UTFAssumption:
    """Explicit assumption a claim/model depends on."""
    assumption_id: str
    statement: str
    assumption_type: str  # Data, Compute, Distribution, Causal, Measurement, Social
    violations: str  # what happens if violated
    scope: str  # where this assumption applies
    source_id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class UTFLimitation:
    """Explicit limitation or caveat."""
    limitation_id: str
    statement: str
    severity: str  # minor, moderate, major
    source_id: str
    affects: List[str] = field(default_factory=list)  # claim_ids affected
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class UTFEdge:
    """Relationship between nodes."""
    from_id: str
    to_id: str
    edge_type: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class UTFExtractionResult:
    """Complete extraction result for a document."""
    source: UTFSource
    excerpts: List[UTFExcerpt]
    claims: List[UTFClaim]
    concepts: List[UTFConcept]
    assumptions: List[UTFAssumption]
    limitations: List[UTFLimitation]
    edges: List[UTFEdge]
    quality_gate_passed: bool
    extraction_stats: Dict[str, int]

# ============================================================================
# LocalAI Interface
# ============================================================================

def localai_complete(prompt: str, max_tokens: int = 500, retries: int = 2) -> str:
    """Call LocalAI for completion with retry logic and caching."""
    # Phase 13.3: Check cache first
    prompt_hash = make_prompt_hash(prompt)
    cached = cache_get(prompt_hash)
    if cached:
        print(f"[Cache HIT] {prompt_hash[:8]}...")
        return cached

    for attempt in range(retries + 1):
        try:
            response = requests.post(
                f"{LOCALAI_URL}/chat/completions",
                json={
                    "model": LOCALAI_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": 0.3
                },
                timeout=180  # 3 minutes - reduced chunks should be faster
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            # Cache successful response
            cache_set(prompt_hash, content)
            print(f"[Cache SET] {prompt_hash[:8]}...")
            return content
        except requests.exceptions.Timeout:
            if attempt < retries:
                print(f"[LocalAI] Timeout, retrying ({attempt + 1}/{retries})...")
                continue
            print(f"[LocalAI Error] Timeout after {retries + 1} attempts")
            return ""
        except Exception as e:
            print(f"[LocalAI Error] {e}")
            return ""
    return ""

# ============================================================================
# Extraction Prompts (Optimized for Mistral 7B)
# ============================================================================

PROMPT_EXTRACT_METADATA = """Extract metadata from this academic paper text. Return ONLY valid JSON.

TEXT (first 3000 chars):
{text}

Return JSON with these fields:
{{
  "title": "actual paper title (not filename)",
  "authors": ["author1", "author2"],
  "year": 2024,
  "abstract": "paper abstract",
  "venue": "conference or journal name",
  "domain": "machine_learning|cognitive_science|mathematics|systems|applications",
  "keywords": ["keyword1", "keyword2", "keyword3"]
}}

JSON:"""

PROMPT_EXTRACT_EXCERPTS = """Extract important excerpts from this text section. Focus on:
- Definitions ("X is defined as", "we define X as")
- Claims with metrics ("achieves X%", "outperforms by Y")
- Limitations ("however", "limitation", "does not")
- Assumptions ("assume", "assuming", "under the condition")

TEXT:
{text}

Return JSON array of excerpts:
[
  {{"text": "exact quote or close paraphrase", "type": "definition|claim|limitation|assumption", "location": "section name or context"}}
]

JSON:"""

PROMPT_ATOMIZE_CLAIMS = """Convert these excerpts into atomic claims. Each claim should be:
- A single testable/falsifiable assertion
- NOT contain "and" joining independent assertions
- Be specific, not vague

EXCERPTS:
{excerpts}

Return JSON array of claims:
[
  {{
    "statement": "single atomic claim",
    "claim_form": "definition|measurement|empirical_regularity|causal_mechanism|limitation|assumption|hypothesis",
    "grounding": "anchored|hypothesis|conjecture",
    "confidence": 0.7,
    "from_excerpt_index": 0
  }}
]

JSON:"""

PROMPT_EXTRACT_CONCEPTS = """Identify key concepts from these claims. A concept is an abstract idea that multiple claims reference.

CLAIMS:
{claims}

Return JSON array of concepts:
[
  {{
    "name": "concept name",
    "definition_1liner": "25 words or less definition",
    "domain": "machine_learning|cognitive_science|mathematics|systems|applications"
  }}
]

JSON:"""

PROMPT_EXTRACT_ASSUMPTIONS = """Identify assumptions from this text. Focus on:
- Data assumptions (distribution, size, quality)
- Compute assumptions (resources needed)
- Causal assumptions (causal relationships assumed)
- Measurement assumptions (how things are measured)

TEXT:
{text}

Return JSON array:
[
  {{
    "statement": "the assumption",
    "assumption_type": "Data|Compute|Distribution|Causal|Measurement|Social",
    "violations": "what fails if this assumption is violated",
    "scope": "where this applies"
  }}
]

JSON:"""

PROMPT_EXTRACT_LIMITATIONS = """Identify limitations and caveats from this text. Look for:
- "however", "but", "limitation", "caveat", "does not", "cannot"
- Scope restrictions
- Failure cases

TEXT:
{text}

Return JSON array:
[
  {{
    "statement": "the limitation",
    "severity": "minor|moderate|major"
  }}
]

JSON:"""

# Claim Classification Prompt (Phase 10.4)
PROMPT_CLASSIFY_CLAIM = """Classify this claim with a unique semantic slug and taxonomy tags.

CLAIM: {claim}
CLAIM_FORM: {claim_form}
DOMAIN: {domain}

Generate:
1. A unique slug_code (3-5 lowercase words joined by hyphens) that captures the core semantic meaning
   - Format: domain-action-subject-qualifier
   - Examples: "ml-attention-mechanism-scaling", "cog-memory-retrieval-decay", "math-convergence-proof-technique"
2. Taxonomy tags (hierarchical classification path)
   - Format: ["Level1", "Level2", "Level3"]
   - Examples: ["Machine Learning", "Transformers", "Attention"], ["Cognitive Science", "Memory", "Working Memory"]

Return JSON:
{{
  "slug_code": "domain-action-subject-qualifier",
  "taxonomy_tags": ["Level1", "Level2", "Level3"]
}}

JSON:"""

PROMPT_COMPUTE_SIMILARITY = """Compare these two claims and rate their semantic similarity.

CLAIM_A: {claim_a}
SLUG_A: {slug_a}

CLAIM_B: {claim_b}
SLUG_B: {slug_b}

Rate similarity from 0.0 (completely different) to 1.0 (same meaning):
- 0.0-0.2: Unrelated claims
- 0.2-0.4: Same domain, different topics
- 0.4-0.6: Related topics, different claims
- 0.6-0.8: Similar claims, different framing
- 0.8-1.0: Nearly identical semantic meaning

Return JSON:
{{
  "similarity": 0.X,
  "relationship": "unrelated|same_domain|related|similar|equivalent",
  "common_concepts": ["concept1", "concept2"]
}}

JSON:"""

# ============================================================================
# Extraction Functions
# ============================================================================

def generate_id(prefix: str, content: str) -> str:
    """Generate a short unique ID."""
    import hashlib
    hash_val = hashlib.md5(content.encode()).hexdigest()[:8]
    return f"{prefix}_{hash_val}"

def parse_json_response(response: str) -> Any:
    """Parse JSON from LocalAI response, handling common issues."""
    # Try to find JSON in response
    response = response.strip()

    # Remove markdown code blocks if present
    if response.startswith("```"):
        lines = response.split("\n")
        response = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    # Try direct parse
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Try to find JSON array or object
    for start, end in [("[", "]"), ("{", "}")]:
        idx_start = response.find(start)
        idx_end = response.rfind(end)
        if idx_start != -1 and idx_end > idx_start:
            try:
                return json.loads(response[idx_start:idx_end + 1])
            except json.JSONDecodeError:
                continue

    return None

def extract_metadata(text: str, file_hash: str) -> UTFSource:
    """Extract source metadata using LocalAI."""
    prompt = PROMPT_EXTRACT_METADATA.format(text=text[:1500])  # Reduced for CPU speed
    response = localai_complete(prompt, max_tokens=500)

    data = parse_json_response(response)
    if not data:
        # Fallback to basic extraction
        data = {
            "title": "Unknown Title",
            "authors": [],
            "year": None,
            "abstract": None,
            "domain": None,
            "keywords": []
        }

    return UTFSource(
        source_id=generate_id("src", file_hash),
        title=data.get("title", "Unknown Title"),
        authors=data.get("authors", []),
        year=data.get("year"),
        source_type="Paper",
        file_hash=file_hash,
        abstract=data.get("abstract"),
        venue=data.get("venue"),
        domain=data.get("domain"),
        keywords=data.get("keywords", [])
    )

def extract_excerpts(text: str, source_id: str, chunk_size: int = 1200) -> List[UTFExcerpt]:  # Reduced for CPU
    """Extract excerpts from text chunks."""
    excerpts = []

    # Process in smaller chunks for LocalAI performance
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

    for i, chunk in enumerate(chunks[:3]):  # Limit to first 3 chunks for speed
        prompt = PROMPT_EXTRACT_EXCERPTS.format(text=chunk)
        response = localai_complete(prompt, max_tokens=800)

        data = parse_json_response(response)
        if data and isinstance(data, list):
            for item in data:
                if item.get("text"):
                    excerpt = UTFExcerpt(
                        excerpt_id=generate_id("exc", item["text"]),
                        source_id=source_id,
                        text=item["text"],
                        location=item.get("location", f"chunk_{i}"),
                        excerpt_type=item.get("type", "direct_quote")
                    )
                    excerpts.append(excerpt)

    return excerpts

def atomize_to_claims(excerpts: List[UTFExcerpt], source_id: str) -> List[UTFClaim]:
    """Atomize excerpts into claims."""
    if not excerpts:
        return []

    excerpt_texts = [{"index": i, "text": e.text, "type": e.excerpt_type}
                     for i, e in enumerate(excerpts)]

    prompt = PROMPT_ATOMIZE_CLAIMS.format(excerpts=json.dumps(excerpt_texts[:10]))
    response = localai_complete(prompt, max_tokens=1000)

    data = parse_json_response(response)
    claims = []

    if data and isinstance(data, list):
        for item in data:
            if item.get("statement"):
                exc_idx = item.get("from_excerpt_index", 0)
                exc_ids = [excerpts[exc_idx].excerpt_id] if exc_idx < len(excerpts) else []

                claim = UTFClaim(
                    claim_id=generate_id("clm", item["statement"]),
                    statement=item["statement"],
                    claim_form=item.get("claim_form", "empirical_regularity"),
                    grounding=item.get("grounding", "anchored"),
                    confidence=item.get("confidence", 0.5),
                    source_id=source_id,
                    excerpt_ids=exc_ids
                )
                claims.append(claim)

    return claims

def extract_concepts(claims: List[UTFClaim]) -> List[UTFConcept]:
    """Extract concepts from claims."""
    if not claims:
        return []

    claim_texts = [{"statement": c.statement, "form": c.claim_form} for c in claims]

    prompt = PROMPT_EXTRACT_CONCEPTS.format(claims=json.dumps(claim_texts[:15]))
    response = localai_complete(prompt, max_tokens=600)

    data = parse_json_response(response)
    concepts = []

    if data and isinstance(data, list):
        for item in data:
            if item.get("name"):
                concept = UTFConcept(
                    concept_id=generate_id("cpt", item["name"]),
                    name=item["name"],
                    definition_1liner=item.get("definition_1liner", ""),
                    domain=item.get("domain"),
                    source_ids=[c.source_id for c in claims[:1]]
                )
                concepts.append(concept)

    return concepts

def extract_assumptions(text: str, source_id: str) -> List[UTFAssumption]:
    """Extract assumptions from text."""
    prompt = PROMPT_EXTRACT_ASSUMPTIONS.format(text=text[:1200])  # Reduced for CPU
    response = localai_complete(prompt, max_tokens=600)

    data = parse_json_response(response)
    assumptions = []

    if data and isinstance(data, list):
        for item in data:
            if item.get("statement"):
                assumption = UTFAssumption(
                    assumption_id=generate_id("asm", item["statement"]),
                    statement=item["statement"],
                    assumption_type=item.get("assumption_type", "Data"),
                    violations=item.get("violations", "Unknown"),
                    scope=item.get("scope", "General"),
                    source_id=source_id
                )
                assumptions.append(assumption)

    return assumptions

def extract_limitations(text: str, source_id: str) -> List[UTFLimitation]:
    """Extract limitations from text."""
    prompt = PROMPT_EXTRACT_LIMITATIONS.format(text=text[:1200])  # Reduced for CPU
    response = localai_complete(prompt, max_tokens=500)

    data = parse_json_response(response)
    limitations = []

    if data and isinstance(data, list):
        for item in data:
            if item.get("statement"):
                limitation = UTFLimitation(
                    limitation_id=generate_id("lim", item["statement"]),
                    statement=item["statement"],
                    severity=item.get("severity", "moderate"),
                    source_id=source_id
                )
                limitations.append(limitation)

    return limitations

# ============================================================================
# Claim Classification (Phase 10.4)
# ============================================================================

def classify_claim(claim: UTFClaim, domain: str = None) -> UTFClaim:
    """Generate semantic slug and taxonomy tags for a claim."""
    prompt = PROMPT_CLASSIFY_CLAIM.format(
        claim=claim.statement,
        claim_form=claim.claim_form,
        domain=domain or "general"
    )
    response = localai_complete(prompt, max_tokens=200)

    data = parse_json_response(response)
    if data:
        claim.slug_code = data.get("slug_code", generate_fallback_slug(claim.statement))
        claim.taxonomy_tags = data.get("taxonomy_tags", [])
    else:
        # Fallback slug generation
        claim.slug_code = generate_fallback_slug(claim.statement)
        claim.taxonomy_tags = [claim.claim_form]

    return claim

def generate_fallback_slug(statement: str) -> str:
    """Generate a fallback slug from the statement."""
    import re
    # Extract key words (nouns and verbs)
    words = re.findall(r'\b[a-z]{4,}\b', statement.lower())
    # Take first 4 unique words
    seen = set()
    slug_parts = []
    for w in words:
        if w not in seen and w not in {'that', 'this', 'which', 'with', 'from', 'have', 'been'}:
            seen.add(w)
            slug_parts.append(w)
            if len(slug_parts) >= 4:
                break
    return '-'.join(slug_parts) if slug_parts else f"claim-{hash(statement) % 10000:04d}"

def compute_claim_similarity(claim_a: UTFClaim, claim_b: UTFClaim) -> Dict[str, Any]:
    """Compute semantic similarity between two claims."""
    prompt = PROMPT_COMPUTE_SIMILARITY.format(
        claim_a=claim_a.statement,
        slug_a=claim_a.slug_code or "unknown",
        claim_b=claim_b.statement,
        slug_b=claim_b.slug_code or "unknown"
    )
    response = localai_complete(prompt, max_tokens=150)

    data = parse_json_response(response)
    if data:
        return {
            "similarity": data.get("similarity", 0.0),
            "relationship": data.get("relationship", "unknown"),
            "common_concepts": data.get("common_concepts", []),
            "claim_a_id": claim_a.claim_id,
            "claim_b_id": claim_b.claim_id
        }

    # Fallback: simple slug-based similarity
    if claim_a.slug_code and claim_b.slug_code:
        a_parts = set(claim_a.slug_code.split('-'))
        b_parts = set(claim_b.slug_code.split('-'))
        overlap = len(a_parts & b_parts) / max(len(a_parts | b_parts), 1)
        return {
            "similarity": overlap,
            "relationship": "slug_match" if overlap > 0.5 else "different",
            "common_concepts": list(a_parts & b_parts),
            "claim_a_id": claim_a.claim_id,
            "claim_b_id": claim_b.claim_id
        }

    return {"similarity": 0.0, "relationship": "unknown", "common_concepts": []}

def batch_classify_claims(claims: List[UTFClaim], domain: str = None) -> List[UTFClaim]:
    """Classify multiple claims efficiently."""
    classified = []
    for i, claim in enumerate(claims):
        print(f"    [Classify] Claim {i+1}/{len(claims)}: {claim.statement[:40]}...")
        classified.append(classify_claim(claim, domain))
    return classified

def find_similar_claims(target_claim: UTFClaim, all_claims: List[UTFClaim],
                        threshold: float = 0.5) -> List[Dict[str, Any]]:
    """Find claims similar to target above threshold."""
    similar = []
    for claim in all_claims:
        if claim.claim_id == target_claim.claim_id:
            continue
        result = compute_claim_similarity(target_claim, claim)
        if result["similarity"] >= threshold:
            similar.append(result)
    return sorted(similar, key=lambda x: x["similarity"], reverse=True)

def create_edges(source: UTFSource, excerpts: List[UTFExcerpt],
                 claims: List[UTFClaim], concepts: List[UTFConcept],
                 assumptions: List[UTFAssumption]) -> List[UTFEdge]:
    """Create edges between nodes."""
    edges = []

    # Claim -> Excerpt (supported_by)
    for claim in claims:
        for exc_id in claim.excerpt_ids:
            edges.append(UTFEdge(
                from_id=claim.claim_id,
                to_id=exc_id,
                edge_type="supported_by"
            ))

    # Claim -> Assumption (depends_on_assumption)
    for claim in claims:
        for assumption in assumptions:
            edges.append(UTFEdge(
                from_id=claim.claim_id,
                to_id=assumption.assumption_id,
                edge_type="depends_on_assumption"
            ))

    # Claim -> Concept (defines) - for definition claims
    definition_claims = [c for c in claims if c.claim_form == "definition"]
    for claim in definition_claims:
        for concept in concepts:
            if concept.name.lower() in claim.statement.lower():
                edges.append(UTFEdge(
                    from_id=claim.claim_id,
                    to_id=concept.concept_id,
                    edge_type="defines"
                ))

    return edges

def check_quality_gate(source: UTFSource, excerpts: List[UTFExcerpt],
                       claims: List[UTFClaim]) -> bool:
    """Check if extraction passes quality gate."""
    # Gate 1: Source Acceptance
    # - Title extracted (not filename)
    # - At least 1 author identified
    # - At least 3 excerpts extracted
    # - At least 2 claims derived

    has_title = source.title and source.title != "Unknown Title"
    has_authors = len(source.authors) >= 1
    has_excerpts = len(excerpts) >= 3
    has_claims = len(claims) >= 2

    return has_title and has_excerpts and has_claims

# ============================================================================
# Main Extraction Function
# ============================================================================

def extract_utf_schema(text: str, file_hash: str, classify: bool = True) -> UTFExtractionResult:
    """
    Full UTF extraction pipeline.

    Pass 1: Structural (metadata)
    Pass 2: Excerpt extraction
    Pass 3: Claim atomization + concepts
    Pass 4: Assumptions + limitations
    Pass 5: Claim classification with slug codes (optional)
    """
    print("    [UTF Pass 1] Extracting metadata...")
    source = extract_metadata(text, file_hash)

    print("    [UTF Pass 2] Extracting excerpts...")
    excerpts = extract_excerpts(text, source.source_id)

    print("    [UTF Pass 3] Atomizing claims + concepts...")
    claims = atomize_to_claims(excerpts, source.source_id)
    concepts = extract_concepts(claims)

    print("    [UTF Pass 4] Extracting assumptions + limitations...")
    assumptions = extract_assumptions(text, source.source_id)
    limitations = extract_limitations(text, source.source_id)

    # Pass 5: Claim classification with slug codes
    if classify and claims:
        print("    [UTF Pass 5] Classifying claims with slug codes...")
        claims = batch_classify_claims(claims, source.domain)

    print("    [UTF] Creating edges...")
    edges = create_edges(source, excerpts, claims, concepts, assumptions)

    # Quality gate
    passed = check_quality_gate(source, excerpts, claims)
    source.quality_status = "accepted" if passed else "needs_review"

    stats = {
        "excerpts": len(excerpts),
        "claims": len(claims),
        "concepts": len(concepts),
        "assumptions": len(assumptions),
        "limitations": len(limitations),
        "edges": len(edges)
    }

    print(f"    [UTF] Extraction complete: {stats}")

    return UTFExtractionResult(
        source=source,
        excerpts=excerpts,
        claims=claims,
        concepts=concepts,
        assumptions=assumptions,
        limitations=limitations,
        edges=edges,
        quality_gate_passed=passed,
        extraction_stats=stats
    )

# ============================================================================
# Obsidian Export
# ============================================================================

def export_to_obsidian(result: UTFExtractionResult, vault_path: Path):
    """Export extraction result to Obsidian vault."""

    # Source note
    source_dir = vault_path / "00_Sources"
    source_dir.mkdir(parents=True, exist_ok=True)

    source_note = f"""---
type: Source
source_id: {result.source.source_id}
title: "{result.source.title}"
authors: {result.source.authors}
year: {result.source.year}
domain: {result.source.domain}
quality_status: {result.source.quality_status}
created_at: {result.source.created_at}
---

# {result.source.title}

## Abstract
{result.source.abstract or "No abstract extracted"}

## Keywords
{', '.join(result.source.keywords)}

## Extracted Content

### Claims ({len(result.claims)})
{chr(10).join([f'- [[Claim-{c.claim_id}|{c.statement[:50]}...]]' for c in result.claims[:10]])}

### Concepts ({len(result.concepts)})
{chr(10).join([f'- [[Concept-{c.concept_id}|{c.name}]]' for c in result.concepts])}

### Assumptions ({len(result.assumptions)})
{chr(10).join([f'- {a.statement}' for a in result.assumptions])}

### Limitations ({len(result.limitations)})
{chr(10).join([f'- {l.statement}' for l in result.limitations])}
"""

    safe_title = re.sub(r'[<>:"/\\|?*]', '_', result.source.title)[:100]
    with open(source_dir / f"{safe_title}.md", "w", encoding="utf-8") as f:
        f.write(source_note)

    # Claim notes
    claims_dir = vault_path / "02_Claims"
    claims_dir.mkdir(parents=True, exist_ok=True)

    for claim in result.claims:
        claim_note = f"""---
type: Claim
claim_id: {claim.claim_id}
slug_code: {claim.slug_code or "unclassified"}
claim_form: {claim.claim_form}
grounding: {claim.grounding}
confidence: {claim.confidence}
taxonomy: {claim.taxonomy_tags}
source_id: {claim.source_id}
created_at: {claim.created_at}
---

# {claim.statement[:50]}...

## Full Statement
{claim.statement}

## Classification
- **Slug Code**: `{claim.slug_code or "unclassified"}`
- **Taxonomy**: {' > '.join(claim.taxonomy_tags) if claim.taxonomy_tags else "Unclassified"}

## Metadata
- **Form**: {claim.claim_form}
- **Grounding**: {claim.grounding}
- **Confidence**: {claim.confidence}

## Source
[[{safe_title}]]
"""
        with open(claims_dir / f"Claim-{claim.claim_id}.md", "w", encoding="utf-8") as f:
            f.write(claim_note)

    # Concept notes
    concepts_dir = vault_path / "03_Concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)

    for concept in result.concepts:
        concept_note = f"""---
type: Concept
concept_id: {concept.concept_id}
name: "{concept.name}"
domain: {concept.domain}
maturity_status: {concept.maturity_status}
created_at: {concept.created_at}
---

# {concept.name}

## Definition (1-liner)
{concept.definition_1liner}

## Sources
[[{safe_title}]]
"""
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', concept.name)[:50]
        with open(concepts_dir / f"Concept-{safe_name}.md", "w", encoding="utf-8") as f:
            f.write(concept_note)

# ============================================================================
# CLI Interface
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="UTF Schema Extractor")
    parser.add_argument("--test", help="Test extraction on a text file")
    parser.add_argument("--vault", default=str(Path.home() / "Documents" / "Obsidian" / "ClaudeKnowledge"),
                        help="Obsidian vault path")

    args = parser.parse_args()

    if args.test:
        with open(args.test, "r", encoding="utf-8") as f:
            text = f.read()

        import hashlib
        file_hash = hashlib.sha256(text.encode()).hexdigest()[:16]

        result = extract_utf_schema(text, file_hash)

        print(f"\nExtraction Results:")
        print(f"  Source: {result.source.title}")
        print(f"  Quality Gate: {'PASSED' if result.quality_gate_passed else 'NEEDS REVIEW'}")
        print(f"  Stats: {result.extraction_stats}")

        if args.vault:
            export_to_obsidian(result, Path(args.vault))
            print(f"\nExported to: {args.vault}")
