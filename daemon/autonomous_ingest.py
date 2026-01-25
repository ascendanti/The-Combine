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

# MinerU for superior PDF extraction (Phase 14)
try:
    from magic_pdf.tools.common import do_parse
    import tempfile
    MINERU_AVAILABLE = True
except ImportError:
    MINERU_AVAILABLE = False

# Dragonfly/Redis cache (Phase 13.3)
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Configuration
WATCH_FOLDER = Path(os.environ.get("BOOK_WATCH_FOLDER", str(Path.home() / "Documents" / "GateofTruth")))
LOCALAI_URL = os.environ.get("LOCALAI_URL", "http://localhost:8080/v1")
USE_UTF_SCHEMA = os.environ.get("USE_UTF_SCHEMA", "true").lower() == "true"
OBSIDIAN_VAULT = Path(os.environ.get("OBSIDIAN_VAULT", str(Path.home() / "Documents" / "Obsidian" / "ClaudeKnowledge")))
LOCALAI_MODEL = "mistral-7b-instruct-v0.3"  # Phase 13.1: docker-compose now uses THREADS=10
DRAGONFLY_URL = os.environ.get("DRAGONFLY_URL", "redis://localhost:6379")
LLM_CACHE_TTL = 86400  # 24 hours for LLM response cache
KG_PATH = Path.home() / ".claude" / "memory" / "knowledge-graph.jsonl"
DB_PATH = Path(__file__).parent / "ingest.db"
UTF_DB_PATH = Path(__file__).parent / "utf_knowledge.db"

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
# Phase 13.3: Dragonfly LLM Response Cache
# ============================================================================

_dragonfly_client = None
_cache_stats = {"hits": 0, "misses": 0, "writes": 0}

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

def get_cache_stats() -> Dict:
    """Get cache efficiency statistics."""
    total = _cache_stats["hits"] + _cache_stats["misses"]
    hit_rate = (_cache_stats["hits"] / total * 100) if total > 0 else 0
    return {
        "hits": _cache_stats["hits"],
        "misses": _cache_stats["misses"],
        "writes": _cache_stats["writes"],
        "hit_rate": f"{hit_rate:.1f}%",
        "total_queries": total
    }

def cache_llm_response(prompt_hash: str, response: str, ttl: int = LLM_CACHE_TTL):
    """Cache LLM response in Dragonfly."""
    global _cache_stats
    client = get_dragonfly()
    if client:
        try:
            cache_key = f"llm:ingest:{prompt_hash}"
            client.setex(cache_key, ttl, json.dumps(response))
            _cache_stats["writes"] += 1
            return True
        except Exception:
            pass
    return False

def get_cached_llm_response(prompt_hash: str) -> Optional[Dict]:
    """Get cached LLM response from Dragonfly."""
    global _cache_stats
    client = get_dragonfly()
    if client:
        try:
            cache_key = f"llm:ingest:{prompt_hash}"
            result = client.get(cache_key)
            if result:
                _cache_stats["hits"] += 1
                return json.loads(result.decode())
            _cache_stats["misses"] += 1
        except Exception:
            _cache_stats["misses"] += 1
    else:
        _cache_stats["misses"] += 1
    return None

def make_prompt_hash(prompt: str, model: str = LOCALAI_MODEL) -> str:
    """Create deterministic hash for prompt caching."""
    key = f"{model}:{prompt[:1000]}"  # First 1000 chars for key
    return hashlib.sha256(key.encode()).hexdigest()[:16]

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
    """Check if file already successfully processed (not pending/failed)."""
    c = conn.cursor()
    c.execute("SELECT status FROM processed_files WHERE file_hash = ?", (fhash,))
    row = c.fetchone()
    # Only skip if status is 'completed' - reprocess pending/failed
    return row is not None and row[0] == 'completed'


# ============================================================================
# Document Extraction (MinerU > MarkItDown > PyMuPDF)
# ============================================================================

