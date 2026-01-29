#!/usr/bin/env python3
"""
HookBus - Standardized Hook Infrastructure

WIRED: 2026-01-29 - HookBus Foundation PHASE 1

Features:
- Correlation IDs (deterministic from session+tool+index)
- Guard wrapper (exception-safe, always pass-through)
- Bounded logging (200KB cap, optional compression)
- Idempotency/dedupe (SQLite + TTL)
- Metrics collection (duration, failures, payload size)

Environment Flags (all default safe):
- HOOKBUS_ENABLED=0          Enable HookBus processing
- HOOKBUS_MAX_BYTES=200000   Max payload size (200KB)
- HOOKBUS_COMPRESS=0         Enable zlib compression
- HOOKBUS_STORE_RAW=0        Store raw payloads
- HOOKBUS_DEDUPE_TTL=3600    Dedupe TTL seconds
- HOOKBUS_RETENTION_DAYS=7   Log retention days

Rollback: SET HOOKBUS_ENABLED=0 (or delete hook_bus.db)
"""

import hashlib
import json
import os
import sqlite3
import time
import zlib
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
import re
import threading

# Thread-local storage for call index tracking
_local = threading.local()

DAEMON_DIR = Path(__file__).parent
HOOKBUS_DB = DAEMON_DIR / "hook_bus.db"

# Feature flags with safe defaults (read at import time, can be overridden via env)
HOOKBUS_MAX_BYTES = int(os.environ.get("HOOKBUS_MAX_BYTES", "200000"))
HOOKBUS_COMPRESS = os.environ.get("HOOKBUS_COMPRESS", "0").lower() in ("1", "true", "yes")
HOOKBUS_STORE_RAW = os.environ.get("HOOKBUS_STORE_RAW", "0").lower() in ("1", "true", "yes")
HOOKBUS_DEDUPE_TTL = int(os.environ.get("HOOKBUS_DEDUPE_TTL", "3600"))
HOOKBUS_RETENTION_DAYS = int(os.environ.get("HOOKBUS_RETENTION_DAYS", "7"))


def is_enabled() -> bool:
    """Check if HookBus is enabled (reads env at runtime for testability)."""
    return os.environ.get("HOOKBUS_ENABLED", "0").lower() in ("1", "true", "yes")

# Secret patterns to redact
SECRET_PATTERNS = [
    (re.compile(r'(api[_-]?key|apikey)["\s:=]+["\']?([a-zA-Z0-9_\-]{20,})["\']?', re.I), r'\1=***REDACTED***'),
    (re.compile(r'(bearer\s+)([a-zA-Z0-9_\-\.]+)', re.I), r'\1***REDACTED***'),
    (re.compile(r'(authorization)["\s:=]+["\']?([^\s"\']{10,})["\']?', re.I), r'\1=***REDACTED***'),
    (re.compile(r'(password|passwd|secret|token)["\s:=]+["\']?([^\s"\']{6,})["\']?', re.I), r'\1=***REDACTED***'),
    (re.compile(r'(sk-[a-zA-Z0-9]{20,})', re.I), '***REDACTED_KEY***'),
    (re.compile(r'(ghp_[a-zA-Z0-9]{36,})', re.I), '***REDACTED_GH***'),
]


