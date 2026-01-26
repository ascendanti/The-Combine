#!/usr/bin/env python3
"""
Context Router - HOT/WARM/COLD Tiered Context Management

Based on claude-cognitive architecture for 64-95% token reduction.

Tiers:
- HOT (score > 0.8): Full content injection
- WARM (0.25 < score <= 0.8): Headers/signatures only
- COLD (score <= 0.25): Evicted (reference only)

Features:
- Relevance scoring based on access patterns
- Decay over conversation turns (0.85 multiplier)
- Co-activation for related files
- AST extraction for WARM tier

WIRING (2026-01-26): Integrated into PreToolUse hook for auto-cache.
"""

import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import re

DB_PATH = Path(__file__).parent / "context_router.db"

# Tier thresholds
HOT_THRESHOLD = 0.8
WARM_THRESHOLD = 0.25
DECAY_FACTOR = 0.85  # Per turn decay

# Co-activation patterns (files that tend to be accessed together)
CO_ACTIVATION_BOOST = 0.15


@dataclass
class ContextEntry:
    """A file or context entry with relevance scoring."""
    path: str
    score: float
    tier: str  # "hot", "warm", "cold"
    last_accessed: str
    access_count: int
    tokens_full: int
    tokens_warm: int
    content_hash: str
    co_activated: List[str]


