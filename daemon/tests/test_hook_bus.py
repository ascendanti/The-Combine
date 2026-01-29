#!/usr/bin/env python3
"""
Unit tests for HookBus - PHASE 3

Run: python -m pytest daemon/tests/test_hook_bus.py -v
"""

import os
import sys
import time
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

# Add daemon to path
DAEMON_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(DAEMON_DIR))

import pytest

# Force enable HookBus for tests
os.environ["HOOKBUS_ENABLED"] = "1"
os.environ["HOOKBUS_STORE_RAW"] = "1"

from hook_bus import (
    generate_correlation_id,
    redact_secrets,
    bound_payload,
    check_dedupe,
    generate_dedupe_key,
    guard,
    guarded_execution,
    log_hook_execution,
    get_metrics,
    cleanup_old_logs,
    reset_call_index,
    is_enabled,
    HOOKBUS_MAX_BYTES,
    HOOKBUS_DB,
)


class TestCorrelationId:
    """Tests for correlation ID generation."""

    def test_deterministic(self):
        """Same inputs produce same ID."""
        id1 = generate_correlation_id("session1", "Read", 0)
        id2 = generate_correlation_id("session1", "Read", 0)
        assert id1 == id2

    def test_different_sessions(self):
        """Different sessions produce different IDs."""
        id1 = generate_correlation_id("session1", "Read", 0)
        id2 = generate_correlation_id("session2", "Read", 0)
        assert id1 != id2

    def test_different_tools(self):
        """Different tools produce different IDs."""
        id1 = generate_correlation_id("session1", "Read", 0)
        id2 = generate_correlation_id("session1", "Write", 0)
        assert id1 != id2

    def test_different_indices(self):
        """Different indices produce different IDs."""
        id1 = generate_correlation_id("session1", "Read", 0)
        id2 = generate_correlation_id("session1", "Read", 1)
        assert id1 != id2

    def test_length(self):
        """Correlation ID is 16 characters."""
        cid = generate_correlation_id("test", "Read", 0)
        assert len(cid) == 16

    def test_hex_only(self):
        """Correlation ID contains only hex characters."""
        cid = generate_correlation_id("test", "Read", 0)
        assert all(c in "0123456789abcdef" for c in cid)

    def test_auto_index(self):
        """Auto-incrementing index works."""
        reset_call_index()
        id1 = generate_correlation_id("session1", "Read")
        id2 = generate_correlation_id("session1", "Read")
        assert id1 != id2


class TestSecretRedaction:
    """Tests for secret redaction."""

    def test_api_key(self):
        """API keys are redacted."""
        text = 'api_key="sk-1234567890abcdefghij"'
        redacted = redact_secrets(text)
        assert "sk-" not in redacted
        assert "REDACTED" in redacted

    def test_bearer_token(self):
        """Bearer tokens are redacted."""
        text = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        redacted = redact_secrets(text)
        assert "eyJ" not in redacted
        assert "REDACTED" in redacted

    def test_password(self):
        """Passwords are redacted."""
        text = 'password="supersecret123"'
        redacted = redact_secrets(text)
        assert "supersecret" not in redacted
        assert "REDACTED" in redacted

    def test_github_token(self):
        """GitHub tokens are redacted."""
        text = "ghp_1234567890123456789012345678901234567890"
        redacted = redact_secrets(text)
        assert "ghp_" not in redacted

    def test_safe_text_unchanged(self):
        """Non-secret text is unchanged."""
        text = "This is normal text with no secrets"
        redacted = redact_secrets(text)
        assert redacted == text

    def test_none_input(self):
        """None input returns None."""
        assert redact_secrets(None) is None

    def test_empty_string(self):
        """Empty string returns empty string."""
        assert redact_secrets("") == ""


class TestBoundPayload:
    """Tests for payload bounding."""

    def test_small_payload_unchanged(self):
        """Small payloads are not truncated."""
        payload = {"key": "value"}
        bounded, orig, truncated = bound_payload(payload)
        assert not truncated
        assert "value" in bounded

    def test_large_payload_truncated(self):
        """Large payloads are truncated."""
        payload = "x" * 300000
        bounded, orig, truncated = bound_payload(payload)
        assert truncated
        assert len(bounded) <= HOOKBUS_MAX_BYTES + 100
        assert "TRUNCATED" in bounded

    def test_preserves_start_and_end(self):
        """Truncation preserves start and end of content."""
        payload = "START" + "x" * 300000 + "END"
        bounded, orig, truncated = bound_payload(payload)
        assert bounded.startswith("START")
        assert bounded.endswith("END")

    def test_reports_original_size(self):
        """Reports original size correctly."""
        payload = "x" * 100
        bounded, orig, truncated = bound_payload(payload)
        assert orig == 100

    def test_string_input(self):
        """String inputs work."""
        payload = "test string"
        bounded, orig, truncated = bound_payload(payload)
        assert bounded == "test string"

    def test_dict_input(self):
        """Dict inputs are JSON serialized."""
        payload = {"key": "value"}
        bounded, orig, truncated = bound_payload(payload)
        assert "key" in bounded
        assert "value" in bounded

    def test_secrets_redacted(self):
        """Secrets in payload are redacted."""
        payload = {"api_key": "sk-1234567890abcdefghij"}
        bounded, orig, truncated = bound_payload(payload)
        assert "sk-" not in bounded


