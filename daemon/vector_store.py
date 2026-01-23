#!/usr/bin/env python3
"""
Vector Store - Semantic search with embeddings

Fixes the missing RAG components:
- Embeddings: Via model_router (LocalAI → OpenAI → fallback)
- Vector Search: Cosine similarity over stored embeddings
- Reranking: BM25 + vector hybrid scoring

Storage: SQLite with numpy serialization (no external vector DB needed)

Usage:
    from vector_store import VectorStore
    store = VectorStore()

    # Add documents
    store.add("doc_id", "content here", metadata={"book": "xyz"})

    # Search
    results = store.search("query text", k=5)

    # Hybrid search (vector + keyword)
    results = store.hybrid_search("query", k=5, alpha=0.7)
"""

import json
import sqlite3
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
import struct

VECTOR_DB = Path(__file__).parent / "vectors.db"

# ============================================================================
# Data Models
# ============================================================================

@dataclass
class SearchResult:
    """A search result with scoring."""
    doc_id: str
    content: str
    score: float
    vector_score: float = 0.0
    bm25_score: float = 0.0
    metadata: Dict[str, Any] = None

# ============================================================================
# Embedding Serialization (numpy-free)
# ============================================================================

def serialize_embedding(embedding: List[float]) -> bytes:
    """Serialize embedding to bytes (no numpy needed)."""
    return struct.pack(f'{len(embedding)}f', *embedding)

def deserialize_embedding(data: bytes) -> List[float]:
    """Deserialize bytes to embedding list."""
    n = len(data) // 4  # 4 bytes per float
    return list(struct.unpack(f'{n}f', data))

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b):
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)

# ============================================================================
# BM25 Scoring (for hybrid search)
# ============================================================================

