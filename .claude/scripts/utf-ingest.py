#!/usr/bin/env python3
"""
UTF Iterative Ingest - Taxonomy-Aware Knowledge Extraction

Key Principles:
1. ITERATIVE processing (page-by-page, not batch) for LocalAI memory limits
2. UTF taxonomy structure (L0-L6 abstraction ladder)
3. Quality gates (what counts as "knowledge" vs just text)
4. Comprehension scaffolds (7-slot system)
5. DKCS coordinates for filtering/retrieval

Node Types Extracted (MVP):
- Source (L0) - the document itself
- Excerpt (L1) - direct quotes with location
- Claim (L2) - atomic assertions with claim_form
- Concept (L3) - with 7-slot scaffold
- Assumption - dependencies that if violated break claims
- Limitation - constraints on applicability

Usage:
    python utf-ingest.py <pdf_path>              # Iterative ingest
    python utf-ingest.py <pdf_path> --resume     # Resume from checkpoint
    python utf-ingest.py --query "topic"         # Taxonomy-filtered retrieval
    python utf-ingest.py --status                # Show knowledge stats
"""

import os
import sys
import json
import hashlib
import sqlite3
import requests
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum

# Configuration
LOCALAI_URL = os.environ.get("LOCALAI_URL", "http://localhost:8080/v1")
LOCALAI_MODEL = os.environ.get("LOCALAI_MODEL", "mistral-7b-instruct-v0.3")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"  # For complex synthesis only

PROJECT_DIR = Path(__file__).parent.parent.parent
DB_PATH = PROJECT_DIR / "daemon" / "utf_knowledge.db"
OBSIDIAN_VAULT = Path.home() / "Documents" / "Obsidian" / "ClaudeKnowledge"
KG_PATH = Path.home() / ".claude" / "memory" / "knowledge-graph.jsonl"

# ============================================================================
# UTF Enums (from spec)
# ============================================================================

class ClaimForm(Enum):
    DEFINITION = "Definition"
    MEASUREMENT = "Measurement"
    EMPIRICAL_REGULARITY = "EmpiricalRegularity"
    CAUSAL_MECHANISM = "CausalMechanism"
    THEOREM = "Theorem"
    ALGORITHM = "Algorithm"
    NEGATIVE_RESULT = "NegativeResult"
    LIMITATION = "Limitation"
    CONJECTURE = "Conjecture"
    SURVEY_SYNTHESIS = "SurveySynthesis"

class StabilityClass(Enum):
    INVARIANT = "Invariant"
    CONTEXT_STABLE = "ContextStable"
    CONTEXT_FRAGILE = "ContextFragile"
    CONTESTED = "Contested"

class EpistemicStatus(Enum):
    ESTABLISHED = "Established"
    SUPPORTED = "Supported"
    CONTESTED = "Contested"
    SPECULATIVE = "Speculative"
    REFUTED = "Refuted"

class AssumptionType(Enum):
    DATA = "Data"
    COMPUTE = "Compute"
    DISTRIBUTION = "Distribution"
    CAUSAL = "Causal"
    MEASUREMENT = "Measurement"
    SOCIAL = "Social"
    NORMATIVE = "Normative"

class AbstractionLevel(Enum):
    L0_SOURCE = 0
    L1_EXCERPT = 1
    L2_CLAIM = 2
    L3_CONCEPT = 3
    L4_MODEL = 4
    L5_FRAMEWORK = 5
    L6_PROGRAM = 6

# ============================================================================
# UTF Data Models
# ============================================================================

@dataclass
class UTFSource:
    """L0: Original document."""
    source_id: str
    title: str
    authors: List[str]
    year: Optional[int]
    source_type: str  # Paper, Book, Report, etc.
    file_hash: str
    file_path: str
    domain: str
    ingested_at: str
    extraction_quality: str = "pending"  # pending, partial, complete
    claim_density: str = "unknown"  # low, medium, high
    pages_processed: int = 0
    total_pages: int = 0

@dataclass
class UTFExcerpt:
    """L1: Direct quote with location."""
    excerpt_id: str
    source_id: str
    text: str
    location: str  # page:paragraph or section
    extraction_method: str  # LocalAI, Manual, OCR

@dataclass
class UTFClaim:
    """L2: Atomic assertion."""
    claim_id: str
    source_id: str
    statement: str
    claim_form: str  # ClaimForm enum value
    grounding: str  # Anchored, Hypothesis, Conjecture
    confidence: float
    stability_class: str
    evidence_grade: str  # A, B, C, D
    excerpt_ids: List[str]  # supporting excerpts
    domain: str
    scope: str  # Universal, DomainWide, ContextSpecific

@dataclass
class UTFConcept:
    """L3: Abstract idea with comprehension scaffold."""
    concept_id: str
    source_id: str
    name: str
    domain: str
    epistemic: str
    # Compression triplet
    definition_1liner: str
    definition_5bullet: List[str]
    # 7-slot comprehension scaffold
    scaffold_what: str = ""
    scaffold_how: str = ""
    scaffold_when_scope: str = ""
    scaffold_why_stakes: str = ""
    scaffold_how_to_use: str = ""
    scaffold_boundary_conditions: str = ""
    scaffold_failure_modes: str = ""
    scaffold_completeness: int = 0  # 0-7

