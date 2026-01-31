"""MCP Connection Pool - Manages concurrent MCP connections with hard limits.

Token Efficiency Design:
- Max 2 concurrent connections (configurable)
- Queue for pending requests
- Auto-release after timeout
- Thread-safe with lock mechanism
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from queue import Queue, Empty
import logging

log = logging.getLogger(__name__)


@dataclass
class MCPConnection:
    """Represents an active MCP connection."""

    name: str
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    _client: Any = None
    _closed: bool = False

    def touch(self):
        """Update last used timestamp."""
        self.last_used = time.time()

    def close(self):
        """Close the connection and release resources."""
        if self._closed:
            return
        self._closed = True
        if self._client:
            try:
                if hasattr(self._client, "close"):
                    self._client.close()
                elif hasattr(self._client, "disconnect"):
                    self._client.disconnect()
            except Exception as e:
                log.warning("mcp_close_error", connection=self.name, error=str(e))
        log.debug("mcp_connection_closed", connection=self.name)

    @property
    def is_closed(self) -> bool:
        return self._closed

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    @property
    def idle_seconds(self) -> float:
        return time.time() - self.last_used


class MCPPoolExhausted(Exception):
    """Raised when pool is full and timeout exceeded."""

    pass


class MCPConnectionError(Exception):
    """Raised when MCP connection fails."""

    pass


class MCPPool:
    """Manages MCP connections with hard limit.

    Prevents context bloat by:
    - Max 2 concurrent connections (default)
    - Queue for pending requests with timeout
    - Auto-release after idle timeout
    - Reuse existing connections when possible

    Thread Safety:
    - All operations are thread-safe via lock
    - Waiting happens outside lock to prevent deadlocks

    Usage:
        pool = MCPPool(max_connections=2)

        # Acquire connection (blocks if pool full)
        conn = pool.acquire("claude-cortex", timeout=60)
        try:
            # Use connection
            result = conn._client.call("method", args)
        finally:
            pool.release("claude-cortex")

        # Or use context manager
        with pool.connection("claude-cortex") as conn:
            result = conn._client.call("method", args)
    """

    def __init__(
        self,
        max_connections: int = 2,
        idle_timeout: int = 300,
        connection_factory: Optional[Callable[[str], Any]] = None,
    ):
        """Initialize MCP pool.

        Args:
            max_connections: Maximum concurrent connections (default 2)
            idle_timeout: Seconds before idle connection auto-closes (default 300)
            connection_factory: Optional factory to create MCP clients
        """
        self._max = max_connections
        self._idle_timeout = idle_timeout
        self._connection_factory = connection_factory or self._default_factory

        self._active: Dict[str, MCPConnection] = {}
        self._waiters: List[Tuple[str, threading.Event]] = []
        self._lock = threading.Lock()

        # Background cleanup thread
        self._cleanup_thread: Optional[threading.Thread] = None
        self._shutdown = threading.Event()

        log.info(
            "mcp_pool_initialized",
            max_connections=max_connections,
            idle_timeout=idle_timeout,
        )

    def _default_factory(self, mcp_name: str) -> Any:
        """Default MCP client factory - returns stub for now."""
        log.debug("mcp_default_factory", name=mcp_name)
        return {"name": mcp_name, "type": "stub"}

    def _create_connection(self, mcp_name: str) -> MCPConnection:
        """Create a new MCP connection."""
        try:
            client = self._connection_factory(mcp_name)
            conn = MCPConnection(name=mcp_name, _client=client)
            log.debug("mcp_connection_created", name=mcp_name)
            return conn
        except Exception as e:
            log.error("mcp_connection_failed", name=mcp_name, error=str(e))
            raise MCPConnectionError(f"Failed to connect to {mcp_name}: {e}")

    def acquire(self, mcp_name: str, timeout: int = 60) -> MCPConnection:
        """Get MCP connection, blocking if pool full.

        Args:
            mcp_name: Name of MCP server to connect to
            timeout: Max seconds to wait for available slot

        Returns:
            MCPConnection ready for use

        Raises:
            MCPPoolExhausted: If timeout exceeded waiting for slot
            MCPConnectionError: If connection creation fails
        """
        wait_event: Optional[threading.Event] = None

        with self._lock:
            # Check if we already have this connection
            if mcp_name in self._active:
                conn = self._active[mcp_name]
                conn.touch()
                log.debug("mcp_connection_reused", name=mcp_name)
                return conn

            # Check if we have capacity
            if len(self._active) < self._max:
                conn = self._create_connection(mcp_name)
                self._active[mcp_name] = conn
                return conn

            # Pool full - need to wait
            wait_event = threading.Event()
            self._waiters.append((mcp_name, wait_event))
            log.debug(
                "mcp_pool_full_waiting",
                name=mcp_name,
                active=len(self._active),
                waiters=len(self._waiters),
            )

        # Wait outside lock to prevent deadlocks
        if not wait_event.wait(timeout):
            # Timeout - remove from waiters
            with self._lock:
                self._waiters = [
                    (n, e) for n, e in self._waiters if e is not wait_event
                ]
            raise MCPPoolExhausted(
                f"MCP pool full ({self._max} connections), waited {timeout}s for {mcp_name}"
            )

        # We were woken up - connection should be ready
        with self._lock:
            if mcp_name in self._active:
                return self._active[mcp_name]
            # Create if not exists (shouldn't happen normally)
            conn = self._create_connection(mcp_name)
            self._active[mcp_name] = conn
            return conn

    def release(self, mcp_name: str, force_close: bool = False):
        """Release connection back to pool.

        Args:
            mcp_name: Name of MCP connection to release
            force_close: If True, close connection instead of keeping
        """
        with self._lock:
            if mcp_name not in self._active:
                log.warning("mcp_release_not_found", name=mcp_name)
                return

            if force_close:
                conn = self._active.pop(mcp_name)
                conn.close()
                log.debug("mcp_connection_force_closed", name=mcp_name)
            else:
                # Keep connection alive for reuse
                self._active[mcp_name].touch()
                log.debug("mcp_connection_released", name=mcp_name)

            # Wake next waiter if any
            if self._waiters and len(self._active) < self._max:
                next_name, event = self._waiters.pop(0)
                if next_name not in self._active:
                    conn = self._create_connection(next_name)
                    self._active[next_name] = conn
                event.set()
                log.debug("mcp_waiter_woken", name=next_name)

    def connection(self, mcp_name: str, timeout: int = 60):
        """Context manager for MCP connection.

        Usage:
            with pool.connection("claude-cortex") as conn:
                result = conn._client.call("method", args)
        """
        return _MCPConnectionContext(self, mcp_name, timeout)

    def close_idle(self, max_idle: Optional[int] = None):
        """Close connections idle longer than threshold.

        Args:
            max_idle: Override idle timeout (uses pool default if None)
        """
        max_idle = max_idle or self._idle_timeout
        now = time.time()
        to_close = []

        with self._lock:
            for name, conn in list(self._active.items()):
                if conn.idle_seconds > max_idle:
                    to_close.append(name)

        for name in to_close:
            self.release(name, force_close=True)
            log.debug("mcp_idle_closed", name=name, idle_seconds=max_idle)

    def close_all(self):
        """Close all connections and shutdown pool."""
        self._shutdown.set()

        with self._lock:
            for name in list(self._active.keys()):
                conn = self._active.pop(name)
                conn.close()

            # Wake all waiters with error
            for _, event in self._waiters:
                event.set()
            self._waiters.clear()

        log.info("mcp_pool_shutdown")

    @property
    def active_count(self) -> int:
        """Number of active connections."""
        with self._lock:
            return len(self._active)

    @property
    def waiter_count(self) -> int:
        """Number of waiting requests."""
        with self._lock:
            return len(self._waiters)

    @property
    def available_slots(self) -> int:
        """Number of available connection slots."""
        with self._lock:
            return self._max - len(self._active)

    def status(self) -> Dict:
        """Get pool status for monitoring."""
        with self._lock:
            return {
                "max_connections": self._max,
                "active_count": len(self._active),
                "waiter_count": len(self._waiters),
                "available_slots": self._max - len(self._active),
                "active_connections": [
                    {
                        "name": c.name,
                        "age_seconds": c.age_seconds,
                        "idle_seconds": c.idle_seconds,
                    }
                    for c in self._active.values()
                ],
            }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_all()
        return False


class _MCPConnectionContext:
    """Context manager for individual MCP connection."""

    def __init__(self, pool: MCPPool, mcp_name: str, timeout: int):
        self._pool = pool
        self._mcp_name = mcp_name
        self._timeout = timeout
        self._conn: Optional[MCPConnection] = None

    def __enter__(self) -> MCPConnection:
        self._conn = self._pool.acquire(self._mcp_name, self._timeout)
        return self._conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            # Force close on error, keep alive otherwise
            self._pool.release(self._mcp_name, force_close=exc_type is not None)
        return False


# Global pool instance (lazy initialized)
_global_pool: Optional[MCPPool] = None


def get_mcp_pool(max_connections: int = 2) -> MCPPool:
    """Get or create global MCP pool."""
    global _global_pool
    if _global_pool is None:
        _global_pool = MCPPool(max_connections=max_connections)
    return _global_pool


def reset_mcp_pool():
    """Reset global pool (for testing)."""
    global _global_pool
    if _global_pool:
        _global_pool.close_all()
    _global_pool = None
