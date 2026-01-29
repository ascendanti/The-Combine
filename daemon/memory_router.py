#!/usr/bin/env python3
"""
Unified Memory Router - Single interface to all memory systems.

Routes queries to appropriate backends and aggregates results.
Prevents memory system clashes through unified interface.

WIRING (2026-01-26):
- L1 Cache: Dragonfly (Redis-compatible) for fast lookups
- L2: SQLite daemon memory for learnings/decisions
- L3: Knowledge Graph for entity relations
"""

import json
import sys
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

# Add daemon directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Local imports
from memory import Memory, Learning, Decision

# WIRED: Dragonfly L1 cache
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# WIRED: Sentence Transformers for true semantic matching
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    EMBEDDINGS_AVAILABLE = True
    # Load model once at module level (lazy loading)
    _embedding_model = None
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    _embedding_model = None

# WIRED (2026-01-28): Token compression for cached results
try:
    from headroom_optimizer import compress_search_results
    HEADROOM_AVAILABLE = True
except ImportError:
    HEADROOM_AVAILABLE = False
    compress_search_results = None


def _get_embedding_model():
    """Lazy load embedding model."""
    global _embedding_model
    if _embedding_model is None and EMBEDDINGS_AVAILABLE:
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model

KNOWLEDGE_GRAPH_PATH = Path.home() / ".claude" / "memory" / "knowledge-graph.jsonl"
CACHE_TTL = 300  # 5 minutes for search results

# Two-stage semantic matching thresholds (inspired by prompt-cache)
SIMILARITY_HIGH = 0.85   # Immediately return cached (high confidence match)
SIMILARITY_LOW = 0.5     # Bypass cache entirely (too different)
# Gray zone (0.5-0.85) could trigger LLM verification, but we skip for performance


@dataclass
class UnifiedResult:
    """Unified search result across all memory systems."""
    source: str  # "daemon", "knowledge_graph", "token_cache"
    content: str
    relevance: float
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "content": self.content,
            "relevance": self.relevance,
            "metadata": self.metadata
        }


