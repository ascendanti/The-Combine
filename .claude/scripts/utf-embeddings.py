#!/usr/bin/env python3
"""
UTF Embeddings - Semantic Vector Search for Knowledge

Uses sentence-transformers (all-MiniLM-L6-v2, 80MB) for:
1. Embedding UTF claims/concepts
2. Semantic search over knowledge
3. Efficient retrieval without reading full documents

This enables token-efficient RAG:
- Instead of reading 5000 tokens of raw PDF, retrieve 200 tokens of pre-processed claims

Usage:
    python utf-embeddings.py --index      # Build/update vector index
    python utf-embeddings.py --search "query"  # Semantic search
    python utf-embeddings.py --status     # Show index stats
"""

import os
import sys
import json
import sqlite3
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Paths
PROJECT_DIR = Path(__file__).parent.parent.parent
UTF_DB = PROJECT_DIR / "daemon" / "utf_knowledge.db"
VECTOR_DB = PROJECT_DIR / "daemon" / "utf_vectors.db"
MODEL_CACHE = Path.home() / ".cache" / "sentence-transformers"

# Model config
MODEL_NAME = "all-MiniLM-L6-v2"  # 80MB, fast, good quality
EMBEDDING_DIM = 384

# Global model (lazy loaded)
_model = None

def get_model():
    """Lazy load embedding model."""
    global _model
    if _model is None:
        print(f"Loading embedding model: {MODEL_NAME}...")
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME, cache_folder=str(MODEL_CACHE))
        print(f"  Loaded ({EMBEDDING_DIM} dimensions)")
    return _model

def embed_text(text: str) -> np.ndarray:
    """Embed a single text string."""
    model = get_model()
    return model.encode(text, convert_to_numpy=True, normalize_embeddings=True)