def init_db():
    """Initialize context router database."""
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS context_scores (
            path TEXT PRIMARY KEY,
            score REAL,
            tier TEXT,
            last_accessed TEXT,
            access_count INTEGER DEFAULT 1,
            tokens_full INTEGER DEFAULT 0,
            tokens_warm INTEGER DEFAULT 0,
            content_hash TEXT,
            co_activated TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS access_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT,
            timestamp TEXT,
            turn_number INTEGER,
            query_context TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_scores_tier ON context_scores(tier);
        CREATE INDEX IF NOT EXISTS idx_history_path ON access_history(path);
    """)
    conn.commit()
    conn.close()


# Initialize on import
init_db()


class ContextRouter:
    """
    Routes context based on HOT/WARM/COLD tiers.

    Usage:
        router = ContextRouter()
        tier, content = router.get_context(file_path)
        router.record_access(file_path, query_context)
        router.decay_scores()  # Call at turn end
    """

    def __init__(self, session_id: str = None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d%H%M%S")
        self.turn_number = 0
        self._recent_accesses = []  # For co-activation detection

    def get_context(self, path: str) -> Tuple[str, str]:
        """
        Get context for a file based on its tier.

        Returns:
            (tier, content) - tier is "hot", "warm", or "cold"
            content varies by tier:
            - hot: full file content
            - warm: headers/signatures only
            - cold: just the path reference
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute(
            "SELECT score, tier, tokens_full, tokens_warm FROM context_scores WHERE path = ?",
            (path,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            # New file - start at WARM
            return "warm", self._extract_warm_content(path)

        score, tier, tokens_full, tokens_warm = row

        if tier == "hot":
            return "hot", self._read_full_content(path)
        elif tier == "warm":
            return "warm", self._extract_warm_content(path)
        else:
            return "cold", f"[File: {path}]"

    def record_access(self, path: str, query_context: str = ""):
        """Record file access and update scores."""
        conn = sqlite3.connect(DB_PATH)
        now = datetime.now().isoformat()

        # Check if exists
        cursor = conn.execute("SELECT score, access_count FROM context_scores WHERE path = ?", (path,))
        row = cursor.fetchone()

        if row:
            # Update existing
            old_score, count = row
            new_score = min(1.0, old_score + 0.2)  # Boost on access, cap at 1.0
            new_tier = self._score_to_tier(new_score)

            conn.execute("""
                UPDATE context_scores
                SET score = ?, tier = ?, last_accessed = ?, access_count = ?
                WHERE path = ?
            """, (new_score, new_tier, now, count + 1, path))
        else:
            # New entry - start at WARM threshold
            new_score = WARM_THRESHOLD + 0.3  # Start above WARM threshold
            tokens_full = self._estimate_tokens(path, full=True)
            tokens_warm = self._estimate_tokens(path, full=False)
            content_hash = self._hash_content(path)

            conn.execute("""
                INSERT INTO context_scores (path, score, tier, last_accessed, access_count,
                                           tokens_full, tokens_warm, content_hash)
                VALUES (?, ?, ?, ?, 1, ?, ?, ?)
            """, (path, new_score, "warm", now, tokens_full, tokens_warm, content_hash))

        # Record history
        conn.execute("""
            INSERT INTO access_history (path, timestamp, turn_number, query_context)
            VALUES (?, ?, ?, ?)
        """, (path, now, self.turn_number, query_context[:500]))

        conn.commit()
        conn.close()

        # Track for co-activation
        self._recent_accesses.append(path)
        self._update_co_activation()

    def decay_scores(self):
        """Apply decay to all scores. Call at end of each turn."""
        self.turn_number += 1
        conn = sqlite3.connect(DB_PATH)

        # Decay all scores
        conn.execute("""
            UPDATE context_scores
            SET score = score * ?,
                tier = CASE
                    WHEN score * ? > ? THEN 'hot'
                    WHEN score * ? > ? THEN 'warm'
                    ELSE 'cold'
                END
        """, (DECAY_FACTOR, DECAY_FACTOR, HOT_THRESHOLD, DECAY_FACTOR, WARM_THRESHOLD))

        conn.commit()
        conn.close()

        # Reset co-activation tracking
        self._recent_accesses = []

    def get_hot_files(self) -> List[str]:
        """Get list of HOT tier files."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("SELECT path FROM context_scores WHERE tier = 'hot' ORDER BY score DESC")
        files = [row[0] for row in cursor.fetchall()]
        conn.close()
        return files

    def get_warm_files(self) -> List[str]:
        """Get list of WARM tier files."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("SELECT path FROM context_scores WHERE tier = 'warm' ORDER BY score DESC")
        files = [row[0] for row in cursor.fetchall()]
        conn.close()
        return files

    def get_stats(self) -> Dict[str, Any]:
        """Get context router statistics."""
        conn = sqlite3.connect(DB_PATH)

        cursor = conn.execute("""
            SELECT tier, COUNT(*), SUM(tokens_full), SUM(tokens_warm)
            FROM context_scores
            GROUP BY tier
        """)
        tier_stats = {}
        total_full = 0
        total_warm = 0

        for tier, count, tokens_full, tokens_warm in cursor.fetchall():
            tier_stats[tier] = {
                "count": count,
                "tokens_full": tokens_full or 0,
                "tokens_warm": tokens_warm or 0
            }
            if tier == "hot":
                total_full += tokens_full or 0
            elif tier == "warm":
                total_warm += tokens_warm or 0

        conn.close()

        # Calculate savings
        all_full = sum(s.get("tokens_full", 0) for s in tier_stats.values())
        current_usage = total_full + total_warm
        savings = 1 - (current_usage / all_full) if all_full > 0 else 0

        return {
            "tiers": tier_stats,
            "token_savings": f"{savings:.1%}",
            "current_tokens": current_usage,
            "full_tokens": all_full
        }

    def _score_to_tier(self, score: float) -> str:
        """Convert score to tier."""
        if score > HOT_THRESHOLD:
            return "hot"
        elif score > WARM_THRESHOLD:
            return "warm"
        return "cold"

    def _read_full_content(self, path: str) -> str:
        """Read full file content."""
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except:
            return f"[Error reading: {path}]"

    def _extract_warm_content(self, path: str) -> str:
        """Extract headers/signatures for WARM tier."""
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Extract based on file type
            if path.endswith('.py'):
                return self._extract_python_signatures(content, path)
            elif path.endswith(('.js', '.ts', '.tsx')):
                return self._extract_js_signatures(content, path)
            elif path.endswith('.md'):
                return self._extract_markdown_headers(content, path)
            else:
                # Generic: first 50 lines
                lines = content.split('\n')[:50]
                return f"[WARM: {path}]\n" + '\n'.join(lines)

        except:
            return f"[WARM: {path} - unavailable]"

    def _extract_python_signatures(self, content: str, path: str) -> str:
        """Extract Python class/function signatures."""
        lines = []
        lines.append(f"[WARM: {path}]")

        # Extract imports, class defs, function defs, docstrings
        for line in content.split('\n'):
            stripped = line.strip()
            if stripped.startswith(('import ', 'from ')):
                lines.append(line)
            elif stripped.startswith('class '):
                lines.append(line)
            elif stripped.startswith('def '):
                lines.append(line)
            elif stripped.startswith('"""') or stripped.startswith("'''"):
                lines.append(line)
            elif '# ' in line and len(stripped) > 5:
                # Include significant comments
                if any(kw in stripped.lower() for kw in ['todo', 'fixme', 'note', 'important']):
                    lines.append(line)

        return '\n'.join(lines[:100])  # Cap at 100 lines

    def _extract_js_signatures(self, content: str, path: str) -> str:
        """Extract JS/TS signatures."""
        lines = [f"[WARM: {path}]"]

        for line in content.split('\n'):
            stripped = line.strip()
            if stripped.startswith(('import ', 'export ', 'const ', 'function ', 'class ', 'interface ', 'type ')):
                lines.append(line)
            elif 'async ' in stripped and ('function' in stripped or '=>' in stripped):
                lines.append(line)

        return '\n'.join(lines[:100])

    def _extract_markdown_headers(self, content: str, path: str) -> str:
        """Extract Markdown headers."""
        lines = [f"[WARM: {path}]"]

        for line in content.split('\n'):
            if line.startswith('#'):
                lines.append(line)
            elif line.startswith('- ') and len(line) < 100:
                lines.append(line)

        return '\n'.join(lines[:50])

    def _estimate_tokens(self, path: str, full: bool = True) -> int:
        """Estimate token count for a file."""
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            if full:
                return len(content) // 4  # Rough estimate: 4 chars per token
            else:
                warm = self._extract_warm_content(path)
                return len(warm) // 4
        except:
            return 0

    def _hash_content(self, path: str) -> str:
        """Hash file content for change detection."""
        try:
            with open(path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()[:16]
        except:
            return "unknown"

    def _update_co_activation(self):
        """Update co-activation relationships."""
        if len(self._recent_accesses) < 2:
            return

        conn = sqlite3.connect(DB_PATH)

        # Get last two accessed files
        for i in range(len(self._recent_accesses) - 1):
            path1 = self._recent_accesses[i]
            path2 = self._recent_accesses[i + 1]

            if path1 == path2:
                continue

            # Update co-activation for both
            for p1, p2 in [(path1, path2), (path2, path1)]:
                cursor = conn.execute("SELECT co_activated FROM context_scores WHERE path = ?", (p1,))
                row = cursor.fetchone()
                if row:
                    try:
                        co_list = json.loads(row[0])
                    except:
                        co_list = []

                    if p2 not in co_list:
                        co_list.append(p2)
                        co_list = co_list[-10:]  # Keep last 10
                        conn.execute(
                            "UPDATE context_scores SET co_activated = ? WHERE path = ?",
                            (json.dumps(co_list), p1)
                        )

        conn.commit()
        conn.close()


def get_tiered_context(paths: List[str]) -> Dict[str, str]:
    """
    Convenience function: Get tiered context for multiple paths.

    Returns dict of {path: content} with content based on tier.
    """
    router = ContextRouter()
    result = {}

    for path in paths:
        tier, content = router.get_context(path)
        result[path] = content
        router.record_access(path)

    return result


# CLI for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Context Router")
    parser.add_argument("action", choices=["stats", "hot", "warm", "decay", "test"])
    parser.add_argument("--path", type=str, help="File path for testing")

    args = parser.parse_args()
    router = ContextRouter()

    if args.action == "stats":
        stats = router.get_stats()
        print(json.dumps(stats, indent=2))

    elif args.action == "hot":
        files = router.get_hot_files()
        print(f"HOT files ({len(files)}):")
        for f in files:
            print(f"  {f}")

    elif args.action == "warm":
        files = router.get_warm_files()
        print(f"WARM files ({len(files)}):")
        for f in files:
            print(f"  {f}")

    elif args.action == "decay":
        router.decay_scores()
        print("Decay applied")

    elif args.action == "test" and args.path:
        tier, content = router.get_context(args.path)
        print(f"Tier: {tier}")
        print(f"Content ({len(content)} chars):")
        print(content[:500])