def _init_db():
    """Initialize HookBus database with WAL mode."""
    conn = sqlite3.connect(HOOKBUS_DB)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")

    conn.executescript("""
        -- Dedupe keys with TTL
        CREATE TABLE IF NOT EXISTS dedupe_keys (
            key TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_dedupe_expires ON dedupe_keys(expires_at);

        -- Hook execution logs (bounded)
        CREATE TABLE IF NOT EXISTS hook_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            correlation_id TEXT NOT NULL,
            hook_name TEXT NOT NULL,
            event_type TEXT NOT NULL,
            tool_name TEXT,
            status TEXT NOT NULL,
            duration_ms REAL,
            payload_bytes INTEGER,
            compressed INTEGER DEFAULT 0,
            payload TEXT,
            error TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_hook_logs_correlation ON hook_logs(correlation_id);
        CREATE INDEX IF NOT EXISTS idx_hook_logs_created ON hook_logs(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_hook_logs_hook ON hook_logs(hook_name);

        -- Metrics aggregates
        CREATE TABLE IF NOT EXISTS hook_metrics (
            metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
            hook_name TEXT NOT NULL,
            period TEXT NOT NULL,
            call_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            failure_count INTEGER DEFAULT 0,
            dedupe_hits INTEGER DEFAULT 0,
            total_duration_ms REAL DEFAULT 0,
            total_payload_bytes INTEGER DEFAULT 0,
            p50_duration_ms REAL,
            p95_duration_ms REAL,
            p99_duration_ms REAL,
            created_at TEXT NOT NULL,
            UNIQUE(hook_name, period)
        );
        CREATE INDEX IF NOT EXISTS idx_metrics_period ON hook_metrics(period DESC);
    """)
    conn.commit()
    conn.close()


# Initialize on import (safe - creates empty tables)
_init_db()


