#!/usr/bin/env python3
"""
Google Drive Client - Core API wrapper.

Provides authenticated access to Google Drive with caching.
"""

import json
import io
from pathlib import Path
from typing import List, Dict, Optional, BinaryIO
from dataclasses import dataclass
from datetime import datetime

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# Paths
CREDS_DIR = Path.home() / '.atlas' / 'gdrive_credentials'
TOKEN_FILE = CREDS_DIR / 'token.json'
SCOPES = ['https://www.googleapis.com/auth/drive']


@dataclass
class FileMetadata:
    """Google Drive file metadata."""
    id: str
    name: str
    mime_type: str
    size: Optional[int] = None
    parent_id: Optional[str] = None
    modified_time: Optional[str] = None
    md5_checksum: Optional[str] = None
    web_view_link: Optional[str] = None

    @classmethod
    def from_api(cls, data: dict) -> 'FileMetadata':
        """Create from API response."""
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            mime_type=data.get('mimeType', ''),
            size=int(data['size']) if 'size' in data else None,
            parent_id=data.get('parents', [None])[0] if data.get('parents') else None,
            modified_time=data.get('modifiedTime'),
            md5_checksum=data.get('md5Checksum'),
            web_view_link=data.get('webViewLink'),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'mime_type': self.mime_type,
            'size': self.size,
            'parent_id': self.parent_id,
            'modified_time': self.modified_time,
            'md5_checksum': self.md5_checksum,
            'web_view_link': self.web_view_link,
        }


