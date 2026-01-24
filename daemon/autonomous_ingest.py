#!/usr/bin/env python3
"""
Autonomous Book Ingestion - Enhanced with HiRAG + LeanRAG + MarkItDown

Integrates:
1. MarkItDown - Structure-preserving document conversion (Microsoft)
2. LeanRAG pattern - Semantic aggregation (entities → clusters → summary nodes)
3. HiRAG pattern - Hierarchical knowledge (local → bridge → global)
4. gpt_academic patterns - Academic paper extraction (title, abstract, methods, findings)

Cost: $0 (LocalAI only)

Usage:
    python autonomous_ingest.py                # Process once
    python autonomous_ingest.py --watch        # Continuous monitoring
    python autonomous_ingest.py --status       # Show processed files
    python autonomous_ingest.py --query "X"    # Hierarchical retrieval (HiRAG)
"""

import os
import sys
import json
import time
import hashlib
import sqlite3
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict

# MarkItDown for document conversion
try:
    from markitdown import MarkItDown
    MARKITDOWN_AVAILABLE = True
except ImportError:
    MARKITDOWN_AVAILABLE = False

# UTF Schema Extractor
try:
    from utf_extractor import extract_utf_schema, export_to_obsidian, UTFExtractionResult
    UTF_AVAILABLE = True
except ImportError:
    UTF_AVAILABLE = False

# Fallback to PyMuPDF
try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# Configuration
WATCH_FOLDER = Path(os.environ.get("BOOK_WATCH_FOLDER", str(Path.home() / "Documents" / "GateofTruth")))
LOCALAI_URL = os.environ.get("LOCALAI_URL", "http://localhost:8080/v1")
USE_UTF_SCHEMA = os.environ.get("USE_UTF_SCHEMA", "true").lower() == "true"
OBSIDIAN_VAULT = Path(os.environ.get("OBSIDIAN_VAULT", str(Path.home() / "Documents" / "Obsidian" / "ClaudeKnowledge")))
LOCALAI_MODEL = "mistral-7b-instruct-v0.3"
KG_PATH = Path.home() / ".claude" / "memory" / "knowledge-graph.jsonl"
DB_PATH = Path(__file__).parent / "ingest.db"

SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.md', '.docx', '.pptx', '.html', '.epub'}

# Telegram notifications
try:
    from telegram_notify import notify, notify_progress, notify_complete, notify_error, notify_localai_summary
    TELEGRAM_ENABLED = True
except ImportError:
    TELEGRAM_ENABLED = False
    def notify(*args, **kwargs): pass
    def notify_progress(*args, **kwargs): pass
    def notify_complete(*args, **kwargs): pass
    def notify_error(*args, **kwargs): pass
    def notify_localai_summary(*args, **kwargs): pass

# ============================================================================
# LeanRAG: Knowledge Structures (Semantic Aggregation)
# ============================================================================

@dataclass
class LocalKnowledge:
    """Fine-grained facts from specific text segments."""
    fact_id: str
    content: str
    source_chunk: int
    confidence: float
    keywords: List[str]

@dataclass
class BridgeKnowledge:
    """Connections between local facts."""
    from_fact: str
    to_fact: str
    relationship: str
    strength: float

@dataclass
class GlobalKnowledge:
    """High-level summaries and cross-document patterns."""
    concept: str
    summary: str
    supporting_facts: List[str]
    abstraction_level: int  # 1=section, 2=chapter, 3=document, 4=cross-doc

@dataclass
class HierarchicalKG:
    """LeanRAG + HiRAG combined structure."""
    document_id: str
    local: List[LocalKnowledge]
    bridges: List[BridgeKnowledge]
    globals: List[GlobalKnowledge]
    metadata: Dict[str, Any]


# ============================================================================
# Database
# ============================================================================

