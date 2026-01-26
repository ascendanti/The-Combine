#!/usr/bin/env python3
"""
Schema Migrations - Versioned database schema management.

Replaces ad-hoc CREATE TABLE IF NOT EXISTS with proper migrations.
Tracks schema version and applies incremental changes.

Usage:
    from schema_migrations import ensure_schema

    conn = sqlite3.connect("mydb.db")
    ensure_schema(conn, "utf_knowledge", UTF_MIGRATIONS)
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Callable, Optional

DAEMON_DIR = Path(__file__).parent

# Migration format: (version, description, sql_or_callable)
Migration = Tuple[int, str, str | Callable[[sqlite3.Connection], None]]


def init_migrations_table(conn: sqlite3.Connection) -> None:
    """Create migrations tracking table if not exists."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _schema_migrations (
            db_name TEXT,
            version INTEGER,
            description TEXT,
            applied_at TEXT,
            PRIMARY KEY (db_name, version)
        )
    """)
    conn.commit()


def get_current_version(conn: sqlite3.Connection, db_name: str) -> int:
    """Get current schema version for a database."""
    try:
        cursor = conn.execute(
            "SELECT MAX(version) FROM _schema_migrations WHERE db_name = ?",
            (db_name,)
        )
        result = cursor.fetchone()[0]
        return result if result is not None else 0
    except sqlite3.OperationalError:
        return 0


def apply_migration(
    conn: sqlite3.Connection,
    db_name: str,
    version: int,
    description: str,
    migration: str | Callable
) -> bool:
    """Apply a single migration."""
    try:
        if callable(migration):
            migration(conn)
        else:
            conn.executescript(migration)

        conn.execute("""
            INSERT INTO _schema_migrations (db_name, version, description, applied_at)
            VALUES (?, ?, ?, ?)
        """, (db_name, version, description, datetime.now().isoformat()))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"[schema] Migration {version} failed: {e}")
        return False


def ensure_schema(
    conn: sqlite3.Connection,
    db_name: str,
    migrations: List[Migration],
    verbose: bool = False
) -> int:
    """
    Ensure database schema is up to date.

    Args:
        conn: SQLite connection
        db_name: Logical database name for tracking
        migrations: List of (version, description, sql_or_callable)
        verbose: Print migration progress

    Returns:
        Number of migrations applied
    """
    init_migrations_table(conn)
    current = get_current_version(conn, db_name)
    applied = 0

    for version, description, migration in sorted(migrations, key=lambda m: m[0]):
        if version > current:
            if verbose:
                print(f"[schema] Applying {db_name} v{version}: {description}")
            if apply_migration(conn, db_name, version, description, migration):
                applied += 1
            else:
                break  # Stop on failure

    return applied


# ============================================================================
# UTF Knowledge Database Migrations
# ============================================================================

UTF_MIGRATIONS: List[Migration] = [
    (1, "Initial schema", """
        CREATE TABLE IF NOT EXISTS enhanced_facts (
            fact_id TEXT PRIMARY KEY,
            source_doc TEXT,
            original_content TEXT,
            claim_form TEXT,
            confidence REAL,
            stability_class TEXT,
            domain TEXT,
            dkcs_coordinates TEXT,
            enhanced_at TEXT
        );

        CREATE TABLE IF NOT EXISTS concept_scaffolds (
            concept_id TEXT PRIMARY KEY,
            name TEXT,
            domain TEXT,
            definition_1liner TEXT,
            scaffold_what TEXT,
            scaffold_how TEXT,
            scaffold_when_scope TEXT,
            scaffold_why_stakes TEXT,
            scaffold_how_to_use TEXT,
            scaffold_boundary_conditions TEXT,
            scaffold_failure_modes TEXT,
            completeness INTEGER,
            last_updated TEXT
        );

        CREATE TABLE IF NOT EXISTS assumptions (
            assumption_id TEXT PRIMARY KEY,
            source_doc TEXT,
            statement TEXT,
            assumption_type TEXT,
            violations TEXT,
            dependent_facts TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS limitations (
            limitation_id TEXT PRIMARY KEY,
            source_doc TEXT,
            statement TEXT,
            severity TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS enhancement_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_id TEXT,
            enhancement_type TEXT,
            status TEXT,
            created_at TEXT,
            completed_at TEXT
        );
    """),

    (2, "Add indexes for performance", """
        CREATE INDEX IF NOT EXISTS idx_facts_domain ON enhanced_facts(domain);
        CREATE INDEX IF NOT EXISTS idx_facts_stability ON enhanced_facts(stability_class);
        CREATE INDEX IF NOT EXISTS idx_concepts_domain ON concept_scaffolds(domain);
        CREATE INDEX IF NOT EXISTS idx_queue_status ON enhancement_queue(status);
    """),

    (3, "Add source tracking", """
        ALTER TABLE enhanced_facts ADD COLUMN source_type TEXT DEFAULT 'unknown';
        ALTER TABLE enhanced_facts ADD COLUMN extraction_method TEXT;
    """),
]


# ============================================================================
# HiRAG Database Migrations
# ============================================================================

HIRAG_MIGRATIONS: List[Migration] = [
    (1, "Initial HiRAG schema", """
        CREATE TABLE IF NOT EXISTS sources (
            id TEXT PRIMARY KEY,
            path TEXT,
            filename TEXT,
            file_type TEXT,
            file_size INTEGER,
            content_hash TEXT,
            indexed_at TEXT,
            chunk_count INTEGER DEFAULT 0,
            extraction_method TEXT
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY,
            source_id TEXT REFERENCES sources(id),
            chunk_index INTEGER,
            content TEXT,
            embedding BLOB,
            metadata TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS claims (
            id TEXT PRIMARY KEY,
            source_id TEXT REFERENCES sources(id),
            content TEXT,
            claim_type TEXT,
            confidence REAL,
            stability_class TEXT,
            embedding BLOB,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS concepts (
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE,
            definition TEXT,
            domain TEXT,
            source_ids TEXT,
            created_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_id);
        CREATE INDEX IF NOT EXISTS idx_claims_source ON claims(source_id);
    """),

    (2, "Add FTS for text search", """
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            content,
            content='chunks',
            content_rowid='rowid'
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS claims_fts USING fts5(
            content,
            content='claims',
            content_rowid='rowid'
        );
    """),
]


# ============================================================================
# Tool Tracking Database Migrations
# ============================================================================

TOOL_TRACKING_MIGRATIONS: List[Migration] = [
    (1, "Initial tracking schema", """
        CREATE TABLE IF NOT EXISTS tool_uses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            tool_name TEXT,
            file_path TEXT,
            input_size INTEGER,
            output_size INTEGER,
            duration_ms INTEGER,
            cached INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS cache_hits (
            path TEXT PRIMARY KEY,
            hit_count INTEGER DEFAULT 0,
            last_hit TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_tool_uses_tool ON tool_uses(tool_name);
        CREATE INDEX IF NOT EXISTS idx_tool_uses_time ON tool_uses(timestamp);
    """),

    (2, "Add session tracking", """
        ALTER TABLE tool_uses ADD COLUMN session_id TEXT;
        CREATE INDEX IF NOT EXISTS idx_tool_uses_session ON tool_uses(session_id);
    """),
]


# ============================================================================
# Error Tracking Database Migrations
# ============================================================================

ERROR_TRACKING_MIGRATIONS: List[Migration] = [
    (1, "Initial error schema", """
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
    """),
]


# ============================================================================
# Convenience Functions
# ============================================================================

def migrate_all_databases(verbose: bool = True) -> dict:
    """Run migrations on all known databases."""
    results = {}

    databases = [
        (DAEMON_DIR / "utf_knowledge.db", "utf_knowledge", UTF_MIGRATIONS),
        (DAEMON_DIR / "ingest.db", "hirag", HIRAG_MIGRATIONS),
        (DAEMON_DIR / "tool_tracking.db", "tool_tracking", TOOL_TRACKING_MIGRATIONS),
        (DAEMON_DIR / "errors.db", "errors", ERROR_TRACKING_MIGRATIONS),
    ]

    for db_path, db_name, migrations in databases:
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            applied = ensure_schema(conn, db_name, migrations, verbose)
            conn.close()
            results[db_name] = applied
            if verbose and applied > 0:
                print(f"[schema] {db_name}: {applied} migrations applied")

    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "migrate":
        results = migrate_all_databases(verbose=True)
        total = sum(results.values())
        print(f"\nTotal migrations applied: {total}")
    else:
        print("Usage: python schema_migrations.py migrate")
        print("\nAvailable migrations:")
        print(f"  UTF: {len(UTF_MIGRATIONS)} versions")
        print(f"  HiRAG: {len(HIRAG_MIGRATIONS)} versions")
        print(f"  Tool Tracking: {len(TOOL_TRACKING_MIGRATIONS)} versions")
        print(f"  Errors: {len(ERROR_TRACKING_MIGRATIONS)} versions")
