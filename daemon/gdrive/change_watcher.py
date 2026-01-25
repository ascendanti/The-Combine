#!/usr/bin/env python3
"""
Change Feed Watcher - Phase 3

Uses Google Drive Changes API to detect manifest.json modifications.
Enables reactive pack sync instead of polling.

Usage:
    python change_watcher.py watch       # Start watching for changes
    python change_watcher.py check       # One-time change check
    python change_watcher.py reset       # Reset change token
"""

import time
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

try:
    from .client import GDriveClient, FileMetadata
    from .pack_sync import PackSync
except ImportError:
    from client import GDriveClient, FileMetadata
    from pack_sync import PackSync


DB_PATH = Path(__file__).parent.parent / "change_watcher.db"


@dataclass
class ChangeEvent:
    """A detected change in Drive."""
    file_id: str
    file_name: str
    change_type: str  # 'modified', 'created', 'deleted'
    parent_folder: Optional[str]
    timestamp: str
    is_manifest: bool


class ChangeWatcher:
    """
    Watches for changes in Google Drive using Changes API.

    Key concepts:
    - Start token: Marks where to begin watching
    - Page token: Used for pagination of changes
    - Change polling: Periodic check for new changes

    Flow:
    1. Get initial start token (marks "now")
    2. Poll for changes using token
    3. Filter for manifest.json changes
    4. Trigger pack sync when manifest changes
    """

    POLL_INTERVAL = 60  # seconds between checks

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DB_PATH
        self.drive = GDriveClient()
        self.pack_sync = PackSync()
        self._init_db()
        self._callbacks: List[Callable[[ChangeEvent], None]] = []

    def _init_db(self):
        """Initialize change tracking database."""
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS change_tokens (
                id INTEGER PRIMARY KEY,
                token TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_used TEXT
            );

            CREATE TABLE IF NOT EXISTS change_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT,
                file_name TEXT,
                change_type TEXT,
                parent_folder TEXT,
                is_manifest INTEGER,
                processed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_changelog_processed
                ON change_log(processed);
        """)
        conn.commit()
        conn.close()

    # -------------------------------------------------------------------------
    # Token Management
    # -------------------------------------------------------------------------

    def get_start_token(self) -> str:
        """Get a new start token from Drive API."""
        service = self.drive._get_service()
        response = service.changes().getStartPageToken().execute()
        return response.get('startPageToken')

    def get_stored_token(self) -> Optional[str]:
        """Get stored change token from database."""
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT token FROM change_tokens ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        return row[0] if row else None

    def store_token(self, token: str):
        """Store change token in database."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO change_tokens (token, last_used) VALUES (?, ?)",
            (token, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    def ensure_token(self) -> str:
        """Ensure we have a valid change token."""
        token = self.get_stored_token()
        if not token:
            token = self.get_start_token()
            self.store_token(token)
            print(f"Initialized change token: {token}")
        return token

    def reset_token(self):
        """Reset change token (start fresh)."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM change_tokens")
        conn.commit()
        conn.close()

        token = self.get_start_token()
        self.store_token(token)
        print(f"Reset change token to: {token}")
        return token

    # -------------------------------------------------------------------------
    # Change Detection
    # -------------------------------------------------------------------------

    def check_changes(self) -> List[ChangeEvent]:
        """
        Check for changes since last token.
        Returns list of ChangeEvent objects.
        """
        token = self.ensure_token()
        service = self.drive._get_service()

        changes = []
        page_token = token

        while page_token:
            response = service.changes().list(
                pageToken=page_token,
                spaces='drive',
                includeItemsFromAllDrives=False,
                fields='nextPageToken, newStartPageToken, changes(fileId, file(name, parents, mimeType, trashed))'
            ).execute()

            for change in response.get('changes', []):
                file_info = change.get('file', {})

                # Determine change type
                if file_info.get('trashed'):
                    change_type = 'deleted'
                elif change.get('removed'):
                    change_type = 'deleted'
                else:
                    change_type = 'modified'  # Could be created or modified

                file_name = file_info.get('name', 'unknown')
                is_manifest = file_name.lower() == 'manifest.json'

                event = ChangeEvent(
                    file_id=change.get('fileId'),
                    file_name=file_name,
                    change_type=change_type,
                    parent_folder=file_info.get('parents', [None])[0],
                    timestamp=datetime.now().isoformat(),
                    is_manifest=is_manifest
                )
                changes.append(event)

                # Log change
                self._log_change(event)

            # Get next page or new start token
            if 'newStartPageToken' in response:
                # No more changes, save new token
                self.store_token(response['newStartPageToken'])
                page_token = None
            else:
                page_token = response.get('nextPageToken')

        return changes

    def _log_change(self, event: ChangeEvent):
        """Log change to database."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO change_log (file_id, file_name, change_type,
                                    parent_folder, is_manifest)
            VALUES (?, ?, ?, ?, ?)
        """, (
            event.file_id,
            event.file_name,
            event.change_type,
            event.parent_folder,
            1 if event.is_manifest else 0
        ))
        conn.commit()
        conn.close()

    # -------------------------------------------------------------------------
    # Manifest-Specific Detection
    # -------------------------------------------------------------------------

    def get_manifest_changes(self) -> List[ChangeEvent]:
        """Get only manifest.json changes."""
        changes = self.check_changes()
        return [c for c in changes if c.is_manifest]

    def get_changed_packs(self) -> List[str]:
        """
        Get pack IDs that have changed manifests.
        Returns list of pack_id strings.
        """
        manifest_changes = self.get_manifest_changes()

        # Map parent folder IDs to pack names
        pack_ids = []
        packs_folder = self.pack_sync._get_packs_folder()

        if not packs_folder:
            return []

        # Get all pack folders
        pack_folders = self.drive.list_folder(packs_folder)
        folder_map = {f.id: f.name for f in pack_folders
                      if f.mime_type == GDriveClient.FOLDER_MIME}

        for change in manifest_changes:
            if change.parent_folder in folder_map:
                pack_ids.append(folder_map[change.parent_folder])

        return list(set(pack_ids))

    # -------------------------------------------------------------------------
    # Watch Loop
    # -------------------------------------------------------------------------

    def add_callback(self, callback: Callable[[ChangeEvent], None]):
        """Add callback for change events."""
        self._callbacks.append(callback)

    def watch(self, auto_sync: bool = True, interval: int = None):
        """
        Start watching for changes.

        Args:
            auto_sync: Automatically sync changed packs
            interval: Poll interval in seconds (default: 60)
        """
        interval = interval or self.POLL_INTERVAL
        print(f"Starting change watcher (polling every {interval}s)")
        print("Press Ctrl+C to stop")

        while True:
            try:
                changes = self.check_changes()

                if changes:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {len(changes)} changes detected")

                    manifest_changes = [c for c in changes if c.is_manifest]
                    if manifest_changes:
                        print(f"  - {len(manifest_changes)} manifest changes")

                        if auto_sync:
                            pack_ids = self.get_changed_packs()
                            for pack_id in pack_ids:
                                print(f"  - Syncing pack: {pack_id}")
                                result = self.pack_sync.pull_pack(pack_id)
                                status = "OK" if result.success else "FAILED"
                                print(f"    {status}: {result.files_synced} files")

                    # Trigger callbacks
                    for change in changes:
                        for callback in self._callbacks:
                            try:
                                callback(change)
                            except Exception as e:
                                print(f"Callback error: {e}")
                else:
                    print(".", end="", flush=True)

                time.sleep(interval)

            except KeyboardInterrupt:
                print("\nStopping watcher")
                break
            except Exception as e:
                print(f"\nError: {e}")
                time.sleep(interval)

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict:
        """Get change watcher statistics."""
        conn = sqlite3.connect(self.db_path)

        # Total changes
        total = conn.execute("SELECT COUNT(*) FROM change_log").fetchone()[0]

        # Manifest changes
        manifests = conn.execute(
            "SELECT COUNT(*) FROM change_log WHERE is_manifest = 1"
        ).fetchone()[0]

        # By type
        by_type = dict(conn.execute("""
            SELECT change_type, COUNT(*)
            FROM change_log
            GROUP BY change_type
        """).fetchall())

        # Recent changes
        recent = conn.execute("""
            SELECT file_name, change_type, created_at
            FROM change_log
            ORDER BY id DESC LIMIT 10
        """).fetchall()

        conn.close()

        return {
            "total_changes": total,
            "manifest_changes": manifests,
            "by_type": by_type,
            "recent": [
                {"file": r[0], "type": r[1], "at": r[2]}
                for r in recent
            ]
        }


# CLI
if __name__ == "__main__":
    import fire

    class CLI:
        """Change Watcher CLI."""

        def __init__(self):
            self.watcher = ChangeWatcher()

        def watch(self, interval: int = 60, no_sync: bool = False):
            """Start watching for changes."""
            self.watcher.watch(auto_sync=not no_sync, interval=interval)

        def check(self):
            """One-time change check."""
            changes = self.watcher.check_changes()
            if not changes:
                print("No changes detected")
                return

            print(f"Found {len(changes)} changes:")
            for c in changes:
                manifest = " [MANIFEST]" if c.is_manifest else ""
                print(f"  {c.change_type}: {c.file_name}{manifest}")

        def packs(self):
            """Check for changed packs."""
            pack_ids = self.watcher.get_changed_packs()
            if not pack_ids:
                print("No pack changes detected")
                return

            print(f"Changed packs: {pack_ids}")

        def reset(self):
            """Reset change token (start fresh)."""
            self.watcher.reset_token()

        def stats(self):
            """Show watcher statistics."""
            stats = self.watcher.get_stats()
            print(f"Total changes: {stats['total_changes']}")
            print(f"Manifest changes: {stats['manifest_changes']}")
            print(f"By type: {stats['by_type']}")
            if stats['recent']:
                print("Recent:")
                for r in stats['recent'][:5]:
                    print(f"  {r['type']}: {r['file']} ({r['at']})")

    fire.Fire(CLI)