def init_db() -> sqlite3.Connection:
    """Initialize tracking database with hierarchical schema."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # File tracking
    c.execute('''CREATE TABLE IF NOT EXISTS processed_files (
        file_hash TEXT PRIMARY KEY,
        file_path TEXT,
        file_name TEXT,
        processed_at TEXT,
        token_cost INTEGER,
        status TEXT
    )''')

    # LeanRAG: Local knowledge (fine-grained facts)
    c.execute('''CREATE TABLE IF NOT EXISTS local_knowledge (
        id TEXT PRIMARY KEY,
        document_id TEXT,
        chunk_index INTEGER,
        content TEXT,
        keywords TEXT,
        confidence REAL,
        created_at TEXT
    )''')

    # LeanRAG: Bridge knowledge (relationships)
    c.execute('''CREATE TABLE IF NOT EXISTS bridge_knowledge (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_fact_id TEXT,
        to_fact_id TEXT,
        relationship TEXT,
        strength REAL,
        created_at TEXT
    )''')

    # HiRAG: Global knowledge (summaries at different abstraction levels)
    c.execute('''CREATE TABLE IF NOT EXISTS global_knowledge (
        id TEXT PRIMARY KEY,
        document_id TEXT,
        concept TEXT,
        summary TEXT,
        supporting_facts TEXT,
        abstraction_level INTEGER,
        created_at TEXT
    )''')

    # Indexes for hierarchical retrieval
    c.execute('CREATE INDEX IF NOT EXISTS idx_local_doc ON local_knowledge(document_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_global_level ON global_knowledge(abstraction_level)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_bridge_from ON bridge_knowledge(from_fact_id)')

    conn.commit()
    return conn


def file_hash(path: Path) -> str:
    """Compute file hash for deduplication."""
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def is_processed(conn: sqlite3.Connection, fhash: str) -> bool:
    """Check if file already processed."""
    c = conn.cursor()
    c.execute("SELECT 1 FROM processed_files WHERE file_hash = ?", (fhash,))
    return c.fetchone() is not None


# ============================================================================
# Document Extraction (MarkItDown preferred)
# ============================================================================

def extract_with_markitdown(path: Path) -> str:
    """Extract text using MarkItDown (structure-preserving)."""
    if not MARKITDOWN_AVAILABLE:
        return ""

    md = MarkItDown()
    result = md.convert(str(path))
    return result.text_content if result else ""


def extract_with_pymupdf(path: Path, max_pages: int = 30) -> str:
    """Fallback: Extract text using PyMuPDF."""
    if not PYMUPDF_AVAILABLE:
        return ""

    doc = fitz.open(path)
    text_parts = []
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        text_parts.append(page.get_text())
    doc.close()

    return '\n'.join(text_parts)


def extract_document(path: Path) -> str:
    """Extract document text using best available method."""
    ext = path.suffix.lower()

    # Try MarkItDown first (better structure preservation)
    if MARKITDOWN_AVAILABLE and ext in {'.pdf', '.docx', '.pptx', '.html', '.epub'}:
        text = extract_with_markitdown(path)
        if text:
            return text.encode('ascii', 'replace').decode('ascii')

    # Fallback to PyMuPDF for PDFs
    if ext == '.pdf' and PYMUPDF_AVAILABLE:
        text = extract_with_pymupdf(path)
        if text:
            return text.encode('ascii', 'replace').decode('ascii')

    # Plain text files
    if ext in {'.txt', '.md'}:
        return path.read_text(encoding='utf-8', errors='replace')

    return ""


# ============================================================================
# gpt_academic Pattern: Academic Paper Extraction
# ============================================================================

def extract_academic_structure(text: str, filename: str) -> Dict:
    """Extract academic paper structure using LocalAI."""
    prompt = f"""Analyze this academic paper and extract structured information.

Document: {filename}
Content (first 5000 chars):
{text[:5000]}