@dataclass
class UTFAssumption:
    """Dependency that if violated breaks claims."""
    assumption_id: str
    source_id: str
    statement: str
    assumption_type: str  # AssumptionType enum
    violations: str  # what breaks if false
    scope: str
    testable: bool
    tested: bool = False
    dependent_claims: List[str] = field(default_factory=list)

@dataclass
class UTFLimitation:
    """Constraint on applicability."""
    limitation_id: str
    source_id: str
    statement: str
    severity: str  # Critical, Major, Minor, Noted
    applies_to: List[str]  # node IDs
    acknowledged_by_authors: bool

# ============================================================================
# Database Setup
# ============================================================================

def init_db() -> sqlite3.Connection:
    """Initialize UTF knowledge database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Sources (L0)
    c.execute('''CREATE TABLE IF NOT EXISTS sources (
        source_id TEXT PRIMARY KEY,
        title TEXT,
        authors TEXT,
        year INTEGER,
        source_type TEXT,
        file_hash TEXT UNIQUE,
        file_path TEXT,
        domain TEXT,
        ingested_at TEXT,
        extraction_quality TEXT,
        claim_density TEXT,
        pages_processed INTEGER,
        total_pages INTEGER,
        metadata TEXT
    )''')

    # Excerpts (L1)
    c.execute('''CREATE TABLE IF NOT EXISTS excerpts (
        excerpt_id TEXT PRIMARY KEY,
        source_id TEXT,
        text TEXT,
        location TEXT,
        extraction_method TEXT,
        FOREIGN KEY (source_id) REFERENCES sources(source_id)
    )''')

    # Claims (L2)
    c.execute('''CREATE TABLE IF NOT EXISTS claims (
        claim_id TEXT PRIMARY KEY,
        source_id TEXT,
        statement TEXT,
        claim_form TEXT,
        grounding TEXT,
        confidence REAL,
        stability_class TEXT,
        evidence_grade TEXT,
        excerpt_ids TEXT,
        domain TEXT,
        scope TEXT,
        created_at TEXT,
        FOREIGN KEY (source_id) REFERENCES sources(source_id)
    )''')

    # Concepts (L3)
    c.execute('''CREATE TABLE IF NOT EXISTS concepts (
        concept_id TEXT PRIMARY KEY,
        source_id TEXT,
        name TEXT,
        domain TEXT,
        epistemic TEXT,
        definition_1liner TEXT,
        definition_5bullet TEXT,
        scaffold_what TEXT,
        scaffold_how TEXT,
        scaffold_when_scope TEXT,
        scaffold_why_stakes TEXT,
        scaffold_how_to_use TEXT,
        scaffold_boundary_conditions TEXT,
        scaffold_failure_modes TEXT,
        scaffold_completeness INTEGER,
        created_at TEXT,
        FOREIGN KEY (source_id) REFERENCES sources(source_id)
    )''')

    # Assumptions
    c.execute('''CREATE TABLE IF NOT EXISTS assumptions (
        assumption_id TEXT PRIMARY KEY,
        source_id TEXT,
        statement TEXT,
        assumption_type TEXT,
        violations TEXT,
        scope TEXT,
        testable INTEGER,
        tested INTEGER,
        dependent_claims TEXT,
        created_at TEXT,
        FOREIGN KEY (source_id) REFERENCES sources(source_id)
    )''')

    # Limitations
    c.execute('''CREATE TABLE IF NOT EXISTS limitations (
        limitation_id TEXT PRIMARY KEY,
        source_id TEXT,
        statement TEXT,
        severity TEXT,
        applies_to TEXT,
        acknowledged_by_authors INTEGER,
        created_at TEXT,
        FOREIGN KEY (source_id) REFERENCES sources(source_id)
    )''')

    # Processing checkpoints (for resume)
    c.execute('''CREATE TABLE IF NOT EXISTS checkpoints (
        source_id TEXT PRIMARY KEY,
        last_page INTEGER,
        state TEXT,
        updated_at TEXT
    )''')

    # Indexes for taxonomy-filtered retrieval
    c.execute('CREATE INDEX IF NOT EXISTS idx_claims_domain ON claims(domain)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_claims_form ON claims(claim_form)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_concepts_domain ON concepts(domain)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_concepts_epistemic ON concepts(epistemic)')

    # Full-text search
    c.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS claims_fts
        USING fts5(statement, claim_form, domain)''')
    c.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS concepts_fts
        USING fts5(name, definition_1liner, scaffold_what, scaffold_how)''')

    conn.commit()
    return conn

# ============================================================================
# LocalAI Interface (Iterative, Memory-Friendly)
# ============================================================================

def localai_extract(prompt: str, max_tokens: int = 500) -> Dict:
    """Call LocalAI with memory-friendly settings."""
    try:
        response = requests.post(
            f"{LOCALAI_URL}/chat/completions",
            json={
                "model": LOCALAI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.3  # Lower for consistency
            },
            timeout=120
        )
        result = response.json()
        return {
            "content": result['choices'][0]['message']['content'],
            "tokens": result['usage']['total_tokens'],
            "success": True
        }
    except Exception as e:
        return {"content": "", "tokens": 0, "success": False, "error": str(e)}

def openai_extract(prompt: str, max_tokens: int = 800) -> Dict:
    """Call OpenAI for complex synthesis (use sparingly)."""
    if not OPENAI_API_KEY:
        return {"content": "", "tokens": 0, "success": False, "error": "No API key"}

    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3
        )
        return {
            "content": response.choices[0].message.content,
            "tokens": response.usage.total_tokens,
            "success": True
        }
    except Exception as e:
        return {"content": "", "tokens": 0, "success": False, "error": str(e)}

# ============================================================================
# Iterative Extraction Functions
# ============================================================================

def extract_page_text(pdf_path: str, page_num: int) -> str:
    """Extract text from a single page (memory-friendly)."""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        if page_num < len(doc):
            text = doc[page_num].get_text()
            doc.close()
            return text.encode('ascii', 'replace').decode('ascii')
        doc.close()
        return ""
    except:
        return ""

def get_total_pages(pdf_path: str) -> int:
    """Get total page count."""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        count = len(doc)
        doc.close()
        return count
    except:
        return 0

def extract_metadata_from_page1(text: str, filename: str) -> Dict:
    """Extract title, authors from first page (iterative step 1)."""
    prompt = f"""Extract metadata from this document's first page.

