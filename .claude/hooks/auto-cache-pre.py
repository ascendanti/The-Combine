#!/usr/bin/env python3
"""
Auto-Cache PreToolUse Hook

Checks cache before executing Read, Grep, Glob operations.
Returns cached result if valid, saving tokens.

Cache invalidation:
- Read: Checks file mtime (reloads if file changed)
- Grep/Glob: TTL-based (1 hour default)
"""

import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

# Cache settings
CACHE_DIR = Path.home() / ".token-optimizer-cache" / "auto-cache"
CACHE_TTL_HOURS = 1  # Default TTL for non-file caches

# Tools to check cache for
CACHEABLE_TOOLS = {"Read", "Grep", "Glob"}

def get_cache_key(tool_name: str, params: dict) -> str:
    """Generate cache key from tool + params."""
    key_data = f"{tool_name}:{json.dumps(params, sort_keys=True)}"
    return hashlib.md5(key_data.encode()).hexdigest()

def get_file_mtime(path: str) -> float:
    """Get file modification time."""
    try:
        return Path(path).stat().st_mtime
    except:
        return 0

def get_cached(key: str) -> dict:
    """Retrieve from cache if exists and valid."""
    cache_file = CACHE_DIR / f"{key}.json"

    if not cache_file.exists():
        return None

    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except:
        return None

def is_cache_valid(cached_data: dict, tool_name: str, tool_input: dict) -> bool:
    """Check if cached data is still valid."""
    if not cached_data:
        return False

    metadata = cached_data.get("metadata", {})
    cached_at = cached_data.get("cached_at", "")

    # For Read operations, check file mtime
    if tool_name == "Read" and "file_path" in tool_input:
        cached_mtime = metadata.get("mtime", 0)
        current_mtime = get_file_mtime(tool_input["file_path"])
        if current_mtime != cached_mtime:
            return False  # File changed, invalidate

    # For other operations, check TTL
    else:
        try:
            cached_time = datetime.fromisoformat(cached_at)
            if datetime.now() - cached_time > timedelta(hours=CACHE_TTL_HOURS):
                return False  # Expired
        except:
            return False

    return True

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

    # Generate cache key
    cache_key = get_cache_key(tool_name, tool_input)

    # Check cache
    cached = get_cached(cache_key)

    if cached and is_cache_valid(cached, tool_name, tool_input):
        # Return cached result via message (Claude will see this)
        # The tool still runs but we provide the cached content for reference
        cached_result = cached.get("result", "")
        cached_size = len(cached_result)

        # For large caches, suggest using mcp__token-optimizer__smart_read instead
        if cached_size > 2000:
            print(json.dumps({
                "continue": True,
                "message": f"[CACHE AVAILABLE] {cached_size} bytes cached for this {tool_name}. Consider: mcp__token-optimizer__get_cached with key={cache_key}"
            }))
        else:
            # Small enough to include inline
            print(json.dumps({
                "continue": True,
                "message": f"[CACHE HIT] {tool_name} cached ({cached_size}b):\n{cached_result[:1000]}"
            }))
    else:
        print(json.dumps({"continue": True}))

if __name__ == "__main__":
    main()