Extract in this EXACT format:
TITLE: <paper title>
AUTHORS: <author names, comma-separated>
ABSTRACT: <paper abstract or summary>
PROBLEM: <what problem does this solve?>
METHOD: <key methodology or approach>
FINDINGS: <main results or conclusions>
CONTRIBUTIONS: <novel contributions, comma-separated>
LIMITATIONS: <acknowledged limitations>
FUTURE_WORK: <suggested future directions>
DOMAIN: <research domain: ML, NLP, CV, systems, theory, etc.>
"""

    try:
        response = requests.post(
            f"{LOCALAI_URL}/chat/completions",
            json={
                "model": LOCALAI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 800
            },
            timeout=180
        )

        result = response.json()
        content = result['choices'][0]['message']['content']
        tokens = result['usage']['total_tokens']

        return {"raw": content, "tokens": tokens, "success": True}
    except Exception as e:
        return {"raw": "", "tokens": 0, "success": False, "error": str(e)}


# ============================================================================
# LeanRAG: Semantic Chunking + Aggregation
# ============================================================================

def semantic_chunk(text: str, chunk_size: int = 1500) -> List[Dict]:
    """Split text into semantic chunks (paragraph-aware)."""
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    current_index = 0

    for para in paragraphs:
        if len(current_chunk) + len(para) > chunk_size and current_chunk:
            chunks.append({
                "index": current_index,
                "content": current_chunk.strip()
            })
            current_index += 1
            current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para

    if current_chunk.strip():
        chunks.append({
            "index": current_index,
            "content": current_chunk.strip()
        })

    return chunks


def extract_local_knowledge(chunk: Dict, doc_id: str) -> Dict:
    """Extract fine-grained facts from a chunk using LocalAI."""
    prompt = f"""Extract atomic facts from this text chunk. Each fact should be:
- Self-contained (understandable without context)
- Specific (not vague)
- Attributable (could be verified)

Text:
{chunk['content'][:2000]}

Format each fact on a new line:
FACT: <atomic fact>
FACT: <atomic fact>
...
KEYWORDS: <relevant keywords for this chunk, comma-separated>
"""

    try:
        response = requests.post(
            f"{LOCALAI_URL}/chat/completions",
            json={
                "model": LOCALAI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500
            },
            timeout=120
        )

        result = response.json()
        content = result['choices'][0]['message']['content']
        tokens = result['usage']['total_tokens']

        # Parse facts
        facts = []
        keywords = []
        for line in content.split('\n'):
            line = line.strip()
            if line.upper().startswith('FACT:'):
                facts.append(line[5:].strip())
            elif line.upper().startswith('KEYWORDS:'):
                keywords = [k.strip() for k in line[9:].split(',')]

        return {
            "facts": facts,
            "keywords": keywords,
            "tokens": tokens,
            "chunk_index": chunk['index']
        }
    except Exception as e:
        return {"facts": [], "keywords": [], "tokens": 0, "error": str(e)}


def aggregate_to_global(local_facts: List[Dict], doc_id: str, level: int = 1) -> Dict:
    """LeanRAG: Aggregate local facts into global summary."""
    # Collect all facts
    all_facts = []
    for lf in local_facts:
        all_facts.extend(lf.get('facts', []))

    if not all_facts:
        return {"summary": "", "tokens": 0}

    facts_text = '\n'.join(f"- {f}" for f in all_facts[:30])

    prompt = f"""These are extracted facts from a document. Create a HIGHER-LEVEL summary that:
1. Identifies the main themes
2. Synthesizes related facts
3. Captures the essential knowledge

Facts:
{facts_text}

