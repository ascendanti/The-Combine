#!/usr/bin/env python3
"""
Dragonfly MCP Server - Redis-compatible caching layer for Claude Code.

Provides:
- Key-value caching with TTL
- Session state persistence
- Context offloading for token reduction
- Semantic cache for repeated queries
"""

import json
import sys
import hashlib
from datetime import datetime
from typing import Any, Optional

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# MCP Protocol helpers
def send_response(id: str, result: Any):
    response = {"jsonrpc": "2.0", "id": id, "result": result}
    print(json.dumps(response), flush=True)

def send_error(id: str, code: int, message: str):
    response = {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}
    print(json.dumps(response), flush=True)

# Redis connection
def get_redis() -> Optional[redis.Redis]:
    if not REDIS_AVAILABLE:
        return None
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        return r
    except:
        return None

# Tool implementations
def cache_set(key: str, value: str, ttl: int = 3600) -> dict:
    """Store a value in cache with optional TTL."""
    r = get_redis()
    if not r:
        return {"success": False, "error": "Redis not available"}

    r.setex(f"claude:{key}", ttl, value)
    return {"success": True, "key": key, "ttl": ttl}

def cache_get(key: str) -> dict:
    """Retrieve a value from cache."""
    r = get_redis()
    if not r:
        return {"success": False, "error": "Redis not available"}

    value = r.get(f"claude:{key}")
    if value is None:
        return {"success": False, "found": False}
    return {"success": True, "found": True, "value": value}

def cache_delete(key: str) -> dict:
    """Delete a key from cache."""
    r = get_redis()
    if not r:
        return {"success": False, "error": "Redis not available"}

    deleted = r.delete(f"claude:{key}")
    return {"success": True, "deleted": deleted > 0}

def cache_keys(pattern: str = "*") -> dict:
    """List keys matching pattern."""
    r = get_redis()
    if not r:
        return {"success": False, "error": "Redis not available"}

    keys = r.keys(f"claude:{pattern}")
    # Strip prefix
    keys = [k.replace("claude:", "", 1) for k in keys]
    return {"success": True, "keys": keys[:100]}  # Limit to 100

def session_save(session_id: str, data: dict) -> dict:
    """Save session state."""
    r = get_redis()
    if not r:
        return {"success": False, "error": "Redis not available"}

    key = f"session:{session_id}"
    data["_updated"] = datetime.now().isoformat()
    r.hset(f"claude:{key}", mapping={k: json.dumps(v) for k, v in data.items()})
    r.expire(f"claude:{key}", 86400 * 7)  # 7 days
    return {"success": True, "session_id": session_id}

def session_load(session_id: str) -> dict:
    """Load session state."""
    r = get_redis()
    if not r:
        return {"success": False, "error": "Redis not available"}

    key = f"session:{session_id}"
    data = r.hgetall(f"claude:{key}")
    if not data:
        return {"success": False, "found": False}

    # Parse JSON values
    parsed = {}
    for k, v in data.items():
        try:
            parsed[k] = json.loads(v)
        except:
            parsed[k] = v
    return {"success": True, "found": True, "data": parsed}

def context_offload(context_id: str, content: str, metadata: dict = None) -> dict:
    """Offload large context to cache for token reduction."""
    r = get_redis()
    if not r:
        return {"success": False, "error": "Redis not available"}

    key = f"context:{context_id}"
    payload = {
        "content": content,
        "metadata": metadata or {},
        "tokens_approx": len(content) // 4,
        "stored_at": datetime.now().isoformat()
    }
    r.setex(f"claude:{key}", 3600 * 24, json.dumps(payload))  # 24 hours

    return {
        "success": True,
        "context_id": context_id,
        "tokens_saved": payload["tokens_approx"],
        "retrieval_hint": f"Use context_recall('{context_id}') to retrieve"
    }

def context_recall(context_id: str) -> dict:
    """Recall offloaded context."""
    r = get_redis()
    if not r:
        return {"success": False, "error": "Redis not available"}

    key = f"context:{context_id}"
    data = r.get(f"claude:{key}")
    if not data:
        return {"success": False, "found": False}

    payload = json.loads(data)
    return {"success": True, "found": True, **payload}

def semantic_cache_set(query: str, response: str, ttl: int = 1800) -> dict:
    """Cache a query-response pair for semantic deduplication."""
    r = get_redis()
    if not r:
        return {"success": False, "error": "Redis not available"}

    # Simple hash-based key (for exact matches)
    query_hash = hashlib.sha256(query.lower().strip().encode()).hexdigest()[:16]
    key = f"semantic:{query_hash}"

    payload = {
        "query": query,
        "response": response,
        "cached_at": datetime.now().isoformat()
    }
    r.setex(f"claude:{key}", ttl, json.dumps(payload))
    return {"success": True, "cache_key": query_hash}

def semantic_cache_get(query: str) -> dict:
    """Check if a similar query has been cached."""
    r = get_redis()
    if not r:
        return {"success": False, "error": "Redis not available"}

    query_hash = hashlib.sha256(query.lower().strip().encode()).hexdigest()[:16]
    key = f"semantic:{query_hash}"

    data = r.get(f"claude:{key}")
    if not data:
        return {"success": False, "found": False}

    payload = json.loads(data)
    return {"success": True, "found": True, **payload}