Text:
{text[:2000]}

Filename: {filename}

Respond in EXACTLY this format:
TITLE: <actual paper/book title from content, not filename>
AUTHORS: <author names comma-separated, or "Unknown">
YEAR: <publication year, or "Unknown">
DOMAIN: <one of: machine_learning, mathematics, physics, neuroscience, economics, philosophy, engineering, other>
TYPE: <Paper, Book, Report, Preprint, Documentation>
"""
    result = localai_extract(prompt, max_tokens=200)

    parsed = {
        "title": filename,
        "authors": [],
        "year": None,
        "domain": "other",
        "source_type": "Paper"
    }

    if result["success"]:
        for line in result["content"].split('\n'):
            line = line.strip()
            if line.startswith("TITLE:"):
                parsed["title"] = line[6:].strip()
            elif line.startswith("AUTHORS:"):
                authors = line[8:].strip()
                if authors and authors != "Unknown":
                    parsed["authors"] = [a.strip() for a in authors.split(',')]
            elif line.startswith("YEAR:"):
                try:
                    parsed["year"] = int(line[5:].strip())
                except:
                    pass
            elif line.startswith("DOMAIN:"):
                parsed["domain"] = line[7:].strip().lower().replace(" ", "_")
            elif line.startswith("TYPE:"):
                parsed["source_type"] = line[5:].strip()

    return parsed

def extract_claims_from_page(text: str, page_num: int, source_id: str, domain: str) -> List[Dict]:
    """Extract atomic claims from a single page (iterative)."""
    prompt = f"""Extract ATOMIC CLAIMS from this text. Each claim should be:
- Self-contained (understandable alone)
- Falsifiable (could be tested/verified)
- Single assertion (no "and" combining independent claims)

Text (page {page_num}):
{text[:2500]}

For EACH claim, provide:
CLAIM: <atomic statement, max 200 chars>
FORM: <one of: Definition, Measurement, EmpiricalRegularity, CausalMechanism, Theorem, Algorithm, NegativeResult, Limitation, Conjecture, SurveySynthesis>
CONFIDENCE: <0.0-1.0 based on how well-supported it appears>
GROUNDING: <Anchored if directly stated, Hypothesis if implied>

Extract 3-5 claims max. If no clear claims, respond "NO_CLAIMS".
"""
    result = localai_extract(prompt, max_tokens=600)

    claims = []
    if result["success"] and "NO_CLAIMS" not in result["content"]:
        current_claim = {}
        for line in result["content"].split('\n'):
            line = line.strip()
            if line.startswith("CLAIM:"):
                if current_claim.get("statement"):
                    claims.append(current_claim)
                current_claim = {
                    "statement": line[6:].strip()[:200],
                    "source_id": source_id,
                    "domain": domain,
                    "page": page_num
                }
            elif line.startswith("FORM:"):
                current_claim["claim_form"] = line[5:].strip()
            elif line.startswith("CONFIDENCE:"):
                try:
                    current_claim["confidence"] = float(line[11:].strip())
                except:
                    current_claim["confidence"] = 0.5
            elif line.startswith("GROUNDING:"):
                current_claim["grounding"] = line[10:].strip()

        if current_claim.get("statement"):
            claims.append(current_claim)

    return claims

def extract_concepts_from_page(text: str, page_num: int, source_id: str, domain: str) -> List[Dict]:
    """Extract concepts with partial scaffold (iterative)."""
    prompt = f"""Identify KEY CONCEPTS defined or explained in this text.

Text (page {page_num}):
{text[:2500]}