def embed_batch(texts: List[str], batch_size: int = 32) -> np.ndarray:
    """Embed multiple texts efficiently."""
    model = get_model()
    return model.encode(texts, batch_size=batch_size, convert_to_numpy=True,
                       normalize_embeddings=True, show_progress_bar=True)

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity (embeddings are normalized)."""
    return float(np.dot(a, b))

# ============================================================================
# Vector Database
# ============================================================================

def init_vector_db() -> sqlite3.Connection:
    """Initialize vector storage."""
    conn = sqlite3.connect(VECTOR_DB)
    c = conn.cursor()

    # Vector storage (serialized numpy arrays)
    c.execute('''CREATE TABLE IF NOT EXISTS vectors (
        node_id TEXT PRIMARY KEY,
        node_type TEXT,
        content_preview TEXT,
        embedding BLOB,
        source_id TEXT,
        domain TEXT,
        claim_form TEXT,
        indexed_at TEXT
    )''')

    # Index metadata
    c.execute('''CREATE TABLE IF NOT EXISTS index_meta (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')

    c.execute('CREATE INDEX IF NOT EXISTS idx_vectors_type ON vectors(node_type)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_vectors_domain ON vectors(domain)')

    conn.commit()
    return conn

def store_vector(conn: sqlite3.Connection, node_id: str, node_type: str,
                 content: str, embedding: np.ndarray, source_id: str,
                 domain: str = "", claim_form: str = ""):
    """Store a vector in the database."""
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO vectors
        (node_id, node_type, content_preview, embedding, source_id, domain, claim_form, indexed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (node_id, node_type, content[:200], embedding.tobytes(),
         source_id, domain, claim_form, datetime.now().isoformat()))
    conn.commit()

def load_all_vectors(conn: sqlite3.Connection,
                     node_type: Optional[str] = None,
                     domain: Optional[str] = None) -> List[Tuple[str, str, np.ndarray]]:
    """Load vectors with optional filtering."""
    c = conn.cursor()

    sql = "SELECT node_id, content_preview, embedding FROM vectors WHERE 1=1"
    params = []

    if node_type:
        sql += " AND node_type = ?"
        params.append(node_type)
    if domain:
        sql += " AND domain = ?"
        params.append(domain)

    c.execute(sql, params)

    results = []
    for row in c.fetchall():
        embedding = np.frombuffer(row[2], dtype=np.float32)
        results.append((row[0], row[1], embedding))

    return results

# ============================================================================
# Indexing
# ============================================================================

def index_utf_knowledge(utf_conn: Optional[sqlite3.Connection] = None,
                        vector_conn: Optional[sqlite3.Connection] = None) -> Dict:
    """Index all UTF knowledge for semantic search."""
    if utf_conn is None:
        if not UTF_DB.exists():
            return {"success": False, "error": "UTF database not found"}
        utf_conn = sqlite3.connect(UTF_DB)

    if vector_conn is None:
        vector_conn = init_vector_db()

    stats = {"claims": 0, "concepts": 0, "assumptions": 0, "skipped": 0}

    # Check what's already indexed
    vc = vector_conn.cursor()
    uc = utf_conn.cursor()

    # Index claims
    print("Indexing claims...")
    uc.execute("SELECT claim_id, statement, source_id, domain, claim_form FROM claims")
    claims = uc.fetchall()

    new_claims = []
    for claim in claims:
        vc.execute("SELECT 1 FROM vectors WHERE node_id = ?", (claim[0],))
        if not vc.fetchone():
            new_claims.append(claim)

    if new_claims:
        texts = [c[1] for c in new_claims]
        embeddings = embed_batch(texts)

        for i, claim in enumerate(new_claims):
            store_vector(vector_conn, claim[0], "claim", claim[1],
                        embeddings[i], claim[2], claim[3] or "", claim[4] or "")
            stats["claims"] += 1

    # Index concepts
    print("Indexing concepts...")
    uc.execute("SELECT concept_id, name, definition_1liner, source_id, domain FROM concepts")
    concepts = uc.fetchall()

    new_concepts = []
    for concept in concepts:
        vc.execute("SELECT 1 FROM vectors WHERE node_id = ?", (concept[0],))
        if not vc.fetchone():
            new_concepts.append(concept)

    if new_concepts:
        # Combine name and definition for better embedding
        texts = [f"{c[1]}: {c[2] or ''}" for c in new_concepts]
        embeddings = embed_batch(texts)

        for i, concept in enumerate(new_concepts):
            store_vector(vector_conn, concept[0], "concept", texts[i],
                        embeddings[i], concept[3], concept[4] or "", "")
            stats["concepts"] += 1

    # Index assumptions
    print("Indexing assumptions...")
    uc.execute("SELECT assumption_id, statement, source_id FROM assumptions")
    assumptions = uc.fetchall()

    new_assumptions = []
    for assumption in assumptions:
        vc.execute("SELECT 1 FROM vectors WHERE node_id = ?", (assumption[0],))
        if not vc.fetchone():
            new_assumptions.append(assumption)

    if new_assumptions:
        texts = [a[1] for a in new_assumptions]
        embeddings = embed_batch(texts)

        for i, assumption in enumerate(new_assumptions):
            store_vector(vector_conn, assumption[0], "assumption", assumption[1],
                        embeddings[i], assumption[2], "", "")
            stats["assumptions"] += 1

    # Update metadata
    vc.execute('''INSERT OR REPLACE INTO index_meta (key, value) VALUES (?, ?)''',
              ("last_indexed", datetime.now().isoformat()))
    vc.execute('''INSERT OR REPLACE INTO index_meta (key, value) VALUES (?, ?)''',
              ("total_vectors", str(stats["claims"] + stats["concepts"] + stats["assumptions"])))
    vector_conn.commit()

    return {"success": True, "stats": stats}

# ============================================================================
# Semantic Search
# ============================================================================

def semantic_search(query: str,
                    k: int = 5,
                    node_type: Optional[str] = None,
                    domain: Optional[str] = None,
                    min_score: float = 0.3) -> List[Dict]:
    """
    Semantic search over UTF knowledge.

    Returns compact results for token-efficient retrieval:
    - node_id: for tracing
    - content: pre-processed text (not raw PDF)
    - score: relevance
    - type: claim/concept/assumption
    """
    vector_conn = init_vector_db()

    # Embed query
    query_embedding = embed_text(query)

    # Load candidate vectors
    candidates = load_all_vectors(vector_conn, node_type=node_type, domain=domain)

    if not candidates:
        return []

    # Compute similarities
    scored = []
    for node_id, content, embedding in candidates:
        score = cosine_similarity(query_embedding, embedding)
        if score >= min_score:
            scored.append((node_id, content, score))

    # Sort by score
    scored.sort(key=lambda x: x[2], reverse=True)

    # Return top k
    results = []
    for node_id, content, score in scored[:k]:
        # Get full node info
        c = vector_conn.cursor()
        c.execute("SELECT node_type, domain, claim_form, source_id FROM vectors WHERE node_id = ?",
                 (node_id,))
        row = c.fetchone()

        results.append({
            "node_id": node_id,
            "content": content,
            "score": round(score, 3),
            "type": row[0] if row else "unknown",
            "domain": row[1] if row else "",
            "claim_form": row[2] if row else "",
            "source_id": row[3] if row else ""
        })

    vector_conn.close()
    return results

def format_search_for_context(results: List[Dict], max_tokens: int = 500) -> str:
    """
    Format search results as compact context injection.

    Target: Replace 5000 tokens of raw PDF with ~200 tokens of pre-processed claims.
    """
    if not results:
        return ""

    lines = ["<utf-rag>"]
    estimated_tokens = 10  # Header overhead

    for r in results:
        # Estimate tokens (~1.3 per word)
        content_tokens = len(r["content"].split()) * 1.3

        if estimated_tokens + content_tokens > max_tokens:
            break

        # Compact format
        line = f"[{r['type']}:{r['score']}] {r['content']}"
        if r.get("claim_form"):
            line = f"[{r['claim_form']}:{r['score']}] {r['content']}"

        lines.append(line)
        estimated_tokens += content_tokens

    lines.append("</utf-rag>")
    return "\n".join(lines)

# ============================================================================
# Status
# ============================================================================

def show_status():
    """Show vector index statistics."""
    vector_conn = init_vector_db()
    c = vector_conn.cursor()

    print("=" * 60)
    print("UTF Vector Index Status")
    print("=" * 60)

    # Total vectors
    c.execute("SELECT COUNT(*) FROM vectors")
    total = c.fetchone()[0]
    print(f"Total vectors: {total}")

    # By type
    c.execute("SELECT node_type, COUNT(*) FROM vectors GROUP BY node_type")
    for row in c.fetchall():
        print(f"  {row[0]}: {row[1]}")

    # By domain
    c.execute("SELECT domain, COUNT(*) FROM vectors WHERE domain != '' GROUP BY domain ORDER BY COUNT(*) DESC LIMIT 5")
    domains = c.fetchall()
    if domains:
        print(f"\nTop domains: {', '.join(f'{d[0]}({d[1]})' for d in domains)}")

    # Last indexed
    c.execute("SELECT value FROM index_meta WHERE key = 'last_indexed'")
    row = c.fetchone()
    if row:
        print(f"\nLast indexed: {row[0]}")

    # Model info
    print(f"\nModel: {MODEL_NAME} ({EMBEDDING_DIM} dim)")

    vector_conn.close()

# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='UTF Semantic Vector Search')
    parser.add_argument('--index', action='store_true', help='Build/update vector index')
    parser.add_argument('--search', type=str, help='Semantic search query')
    parser.add_argument('--k', type=int, default=5, help='Number of results')
    parser.add_argument('--type', type=str, help='Filter by node type (claim/concept/assumption)')
    parser.add_argument('--domain', type=str, help='Filter by domain')
    parser.add_argument('--status', action='store_true', help='Show index status')
    parser.add_argument('--compact', action='store_true', help='Output as compact context')

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.index:
        result = index_utf_knowledge()
        print(json.dumps(result, indent=2))
    elif args.search:
        results = semantic_search(
            args.search,
            k=args.k,
            node_type=args.type,
            domain=args.domain
        )

        if args.compact:
            print(format_search_for_context(results))
        else:
            print(json.dumps(results, indent=2))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
