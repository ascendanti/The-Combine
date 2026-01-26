#!/usr/bin/env python3
"""
Central Configuration - Single source of truth for all paths and settings.

Replaces hard-coded paths scattered across modules with env-driven config.

Usage:
    from config import cfg

    # Paths
    db_path = cfg.DAEMON_DIR / "mydb.db"
    project = cfg.PROJECT_DIR

    # Settings
    if cfg.DEBUG:
        print("Debug mode")
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


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

    # Timeouts (seconds)
    LOCALAI_TIMEOUT: int = 30
    EMBEDDING_TIMEOUT: int = 60
    TASK_TIMEOUT: int = 600

    # Feature flags
    DEBUG: bool = False
    USE_LOCALAI: bool = True
    USE_DRAGONFLY_CACHE: bool = True
    ENABLE_TELEMETRY: bool = False

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

        # Feature flags
        self.DEBUG = os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")
        self.USE_LOCALAI = os.environ.get("USE_LOCALAI", "1").lower() not in ("0", "false", "no")
        self.USE_DRAGONFLY_CACHE = os.environ.get("USE_DRAGONFLY_CACHE", "1").lower() not in ("0", "false", "no")

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


if __name__ == "__main__":
    import json
    print(json.dumps(cfg.status(), indent=2))
