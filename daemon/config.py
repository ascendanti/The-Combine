#!/usr/bin/env python3
"""
Central Configuration - Single source of truth for all paths and settings.

Replaces hard-coded paths scattered across modules with env-driven config.

WIRED: 2026-01-29 - PHASE 5 DevOps Defaults (WAL, logging, SAFE_MODE)

Usage:
    from config import cfg, get_db_connection, setup_logging, log

    # Paths
    db_path = cfg.DAEMON_DIR / "mydb.db"
    project = cfg.PROJECT_DIR

    # Database with WAL mode
    conn = get_db_connection(db_path)

    # Structured logging
    log.info("event_type", key="value")

    # Safe mode check
    if cfg.SAFE_MODE:
        # Throttled/cautious behavior
"""

import os
import sqlite3
import logging
import json
from pathlib import Path
from typing import Optional, Any, Dict
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Config:
    """Centralized configuration with environment variable support."""

    # Core directories
    DAEMON_DIR: Path = field(default_factory=lambda: Path(__file__).parent)
    PROJECT_DIR: Path = field(default_factory=lambda: Path(__file__).parent.parent)

    # Environment-driven overrides
    ATLAS_ROOT: Optional[Path] = None
    UTF_RESEARCH: Optional[Path] = None
    REFERENCE_FRAMEWORKS: Optional[Path] = None
    MALAZAN_DIR: Optional[Path] = None

    # Database paths (relative to DAEMON_DIR)
    DB_MEMORY: str = "memory.db"
    DB_TASKS: str = "tasks.db"
    DB_INGEST: str = "ingest.db"
    DB_UTF: str = "utf_knowledge.db"
    DB_ERRORS: str = "errors.db"
    DB_OUTCOMES: str = "outcomes.db"
    DB_STRATEGIES: str = "strategies.db"
    DB_TOOL_TRACKING: str = "tool_tracking.db"
    DB_ROUTER: str = "router.db"
    DB_CONTROLLER: str = "controller.db"
    DB_SYNTHESIS: str = "synthesis.db"
    DB_TOKEN_MONITOR: str = "token_monitor.db"
    DB_BOOKS: str = "books.db"

    # Service URLs
    LOCALAI_URL: str = "http://localhost:8080"
    DRAGONFLY_URL: str = "redis://localhost:6379"
    DAEMON_API_URL: str = "http://localhost:8765"

    # Clawdbot OAuth Gateway (via Tailscale Serve)
    CLAWDBOT_URL: str = "https://desktop-au69ba4.taileea598.ts.net"  # Tailscale Serve HTTPS
    CLAWDBOT_TAILSCALE_URL: str = "https://desktop-au69ba4.taileea598.ts.net"
    CLAWDBOT_TOKEN: str = "33e3f2b4dc0c7f142aa1e7c7ee5852ec73d9eba7f43e4d8a"
    USE_CLAWDBOT: bool = True  # Route OAuth-enabled requests through Clawdbot

    # Timeouts (seconds)
    LOCALAI_TIMEOUT: int = 30
    EMBEDDING_TIMEOUT: int = 60
    TASK_TIMEOUT: int = 600

    # Feature flags
    DEBUG: bool = False
    USE_LOCALAI: bool = True
    USE_DRAGONFLY_CACHE: bool = True
    ENABLE_TELEMETRY: bool = False

    # SAFE_MODE: Throttles/disables risky operations
    # Set SAFE_MODE=1 to enable cautious behavior:
    # - Lower task generation limits
    # - More aggressive deduplication
    # - Stricter budget caps
    # - Read-only mode for external APIs
    SAFE_MODE: bool = False
    SAFE_MODE_MAX_TASKS_PER_HOUR: int = 10  # vs 50 normal
    SAFE_MODE_MAX_CONCURRENT: int = 3  # vs 10 normal
    SAFE_MODE_TTL_MULTIPLIER: float = 2.0  # Double TTL in safe mode

    def __post_init__(self):
        """Load overrides from environment variables."""
        # Directory overrides
        if atlas := os.environ.get("ATLAS_ROOT"):
            self.ATLAS_ROOT = Path(atlas)

        if utf := os.environ.get("UTF_RESEARCH"):
            self.UTF_RESEARCH = Path(utf)

        if ref := os.environ.get("REFERENCE_FRAMEWORKS"):
            self.REFERENCE_FRAMEWORKS = Path(ref)

        if malazan := os.environ.get("MALAZAN_DIR"):
            self.MALAZAN_DIR = Path(malazan)

        if project := os.environ.get("CLAUDE_PROJECT_DIR"):
            self.PROJECT_DIR = Path(project)

        # Service URL overrides
        if localai := os.environ.get("LOCALAI_URL"):
            self.LOCALAI_URL = localai

        if dragonfly := os.environ.get("DRAGONFLY_URL"):
            self.DRAGONFLY_URL = dragonfly

        if daemon := os.environ.get("DAEMON_API_URL"):
            self.DAEMON_API_URL = daemon

        # Clawdbot OAuth Gateway overrides
        if clawdbot := os.environ.get("CLAWDBOT_URL"):
            self.CLAWDBOT_URL = clawdbot
        if clawdbot_ts := os.environ.get("CLAWDBOT_TAILSCALE_URL"):
            self.CLAWDBOT_TAILSCALE_URL = clawdbot_ts
        if clawdbot_token := os.environ.get("CLAWDBOT_TOKEN"):
            self.CLAWDBOT_TOKEN = clawdbot_token
        self.USE_CLAWDBOT = os.environ.get("USE_CLAWDBOT", "1").lower() not in (
            "0", "false", "no"
        )

        # Feature flags
        self.DEBUG = os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")
        self.USE_LOCALAI = os.environ.get("USE_LOCALAI", "1").lower() not in (
            "0",
            "false",
            "no",
        )
        self.USE_DRAGONFLY_CACHE = os.environ.get(
            "USE_DRAGONFLY_CACHE", "1"
        ).lower() not in ("0", "false", "no")

        # SAFE_MODE: Enable via SAFE_MODE=1 environment variable
        self.SAFE_MODE = os.environ.get("SAFE_MODE", "").lower() in ("1", "true", "yes")

    # Database path helpers
    def db_path(self, name: str) -> Path:
        """Get full path to a database file."""
        db_attr = f"DB_{name.upper()}"
        if hasattr(self, db_attr):
            return self.DAEMON_DIR / getattr(self, db_attr)
        return self.DAEMON_DIR / f"{name}.db"

    @property
    def memory_db(self) -> Path:
        return self.DAEMON_DIR / self.DB_MEMORY

    @property
    def tasks_db(self) -> Path:
        return self.DAEMON_DIR / self.DB_TASKS

    @property
    def ingest_db(self) -> Path:
        return self.DAEMON_DIR / self.DB_INGEST

    @property
    def utf_db(self) -> Path:
        return self.DAEMON_DIR / self.DB_UTF

    @property
    def errors_db(self) -> Path:
        return self.DAEMON_DIR / self.DB_ERRORS

    @property
    def outcomes_db(self) -> Path:
        return self.DAEMON_DIR / self.DB_OUTCOMES

    @property
    def strategies_db(self) -> Path:
        return self.DAEMON_DIR / self.DB_STRATEGIES

    # Directory helpers
    @property
    def hooks_dir(self) -> Path:
        return self.PROJECT_DIR / ".claude" / "hooks"

    @property
    def scripts_dir(self) -> Path:
        return self.PROJECT_DIR / ".claude" / "scripts"

    @property
    def agents_dir(self) -> Path:
        return self.PROJECT_DIR / ".claude" / "agents"

    @property
    def skills_dir(self) -> Path:
        return self.PROJECT_DIR / ".claude" / "skills"

    @property
    def handoffs_dir(self) -> Path:
        return self.PROJECT_DIR / "thoughts" / "handoffs"

    @property
    def cache_dir(self) -> Path:
        cache = self.PROJECT_DIR / ".claude" / "cache"
        cache.mkdir(parents=True, exist_ok=True)
        return cache

    # Status
    def status(self) -> dict:
        """Return current configuration status."""
        return {
            "project_dir": str(self.PROJECT_DIR),
            "daemon_dir": str(self.DAEMON_DIR),
            "atlas_root": str(self.ATLAS_ROOT) if self.ATLAS_ROOT else None,
            "localai_url": self.LOCALAI_URL,
            "debug": self.DEBUG,
            "use_localai": self.USE_LOCALAI,
            "use_dragonfly": self.USE_DRAGONFLY_CACHE,
        }


