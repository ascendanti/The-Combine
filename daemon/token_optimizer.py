#!/usr/bin/env python3
"""
Token Optimizer - Intelligent caching and compression for 70%+ token savings

Phase14-TokenOpt Implementation:
1. Prompt pattern caching with semantic similarity
2. Context compression using extractive summarization
3. Cache warming for common patterns
4. Real-time token savings tracking

Integrates with: model_router.py, Dragonfly cache, LocalAI

Usage:
    from token_optimizer import TokenOptimizer
    optimizer = TokenOptimizer()
    result = optimizer.optimize(prompt, content)
"""

import os
import hashlib
import sqlite3
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

# Optional imports
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Token compression modules (WIRED 2026-01-28)
try:
    from toonify_optimizer import toonify_data, detoonify_data, estimate_savings as toon_savings
    TOONIFY_AVAILABLE = True
except ImportError:
    TOONIFY_AVAILABLE = False
    toonify_data = None

try:
    from headroom_optimizer import compress_logs, compress_tool_output, compress_search_results
    HEADROOM_AVAILABLE = True
except ImportError:
    HEADROOM_AVAILABLE = False
    compress_logs = None

DAEMON_DIR = Path(__file__).parent
OPTIMIZER_DB = DAEMON_DIR / "token_optimizer.db"

# ============================================================================
# Configuration
# ============================================================================

@dataclass
class OptimizerConfig:
    """Configuration for token optimization."""
    dragonfly_url: str = os.environ.get("DRAGONFLY_URL", "redis://localhost:6379")

    # Cache settings
    cache_ttl: int = 3600 * 24  # 24 hours
    similarity_threshold: float = 0.85  # For pattern matching
    max_cache_entries: int = 10000

    # Compression settings
    compression_threshold: int = 2000  # Compress if > this many tokens
    target_compression_ratio: float = 0.3  # Target 70% reduction

    # Pattern learning
    min_pattern_frequency: int = 3  # Learn pattern after N occurrences

# ============================================================================
# Pattern Templates
# ============================================================================

# Common prompt patterns to detect and cache
PROMPT_PATTERNS = {
    "summarize": [
        r"summarize\s+(this|the)",
        r"give\s+me\s+a\s+summary",
        r"tldr",
        r"brief\s+overview"
    ],
    "explain": [
        r"explain\s+(this|how|why|what)",
        r"what\s+does\s+.*\s+mean",
        r"describe\s+(how|what)"
    ],
    "fix_code": [
        r"fix\s+(this|the)\s+(bug|error|issue)",
        r"debug\s+this",
        r"why\s+.*\s+(error|fail|crash)"
    ],
    "implement": [
        r"implement\s+.*\s+function",
        r"write\s+.*\s+(code|function|class)",
        r"create\s+.*\s+that"
    ],
    "review": [
        r"review\s+(this|the)\s+code",
        r"check\s+(this|the)\s+code",
        r"any\s+issues\s+with"
    ],
    "translate": [
        r"translate\s+.*\s+to",
        r"convert\s+.*\s+to"
    ]
}


def detect_pattern(prompt: str) -> Optional[str]:
    """Detect which pattern template a prompt matches."""
    prompt_lower = prompt.lower()
    for pattern_type, patterns in PROMPT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, prompt_lower):
                return pattern_type
    return None


# ============================================================================
# Token Estimation
# ============================================================================