class GDriveClient:
    """Google Drive API client with caching."""

    FOLDER_MIME = 'application/vnd.google-apps.folder'
    FILE_FIELDS = 'id, name, mimeType, size, parents, modifiedTime, md5Checksum, webViewLink'

    def __init__(self, token_path: Path = None):
        """Initialize client with OAuth token."""
        self.token_path = token_path or TOKEN_FILE
        self._service = None
        self._creds = None

    def _get_creds(self) -> Credentials:
        """Load and refresh credentials."""
        if self._creds and self._creds.valid:
            return self._creds

        if not self.token_path.exists():
            raise FileNotFoundError(
                f"Token not found at {self.token_path}. Run gdrive_oauth_simple.py first."
            )

        self._creds = Credentials.from_authorized_user_file(
            str(self.token_path), SCOPES
        )

        # Refresh if expired
        if self._creds.expired and self._creds.refresh_token:
            self._creds.refresh(Request())
            self.token_path.write_text(self._creds.to_json())

        return self._creds

    @property
    def service(self):
        """Get authenticated Drive service."""
        if self._service is None:
            creds = self._get_creds()
            self._service = build('drive', 'v3', credentials=creds)
        return self._service

    # -------------------------------------------------------------------------
    # List & Search
    # -------------------------------------------------------------------------

    def list_folder(self, folder_id: str = 'root', page_size: int = 100) -> List[FileMetadata]:
        """List contents of a folder."""
        query = f"'{folder_id}' in parents and trashed=false"
        return self._search(query, page_size)

    def search(self, query: str, folder_id: str = None, page_size: int = 50) -> List[FileMetadata]:
        """Search for files by name or content."""
        q_parts = [f"name contains '{query}'", "trashed=false"]
        if folder_id:
            q_parts.append(f"'{folder_id}' in parents")
        return self._search(" and ".join(q_parts), page_size)

    def search_by_type(self, mime_type: str, folder_id: str = None, page_size: int = 50) -> List[FileMetadata]:
        """Search for files by MIME type."""
        q_parts = [f"mimeType='{mime_type}'", "trashed=false"]
        if folder_id:
            q_parts.append(f"'{folder_id}' in parents")
        return self._search(" and ".join(q_parts), page_size)

    def list_pdfs(self, folder_id: str = None, page_size: int = 100) -> List[FileMetadata]:
        """List all PDFs (for RAG corpus sync)."""
        return self.search_by_type('application/pdf', folder_id, page_size)

    def _search(self, query: str, page_size: int) -> List[FileMetadata]:
        """Execute a search query."""
        results = []
        page_token = None

        while True:
            response = self.service.files().list(
                q=query,
                pageSize=min(page_size, 1000),
                fields=f"nextPageToken, files({self.FILE_FIELDS})",
                pageToken=page_token
            ).execute()

            for item in response.get('files', []):
                results.append(FileMetadata.from_api(item))

            page_token = response.get('nextPageToken')
            if not page_token or len(results) >= page_size:
                break

        return results[:page_size]

    # -------------------------------------------------------------------------
    # Read
    # -------------------------------------------------------------------------

    def get_metadata(self, file_id: str) -> FileMetadata:
        """Get file metadata."""
        data = self.service.files().get(
            fileId=file_id,
            fields=self.FILE_FIELDS
        ).execute()
        return FileMetadata.from_api(data)

    def read_file(self, file_id: str) -> bytes:
        """Download file content."""
        request = self.service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        return buffer.getvalue()

    def download_file(self, file_id: str, local_path: Path) -> Path:
        """Download file to local path."""
        content = self.read_file(file_id)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(content)
        return local_path

    # -------------------------------------------------------------------------
    # Write
    # -------------------------------------------------------------------------

    def upload_file(self, local_path: Path, parent_id: str = 'root', name: str = None) -> FileMetadata:
        """Upload a file to Drive."""
        file_name = name or local_path.name

        # Determine MIME type
        import mimetypes
        mime_type, _ = mimetypes.guess_type(str(local_path))
        mime_type = mime_type or 'application/octet-stream'

        file_metadata = {
            'name': file_name,
            'parents': [parent_id]
        }

        media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=True)

        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields=self.FILE_FIELDS
        ).execute()

        return FileMetadata.from_api(file)

    def create_folder(self, name: str, parent_id: str = 'root') -> FileMetadata:
        """Create a folder."""
        file_metadata = {
            'name': name,
            'mimeType': self.FOLDER_MIME,
            'parents': [parent_id]
        }

        file = self.service.files().create(
            body=file_metadata,
            fields=self.FILE_FIELDS
        ).execute()

        return FileMetadata.from_api(file)

    def move_file(self, file_id: str, new_parent_id: str) -> FileMetadata:
        """Move a file to a different folder."""
        # Get current parents
        file = self.service.files().get(fileId=file_id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents', []))

        # Move file
        file = self.service.files().update(
            fileId=file_id,
            addParents=new_parent_id,
            removeParents=previous_parents,
            fields=self.FILE_FIELDS
        ).execute()

        return FileMetadata.from_api(file)

    def rename_file(self, file_id: str, new_name: str) -> FileMetadata:
        """Rename a file."""
        file = self.service.files().update(
            fileId=file_id,
            body={'name': new_name},
            fields=self.FILE_FIELDS
        ).execute()
        return FileMetadata.from_api(file)

    def delete_file(self, file_id: str) -> bool:
        """Move file to trash."""
        self.service.files().update(
            fileId=file_id,
            body={'trashed': True}
        ).execute()
        return True

    # -------------------------------------------------------------------------
    # Navigation
    # -------------------------------------------------------------------------

    def get_folder_by_path(self, path: str) -> Optional[FileMetadata]:
        """Get folder by path like '/Documents/Work/Projects'."""
        if not path or path == '/':
            return FileMetadata(id='root', name='My Drive', mime_type=self.FOLDER_MIME)

        parts = [p for p in path.strip('/').split('/') if p]
        current_id = 'root'

        for part in parts:
            query = f"name='{part}' and '{current_id}' in parents and mimeType='{self.FOLDER_MIME}' and trashed=false"
            results = self._search(query, 1)
            if not results:
                return None
            current_id = results[0].id

        return self.get_metadata(current_id)

    def ensure_folder_path(self, path: str) -> FileMetadata:
        """Create folder path if it doesn't exist."""
        if not path or path == '/':
            return FileMetadata(id='root', name='My Drive', mime_type=self.FOLDER_MIME)

        parts = [p for p in path.strip('/').split('/') if p]
        current_id = 'root'
        current_meta = None

        for part in parts:
            query = f"name='{part}' and '{current_id}' in parents and mimeType='{self.FOLDER_MIME}' and trashed=false"
            results = self._search(query, 1)

            if results:
                current_id = results[0].id
                current_meta = results[0]
            else:
                # Create folder
                current_meta = self.create_folder(part, current_id)
                current_id = current_meta.id

        return current_meta

    # -------------------------------------------------------------------------
    # Storage Info
    # -------------------------------------------------------------------------

    def get_storage_quota(self) -> Dict:
        """Get storage quota information."""
        about = self.service.about().get(fields='storageQuota, user').execute()
        quota = about.get('storageQuota', {})
        user = about.get('user', {})

        return {
            'user': user.get('displayName', 'Unknown'),
            'email': user.get('emailAddress', ''),
            'limit': int(quota.get('limit', 0)),
            'usage': int(quota.get('usage', 0)),
            'usage_in_drive': int(quota.get('usageInDrive', 0)),
            'usage_in_trash': int(quota.get('usageInDriveTrash', 0)),
            'limit_gb': int(quota.get('limit', 0)) / (1024**3),
            'usage_gb': int(quota.get('usage', 0)) / (1024**3),
            'free_gb': (int(quota.get('limit', 0)) - int(quota.get('usage', 0))) / (1024**3),
        }


# CLI for testing
if __name__ == '__main__':
    import fire

    class CLI:
        """GDrive Client CLI."""

        def __init__(self):
            self.client = GDriveClient()

        def quota(self):
            """Show storage quota."""
            q = self.client.get_storage_quota()
            print(f"User: {q['user']} ({q['email']})")
            print(f"Storage: {q['usage_gb']:.2f} GB / {q['limit_gb']:.2f} GB")
            print(f"Free: {q['free_gb']:.2f} GB")

        def ls(self, path: str = '/'):
            """List folder contents."""
            folder = self.client.get_folder_by_path(path)
            if not folder:
                print(f"Folder not found: {path}")
                return

            files = self.client.list_folder(folder.id)
            for f in files:
                prefix = 'd' if f.mime_type == GDriveClient.FOLDER_MIME else 'f'
                size = f"{f.size:,}" if f.size else '-'
                print(f"[{prefix}] {f.name:40} {size:>15}")

        def search(self, query: str):
            """Search for files."""
            files = self.client.search(query)
            for f in files:
                print(f"{f.name} ({f.id})")

        def pdfs(self):
            """List all PDFs."""
            files = self.client.list_pdfs()
            print(f"Found {len(files)} PDFs:")
            for f in files:
                size_mb = f.size / (1024*1024) if f.size else 0
                print(f"  {f.name} ({size_mb:.1f} MB)")

        def download(self, file_id: str, dest: str):
            """Download a file."""
            path = self.client.download_file(file_id, Path(dest))
            print(f"Downloaded to: {path}")

        def mkdir(self, path: str):
            """Create folder path."""
            folder = self.client.ensure_folder_path(path)
            print(f"Created/exists: {folder.name} ({folder.id})")

    fire.Fire(CLI)
