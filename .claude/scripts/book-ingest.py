#!/usr/bin/env python3
"""
Book Ingestion Pipeline - Hierarchical RAG for Technical Documents

Handles:
- Large PDFs (50+ pages, full books)
- Mathematical formulas and equations
- High-order concepts with relationships
- Hierarchical summarization (paragraph → section → chapter → book)
- Semantic chunking with context preservation
- Integration with existing memory infrastructure

Usage:
    python book-ingest.py <pdf_path> [--title "Book Title"]
    python book-ingest.py <pdf_path> --query "What does it say about X?"
    python book-ingest.py --list  # List ingested books
"""

import sys
import json
import re
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional
import sqlite3

# Add daemon to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent.parent
DAEMON_DIR = PROJECT_DIR / "daemon"
sys.path.insert(0, str(DAEMON_DIR))

# Import controller and feedback bridge for adaptive settings
try:
    from controller import MAPEController, Metric, MetricType
    CONTROLLER_AVAILABLE = True
except ImportError:
    CONTROLLER_AVAILABLE = False

try:
    from feedback_bridge import FeedbackBridge
    BRIDGE_AVAILABLE = True
except ImportError:
    BRIDGE_AVAILABLE = False

# Storage paths
BOOKS_DB = PROJECT_DIR / "daemon" / "books.db"
KNOWLEDGE_GRAPH = Path.home() / ".claude" / "memory" / "knowledge-graph.jsonl"

# ============================================================================
# Data Models
# ============================================================================

@dataclass
class Chunk:
    """A semantic chunk of text with metadata."""
    id: str
    book_id: str
    content: str
    chunk_type: str  # paragraph, section, formula, definition, theorem
    level: int  # Hierarchy level (0=book, 1=chapter, 2=section, 3=paragraph)
    parent_id: Optional[str] = None
    position: int = 0
    token_count: int = 0
    embedding: Optional[list] = None
    metadata: dict = field(default_factory=dict)

@dataclass
class Summary:
    """Hierarchical summary at various levels."""
    id: str
    book_id: str
    level: str  # book, chapter, section
    title: str
    summary: str
    key_concepts: list
    formulas: list
    parent_id: Optional[str] = None
    children_ids: list = field(default_factory=list)

@dataclass
class Concept:
    """Extracted high-order concept."""
    id: str
    book_id: str
    name: str
    definition: str
    related_concepts: list
    formulas: list
    chunk_refs: list  # References to source chunks

# ============================================================================
# Database Setup
# ============================================================================

