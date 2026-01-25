#!/usr/bin/env python3
"""
Claim Similarity Index - Cross-paper claim matching using UTF closeness values.

Phase 10.4: Enables finding related claims across different papers by:
1. Slug code matching (fast, deterministic)
2. Taxonomy distance (hierarchical closeness)
3. Semantic similarity via embeddings (deep matching)
4. Network graph clustering (structural relationships)

Usage:
    python claim_similarity.py index --rebuild    # Rebuild index from UTF DB
    python claim_similarity.py find "claim text"  # Find similar claims
    python claim_similarity.py clusters           # Show claim clusters
"""

import os
import json
import sqlite3
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ============================================================================
# Configuration
# ============================================================================

DB_PATH = Path(os.environ.get("UTF_DB_PATH", Path(__file__).parent / "utf_knowledge.db"))
INDEX_PATH = Path(os.environ.get("SIMILARITY_INDEX", Path(__file__).parent / "claim_index.json"))

# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ClaimIndex:
    """Indexed claim for similarity search."""
    claim_id: str
    slug_code: str
    statement: str
    source_id: str
    source_title: str
    taxonomy_tags: List[str]
    claim_form: str
    embedding: Optional[List[float]] = None

@dataclass
class SimilarityResult:
    """Result of similarity search."""
    target_claim_id: str
    matched_claim_id: str
    matched_statement: str
    matched_source: str
    similarity_score: float
    match_type: str  # slug_exact, slug_partial, taxonomy, semantic, cluster
    common_tags: List[str] = field(default_factory=list)

@dataclass
class ClaimCluster:
    """Cluster of related claims."""
    cluster_id: str
    centroid_slug: str
    claims: List[str]  # claim_ids
    sources: List[str]  # source_ids
    common_taxonomy: List[str]
    cohesion_score: float

# ============================================================================
# Similarity Metrics
# ============================================================================

def slug_similarity(slug_a: str, slug_b: str) -> float:
    """Compute Jaccard similarity between slug codes."""
    if not slug_a or not slug_b:
        return 0.0
    parts_a = set(slug_a.lower().split('-'))
    parts_b = set(slug_b.lower().split('-'))
    intersection = parts_a & parts_b
    union = parts_a | parts_b
    return len(intersection) / len(union) if union else 0.0

def taxonomy_distance(tags_a: List[str], tags_b: List[str]) -> float:
    """Compute hierarchical distance between taxonomy paths."""
    if not tags_a or not tags_b:
        return 1.0  # Maximum distance

    # Find common prefix length
    common_len = 0
    for i in range(min(len(tags_a), len(tags_b))):
        if tags_a[i].lower() == tags_b[i].lower():
            common_len += 1
        else:
            break

    # Distance = 1 - (common_prefix / max_depth)
    max_depth = max(len(tags_a), len(tags_b))
    return 1.0 - (common_len / max_depth) if max_depth > 0 else 0.0

def utf_closeness(claim_a: ClaimIndex, claim_b: ClaimIndex) -> Dict[str, float]:
    """
    Compute UTF closeness value between two claims.

    Returns composite score from multiple metrics:
    - slug_sim: Slug code similarity (0-1)
    - taxonomy_sim: Taxonomy path similarity (0-1)
    - form_match: Claim form match (0 or 1)
    - composite: Weighted average
    """
    slug_sim = slug_similarity(claim_a.slug_code, claim_b.slug_code)
    taxonomy_sim = 1.0 - taxonomy_distance(claim_a.taxonomy_tags, claim_b.taxonomy_tags)
    form_match = 1.0 if claim_a.claim_form == claim_b.claim_form else 0.0

    # Weighted composite (slug most important for semantic match)
    composite = (slug_sim * 0.5) + (taxonomy_sim * 0.3) + (form_match * 0.2)

    return {
        "slug_similarity": slug_sim,
        "taxonomy_similarity": taxonomy_sim,
        "form_match": form_match,
        "composite": composite
    }

# ============================================================================
# Index Operations
# ============================================================================