class TestDedupe:
    """Tests for idempotency/dedupe."""

    def test_first_check_passes(self):
        """First check for a key passes."""
        key = generate_dedupe_key("test", time.time(), "unique1")
        result = check_dedupe(key, ttl_seconds=5)
        assert not result  # First check should NOT be deduped

    def test_second_check_blocked(self):
        """Second check for same key is blocked."""
        key = generate_dedupe_key("test", time.time(), "unique2")
        first = check_dedupe(key, ttl_seconds=5)
        second = check_dedupe(key, ttl_seconds=5)
        assert not first
        assert second  # Second check SHOULD be deduped

    def test_different_keys_both_pass(self):
        """Different keys both pass."""
        key1 = generate_dedupe_key("test", time.time(), "a")
        key2 = generate_dedupe_key("test", time.time(), "b")
        result1 = check_dedupe(key1)
        result2 = check_dedupe(key2)
        assert not result1
        assert not result2

    def test_key_generation_deterministic(self):
        """Same inputs produce same dedupe key."""
        key1 = generate_dedupe_key("task_inject", "prompt", "source")
        key2 = generate_dedupe_key("task_inject", "prompt", "source")
        assert key1 == key2

    def test_key_length(self):
        """Dedupe key is 32 characters."""
        key = generate_dedupe_key("test", "value")
        assert len(key) == 32


class TestGuardDecorator:
    """Tests for guard decorator."""

    def test_success_captured(self):
        """Successful execution is captured."""
        @guard("test-hook", "Test", "TestTool")
        def success_func():
            return {"status": "ok"}

        result = success_func()
        assert result.success
        assert result.output == {"status": "ok"}
        assert result.error is None
        assert result.correlation_id is not None

    def test_error_captured(self):
        """Errors are captured, not raised."""
        @guard("test-hook", "Test", "TestTool")
        def error_func():
            raise ValueError("test error")

        result = error_func()
        assert not result.success
        assert result.output is None
        assert "ValueError" in result.error
        assert "test error" in result.error

    def test_duration_tracked(self):
        """Duration is tracked."""
        @guard("test-hook", "Test")
        def slow_func():
            time.sleep(0.01)
            return True

        result = slow_func()
        assert result.duration_ms >= 10

    def test_dedupe_key_works(self):
        """Dedupe key prevents duplicate execution."""
        execution_count = 0
        dedupe_key = generate_dedupe_key("guard_test", time.time())

        @guard("test-hook", "Test", dedupe_key=dedupe_key)
        def counted_func():
            nonlocal execution_count
            execution_count += 1
            return True

        result1 = counted_func()
        result2 = counted_func()

        assert result1.success
        assert result2.success
        assert execution_count == 1  # Only executed once


class TestGuardedContext:
    """Tests for guarded execution context manager."""

    def test_success(self):
        """Successful execution works."""
        with guarded_execution("test-ctx", "Test") as ctx:
            ctx.set_output({"result": 42})

        assert ctx.output == {"result": 42}
        assert ctx.error is None

    def test_error_caught(self):
        """Errors are caught, not raised."""
        with guarded_execution("test-ctx", "Test") as ctx:
            raise ValueError("context error")

        assert "ValueError" in ctx.error

    def test_dedupe_skips(self):
        """Dedupe key signals skip (caller must check ctx.skipped)."""
        dedupe_key = generate_dedupe_key("ctx_test", time.time())

        executed = []

        with guarded_execution("test-ctx", "Test", dedupe_key=dedupe_key) as ctx1:
            if not ctx1.skipped:
                executed.append(1)

        with guarded_execution("test-ctx", "Test", dedupe_key=dedupe_key) as ctx2:
            if not ctx2.skipped:
                executed.append(2)

        assert executed == [1]  # Second execution skipped
        assert ctx2.skipped


class TestMetrics:
    """Tests for metrics collection."""

    def test_metrics_structure(self):
        """Metrics have expected structure."""
        # Log some test executions
        log_hook_execution(
            "test-cid", "metrics-test", "Test", "Tool",
            status="success", duration_ms=5.0
        )

        metrics = get_metrics(hook_name="metrics-test", hours=1)

        if "metrics-test" in metrics:
            m = metrics["metrics-test"]
            assert "total_calls" in m
            assert "successes" in m
            assert "failures" in m
            assert "avg_duration_ms" in m


class TestCleanup:
    """Tests for log cleanup."""

    def test_cleanup_runs(self):
        """Cleanup doesn't error."""
        cleanup_old_logs()  # Should not raise


class TestFeatureFlags:
    """Tests for feature flag behavior."""

    def test_is_enabled(self):
        """is_enabled reads environment."""
        os.environ["HOOKBUS_ENABLED"] = "1"
        assert is_enabled()

        os.environ["HOOKBUS_ENABLED"] = "0"
        assert not is_enabled()

        # Restore for other tests
        os.environ["HOOKBUS_ENABLED"] = "1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
