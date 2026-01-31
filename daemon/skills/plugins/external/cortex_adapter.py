"""Claude Cortex adapter - Brain-like memory system.

MCP-based adapter for Claude Cortex memory operations:
- Short-term memory (session-level)
- Long-term memory (persistent)
- Episodic memory with salience detection
- Memory batching for efficiency
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging

from .base_adapter import MCPToolAdapter

if TYPE_CHECKING:
    from ..mcp_pool import MCPConnection

log = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A memory entry with metadata."""

    key: str
    value: Any
    salience: float = 0.5
    memory_type: str = "short_term"  # short_term, long_term, episodic
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "key": self.key,
            "value": self.value,
            "salience": self.salience,
            "memory_type": self.memory_type,
            "created_at": self.created_at,
            "accessed_at": self.accessed_at,
            "access_count": self.access_count,
            "tags": self.tags,
        }


class CortexAdapter(MCPToolAdapter):
    """Adapter for Claude Cortex memory system.

    Token Efficiency:
    - Batches memory operations (default 10)
    - Auto-flushes on execute completion
    - Salience-based retrieval (most relevant first)

    Usage:
        adapter = CortexAdapter(mcp_pool)

        # Store memory
        result = adapter.execute({
            "operation": "store",
            "key": "user_preference",
            "value": {"theme": "dark"},
            "salience": 0.8,
            "memory_type": "long_term"
        }, budget_tokens=1000)

        # Retrieve memory
        result = adapter.execute({
            "operation": "retrieve",
            "key": "user_preference"
        }, budget_tokens=500)

        # Search memories
        result = adapter.execute({
            "operation": "search",
            "query": "preferences",
            "limit": 5
        }, budget_tokens=1000)
    """

    BATCH_SIZE = 10  # Flush after this many operations

    def __init__(self, mcp_pool=None):
        super().__init__(mcp_pool)
        self._batch: List[Dict] = []
        self._local_cache: Dict[str, MemoryEntry] = {}

    @property
    def tool_name(self) -> str:
        return "claude-cortex"

    def _invoke_with_mcp(
        self, conn: "MCPConnection", input_data: Dict, budget: int
    ) -> Dict:
        """Execute Cortex operation via MCP.

        Args:
            conn: Active MCP connection
            input_data: {
                "operation": "store" | "retrieve" | "search" | "batch_store",
                "key": str (for store/retrieve),
                "value": Any (for store),
                "query": str (for search),
                ...
            }
            budget: Token budget

        Returns:
            Operation-specific result
        """
        operation = input_data.get("operation", "retrieve")
        self._track_tokens(50)  # Base overhead

        if operation == "store":
            return self._store(conn, input_data)
        elif operation == "retrieve":
            return self._retrieve(conn, input_data)
        elif operation == "search":
            return self._search(conn, input_data)
        elif operation == "batch_store":
            return self._batch_store(conn, input_data)
        elif operation == "decay":
            return self._apply_decay(conn, input_data)
        else:
            return {"error": f"Unknown operation: {operation}"}

    def _store(self, conn: "MCPConnection", input_data: Dict) -> Dict:
        """Store a memory entry."""
        key = input_data.get("key")
        value = input_data.get("value")
        salience = input_data.get("salience", 0.5)
        memory_type = input_data.get("memory_type", "short_term")
        tags = input_data.get("tags", [])

        if not key:
            return {"error": "No key provided"}

        entry = MemoryEntry(
            key=key,
            value=value,
            salience=salience,
            memory_type=memory_type,
            tags=tags,
        )

        # Add to batch
        self._batch.append({"action": "store", "entry": entry.to_dict()})

        # Also cache locally
        self._local_cache[key] = entry

        self._track_tokens(len(json.dumps(entry.to_dict())) // 4)

        # Auto-flush if batch full
        if len(self._batch) >= self.BATCH_SIZE:
            self._flush_batch(conn)

        return {
            "stored": True,
            "key": key,
            "memory_type": memory_type,
            "batch_size": len(self._batch),
        }

    def _retrieve(self, conn: "MCPConnection", input_data: Dict) -> Dict:
        """Retrieve a memory entry."""
        key = input_data.get("key")
        if not key:
            return {"error": "No key provided"}

        # Check local cache first
        if key in self._local_cache:
            entry = self._local_cache[key]
            entry.accessed_at = time.time()
            entry.access_count += 1
            # Reinforce salience on access
            entry.salience = min(1.0, entry.salience * 1.1)

            self._track_tokens(len(json.dumps(entry.to_dict())) // 4)
            return {
                "found": True,
                "entry": entry.to_dict(),
                "source": "cache",
            }

        # Try MCP if not in cache
        try:
            if conn._client and hasattr(conn._client, "call"):
                result = conn._client.call("memory.retrieve", {"key": key})
                if result:
                    self._track_tokens(len(json.dumps(result)) // 4)
                    return {"found": True, "entry": result, "source": "cortex"}
        except Exception as e:
            log.warning("cortex_retrieve_error", key=key, error=str(e))

        return {"found": False, "key": key}

    def _search(self, conn: "MCPConnection", input_data: Dict) -> Dict:
        """Search memories by query."""
        query = input_data.get("query", "")
        limit = input_data.get("limit", 10)
        memory_type = input_data.get("memory_type")  # Optional filter

        self._track_tokens(len(query) // 4)

        # Search local cache first
        results = []
        query_lower = query.lower()

        for key, entry in self._local_cache.items():
            # Simple relevance scoring
            score = 0.0
            if query_lower in key.lower():
                score += 0.5
            if isinstance(entry.value, str) and query_lower in entry.value.lower():
                score += 0.3
            if any(query_lower in tag.lower() for tag in entry.tags):
                score += 0.2

            # Apply salience weight
            score *= entry.salience

            # Filter by memory type if specified
            if memory_type and entry.memory_type != memory_type:
                continue

            if score > 0:
                results.append({
                    "entry": entry.to_dict(),
                    "relevance": score,
                })

        # Sort by relevance
        results.sort(key=lambda x: x["relevance"], reverse=True)
        results = results[:limit]

        self._track_tokens(len(json.dumps(results)) // 4)

        return {
            "query": query,
            "results": results,
            "count": len(results),
            "source": "cache",
        }

    def _batch_store(self, conn: "MCPConnection", input_data: Dict) -> Dict:
        """Store multiple entries at once."""
        entries = input_data.get("entries", [])
        if not entries:
            return {"error": "No entries provided"}

        stored = 0
        for entry_data in entries:
            entry = MemoryEntry(
                key=entry_data.get("key", f"entry_{stored}"),
                value=entry_data.get("value"),
                salience=entry_data.get("salience", 0.5),
                memory_type=entry_data.get("memory_type", "short_term"),
                tags=entry_data.get("tags", []),
            )
            self._local_cache[entry.key] = entry
            self._batch.append({"action": "store", "entry": entry.to_dict()})
            stored += 1

        self._track_tokens(len(json.dumps(entries)) // 4)

        # Flush if batch full
        if len(self._batch) >= self.BATCH_SIZE:
            self._flush_batch(conn)

        return {"stored": stored, "batch_size": len(self._batch)}

    def _apply_decay(self, conn: "MCPConnection", input_data: Dict) -> Dict:
        """Apply temporal decay to memories.

        Memories fade over time unless reinforced by access.
        """
        decay_rate = input_data.get("decay_rate", 0.1)
        min_salience = input_data.get("min_salience", 0.1)
        now = time.time()

        decayed = 0
        removed = 0

        for key, entry in list(self._local_cache.items()):
            # Calculate time-based decay
            hours_since_access = (now - entry.accessed_at) / 3600
            decay = decay_rate * hours_since_access

            # Apply decay
            entry.salience = max(min_salience, entry.salience - decay)

            # Remove if below threshold and short-term
            if entry.salience <= min_salience and entry.memory_type == "short_term":
                del self._local_cache[key]
                removed += 1
            else:
                decayed += 1

        return {
            "decayed": decayed,
            "removed": removed,
            "remaining": len(self._local_cache),
        }

    def _flush_batch(self, conn: "MCPConnection"):
        """Flush pending batch to Cortex."""
        if not self._batch:
            return

        try:
            if conn._client and hasattr(conn._client, "call"):
                conn._client.call("memory.batch", {"operations": self._batch})
                log.debug("cortex_batch_flushed", count=len(self._batch))
        except Exception as e:
            log.warning("cortex_flush_error", error=str(e))

        self._batch = []

    def cleanup(self):
        """Cleanup - flush any pending batch."""
        # Note: Can't flush without connection, batch will be lost
        if self._batch:
            log.warning("cortex_batch_lost", count=len(self._batch))
        self._batch = []
        super().cleanup()

    def get_cache_stats(self) -> Dict:
        """Get local cache statistics."""
        if not self._local_cache:
            return {"count": 0}

        return {
            "count": len(self._local_cache),
            "by_type": {
                mtype: sum(1 for e in self._local_cache.values() if e.memory_type == mtype)
                for mtype in ["short_term", "long_term", "episodic"]
            },
            "avg_salience": sum(e.salience for e in self._local_cache.values()) / len(self._local_cache),
            "pending_batch": len(self._batch),
        }