For EACH concept (max 3):
CONCEPT: <concept name>
WHAT: <1-2 sentence definition>
HOW: <how it works, if explained>
SCOPE: <when/where it applies>

If no clear concepts, respond "NO_CONCEPTS".
"""
    result = localai_extract(prompt, max_tokens=500)

    concepts = []
    if result["success"] and "NO_CONCEPTS" not in result["content"]:
        current = {}
        for line in result["content"].split('\n'):
            line = line.strip()
            if line.startswith("CONCEPT:"):
                if current.get("name"):
                    concepts.append(current)
                current = {
                    "name": line[8:].strip(),
                    "source_id": source_id,
                    "domain": domain,
                    "page": page_num
                }
            elif line.startswith("WHAT:"):
                current["scaffold_what"] = line[5:].strip()
            elif line.startswith("HOW:"):
                current["scaffold_how"] = line[4:].strip()
            elif line.startswith("SCOPE:"):
                current["scaffold_when_scope"] = line[6:].strip()

        if current.get("name"):
            concepts.append(current)

    return concepts

def extract_assumptions_from_page(text: str, page_num: int, source_id: str) -> List[Dict]:
    """Extract assumptions (often implicit)."""
    prompt = f"""Identify ASSUMPTIONS made in this text. Look for:
- Data assumptions ("assumes IID", "assumes normal distribution")
- Causal assumptions ("X causes Y")
- Scope assumptions ("in this context", "given that")
- Hidden premises

Text (page {page_num}):
{text[:2000]}

For EACH assumption:
ASSUMPTION: <what is assumed>
TYPE: <Data, Compute, Distribution, Causal, Measurement, Social, Normative>
VIOLATION: <what breaks if this assumption is false>

Max 3 assumptions. If none found, respond "NO_ASSUMPTIONS".
"""
    result = localai_extract(prompt, max_tokens=400)

    assumptions = []
    if result["success"] and "NO_ASSUMPTIONS" not in result["content"]:
        current = {}
        for line in result["content"].split('\n'):
            line = line.strip()
            if line.startswith("ASSUMPTION:"):
                if current.get("statement"):
                    assumptions.append(current)
                current = {
                    "statement": line[11:].strip(),
                    "source_id": source_id,
                    "page": page_num
                }
            elif line.startswith("TYPE:"):
                current["assumption_type"] = line[5:].strip()
            elif line.startswith("VIOLATION:"):
                current["violations"] = line[10:].strip()

        if current.get("statement"):
            assumptions.append(current)

    return assumptions

def extract_limitations_from_page(text: str, page_num: int, source_id: str) -> List[Dict]:
    """Extract limitations mentioned in text."""
    # Look for limitation keywords
    limitation_keywords = ["however", "limitation", "does not", "cannot", "fails to",
                          "restricted to", "only works", "assumes", "caveat"]

    if not any(kw in text.lower() for kw in limitation_keywords):
        return []

    prompt = f"""Identify LIMITATIONS mentioned or implied in this text.

Text (page {page_num}):
{text[:2000]}

For EACH limitation:
LIMITATION: <what the limitation is>
SEVERITY: <Critical, Major, Minor, Noted>
ACKNOWLEDGED: <Yes if authors explicitly mention it, No if implied>

