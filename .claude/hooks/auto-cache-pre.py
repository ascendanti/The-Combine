#!/usr/bin/env python3
"""
Auto-Cache PreToolUse Hook

Checks Dragonfly cache before executing Read, Grep, Glob operations.
Returns cached result if valid, saving tokens.

WIRED (2026-01-26): Now integrates Context Router for HOT/WARM/COLD tiering.
- HOT files: Full content (frequently accessed)
- WARM files: Headers/signatures only (64-95% token savings)
- COLD files: Reference only (evicted)

Cache invalidation:
- Read: Checks file mtime (reloads if file changed)
- Grep/Glob: TTL-based (1 hour default)
"""

import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime

# Add daemon to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "daemon"))

try:
    from cache_client import cache, tool_cache_key
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False

# WIRED: Context Router for tiered context management
try:
    from context_router import ContextRouter
    CONTEXT_ROUTER_AVAILABLE = True
except ImportError:
    CONTEXT_ROUTER_AVAILABLE = False
    ContextRouter = None

# WIRED (2026-01-28): Token compression for Grep/Glob results
try:
    from headroom_optimizer import compress_search_results
    HEADROOM_AVAILABLE = True
except ImportError:
    HEADROOM_AVAILABLE = False
    compress_search_results = None

# Tools to check cache for
CACHEABLE_TOOLS = {"Read", "Grep", "Glob"}


def get_file_mtime(path: str) -> float:
    """Get file modification time."""
    try:
        return Path(path).stat().st_mtime
    except:
        return 0


def main():
    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except:
        print(json.dumps({"continue": True}))
        return

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Only check cache for specific tools
    if tool_name not in CACHEABLE_TOOLS:
        print(json.dumps({"continue": True}))
        return

    # WIRED: Use Context Router for Read operations
    if tool_name == "Read" and CONTEXT_ROUTER_AVAILABLE and "file_path" in tool_input:
        file_path = tool_input["file_path"]
        try:
            router = ContextRouter()
            tier, content = router.get_context(file_path)
            router.record_access(file_path, "PreToolUse Read")

            if tier == "warm":
                # Return WARM content instead of full
                print(json.dumps({
                    "continue": True,
                    "message": f"[CONTEXT ROUTER] {tier.upper()} tier - headers only ({len(content)} chars)\n{content[:2000]}"
                }))
                return
            elif tier == "cold":
                # File is COLD - just reference
                print(json.dumps({
                    "continue": True,
                    "message": f"[CONTEXT ROUTER] COLD tier - {file_path} (evicted, access to promote)"
                }))
                return
            # HOT tier - continue to full read

        except Exception as e:
            pass  # Fall through to normal processing

    if not CACHE_AVAILABLE:
        print(json.dumps({"continue": True}))
        return

    # Generate cache key
    cache_key = tool_cache_key(tool_name, tool_input)

    # Check cache
    cached = cache.hgetall(cache_key)

    if cached:
        # For Read operations, check file mtime
        if tool_name == "Read" and "file_path" in tool_input:
            cached_mtime = float(cached.get("mtime", 0))
            current_mtime = get_file_mtime(tool_input["file_path"])
            if current_mtime != cached_mtime:
                # File changed, invalidate
                cache.delete(cache_key)
                print(json.dumps({"continue": True}))
                return

        # Cache hit!
        cached_result = cached.get("result", "")
        cached_size = len(cached_result)

        # WIRED (2026-01-28): Compress large Grep/Glob results
        if tool_name in {"Grep", "Glob"} and HEADROOM_AVAILABLE and cached_size > 3000:
            try:
                import json as json_mod
                # Try to parse as JSON for structured compression
                if cached_result.strip().startswith(('[', '{')):
                    parsed = json_mod.loads(cached_result)
                    # Get query from tool_input for relevance scoring
                    query_context = tool_input.get("pattern", tool_input.get("query", ""))
                    compressed = compress_search_results(parsed, query=query_context, max_results=20)
                    cached_result = json_mod.dumps(compressed) if isinstance(compressed, (dict, list)) else str(compressed)
                    cached_size = len(cached_result)
            except Exception:
                pass  # Keep original on error

        if cached_size > 2000:
            # Large cache - suggest retrieval
            print(json.dumps({
                "continue": True,
                "message": f"[CACHE HIT] {tool_name} ({cached_size}b) key={cache_key}"
            }))
        else:
            # Small enough to include inline
            print(json.dumps({
                "continue": True,
                "message": f"[CACHE HIT] {tool_name} ({cached_size}b):\n{cached_result[:1000]}"
            }))
    else:
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