def estimate_tokens(text: str) -> int:
    """Estimate token count (words * 1.3 + special chars)."""
    if not text:
        return 0
    words = len(text.split())
    special_chars = len(re.findall(r'[{}()\[\]<>:;]', text))
    return int(words * 1.3 + special_chars * 0.5)


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to approximately max_tokens."""
    estimated = estimate_tokens(text)
    if estimated <= max_tokens:
        return text

    # Approximate character ratio
    char_ratio = max_tokens / estimated
    target_chars = int(len(text) * char_ratio * 0.95)  # 5% safety margin
    return text[:target_chars] + "..."


# ============================================================================
# Semantic Hashing
# ============================================================================

def semantic_hash(text: str, pattern: str = None) -> str:
    """
    Create a semantic hash for cache lookup.

    Uses pattern type + normalized content fingerprint.
    Similar prompts should produce similar hashes.
    """
    # Normalize text
    normalized = text.lower().strip()
    # Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized)
    # Remove common filler words for better matching
    filler_words = ['the', 'a', 'an', 'this', 'that', 'is', 'are', 'was', 'were']
    for word in filler_words:
        normalized = re.sub(rf'\b{word}\b', '', normalized)

    # Create hash components
    components = []
    if pattern:
        components.append(f"pattern:{pattern}")

    # Add first 100 chars hash (catches similar prompts)
    components.append(hashlib.md5(normalized[:100].encode()).hexdigest()[:8])

    # Add length bucket (groups by approximate size)
    length_bucket = len(normalized) // 500
    components.append(f"len:{length_bucket}")

    return ":".join(components)


def content_fingerprint(content: str) -> str:
    """Create a fingerprint of content for cache key."""
    if not content:
        return "empty"

    # Extract key features
    features = []

    # First 200 chars hash
    features.append(hashlib.md5(content[:200].encode()).hexdigest()[:8])

    # Token count bucket
    token_bucket = estimate_tokens(content) // 500
    features.append(f"t{token_bucket}")

    # Code detection
    if re.search(r'(def |class |function |import |const |let |var )', content):
        features.append("code")

    return "-".join(features)


# ============================================================================
# Context Compressor
# ============================================================================

class ContextCompressor:
    """
    Compress context using extractive summarization.

    Strategies:
    1. Key sentence extraction
    2. Code block preservation
    3. Important line detection
    """

    def __init__(self, target_ratio: float = 0.3):
        self.target_ratio = target_ratio  # Keep 30% of content

    def compress(self, content: str, preserve_code: bool = True) -> Tuple[str, Dict]:
        """
        Compress content while preserving important information.

        Returns: (compressed_content, compression_stats)
        """
        if not content:
            return content, {"ratio": 1.0, "method": "none"}

        original_tokens = estimate_tokens(content)
        if original_tokens < 500:
            # Don't compress small content
            return content, {"ratio": 1.0, "method": "skip"}

        # Split into sections
        sections = self._split_sections(content)

        # Score and select sections
        compressed_parts = []
        target_tokens = int(original_tokens * self.target_ratio)
        current_tokens = 0

        # Always keep code blocks if preserve_code is True
        code_blocks = []
        text_sections = []

        for section in sections:
            if preserve_code and self._is_code_block(section):
                code_blocks.append(section)
            else:
                text_sections.append((section, self._score_section(section)))

        # Add code blocks first
        for block in code_blocks:
            block_tokens = estimate_tokens(block)
            if current_tokens + block_tokens < target_tokens * 1.5:
                compressed_parts.append(block)
                current_tokens += block_tokens

        # Add top-scored text sections
        text_sections.sort(key=lambda x: x[1], reverse=True)
        for section, score in text_sections:
            section_tokens = estimate_tokens(section)
            if current_tokens + section_tokens < target_tokens:
                compressed_parts.append(section)
                current_tokens += section_tokens

        compressed = "\n\n".join(compressed_parts)
        final_tokens = estimate_tokens(compressed)

        return compressed, {
            "original_tokens": original_tokens,
            "compressed_tokens": final_tokens,
            "ratio": round(final_tokens / original_tokens, 3) if original_tokens > 0 else 1.0,
            "method": "extractive",
            "savings": original_tokens - final_tokens
        }

    def _split_sections(self, content: str) -> List[str]:
        """Split content into logical sections."""
        # Split by double newlines or code blocks
        sections = re.split(r'\n\n+|```', content)
        return [s.strip() for s in sections if s.strip()]

    def _is_code_block(self, section: str) -> bool:
        """Detect if section is code."""
        code_indicators = [
            r'^(def |class |function |import |from |const |let |var |async )',
            r'[{}\[\]();]+',
            r'^#\s*(include|define|pragma)',
            r'(return |if\s*\(|for\s*\(|while\s*\()'
        ]
        for pattern in code_indicators:
            if re.search(pattern, section, re.MULTILINE):
                return True
        return False

    def _score_section(self, section: str) -> float:
        """Score section importance (0-1)."""
        score = 0.5

        # Boost for questions
        if '?' in section:
            score += 0.2

        # Boost for key phrases
        key_phrases = ['important', 'note', 'warning', 'error', 'must', 'should', 'todo']
        for phrase in key_phrases:
            if phrase in section.lower():
                score += 0.1

        # Boost for short, dense sections
        words = len(section.split())
        if 20 < words < 100:
            score += 0.1

        # Reduce for very long sections
        if words > 200:
            score -= 0.1

        return min(1.0, max(0.0, score))


# ============================================================================
# Token Optimizer
# ============================================================================

class TokenOptimizer:
    """
    Main token optimization engine.

    Features:
    1. Pattern-based caching with semantic similarity
    2. Context compression for long content
    3. Token budget management
    4. Real-time savings tracking
    """

    def __init__(self, config: OptimizerConfig = None):
        self.config = config or OptimizerConfig()
        self.compressor = ContextCompressor(self.config.target_compression_ratio)
        self.redis = None

        if REDIS_AVAILABLE:
            try:
                self.redis = redis.from_url(self.config.dragonfly_url)
                self.redis.ping()
            except Exception as e:
                print(f"Redis not available: {e}")
                self.redis = None

        self._init_db()

    def _init_db(self):
        """Initialize optimizer database."""
        conn = sqlite3.connect(OPTIMIZER_DB)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS pattern_cache (
                cache_key TEXT PRIMARY KEY,
                pattern_type TEXT,
                prompt_hash TEXT,
                content_hash TEXT,
                response TEXT,
                tokens_saved INTEGER,
                hit_count INTEGER DEFAULT 0,
                created_at TEXT,
                last_hit TEXT
            );

            CREATE TABLE IF NOT EXISTS optimization_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                action TEXT,
                tokens_input INTEGER,
                tokens_output INTEGER,
                tokens_saved INTEGER,
                cache_hit INTEGER,
                compression_ratio REAL
            );

            CREATE TABLE IF NOT EXISTS learned_patterns (
                pattern_hash TEXT PRIMARY KEY,
                pattern_text TEXT,
                frequency INTEGER DEFAULT 1,
                avg_tokens INTEGER,
                created_at TEXT,
                last_seen TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_pattern_type ON pattern_cache(pattern_type);
            CREATE INDEX IF NOT EXISTS idx_cache_hits ON pattern_cache(hit_count DESC);
        """)
        conn.commit()
        conn.close()

    def optimize(self, prompt: str, content: str = "",
                 max_tokens: int = 8000) -> Dict[str, Any]:
        """
        Optimize prompt and content for minimal token usage.

        Returns:
            {
                "prompt": optimized prompt,
                "content": optimized content,
                "cached_response": response if cache hit,
                "tokens_saved": number of tokens saved,
                "compression_stats": compression details,
                "cache_hit": bool
            }
        """
        result = {
            "prompt": prompt,
            "content": content,
            "cached_response": None,
            "tokens_saved": 0,
            "compression_stats": {},
            "cache_hit": False
        }

        original_tokens = estimate_tokens(prompt) + estimate_tokens(content)

        # 1. Check pattern cache
        pattern = detect_pattern(prompt)
        cache_key = self._build_cache_key(prompt, content, pattern)

        cached = self._get_cached(cache_key)
        if cached:
            result["cached_response"] = cached
            result["cache_hit"] = True
            result["tokens_saved"] = original_tokens
            self._log_optimization("cache_hit", original_tokens, 0, original_tokens, True, 1.0)
            return result

        # 2. Compress content if needed
        if estimate_tokens(content) > self.config.compression_threshold:
            compressed, stats = self.compressor.compress(content)
            result["content"] = compressed
            result["compression_stats"] = stats
            result["tokens_saved"] = stats.get("savings", 0)

        # 3. Learn pattern for future
        self._learn_pattern(prompt, pattern)

        # Log optimization
        final_tokens = estimate_tokens(result["prompt"]) + estimate_tokens(result["content"])
        self._log_optimization(
            "optimize",
            original_tokens,
            final_tokens,
            result["tokens_saved"],
            False,
            result["compression_stats"].get("ratio", 1.0)
        )

        return result

    def cache_response(self, prompt: str, content: str, response: str):
        """Cache a response for future use."""
        pattern = detect_pattern(prompt)
        cache_key = self._build_cache_key(prompt, content, pattern)

        tokens_saved = estimate_tokens(prompt) + estimate_tokens(content)

        conn = sqlite3.connect(OPTIMIZER_DB)
        conn.execute("""
            INSERT OR REPLACE INTO pattern_cache
            (cache_key, pattern_type, prompt_hash, content_hash, response,
             tokens_saved, hit_count, created_at, last_hit)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
        """, (
            cache_key, pattern or "unknown",
            hashlib.md5(prompt.encode()).hexdigest(),
            content_fingerprint(content),
            response, tokens_saved,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

        # Also cache in Redis for fast access
        if self.redis:
            self.redis.setex(
                f"tokopt:{cache_key}",
                self.config.cache_ttl,
                response
            )

    def _build_cache_key(self, prompt: str, content: str, pattern: str = None) -> str:
        """Build cache key from prompt and content."""
        prompt_hash = semantic_hash(prompt, pattern)
        content_fp = content_fingerprint(content)
        return f"{prompt_hash}:{content_fp}"

    def _get_cached(self, cache_key: str) -> Optional[str]:
        """Get cached response."""
        # Try Redis first (faster)
        if self.redis:
            cached = self.redis.get(f"tokopt:{cache_key}")
            if cached:
                self._increment_hit_count(cache_key)
                return cached.decode()

        # Fall back to SQLite
        conn = sqlite3.connect(OPTIMIZER_DB)
        cursor = conn.execute(
            "SELECT response FROM pattern_cache WHERE cache_key = ?",
            (cache_key,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            self._increment_hit_count(cache_key)
            return row[0]

        return None

    def _increment_hit_count(self, cache_key: str):
        """Increment cache hit count."""
        conn = sqlite3.connect(OPTIMIZER_DB)
        conn.execute("""
            UPDATE pattern_cache
            SET hit_count = hit_count + 1, last_hit = ?
            WHERE cache_key = ?
        """, (datetime.now().isoformat(), cache_key))
        conn.commit()
        conn.close()

    def _learn_pattern(self, prompt: str, pattern: str):
        """Learn a new pattern from usage."""
        pattern_hash = hashlib.md5(prompt[:100].lower().encode()).hexdigest()

        conn = sqlite3.connect(OPTIMIZER_DB)
        conn.execute("""
            INSERT INTO learned_patterns (pattern_hash, pattern_text, frequency, avg_tokens, created_at, last_seen)
            VALUES (?, ?, 1, ?, ?, ?)
            ON CONFLICT(pattern_hash) DO UPDATE SET
                frequency = frequency + 1,
                last_seen = excluded.last_seen
        """, (
            pattern_hash, prompt[:200],
            estimate_tokens(prompt),
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

    def _log_optimization(self, action: str, tokens_in: int, tokens_out: int,
                          tokens_saved: int, cache_hit: bool, compression_ratio: float):
        """Log optimization action."""
        conn = sqlite3.connect(OPTIMIZER_DB)
        conn.execute("""
            INSERT INTO optimization_stats
            (timestamp, action, tokens_input, tokens_output, tokens_saved, cache_hit, compression_ratio)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(), action,
            tokens_in, tokens_out, tokens_saved,
            1 if cache_hit else 0, compression_ratio
        ))
        conn.commit()
        conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """Get optimization statistics."""
        conn = sqlite3.connect(OPTIMIZER_DB)

        # Total savings
        cursor = conn.execute("""
            SELECT SUM(tokens_saved), SUM(cache_hit), COUNT(*)
            FROM optimization_stats
        """)
        row = cursor.fetchone()
        total_saved = row[0] or 0
        cache_hits = row[1] or 0
        total_ops = row[2] or 0

        # Recent performance
        cursor = conn.execute("""
            SELECT AVG(tokens_saved), AVG(compression_ratio)
            FROM optimization_stats
            WHERE timestamp > datetime('now', '-24 hours')
        """)
        recent = cursor.fetchone()
        avg_saved_24h = recent[0] or 0
        avg_compression_24h = recent[1] or 1.0

        # Top cached patterns
        cursor = conn.execute("""
            SELECT pattern_type, SUM(hit_count), SUM(tokens_saved)
            FROM pattern_cache
            GROUP BY pattern_type
            ORDER BY SUM(hit_count) DESC
            LIMIT 5
        """)
        top_patterns = [{"type": r[0], "hits": r[1], "saved": r[2]} for r in cursor.fetchall()]

        # Learned patterns
        cursor = conn.execute("""
            SELECT COUNT(*), SUM(frequency)
            FROM learned_patterns
            WHERE frequency >= ?
        """, (self.config.min_pattern_frequency,))
        learned = cursor.fetchone()

        conn.close()

        # Calculate savings percentage
        # Assuming average prompt is ~500 tokens, calculate % saved
        savings_percent = (total_saved / (total_ops * 500)) * 100 if total_ops > 0 else 0

        return {
            "total_tokens_saved": total_saved,
            "cache_hits": cache_hits,
            "total_operations": total_ops,
            "cache_hit_rate": round(cache_hits / total_ops, 3) if total_ops > 0 else 0,
            "savings_percentage": round(savings_percent, 1),
            "avg_saved_24h": round(avg_saved_24h, 1),
            "avg_compression_24h": round(avg_compression_24h, 3),
            "top_patterns": top_patterns,
            "learned_patterns": learned[0] or 0,
            "pattern_occurrences": learned[1] or 0
        }

    def warm_cache(self, common_prompts: List[Dict[str, str]]):
        """
        Warm cache with common prompt/response pairs.

        Args:
            common_prompts: List of {"prompt": str, "content": str, "response": str}
        """
        for item in common_prompts:
            self.cache_response(
                item["prompt"],
                item.get("content", ""),
                item["response"]
            )
        print(f"Warmed cache with {len(common_prompts)} entries")


# ============================================================================
# Integration with model_router
# ============================================================================

def optimize_router_call(prompt: str, content: str,
                         optimizer: TokenOptimizer = None) -> Dict[str, Any]:
    """
    Wrapper to optimize a model router call.

    Returns optimized prompt/content and any cached response.
    """
    if optimizer is None:
        optimizer = TokenOptimizer()

    result = optimizer.optimize(prompt, content)

    return {
        "prompt": result["prompt"],
        "content": result["content"],
        "use_cache": result["cache_hit"],
        "cached_response": result["cached_response"],
        "tokens_saved": result["tokens_saved"]
    }


# ============================================================================
# Unified Compression Pipeline (WIRED 2026-01-28)
# ============================================================================

def optimize_structured_data(data: Any, query: str = None) -> Tuple[str, Dict]:
    """
    Chain TOON + Headroom for maximum compression on structured data.

    Pipeline:
    1. TOON format (60%+ savings on JSON)
    2. Headroom SmartCrusher (50%+ additional on lists)

    Args:
        data: JSON-serializable data (dict, list)
        query: Optional query for relevance filtering

    Returns:
        (compressed_string, stats)
    """
    stats = {
        "original_tokens": 0,
        "final_tokens": 0,
        "toon_applied": False,
        "headroom_applied": False,
        "total_savings_pct": 0.0
    }

    if data is None:
        return "", stats

    # Estimate original size
    try:
        import json
        original_str = json.dumps(data) if not isinstance(data, str) else data
        stats["original_tokens"] = estimate_tokens(original_str)
    except:
        return str(data), stats

    result = data

    # Step 1: Apply Headroom compression for lists
    if HEADROOM_AVAILABLE and isinstance(data, list) and len(data) > 10:
        result = compress_tool_output(data, query=query, max_items=10)
        stats["headroom_applied"] = True
    elif HEADROOM_AVAILABLE and isinstance(data, dict):
        # Compress any large nested lists
        result = compress_tool_output(data, query=query, max_items=10)
        stats["headroom_applied"] = True

    # Step 2: Apply TOON format for structured data
    if TOONIFY_AVAILABLE and isinstance(result, (dict, list)):
        try:
            toon_result = toon_savings(result)
            if toon_result.savings_pct >= 20:  # Only if beneficial
                result = toon_result.toon_str
                stats["toon_applied"] = True
            else:
                result = json.dumps(result, separators=(',', ':'))
        except:
            result = json.dumps(result, separators=(',', ':'))
    else:
        result = json.dumps(result, separators=(',', ':')) if not isinstance(result, str) else result

    # Calculate final stats
    stats["final_tokens"] = estimate_tokens(result)
    if stats["original_tokens"] > 0:
        stats["total_savings_pct"] = round(
            (1 - stats["final_tokens"] / stats["original_tokens"]) * 100, 1
        )

    return result, stats


def optimize_logs(logs: List[Dict], query: str = None) -> Tuple[List, Dict]:
    """
    Optimize log entries using Headroom SmartCrusher.

    Keeps: first N, last N, errors/warnings, query-relevant entries.
    """
    if not HEADROOM_AVAILABLE:
        return logs, {"headroom_available": False}

    result = compress_logs(logs, query=query)
    return result.compressed, {
        "original_count": result.original_count,
        "compressed_count": result.compressed_count,
        "reduction_pct": result.reduction_pct,
        "kept_reasons": result.kept_reasons
    }


def optimize_search_results(results: List[Dict], query: str) -> List[Dict]:
    """Optimize search results using Headroom relevance scoring."""
    if not HEADROOM_AVAILABLE:
        return results[:10] if len(results) > 10 else results

    return compress_search_results(results, query, max_results=10)


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Token Optimizer")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("stats", help="Show optimization statistics")
    subparsers.add_parser("test", help="Test optimization")

    warm_parser = subparsers.add_parser("warm", help="Warm cache with defaults")
    warm_parser.add_argument("--file", help="JSON file with prompt/response pairs")

    args = parser.parse_args()

    optimizer = TokenOptimizer()

    if args.command == "stats":
        stats = optimizer.get_stats()
        print("\n=== Token Optimizer Statistics ===")
        print(f"Total tokens saved: {stats['total_tokens_saved']:,}")
        print(f"Cache hit rate: {stats['cache_hit_rate']*100:.1f}%")
        print(f"Savings percentage: {stats['savings_percentage']:.1f}%")
        print(f"Learned patterns: {stats['learned_patterns']}")
        print(f"\nTop patterns:")
        for p in stats['top_patterns']:
            print(f"  {p['type']}: {p['hits']} hits, {p['saved']} tokens saved")

    elif args.command == "test":
        # Test optimization
        test_prompt = "Summarize this document about machine learning"
        test_content = """
        Machine learning is a subset of artificial intelligence (AI) that provides
        systems the ability to automatically learn and improve from experience without
        being explicitly programmed. Machine learning focuses on the development of
        computer programs that can access data and use it to learn for themselves.

        The process of learning begins with observations or data, such as examples,
        direct experience, or instruction, in order to look for patterns in data and
        make better decisions in the future based on the examples that we provide.
        """ * 10  # Make it longer

        result = optimizer.optimize(test_prompt, test_content)
        print(f"\nOriginal tokens: {estimate_tokens(test_prompt + test_content)}")
        print(f"Optimized tokens: {estimate_tokens(result['prompt'] + result['content'])}")
        print(f"Tokens saved: {result['tokens_saved']}")
        print(f"Cache hit: {result['cache_hit']}")
        print(f"Compression: {result['compression_stats']}")

    elif args.command == "warm":
        # Default common patterns to warm
        defaults = [
            {"prompt": "Summarize this code", "content": "# sample code", "response": "[Cached summary template]"},
            {"prompt": "Explain this function", "content": "def foo():", "response": "[Cached explanation template]"},
            {"prompt": "Fix this bug", "content": "error: undefined", "response": "[Cached fix template]"},
        ]

        if args.file:
            with open(args.file) as f:
                defaults = json.load(f)

        optimizer.warm_cache(defaults)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