def extract_with_mineru(path: Path) -> str:
    """Extract PDF using MinerU (best for academic papers, tables, figures)."""
    if not MINERU_AVAILABLE:
        return ""

    try:
        # Read PDF bytes
        pdf_bytes = path.read_bytes()

        # Create temp output directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Use do_parse for extraction (auto method = automatic detection)
            try:
                do_parse(
                    output_dir=str(tmp_path),
                    pdf_file_name=path.stem,
                    pdf_bytes_or_dataset=pdf_bytes,
                    model_list=[],  # Empty = use defaults
                    parse_method="auto",  # Auto-detect text vs OCR
                    f_dump_md=True,
                    f_dump_middle_json=False,
                    f_dump_model_json=False,
                    f_dump_orig_pdf=False,
                    f_dump_content_list=False,
                    f_draw_span_bbox=False,
                    f_draw_layout_bbox=False,
                    f_make_md_mode="mm_markdown"
                )

                # Read the generated markdown
                md_file = tmp_path / "auto" / f"{path.stem}.md"
                if not md_file.exists():
                    # Try alternate paths
                    for subdir in ["txt", "ocr"]:
                        alt_file = tmp_path / subdir / f"{path.stem}.md"
                        if alt_file.exists():
                            md_file = alt_file
                            break

                if md_file.exists():
                    md_content = md_file.read_text(encoding='utf-8', errors='replace')
                    if md_content and len(md_content) > 100:
                        return md_content
            except Exception as e:
                print(f"    [MinerU] Parse error: {e}")

        return ""
    except Exception as e:
        print(f"    [MinerU] Extraction failed: {e}")
        return ""


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


def extract_document(path: Path) -> tuple[str, str]:
    """Extract document text using best available method.

    Priority for PDFs: MinerU > MarkItDown > PyMuPDF
    MinerU provides structured markdown with tables/figures preserved.

    Returns: (text, extraction_method)
    """
    ext = path.suffix.lower()

    # For PDFs: Try MinerU first (best for academic papers)
    if ext == '.pdf' and MINERU_AVAILABLE:
        text = extract_with_mineru(path)
        if text and len(text) > 200:
            return text.encode('ascii', 'replace').decode('ascii'), "MinerU"

    # Try MarkItDown for various formats
    if MARKITDOWN_AVAILABLE and ext in {'.pdf', '.docx', '.pptx', '.html', '.epub'}:
        text = extract_with_markitdown(path)
        if text:
            return text.encode('ascii', 'replace').decode('ascii'), "MarkItDown"

    # Fallback to PyMuPDF for PDFs
    if ext == '.pdf' and PYMUPDF_AVAILABLE:
        text = extract_with_pymupdf(path)
        if text:
            return text.encode('ascii', 'replace').decode('ascii'), "PyMuPDF"

    # Plain text files
    if ext in {'.txt', '.md'}:
        return path.read_text(encoding='utf-8', errors='replace'), "PlainText"

    return "", "None"


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

    # Phase 13.3: Check cache first
    prompt_hash = make_prompt_hash(prompt)
    cached = get_cached_llm_response(prompt_hash)
    if cached:
        return {"raw": cached.get("content", ""), "tokens": 0, "success": True, "cached": True}

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

        # Cache successful response
        cache_llm_response(prompt_hash, {"content": content, "tokens": tokens})

        return {"raw": content, "tokens": tokens, "success": True, "cached": False}
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

    # Phase 13.3: Check cache first
    prompt_hash = make_prompt_hash(prompt)
    cached = get_cached_llm_response(prompt_hash)
    if cached:
        content = cached.get("content", "")
        tokens = 0
    else:
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

            # Cache successful response
            cache_llm_response(prompt_hash, {"content": content, "tokens": tokens})
        except Exception as e:
            return {"facts": [], "keywords": [], "tokens": 0, "success": False}

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

    # Phase 13.3: Check cache first
    prompt_hash = make_prompt_hash(prompt)
    cached = get_cached_llm_response(prompt_hash)
    if cached:
        return {
            "summary": cached.get("content", ""),
            "tokens": 0,
            "level": level,
            "fact_count": len(all_facts),
            "cached": True
        }

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

        # Cache successful response
        cache_llm_response(prompt_hash, {"content": content, "tokens": tokens})

        return {
            "summary": content,
            "tokens": tokens,
            "level": level,
            "fact_count": len(all_facts),
            "cached": False
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

    # 1. Extract document text (MinerU > MarkItDown > PyMuPDF)
    print("    [1/5] Extracting text...")
    text, method = extract_document(path)
    if not text or len(text) < 200:
        return {"success": False, "error": "No text extracted"}
    print(f"    Extracted {len(text)} chars via {method}")

    # Use UTF Schema extraction if enabled and available
    if USE_UTF_SCHEMA and UTF_AVAILABLE:
        return process_document_utf(path, text, conn, method)
    else:
        return process_document_legacy(path, text, conn, method)


def process_document_utf(path: Path, text: str, conn: sqlite3.Connection, method: str = "Unknown") -> Dict:
    """Process document using UTF Research OS schema."""
    print(f"    [UTF MODE] Using UTF Research OS extraction (text via {method})...")

    fhash = file_hash(path)

    # Run UTF extraction
    result = extract_utf_schema(text, fhash)

    # Export to Obsidian vault
    if OBSIDIAN_VAULT.exists():
        export_to_obsidian(result, OBSIDIAN_VAULT)
        print(f"    [UTF] Exported to Obsidian: {OBSIDIAN_VAULT}")

    # Store to Knowledge Graph (JSON)
    store_utf_to_kg(result)

    # Store to SQLite for claim similarity
    store_utf_to_sqlite(result)

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
        "quality_gate": result.quality_gate_passed,
        "extraction_method": method
    }