def init_db():
    """Initialize SQLite database for book storage."""
    conn = sqlite3.connect(BOOKS_DB)
    c = conn.cursor()

    # Books table
    c.execute('''CREATE TABLE IF NOT EXISTS books (
        id TEXT PRIMARY KEY,
        title TEXT,
        author TEXT,
        source_path TEXT,
        ingested_at TEXT,
        total_chunks INTEGER,
        total_pages INTEGER,
        book_summary TEXT,
        metadata TEXT
    )''')

    # Chunks table
    c.execute('''CREATE TABLE IF NOT EXISTS chunks (
        id TEXT PRIMARY KEY,
        book_id TEXT,
        content TEXT,
        chunk_type TEXT,
        level INTEGER,
        parent_id TEXT,
        position INTEGER,
        token_count INTEGER,
        embedding BLOB,
        metadata TEXT,
        FOREIGN KEY (book_id) REFERENCES books(id)
    )''')

    # Summaries table (hierarchical)
    c.execute('''CREATE TABLE IF NOT EXISTS summaries (
        id TEXT PRIMARY KEY,
        book_id TEXT,
        level TEXT,
        title TEXT,
        summary TEXT,
        key_concepts TEXT,
        formulas TEXT,
        parent_id TEXT,
        children_ids TEXT,
        FOREIGN KEY (book_id) REFERENCES books(id)
    )''')

    # Concepts table
    c.execute('''CREATE TABLE IF NOT EXISTS concepts (
        id TEXT PRIMARY KEY,
        book_id TEXT,
        name TEXT,
        definition TEXT,
        related_concepts TEXT,
        formulas TEXT,
        chunk_refs TEXT,
        FOREIGN KEY (book_id) REFERENCES books(id)
    )''')

    # Full-text search
    c.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
        USING fts5(content, chunk_type, book_id)''')

    conn.commit()
    return conn

# ============================================================================
# PDF Processing
# ============================================================================

def convert_pdf_to_markdown(pdf_path: str) -> tuple[str, dict]:
    """Convert PDF to markdown using Docling."""
    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(pdf_path)
        markdown = result.document.export_to_markdown()

        # Extract metadata
        metadata = {
            "pages": getattr(result.document, 'num_pages', None),
            "source": pdf_path,
            "converted_at": datetime.now().isoformat()
        }

        return markdown, metadata
    except ImportError:
        print("Error: Docling not installed. Run: pip install docling")
        sys.exit(1)

# ============================================================================
# Smart Chunking
# ============================================================================

def estimate_tokens(text: str) -> int:
    """Rough token estimate (words * 1.3)."""
    return int(len(text.split()) * 1.3)

def extract_formulas(text: str) -> list[dict]:
    """Extract mathematical formulas and equations."""
    formulas = []

    # LaTeX inline: $...$
    inline = re.findall(r'\$([^\$]+)\$', text)
    for f in inline:
        formulas.append({"type": "inline", "latex": f})

    # LaTeX display: $$...$$
    display = re.findall(r'\$\$([^\$]+)\$\$', text, re.DOTALL)
    for f in display:
        formulas.append({"type": "display", "latex": f.strip()})

    # Equation environments
    equations = re.findall(r'\\begin\{equation\}(.*?)\\end\{equation\}', text, re.DOTALL)
    for f in equations:
        formulas.append({"type": "equation", "latex": f.strip()})

    # Common patterns: x = ..., f(x) = ...
    patterns = re.findall(r'([a-zA-Z]\([^)]+\)\s*=\s*[^\n]+)', text)
    for p in patterns:
        if len(p) > 5:
            formulas.append({"type": "expression", "text": p.strip()})

    return formulas

def extract_definitions(text: str) -> list[dict]:
    """Extract definitions, theorems, lemmas."""
    definitions = []

    # Definition patterns
    def_patterns = [
        (r'(?:Definition|Def\.?)\s*[\d.]*[:\s]+([^\n]+(?:\n(?![A-Z]).*)*)', 'definition'),
        (r'(?:Theorem|Thm\.?)\s*[\d.]*[:\s]+([^\n]+(?:\n(?![A-Z]).*)*)', 'theorem'),
        (r'(?:Lemma)\s*[\d.]*[:\s]+([^\n]+(?:\n(?![A-Z]).*)*)', 'lemma'),
        (r'(?:Corollary|Cor\.?)\s*[\d.]*[:\s]+([^\n]+(?:\n(?![A-Z]).*)*)', 'corollary'),
        (r'(?:Proposition|Prop\.?)\s*[\d.]*[:\s]+([^\n]+(?:\n(?![A-Z]).*)*)', 'proposition'),
        (r'(?:Axiom)\s*[\d.]*[:\s]+([^\n]+(?:\n(?![A-Z]).*)*)', 'axiom'),
    ]

    for pattern, dtype in def_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        for m in matches:
            definitions.append({"type": dtype, "content": m.strip()[:500]})

    return definitions

def smart_chunk(markdown: str, max_tokens: int = 500) -> list[Chunk]:
    """
    Intelligent chunking that preserves:
    - Section boundaries
    - Formula integrity
    - Definition completeness
    - Contextual coherence
    """
    chunks = []

    # Split by headers first (preserve hierarchy)
    sections = re.split(r'(^#{1,6}\s+.+$)', markdown, flags=re.MULTILINE)

    current_header = ""
    current_level = 0
    position = 0

    for i, section in enumerate(sections):
        if not section.strip():
            continue

        # Check if this is a header
        header_match = re.match(r'^(#{1,6})\s+(.+)$', section)
        if header_match:
            current_level = len(header_match.group(1))
            current_header = header_match.group(2)
            continue

        # Process content section
        paragraphs = section.split('\n\n')

        current_chunk = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Check for special content
            formulas = extract_formulas(para)
            definitions = extract_definitions(para)

            # Determine chunk type
            if definitions:
                chunk_type = definitions[0]['type']
            elif formulas:
                chunk_type = 'formula'
            else:
                chunk_type = 'paragraph'

            # Check if adding this would exceed limit
            combined = current_chunk + "\n\n" + para if current_chunk else para
            if estimate_tokens(combined) > max_tokens and current_chunk:
                # Save current chunk
                chunk_id = hashlib.md5(current_chunk.encode()).hexdigest()[:12]
                chunks.append(Chunk(
                    id=chunk_id,
                    book_id="",  # Set later
                    content=current_chunk,
                    chunk_type=chunk_type,
                    level=current_level + 2,  # Paragraphs are below sections
                    position=position,
                    token_count=estimate_tokens(current_chunk),
                    metadata={
                        "header": current_header,
                        "formulas": formulas,
                        "definitions": definitions
                    }
                ))
                position += 1
                current_chunk = para
            else:
                current_chunk = combined

        # Don't forget last chunk
        if current_chunk:
            chunk_id = hashlib.md5(current_chunk.encode()).hexdigest()[:12]
            formulas = extract_formulas(current_chunk)
            definitions = extract_definitions(current_chunk)
            chunk_type = 'formula' if formulas else ('definition' if definitions else 'paragraph')

            chunks.append(Chunk(
                id=chunk_id,
                book_id="",
                content=current_chunk,
                chunk_type=chunk_type,
                level=current_level + 2,
                position=position,
                token_count=estimate_tokens(current_chunk),
                metadata={
                    "header": current_header,
                    "formulas": formulas,
                    "definitions": definitions
                }
            ))
            position += 1

    return chunks

# ============================================================================
# Hierarchical Summarization
# ============================================================================

def build_hierarchy(markdown: str) -> dict:
    """Build document hierarchy from markdown headers."""
    hierarchy = {
        "title": "Document",
        "level": 0,
        "content": "",
        "children": []
    }

    lines = markdown.split('\n')
    stack = [hierarchy]
    current_content = []

    for line in lines:
        header_match = re.match(r'^(#{1,6})\s+(.+)$', line)

        if header_match:
            # Save accumulated content to current node
            if current_content:
                stack[-1]["content"] = '\n'.join(current_content)
                current_content = []

            level = len(header_match.group(1))
            title = header_match.group(2)

            new_node = {
                "title": title,
                "level": level,
                "content": "",
                "children": []
            }

            # Find correct parent
            while len(stack) > 1 and stack[-1]["level"] >= level:
                stack.pop()

            stack[-1]["children"].append(new_node)
            stack.append(new_node)
        else:
            current_content.append(line)

    # Save final content
    if current_content:
        stack[-1]["content"] = '\n'.join(current_content)

    return hierarchy

def generate_section_summary(content: str, title: str, formulas: list, concepts: list) -> str:
    """Generate a summary for a section (would use LLM in production)."""
    # For now, create structured summary from extracted elements
    summary_parts = []

    # First sentence or two
    sentences = re.split(r'[.!?]+', content)
    if sentences:
        intro = '. '.join(sentences[:2]).strip()
        if intro:
            summary_parts.append(intro[:300])

    # Key formulas
    if formulas:
        formula_text = f"Key formulas: {', '.join([f.get('latex', f.get('text', ''))[:50] for f in formulas[:3]])}"
        summary_parts.append(formula_text)

    # Concepts mentioned
    if concepts:
        concept_text = f"Concepts: {', '.join(concepts[:5])}"
        summary_parts.append(concept_text)

    return ' | '.join(summary_parts) if summary_parts else f"Section: {title}"

def create_hierarchical_summaries(hierarchy: dict, book_id: str, conn: sqlite3.Connection) -> list[Summary]:
    """Create summaries at each level of the hierarchy."""
    summaries = []

    def process_node(node: dict, parent_id: Optional[str] = None) -> str:
        # Extract formulas and concepts from content
        formulas = extract_formulas(node["content"]) if node["content"] else []
        definitions = extract_definitions(node["content"]) if node["content"] else []

        # Determine level name
        level_names = {0: "book", 1: "part", 2: "chapter", 3: "section", 4: "subsection"}
        level_name = level_names.get(node["level"], "paragraph")

        # Create summary ID
        summary_id = hashlib.md5(f"{book_id}:{node['title']}:{node['level']}".encode()).hexdigest()[:12]

        # Process children first (bottom-up for aggregation)
        children_ids = []
        children_concepts = []
        children_formulas = []

        for child in node.get("children", []):
            child_id = process_node(child, summary_id)
            children_ids.append(child_id)

        # Aggregate concepts from children
        concepts = [d["content"][:100] for d in definitions]

        # Generate summary
        summary_text = generate_section_summary(
            node["content"],
            node["title"],
            formulas,
            concepts
        )

        summary = Summary(
            id=summary_id,
            book_id=book_id,
            level=level_name,
            title=node["title"],
            summary=summary_text,
            key_concepts=concepts,
            formulas=[f.get("latex", f.get("text", "")) for f in formulas],
            parent_id=parent_id,
            children_ids=children_ids
        )

        summaries.append(summary)

        # Store in database
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO summaries
            (id, book_id, level, title, summary, key_concepts, formulas, parent_id, children_ids)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (summary.id, summary.book_id, summary.level, summary.title, summary.summary,
             json.dumps(summary.key_concepts), json.dumps(summary.formulas),
             summary.parent_id, json.dumps(summary.children_ids)))
        conn.commit()

        return summary_id

    process_node(hierarchy)
    return summaries

# ============================================================================
# Concept Extraction
# ============================================================================

def extract_concepts(chunks: list[Chunk], book_id: str, conn: sqlite3.Connection) -> list[Concept]:
    """Extract high-order concepts and their relationships."""
    concepts = []
    concept_mentions = {}  # Track where concepts appear

    # First pass: identify potential concepts
    for chunk in chunks:
        definitions = chunk.metadata.get("definitions", [])

        for defn in definitions:
            # Extract concept name from definition
            content = defn["content"]

            # Try to extract the term being defined
            # Pattern: "A [term] is..." or "[Term]: ..."
            term_match = re.match(r'^(?:A|An|The)?\s*([A-Z][a-z]+(?:\s+[a-z]+)*)\s+(?:is|are|means)', content)
            if not term_match:
                term_match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z]?[a-z]+)*)[:\s]', content)

            if term_match:
                term = term_match.group(1).strip()

                if term not in concept_mentions:
                    concept_mentions[term] = {
                        "definition": content,
                        "type": defn["type"],
                        "chunks": [],
                        "formulas": []
                    }
                concept_mentions[term]["chunks"].append(chunk.id)

                # Collect associated formulas
                for formula in chunk.metadata.get("formulas", []):
                    concept_mentions[term]["formulas"].append(
                        formula.get("latex", formula.get("text", ""))
                    )

    # Second pass: find relationships between concepts
    concept_names = list(concept_mentions.keys())

    for name, data in concept_mentions.items():
        related = []
        definition_lower = data["definition"].lower()

        for other_name in concept_names:
            if other_name != name and other_name.lower() in definition_lower:
                related.append(other_name)

        concept_id = hashlib.md5(f"{book_id}:{name}".encode()).hexdigest()[:12]

        concept = Concept(
            id=concept_id,
            book_id=book_id,
            name=name,
            definition=data["definition"][:1000],
            related_concepts=related,
            formulas=list(set(data["formulas"]))[:10],
            chunk_refs=data["chunks"]
        )
        concepts.append(concept)

        # Store in database
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO concepts
            (id, book_id, name, definition, related_concepts, formulas, chunk_refs)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (concept.id, concept.book_id, concept.name, concept.definition,
             json.dumps(concept.related_concepts), json.dumps(concept.formulas),
             json.dumps(concept.chunk_refs)))
        conn.commit()

    return concepts

# ============================================================================
# Knowledge Graph Integration
# ============================================================================

def export_to_knowledge_graph(book_id: str, title: str, concepts: list[Concept], summaries: list[Summary]):
    """Export entities and relations to knowledge graph."""
    KNOWLEDGE_GRAPH.parent.mkdir(parents=True, exist_ok=True)

    with open(KNOWLEDGE_GRAPH, 'a') as f:
        # Book entity
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "type": "entity",
            "data": {
                "name": f"book_{book_id}",
                "entityType": "book",
                "observations": [f"Title: {title}", f"Concepts: {len(concepts)}", f"Sections: {len(summaries)}"]
            }
        }) + '\n')

        # Concept entities
        for concept in concepts:
            f.write(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "type": "entity",
                "data": {
                    "name": f"concept_{concept.name.lower().replace(' ', '_')}",
                    "entityType": "concept",
                    "observations": [
                        f"Book: {title}",
                        f"Definition: {concept.definition[:200]}",
                        f"Formulas: {len(concept.formulas)}",
                        f"Related: {', '.join(concept.related_concepts[:5])}"
                    ]
                }
            }) + '\n')

        # Relations between concepts
        for concept in concepts:
            for related in concept.related_concepts:
                f.write(json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "type": "relation",
                    "data": {
                        "from": f"concept_{concept.name.lower().replace(' ', '_')}",
                        "to": f"concept_{related.lower().replace(' ', '_')}",
                        "relationType": "related_to"
                    }
                }) + '\n')

# ============================================================================
# Embedding (Placeholder - integrate with your embedding service)
# ============================================================================

def generate_embeddings(chunks: list[Chunk]) -> list[Chunk]:
    """Generate embeddings for chunks. Override with your embedding service."""
    # Placeholder - in production, use:
    # - sentence-transformers locally
    # - OpenAI embeddings API
    # - Your existing memory.py embedding function

    try:
        from memory import Memory
        mem = Memory()

        for chunk in chunks:
            # If Memory has embedding capability, use it
            if hasattr(mem, 'embed'):
                chunk.embedding = mem.embed(chunk.content)
    except:
        pass  # Embeddings are optional enhancement

    return chunks

# ============================================================================
# Query Interface
# ============================================================================

def query_book(book_id: str, query: str, conn: sqlite3.Connection) -> dict:
    """Query ingested book content."""
    c = conn.cursor()

    results = {
        "query": query,
        "chunks": [],
        "concepts": [],
        "summaries": []
    }

    # Full-text search in chunks
    c.execute('''SELECT c.* FROM chunks c
        JOIN chunks_fts fts ON c.id = fts.rowid
        WHERE chunks_fts MATCH ? AND c.book_id = ?
        LIMIT 5''', (query, book_id))

    for row in c.fetchall():
        results["chunks"].append({
            "id": row[0],
            "content": row[2][:500],
            "type": row[3],
            "metadata": json.loads(row[9]) if row[9] else {}
        })

    # Search concepts
    c.execute('''SELECT * FROM concepts
        WHERE book_id = ? AND (name LIKE ? OR definition LIKE ?)
        LIMIT 5''', (book_id, f'%{query}%', f'%{query}%'))

    for row in c.fetchall():
        results["concepts"].append({
            "name": row[2],
            "definition": row[3][:300],
            "formulas": json.loads(row[5]) if row[5] else []
        })

    # Get relevant summaries
    c.execute('''SELECT * FROM summaries
        WHERE book_id = ? AND (title LIKE ? OR summary LIKE ?)
        LIMIT 3''', (book_id, f'%{query}%', f'%{query}%'))

    for row in c.fetchall():
        results["summaries"].append({
            "level": row[2],
            "title": row[3],
            "summary": row[4]
        })

    return results

# ============================================================================
# Main Pipeline
# ============================================================================

def get_adaptive_settings() -> dict:
    """Get chunk settings from MAPE controller (adaptive)."""
    defaults = {"chunk_size": 500, "chunk_overlap": 50, "retrieval_k": 5}

    if not CONTROLLER_AVAILABLE:
        return defaults

    try:
        ctrl = MAPEController()
        state = ctrl.state
        return {
            "chunk_size": state.chunk_size,
            "chunk_overlap": state.chunk_overlap,
            "retrieval_k": state.retrieval_k
        }
    except Exception:
        return defaults


def report_metrics_to_controller(book_id: str, chunks: list, concepts: list, summaries: list):
    """Report ingestion metrics to MAPE controller for learning."""
    if not CONTROLLER_AVAILABLE:
        return

    try:
        # Calculate quality metrics
        avg_chunk_tokens = sum(c.token_count for c in chunks) / len(chunks) if chunks else 0
        concept_density = len(concepts) / len(chunks) if chunks else 0
        formula_count = sum(len(c.metadata.get("formulas", [])) for c in chunks)

        # Estimate comprehension (heuristic: more concepts + summaries = better structure)
        comprehension_score = min(1.0, (len(concepts) + len(summaries)) / (len(chunks) * 0.5))

        # Token efficiency: comprehension per token
        total_tokens = sum(c.token_count for c in chunks)
        efficiency = comprehension_score / total_tokens if total_tokens > 0 else 0

        # Chunk quality: variance in chunk size (lower = more consistent = better)
        token_counts = [c.token_count for c in chunks]
        if len(token_counts) > 1:
            import statistics
            variance = statistics.variance(token_counts)
            chunk_quality = max(0, 1 - variance / 10000)  # Normalize
        else:
            chunk_quality = 0.5

        metrics = [
            Metric(type=MetricType.COMPREHENSION, value=comprehension_score, book_id=book_id),
            Metric(type=MetricType.TOKEN_EFFICIENCY, value=efficiency, book_id=book_id),
            Metric(type=MetricType.CHUNK_QUALITY, value=chunk_quality, book_id=book_id,
                   context={"avg_tokens": avg_chunk_tokens, "concepts": len(concepts)}),
        ]

        print(f"    [CTRL] Reported metrics: comprehension={comprehension_score:.2f}, chunk_quality={chunk_quality:.2f}")

        # Use feedback bridge if available (decision-informed control)
        if BRIDGE_AVAILABLE:
            bridge = FeedbackBridge()
            result = bridge.run_cycle(metrics)

            if result.get("selected_action"):
                action = result["selected_action"]
                print(f"    [BRIDGE] Decision-informed action: {action['type']}")
                print(f"    [BRIDGE] Rationale: {action['rationale']}")
        else:
            # Fallback to direct controller
            ctrl = MAPEController()
            ctrl.monitor(metrics)
            result = ctrl.run_cycle()

            if result.get("executed_actions"):
                print(f"    [CTRL] Controller adapted: {len(result['executed_actions'])} actions")

    except Exception as e:
        print(f"    [CTRL] Warning: Could not report metrics: {e}")


def ingest_book(pdf_path: str, title: Optional[str] = None) -> dict:
    """Main ingestion pipeline."""
    print(f"[BOOK] Ingesting: {pdf_path}")

    # Initialize database
    conn = init_db()

    # Get adaptive settings from controller
    settings = get_adaptive_settings()
    chunk_size = settings["chunk_size"]
    print(f"  [CTRL] Using chunk_size={chunk_size} (adaptive)")

    # Generate book ID
    book_id = hashlib.md5(pdf_path.encode()).hexdigest()[:12]

    # Step 1: Convert PDF to markdown
    print("  -> Converting PDF to Markdown...")
    markdown, metadata = convert_pdf_to_markdown(pdf_path)
    print(f"    [OK] Converted ({len(markdown)} chars)")

    # Step 2: Build document hierarchy
    print("  -> Building document hierarchy...")
    hierarchy = build_hierarchy(markdown)

    # Use first header as title if not provided
    if not title:
        if hierarchy["children"]:
            title = hierarchy["children"][0].get("title", Path(pdf_path).stem)
        else:
            title = Path(pdf_path).stem
    hierarchy["title"] = title
    print(f"    [OK] Title: {title}")

    # Step 3: Smart chunking (using adaptive settings)
    print("  -> Chunking content...")
    chunks = smart_chunk(markdown, max_tokens=chunk_size)
    for chunk in chunks:
        chunk.book_id = book_id
    print(f"    [OK] Created {len(chunks)} chunks (target: {chunk_size} tokens)")

    # Step 4: Generate embeddings (if available)
    print("  -> Generating embeddings...")
    chunks = generate_embeddings(chunks)
    print("    [OK] Embeddings complete")

    # Step 5: Store chunks
    print("  -> Storing chunks...")
    c = conn.cursor()
    for chunk in chunks:
        c.execute('''INSERT OR REPLACE INTO chunks
            (id, book_id, content, chunk_type, level, parent_id, position, token_count, embedding, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (chunk.id, chunk.book_id, chunk.content, chunk.chunk_type, chunk.level,
             chunk.parent_id, chunk.position, chunk.token_count,
             json.dumps(chunk.embedding) if chunk.embedding else None,
             json.dumps(chunk.metadata)))

        # Add to FTS index
        c.execute('''INSERT OR REPLACE INTO chunks_fts (rowid, content, chunk_type, book_id)
            VALUES ((SELECT rowid FROM chunks WHERE id = ?), ?, ?, ?)''',
            (chunk.id, chunk.content, chunk.chunk_type, chunk.book_id))
    conn.commit()
    print(f"    [OK] Stored {len(chunks)} chunks")

    # Step 6: Create hierarchical summaries
    print("  -> Creating hierarchical summaries...")
    summaries = create_hierarchical_summaries(hierarchy, book_id, conn)
    print(f"    [OK] Created {len(summaries)} summaries")

    # Step 7: Extract concepts
    print("  -> Extracting concepts...")
    concepts = extract_concepts(chunks, book_id, conn)
    print(f"    [OK] Extracted {len(concepts)} concepts")

    # Step 8: Export to knowledge graph
    print("  -> Exporting to knowledge graph...")
    export_to_knowledge_graph(book_id, title, concepts, summaries)
    print("    [OK] Knowledge graph updated")

    # Step 9: Store book metadata
    book_summary = ""
    for s in summaries:
        if s.level == "book":
            book_summary = s.summary
            break

    c.execute('''INSERT OR REPLACE INTO books
        (id, title, author, source_path, ingested_at, total_chunks, total_pages, book_summary, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (book_id, title, metadata.get("author", "Unknown"), pdf_path,
         datetime.now().isoformat(), len(chunks), metadata.get("pages"),
         book_summary, json.dumps(metadata)))
    conn.commit()

    # Step 10: Report metrics to controller for adaptive learning
    print("  -> Reporting to controller...")
    report_metrics_to_controller(book_id, chunks, concepts, summaries)

    # Report
    result = {
        "success": True,
        "book_id": book_id,
        "title": title,
        "chunks": len(chunks),
        "summaries": len(summaries),
        "concepts": len(concepts),
        "storage": str(BOOKS_DB),
        "chunk_size_used": chunk_size
    }

    print(f"\n[DONE] Ingestion complete!")
    print(f"   Book ID: {book_id}")
    print(f"   Chunks: {len(chunks)} (chunk_size={chunk_size})")
    print(f"   Summaries: {len(summaries)}")
    print(f"   Concepts: {len(concepts)}")

    conn.close()
    return result

def list_books():
    """List all ingested books."""
    conn = init_db()
    c = conn.cursor()

    c.execute('SELECT id, title, total_chunks, ingested_at FROM books ORDER BY ingested_at DESC')
    books = c.fetchall()

    if not books:
        print("No books ingested yet.")
        return

    print("\n[BOOKS] Ingested Books:")
    print("-" * 60)
    for book in books:
        print(f"  [{book[0]}] {book[1]}")
        print(f"      Chunks: {book[2]} | Ingested: {book[3][:10]}")
    print("-" * 60)

    conn.close()

def main():
    parser = argparse.ArgumentParser(description='Book Ingestion Pipeline')
    parser.add_argument('pdf_path', nargs='?', help='Path to PDF file')
    parser.add_argument('--title', help='Book title (optional)')
    parser.add_argument('--query', help='Query an ingested book')
    parser.add_argument('--list', action='store_true', help='List ingested books')
    parser.add_argument('--book-id', help='Book ID for queries')

    args = parser.parse_args()

    if args.list:
        list_books()
    elif args.query and args.book_id:
        conn = init_db()
        results = query_book(args.book_id, args.query, conn)
        print(json.dumps(results, indent=2))
        conn.close()
    elif args.pdf_path:
        result = ingest_book(args.pdf_path, args.title)
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