Provide:
THEMES: <3-5 main themes, comma-separated>
SYNTHESIS: <2-3 paragraph summary that integrates the facts>
KEY_INSIGHT: <the single most important takeaway>
"""

    try:
        response = requests.post(
            f"{LOCALAI_URL}/chat/completions",
            json={
                "model": LOCALAI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 600
            },
            timeout=120
        )

        result = response.json()
        content = result['choices'][0]['message']['content']
        tokens = result['usage']['total_tokens']

        return {
            "summary": content,
            "tokens": tokens,
            "level": level,
            "fact_count": len(all_facts)
        }
    except Exception as e:
        return {"summary": "", "tokens": 0, "error": str(e)}


# ============================================================================
# HiRAG: Hierarchical Retrieval
# ============================================================================

def hirag_retrieve(query: str, conn: sqlite3.Connection,
                   complexity: str = "auto") -> Dict:
    """
    HiRAG-style hierarchical retrieval.

    complexity levels:
    - "simple": local facts only
    - "moderate": local + bridge
    - "complex": local + bridge + global
    - "auto": determine from query
    """

    # Determine complexity if auto
    if complexity == "auto":
        complex_indicators = ["how", "why", "explain", "compare", "relationship",
                            "impact", "significance", "implications"]
        if any(ind in query.lower() for ind in complex_indicators):
            complexity = "complex"
        elif len(query.split()) > 10:
            complexity = "moderate"
        else:
            complexity = "simple"

    results = {"query": query, "complexity": complexity, "local": [], "bridges": [], "global": []}

    c = conn.cursor()

    # Always get local facts (keyword match)
    query_terms = query.lower().split()
    for term in query_terms[:5]:  # Limit search terms
        c.execute("""
            SELECT id, content, keywords, document_id
            FROM local_knowledge
            WHERE keywords LIKE ? OR content LIKE ?
            LIMIT 10
        """, (f'%{term}%', f'%{term}%'))

        for row in c.fetchall():
            results["local"].append({
                "id": row[0],
                "content": row[1],
                "keywords": row[2],
                "document_id": row[3]
            })

    # Get bridges if moderate or complex
    if complexity in ["moderate", "complex"] and results["local"]:
        fact_ids = [f["id"] for f in results["local"][:5]]
        for fid in fact_ids:
            c.execute("""
                SELECT from_fact_id, to_fact_id, relationship
                FROM bridge_knowledge
                WHERE from_fact_id = ? OR to_fact_id = ?
            """, (fid, fid))

            for row in c.fetchall():
                results["bridges"].append({
                    "from": row[0],
                    "to": row[1],
                    "relationship": row[2]
                })

    # Get global summaries if complex
    if complexity == "complex":
        c.execute("""
            SELECT concept, summary, abstraction_level
            FROM global_knowledge
            ORDER BY abstraction_level DESC
            LIMIT 5
        """)

        for row in c.fetchall():
            results["global"].append({
                "concept": row[0],
                "summary": row[1],
                "level": row[2]
            })

    return results


# ============================================================================
# Storage: Combined KG + SQLite
# ============================================================================

def store_hierarchical(doc_id: str, filepath: str, academic: Dict,
                       local_facts: List[Dict], global_summary: Dict,
                       conn: sqlite3.Connection):
    """Store all hierarchical knowledge."""

    timestamp = datetime.now().isoformat()
    c = conn.cursor()

    # Store local facts
    for lf in local_facts:
        for i, fact in enumerate(lf.get('facts', [])):
            fact_id = f"{doc_id}_L{lf['chunk_index']}_{i}"
            c.execute("""
                INSERT OR REPLACE INTO local_knowledge
                (id, document_id, chunk_index, content, keywords, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (fact_id, doc_id, lf['chunk_index'], fact,
                  ','.join(lf.get('keywords', [])), 0.8, timestamp))

    # Store global summary
    if global_summary.get('summary'):
        global_id = f"{doc_id}_G{global_summary.get('level', 1)}"
        c.execute("""
            INSERT OR REPLACE INTO global_knowledge
            (id, document_id, concept, summary, supporting_facts, abstraction_level, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (global_id, doc_id, "document_summary", global_summary['summary'],
              json.dumps([]), global_summary.get('level', 1), timestamp))

    conn.commit()

    # Also store to JSONL KG for compatibility
    store_to_kg_jsonl(doc_id, filepath, academic, local_facts, global_summary)


def store_to_kg_jsonl(doc_id: str, filepath: str, academic: Dict,
                      local_facts: List[Dict], global_summary: Dict):
    """Store to JSONL KG for MCP compatibility."""
    KG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Parse academic structure
    parsed = {}
    if academic.get('raw'):
        for line in academic['raw'].split('\n'):
            line = line.strip()
            for field in ['TITLE', 'ABSTRACT', 'PROBLEM', 'METHOD', 'FINDINGS',
                         'CONTRIBUTIONS', 'DOMAIN', 'AUTHORS']:
                if line.upper().startswith(f'{field}:'):
                    parsed[field.lower()] = line[len(field)+1:].strip()

    # Create hierarchical entity (HiRAG structure)
    entity = {
        "type": "entity",
        "name": f"doc:{doc_id}",
        "entityType": "hierarchical_document",
        "observations": [
            f"TITLE:{parsed.get('title', doc_id)}",
            f"ABSTRACT:{parsed.get('abstract', '')}",
            f"PROBLEM:{parsed.get('problem', '')}",
            f"METHOD:{parsed.get('method', '')}",
            f"FINDINGS:{parsed.get('findings', '')}",
            f"CONTRIBUTIONS:{parsed.get('contributions', '')}",
            f"DOMAIN:{parsed.get('domain', 'unknown')}",
            f"GLOBAL_SUMMARY:{global_summary.get('summary', '')[:500]}",
            f"LOCAL_FACT_COUNT:{sum(len(lf.get('facts', [])) for lf in local_facts)}",
            f"PATH:{filepath}",
            f"INGESTED:{datetime.now().isoformat()}",
            f"SOURCE:hirag_leanrag_autonomous"
        ]
    }

    with open(KG_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entity) + '\n')


# ============================================================================
# Main Processing Pipeline
# ============================================================================

def process_document(path: Path, conn: sqlite3.Connection) -> Dict:
    """Full hierarchical processing pipeline."""
    print(f"  Processing: {path.name}")
    # Notification only on completion, not start

    doc_id = path.stem

    # 1. Extract document text (MarkItDown preferred)
    print("    [1/5] Extracting text...")
    text = extract_document(path)
    if not text or len(text) < 200:
        return {"success": False, "error": "No text extracted"}
    print(f"    Extracted {len(text)} chars (using {'MarkItDown' if MARKITDOWN_AVAILABLE else 'PyMuPDF'})")

    # Use UTF Schema extraction if enabled and available
    if USE_UTF_SCHEMA and UTF_AVAILABLE:
        return process_document_utf(path, text, conn)
    else:
        return process_document_legacy(path, text, conn)


def process_document_utf(path: Path, text: str, conn: sqlite3.Connection) -> Dict:
    """Process document using UTF Research OS schema."""
    print("    [UTF MODE] Using UTF Research OS extraction...")

    fhash = file_hash(path)

    # Run UTF extraction
    result = extract_utf_schema(text, fhash)

    # Export to Obsidian vault
    if OBSIDIAN_VAULT.exists():
        export_to_obsidian(result, OBSIDIAN_VAULT)
        print(f"    [UTF] Exported to Obsidian: {OBSIDIAN_VAULT}")

    # Store to Knowledge Graph
    store_utf_to_kg(result)

    # Record processed
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO processed_files
        (file_hash, file_path, file_name, processed_at, token_cost, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (fhash, str(path), path.name, datetime.now().isoformat(), 0, 'completed'))
    conn.commit()

    stats = result.extraction_stats
    print(f"    [OK] UTF extraction: {stats['claims']} claims, {stats['concepts']} concepts")

    # Send completion notification
    notify_complete(f"UTF Ingested: {path.name}", {
        "title": result.source.title,
        "claims": stats['claims'],
        "concepts": stats['concepts'],
        "quality": "PASSED" if result.quality_gate_passed else "REVIEW"
    })

    return {
        "success": True,
        "doc_id": result.source.source_id,
        "title": result.source.title,
        "claims": stats['claims'],
        "concepts": stats['concepts'],
        "quality_gate": result.quality_gate_passed
    }


def store_utf_to_kg(result: 'UTFExtractionResult'):
    """Store UTF extraction result to knowledge graph."""
    import json
    from dataclasses import asdict

    # Store source
    source_entity = {
        "name": result.source.title,
        "entityType": "Source",
        "observations": [
            f"Authors: {', '.join(result.source.authors)}",
            f"Year: {result.source.year}",
            f"Domain: {result.source.domain}",
            f"Abstract: {result.source.abstract[:500] if result.source.abstract else 'N/A'}",
            f"Quality: {result.source.quality_status}",
            f"SOURCE_ID:{result.source.source_id}"
        ]
    }

    with open(KG_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(source_entity) + '\n')

        # Store claims
        for claim in result.claims:
            claim_entity = {
                "name": f"Claim: {claim.statement[:50]}...",
                "entityType": "Claim",
                "observations": [
                    f"Statement: {claim.statement}",
                    f"Form: {claim.claim_form}",
                    f"Grounding: {claim.grounding}",
                    f"Confidence: {claim.confidence}",
                    f"SOURCE_ID:{claim.source_id}",
                    f"CLAIM_ID:{claim.claim_id}"
                ]
            }
            f.write(json.dumps(claim_entity) + '\n')

        # Store concepts
        for concept in result.concepts:
            concept_entity = {
                "name": concept.name,
                "entityType": "Concept",
                "observations": [
                    f"Definition: {concept.definition_1liner}",
                    f"Domain: {concept.domain}",
                    f"CONCEPT_ID:{concept.concept_id}"
                ]
            }
            f.write(json.dumps(concept_entity) + '\n')

        # Store assumptions
        for assumption in result.assumptions:
            assumption_entity = {
                "name": f"Assumption: {assumption.statement[:40]}...",
                "entityType": "Assumption",
                "observations": [
                    f"Statement: {assumption.statement}",
                    f"Type: {assumption.assumption_type}",
                    f"Violations: {assumption.violations}",
                    f"ASSUMPTION_ID:{assumption.assumption_id}"
                ]
            }
            f.write(json.dumps(assumption_entity) + '\n')


def process_document_legacy(path: Path, text: str, conn: sqlite3.Connection) -> Dict:
    """Legacy HiRAG/LeanRAG processing pipeline."""
    doc_id = path.stem
    total_tokens = 0

    # 2. Academic structure extraction (gpt_academic pattern)
    print("    [2/5] Extracting academic structure...")
    academic = extract_academic_structure(text, path.name)
    total_tokens += academic.get('tokens', 0)
    if academic.get('success'):
        print(f"    Academic extraction: {academic['tokens']} tokens")

    # 3. Semantic chunking (LeanRAG)
    print("    [3/5] Semantic chunking...")
    chunks = semantic_chunk(text)
    print(f"    Created {len(chunks)} chunks")

    # 4. Local knowledge extraction (LeanRAG)
    print("    [4/5] Extracting local knowledge...")
    local_facts = []
    for chunk in chunks[:10]:  # Limit to first 10 chunks for speed
        lf = extract_local_knowledge(chunk, doc_id)
        local_facts.append(lf)
        total_tokens += lf.get('tokens', 0)

    total_facts = sum(len(lf.get('facts', [])) for lf in local_facts)
    print(f"    Extracted {total_facts} local facts")

    # 5. Global aggregation (LeanRAG + HiRAG)
    print("    [5/5] Aggregating to global summary...")
    global_summary = aggregate_to_global(local_facts, doc_id, level=3)
    total_tokens += global_summary.get('tokens', 0)
    print(f"    Global summary created")

    # Store everything
    store_hierarchical(doc_id, str(path), academic, local_facts, global_summary, conn)

    # Record processed
    fhash = file_hash(path)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO processed_files
        (file_hash, file_path, file_name, processed_at, token_cost, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (fhash, str(path), path.name, datetime.now().isoformat(), total_tokens, 'completed'))
    conn.commit()

    print(f"    [OK] Total tokens: {total_tokens} (FREE via LocalAI)")

    # Send completion notification with summary
    notify_complete(f"Ingested: {path.name}", {
        "facts": total_facts,
        "chunks": len(chunks),
        "tokens": total_tokens
    })

    # Send LocalAI summary to Telegram
    if global_summary.get('summary'):
        notify_localai_summary(path.name, global_summary['summary'][:1000])

    return {
        "success": True,
        "doc_id": doc_id,
        "tokens": total_tokens,
        "facts": total_facts,
        "chunks": len(chunks)
    }


def check_localai() -> bool:
    """Check if LocalAI is available."""
    try:
        r = requests.get(f"{LOCALAI_URL.replace('/v1', '')}/readyz", timeout=5)
        return r.status_code == 200
    except:
        return False


def scan_folder(conn: sqlite3.Connection) -> List[Path]:
    """Scan folder for new files."""
    if not WATCH_FOLDER.exists():
        WATCH_FOLDER.mkdir(parents=True)
        return []

    new_files = []
    for path in WATCH_FOLDER.iterdir():
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            fhash = file_hash(path)
            if not is_processed(conn, fhash):
                new_files.append(path)

    return new_files


def run_ingest(watch: bool = False, interval: int = 300):
    """Run the autonomous ingestion."""
    print("=" * 60)
    print("Autonomous Ingestion (HiRAG + LeanRAG + MarkItDown)")
    print("=" * 60)
    print(f"Watch folder: {WATCH_FOLDER}")
    print(f"LocalAI URL: {LOCALAI_URL}")
    print(f"MarkItDown: {'Available' if MARKITDOWN_AVAILABLE else 'Not installed'}")
    print(f"PyMuPDF: {'Available' if PYMUPDF_AVAILABLE else 'Not installed'}")
    print()

    if not check_localai():
        print("[ERROR] LocalAI not available")
        return

    print("[OK] LocalAI connected")

    conn = init_db()

    while True:
        new_files = scan_folder(conn)

        if new_files:
            print(f"\nFound {len(new_files)} new file(s)")
            for path in new_files:
                try:
                    result = process_document(path, conn)
                    if result.get('success'):
                        print(f"    Stored: {result['facts']} facts, {result['chunks']} chunks")
                except Exception as e:
                    print(f"    [ERR] {e}")

        if not watch:
            print("\nDone. Use --watch for continuous monitoring.")
            break

        print(f"\nSleeping {interval}s...")
        time.sleep(interval)

    conn.close()


def run_query(query: str):
    """Run HiRAG hierarchical retrieval."""
    print(f"\n[HiRAG QUERY] {query}")
    print("=" * 50)

    conn = init_db()
    results = hirag_retrieve(query, conn)
    conn.close()

    print(f"Complexity: {results['complexity']}")

    if results['local']:
        print(f"\n[LOCAL FACTS] ({len(results['local'])} found)")
        for f in results['local'][:5]:
            print(f"  - {f['content'][:100]}...")

    if results['bridges']:
        print(f"\n[BRIDGES] ({len(results['bridges'])} found)")
        for b in results['bridges'][:3]:
            print(f"  {b['from']} --{b['relationship']}--> {b['to']}")

    if results['global']:
        print(f"\n[GLOBAL SUMMARIES] ({len(results['global'])} found)")
        for g in results['global'][:2]:
            print(f"  [{g['level']}] {g['summary'][:200]}...")


def show_status():
    """Show processed files and knowledge stats."""
    conn = init_db()
    c = conn.cursor()

    # File stats
    c.execute("SELECT COUNT(*), SUM(token_cost) FROM processed_files")
    files, tokens = c.fetchone()

    # Knowledge stats
    c.execute("SELECT COUNT(*) FROM local_knowledge")
    local_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM global_knowledge")
    global_count = c.fetchone()[0]

    conn.close()

    print("=" * 50)
    print("Knowledge Base Status")
    print("=" * 50)
    print(f"Documents processed: {files or 0}")
    print(f"Total tokens used: {tokens or 0} (FREE via LocalAI)")
    print(f"Local facts stored: {local_count}")
    print(f"Global summaries: {global_count}")
    print(f"\nHierarchy: Local ({local_count}) -> Global ({global_count})")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Autonomous Hierarchical Ingestion')
    parser.add_argument('--watch', action='store_true', help='Watch folder continuously')
    parser.add_argument('--interval', type=int, default=300, help='Check interval (seconds)')
    parser.add_argument('--status', action='store_true', help='Show knowledge base status')
    parser.add_argument('--query', type=str, help='HiRAG query')
    parser.add_argument('--reprocess', action='store_true', help='Reprocess all files')

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.query:
        run_query(args.query)
    else:
        run_ingest(watch=args.watch, interval=args.interval)