class BM25:
    """BM25 ranking for keyword search."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_freqs: Dict[str, int] = {}
        self.doc_lengths: Dict[str, int] = {}
        self.avg_doc_length: float = 0.0
        self.total_docs: int = 0
        self.inverted_index: Dict[str, List[Tuple[str, int]]] = {}

    def tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        return re.findall(r'\w+', text.lower())

    def add_document(self, doc_id: str, content: str):
        """Index a document."""
        tokens = self.tokenize(content)
        self.doc_lengths[doc_id] = len(tokens)
        self.total_docs += 1
        self.avg_doc_length = sum(self.doc_lengths.values()) / self.total_docs

        token_counts = Counter(tokens)
        for token, count in token_counts.items():
            if token not in self.inverted_index:
                self.inverted_index[token] = []
                self.doc_freqs[token] = 0
            self.inverted_index[token].append((doc_id, count))
            self.doc_freqs[token] += 1

    def score(self, query: str, doc_id: str, doc_content: str) -> float:
        """Score a document against a query."""
        query_tokens = self.tokenize(query)
        doc_tokens = self.tokenize(doc_content)
        doc_token_counts = Counter(doc_tokens)
        doc_length = len(doc_tokens)

        score = 0.0
        for token in query_tokens:
            if token not in doc_token_counts:
                continue

            tf = doc_token_counts[token]
            df = self.doc_freqs.get(token, 1)
            idf = math.log((self.total_docs - df + 0.5) / (df + 0.5) + 1)

            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_length / max(self.avg_doc_length, 1))
            score += idf * numerator / denominator

        return score

# ============================================================================
# Vector Store
# ============================================================================

class VectorStore:
    """
    SQLite-based vector store with hybrid search.

    Features:
    - Embeddings via model_router (LocalAI/OpenAI)
    - Cosine similarity search
    - BM25 keyword search
    - Hybrid ranking (configurable alpha)
    """

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or VECTOR_DB
        self.bm25 = BM25()
        self._router = None  # Lazy load
        self._init_db()
        self._load_bm25_index()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            content TEXT,
            embedding BLOB,
            metadata TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')

        c.execute('''CREATE INDEX IF NOT EXISTS idx_doc_created
            ON documents(created_at)''')

        conn.commit()
        conn.close()

    def _load_bm25_index(self):
        """Load existing documents into BM25 index."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT doc_id, content FROM documents')
        for doc_id, content in c.fetchall():
            self.bm25.add_document(doc_id, content)
        conn.close()

    @property
    def router(self):
        """Lazy-load model router."""
        if self._router is None:
            from model_router import ModelRouter
            self._router = ModelRouter()
        return self._router

    def add(self, doc_id: str, content: str, metadata: Dict = None,
            embedding: List[float] = None) -> bool:
        """
        Add document with embedding.

        If no embedding provided, generates via model_router.
        """
        # Generate embedding if not provided
        if embedding is None:
            result = self.router.embed(content[:8000])  # Truncate for embedding
            if result.get("embedding"):
                embedding = result["embedding"]
            else:
                # No embedding available - store without
                embedding = None

        # Store
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''INSERT OR REPLACE INTO documents
            (doc_id, content, embedding, metadata)
            VALUES (?, ?, ?, ?)''',
            (doc_id, content,
             serialize_embedding(embedding) if embedding else None,
             json.dumps(metadata) if metadata else None))

        conn.commit()
        conn.close()

        # Update BM25 index
        self.bm25.add_document(doc_id, content)

        return True

    def add_batch(self, documents: List[Dict]) -> int:
        """
        Add multiple documents.

        Each dict: {"doc_id": str, "content": str, "metadata": dict}
        """
        count = 0
        for doc in documents:
            if self.add(doc["doc_id"], doc["content"], doc.get("metadata")):
                count += 1
        return count

    def search(self, query: str, k: int = 5,
               filter_metadata: Dict = None) -> List[SearchResult]:
        """
        Pure vector search using cosine similarity.
        """
        # Get query embedding
        result = self.router.embed(query)
        if not result.get("embedding"):
            # Fallback to BM25 only
            return self.keyword_search(query, k, filter_metadata)

        query_embedding = result["embedding"]

        # Fetch all documents with embeddings
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        if filter_metadata:
            # Simple metadata filter (exact match on one key)
            key, value = list(filter_metadata.items())[0]
            c.execute('''SELECT doc_id, content, embedding, metadata
                FROM documents WHERE embedding IS NOT NULL
                AND json_extract(metadata, ?) = ?''',
                (f'$.{key}', value))
        else:
            c.execute('''SELECT doc_id, content, embedding, metadata
                FROM documents WHERE embedding IS NOT NULL''')

        # Score all documents
        scores = []
        for doc_id, content, emb_bytes, meta_json in c.fetchall():
            doc_embedding = deserialize_embedding(emb_bytes)
            sim = cosine_similarity(query_embedding, doc_embedding)
            scores.append(SearchResult(
                doc_id=doc_id,
                content=content,
                score=sim,
                vector_score=sim,
                metadata=json.loads(meta_json) if meta_json else {}
            ))

        conn.close()

        # Sort by score and return top-k
        scores.sort(key=lambda x: x.score, reverse=True)
        return scores[:k]

    def keyword_search(self, query: str, k: int = 5,
                       filter_metadata: Dict = None) -> List[SearchResult]:
        """BM25 keyword search."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        if filter_metadata:
            key, value = list(filter_metadata.items())[0]
            c.execute('''SELECT doc_id, content, metadata
                FROM documents WHERE json_extract(metadata, ?) = ?''',
                (f'$.{key}', value))
        else:
            c.execute('SELECT doc_id, content, metadata FROM documents')

        scores = []
        for doc_id, content, meta_json in c.fetchall():
            bm25_score = self.bm25.score(query, doc_id, content)
            if bm25_score > 0:
                scores.append(SearchResult(
                    doc_id=doc_id,
                    content=content,
                    score=bm25_score,
                    bm25_score=bm25_score,
                    metadata=json.loads(meta_json) if meta_json else {}
                ))

        conn.close()

        scores.sort(key=lambda x: x.score, reverse=True)
        return scores[:k]

    def hybrid_search(self, query: str, k: int = 5,
                      alpha: float = 0.7,
                      filter_metadata: Dict = None) -> List[SearchResult]:
        """
        Hybrid search: alpha * vector + (1-alpha) * BM25

        alpha=1.0 = pure vector search
        alpha=0.0 = pure keyword search
        alpha=0.7 = recommended default (favor semantic)
        """
        # Get both result sets
        vector_results = self.search(query, k * 2, filter_metadata)
        keyword_results = self.keyword_search(query, k * 2, filter_metadata)

        # Normalize scores
        if vector_results:
            max_v = max(r.vector_score for r in vector_results) or 1
            for r in vector_results:
                r.vector_score /= max_v

        if keyword_results:
            max_b = max(r.bm25_score for r in keyword_results) or 1
            for r in keyword_results:
                r.bm25_score /= max_b

        # Merge by doc_id
        merged = {}
        for r in vector_results:
            merged[r.doc_id] = r

        for r in keyword_results:
            if r.doc_id in merged:
                merged[r.doc_id].bm25_score = r.bm25_score
            else:
                merged[r.doc_id] = r

        # Compute hybrid score
        results = []
        for r in merged.values():
            r.score = alpha * r.vector_score + (1 - alpha) * r.bm25_score
            results.append(r)

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:k]

    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get a document by ID."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT content, metadata FROM documents WHERE doc_id = ?', (doc_id,))
        row = c.fetchone()
        conn.close()

        if row:
            return {
                "doc_id": doc_id,
                "content": row[0],
                "metadata": json.loads(row[1]) if row[1] else {}
            }
        return None

    def delete(self, doc_id: str) -> bool:
        """Delete a document."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('DELETE FROM documents WHERE doc_id = ?', (doc_id,))
        deleted = c.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def count(self) -> int:
        """Count documents."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM documents')
        count = c.fetchone()[0]
        conn.close()
        return count

    def stats(self) -> Dict:
        """Get store statistics."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('SELECT COUNT(*) FROM documents')
        total = c.fetchone()[0]

        c.execute('SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL')
        with_embeddings = c.fetchone()[0]

        conn.close()

        return {
            "total_documents": total,
            "with_embeddings": with_embeddings,
            "without_embeddings": total - with_embeddings,
            "bm25_indexed": self.bm25.total_docs
        }

# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Vector Store')
    parser.add_argument('--stats', action='store_true', help='Show stats')
    parser.add_argument('--search', type=str, help='Search query')
    parser.add_argument('--hybrid', type=str, help='Hybrid search query')
    parser.add_argument('-k', type=int, default=5, help='Number of results')
    parser.add_argument('--add', type=str, help='Add document (content)')
    parser.add_argument('--id', type=str, help='Document ID for add')

    args = parser.parse_args()
    store = VectorStore()

    if args.stats:
        print(json.dumps(store.stats(), indent=2))
    elif args.search:
        results = store.search(args.search, args.k)
        for r in results:
            print(f"[{r.score:.3f}] {r.doc_id}: {r.content[:100]}...")
    elif args.hybrid:
        results = store.hybrid_search(args.hybrid, args.k)
        for r in results:
            print(f"[{r.score:.3f}] (v:{r.vector_score:.2f} b:{r.bm25_score:.2f}) {r.doc_id}: {r.content[:100]}...")
    elif args.add and args.id:
        store.add(args.id, args.add)
        print(f"Added document {args.id}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