def init_utf_db():
    """Initialize UTF knowledge SQLite database for claim similarity."""
    conn = sqlite3.connect(UTF_DB_PATH)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS sources (
        source_id TEXT PRIMARY KEY,
        title TEXT,
        authors TEXT,
        year INTEGER,
        domain TEXT,
        abstract TEXT,
        quality_status TEXT,
        created_at TEXT
    )''')

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
        slug_code TEXT,
        taxonomy_tags TEXT,
        FOREIGN KEY (source_id) REFERENCES sources(source_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS concepts (
        concept_id TEXT PRIMARY KEY,
        source_id TEXT,
        name TEXT,
        definition_1liner TEXT,
        domain TEXT,
        created_at TEXT,
        FOREIGN KEY (source_id) REFERENCES sources(source_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS excerpts (
        excerpt_id TEXT PRIMARY KEY,
        source_id TEXT,
        content TEXT,
        page_num INTEGER,
        created_at TEXT,
        FOREIGN KEY (source_id) REFERENCES sources(source_id)
    )''')

    conn.commit()
    conn.close()


def store_utf_to_sqlite(result: 'UTFExtractionResult'):
    """Store UTF extraction result to SQLite for claim similarity."""
    import json

    init_utf_db()
    conn = sqlite3.connect(UTF_DB_PATH)
    c = conn.cursor()

    # Store source
    c.execute('''INSERT OR REPLACE INTO sources
        (source_id, title, authors, year, domain, abstract, quality_status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (result.source.source_id, result.source.title,
         json.dumps(result.source.authors), result.source.year,
         result.source.domain, result.source.abstract,
         result.source.quality_status, datetime.now().isoformat()))

    # Store claims
    for claim in result.claims:
        c.execute('''INSERT OR REPLACE INTO claims
            (claim_id, source_id, statement, claim_form, grounding, confidence,
             stability_class, evidence_grade, excerpt_ids, domain, scope, created_at,
             slug_code, taxonomy_tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (claim.claim_id, claim.source_id, claim.statement, claim.claim_form,
             claim.grounding, claim.confidence, claim.stability_class,
             claim.evidence_grade, json.dumps(claim.excerpt_ids),
             claim.domain, claim.scope, datetime.now().isoformat(),
             getattr(claim, 'slug_code', None),
             json.dumps(getattr(claim, 'taxonomy_tags', []))))

    # Store concepts
    for concept in result.concepts:
        # source_ids is a list, use first or join
        source_id = concept.source_ids[0] if concept.source_ids else result.source.source_id
        c.execute('''INSERT OR REPLACE INTO concepts
            (concept_id, source_id, name, definition_1liner, domain, created_at)
            VALUES (?, ?, ?, ?, ?, ?)''',
            (concept.concept_id, source_id, concept.name,
             concept.definition_1liner, concept.domain, datetime.now().isoformat()))

    # Store excerpts
    for excerpt in result.excerpts:
        c.execute('''INSERT OR REPLACE INTO excerpts
            (excerpt_id, source_id, content, page_num, created_at)
            VALUES (?, ?, ?, ?, ?)''',
            (excerpt.excerpt_id, excerpt.source_id, excerpt.text,
             excerpt.location, datetime.now().isoformat()))

    conn.commit()
    conn.close()


# ============================================================================
# Self-Model: System knows itself to recognize improvements
# ============================================================================

SELF_MODEL_PATH = Path(__file__).parent / "SELF_MODEL.json"
METRICS_DB = Path(__file__).parent / "ingest.db"  # Use existing DB, not new one
_self_model = None
_session_metrics = {"docs_processed": 0, "tokens_used": 0, "cache_hits": 0,
                    "upgrades_found": 0, "start_time": None}

def get_self_model() -> Dict:
    """Load the system's self-model (cached)."""
    global _self_model
    if _self_model is None:
        if SELF_MODEL_PATH.exists():
            _self_model = json.loads(SELF_MODEL_PATH.read_text())
        else:
            _self_model = {"capabilities": {}}
    return _self_model


def track_metric(name: str, value: float, conn: Optional[sqlite3.Connection] = None):
    """Track performance metric - built into core flow, not separate.

    Metrics are stored in existing ingest.db to avoid database proliferation.
    """
    if conn is None:
        conn = sqlite3.connect(METRICS_DB)
        close_after = True
    else:
        close_after = False

    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS performance_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        metric_name TEXT,
        value REAL
    )''')
    c.execute('INSERT INTO performance_metrics (timestamp, metric_name, value) VALUES (?, ?, ?)',
              (datetime.now().isoformat(), name, value))
    conn.commit()

    if close_after:
        conn.close()


def get_efficiency_trend(metric: str, days: int = 7) -> Dict:
    """Get efficiency trend for a metric - detect bloat or improvement."""
    conn = sqlite3.connect(METRICS_DB)
    c = conn.cursor()

    try:
        c.execute('''SELECT value, timestamp FROM performance_metrics
                     WHERE metric_name = ? ORDER BY timestamp DESC LIMIT 100''', (metric,))
        rows = c.fetchall()
    except:
        rows = []
    conn.close()

    if len(rows) < 2:
        return {"trend": "insufficient_data", "values": []}

    values = [r[0] for r in rows]
    recent_avg = sum(values[:10]) / min(10, len(values[:10]))
    older_avg = sum(values[-10:]) / min(10, len(values[-10:]))

    if recent_avg > older_avg * 1.2:
        trend = "increasing"  # Could be bloat if it's cost/time
    elif recent_avg < older_avg * 0.8:
        trend = "decreasing"  # Could be good if it's cost/time
    else:
        trend = "stable"

    return {"trend": trend, "recent": recent_avg, "older": older_avg, "change_pct": (recent_avg - older_avg) / older_avg * 100 if older_avg else 0}


def check_system_health() -> Dict:
    """Self-aware health check - knows when efficiency is dropping."""
    health = {"status": "healthy", "issues": [], "metrics": {}}

    # Check token efficiency trend
    token_trend = get_efficiency_trend("tokens_per_doc")
    health["metrics"]["tokens_per_doc"] = token_trend
    if token_trend.get("trend") == "increasing" and token_trend.get("change_pct", 0) > 20:
        health["issues"].append(f"Token usage increasing {token_trend['change_pct']:.0f}% - possible bloat")
        health["status"] = "degraded"

    # Check processing time trend
    time_trend = get_efficiency_trend("processing_time")
    health["metrics"]["processing_time"] = time_trend
    if time_trend.get("trend") == "increasing" and time_trend.get("change_pct", 0) > 30:
        health["issues"].append(f"Processing time increasing {time_trend['change_pct']:.0f}% - investigate")
        health["status"] = "degraded"

    # Check cache hit rate
    cache_trend = get_efficiency_trend("cache_hit_rate")
    health["metrics"]["cache_hit_rate"] = cache_trend
    if cache_trend.get("recent", 0) < 0.3:
        health["issues"].append("Cache hit rate below 30% - cache may be ineffective")

    return health


def detect_upgrade_potential(claim_statement: str, source_id: str) -> Optional[Dict]:
    """Check if a claim suggests an upgrade to our current methods.

    Uses SELF_MODEL.json to know what the system is and what could improve it.
    This runs on EVERY input - the architecture inherently seeks self-improvement.
    """
    UPGRADE_INDICATORS = ["improves", "outperforms", "better than", "state-of-the-art",
                          "novel approach", "more efficient", "faster", "reduces",
                          "10x", "2x", "order of magnitude", "significantly"]

    model = get_self_model()
    capabilities = model.get("capabilities", {})

    statement_lower = claim_statement.lower()

    # Check for upgrade indicators
    has_upgrade_signal = any(ind in statement_lower for ind in UPGRADE_INDICATORS)

    # Match against our capabilities (from self-model)
    for cap_name, cap_info in capabilities.items():
        keywords = cap_info.get("keywords", [])
        triggers = cap_info.get("upgrade_triggers", [])
        limitations = cap_info.get("limitations", [])

        # Check if claim relates to this capability
        keyword_match = any(kw.lower() in statement_lower for kw in keywords)

        if keyword_match:
            # Check if it addresses a known limitation or matches upgrade trigger
            addresses_limitation = any(lim.lower() in statement_lower for lim in limitations)
            matches_trigger = any(trig.lower() in statement_lower for trig in triggers)

            if has_upgrade_signal or addresses_limitation or matches_trigger:
                return {
                    "capability": cap_name,
                    "current_method": cap_info.get("current_method"),
                    "claim": claim_statement[:300],
                    "source": source_id,
                    "detected_at": datetime.now().isoformat(),
                    "trigger_type": "limitation" if addresses_limitation else ("trigger" if matches_trigger else "indicator"),
                    "priority": "high" if addresses_limitation else "medium"
                }

    return None


def store_utf_to_kg(result: 'UTFExtractionResult'):
    """Store UTF extraction result to knowledge graph."""
    import json
    from dataclasses import asdict

    # Check claims for upgrade potential (integrated, not separate)
    upgrades = []
    for claim in result.claims:
        upgrade = detect_upgrade_potential(claim.statement, result.source.source_id)
        if upgrade:
            upgrades.append(upgrade)

    if upgrades:
        print(f"    [UPGRADE] Found {len(upgrades)} potential improvements:")
        for u in upgrades[:3]:
            print(f"      → {u['method']}: {u['claim'][:60]}...")

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
            f"SOURCE_ID:{result.source.source_id}",
            f"UPGRADES:{len(upgrades)}"
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


def process_document_legacy(path: Path, text: str, conn: sqlite3.Connection, method: str = "Unknown") -> Dict:
    """Legacy HiRAG/LeanRAG processing pipeline."""
    print(f"    [LEGACY MODE] HiRAG/LeanRAG (text via {method})")
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
        "chunks": len(chunks),
        "extraction_method": method
    }


def check_localai() -> bool:
    """Check if LocalAI is available."""
    try:
        r = requests.get(f"{LOCALAI_URL.replace('/v1', '')}/readyz", timeout=5)
        return r.status_code == 200
    except:
        return False


def scan_folder(conn: sqlite3.Connection, min_size_kb: int = 10) -> List[Path]:
    """Scan folder for new files, prioritized by size (larger = more content)."""
    if not WATCH_FOLDER.exists():
        WATCH_FOLDER.mkdir(parents=True)
        return []

    new_files = []
    for path in WATCH_FOLDER.iterdir():
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            # Skip tiny files (likely incomplete or placeholders)
            if path.stat().st_size < min_size_kb * 1024:
                continue
            fhash = file_hash(path)
            if not is_processed(conn, fhash):
                new_files.append(path)

    # Sort by size (process larger documents first - more likely to be valuable)
    new_files.sort(key=lambda p: p.stat().st_size, reverse=True)
    return new_files


def run_ingest(watch: bool = False, interval: int = 300):
    """Run the autonomous ingestion."""
    print("=" * 60)
    print("Autonomous Ingestion (HiRAG + LeanRAG + MinerU)")
    print("=" * 60)
    print(f"Watch folder: {WATCH_FOLDER}")
    print(f"LocalAI URL: {LOCALAI_URL}")
    print()
    print("Extraction Stack (priority order):")
    print(f"  1. MinerU:     {'[OK] Best for PDFs with tables/figures' if MINERU_AVAILABLE else '[--] Not installed'}")
    print(f"  2. MarkItDown: {'[OK] Structure-preserving' if MARKITDOWN_AVAILABLE else '[--] Not installed'}")
    print(f"  3. PyMuPDF:    {'[OK] Fallback text extraction' if PYMUPDF_AVAILABLE else '[--] Not installed'}")
    print()
    print("Efficiency Features:")
    print(f"  - Dragonfly Cache: {'[OK] 24h TTL' if REDIS_AVAILABLE and get_dragonfly() else '[--] Disabled'}")
    print(f"  - UTF Schema:      {'[OK] Enabled' if USE_UTF_SCHEMA and UTF_AVAILABLE else '[--] Disabled'}")
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
                        method = result.get('extraction_method', 'Unknown')
                        # Handle both UTF and legacy mode outputs
                        if 'claims' in result:
                            print(f"    [OK] {result['claims']} claims, {result['concepts']} concepts [{method}]")
                        else:
                            print(f"    [OK] {result['facts']} facts, {result['chunks']} chunks [{method}]")
                    else:
                        print(f"    [SKIP] {result.get('error', 'Unknown error')}")
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

    # Cache stats
    cache = get_cache_stats()

    print("=" * 50)
    print("Knowledge Base Status")
    print("=" * 50)
    print(f"Documents processed: {files or 0}")
    print(f"Total tokens used: {tokens or 0} (FREE via LocalAI)")
    print(f"Local facts stored: {local_count}")
    print(f"Global summaries: {global_count}")
    print(f"\nHierarchy: Local ({local_count}) -> Global ({global_count})")
    print()
    print("Extraction Stack:")
    print(f"  MinerU:     {'Available' if MINERU_AVAILABLE else 'Not installed'}")
    print(f"  MarkItDown: {'Available' if MARKITDOWN_AVAILABLE else 'Not installed'}")
    print(f"  PyMuPDF:    {'Available' if PYMUPDF_AVAILABLE else 'Not installed'}")
    print()
    print("Cache Efficiency (this session):")
    print(f"  Hit rate: {cache['hit_rate']}")
    print(f"  Hits: {cache['hits']} | Misses: {cache['misses']} | Writes: {cache['writes']}")


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