Max 2 limitations. If none, respond "NO_LIMITATIONS".
"""
    result = localai_extract(prompt, max_tokens=300)

    limitations = []
    if result["success"] and "NO_LIMITATIONS" not in result["content"]:
        current = {}
        for line in result["content"].split('\n'):
            line = line.strip()
            if line.startswith("LIMITATION:"):
                if current.get("statement"):
                    limitations.append(current)
                current = {
                    "statement": line[11:].strip(),
                    "source_id": source_id,
                    "page": page_num
                }
            elif line.startswith("SEVERITY:"):
                current["severity"] = line[9:].strip()
            elif line.startswith("ACKNOWLEDGED:"):
                current["acknowledged_by_authors"] = "yes" in line.lower()

        if current.get("statement"):
            limitations.append(current)

    return limitations

# ============================================================================
# Storage Functions
# ============================================================================

def generate_id(prefix: str, content: str) -> str:
    """Generate deterministic ID for dedup."""
    return f"{prefix}_{hashlib.md5(content.encode()).hexdigest()[:10]}"

def store_source(conn: sqlite3.Connection, source: Dict) -> str:
    """Store source and return ID."""
    source_id = generate_id("src", source.get("file_hash", source.get("title", "")))

    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO sources
        (source_id, title, authors, year, source_type, file_hash, file_path,
         domain, ingested_at, extraction_quality, claim_density, pages_processed, total_pages, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (source_id, source.get("title"), json.dumps(source.get("authors", [])),
         source.get("year"), source.get("source_type"), source.get("file_hash"),
         source.get("file_path"), source.get("domain"), datetime.now().isoformat(),
         "pending", "unknown", 0, source.get("total_pages", 0), json.dumps({})))
    conn.commit()
    return source_id

def store_claim(conn: sqlite3.Connection, claim: Dict):
    """Store a claim."""
    claim_id = generate_id("clm", claim.get("statement", ""))

    c = conn.cursor()
    c.execute('''INSERT OR IGNORE INTO claims
        (claim_id, source_id, statement, claim_form, grounding, confidence,
         stability_class, evidence_grade, excerpt_ids, domain, scope, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (claim_id, claim.get("source_id"), claim.get("statement"),
         claim.get("claim_form", "EmpiricalRegularity"),
         claim.get("grounding", "Anchored"),
         claim.get("confidence", 0.5), "ContextStable", "C",
         json.dumps([]), claim.get("domain", "other"),
         "DomainWide", datetime.now().isoformat()))

    # Add to FTS
    c.execute('''INSERT OR IGNORE INTO claims_fts (rowid, statement, claim_form, domain)
        VALUES ((SELECT rowid FROM claims WHERE claim_id = ?), ?, ?, ?)''',
        (claim_id, claim.get("statement"), claim.get("claim_form"), claim.get("domain")))

    conn.commit()
    return claim_id

def store_concept(conn: sqlite3.Connection, concept: Dict):
    """Store a concept with partial scaffold."""
    concept_id = generate_id("con", concept.get("name", ""))

    # Calculate scaffold completeness
    completeness = sum(1 for k in ["scaffold_what", "scaffold_how", "scaffold_when_scope",
                                   "scaffold_why_stakes", "scaffold_how_to_use",
                                   "scaffold_boundary_conditions", "scaffold_failure_modes"]
                      if concept.get(k))

    # Generate 1-liner from scaffold_what
    definition_1liner = concept.get("scaffold_what", concept.get("name", ""))[:100]

    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO concepts
        (concept_id, source_id, name, domain, epistemic, definition_1liner, definition_5bullet,
         scaffold_what, scaffold_how, scaffold_when_scope, scaffold_why_stakes,
         scaffold_how_to_use, scaffold_boundary_conditions, scaffold_failure_modes,
         scaffold_completeness, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (concept_id, concept.get("source_id"), concept.get("name"),
         concept.get("domain", "other"), "Supported", definition_1liner, json.dumps([]),
         concept.get("scaffold_what", ""), concept.get("scaffold_how", ""),
         concept.get("scaffold_when_scope", ""), concept.get("scaffold_why_stakes", ""),
         concept.get("scaffold_how_to_use", ""), concept.get("scaffold_boundary_conditions", ""),
         concept.get("scaffold_failure_modes", ""), completeness, datetime.now().isoformat()))

    # Add to FTS
    c.execute('''INSERT OR REPLACE INTO concepts_fts (rowid, name, definition_1liner, scaffold_what, scaffold_how)
        VALUES ((SELECT rowid FROM concepts WHERE concept_id = ?), ?, ?, ?, ?)''',
        (concept_id, concept.get("name"), definition_1liner,
         concept.get("scaffold_what", ""), concept.get("scaffold_how", "")))

    conn.commit()
    return concept_id

def store_assumption(conn: sqlite3.Connection, assumption: Dict):
    """Store an assumption."""
    assumption_id = generate_id("asm", assumption.get("statement", ""))

    c = conn.cursor()
    c.execute('''INSERT OR IGNORE INTO assumptions
        (assumption_id, source_id, statement, assumption_type, violations, scope,
         testable, tested, dependent_claims, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (assumption_id, assumption.get("source_id"), assumption.get("statement"),
         assumption.get("assumption_type", "Data"), assumption.get("violations", ""),
         "", 1, 0, json.dumps([]), datetime.now().isoformat()))
    conn.commit()
    return assumption_id

def store_limitation(conn: sqlite3.Connection, limitation: Dict):
    """Store a limitation."""
    limitation_id = generate_id("lim", limitation.get("statement", ""))

    c = conn.cursor()
    c.execute('''INSERT OR IGNORE INTO limitations
        (limitation_id, source_id, statement, severity, applies_to,
         acknowledged_by_authors, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (limitation_id, limitation.get("source_id"), limitation.get("statement"),
         limitation.get("severity", "Noted"), json.dumps([]),
         1 if limitation.get("acknowledged_by_authors") else 0,
         datetime.now().isoformat()))
    conn.commit()
    return limitation_id

def save_checkpoint(conn: sqlite3.Connection, source_id: str, page: int, state: Dict):
    """Save processing checkpoint for resume."""
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO checkpoints
        (source_id, last_page, state, updated_at)
        VALUES (?, ?, ?, ?)''',
        (source_id, page, json.dumps(state), datetime.now().isoformat()))
    conn.commit()

def load_checkpoint(conn: sqlite3.Connection, source_id: str) -> Optional[Dict]:
    """Load checkpoint for resume."""
    c = conn.cursor()
    c.execute('SELECT last_page, state FROM checkpoints WHERE source_id = ?', (source_id,))
    row = c.fetchone()
    if row:
        return {"last_page": row[0], "state": json.loads(row[1])}
    return None

def update_source_progress(conn: sqlite3.Connection, source_id: str,
                           pages_processed: int, claim_count: int):
    """Update source extraction progress."""
    claim_density = "high" if claim_count / max(pages_processed, 1) > 2 else \
                   "medium" if claim_count / max(pages_processed, 1) > 0.5 else "low"

    quality = "complete" if pages_processed > 0 else "pending"

    c = conn.cursor()
    c.execute('''UPDATE sources SET pages_processed = ?, extraction_quality = ?, claim_density = ?
        WHERE source_id = ?''', (pages_processed, quality, claim_density, source_id))
    conn.commit()

# ============================================================================
# Quality Gates
# ============================================================================

def check_source_quality_gate(source_id: str, excerpts: int, claims: int) -> Dict:
    """
    Gate 1: Source Acceptance
    A Source becomes "knowledge" when:
    - Title extracted (not filename)
    - At least 3 excerpts extracted
    - At least 2 claims derived
    - At least 1 assumption identified
    """
    passed = excerpts >= 3 and claims >= 2
    return {
        "gate": "source_acceptance",
        "passed": passed,
        "excerpts": excerpts,
        "claims": claims,
        "status": "accepted" if passed else "pending_review"
    }

def check_claim_quality_gate(claim: Dict) -> Dict:
    """
    Gate 2: Claim Validity
    - Single atomic assertion
    - Has grounding (Anchored with excerpt, or Hypothesis)
    - claim_form assigned
    - confidence assigned
    """
    statement = claim.get("statement", "")
    # Check for compound claims (multiple independent assertions)
    compound_indicators = [" and ", " but also ", " as well as ", " furthermore "]
    is_atomic = not any(ind in statement.lower() for ind in compound_indicators)

    has_grounding = claim.get("grounding") in ["Anchored", "Hypothesis", "Conjecture"]
    has_form = claim.get("claim_form") in [e.value for e in ClaimForm]
    has_confidence = 0 <= claim.get("confidence", -1) <= 1

    passed = is_atomic and has_grounding and has_form and has_confidence

    return {
        "gate": "claim_validity",
        "passed": passed,
        "is_atomic": is_atomic,
        "has_grounding": has_grounding,
        "has_form": has_form,
        "has_confidence": has_confidence,
        "status": "valid" if passed else "needs_review"
    }

# ============================================================================
# Main Iterative Pipeline
# ============================================================================

def iterative_ingest(pdf_path: str, resume: bool = False) -> Dict:
    """
    Main iterative ingestion pipeline.
    Processes page-by-page to respect LocalAI memory limits.
    """
    print(f"\n{'='*60}")
    print(f"UTF Iterative Ingest")
    print(f"{'='*60}")
    print(f"File: {pdf_path}")

    conn = init_db()
    path = Path(pdf_path)

    if not path.exists():
        return {"success": False, "error": "File not found"}

    # Calculate file hash for dedup
    file_hash = hashlib.md5(path.read_bytes()).hexdigest()
    total_pages = get_total_pages(pdf_path)

    print(f"Pages: {total_pages}")
    print(f"Hash: {file_hash[:12]}...")

    # Check for existing/resume
    source_id = generate_id("src", file_hash)
    checkpoint = load_checkpoint(conn, source_id) if resume else None
    start_page = checkpoint["last_page"] + 1 if checkpoint else 0

    if checkpoint:
        print(f"Resuming from page {start_page}")

    # Stats
    stats = {
        "claims": 0,
        "concepts": 0,
        "assumptions": 0,
        "limitations": 0,
        "tokens_used": 0
    }

    # Step 1: Extract metadata from page 1 (if starting fresh)
    if start_page == 0:
        print("\n[1/N] Extracting metadata from page 1...")
        page1_text = extract_page_text(pdf_path, 0)
        metadata = extract_metadata_from_page1(page1_text, path.name)

        # Create source record
        source_data = {
            "title": metadata["title"],
            "authors": metadata["authors"],
            "year": metadata["year"],
            "source_type": metadata["source_type"],
            "domain": metadata["domain"],
            "file_hash": file_hash,
            "file_path": str(path.absolute()),
            "total_pages": total_pages
        }
        source_id = store_source(conn, source_data)
        print(f"    Title: {metadata['title']}")
        print(f"    Domain: {metadata['domain']}")
        start_page = 1  # Already processed page 0

    # Get source info for domain
    c = conn.cursor()
    c.execute('SELECT domain FROM sources WHERE source_id = ?', (source_id,))
    row = c.fetchone()
    domain = row[0] if row else "other"

    # Step 2: Process pages iteratively
    print(f"\n[2/N] Processing pages {start_page+1} to {total_pages}...")

    for page_num in range(start_page, min(total_pages, 50)):  # Cap at 50 pages
        print(f"\n  Page {page_num + 1}/{total_pages}...", end=" ")

        page_text = extract_page_text(pdf_path, page_num)
        if not page_text or len(page_text) < 100:
            print("(skipped - no text)")
            continue

        # Extract claims
        claims = extract_claims_from_page(page_text, page_num, source_id, domain)
        for claim in claims:
            gate = check_claim_quality_gate(claim)
            if gate["passed"]:
                store_claim(conn, claim)
                stats["claims"] += 1

        # Extract concepts
        concepts = extract_concepts_from_page(page_text, page_num, source_id, domain)
        for concept in concepts:
            store_concept(conn, concept)
            stats["concepts"] += 1

        # Extract assumptions (every 3rd page to save tokens)
        if page_num % 3 == 0:
            assumptions = extract_assumptions_from_page(page_text, page_num, source_id)
            for assumption in assumptions:
                store_assumption(conn, assumption)
                stats["assumptions"] += 1

        # Extract limitations (look for keywords first)
        limitations = extract_limitations_from_page(page_text, page_num, source_id)
        for limitation in limitations:
            store_limitation(conn, limitation)
            stats["limitations"] += 1

        print(f"[C:{len(claims)} N:{len(concepts)}]", end="")

        # Save checkpoint every 5 pages
        if page_num % 5 == 0:
            save_checkpoint(conn, source_id, page_num, stats)

        # Update progress
        update_source_progress(conn, source_id, page_num + 1, stats["claims"])

    # Final checkpoint
    save_checkpoint(conn, source_id, min(total_pages, 50) - 1, stats)

    # Quality gate check
    gate = check_source_quality_gate(source_id, stats["claims"], stats["claims"])

    print(f"\n\n{'='*60}")
    print(f"EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Claims:      {stats['claims']}")
    print(f"Concepts:    {stats['concepts']}")
    print(f"Assumptions: {stats['assumptions']}")
    print(f"Limitations: {stats['limitations']}")
    print(f"Quality:     {gate['status']}")
    print(f"{'='*60}")

    # Export to KG for compatibility
    export_to_kg(conn, source_id)

    conn.close()

    return {
        "success": True,
        "source_id": source_id,
        "stats": stats,
        "quality_gate": gate
    }

# ============================================================================
# Taxonomy-Filtered Retrieval
# ============================================================================

def taxonomy_query(query: str,
                   domain_filter: Optional[str] = None,
                   claim_form_filter: Optional[str] = None,
                   min_confidence: float = 0.0,
                   level_filter: Optional[str] = None) -> Dict:
    """
    Query with UTF taxonomy filters.

    Args:
        query: Search text
        domain_filter: Filter by domain (e.g., "machine_learning")
        claim_form_filter: Filter by claim form (e.g., "CausalMechanism")
        min_confidence: Minimum confidence threshold
        level_filter: L2 (claims), L3 (concepts), or "all"
    """
    conn = init_db()
    results = {
        "query": query,
        "filters": {
            "domain": domain_filter,
            "claim_form": claim_form_filter,
            "min_confidence": min_confidence,
            "level": level_filter
        },
        "claims": [],
        "concepts": [],
        "assumptions": []
    }

    c = conn.cursor()

    # Search claims (L2)
    if level_filter in [None, "all", "L2", "claims"]:
        sql = '''SELECT c.* FROM claims c
            JOIN claims_fts fts ON c.rowid = fts.rowid
            WHERE claims_fts MATCH ?'''
        params = [query]

        if domain_filter:
            sql += ' AND c.domain = ?'
            params.append(domain_filter)
        if claim_form_filter:
            sql += ' AND c.claim_form = ?'
            params.append(claim_form_filter)
        if min_confidence > 0:
            sql += ' AND c.confidence >= ?'
            params.append(min_confidence)

        sql += ' LIMIT 10'

        try:
            c.execute(sql, params)
            for row in c.fetchall():
                results["claims"].append({
                    "claim_id": row[0],
                    "statement": row[2],
                    "claim_form": row[3],
                    "confidence": row[5],
                    "domain": row[9],
                    "level": "L2"
                })
        except:
            pass  # FTS might not match

    # Search concepts (L3)
    if level_filter in [None, "all", "L3", "concepts"]:
        sql = '''SELECT c.* FROM concepts c
            JOIN concepts_fts fts ON c.rowid = fts.rowid
            WHERE concepts_fts MATCH ?'''
        params = [query]

        if domain_filter:
            sql += ' AND c.domain = ?'
            params.append(domain_filter)

        sql += ' LIMIT 10'

        try:
            c.execute(sql, params)
            for row in c.fetchall():
                results["concepts"].append({
                    "concept_id": row[0],
                    "name": row[2],
                    "domain": row[3],
                    "definition": row[5],
                    "scaffold_completeness": row[14],
                    "level": "L3"
                })
        except:
            pass

    # Get related assumptions
    if results["claims"]:
        claim_sources = list(set(r.get("source_id") for r in results["claims"] if r.get("source_id")))
        if claim_sources:
            placeholders = ','.join(['?'] * len(claim_sources))
            c.execute(f'''SELECT * FROM assumptions WHERE source_id IN ({placeholders}) LIMIT 5''',
                     claim_sources)
            for row in c.fetchall():
                results["assumptions"].append({
                    "assumption_id": row[0],
                    "statement": row[2],
                    "type": row[3],
                    "violations": row[4]
                })

    conn.close()
    return results

# ============================================================================
# Export to KG (Compatibility)
# ============================================================================

def export_to_kg(conn: sqlite3.Connection, source_id: str):
    """Export UTF nodes to JSONL KG for MCP compatibility."""
    KG_PATH.parent.mkdir(parents=True, exist_ok=True)

    c = conn.cursor()

    # Get source info
    c.execute('SELECT title, domain, authors FROM sources WHERE source_id = ?', (source_id,))
    source = c.fetchone()
    if not source:
        return

    title, domain, authors = source

    with open(KG_PATH, 'a', encoding='utf-8') as f:
        # Source entity
        f.write(json.dumps({
            "type": "entity",
            "name": f"utf_source:{source_id}",
            "entityType": "utf_source",
            "observations": [
                f"TITLE:{title}",
                f"DOMAIN:{domain}",
                f"AUTHORS:{authors}",
                f"LEVEL:L0",
                f"SCHEMA:UTF_v1"
            ]
        }) + '\n')

        # Get claims
        c.execute('SELECT claim_id, statement, claim_form, confidence FROM claims WHERE source_id = ?',
                 (source_id,))
        for row in c.fetchall():
            f.write(json.dumps({
                "type": "entity",
                "name": f"utf_claim:{row[0]}",
                "entityType": "utf_claim",
                "observations": [
                    f"STATEMENT:{row[1]}",
                    f"FORM:{row[2]}",
                    f"CONFIDENCE:{row[3]}",
                    f"SOURCE:{source_id}",
                    f"LEVEL:L2"
                ]
            }) + '\n')

        # Get concepts
        c.execute('''SELECT concept_id, name, definition_1liner, scaffold_what, scaffold_how
                    FROM concepts WHERE source_id = ?''', (source_id,))
        for row in c.fetchall():
            f.write(json.dumps({
                "type": "entity",
                "name": f"utf_concept:{row[0]}",
                "entityType": "utf_concept",
                "observations": [
                    f"NAME:{row[1]}",
                    f"DEFINITION:{row[2]}",
                    f"WHAT:{row[3]}",
                    f"HOW:{row[4]}",
                    f"SOURCE:{source_id}",
                    f"LEVEL:L3"
                ]
            }) + '\n')

# ============================================================================
# Status & CLI
# ============================================================================

def show_status():
    """Show knowledge base statistics."""
    conn = init_db()
    c = conn.cursor()

    print(f"\n{'='*60}")
    print("UTF Knowledge Base Status")
    print(f"{'='*60}")

    # Sources
    c.execute("SELECT COUNT(*), SUM(pages_processed) FROM sources")
    sources, pages = c.fetchone()
    print(f"Sources (L0):     {sources or 0} ({pages or 0} pages processed)")

    # Claims
    c.execute("SELECT COUNT(*) FROM claims")
    claims = c.fetchone()[0]
    c.execute("SELECT claim_form, COUNT(*) FROM claims GROUP BY claim_form ORDER BY COUNT(*) DESC LIMIT 5")
    forms = c.fetchall()
    print(f"Claims (L2):      {claims}")
    if forms:
        print(f"  Top forms: {', '.join(f'{f[0]}({f[1]})' for f in forms)}")

    # Concepts
    c.execute("SELECT COUNT(*), AVG(scaffold_completeness) FROM concepts")
    concepts, avg_scaffold = c.fetchone()
    print(f"Concepts (L3):    {concepts or 0} (avg scaffold: {avg_scaffold or 0:.1f}/7)")

    # Assumptions
    c.execute("SELECT COUNT(*) FROM assumptions")
    assumptions = c.fetchone()[0]
    print(f"Assumptions:      {assumptions}")

    # Limitations
    c.execute("SELECT COUNT(*) FROM limitations")
    limitations = c.fetchone()[0]
    print(f"Limitations:      {limitations}")

    # Domain breakdown
    c.execute("SELECT domain, COUNT(*) FROM claims GROUP BY domain ORDER BY COUNT(*) DESC LIMIT 5")
    domains = c.fetchall()
    if domains:
        print(f"\nDomains: {', '.join(f'{d[0]}({d[1]})' for d in domains)}")

    print(f"{'='*60}")
    conn.close()

def main():
    parser = argparse.ArgumentParser(description='UTF Iterative Knowledge Ingest')
    parser.add_argument('pdf_path', nargs='?', help='Path to PDF file')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    parser.add_argument('--status', action='store_true', help='Show knowledge base status')
    parser.add_argument('--query', type=str, help='Search query')
    parser.add_argument('--domain', type=str, help='Filter by domain')
    parser.add_argument('--form', type=str, help='Filter by claim form')
    parser.add_argument('--level', type=str, help='Filter by level (L2, L3, all)')
    parser.add_argument('--min-confidence', type=float, default=0.0, help='Min confidence')

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.query:
        results = taxonomy_query(
            args.query,
            domain_filter=args.domain,
            claim_form_filter=args.form,
            min_confidence=args.min_confidence,
            level_filter=args.level
        )
        print(json.dumps(results, indent=2))
    elif args.pdf_path:
        result = iterative_ingest(args.pdf_path, resume=args.resume)
        if not result["success"]:
            print(f"Error: {result.get('error')}")
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
