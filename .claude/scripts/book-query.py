#!/usr/bin/env python3
"""
Quick book query interface with semantic coherence scoring.

Usage:
    python book-query.py "What is gradient descent?"
    python book-query.py --book <id> "query"
    python book-query.py --concepts  # List all concepts
    python book-query.py --summary <book_id>  # Get book summary tree
    python book-query.py --scored "query"  # Query with coherence scoring
"""

import sys
import json
import sqlite3
import argparse
import re
from pathlib import Path
from collections import Counter
from math import sqrt

BOOKS_DB = Path(__file__).parent.parent.parent / "daemon" / "books.db"
DAEMON_DIR = Path(__file__).parent.parent.parent / "daemon"

# Try to import controller for metrics reporting
try:
    sys.path.insert(0, str(DAEMON_DIR))
    from controller import MAPEController, Metric, MetricType
    CONTROLLER_AVAILABLE = True
except ImportError:
    CONTROLLER_AVAILABLE = False


# ============================================================================
# Semantic Coherence Scoring
# ============================================================================

def tokenize(text: str) -> list:
    """Simple tokenization - lowercase, split, remove punctuation."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    return [w for w in text.split() if len(w) > 2]


def compute_tf(tokens: list) -> dict:
    """Compute term frequency."""
    tf = Counter(tokens)
    total = len(tokens)
    return {k: v / total for k, v in tf.items()} if total > 0 else {}


def cosine_similarity(tf1: dict, tf2: dict) -> float:
    """Compute cosine similarity between two TF vectors."""
    if not tf1 or not tf2:
        return 0.0

    # Get all terms
    all_terms = set(tf1.keys()) | set(tf2.keys())

    # Compute dot product and magnitudes
    dot = sum(tf1.get(t, 0) * tf2.get(t, 0) for t in all_terms)
    mag1 = sqrt(sum(v**2 for v in tf1.values()))
    mag2 = sqrt(sum(v**2 for v in tf2.values()))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return dot / (mag1 * mag2)


def compute_coherence_score(query: str, results: list) -> dict:
    """
    Compute semantic coherence score for retrieval results.

    Metrics:
    - query_relevance: How well results match the query (avg cosine sim)
    - inter_chunk_coherence: How coherent chunks are with each other
    - coverage: Proportion of query terms found in results

    Returns dict with scores and overall coherence (0-1).
    """
    if not results:
        return {"overall": 0.0, "query_relevance": 0.0,
                "inter_chunk_coherence": 0.0, "coverage": 0.0}

    # Tokenize query
    query_tokens = tokenize(query)
    query_tf = compute_tf(query_tokens)
    query_terms = set(query_tokens)

    # Compute per-chunk metrics
    chunk_tfs = []
    relevance_scores = []
    terms_found = set()

    for r in results:
        # Get content text
        content = r.get("content", "") or r.get("definition", "")
        chunk_tokens = tokenize(content)
        chunk_tf = compute_tf(chunk_tokens)
        chunk_tfs.append(chunk_tf)

        # Query relevance (cosine similarity)
        relevance = cosine_similarity(query_tf, chunk_tf)
        relevance_scores.append(relevance)

        # Track coverage
        terms_found.update(t for t in query_terms if t in set(chunk_tokens))

    # Query relevance: average similarity
    query_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0

    # Inter-chunk coherence: how similar chunks are to each other
    inter_scores = []
    for i in range(len(chunk_tfs)):
        for j in range(i + 1, len(chunk_tfs)):
            inter_scores.append(cosine_similarity(chunk_tfs[i], chunk_tfs[j]))
    inter_chunk_coherence = sum(inter_scores) / len(inter_scores) if inter_scores else 1.0

    # Coverage: what fraction of query terms appear in results
    coverage = len(terms_found) / len(query_terms) if query_terms else 0

    # Overall coherence (weighted average)
    overall = 0.5 * query_relevance + 0.3 * coverage + 0.2 * inter_chunk_coherence

    return {
        "overall": round(overall, 4),
        "query_relevance": round(query_relevance, 4),
        "inter_chunk_coherence": round(inter_chunk_coherence, 4),
        "coverage": round(coverage, 4),
        "num_results": len(results)
    }


def report_retrieval_metrics(query: str, coherence: dict):
    """Report retrieval metrics to MAPE controller."""
    if not CONTROLLER_AVAILABLE:
        return

    try:
        ctrl = MAPEController()
        metrics = [
            Metric(
                type=MetricType.RETRIEVAL_ACCURACY,
                value=coherence["overall"],
                context={
                    "query": query[:100],
                    "query_relevance": coherence["query_relevance"],
                    "coverage": coherence["coverage"]
                }
            )
        ]
        ctrl.monitor(metrics)
    except Exception:
        pass  # Non-blocking

def query_all_books(query: str, with_scoring: bool = False) -> dict:
    """Search across all ingested books with optional coherence scoring."""
    if not BOOKS_DB.exists():
        return {"error": "No books database. Run book-ingest.py first."}

    conn = sqlite3.connect(BOOKS_DB)
    c = conn.cursor()

    results = {"query": query, "matches": []}

    # Search chunks via FTS
    c.execute('''SELECT c.book_id, b.title, c.content, c.chunk_type
        FROM chunks c
        JOIN chunks_fts fts ON c.rowid = fts.rowid
        JOIN books b ON c.book_id = b.id
        WHERE chunks_fts MATCH ?
        LIMIT 10''', (query,))

    for row in c.fetchall():
        results["matches"].append({
            "book_id": row[0],
            "book": row[1],
            "content": row[2][:400] + "..." if len(row[2]) > 400 else row[2],
            "type": row[3]
        })

    # Search concepts
    c.execute('''SELECT c.book_id, b.title, c.name, c.definition
        FROM concepts c
        JOIN books b ON c.book_id = b.id
        WHERE c.name LIKE ? OR c.definition LIKE ?
        LIMIT 5''', (f'%{query}%', f'%{query}%'))

    for row in c.fetchall():
        results["matches"].append({
            "book_id": row[0],
            "book": row[1],
            "concept": row[2],
            "definition": row[3][:300]
        })

    conn.close()

    # Add coherence scoring if requested
    if with_scoring and results["matches"]:
        coherence = compute_coherence_score(query, results["matches"])
        results["coherence"] = coherence

        # Report to controller (non-blocking)
        report_retrieval_metrics(query, coherence)

    return results

def get_summary_tree(book_id: str) -> dict:
    """Get hierarchical summary of a book."""
    conn = sqlite3.connect(BOOKS_DB)
    c = conn.cursor()

    c.execute('SELECT title, book_summary FROM books WHERE id = ?', (book_id,))
    book = c.fetchone()
    if not book:
        return {"error": f"Book {book_id} not found"}

    tree = {"title": book[0], "summary": book[1], "sections": []}

    # Get chapter-level summaries
    c.execute('''SELECT title, summary, key_concepts FROM summaries
        WHERE book_id = ? AND level IN ('chapter', 'part')
        ORDER BY rowid''', (book_id,))

    for row in c.fetchall():
        tree["sections"].append({
            "title": row[0],
            "summary": row[1],
            "concepts": json.loads(row[2]) if row[2] else []
        })

    conn.close()
    return tree

def list_concepts(book_id: str = None) -> list:
    """List all extracted concepts."""
    conn = sqlite3.connect(BOOKS_DB)
    c = conn.cursor()

    if book_id:
        c.execute('''SELECT c.name, c.definition, b.title
            FROM concepts c JOIN books b ON c.book_id = b.id
            WHERE c.book_id = ?''', (book_id,))
    else:
        c.execute('''SELECT c.name, c.definition, b.title
            FROM concepts c JOIN books b ON c.book_id = b.id''')

    concepts = []
    for row in c.fetchall():
        concepts.append({
            "name": row[0],
            "definition": row[1][:200],
            "book": row[2]
        })

    conn.close()
    return concepts

def main():
    parser = argparse.ArgumentParser(description='Query ingested books')
    parser.add_argument('query', nargs='?', help='Search query')
    parser.add_argument('--book', help='Specific book ID')
    parser.add_argument('--concepts', action='store_true', help='List concepts')
    parser.add_argument('--summary', help='Get book summary tree')
    parser.add_argument('--scored', action='store_true',
                       help='Include coherence scoring and report metrics')

    args = parser.parse_args()

    if args.concepts:
        concepts = list_concepts(args.book)
        print(json.dumps(concepts, indent=2))
    elif args.summary:
        tree = get_summary_tree(args.summary)
        print(json.dumps(tree, indent=2))
    elif args.query:
        results = query_all_books(args.query, with_scoring=args.scored)
        print(json.dumps(results, indent=2))

        # Print coherence summary if scored
        if args.scored and "coherence" in results:
            c = results["coherence"]
            print(f"\n[COHERENCE] Overall: {c['overall']:.2f} | "
                  f"Relevance: {c['query_relevance']:.2f} | "
                  f"Coverage: {c['coverage']:.2f}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