def _get_conn() -> sqlite3.Connection:
    """Get database connection with WAL mode."""
    conn = sqlite3.connect(HOOKBUS_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


# ==============================================================================
# Correlation ID Generation
# ==============================================================================

def get_call_index() -> int:
    """Get and increment thread-local call index."""
    if not hasattr(_local, 'call_index'):
        _local.call_index = 0
    idx = _local.call_index
    _local.call_index += 1
    return idx


def reset_call_index():
    """Reset call index (call at session start)."""
    _local.call_index = 0


def generate_correlation_id(
    session_id: str = None,
    tool_name: str = None,
    tool_call_index: int = None
) -> str:
    """
    Generate deterministic correlation ID.

    Format: 16-char hex hash of session:tool:index
    Collision-resistant via SHA256.
    """
    # Defaults for missing values
    session_id = session_id or os.environ.get("CLAUDE_SESSION_ID", "unknown")
    tool_name = tool_name or "unknown"
    if tool_call_index is None:
        tool_call_index = get_call_index()

    content = f"{session_id}:{tool_name}:{tool_call_index}"
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


# ==============================================================================
# Secret Redaction
# ==============================================================================

def redact_secrets(text: str) -> str:
    """Redact known secret patterns from text."""
    if not text:
        return text

    result = text
    for pattern, replacement in SECRET_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


# ==============================================================================
# Bounded Logging
# ==============================================================================

def bound_payload(payload: Any, max_bytes: int = None) -> Tuple[str, int, bool]:
    """
    Bound payload to max size with optional compression.

    Returns: (bounded_payload, original_bytes, was_truncated)
    """
    max_bytes = max_bytes or HOOKBUS_MAX_BYTES

    # Serialize to JSON
    if isinstance(payload, str):
        serialized = payload
    else:
        try:
            serialized = json.dumps(payload, default=str, ensure_ascii=False)
        except Exception:
            serialized = str(payload)

    # Redact secrets
    serialized = redact_secrets(serialized)

    original_bytes = len(serialized.encode('utf-8'))
    was_truncated = False

    # Check if compression helps
    if HOOKBUS_COMPRESS and original_bytes > max_bytes // 2:
        try:
            compressed = zlib.compress(serialized.encode('utf-8'), level=6)
            if len(compressed) < original_bytes:
                # Return base64-encoded compressed data
                import base64
                return f"COMPRESSED:{base64.b64encode(compressed).decode()}", original_bytes, False
        except Exception:
            pass

    # Truncate if needed
    if original_bytes > max_bytes:
        # Smart truncation - keep start and end
        keep_bytes = max_bytes - 50  # Reserve for truncation marker
        start_bytes = keep_bytes * 2 // 3
        end_bytes = keep_bytes // 3

        encoded = serialized.encode('utf-8')
        truncated = (
            encoded[:start_bytes].decode('utf-8', errors='ignore') +
            f"\n...TRUNCATED {original_bytes - keep_bytes} bytes...\n" +
            encoded[-end_bytes:].decode('utf-8', errors='ignore')
        )
        return truncated, original_bytes, True

    return serialized, original_bytes, False


def log_hook_execution(
    correlation_id: str,
    hook_name: str,
    event_type: str,
    tool_name: str = None,
    status: str = "success",
    duration_ms: float = None,
    payload: Any = None,
    error: str = None
):
    """Log hook execution with bounded payload."""
    if not is_enabled():
        return

    try:
        bounded_payload = None
        payload_bytes = 0
        compressed = 0

        if HOOKBUS_STORE_RAW and payload is not None:
            bounded_payload, payload_bytes, _ = bound_payload(payload)
            if bounded_payload.startswith("COMPRESSED:"):
                compressed = 1
        elif payload is not None:
            # Just track size, don't store
            if isinstance(payload, str):
                payload_bytes = len(payload.encode('utf-8'))
            else:
                try:
                    payload_bytes = len(json.dumps(payload, default=str).encode('utf-8'))
                except:
                    payload_bytes = 0

        conn = _get_conn()
        conn.execute("""
            INSERT INTO hook_logs
            (correlation_id, hook_name, event_type, tool_name, status, duration_ms,
             payload_bytes, compressed, payload, error, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            correlation_id,
            hook_name,
            event_type,
            tool_name,
            status,
            duration_ms,
            payload_bytes,
            compressed,
            bounded_payload,
            error,
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
    except Exception:
        # Never fail on logging
        pass


# ==============================================================================
# Idempotency / Dedupe
# ==============================================================================

def check_dedupe(key: str, ttl_seconds: int = None) -> bool:
    """
    Check if operation should be deduped.

    Returns True if key exists and not expired (skip operation).
    Returns False if key doesn't exist (proceed with operation).
    """
    if not is_enabled():
        return False

    ttl_seconds = ttl_seconds or HOOKBUS_DEDUPE_TTL

    try:
        conn = _get_conn()
        c = conn.cursor()

        now = datetime.now()

        # Clean expired keys
        c.execute("DELETE FROM dedupe_keys WHERE expires_at < ?", (now.isoformat(),))

        # Check if key exists
        c.execute("SELECT 1 FROM dedupe_keys WHERE key = ?", (key,))
        exists = c.fetchone() is not None

        if not exists:
            # Insert new key
            expires_at = now + timedelta(seconds=ttl_seconds)
            c.execute("""
                INSERT OR REPLACE INTO dedupe_keys (key, created_at, expires_at)
                VALUES (?, ?, ?)
            """, (key, now.isoformat(), expires_at.isoformat()))

        conn.commit()
        conn.close()
        return exists
    except Exception:
        return False  # On error, allow operation


def generate_dedupe_key(category: str, *identifiers) -> str:
    """
    Generate dedupe key for operation.

    Categories: task_inject, post_cache, learning_flush, tool_track
    """
    content = f"{category}:" + ":".join(str(i) for i in identifiers)
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:32]


# ==============================================================================
# Guard Wrapper (Exception-Safe)
# ==============================================================================

@dataclass
class HookResult:
    """Result from guarded hook execution."""
    success: bool
    output: Any = None
    error: str = None
    duration_ms: float = 0
    correlation_id: str = None


def guard(
    hook_name: str,
    event_type: str = "unknown",
    tool_name: str = None,
    dedupe_key: str = None
):
    """
    Decorator for exception-safe hook execution.

    Usage:
        @guard("my-hook", "PostToolUse", "Read")
        def my_hook_function(input_data):
            # Your hook logic
            return result

    Guarantees:
    - Never raises exceptions (returns HookResult with error)
    - Always logs execution (if HOOKBUS_ENABLED)
    - Respects dedupe keys
    - Tracks duration
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> HookResult:
            correlation_id = generate_correlation_id(tool_name=tool_name)
            start_time = time.perf_counter()

            # Check dedupe
            if dedupe_key and check_dedupe(dedupe_key):
                duration_ms = (time.perf_counter() - start_time) * 1000
                log_hook_execution(
                    correlation_id, hook_name, event_type, tool_name,
                    status="dedupe_skip", duration_ms=duration_ms
                )
                return HookResult(
                    success=True,
                    output=None,
                    correlation_id=correlation_id,
                    duration_ms=duration_ms
                )

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                log_hook_execution(
                    correlation_id, hook_name, event_type, tool_name,
                    status="success", duration_ms=duration_ms,
                    payload=result if HOOKBUS_STORE_RAW else None
                )

                return HookResult(
                    success=True,
                    output=result,
                    correlation_id=correlation_id,
                    duration_ms=duration_ms
                )
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                error_str = f"{type(e).__name__}: {str(e)}"

                log_hook_execution(
                    correlation_id, hook_name, event_type, tool_name,
                    status="error", duration_ms=duration_ms,
                    error=error_str
                )

                return HookResult(
                    success=False,
                    error=error_str,
                    correlation_id=correlation_id,
                    duration_ms=duration_ms
                )

        return wrapper
    return decorator


@contextmanager
def guarded_execution(
    hook_name: str,
    event_type: str = "unknown",
    tool_name: str = None,
    dedupe_key: str = None
):
    """
    Context manager for guarded execution.

    Usage:
        with guarded_execution("my-hook", "PostToolUse") as ctx:
            # Your hook logic
            ctx.set_output(result)
    """
    correlation_id = generate_correlation_id(tool_name=tool_name)
    start_time = time.perf_counter()

    class ExecutionContext:
        def __init__(self):
            self.output = None
            self.error = None
            self.skipped = False

        def set_output(self, value):
            self.output = value

    ctx = ExecutionContext()

    # Check dedupe
    if dedupe_key and check_dedupe(dedupe_key):
        ctx.skipped = True
        duration_ms = (time.perf_counter() - start_time) * 1000
        log_hook_execution(
            correlation_id, hook_name, event_type, tool_name,
            status="dedupe_skip", duration_ms=duration_ms
        )
        yield ctx
        return

    try:
        yield ctx
        duration_ms = (time.perf_counter() - start_time) * 1000
        log_hook_execution(
            correlation_id, hook_name, event_type, tool_name,
            status="success", duration_ms=duration_ms,
            payload=ctx.output if HOOKBUS_STORE_RAW else None
        )
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        ctx.error = f"{type(e).__name__}: {str(e)}"
        log_hook_execution(
            correlation_id, hook_name, event_type, tool_name,
            status="error", duration_ms=duration_ms,
            error=ctx.error
        )
        # Don't re-raise - pass through


# ==============================================================================
# Metrics
# ==============================================================================

def get_metrics(hook_name: str = None, hours: int = 24) -> Dict[str, Any]:
    """Get hook metrics for the last N hours."""
    try:
        conn = _get_conn()
        c = conn.cursor()

        since = (datetime.now() - timedelta(hours=hours)).isoformat()

        query = """
            SELECT
                hook_name,
                COUNT(*) as total_calls,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successes,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as failures,
                SUM(CASE WHEN status = 'dedupe_skip' THEN 1 ELSE 0 END) as dedupe_hits,
                AVG(duration_ms) as avg_duration_ms,
                SUM(payload_bytes) as total_bytes
            FROM hook_logs
            WHERE created_at > ?
        """
        params = [since]

        if hook_name:
            query += " AND hook_name = ?"
            params.append(hook_name)

        query += " GROUP BY hook_name"

        c.execute(query, params)

        metrics = {}
        for row in c.fetchall():
            metrics[row["hook_name"]] = {
                "total_calls": row["total_calls"],
                "successes": row["successes"],
                "failures": row["failures"],
                "dedupe_hits": row["dedupe_hits"],
                "avg_duration_ms": round(row["avg_duration_ms"] or 0, 2),
                "total_bytes": row["total_bytes"] or 0,
                "success_rate": round((row["successes"] / row["total_calls"]) * 100, 1) if row["total_calls"] > 0 else 0
            }

        # Get percentiles
        for name in metrics:
            c.execute("""
                SELECT duration_ms FROM hook_logs
                WHERE hook_name = ? AND created_at > ? AND duration_ms IS NOT NULL
                ORDER BY duration_ms
            """, (name, since))
            durations = [r[0] for r in c.fetchall()]

            if durations:
                n = len(durations)
                metrics[name]["p50_ms"] = round(durations[int(n * 0.5)] if n > 0 else 0, 2)
                metrics[name]["p95_ms"] = round(durations[int(n * 0.95)] if n > 0 else 0, 2)
                metrics[name]["p99_ms"] = round(durations[int(n * 0.99)] if n > 0 else 0, 2)

        conn.close()
        return metrics
    except Exception as e:
        return {"error": str(e)}


def cleanup_old_logs():
    """Remove logs older than retention period."""
    try:
        conn = _get_conn()
        cutoff = (datetime.now() - timedelta(days=HOOKBUS_RETENTION_DAYS)).isoformat()

        conn.execute("DELETE FROM hook_logs WHERE created_at < ?", (cutoff,))
        conn.execute("DELETE FROM dedupe_keys WHERE expires_at < ?", (datetime.now().isoformat(),))

        conn.commit()
        conn.close()
    except Exception:
        pass


# ==============================================================================
# CLI
# ==============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python hook_bus.py [status|metrics|cleanup|test]")
        print("  status   - Show HookBus configuration")
        print("  metrics  - Show hook metrics (last 24h)")
        print("  cleanup  - Remove old logs")
        print("  test     - Run self-test")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "status":
        print(f"HOOKBUS_ENABLED:      {is_enabled()}")
        print(f"HOOKBUS_MAX_BYTES:    {HOOKBUS_MAX_BYTES:,}")
        print(f"HOOKBUS_COMPRESS:     {HOOKBUS_COMPRESS}")
        print(f"HOOKBUS_STORE_RAW:    {HOOKBUS_STORE_RAW}")
        print(f"HOOKBUS_DEDUPE_TTL:   {HOOKBUS_DEDUPE_TTL}s")
        print(f"HOOKBUS_RETENTION:    {HOOKBUS_RETENTION_DAYS}d")
        print(f"Database:             {HOOKBUS_DB}")

    elif cmd == "metrics":
        hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
        metrics = get_metrics(hours=hours)
        print(json.dumps(metrics, indent=2))

    elif cmd == "cleanup":
        cleanup_old_logs()
        print("Cleanup complete")

    elif cmd == "test":
        # Self-test
        print("Running HookBus self-test...")

        # Force enable for test via env
        os.environ["HOOKBUS_ENABLED"] = "1"

        # Test correlation ID
        cid = generate_correlation_id("test-session", "TestTool", 0)
        assert len(cid) == 16, "Correlation ID should be 16 chars"
        print(f"  Correlation ID: {cid}")

        # Test secret redaction
        test_secret = 'api_key="sk-1234567890abcdefghij"'
        redacted = redact_secrets(test_secret)
        assert "sk-" not in redacted, "Secret should be redacted"
        print(f"  Redaction: OK")

        # Test bounded payload
        large = "x" * 300000
        bounded, orig, truncated = bound_payload(large)
        assert len(bounded) <= HOOKBUS_MAX_BYTES + 100, "Should be bounded"
        assert truncated, "Should be truncated"
        print(f"  Bounding: {orig} -> {len(bounded)} bytes")

        # Test dedupe
        key = generate_dedupe_key("test", "value1", "value2")
        first = check_dedupe(key, ttl_seconds=5)
        second = check_dedupe(key, ttl_seconds=5)
        assert not first, "First check should pass"
        assert second, "Second check should be deduped"
        print(f"  Dedupe: OK")

        # Test guard decorator
        @guard("test-hook", "Test", "TestTool")
        def test_func():
            return {"status": "ok"}

        result = test_func()
        assert result.success, "Guard should capture success"
        print(f"  Guard: OK (duration={result.duration_ms:.2f}ms)")

        # Test guarded context
        with guarded_execution("test-context", "Test") as ctx:
            ctx.set_output({"test": True})
        print(f"  Context Manager: OK")

        print("\nAll tests passed!")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
