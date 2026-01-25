#!/usr/bin/env python3
"""
Google Drive Sync - Bidirectional sync for token optimization.

Syncs:
- Local processed files → Drive archive
- Drive PDFs → Local GateofTruth for processing
- Embeddings → Drive for persistence
- Handoffs/Learnings → Drive for backup
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass

try:
    from .client import GDriveClient, FileMetadata
except ImportError:
    from client import GDriveClient, FileMetadata

# Local paths
LOCAL_GATE_OF_TRUTH = Path(r"C:\Users\New Employee\Documents\GateofTruth")
LOCAL_HANDOFFS = Path(r"C:\Users\New Employee\Downloads\Atlas-OS-main\Claude n8n\thoughts\handoffs")
LOCAL_EMBEDDINGS = Path(r"C:\Users\New Employee\Downloads\Atlas-OS-main\Claude n8n\daemon")

# Drive folder structure
DRIVE_FOLDERS = {
    'root': '/Atlas',
    'pdfs_inbox': '/Atlas/Inbox/PDFs',
    'pdfs_processed': '/Atlas/Archive/PDFs',
    'handoffs': '/Atlas/Backup/Handoffs',
    'embeddings': '/Atlas/Cache/Embeddings',
    'models': '/Atlas/Models',
    'rag_corpus': '/Atlas/RAG_Corpus',
}


@dataclass
class SyncResult:
    """Result of a sync operation."""
    uploaded: List[str]
    downloaded: List[str]
    skipped: List[str]
    errors: List[str]

    def to_dict(self) -> dict:
        return {
            'uploaded': self.uploaded,
            'downloaded': self.downloaded,
            'skipped': self.skipped,
            'errors': self.errors,
            'summary': f"Up:{len(self.uploaded)} Down:{len(self.downloaded)} Skip:{len(self.skipped)} Err:{len(self.errors)}"
        }


class DriveSync:
    """Bidirectional sync between local and Drive."""

    def __init__(self):
        self.client = GDriveClient()
        self._folder_cache: Dict[str, str] = {}  # path -> id

    def _ensure_drive_structure(self):
        """Create Atlas folder structure on Drive."""
        for name, path in DRIVE_FOLDERS.items():
            folder = self.client.ensure_folder_path(path)
            self._folder_cache[path] = folder.id
            print(f"  {name}: {path} ({folder.id})")

    def _get_folder_id(self, drive_path: str) -> str:
        """Get folder ID, creating if needed."""
        if drive_path in self._folder_cache:
            return self._folder_cache[drive_path]
        folder = self.client.ensure_folder_path(drive_path)
        self._folder_cache[drive_path] = folder.id
        return folder.id

    # -------------------------------------------------------------------------
    # PDF Sync: Drive → Local for processing
    # -------------------------------------------------------------------------

    def sync_pdfs_to_local(self, limit: int = 10) -> SyncResult:
        """Download new PDFs from Drive inbox to GateofTruth."""
        result = SyncResult([], [], [], [])

        # Get Drive inbox folder
        inbox_id = self._get_folder_id(DRIVE_FOLDERS['pdfs_inbox'])
        drive_pdfs = self.client.list_folder(inbox_id)

        # Get already-processed files
        processed = self._get_processed_hashes()

        for pdf in drive_pdfs[:limit]:
            if pdf.mime_type != 'application/pdf':
                continue

            # Check if already processed
            if pdf.md5_checksum in processed:
                result.skipped.append(pdf.name)
                continue

            try:
                # Download to GateofTruth
                local_path = LOCAL_GATE_OF_TRUTH / pdf.name
                self.client.download_file(pdf.id, local_path)
                result.downloaded.append(pdf.name)

                # Move to processed folder on Drive
                processed_id = self._get_folder_id(DRIVE_FOLDERS['pdfs_processed'])
                self.client.move_file(pdf.id, processed_id)

            except Exception as e:
                result.errors.append(f"{pdf.name}: {e}")

        return result

    def _get_processed_hashes(self) -> set:
        """Get MD5 hashes of already processed files."""
        db_path = Path(__file__).parent.parent / 'ingest.db'
        if not db_path.exists():
            return set()

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.execute("SELECT file_hash FROM processed_files WHERE status='completed'")
            return {row[0] for row in cursor.fetchall()}
        finally:
            conn.close()

    # -------------------------------------------------------------------------
    # Handoff Sync: Local → Drive for backup
    # -------------------------------------------------------------------------

    def sync_handoffs_to_drive(self) -> SyncResult:
        """Backup local handoffs to Drive."""
        result = SyncResult([], [], [], [])

        if not LOCAL_HANDOFFS.exists():
            return result

        # Get existing handoffs on Drive
        folder_id = self._get_folder_id(DRIVE_FOLDERS['handoffs'])
        drive_files = {f.name: f for f in self.client.list_folder(folder_id)}

        for local_file in LOCAL_HANDOFFS.glob('*.yaml'):
            if local_file.name in drive_files:
                result.skipped.append(local_file.name)
                continue

            try:
                self.client.upload_file(local_file, folder_id)
                result.uploaded.append(local_file.name)
            except Exception as e:
                result.errors.append(f"{local_file.name}: {e}")

        return result

    # -------------------------------------------------------------------------
    # Embedding Sync: Persist embeddings to Drive
    # -------------------------------------------------------------------------

    def sync_embeddings_to_drive(self) -> SyncResult:
        """Backup embedding databases to Drive."""
        result = SyncResult([], [], [], [])

        embedding_files = [
            'utf_knowledge.db',
            'synthesis.db',
            'router.db',
        ]

        folder_id = self._get_folder_id(DRIVE_FOLDERS['embeddings'])

        for filename in embedding_files:
            local_path = LOCAL_EMBEDDINGS / filename
            if not local_path.exists():
                continue

            try:
                # Upload with timestamp suffix
                timestamp = datetime.now().strftime('%Y%m%d')
                backup_name = f"{local_path.stem}_{timestamp}{local_path.suffix}"
                self.client.upload_file(local_path, folder_id, name=backup_name)
                result.uploaded.append(backup_name)
            except Exception as e:
                result.errors.append(f"{filename}: {e}")

        return result

    def restore_embeddings_from_drive(self) -> SyncResult:
        """Restore latest embeddings from Drive."""
        result = SyncResult([], [], [], [])

        folder_id = self._get_folder_id(DRIVE_FOLDERS['embeddings'])
        drive_files = self.client.list_folder(folder_id)

        # Group by base name, get latest
        by_base = {}
        for f in drive_files:
            # Extract base name (utf_knowledge_20260125.db → utf_knowledge)
            base = f.name.rsplit('_', 1)[0] if '_' in f.name else f.name.rsplit('.', 1)[0]
            if base not in by_base or f.modified_time > by_base[base].modified_time:
                by_base[base] = f

        for base, drive_file in by_base.items():
            local_name = f"{base}.db"
            local_path = LOCAL_EMBEDDINGS / local_name

            try:
                self.client.download_file(drive_file.id, local_path)
                result.downloaded.append(local_name)
            except Exception as e:
                result.errors.append(f"{local_name}: {e}")

        return result

    # -------------------------------------------------------------------------
    # Full Sync
    # -------------------------------------------------------------------------

    def full_sync(self) -> Dict[str, SyncResult]:
        """Run all sync operations."""
        print("Ensuring Drive folder structure...")
        self._ensure_drive_structure()

        results = {}

        print("\nSyncing PDFs from Drive inbox...")
        results['pdfs'] = self.sync_pdfs_to_local()
        print(f"  {results['pdfs'].to_dict()['summary']}")

        print("\nBacking up handoffs to Drive...")
        results['handoffs'] = self.sync_handoffs_to_drive()
        print(f"  {results['handoffs'].to_dict()['summary']}")

        print("\nBacking up embeddings to Drive...")
        results['embeddings'] = self.sync_embeddings_to_drive()
        print(f"  {results['embeddings'].to_dict()['summary']}")

        return results

    # -------------------------------------------------------------------------
    # Model Management (for LocalAI)
    # -------------------------------------------------------------------------

    def list_models(self) -> List[FileMetadata]:
        """List available models on Drive."""
        folder_id = self._get_folder_id(DRIVE_FOLDERS['models'])
        return self.client.list_folder(folder_id)

    def download_model(self, model_name: str, local_dir: Path) -> Path:
        """Download a model from Drive."""
        folder_id = self._get_folder_id(DRIVE_FOLDERS['models'])
        files = self.client.search(model_name, folder_id)

        if not files:
            raise FileNotFoundError(f"Model not found: {model_name}")

        model_file = files[0]
        local_path = local_dir / model_file.name
        return self.client.download_file(model_file.id, local_path)

    def upload_model(self, local_path: Path) -> FileMetadata:
        """Upload a model to Drive."""
        folder_id = self._get_folder_id(DRIVE_FOLDERS['models'])
        return self.client.upload_file(local_path, folder_id)


# CLI
if __name__ == '__main__':
    import fire

    class CLI:
        """Drive Sync CLI."""

        def __init__(self):
            self.sync = DriveSync()

        def setup(self):
            """Create Atlas folder structure on Drive."""
            self.sync._ensure_drive_structure()
            print("\nDrive structure ready!")

        def full(self):
            """Run full sync."""
            results = self.sync.full_sync()
            print("\n" + "=" * 50)
            print("SYNC COMPLETE")
            for name, result in results.items():
                print(f"  {name}: {result.to_dict()['summary']}")

        def pdfs(self, limit: int = 10):
            """Sync PDFs from Drive to local."""
            result = self.sync.sync_pdfs_to_local(limit)
            print(f"Downloaded: {result.downloaded}")
            print(f"Skipped: {result.skipped}")
            if result.errors:
                print(f"Errors: {result.errors}")

        def handoffs(self):
            """Backup handoffs to Drive."""
            result = self.sync.sync_handoffs_to_drive()
            print(f"Uploaded: {result.uploaded}")

        def embeddings(self):
            """Backup embeddings to Drive."""
            result = self.sync.sync_embeddings_to_drive()
            print(f"Uploaded: {result.uploaded}")

        def restore(self):
            """Restore embeddings from Drive."""
            result = self.sync.restore_embeddings_from_drive()
            print(f"Downloaded: {result.downloaded}")

        def models(self):
            """List available models on Drive."""
            models = self.sync.list_models()
            print(f"Models on Drive ({len(models)}):")
            for m in models:
                size_gb = m.size / (1024**3) if m.size else 0
                print(f"  {m.name} ({size_gb:.2f} GB)")

    fire.Fire(CLI)