class ClaimSimilarityIndex:
    """Index for fast claim similarity lookup."""

    def __init__(self, db_path: Path = DB_PATH, index_path: Path = INDEX_PATH):
        self.db_path = db_path
        self.index_path = index_path
        self.claims: Dict[str, ClaimIndex] = {}
        self.slug_index: Dict[str, List[str]] = defaultdict(list)  # slug_part -> claim_ids
        self.taxonomy_index: Dict[str, List[str]] = defaultdict(list)  # tag -> claim_ids
        self.clusters: List[ClaimCluster] = []

    def load(self) -> bool:
        """Load index from file."""
        if not self.index_path.exists():
            return False
        try:
            with open(self.index_path, 'r') as f:
                data = json.load(f)
            self.claims = {k: ClaimIndex(**v) for k, v in data.get("claims", {}).items()}
            self.slug_index = defaultdict(list, data.get("slug_index", {}))
            self.taxonomy_index = defaultdict(list, data.get("taxonomy_index", {}))
            self.clusters = [ClaimCluster(**c) for c in data.get("clusters", [])]
            return True
        except Exception as e:
            print(f"[ERROR] Loading index: {e}")
            return False

    def save(self):
        """Save index to file."""
        data = {
            "claims": {k: asdict(v) for k, v in self.claims.items()},
            "slug_index": dict(self.slug_index),
            "taxonomy_index": dict(self.taxonomy_index),
            "clusters": [asdict(c) for c in self.clusters],
            "updated_at": datetime.now().isoformat()
        }
        with open(self.index_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"[OK] Index saved: {len(self.claims)} claims, {len(self.clusters)} clusters")

    def rebuild_from_db(self):
        """Rebuild index from UTF knowledge database."""
        if not self.db_path.exists():
            print(f"[ERROR] Database not found: {self.db_path}")
            return

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all claims with source info
        cursor.execute("""
            SELECT c.claim_id, c.statement, c.claim_form, c.source_id,
                   c.slug_code, c.taxonomy_tags, s.title as source_title
            FROM claims c
            LEFT JOIN sources s ON c.source_id = s.source_id
        """)

        self.claims.clear()
        self.slug_index.clear()
        self.taxonomy_index.clear()

        for row in cursor.fetchall():
            taxonomy = json.loads(row["taxonomy_tags"]) if row["taxonomy_tags"] else []

            claim = ClaimIndex(
                claim_id=row["claim_id"],
                slug_code=row["slug_code"] or "",
                statement=row["statement"],
                source_id=row["source_id"],
                source_title=row["source_title"] or "Unknown",
                taxonomy_tags=taxonomy,
                claim_form=row["claim_form"]
            )

            self.claims[claim.claim_id] = claim

            # Index by slug parts
            if claim.slug_code:
                for part in claim.slug_code.split('-'):
                    self.slug_index[part.lower()].append(claim.claim_id)

            # Index by taxonomy tags
            for tag in taxonomy:
                self.taxonomy_index[tag.lower()].append(claim.claim_id)

        conn.close()

        # Build clusters
        self._build_clusters()

        print(f"[OK] Rebuilt index: {len(self.claims)} claims")
        self.save()

    def _build_clusters(self, threshold: float = 0.6):
        """Build clusters of similar claims."""
        self.clusters.clear()
        assigned = set()

        for claim_id, claim in self.claims.items():
            if claim_id in assigned:
                continue

            # Find similar claims
            cluster_claims = [claim_id]
            cluster_sources = {claim.source_id}

            for other_id, other in self.claims.items():
                if other_id == claim_id or other_id in assigned:
                    continue

                closeness = utf_closeness(claim, other)
                if closeness["composite"] >= threshold:
                    cluster_claims.append(other_id)
                    cluster_sources.add(other.source_id)
                    assigned.add(other_id)

            if len(cluster_claims) > 1:
                assigned.add(claim_id)

                # Find common taxonomy
                all_tags = [self.claims[cid].taxonomy_tags for cid in cluster_claims]
                common = set(all_tags[0]) if all_tags[0] else set()
                for tags in all_tags[1:]:
                    common &= set(tags)

                cluster = ClaimCluster(
                    cluster_id=f"cluster_{len(self.clusters)}",
                    centroid_slug=claim.slug_code,
                    claims=cluster_claims,
                    sources=list(cluster_sources),
                    common_taxonomy=list(common),
                    cohesion_score=threshold
                )
                self.clusters.append(cluster)

    def find_similar(self, claim_text: str, top_k: int = 10,
                     threshold: float = 0.3) -> List[SimilarityResult]:
        """Find claims similar to given text."""
        results = []

        # Extract potential slug parts from query
        import re
        query_words = set(re.findall(r'\b[a-z]{4,}\b', claim_text.lower()))
        query_words -= {'that', 'this', 'which', 'with', 'from', 'have', 'been', 'what'}

        # Find candidate claims via inverted index
        candidates = set()
        for word in query_words:
            if word in self.slug_index:
                candidates.update(self.slug_index[word])

        # If no slug matches, search all claims
        if not candidates:
            candidates = set(self.claims.keys())

        # Score candidates
        for claim_id in candidates:
            claim = self.claims[claim_id]

            # Simple word overlap score (for text-based search)
            claim_words = set(re.findall(r'\b[a-z]{4,}\b', claim.statement.lower()))
            claim_words -= {'that', 'this', 'which', 'with', 'from', 'have', 'been', 'what'}

            overlap = len(query_words & claim_words)
            union = len(query_words | claim_words)
            text_sim = overlap / union if union > 0 else 0.0

            # Slug similarity (if claim has slug)
            slug_sim = 0.0
            if claim.slug_code:
                slug_parts = set(claim.slug_code.split('-'))
                slug_sim = len(query_words & slug_parts) / len(slug_parts) if slug_parts else 0.0

            # Combined score
            score = (text_sim * 0.6) + (slug_sim * 0.4)

            if score >= threshold:
                results.append(SimilarityResult(
                    target_claim_id="query",
                    matched_claim_id=claim_id,
                    matched_statement=claim.statement,
                    matched_source=claim.source_title,
                    similarity_score=score,
                    match_type="text" if text_sim > slug_sim else "slug",
                    common_tags=claim.taxonomy_tags[:3]
                ))

        # Sort by score
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:top_k]

    def find_similar_by_id(self, claim_id: str, top_k: int = 10,
                          threshold: float = 0.3) -> List[SimilarityResult]:
        """Find claims similar to a claim by ID."""
        if claim_id not in self.claims:
            return []

        target = self.claims[claim_id]
        results = []

        for other_id, other in self.claims.items():
            if other_id == claim_id:
                continue

            closeness = utf_closeness(target, other)
            if closeness["composite"] >= threshold:
                results.append(SimilarityResult(
                    target_claim_id=claim_id,
                    matched_claim_id=other_id,
                    matched_statement=other.statement,
                    matched_source=other.source_title,
                    similarity_score=closeness["composite"],
                    match_type="utf_closeness",
                    common_tags=[t for t in target.taxonomy_tags if t in other.taxonomy_tags]
                ))

        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:top_k]

    def get_cross_paper_links(self) -> List[Dict[str, Any]]:
        """Get claims that appear across multiple papers."""
        links = []

        for cluster in self.clusters:
            if len(cluster.sources) > 1:
                claims_info = []
                for cid in cluster.claims:
                    claim = self.claims.get(cid)
                    if claim:
                        claims_info.append({
                            "claim_id": cid,
                            "statement": claim.statement[:100] + "..." if len(claim.statement) > 100 else claim.statement,
                            "source": claim.source_title
                        })

                links.append({
                    "cluster_id": cluster.cluster_id,
                    "common_concept": cluster.centroid_slug,
                    "num_papers": len(cluster.sources),
                    "num_claims": len(cluster.claims),
                    "common_taxonomy": cluster.common_taxonomy,
                    "claims": claims_info
                })

        return sorted(links, key=lambda x: x["num_papers"], reverse=True)


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Claim Similarity Index")
    parser.add_argument("action", choices=["index", "find", "similar", "clusters", "links"])
    parser.add_argument("query", nargs="?", help="Query text or claim ID")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild index from DB")
    parser.add_argument("--top-k", type=int, default=10, help="Number of results")
    parser.add_argument("--threshold", type=float, default=0.3, help="Similarity threshold")

    args = parser.parse_args()

    index = ClaimSimilarityIndex()

    if args.action == "index":
        if args.rebuild:
            index.rebuild_from_db()
        else:
            if index.load():
                print(f"[OK] Loaded index: {len(index.claims)} claims, {len(index.clusters)} clusters")
            else:
                print("[INFO] No index found, rebuilding...")
                index.rebuild_from_db()

    elif args.action == "find":
        if not args.query:
            print("[ERROR] Query text required")
            return
        index.load()
        results = index.find_similar(args.query, args.top_k, args.threshold)
        print(f"\nFound {len(results)} similar claims:\n")
        for r in results:
            print(f"  [{r.similarity_score:.2f}] {r.matched_statement[:80]}...")
            print(f"           Source: {r.matched_source}")
            print(f"           Match: {r.match_type}, Tags: {r.common_tags}\n")

    elif args.action == "similar":
        if not args.query:
            print("[ERROR] Claim ID required")
            return
        index.load()
        results = index.find_similar_by_id(args.query, args.top_k, args.threshold)
        print(f"\nFound {len(results)} similar claims:\n")
        for r in results:
            print(f"  [{r.similarity_score:.2f}] {r.matched_statement[:80]}...")
            print(f"           Source: {r.matched_source}\n")

    elif args.action == "clusters":
        index.load()
        print(f"\n{len(index.clusters)} claim clusters:\n")
        for c in index.clusters[:20]:
            print(f"  {c.cluster_id}: {c.centroid_slug}")
            print(f"    Claims: {len(c.claims)}, Sources: {len(c.sources)}")
            print(f"    Common: {c.common_taxonomy}\n")

    elif args.action == "links":
        index.load()
        links = index.get_cross_paper_links()
        print(f"\n{len(links)} cross-paper links:\n")
        for link in links[:20]:
            print(f"  [{link['num_papers']} papers] {link['common_concept']}")
            print(f"    {link['num_claims']} claims, Taxonomy: {link['common_taxonomy']}")
            for claim in link['claims'][:3]:
                print(f"      - {claim['statement'][:60]}... ({claim['source'][:30]})")
            print()


if __name__ == "__main__":
    main()
