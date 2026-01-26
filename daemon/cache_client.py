#!/usr/bin/env python3
"""
Unified Cache Client for Dragonfly

Provides a simple interface for all caching needs across hooks and daemon modules.
Uses Dragonfly (Redis-compatible) running on localhost:6379.

Usage:
    from cache_client import cache

    # Set with TTL
    cache.set("key", "value", ttl=3600)

    # Get
    value = cache.get("key")

    # Hash operations for structured data
    cache.hset("file:path/to/file", {"content": "...", "mtime": 123})
    data = cache.hgetall("file:path/to/file")
"""

import json
import hashlib
from typing import Any, Optional, Dict
from pathlib import Path

# Try redis, fallback to file-based
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Dragonfly connection settings
DRAGONFLY_HOST = "localhost"
DRAGONFLY_PORT = 6379
DRAGONFLY_DB = 0

# Fallback file cache
FALLBACK_CACHE_DIR = Path.home() / ".atlas-cache"


class DragonflyCache:
    """Dragonfly/Redis cache client with file fallback."""

    def __init__(self):
        self._client = None
        self._fallback_mode = False
        self._connect()

    def _connect(self):
        """Connect to Dragonfly or enable fallback."""
        if not REDIS_AVAILABLE:
            self._fallback_mode = True
            FALLBACK_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            return

        try:
            self._client = redis.Redis(
                host=DRAGONFLY_HOST,
                port=DRAGONFLY_PORT,
                db=DRAGONFLY_DB,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # Test connection
            self._client.ping()
        except (redis.ConnectionError, redis.TimeoutError):
            self._fallback_mode = True
            FALLBACK_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _fallback_path(self, key: str) -> Path:
        """Get fallback file path for a key."""
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return FALLBACK_CACHE_DIR / f"{safe_key}.json"

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set a value with optional TTL (seconds)."""
        try:
            if self._fallback_mode:
                data = {"value": value, "ttl": ttl}
                self._fallback_path(key).write_text(json.dumps(data))
                return True

            if isinstance(value, (dict, list)):
                value = json.dumps(value)

            if ttl > 0:
                self._client.setex(key, ttl, value)
            else:
                self._client.set(key, value)
            return True
        except Exception:
            return False

    def get(self, key: str) -> Optional[str]:
        """Get a value."""
        try:
            if self._fallback_mode:
                path = self._fallback_path(key)
                if path.exists():
                    data = json.loads(path.read_text())
                    return data.get("value")
                return None

            return self._client.get(key)
        except Exception:
            return None

    def get_json(self, key: str) -> Optional[Any]:
        """Get and parse JSON value."""
        value = self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    def delete(self, key: str) -> bool:
        """Delete a key."""
        try:
            if self._fallback_mode:
                path = self._fallback_path(key)
                if path.exists():
                    path.unlink()
                return True

            self._client.delete(key)
            return True
        except Exception:
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            if self._fallback_mode:
                return self._fallback_path(key).exists()

            return bool(self._client.exists(key))
        except Exception:
            return False

    def hset(self, key: str, mapping: Dict[str, Any], ttl: int = 3600) -> bool:
        """Set hash fields."""
        try:
            if self._fallback_mode:
                data = {"mapping": mapping, "ttl": ttl}
                self._fallback_path(key).write_text(json.dumps(data))
                return True

            # Convert non-string values to JSON
            clean_mapping = {}
            for k, v in mapping.items():
                if isinstance(v, (dict, list)):
                    clean_mapping[k] = json.dumps(v)
                else:
                    clean_mapping[k] = str(v) if v is not None else ""

            self._client.hset(key, mapping=clean_mapping)
            if ttl > 0:
                self._client.expire(key, ttl)
            return True
        except Exception:
            return False

    def hgetall(self, key: str) -> Optional[Dict[str, str]]:
        """Get all hash fields."""
        try:
            if self._fallback_mode:
                path = self._fallback_path(key)
                if path.exists():
                    data = json.loads(path.read_text())
                    return data.get("mapping", {})
                return None

            result = self._client.hgetall(key)
            return result if result else None
        except Exception:
            return None

    def hget(self, key: str, field: str) -> Optional[str]:
        """Get single hash field."""
        try:
            if self._fallback_mode:
                data = self.hgetall(key)
                return data.get(field) if data else None

            return self._client.hget(key, field)
        except Exception:
            return None

    def keys(self, pattern: str = "*") -> list:
        """Get keys matching pattern."""
        try:
            if self._fallback_mode:
                # Simple pattern matching for fallback
                return list(FALLBACK_CACHE_DIR.glob("*.json"))

            return self._client.keys(pattern)
        except Exception:
            return []

    def info(self) -> Dict[str, Any]:
        """Get cache info/stats."""
        try:
            if self._fallback_mode:
                files = list(FALLBACK_CACHE_DIR.glob("*.json"))
                return {
                    "mode": "fallback",
                    "keys": len(files),
                    "path": str(FALLBACK_CACHE_DIR)
                }

            info = self._client.info("keyspace")
            stats = self._client.info("stats")
            return {
                "mode": "dragonfly",
                "keyspace": info,
                "hits": stats.get("keyspace_hits", 0),
                "misses": stats.get("keyspace_misses", 0),
                "hit_ratio": stats.get("keyspace_hits", 0) / max(1, stats.get("keyspace_hits", 0) + stats.get("keyspace_misses", 0))
            }
        except Exception as e:
            return {"error": str(e)}

    @property
    def is_connected(self) -> bool:
        """Check if connected to Dragonfly."""
        if self._fallback_mode:
            return False
        try:
            self._client.ping()
            return True
        except:
            return False


# Global cache instance
cache = DragonflyCache()


# Convenience functions
def cache_key(prefix: str, *args) -> str:
    """Generate a cache key from prefix and args."""
    parts = [str(a) for a in args]
    return f"{prefix}:{':'.join(parts)}"


def file_cache_key(file_path: str) -> str:
    """Generate cache key for a file."""
    return f"file:{file_path}"


def tool_cache_key(tool_name: str, params: dict) -> str:
    """Generate cache key for a tool invocation."""
    param_hash = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:12]
    return f"tool:{tool_name}:{param_hash}"


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python cache_client.py info    - Show cache stats")
        print("  python cache_client.py test    - Test cache operations")
        print("  python cache_client.py get <key>")
        print("  python cache_client.py set <key> <value>")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "info":
        info = cache.info()
        print(json.dumps(info, indent=2))

    elif cmd == "test":
        print("Testing cache...")
        cache.set("test:key", "test_value", ttl=60)
        val = cache.get("test:key")
        print(f"  set/get: {'OK' if val == 'test_value' else 'FAIL'}")

        cache.hset("test:hash", {"field1": "value1", "field2": 123}, ttl=60)
        hval = cache.hgetall("test:hash")
        print(f"  hset/hgetall: {'OK' if hval and 'field1' in hval else 'FAIL'}")

        cache.delete("test:key")
        cache.delete("test:hash")
        print(f"  Mode: {cache.info().get('mode', 'unknown')}")
        print("Done.")

    elif cmd == "get" and len(sys.argv) > 2:
        val = cache.get(sys.argv[2])
        print(val if val else "(not found)")

    elif cmd == "set" and len(sys.argv) > 3:
        cache.set(sys.argv[2], sys.argv[3])
        print("OK")

    else:
        print(f"Unknown command: {cmd}")
