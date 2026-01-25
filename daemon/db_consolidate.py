#!/usr/bin/env python3
"""
Database Consolidation - 23 SQLite → 4 SQLite (then → 1 PostgreSQL)

Phase 1: Consolidate related databases
Phase 2: Migrate to PostgreSQL (future)
"""

import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

DAEMON_DIR = Path(__file__).parent
BACKUP_DIR = DAEMON_DIR / "db_backup" / datetime.now().strftime("%Y%m%d_%H%M%S")

# Consolidation plan: 23 → 4
CONSOLIDATION = {
    "knowledge.db": [
        "books.db",
        "utf_knowledge.db",
        "openmemory.db",
        "synthesis.db",
        "ingest.db",
    ],
    "cognitive.db": [
        "coherence.db",
        "decisions.db",
        "metacognition.db",
        "self_improvement.db",
        "bisimulation.db",
        "gcrl.db",
        "memory.db",
    ],
    "operations.db": [
        "tasks.db",
        "generated_tasks.db",
        "scheduler.db",
        "approvals.db",
        "controller.db",
        "token_monitor.db",
        "outcomes.db",
        "strategies.db",
        "book_watcher.db",
    ],
    "routing.db": [
        "router.db",
    ],
}

# Keep separate (for now)
KEEP_SEPARATE = ["overseer.db"]


def backup_all():
    """Backup all databases before consolidation."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    for db_file in DAEMON_DIR.glob("*.db"):
        shutil.copy(db_file, BACKUP_DIR / db_file.name)
        print(f"  Backed up: {db_file.name}")

    print(f"\nBackups saved to: {BACKUP_DIR}")
    return BACKUP_DIR


def get_tables(db_path: Path) -> list:
    """Get all tables in a database."""
    if not db_path.exists():
        return []

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in c.fetchall()]
    conn.close()
    return tables


def consolidate(target_name: str, source_dbs: list, dry_run: bool = True):
    """Consolidate multiple databases into one."""
    target_path = DAEMON_DIR / target_name

    if dry_run:
        print(f"\n[DRY RUN] Would consolidate into {target_name}:")
        for src in source_dbs:
            src_path = DAEMON_DIR / src
            if src_path.exists():
                tables = get_tables(src_path)
                print(f"  {src}: {len(tables)} tables - {tables}")
        return

    # Create new consolidated database
    target_conn = sqlite3.connect(target_path)

    for src in source_dbs:
        src_path = DAEMON_DIR / src
        if not src_path.exists():
            continue

        # Get source schema and data
        src_conn = sqlite3.connect(src_path)
        src_cursor = src_conn.cursor()

        # Get all tables
        src_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in src_cursor.fetchall()]

        for table in tables:
            # Prefix table name with source db name to avoid conflicts
            prefix = src.replace(".db", "")
            new_table = f"{prefix}_{table}"

            # Get create statement
            src_cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
            create_sql = src_cursor.fetchone()[0]

            # Modify to new name
            create_sql = create_sql.replace(f"CREATE TABLE {table}", f"CREATE TABLE {new_table}", 1)

            # Create in target
            try:
                target_conn.execute(create_sql)
            except sqlite3.OperationalError:
                pass  # Table already exists

            # Copy data
            src_cursor.execute(f"SELECT * FROM {table}")
            rows = src_cursor.fetchall()

            if rows:
                placeholders = ",".join(["?" for _ in rows[0]])
                target_conn.executemany(f"INSERT OR IGNORE INTO {new_table} VALUES ({placeholders})", rows)

        src_conn.close()
        print(f"  Merged: {src} → {target_name}")

    target_conn.commit()
    target_conn.close()


def show_plan():
    """Show consolidation plan."""
    print("=" * 60)
    print("DATABASE CONSOLIDATION PLAN")
    print("=" * 60)
    print(f"\nCurrent: 23 SQLite databases")
    print(f"Target:  4 SQLite databases\n")

    total_source = 0
    for target, sources in CONSOLIDATION.items():
        print(f"\n{target}:")
        for src in sources:
            src_path = DAEMON_DIR / src
            if src_path.exists():
                tables = get_tables(src_path)
                size_kb = src_path.stat().st_size / 1024
                print(f"  ← {src} ({len(tables)} tables, {size_kb:.1f}KB)")
                total_source += 1
            else:
                print(f"  ← {src} (not found)")

    print(f"\n{len(KEEP_SEPARATE)} databases kept separate: {KEEP_SEPARATE}")
    print(f"\nTotal: {total_source} → 4 databases")


def run_consolidation(dry_run: bool = True):
    """Run the consolidation."""
    if not dry_run:
        print("\n⚠️  BACKING UP ALL DATABASES FIRST...")
        backup_all()

    for target, sources in CONSOLIDATION.items():
        consolidate(target, sources, dry_run=dry_run)

    if not dry_run:
        print("\n✓ Consolidation complete!")
        print("  Old databases preserved in backup folder.")
        print("  Update module imports to use new database names.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Database Consolidation")
    parser.add_argument("--plan", action="store_true", help="Show consolidation plan")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (show what would happen)")
    parser.add_argument("--execute", action="store_true", help="Actually run consolidation")

    args = parser.parse_args()

    if args.plan:
        show_plan()
    elif args.execute:
        run_consolidation(dry_run=False)
    else:
        run_consolidation(dry_run=True)
