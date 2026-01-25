#!/usr/bin/env python3
"""
Message Bus for Unified Subsystem Communication

All subsystems communicate through this central bus, enabling:
- Loose coupling between components
- Event-driven architecture
- Easy addition of new subsystems
- Cross-domain signal correlation

Can use Redis (distributed) or in-memory (single process).
"""

import json
import queue
import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import asdict
import sqlite3
from pathlib import Path

from .base import Signal, Action, Outcome, Learning


class MessageBus:
    """Central message bus for subsystem communication.

    Supports two modes:
    - In-memory (default): For single-process operation
    - Redis: For distributed operation (requires redis server)
    """

    def __init__(self, mode: str = "memory", redis_url: str = None):
        self.mode = mode
        self.handlers: Dict[str, List[Callable]] = {}
        self.message_log: List[Dict] = []
        self.lock = threading.Lock()

        if mode == "redis" and redis_url:
            try:
                import redis
                self.redis = redis.from_url(redis_url)
                self.pubsub = self.redis.pubsub()
                self._start_redis_listener()
            except ImportError:
                print("Redis not available, falling back to in-memory mode")
                self.mode = "memory"
        else:
            self.mode = "memory"
            self._queue = queue.Queue()
            self._running = True
            self._start_memory_listener()

    def _start_memory_listener(self):
        """Start background thread for in-memory message processing."""
        def worker():
            while self._running:
                try:
                    msg = self._queue.get(timeout=0.1)
                    self._dispatch(msg["channel"], msg["data"])
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"Bus error: {e}")

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()

    def _start_redis_listener(self):
        """Start background thread for Redis pub/sub."""
        def worker():
            for message in self.pubsub.listen():
                if message['type'] == 'pmessage':
                    pattern = message['pattern'].decode()
                    data = json.loads(message['data'])
                    self._dispatch(pattern, data)

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()

    def _dispatch(self, channel: str, data: Dict):
        """Dispatch message to matching handlers."""
        with self.lock:
            # Log message
            self.message_log.append({
                "channel": channel,
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
            # Keep only last 1000 messages
            if len(self.message_log) > 1000:
                self.message_log = self.message_log[-1000:]

        # Find matching handlers
        for pattern, handlers in self.handlers.items():
            if self._matches(pattern, channel):
                for handler in handlers:
                    try:
                        handler(data)
                    except Exception as e:
                        print(f"Handler error on {channel}: {e}")

    def _matches(self, pattern: str, channel: str) -> bool:
        """Check if channel matches pattern (supports * wildcard)."""
        if pattern == channel:
            return True
        if pattern.endswith("*"):
            return channel.startswith(pattern[:-1])
        return False

    def publish(self, channel: str, message: Any):
        """Publish message to channel.

        Args:
            channel: Channel name (e.g., "signal.strategy", "action.task")
            message: Signal, Action, Outcome, or any serializable object
        """
        # Convert dataclass to dict if needed
        if hasattr(message, 'to_dict'):
            data = message.to_dict()
        elif hasattr(message, '__dict__'):
            data = asdict(message) if hasattr(message, '__dataclass_fields__') else message.__dict__
        else:
            data = message

        if self.mode == "redis":
            self.redis.publish(channel, json.dumps(data))
        else:
            self._queue.put({"channel": channel, "data": data})

    def subscribe(self, pattern: str, handler: Callable):
        """Subscribe to channel pattern.

        Args:
            pattern: Channel pattern (e.g., "signal.*" matches all signals)
            handler: Callback function receiving message data
        """
        with self.lock:
            if pattern not in self.handlers:
                self.handlers[pattern] = []
                if self.mode == "redis":
                    self.pubsub.psubscribe(pattern)
            self.handlers[pattern].append(handler)

    def unsubscribe(self, pattern: str, handler: Callable = None):
        """Unsubscribe from channel pattern.

        Args:
            pattern: Channel pattern to unsubscribe from
            handler: Specific handler to remove (if None, removes all)
        """
        with self.lock:
            if pattern in self.handlers:
                if handler:
                    self.handlers[pattern] = [h for h in self.handlers[pattern] if h != handler]
                else:
                    del self.handlers[pattern]
                    if self.mode == "redis":
                        self.pubsub.punsubscribe(pattern)

    def get_recent_messages(self, channel_filter: str = None, limit: int = 100) -> List[Dict]:
        """Get recent messages from log.

        Args:
            channel_filter: Optional pattern to filter channels
            limit: Maximum messages to return
        """
        with self.lock:
            if channel_filter:
                messages = [m for m in self.message_log if self._matches(channel_filter, m["channel"])]
            else:
                messages = self.message_log.copy()
            return messages[-limit:]

    def shutdown(self):
        """Gracefully shutdown the bus."""
        self._running = False
        if hasattr(self, '_thread'):
            self._thread.join(timeout=1.0)


class PersistentMessageBus(MessageBus):
    """Message bus with SQLite persistence for durability."""

    def __init__(self, db_path: Path = None, mode: str = "memory", redis_url: str = None):
        super().__init__(mode, redis_url)
        self.db_path = db_path or Path(__file__).parent.parent / "message_bus.db"
        self._init_db()

    def _init_db(self):
        """Initialize persistence database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS messages (
            message_id TEXT PRIMARY KEY,
            channel TEXT NOT NULL,
            data TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )''')

        c.execute('''CREATE INDEX IF NOT EXISTS idx_channel ON messages(channel)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp)''')

        conn.commit()
        conn.close()

    def publish(self, channel: str, message: Any):
        """Publish and persist message."""
        # Convert to dict
        if hasattr(message, 'to_dict'):
            data = message.to_dict()
        elif hasattr(message, '__dict__'):
            data = asdict(message) if hasattr(message, '__dataclass_fields__') else message.__dict__
        else:
            data = message

        # Persist
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        message_id = f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        c.execute('''INSERT INTO messages (message_id, channel, data, timestamp)
            VALUES (?, ?, ?, ?)''',
            (message_id, channel, json.dumps(data), datetime.now().isoformat()))

        conn.commit()
        conn.close()

        # Then publish normally
        super().publish(channel, message)

    def replay_messages(self, since: str = None, channel_filter: str = None) -> List[Dict]:
        """Replay messages from persistence.

        Args:
            since: ISO timestamp to replay from
            channel_filter: Optional channel pattern to filter
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        query = "SELECT channel, data, timestamp FROM messages"
        params = []

        conditions = []
        if since:
            conditions.append("timestamp > ?")
            params.append(since)
        if channel_filter:
            conditions.append("channel LIKE ?")
            params.append(channel_filter.replace("*", "%"))

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY timestamp ASC"

        c.execute(query, params)

        messages = []
        for row in c.fetchall():
            messages.append({
                "channel": row[0],
                "data": json.loads(row[1]),
                "timestamp": row[2]
            })

        conn.close()
        return messages


# Global bus instance
_global_bus: Optional[MessageBus] = None


def get_bus(persistent: bool = False) -> MessageBus:
    """Get or create global message bus instance."""
    global _global_bus
    if _global_bus is None:
        if persistent:
            _global_bus = PersistentMessageBus()
        else:
            _global_bus = MessageBus()
    return _global_bus


def publish(channel: str, message: Any):
    """Convenience function to publish to global bus."""
    get_bus().publish(channel, message)


def subscribe(pattern: str, handler: Callable):
    """Convenience function to subscribe on global bus."""
    get_bus().subscribe(pattern, handler)


# Standard channel prefixes
CHANNELS = {
    "signal": "signal.*",      # Observations, detections
    "action": "action.*",      # Requested operations
    "outcome": "outcome.*",    # Results
    "learning": "learning.*",  # Extracted patterns
    "alert": "alert.*",        # Urgent notifications
    "query": "query.*",        # Information requests
}