def stats() -> dict:
    """Get cache statistics."""
    r = get_redis()
    if not r:
        return {"success": False, "error": "Redis not available"}

    info = r.info("memory")
    keys = r.keys("claude:*")

    return {
        "success": True,
        "total_keys": len(keys),
        "memory_used": info.get("used_memory_human", "unknown"),
        "contexts_cached": len([k for k in keys if b"context:" in k.encode() if isinstance(k, str) else k]),
        "sessions_active": len([k for k in keys if "session:" in k]),
        "semantic_cache_entries": len([k for k in keys if "semantic:" in k])
    }

# MCP Tool definitions
TOOLS = [
    {
        "name": "dragonfly_cache_set",
        "description": "Store a value in Dragonfly cache with optional TTL",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Cache key"},
                "value": {"type": "string", "description": "Value to store"},
                "ttl": {"type": "integer", "description": "Time to live in seconds", "default": 3600}
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "dragonfly_cache_get",
        "description": "Retrieve a value from Dragonfly cache",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Cache key"}
            },
            "required": ["key"]
        }
    },
    {
        "name": "dragonfly_cache_delete",
        "description": "Delete a key from cache",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Cache key"}
            },
            "required": ["key"]
        }
    },
    {
        "name": "dragonfly_cache_keys",
        "description": "List cache keys matching pattern",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Pattern to match (default: *)", "default": "*"}
            }
        }
    },
    {
        "name": "dragonfly_session_save",
        "description": "Save session state for cross-session persistence",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session identifier"},
                "data": {"type": "object", "description": "Session data to save"}
            },
            "required": ["session_id", "data"]
        }
    },
    {
        "name": "dragonfly_session_load",
        "description": "Load saved session state",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session identifier"}
            },
            "required": ["session_id"]
        }
    },
    {
        "name": "dragonfly_context_offload",
        "description": "Offload large context to cache to reduce token usage. Returns a context_id for later recall.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "context_id": {"type": "string", "description": "Unique identifier for this context"},
                "content": {"type": "string", "description": "Content to offload"},
                "metadata": {"type": "object", "description": "Optional metadata"}
            },
            "required": ["context_id", "content"]
        }
    },
    {
        "name": "dragonfly_context_recall",
        "description": "Recall previously offloaded context by ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "context_id": {"type": "string", "description": "Context identifier"}
            },
            "required": ["context_id"]
        }
    },
    {
        "name": "dragonfly_semantic_cache_set",
        "description": "Cache a query-response pair for deduplication of repeated queries",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The query/question"},
                "response": {"type": "string", "description": "The response to cache"},
                "ttl": {"type": "integer", "description": "Time to live in seconds", "default": 1800}
            },
            "required": ["query", "response"]
        }
    },
    {
        "name": "dragonfly_semantic_cache_get",
        "description": "Check if a similar query has a cached response",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The query to check"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "dragonfly_stats",
        "description": "Get Dragonfly cache statistics",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]

def handle_request(request: dict):
    """Handle incoming MCP request."""
    method = request.get("method", "")
    id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        send_response(id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "dragonfly-cache", "version": "1.0.0"}
        })

    elif method == "tools/list":
        send_response(id, {"tools": TOOLS})

    elif method == "tools/call":
        tool_name = params.get("name", "")
        args = params.get("arguments", {})

        try:
            if tool_name == "dragonfly_cache_set":
                result = cache_set(args["key"], args["value"], args.get("ttl", 3600))
            elif tool_name == "dragonfly_cache_get":
                result = cache_get(args["key"])
            elif tool_name == "dragonfly_cache_delete":
                result = cache_delete(args["key"])
            elif tool_name == "dragonfly_cache_keys":
                result = cache_keys(args.get("pattern", "*"))
            elif tool_name == "dragonfly_session_save":
                result = session_save(args["session_id"], args["data"])
            elif tool_name == "dragonfly_session_load":
                result = session_load(args["session_id"])
            elif tool_name == "dragonfly_context_offload":
                result = context_offload(args["context_id"], args["content"], args.get("metadata"))
            elif tool_name == "dragonfly_context_recall":
                result = context_recall(args["context_id"])
            elif tool_name == "dragonfly_semantic_cache_set":
                result = semantic_cache_set(args["query"], args["response"], args.get("ttl", 1800))
            elif tool_name == "dragonfly_semantic_cache_get":
                result = semantic_cache_get(args["query"])
            elif tool_name == "dragonfly_stats":
                result = stats()
            else:
                send_error(id, -32601, f"Unknown tool: {tool_name}")
                return

            send_response(id, {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]})

        except Exception as e:
            send_response(id, {"content": [{"type": "text", "text": json.dumps({"error": str(e)})}]})

    elif method == "notifications/initialized":
        pass  # No response needed

    else:
        if id:
            send_error(id, -32601, f"Unknown method: {method}")

def main():
    """Main MCP server loop."""
    # Check Redis availability
    r = get_redis()
    if not r:
        sys.stderr.write("Warning: Redis/Dragonfly not available. Install redis-py: pip install redis\n")

    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            handle_request(request)
        except json.JSONDecodeError:
            continue
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")

if __name__ == "__main__":
    main()
