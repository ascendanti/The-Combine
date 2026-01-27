"""
LLM Cache L2 - Persistent semantic compute artifacts.

Codex recommendation: cache_key = (template_id + template_version + model_id + span_hashes)
Expected: 80-95% hit rate vs 40-60% with prompt-hash only.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


class LLMCacheL2:
    """SQLite-backed L2 cache for LLM responses."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            daemon_dir = Path(__file__).parent
            db_path = daemon_dir / "llm_cache_l2.db"

        self.db_path = db_path
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_cache (
                cache_key TEXT PRIMARY KEY,
                template_id TEXT NOT NULL,
                template_version TEXT NOT NULL,
                model_id TEXT NOT NULL,
                span_hashes TEXT NOT NULL,  -- JSON array
                response TEXT NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                hit_count INTEGER DEFAULT 0
            )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_template ON llm_cache(template_id, template_version)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON llm_cache(expires_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_model ON llm_cache(model_id)")
        conn.commit()
        conn.close()

    def get(self, key: str) -> Optional[str]:
        """Get cached response."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            SELECT response, expires_at FROM llm_cache
            WHERE cache_key = ? AND expires_at > ?
        """, (key, datetime.now().isoformat()))

        row = c.fetchone()

        if row:
            # Increment hit count
            c.execute("UPDATE llm_cache SET hit_count = hit_count + 1 WHERE cache_key = ?", (key,))
            conn.commit()
            conn.close()
            return row[0]

        conn.close()
        return None

    def set(self, key: str, value: str, ttl_days: int = 30, metadata: dict = None):
        """Store response in cache."""
        metadata = metadata or {}

        conn = sqlite3.connect(self.db_path)
        expires_at = (datetime.now() + timedelta(days=ttl_days)).isoformat()

        conn.execute("""
            INSERT OR REPLACE INTO llm_cache
            (cache_key, template_id, template_version, model_id, span_hashes,
             response, tokens_used, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            key,
            metadata.get('template_id', 'unknown'),
            metadata.get('template_version', '1.0'),
            metadata.get('model_id', 'unknown'),
            json.dumps(metadata.get('span_hashes', [])),
            value,
            metadata.get('tokens_used', 0),
            datetime.now().isoformat(),
            expires_at
        ))

        conn.commit()
        conn.close()

    def invalidate_template(self, template_id: str, version_before: str):
        """Invalidate all cache entries for template before a version."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            DELETE FROM llm_cache
            WHERE template_id = ? AND template_version < ?
        """, (template_id, version_before))
        deleted = conn.total_changes
        conn.commit()
        conn.close()
        return deleted

    def cleanup_expired(self):
        """Remove expired entries."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM llm_cache WHERE expires_at < ?", (datetime.now().isoformat(),))
        deleted = conn.total_changes
        conn.commit()
        conn.close()
        return deleted

    def stats(self) -> dict:
        """Get cache statistics."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("SELECT COUNT(*), SUM(hit_count), AVG(hit_count) FROM llm_cache")
        total, total_hits, avg_hits = c.fetchone()

        c.execute("""
            SELECT template_id, COUNT(*), SUM(hit_count)
            FROM llm_cache
            GROUP BY template_id
            ORDER BY SUM(hit_count) DESC
            LIMIT 5
        """)
        top_templates = c.fetchall()

        conn.close()

        return {
            'total_entries': total or 0,
            'total_hits': total_hits or 0,
            'avg_hits_per_entry': round(avg_hits or 0, 2),
            'top_templates': [
                {'template': t[0], 'entries': t[1], 'hits': t[2]}
                for t in top_templates
            ]
        }


if __name__ == "__main__":
    cache = LLMCacheL2()

    # Test
    print("Testing L2 cache...")
    cache.set("test_key", "test response", ttl_days=1, metadata={
        'template_id': 'utf_extraction_v2',
        'template_version': 'v2.0',
        'model_id': 'mistral-7b',
        'span_hashes': ['abc123', 'def456'],
        'tokens_used': 2048
    })

    result = cache.get("test_key")
    print(f"Get result: {result}")

    stats = cache.stats()
    print(f"Stats: {json.dumps(stats, indent=2)}")

    # Cleanup
    expired = cache.cleanup_expired()
    print(f"Cleaned up {expired} expired entries")
