#!/usr/bin/env python3
"""
Auto-Cache PreToolUse Hook

Checks Dragonfly cache before executing Read, Grep, Glob operations.
Returns cached result if valid, saving tokens.

Cache invalidation:
- Read: Checks file mtime (reloads if file changed)
- Grep/Glob: TTL-based (1 hour default)
"""

import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime

# Add daemon to path for cache_client
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "daemon"))

try:
    from cache_client import cache, tool_cache_key
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False

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
