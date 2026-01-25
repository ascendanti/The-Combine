#!/usr/bin/env python3
"""
Manifest-Based Pack System - Phase 1

Deterministic pack syncing alongside existing PDF flow.
Uses manifest.json to track pack contents and versions.

Structure:
    /Atlas/                     # Existing root (kept for compatibility)
    /Atlas/Packs/               # New: Pack storage
        Canon/                  # Core knowledge packs
            manifest.json       # Pack metadata + file list
            *.pdf, *.md, etc.
        Toolbox/                # Tools and utilities
            manifest.json
        Research/               # Research papers
            manifest.json

Local cache:
    ~/.atlas/packs/            # Local pack cache
        Canon/
        Toolbox/
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import sqlite3

# Paths
LOCAL_PACK_CACHE = Path.home() / ".atlas" / "packs"
MANIFEST_DB = Path(__file__).parent.parent / "manifests.db"

# Drive structure (using /Atlas for compatibility)
DRIVE_PACKS_ROOT = "Packs"


@dataclass
class PackFile:
    """A file within a pack."""
    name: str
    drive_id: str
    size: int
    md5: str
    modified: str
    local_path: Optional[str] = None


@dataclass
class PackManifest:
    """Manifest for a pack."""
    pack_id: str
    name: str
    version: str
    description: str
    files: List[PackFile]
    created_at: str
    updated_at: str
    checksum: str = ""  # Hash of all file checksums

    def compute_checksum(self) -> str:
        """Compute manifest checksum from file hashes."""
        file_hashes = sorted([f.md5 for f in self.files])
        combined = ":".join(file_hashes)
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def to_json(self) -> str:
        """Convert to JSON string."""
        data = asdict(self)
        data['files'] = [asdict(f) for f in self.files]
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'PackManifest':
        """Create from JSON string."""
        data = json.loads(json_str)
        files = [PackFile(**f) for f in data.pop('files', [])]
        return cls(files=files, **data)

    @classmethod
    def from_dict(cls, data: dict) -> 'PackManifest':
        """Create from dictionary."""
        files = [PackFile(**f) if isinstance(f, dict) else f
                 for f in data.pop('files', [])]
        return cls(files=files, **data)


class ManifestManager:
    """Manages pack manifests and local cache."""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or MANIFEST_DB
        self.local_cache = LOCAL_PACK_CACHE
        self._init_db()
        self._init_cache()

    def _init_db(self):
        """Initialize manifest tracking database."""
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS manifests (
                pack_id TEXT PRIMARY KEY,
                name TEXT,
                version TEXT,
                checksum TEXT,
                drive_folder_id TEXT,
                local_path TEXT,
                last_synced TEXT,
                manifest_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS pack_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pack_id TEXT,
                file_name TEXT,
                drive_id TEXT,
                md5 TEXT,
                size INTEGER,
                local_path TEXT,
                synced INTEGER DEFAULT 0,
                FOREIGN KEY (pack_id) REFERENCES manifests(pack_id)
            );

            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pack_id TEXT,
                action TEXT,
                files_synced INTEGER,
                bytes_transferred INTEGER,
                duration_ms INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_files_pack ON pack_files(pack_id);
        """)
        conn.commit()
        conn.close()

    def _init_cache(self):
        """Initialize local cache directory."""
        self.local_cache.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Manifest CRUD
    # -------------------------------------------------------------------------

    def save_manifest(self, manifest: PackManifest, drive_folder_id: str = None):
        """Save or update a manifest."""
        manifest.checksum = manifest.compute_checksum()
        manifest.updated_at = datetime.now().isoformat()

        local_path = self.local_cache / manifest.pack_id
        local_path.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO manifests
            (pack_id, name, version, checksum, drive_folder_id, local_path,
             last_synced, manifest_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            manifest.pack_id,
            manifest.name,
            manifest.version,
            manifest.checksum,
            drive_folder_id,
            str(local_path),
            datetime.now().isoformat(),
            manifest.to_json(),
            manifest.updated_at
        ))

        # Update file tracking
        conn.execute("DELETE FROM pack_files WHERE pack_id = ?", (manifest.pack_id,))
        for f in manifest.files:
            conn.execute("""
                INSERT INTO pack_files (pack_id, file_name, drive_id, md5, size)
                VALUES (?, ?, ?, ?, ?)
            """, (manifest.pack_id, f.name, f.drive_id, f.md5, f.size))

        conn.commit()
        conn.close()

        # Write local manifest.json
        manifest_path = local_path / "manifest.json"
        manifest_path.write_text(manifest.to_json())

        return manifest

    def get_manifest(self, pack_id: str) -> Optional[PackManifest]:
        """Get a manifest by pack ID."""
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT manifest_json FROM manifests WHERE pack_id = ?",
            (pack_id,)
        ).fetchone()
        conn.close()

        if row:
            return PackManifest.from_json(row[0])
        return None

    def list_manifests(self) -> List[Dict]:
        """List all known manifests."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT pack_id, name, version, checksum, last_synced
            FROM manifests ORDER BY name
        """)
        results = [
            {
                "pack_id": r[0],
                "name": r[1],
                "version": r[2],
                "checksum": r[3],
                "last_synced": r[4]
            }
            for r in cursor.fetchall()
        ]
        conn.close()
        return results

    def delete_manifest(self, pack_id: str):
        """Delete a manifest."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM pack_files WHERE pack_id = ?", (pack_id,))
        conn.execute("DELETE FROM manifests WHERE pack_id = ?", (pack_id,))
        conn.commit()
        conn.close()

    # -------------------------------------------------------------------------
    # Sync Status
    # -------------------------------------------------------------------------

    def get_sync_status(self, pack_id: str) -> Dict:
        """Get sync status for a pack."""
        conn = sqlite3.connect(self.db_path)

        # Get manifest info
        row = conn.execute("""
            SELECT checksum, last_synced, local_path FROM manifests WHERE pack_id = ?
        """, (pack_id,)).fetchone()

        if not row:
            conn.close()
            return {"error": "Pack not found"}

        # Get file stats
        cursor = conn.execute("""
            SELECT COUNT(*), SUM(size), SUM(synced)
            FROM pack_files WHERE pack_id = ?
        """, (pack_id,))
        file_stats = cursor.fetchone()

        conn.close()

        return {
            "pack_id": pack_id,
            "checksum": row[0],
            "last_synced": row[1],
            "local_path": row[2],
            "total_files": file_stats[0] or 0,
            "total_size": file_stats[1] or 0,
            "files_synced": file_stats[2] or 0,
            "sync_complete": (file_stats[2] or 0) == (file_stats[0] or 0)
        }

    def needs_sync(self, pack_id: str, remote_checksum: str) -> bool:
        """Check if pack needs syncing based on checksum."""
        manifest = self.get_manifest(pack_id)
        if not manifest:
            return True  # New pack
        return manifest.checksum != remote_checksum

    def log_sync(self, pack_id: str, action: str, files_synced: int,
                 bytes_transferred: int, duration_ms: int):
        """Log a sync operation."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO sync_log (pack_id, action, files_synced, bytes_transferred, duration_ms)
            VALUES (?, ?, ?, ?, ?)
        """, (pack_id, action, files_synced, bytes_transferred, duration_ms))
        conn.commit()
        conn.close()

    # -------------------------------------------------------------------------
    # Local Cache Operations
    # -------------------------------------------------------------------------

    def get_local_path(self, pack_id: str) -> Path:
        """Get local cache path for a pack."""
        return self.local_cache / pack_id

    def mark_file_synced(self, pack_id: str, file_name: str, local_path: str):
        """Mark a file as synced locally."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE pack_files SET synced = 1, local_path = ?
            WHERE pack_id = ? AND file_name = ?
        """, (local_path, pack_id, file_name))
        conn.commit()
        conn.close()

    def get_unsynced_files(self, pack_id: str) -> List[Dict]:
        """Get list of files that haven't been synced."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT file_name, drive_id, md5, size
            FROM pack_files
            WHERE pack_id = ? AND synced = 0
        """, (pack_id,))
        results = [
            {"name": r[0], "drive_id": r[1], "md5": r[2], "size": r[3]}
            for r in cursor.fetchall()
        ]
        conn.close()
        return results


# CLI
if __name__ == "__main__":
    import fire

    class CLI:
        """Manifest Manager CLI."""

        def __init__(self):
            self.manager = ManifestManager()

        def list(self):
            """List all manifests."""
            manifests = self.manager.list_manifests()
            if not manifests:
                print("No manifests found")
                return
            for m in manifests:
                print(f"{m['pack_id']:20} | {m['name']:20} | v{m['version']} | {m['checksum']}")

        def status(self, pack_id: str):
            """Get sync status for a pack."""
            status = self.manager.get_sync_status(pack_id)
            for k, v in status.items():
                print(f"{k}: {v}")

        def create(self, pack_id: str, name: str, description: str = ""):
            """Create a new empty manifest."""
            manifest = PackManifest(
                pack_id=pack_id,
                name=name,
                version="1.0.0",
                description=description,
                files=[],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            self.manager.save_manifest(manifest)
            print(f"Created manifest: {pack_id}")

        def show(self, pack_id: str):
            """Show manifest details."""
            manifest = self.manager.get_manifest(pack_id)
            if manifest:
                print(manifest.to_json())
            else:
                print(f"Manifest not found: {pack_id}")

    fire.Fire(CLI)
