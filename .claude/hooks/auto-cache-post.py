#!/usr/bin/env python3
"""
Auto-Cache PostToolUse Hook

Automatically caches outputs from Read, Grep, Glob operations
for token efficiency. Works with token-optimizer MCP.

Caches:
- File reads (by path + mtime)
- Grep results (by pattern + path)
- Glob results (by pattern)
"""

import sys
import json
import hashlib
import os
from pathlib import Path
from datetime import datetime

# Cache settings
CACHE_DIR = Path.home() / ".token-optimizer-cache" / "auto-cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Tools to cache
CACHEABLE_TOOLS = {"Read", "Grep", "Glob"}

# Size thresholds (only cache substantial outputs)
MIN_CACHE_SIZE = 500  # bytes
MAX_CACHE_SIZE = 100000  # 100KB max per entry

def get_cache_key(tool_name: str, params: dict) -> str:
    """Generate cache key from tool + params."""
    # Normalize params
    key_data = f"{tool_name}:{json.dumps(params, sort_keys=True)}"
    return hashlib.md5(key_data.encode()).hexdigest()

def get_file_mtime(path: str) -> float:
    """Get file modification time for cache invalidation."""
    try:
        return Path(path).stat().st_mtime
    except:
        return 0

def cache_result(key: str, result: str, metadata: dict = None):
    """Store result in cache."""
    cache_file = CACHE_DIR / f"{key}.json"

    data = {
        "result": result,
        "cached_at": datetime.now().isoformat(),
        "metadata": metadata or {}
    }

    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(data, f)

def main():
    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except:
        # No input or invalid JSON
        print(json.dumps({"continue": True}))
        return

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    tool_output = hook_input.get("tool_output", "")

    # Only cache specific tools
    if tool_name not in CACHEABLE_TOOLS:
        print(json.dumps({"continue": True}))
        return

    # Check size thresholds
    output_size = len(tool_output) if tool_output else 0
    if output_size < MIN_CACHE_SIZE or output_size > MAX_CACHE_SIZE:
        print(json.dumps({"continue": True}))
        return

    # Generate cache key
    cache_key = get_cache_key(tool_name, tool_input)

    # Add file mtime for Read operations (cache invalidation)
    metadata = {"tool": tool_name, "size": output_size}
    if tool_name == "Read" and "file_path" in tool_input:
        metadata["mtime"] = get_file_mtime(tool_input["file_path"])

    # Cache the result
    try:
        cache_result(cache_key, tool_output, metadata)
    except Exception as e:
        # Don't fail on cache errors
        pass

    print(json.dumps({"continue": True}))

if __name__ == "__main__":
    main()
