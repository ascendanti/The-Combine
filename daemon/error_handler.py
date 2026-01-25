#!/usr/bin/env python3
"""
Unified Error Handler - Consistent error handling across daemon modules.

Replaces ad-hoc try/except pass patterns with proper logging and tracking.

Usage:
    from error_handler import safe_execute, log_error, ErrorTracker

    # Decorator for functions
    @safe_execute
    def my_function():
        ...

    # Context manager
    with ErrorTracker("module_name", "operation") as tracker:
        result = risky_operation()
        tracker.set_result(result)

    # Manual logging
    try:
        risky_operation()
    except Exception as e:
        log_error("module", "operation", e)
"""

import sqlite3
import logging
import functools
import traceback
from pathlib import Path
from datetime import datetime
from typing import Optional, Any, Callable
from contextlib import contextmanager

DAEMON_DIR = Path(__file__).parent
ERROR_DB = DAEMON_DIR / "errors.db"

# Configure module logger
logger = logging.getLogger("daemon")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def init_db():
    """Initialize error tracking database."""
    conn = sqlite3.connect(ERROR_DB)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            module TEXT,
            operation TEXT,
            error_type TEXT,
            error_message TEXT,
            traceback TEXT,
            context TEXT,
            resolved INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS error_stats (
            module TEXT,
            operation TEXT,
            count INTEGER DEFAULT 0,
            last_error TEXT,
            PRIMARY KEY (module, operation)
        );

        CREATE INDEX IF NOT EXISTS idx_errors_module ON errors(module);
        CREATE INDEX IF NOT EXISTS idx_errors_timestamp ON errors(timestamp);
    """)
    conn.commit()
    conn.close()

init_db()

def log_error(module: str, operation: str, error: Exception,
              context: Optional[str] = None, reraise: bool = False) -> None:
    """
    Log error to database and logger.

    Args:
        module: Module name (e.g., 'orchestrator', 'memory')
        operation: Operation that failed (e.g., 'process_task', 'search')
        error: The exception that was raised
        context: Optional context string
        reraise: If True, re-raise the exception after logging
    """
    error_type = type(error).__name__
    error_msg = str(error)
    tb = traceback.format_exc()

    # Log to stderr
    logger.error(f"[{module}:{operation}] {error_type}: {error_msg}")

    # Store in database
    try:
        conn = sqlite3.connect(ERROR_DB)
        conn.execute("""
            INSERT INTO errors (timestamp, module, operation, error_type,
                              error_message, traceback, context)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), module, operation, error_type,
              error_msg, tb, context))

        # Update stats
        conn.execute("""
            INSERT INTO error_stats (module, operation, count, last_error)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(module, operation) DO UPDATE SET
                count = count + 1,
                last_error = excluded.last_error
        """, (module, operation, datetime.now().isoformat()))

        conn.commit()
        conn.close()
    except Exception as db_error:
        logger.warning(f"Failed to log error to DB: {db_error}")

    if reraise:
        raise error

def safe_execute(module: str = "unknown", operation: str = "unknown",
                 default: Any = None, reraise: bool = False):
    """
    Decorator for safe execution with error logging.

    Usage:
        @safe_execute("memory", "search")
        def search_memory(query):
            ...

        @safe_execute("memory", "search", default=[], reraise=True)
        def search_memory(query):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_error(module, operation or func.__name__, e, reraise=reraise)
                return default
        return wrapper
    return decorator

@contextmanager
def ErrorTracker(module: str, operation: str, default: Any = None,
                 reraise: bool = False, context: str = None):
    """
    Context manager for error tracking.

    Usage:
        with ErrorTracker("orchestrator", "process") as tracker:
            result = risky_operation()
            tracker.set_result(result)

        # Access result outside context
        final = tracker.result
    """
    class TrackerState:
        def __init__(self):
            self.result = default
            self.error = None
            self.success = False

        def set_result(self, value):
            self.result = value
            self.success = True

    state = TrackerState()

    try:
        yield state
        state.success = True
    except Exception as e:
        state.error = e
        log_error(module, operation, e, context=context, reraise=reraise)

def get_error_stats() -> dict:
    """Get error statistics by module."""
    conn = sqlite3.connect(ERROR_DB)

    # Stats by module
    cursor = conn.execute("""
        SELECT module, SUM(count), MAX(last_error)
        FROM error_stats GROUP BY module
    """)
    by_module = {row[0]: {"count": row[1], "last": row[2]} for row in cursor.fetchall()}

    # Recent errors
    cursor = conn.execute("""
        SELECT timestamp, module, operation, error_type, error_message
        FROM errors ORDER BY id DESC LIMIT 20
    """)
    recent = [
        {"time": r[0], "module": r[1], "op": r[2], "type": r[3], "msg": r[4][:100]}
        for r in cursor.fetchall()
    ]

    # Total counts
    cursor = conn.execute("SELECT COUNT(*), COUNT(DISTINCT module) FROM errors")
    row = cursor.fetchone()
    total = {"errors": row[0], "modules": row[1]}

    conn.close()

    return {
        "total": total,
        "by_module": by_module,
        "recent": recent
    }

def get_frequent_errors(limit: int = 10) -> list:
    """Get most frequent error patterns."""
    conn = sqlite3.connect(ERROR_DB)
    cursor = conn.execute("""
        SELECT module, operation, error_type, COUNT(*) as freq
        FROM errors
        WHERE timestamp > datetime('now', '-7 days')
        GROUP BY module, operation, error_type
        ORDER BY freq DESC
        LIMIT ?
    """, (limit,))
    results = [
        {"module": r[0], "operation": r[1], "error": r[2], "count": r[3]}
        for r in cursor.fetchall()
    ]
    conn.close()
    return results

if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "stats":
            print(json.dumps(get_error_stats(), indent=2))
        elif cmd == "frequent":
            print(json.dumps(get_frequent_errors(), indent=2))
    else:
        print("Usage: python error_handler.py [stats|frequent]")