class MemoryRouter:
    """
    Unified interface to all memory systems.

    WIRED Backends (2026-01-26):
    - L1: Dragonfly/Redis cache - Fast lookup (< 100ms)
    - L2: daemon/memory.py (SQLite) - Learnings & decisions
    - L3: knowledge-graph.jsonl - Entity relations
    """

    def __init__(self):
        self._daemon_memory = Memory(backend="auto")
        self._kg_path = KNOWLEDGE_GRAPH_PATH
        # WIRED: L1 Dragonfly cache
        self._cache = self._init_cache()

    def _init_cache(self) -> Optional[Any]:
        """Initialize Dragonfly/Redis cache connection."""
        if not REDIS_AVAILABLE:
            return None
        try:
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            r.ping()
            return r
        except Exception:
            return None

    def _cache_key(self, query: str, k: int) -> str:
        """Generate cache key for a search query."""
        query_hash = hashlib.sha256(f"{query}:{k}".encode()).hexdigest()[:16]
        return f"claude:memory_router:{query_hash}"

    def _normalize_query(self, query: str) -> set:
        """Normalize query to word set for semantic matching."""
        # Simple tokenization and normalization
        words = set(query.lower().split())
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                      'to', 'of', 'and', 'or', 'in', 'on', 'at', 'for', 'with'}
        return words - stop_words

    def _semantic_similarity(self, query1: str, query2: str) -> float:
        """
        Calculate semantic similarity between queries.

        Uses embeddings if available (cosine similarity), falls back to Jaccard.
        """
        # Try embeddings first (true semantic matching)
        if EMBEDDINGS_AVAILABLE:
            try:
                model = _get_embedding_model()
                if model is not None:
                    embeddings = model.encode([query1, query2])
                    # Cosine similarity
                    cos_sim = np.dot(embeddings[0], embeddings[1]) / (
                        np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
                    )
                    return float(cos_sim)
            except Exception:
                pass  # Fall through to Jaccard

        # Fallback: Jaccard similarity (word overlap)
        words1 = self._normalize_query(query1)
        words2 = self._normalize_query(query2)
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0

    def _cache_get(self, key: str) -> Optional[List[Dict]]:
        """Get from L1 cache."""
        if not self._cache:
            return None
        try:
            data = self._cache.get(key)
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None

    def _cache_get_semantic(self, query: str, k: int) -> Optional[List[Dict]]:
        """
        Two-stage semantic cache lookup (inspired by prompt-cache architecture).

        Stage 1: High similarity (>0.85) → Return immediately
        Stage 2: Low similarity (<0.5) → Skip entirely
        Gray zone: Accept for now (could add LLM verification later)
        """
        if not self._cache:
            return None

        try:
            # Get all cached query keys
            keys = self._cache.keys("claude:memory_router:*")
            if not keys:
                return None

            best_match = None
            best_similarity = 0

            # Check each cached query for semantic similarity
            for cached_key in keys[:50]:  # Limit to 50 for performance
                if ":meta" in str(cached_key):
                    continue  # Skip metadata keys

                # Get the original query from metadata
                meta_key = f"{cached_key}:meta"
                meta = self._cache.get(meta_key)
                if not meta:
                    continue

                meta_data = json.loads(meta)
                cached_query = meta_data.get("query", "")
                cached_k = meta_data.get("k", 0)

                if cached_k < k:
                    continue  # Need at least as many results

                # Two-stage similarity check
                similarity = self._semantic_similarity(query, cached_query)

                if similarity < SIMILARITY_LOW:
                    continue  # Too different, skip

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = cached_key

                # High confidence match - return immediately
                if similarity >= SIMILARITY_HIGH:
                    data = self._cache.get(cached_key)
                    if data:
                        return json.loads(data)

            # Return best gray-zone match if found
            if best_match and best_similarity >= SIMILARITY_LOW:
                data = self._cache.get(best_match)
                if data:
                    return json.loads(data)

        except Exception:
            pass
        return None

    def _cache_set(self, key: str, results: List[Dict], query: str = "", k: int = 0, ttl: int = CACHE_TTL):
        """Set in L1 cache with metadata for semantic matching."""
        if not self._cache:
            return
        try:
            # WIRED (2026-01-28): Compress large result sets before caching
            cache_data = results
            if HEADROOM_AVAILABLE and len(results) > 15:
                try:
                    cache_data = compress_search_results(results, query=query, max_results=20)
                except Exception:
                    pass  # Keep original on compression error

            self._cache.setex(key, ttl, json.dumps(cache_data))
            # Store metadata for semantic matching
            if query:
                meta_key = f"{key}:meta"
                self._cache.setex(meta_key, ttl, json.dumps({"query": query, "k": k}))
        except Exception:
            pass

    @property
    def active_backends(self) -> List[str]:
        """List active memory backends."""
        backends = []
        if self._cache:
            backends.append("dragonfly:l1_cache")
        backends.append(f"daemon:{self._daemon_memory.backend_name}")
        if self._kg_path.exists():
            backends.append("knowledge_graph")
        return backends

    # =========================================================================
    # Unified Store Operations
    # =========================================================================

    def store(self, content: str, content_type: str = "learning", **kwargs) -> Dict[str, Any]:
        """
        Store content to appropriate backend based on type.

        Args:
            content: The content to store
            content_type: "learning", "decision", "entity", "relation"
            **kwargs: Type-specific parameters

        Returns:
            Dict with storage confirmation and IDs
        """
        results = {"stored_to": [], "ids": {}}

        if content_type == "learning":
            learning = self._daemon_memory.store_learning(
                content=content,
                context=kwargs.get("context", ""),
                tags=kwargs.get("tags", []),
                confidence=kwargs.get("confidence", "medium")
            )
            results["stored_to"].append("daemon")
            results["ids"]["daemon"] = learning.id

        elif content_type == "decision":
            decision = self._daemon_memory.store_decision(
                decision=content,
                rationale=kwargs.get("rationale", ""),
                topic=kwargs.get("topic", "")
            )
            results["stored_to"].append("daemon")
            results["ids"]["daemon"] = decision.id

        elif content_type == "entity":
            entity_id = self._store_entity(
                name=kwargs.get("name", ""),
                entity_type=kwargs.get("entity_type", "unknown"),
                observations=[content] + kwargs.get("observations", [])
            )
            results["stored_to"].append("knowledge_graph")
            results["ids"]["knowledge_graph"] = entity_id

        elif content_type == "relation":
            self._store_relation(
                from_entity=kwargs.get("from_entity", ""),
                to_entity=kwargs.get("to_entity", ""),
                relation_type=content
            )
            results["stored_to"].append("knowledge_graph")

        return results

    # =========================================================================
    # Unified Search Operations
    # =========================================================================

    def search(self, query: str, k: int = 10, sources: Optional[List[str]] = None) -> List[UnifiedResult]:
        """
        Search across all memory systems.

        WIRED: Now uses L1 Dragonfly cache for fast repeated queries.

        Args:
            query: Search query
            k: Max results per source
            sources: List of sources to search ["daemon", "knowledge_graph"]
                     If None, searches all.

        Returns:
            List of UnifiedResult sorted by relevance
        """
        if sources is None:
            sources = ["daemon", "knowledge_graph"]

        # WIRED: Check L1 cache first (exact match)
        cache_key = self._cache_key(query, k)
        cached = self._cache_get(cache_key)
        if cached:
            # Reconstruct UnifiedResult from cached dicts
            return [UnifiedResult(**r) for r in cached]

        # WIRED: Try semantic cache (fuzzy match)
        semantic_cached = self._cache_get_semantic(query, k)
        if semantic_cached:
            return [UnifiedResult(**r) for r in semantic_cached]

        results = []

        # Search daemon memory
        if "daemon" in sources:
            learnings = self._daemon_memory.recall_learnings(query, k)
            for i, l in enumerate(learnings):
                results.append(UnifiedResult(
                    source="daemon:learning",
                    content=l.content,
                    relevance=1.0 - (i * 0.1),  # Decay by rank
                    metadata={
                        "id": l.id,
                        "context": l.context,
                        "tags": l.tags,
                        "confidence": l.confidence,
                        "created_at": l.created_at
                    }
                ))

            decisions = self._daemon_memory.recall_decisions(query)
            for i, d in enumerate(decisions[:k]):
                results.append(UnifiedResult(
                    source="daemon:decision",
                    content=d.decision,
                    relevance=0.9 - (i * 0.1),
                    metadata={
                        "id": d.id,
                        "rationale": d.rationale,
                        "topic": d.topic,
                        "created_at": d.created_at
                    }
                ))

        # Search knowledge graph
        if "knowledge_graph" in sources:
            kg_results = self._search_knowledge_graph(query, k)
            results.extend(kg_results)

        # Sort by relevance
        results.sort(key=lambda r: r.relevance, reverse=True)
        final_results = results[:k * 2]  # Return up to 2x k across all sources

        # WIRED: Cache results in L1 for next time (with semantic metadata)
        self._cache_set(cache_key, [r.to_dict() for r in final_results], query=query, k=k)

        return final_results

    # =========================================================================
    # Knowledge Graph Operations
    # =========================================================================

    def _store_entity(self, name: str, entity_type: str, observations: List[str]) -> str:
        """Store entity in knowledge graph."""
        self._kg_path.parent.mkdir(parents=True, exist_ok=True)

        entity_id = f"entity_{name.lower().replace(' ', '_')}"
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "entity",
            "data": {
                "id": entity_id,
                "name": name,
                "entityType": entity_type,
                "observations": observations
            }
        }

        with open(self._kg_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')

        return entity_id

    def _store_relation(self, from_entity: str, to_entity: str, relation_type: str):
        """Store relation in knowledge graph."""
        self._kg_path.parent.mkdir(parents=True, exist_ok=True)

        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "relation",
            "data": {
                "from": from_entity,
                "to": to_entity,
                "relationType": relation_type
            }
        }

        with open(self._kg_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')

    def _search_knowledge_graph(self, query: str, k: int) -> List[UnifiedResult]:
        """Search knowledge graph for matching entities."""
        results = []
        if not self._kg_path.exists():
            return results

        query_lower = query.lower()
        with open(self._kg_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "entity":
                        data = entry.get("data", {})
                        name = data.get("name", "").lower()
                        observations = " ".join(data.get("observations", []))

                        # Simple relevance scoring
                        score = 0.0
                        if query_lower in name:
                            score = 0.9
                        elif query_lower in observations.lower():
                            score = 0.6
                        elif any(word in observations.lower() for word in query_lower.split()):
                            score = 0.4

                        if score > 0:
                            results.append(UnifiedResult(
                                source="knowledge_graph:entity",
                                content=data.get("name", ""),
                                relevance=score,
                                metadata={
                                    "entity_type": data.get("entityType"),
                                    "observations": data.get("observations", []),
                                    "timestamp": entry.get("timestamp")
                                }
                            ))
                except json.JSONDecodeError:
                    continue

        results.sort(key=lambda r: r.relevance, reverse=True)
        return results[:k]

    # =========================================================================
    # Status & Diagnostics
    # =========================================================================

    def status(self) -> Dict[str, Any]:
        """Get status of all memory systems."""
        status = {
            "backends": self.active_backends,
            "daemon_backend": self._daemon_memory.backend_name,
            "knowledge_graph": {
                "exists": self._kg_path.exists(),
                "path": str(self._kg_path),
                "entries": 0
            }
        }

        if self._kg_path.exists():
            with open(self._kg_path, 'r') as f:
                status["knowledge_graph"]["entries"] = sum(1 for _ in f)

        # Count daemon entries
        try:
            status["daemon_learnings"] = len(self._daemon_memory.list_learnings(limit=1000))
            status["daemon_decisions"] = len(self._daemon_memory.list_decisions(limit=1000))
        except:
            status["daemon_learnings"] = "unknown"
            status["daemon_decisions"] = "unknown"

        return status


# =============================================================================
# CLI Interface
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Unified Memory Router CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Status
    subparsers.add_parser("status", help="Show memory system status")

    # Search
    search_parser = subparsers.add_parser("search", help="Search all memory systems")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("-k", type=int, default=5, help="Max results per source")

    # Store
    store_parser = subparsers.add_parser("store", help="Store content")
    store_parser.add_argument("content", help="Content to store")
    store_parser.add_argument("--type", choices=["learning", "decision", "entity"],
                             default="learning", help="Content type")
    store_parser.add_argument("--context", default="", help="Context (for learnings)")
    store_parser.add_argument("--tags", default="", help="Comma-separated tags")
    store_parser.add_argument("--confidence", default="medium", help="Confidence level")
    store_parser.add_argument("--name", default="", help="Entity name (for entities)")
    store_parser.add_argument("--entity-type", default="concept", help="Entity type")

    args = parser.parse_args()
    router = MemoryRouter()

    if args.command == "status":
        status = router.status()
        print(json.dumps(status, indent=2))

    elif args.command == "search":
        results = router.search(args.query, args.k)
        if not results:
            print("No results found.")
        for r in results:
            print(f"\n[{r.source}] relevance={r.relevance:.2f}")
            print(f"  {r.content[:100]}...")
            if r.metadata.get("context"):
                print(f"  context: {r.metadata['context'][:50]}")

    elif args.command == "store":
        kwargs = {
            "context": args.context,
            "tags": [t.strip() for t in args.tags.split(",") if t.strip()],
            "confidence": args.confidence,
            "name": args.name or args.content[:30],
            "entity_type": args.entity_type
        }
        result = router.store(args.content, args.type, **kwargs)
        print(json.dumps(result, indent=2))

    else:
        parser.print_help()
