#!/usr/bin/env python3
"""
Auto-Cache PostToolUse Hook

Automatically caches outputs from Read, Grep, Glob operations
to Dragonfly for token efficiency.

Caches:
- File reads (by path + mtime)
- Grep results (by pattern + path)
- Glob results (by pattern)
"""

import sys
import json
from pathlib import Path

# Add daemon to path for cache_client and optimizers
DAEMON_DIR = Path(__file__).parent.parent.parent / "daemon"
sys.path.insert(0, str(DAEMON_DIR))

try:
    from cache_client import cache, tool_cache_key
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False

# WIRED (2026-01-28): Token compression before caching
try:
    from headroom_optimizer import compress_tool_output, compress_search_results
    HEADROOM_AVAILABLE = True
except ImportError:
    HEADROOM_AVAILABLE = False

try:
    from toonify_optimizer import toonify_data, estimate_savings
    TOONIFY_AVAILABLE = True
except ImportError:
    TOONIFY_AVAILABLE = False

# Tools to cache
CACHEABLE_TOOLS = {"Read", "Grep", "Glob"}

# Size thresholds (only cache substantial outputs)
MIN_CACHE_SIZE = 500  # bytes
MAX_CACHE_SIZE = 100000  # 100KB max per entry

# TTL settings (seconds)
TTL_READ = 3600 * 24  # 24 hours for file reads (mtime checked)
TTL_GREP = 3600  # 1 hour for grep results
TTL_GLOB = 3600  # 1 hour for glob results


def get_file_mtime(path: str) -> float:
    """Get file modification time for cache invalidation."""
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
    tool_output = hook_input.get("tool_output", "")

    # Only cache specific tools
    if tool_name not in CACHEABLE_TOOLS:
        print(json.dumps({"continue": True}))
        return

    if not CACHE_AVAILABLE:
        print(json.dumps({"continue": True}))
        return

    # Check size thresholds
    output_size = len(tool_output) if tool_output else 0
    if output_size < MIN_CACHE_SIZE or output_size > MAX_CACHE_SIZE:
        print(json.dumps({"continue": True}))
        return

    # Generate cache key
    key = tool_cache_key(tool_name, tool_input)

    # Determine TTL
    ttl = TTL_GREP
    if tool_name == "Read":
        ttl = TTL_READ
    elif tool_name == "Glob":
        ttl = TTL_GLOB

    # WIRED (2026-01-28): Compress output before caching
    compressed_output = tool_output
    compression_applied = None

    if HEADROOM_AVAILABLE and output_size > 2000:
        try:
            # Try to parse as JSON for structured compression
            parsed = json.loads(tool_output) if tool_output.startswith(('[', '{')) else None
            if parsed and isinstance(parsed, (list, dict)):
                compressed = compress_tool_output(parsed, max_items=15)
                compressed_output = json.dumps(compressed)
                compression_applied = "headroom"
        except (json.JSONDecodeError, TypeError):
            pass  # Keep original if not JSON

    if TOONIFY_AVAILABLE and compression_applied is None and output_size > 3000:
        try:
            parsed = json.loads(tool_output) if tool_output.startswith(('[', '{')) else None
            if parsed and isinstance(parsed, (list, dict)):
                result = estimate_savings(parsed)
                if result.savings_pct >= 30:  # Only if significant savings
                    compressed_output = result.toon_str
                    compression_applied = "toonify"
        except (json.JSONDecodeError, TypeError):
            pass

    # Build cache data
    cache_data = {
        "result": compressed_output,
        "tool": tool_name,
        "size": len(compressed_output),
        "original_size": output_size,
        "compression": compression_applied
    }

    # Add file mtime for Read operations (cache invalidation)
    if tool_name == "Read" and "file_path" in tool_input:
        cache_data["mtime"] = str(get_file_mtime(tool_input["file_path"]))

    # Cache to Dragonfly
    try:
        cache.hset(key, cache_data, ttl=ttl)
    except Exception:
        pass  # Don't fail on cache errors

    print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