# Global singleton
cfg = Config()


# Legacy compatibility - export commonly used paths
DAEMON_DIR = cfg.DAEMON_DIR
PROJECT_DIR = cfg.PROJECT_DIR


# ==============================================================================
# PHASE 5: WAL Mode Database Connections
# ==============================================================================

def get_db_connection(db_path: Path, wal_mode: bool = True) -> sqlite3.Connection:
    """
    Get a database connection with WAL mode and busy timeout.

    WAL mode provides:
    - Concurrent reads and writes
    - Better crash recovery
    - Improved performance for high-write workloads

    Args:
        db_path: Path to SQLite database
        wal_mode: Whether to enable WAL mode (default True)

    Returns:
        sqlite3.Connection with row_factory set
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    if wal_mode:
        conn.execute("PRAGMA journal_mode=WAL")

    # 5 second busy timeout
    conn.execute("PRAGMA busy_timeout=5000")

    return conn


def ensure_wal_mode(db_path: Path) -> bool:
    """
    Ensure a database is in WAL mode.

    Returns True if WAL mode is now active.
    """
    try:
        conn = sqlite3.connect(db_path)
        result = conn.execute("PRAGMA journal_mode=WAL").fetchone()
        conn.close()
        return result[0].lower() == "wal"
    except Exception:
        return False


# ==============================================================================
# PHASE 5: Structured Logging
# ==============================================================================

class StructuredLogger:
    """
    Structured logger that outputs JSON lines for easy parsing.

    Usage:
        log.info("task_created", task_id="123", source="queue")
        log.error("connection_failed", service="localai", error="timeout")
    """

    def __init__(self, name: str = "daemon", level: int = logging.INFO):
        self.name = name
        self.level = level
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)

        # Only add handler if none exists
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)

    def _log(self, level: str, event: str, **kwargs):
        """Internal logging method."""
        record = {
            "ts": datetime.now().isoformat(),
            "level": level,
            "event": event,
            "module": self.name,
            **kwargs
        }

        # Add safe_mode flag if active
        if cfg.SAFE_MODE:
            record["safe_mode"] = True

        msg = json.dumps(record)

        if level == "error":
            self._logger.error(msg)
        elif level == "warn":
            self._logger.warning(msg)
        elif level == "debug":
            self._logger.debug(msg)
        else:
            self._logger.info(msg)

    def info(self, event: str, **kwargs):
        """Log info level event."""
        self._log("info", event, **kwargs)

    def error(self, event: str, **kwargs):
        """Log error level event."""
        self._log("error", event, **kwargs)

    def warn(self, event: str, **kwargs):
        """Log warning level event."""
        self._log("warn", event, **kwargs)

    def debug(self, event: str, **kwargs):
        """Log debug level event."""
        if cfg.DEBUG:
            self._log("debug", event, **kwargs)


def setup_logging(name: str = "daemon") -> StructuredLogger:
    """
    Setup structured logging for a module.

    Args:
        name: Module name for log attribution

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name, logging.DEBUG if cfg.DEBUG else logging.INFO)


# Default logger instance
log = setup_logging("daemon")


# ==============================================================================
# PHASE 5: SAFE_MODE Helpers
# ==============================================================================

def get_safe_config() -> Dict[str, Any]:
    """
    Get configuration values adjusted for SAFE_MODE.

    Returns dict with adjusted limits if SAFE_MODE is active.
    """
    if cfg.SAFE_MODE:
        return {
            "max_tasks_per_hour": cfg.SAFE_MODE_MAX_TASKS_PER_HOUR,
            "max_concurrent": cfg.SAFE_MODE_MAX_CONCURRENT,
            "ttl_multiplier": cfg.SAFE_MODE_TTL_MULTIPLIER,
            "safe_mode": True
        }
    else:
        return {
            "max_tasks_per_hour": 50,
            "max_concurrent": 10,
            "ttl_multiplier": 1.0,
            "safe_mode": False
        }


if __name__ == "__main__":
    print(json.dumps(cfg.status(), indent=2))
    print("\nSafe config:", json.dumps(get_safe_config(), indent=2))
    log.info("config_loaded", debug=cfg.DEBUG, safe_mode=cfg.SAFE_MODE)
