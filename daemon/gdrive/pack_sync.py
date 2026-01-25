#!/usr/bin/env python3
"""
Pack Sync Workflow - Phase 2

Syncs packs from Google Drive to local cache using manifest.json.
Works alongside existing PDF/embedding sync without replacing it.

Usage:
    python pack_sync.py list           # List remote packs
    python pack_sync.py pull Canon     # Pull a specific pack
    python pack_sync.py pull-all       # Pull all packs
    python pack_sync.py status         # Show sync status
"""

import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

try:
    from .client import GDriveClient, FileMetadata
    from .manifest import ManifestManager, PackManifest, PackFile
except ImportError:
    from client import GDriveClient, FileMetadata
    from manifest import ManifestManager, PackManifest, PackFile


# Drive paths (under /Atlas for compatibility)
PACKS_ROOT = "Packs"  # /Atlas/Packs/


@dataclass
class SyncResult:
    """Result of a pack sync operation."""
    pack_id: str
    success: bool
    files_synced: int
    bytes_transferred: int
    duration_ms: int
    errors: List[str]


class PackSync:
    """
    Syncs packs between Google Drive and local cache.

    Flow:
    1. List packs from /Atlas/Packs/
    2. For each pack, read manifest.json
    3. Compare checksums to detect changes
    4. Download changed/new files
    5. Update local manifest
    """

    def __init__(self):
        self.drive = GDriveClient()
        self.manifests = ManifestManager()
        self._packs_folder_id: Optional[str] = None

    def _get_packs_folder(self) -> Optional[str]:
        """Get or create the Packs folder ID."""
        if self._packs_folder_id:
            return self._packs_folder_id

        # Find or create /Atlas/Packs
        folder = self.drive.get_folder_by_path(f"/{PACKS_ROOT}")
        if folder:
            self._packs_folder_id = folder.id
        else:
            # Create it
            atlas_folder = self.drive.get_folder_by_path("/")
            if atlas_folder:
                folder = self.drive.create_folder(PACKS_ROOT, atlas_folder.id)
                self._packs_folder_id = folder.id

        return self._packs_folder_id

    # -------------------------------------------------------------------------
    # Remote Pack Discovery
    # -------------------------------------------------------------------------

    def list_remote_packs(self) -> List[Dict]:
        """List all packs in /Atlas/Packs/."""
        packs_folder = self._get_packs_folder()
        if not packs_folder:
            return []

        # List subfolders (each subfolder is a pack)
        items = self.drive.list_folder(packs_folder)
        packs = []

        for item in items:
            if item.mime_type == GDriveClient.FOLDER_MIME:
                # Try to read manifest.json
                manifest = self._read_remote_manifest(item.id)
                packs.append({
                    "pack_id": item.name,
                    "folder_id": item.id,
                    "name": manifest.name if manifest else item.name,
                    "version": manifest.version if manifest else "unknown",
                    "checksum": manifest.checksum if manifest else None,
                    "file_count": len(manifest.files) if manifest else 0,
                })

        return packs

    def _read_remote_manifest(self, folder_id: str) -> Optional[PackManifest]:
        """Read manifest.json from a remote pack folder."""
        # Search for manifest.json in folder
        files = self.drive.list_folder(folder_id)
        manifest_file = next(
            (f for f in files if f.name.lower() == "manifest.json"),
            None
        )

        if not manifest_file:
            return None

        try:
            content = self.drive.read_file(manifest_file.id)
            return PackManifest.from_json(content.decode('utf-8'))
        except Exception as e:
            print(f"Error reading manifest: {e}")
            return None

    # -------------------------------------------------------------------------
    # Pull Operations
    # -------------------------------------------------------------------------

    def pull_pack(self, pack_id: str, force: bool = False) -> SyncResult:
        """
        Pull a pack from Drive to local cache.

        Args:
            pack_id: Pack name (folder name in Drive)
            force: Force re-download even if checksums match
        """
        start_time = time.time()
        errors = []
        files_synced = 0
        bytes_transferred = 0

        # Find pack folder
        packs_folder = self._get_packs_folder()
        if not packs_folder:
            return SyncResult(pack_id, False, 0, 0, 0, ["Packs folder not found"])

        # Search for pack folder
        items = self.drive.list_folder(packs_folder)
        pack_folder = next((f for f in items if f.name == pack_id), None)

        if not pack_folder:
            return SyncResult(pack_id, False, 0, 0, 0, [f"Pack not found: {pack_id}"])

        # Read remote manifest
        remote_manifest = self._read_remote_manifest(pack_folder.id)
        if not remote_manifest:
            return SyncResult(pack_id, False, 0, 0, 0, ["No manifest.json in pack"])

        # Check if sync needed
        if not force:
            local_manifest = self.manifests.get_manifest(pack_id)
            if local_manifest and local_manifest.checksum == remote_manifest.checksum:
                duration = int((time.time() - start_time) * 1000)
                return SyncResult(pack_id, True, 0, 0, duration, ["Already up to date"])

        # Ensure local directory
        local_path = self.manifests.get_local_path(pack_id)
        local_path.mkdir(parents=True, exist_ok=True)

        # Download files
        pack_files = self.drive.list_folder(pack_folder.id)
        for file_meta in pack_files:
            if file_meta.name.lower() == "manifest.json":
                continue  # Skip manifest, we'll write our own

            try:
                file_local_path = local_path / file_meta.name
                self.drive.download_file(file_meta.id, file_local_path)
                files_synced += 1
                bytes_transferred += file_meta.size or 0

                # Update manifest file info
                for mf in remote_manifest.files:
                    if mf.name == file_meta.name:
                        mf.local_path = str(file_local_path)
                        break

            except Exception as e:
                errors.append(f"Failed to download {file_meta.name}: {e}")

        # Save manifest locally
        self.manifests.save_manifest(remote_manifest, pack_folder.id)

        duration = int((time.time() - start_time) * 1000)
        self.manifests.log_sync(pack_id, "pull", files_synced, bytes_transferred, duration)

        return SyncResult(
            pack_id=pack_id,
            success=len(errors) == 0,
            files_synced=files_synced,
            bytes_transferred=bytes_transferred,
            duration_ms=duration,
            errors=errors
        )

    def pull_all(self, force: bool = False) -> List[SyncResult]:
        """Pull all packs from Drive."""
        results = []
        packs = self.list_remote_packs()

        for pack in packs:
            print(f"Pulling {pack['pack_id']}...")
            result = self.pull_pack(pack['pack_id'], force)
            results.append(result)
            status = "OK" if result.success else "FAILED"
            print(f"  {status}: {result.files_synced} files, {result.bytes_transferred} bytes")

        return results

    # -------------------------------------------------------------------------
    # Push Operations (for creating packs)
    # -------------------------------------------------------------------------

    def create_remote_pack(self, pack_id: str, name: str, description: str = "") -> str:
        """Create a new pack folder on Drive."""
        packs_folder = self._get_packs_folder()
        if not packs_folder:
            # Create Packs folder
            atlas = self.drive.ensure_folder_path("/")
            folder = self.drive.create_folder(PACKS_ROOT, atlas.id)
            packs_folder = folder.id

        # Create pack subfolder
        pack_folder = self.drive.create_folder(pack_id, packs_folder)

        # Create initial manifest
        manifest = PackManifest(
            pack_id=pack_id,
            name=name,
            version="1.0.0",
            description=description,
            files=[],
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

        # Save locally and upload manifest
        self.manifests.save_manifest(manifest, pack_folder.id)

        # Upload manifest.json to Drive
        local_manifest = self.manifests.get_local_path(pack_id) / "manifest.json"
        self.drive.upload_file(local_manifest, pack_folder.id)

        return pack_folder.id

    def upload_to_pack(self, pack_id: str, local_file: Path) -> bool:
        """Upload a file to an existing pack."""
        manifest = self.manifests.get_manifest(pack_id)
        if not manifest:
            print(f"Pack not found: {pack_id}")
            return False

        # Get pack folder ID
        conn = __import__('sqlite3').connect(self.manifests.db_path)
        row = conn.execute(
            "SELECT drive_folder_id FROM manifests WHERE pack_id = ?",
            (pack_id,)
        ).fetchone()
        conn.close()

        if not row or not row[0]:
            print("Pack folder ID not found")
            return False

        folder_id = row[0]

        # Upload file
        result = self.drive.upload_file(local_file, folder_id)

        # Update manifest
        new_file = PackFile(
            name=local_file.name,
            drive_id=result.id,
            size=result.size or local_file.stat().st_size,
            md5=result.md5_checksum or "",
            modified=datetime.now().isoformat(),
            local_path=str(local_file)
        )
        manifest.files.append(new_file)
        manifest.version = self._increment_version(manifest.version)
        self.manifests.save_manifest(manifest, folder_id)

        # Upload updated manifest
        local_manifest = self.manifests.get_local_path(pack_id) / "manifest.json"
        self.drive.upload_file(local_manifest, folder_id)

        return True

    def _increment_version(self, version: str) -> str:
        """Increment patch version: 1.0.0 -> 1.0.1"""
        parts = version.split('.')
        if len(parts) == 3:
            parts[2] = str(int(parts[2]) + 1)
        return '.'.join(parts)

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict:
        """Get overall sync status."""
        local_manifests = self.manifests.list_manifests()
        remote_packs = self.list_remote_packs()

        # Compare
        local_ids = {m['pack_id'] for m in local_manifests}
        remote_ids = {p['pack_id'] for p in remote_packs}

        return {
            "local_packs": len(local_manifests),
            "remote_packs": len(remote_packs),
            "synced": len(local_ids & remote_ids),
            "local_only": list(local_ids - remote_ids),
            "remote_only": list(remote_ids - local_ids),
            "packs": [
                {
                    **m,
                    "needs_sync": any(
                        p['pack_id'] == m['pack_id'] and p.get('checksum') != m.get('checksum')
                        for p in remote_packs
                    )
                }
                for m in local_manifests
            ]
        }


# CLI
if __name__ == "__main__":
    import fire

    class CLI:
        """Pack Sync CLI."""

        def __init__(self):
            self.sync = PackSync()

        def list(self):
            """List remote packs."""
            packs = self.sync.list_remote_packs()
            if not packs:
                print("No packs found in /Atlas/Packs/")
                return
            print(f"{'Pack ID':20} | {'Name':20} | {'Version':10} | Files")
            print("-" * 70)
            for p in packs:
                print(f"{p['pack_id']:20} | {p['name']:20} | {p['version']:10} | {p['file_count']}")

        def pull(self, pack_id: str, force: bool = False):
            """Pull a pack from Drive."""
            result = self.sync.pull_pack(pack_id, force)
            if result.success:
                print(f"OK: {result.files_synced} files, {result.bytes_transferred} bytes in {result.duration_ms}ms")
            else:
                print(f"FAILED: {result.errors}")

        def pull_all(self, force: bool = False):
            """Pull all packs."""
            results = self.sync.pull_all(force)
            print(f"\n{sum(1 for r in results if r.success)}/{len(results)} packs synced successfully")

        def status(self):
            """Show sync status."""
            status = self.sync.get_status()
            print(f"Local packs: {status['local_packs']}")
            print(f"Remote packs: {status['remote_packs']}")
            print(f"Synced: {status['synced']}")
            if status['remote_only']:
                print(f"Not pulled: {status['remote_only']}")

        def create(self, pack_id: str, name: str, description: str = ""):
            """Create a new pack on Drive."""
            folder_id = self.sync.create_remote_pack(pack_id, name, description)
            print(f"Created pack: {pack_id} (folder: {folder_id})")

        def upload(self, pack_id: str, file_path: str):
            """Upload a file to a pack."""
            path = Path(file_path)
            if not path.exists():
                print(f"File not found: {file_path}")
                return
            if self.sync.upload_to_pack(pack_id, path):
                print(f"Uploaded {path.name} to {pack_id}")
            else:
                print("Upload failed")

    fire.Fire(CLI)
