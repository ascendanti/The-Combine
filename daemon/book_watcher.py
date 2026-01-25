#!/usr/bin/env python3
"""
Book Watcher Daemon - Auto-ingest PDFs when added to watch folder.

Features:
- Watchdog-based file monitoring
- Background processing (non-blocking)
- Deduplication (tracks ingested files)
- Integration with memory.py + knowledge graph
- Token-efficient chunking
- Queue-based processing for multiple files

Usage:
    python book_watcher.py                    # Start watcher (default folder)
    python book_watcher.py --folder /path     # Custom watch folder
    python book_watcher.py --status           # Show queue status
    python book_watcher.py --process-now      # Process pending immediately

Config:
    Set BOOK_WATCH_FOLDER env var or use --folder flag
    Default: ~/Documents/Claude-Books/
"""

import os
import sys
import io
import json
import time
import hashlib
import sqlite3
import threading

# Fix Windows encoding for Unicode filenames
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import argparse
from pathlib import Path
from datetime import datetime
from queue import Queue, Empty
from typing import Optional

# Watchdog for file system events
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    # Dummy base class when watchdog not available
    class FileSystemEventHandler:
        pass
    Observer = None

# Add project paths
DAEMON_DIR = Path(__file__).parent
PROJECT_DIR = DAEMON_DIR.parent
SCRIPTS_DIR = PROJECT_DIR / ".claude" / "scripts"
sys.path.insert(0, str(DAEMON_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

# Configuration
DEFAULT_WATCH_FOLDER = Path.home() / "Documents" / "GateofTruth"
SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.pptx', '.epub', '.html', '.md'}
WATCHER_DB = DAEMON_DIR / "book_watcher.db"
PROCESSING_QUEUE = Queue()

# ============================================================================
# Database for tracking ingested files
# ============================================================================

def init_watcher_db() -> sqlite3.Connection:
    """Initialize the watcher tracking database."""
    conn = sqlite3.connect(WATCHER_DB)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS watched_files (
        file_hash TEXT PRIMARY KEY,
        file_path TEXT,
        file_name TEXT,
        file_size INTEGER,
        detected_at TEXT,
        status TEXT,  -- pending, processing, completed, failed
        book_id TEXT,
        error_message TEXT,
        processed_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS watcher_config (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')

    c.execute('''CREATE INDEX IF NOT EXISTS idx_status ON watched_files(status)''')

    conn.commit()
    return conn

def get_file_hash(file_path: Path) -> str:
    """Generate hash from file path + size + mtime for deduplication."""
    stat = file_path.stat()
    content = f"{file_path.absolute()}:{stat.st_size}:{stat.st_mtime}"
    return hashlib.md5(content.encode()).hexdigest()[:16]

def is_already_tracked(conn: sqlite3.Connection, file_hash: str) -> bool:
    """Check if file is already in the tracking database."""
    c = conn.cursor()
    c.execute('SELECT status FROM watched_files WHERE file_hash = ?', (file_hash,))
    row = c.fetchone()
    return row is not None

def track_file(conn: sqlite3.Connection, file_path: Path, status: str = "pending"):
    """Add file to tracking database."""
    file_hash = get_file_hash(file_path)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO watched_files
        (file_hash, file_path, file_name, file_size, detected_at, status)
        VALUES (?, ?, ?, ?, ?, ?)''',
        (file_hash, str(file_path), file_path.name, file_path.stat().st_size,
         datetime.now().isoformat(), status))
    conn.commit()
    return file_hash

def update_file_status(conn: sqlite3.Connection, file_hash: str,
                       status: str, book_id: str = None, error: str = None):
    """Update processing status of a tracked file."""
    c = conn.cursor()
    c.execute('''UPDATE watched_files
        SET status = ?, book_id = ?, error_message = ?, processed_at = ?
        WHERE file_hash = ?''',
        (status, book_id, error, datetime.now().isoformat(), file_hash))
    conn.commit()

# ============================================================================
# File System Event Handler
# ============================================================================

class BookFileHandler(FileSystemEventHandler):
    """Handler for file system events in the watch folder."""

    def __init__(self, conn: sqlite3.Connection, process_queue: Queue):
        self.conn = conn
        self.queue = process_queue
        super().__init__()

    def _handle_new_file(self, file_path: Path):
        """Process a newly detected file."""
        # Check extension
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return

        # Skip if already tracked
        file_hash = get_file_hash(file_path)
        if is_already_tracked(self.conn, file_hash):
            print(f"  [skip] Already tracked: {file_path.name}")
            return

        # Track and queue for processing
        track_file(self.conn, file_path, "pending")
        self.queue.put((file_hash, file_path))
        print(f"  [queued] New book detected: {file_path.name}")

    def on_created(self, event):
        """Called when a file is created."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Wait a moment for file to be fully written
        time.sleep(1)

        if file_path.exists():
            self._handle_new_file(file_path)

    def on_moved(self, event):
        """Called when a file is moved into the folder."""
        if event.is_directory:
            return

        file_path = Path(event.dest_path)
        if file_path.exists():
            self._handle_new_file(file_path)

# ============================================================================
# Background Processor
# ============================================================================

class BackgroundProcessor(threading.Thread):
    """Background thread that processes queued books."""

    def __init__(self, conn: sqlite3.Connection, process_queue: Queue):
        super().__init__(daemon=True)
        self.conn = conn
        self.queue = process_queue
        self.running = True

    def run(self):
        """Main processing loop."""
        print("[processor] Background processor started")

        while self.running:
            try:
                # Wait for item with timeout (allows clean shutdown)
                file_hash, file_path = self.queue.get(timeout=5)
                self._process_file(file_hash, file_path)
                self.queue.task_done()
            except Empty:
                continue
            except Exception as e:
                print(f"[processor] Error: {e}")

    def _process_file(self, file_hash: str, file_path: Path):
        """Process a single file."""
        print(f"\n[processor] Processing: {file_path.name}")
        update_file_status(self.conn, file_hash, "processing")

        try:
            # Import book ingestion (lazy load to avoid circular imports)
            from book_ingest import ingest_book

            # Run ingestion
            result = ingest_book(str(file_path))

            if result.get("success"):
                update_file_status(self.conn, file_hash, "completed",
                                   book_id=result.get("book_id"))
                print(f"[processor] DONE: {file_path.name} -> {result.get('book_id')}")

                # Store in memory system
                self._add_to_memory(file_path, result)
            else:
                update_file_status(self.conn, file_hash, "failed",
                                   error=result.get("error", "Unknown error"))
                print(f"[processor] FAIL: {file_path.name}")

        except Exception as e:
            update_file_status(self.conn, file_hash, "failed", error=str(e))
            print(f"[processor] ERROR: {e}")

    def _add_to_memory(self, file_path: Path, result: dict):
        """Add ingestion record to memory system."""
        try:
            from memory import Memory
            mem = Memory()
            mem.add(
                f"Ingested book: {file_path.name}. "
                f"Book ID: {result.get('book_id')}. "
                f"Chunks: {result.get('chunks')}. "
                f"Concepts: {result.get('concepts')}.",
                metadata={
                    "type": "book_ingestion",
                    "book_id": result.get("book_id"),
                    "file": str(file_path)
                }
            )
        except Exception as e:
            print(f"[memory] Warning: Could not add to memory: {e}")

    def stop(self):
        """Signal processor to stop."""
        self.running = False

# ============================================================================
# Folder Scanner (for existing files)
# ============================================================================

def scan_existing_files(folder: Path, conn: sqlite3.Connection, queue: Queue) -> int:
    """Scan folder for existing files not yet processed."""
    count = 0

    for ext in SUPPORTED_EXTENSIONS:
        for file_path in folder.glob(f"**/*{ext}"):
            file_hash = get_file_hash(file_path)
            if not is_already_tracked(conn, file_hash):
                track_file(conn, file_path, "pending")
                queue.put((file_hash, file_path))
                count += 1
                print(f"  [scan] Found: {file_path.name}")

    return count

# ============================================================================
# Status and Management
# ============================================================================

def get_status(conn: sqlite3.Connection) -> dict:
    """Get current watcher status."""
    c = conn.cursor()

    status = {"files": {}, "queue_size": PROCESSING_QUEUE.qsize()}

    for state in ["pending", "processing", "completed", "failed"]:
        c.execute('SELECT COUNT(*) FROM watched_files WHERE status = ?', (state,))
        status["files"][state] = c.fetchone()[0]

    # Recent files
    c.execute('''SELECT file_name, status, processed_at
        FROM watched_files ORDER BY detected_at DESC LIMIT 10''')
    status["recent"] = [{"name": r[0], "status": r[1], "processed": r[2]}
                        for r in c.fetchall()]

    return status

def process_pending_now(conn: sqlite3.Connection):
    """Immediately process all pending files."""
    c = conn.cursor()
    c.execute('SELECT file_hash, file_path FROM watched_files WHERE status = ?', ("pending",))

    pending = c.fetchall()
    print(f"Processing {len(pending)} pending files...")

    for file_hash, file_path in pending:
        file_path = Path(file_path)
        if file_path.exists():
            PROCESSING_QUEUE.put((file_hash, file_path))

# ============================================================================
# Main Watcher
# ============================================================================

def start_watcher(watch_folder: Path):
    """Start the book watcher daemon."""
    if not WATCHDOG_AVAILABLE:
        print("Error: watchdog not installed. Run: pip install watchdog")
        sys.exit(1)

    # Ensure folder exists
    watch_folder.mkdir(parents=True, exist_ok=True)

    print(f"""
========================================
  Book Watcher Daemon
========================================
  Watching: {str(watch_folder)[:45]}
  Extensions: {', '.join(SUPPORTED_EXTENSIONS)}
  Database: {str(WATCHER_DB.name)}
========================================
    """)

    # Initialize
    conn = init_watcher_db()

    # Scan for existing files
    print("[startup] Scanning for existing files...")
    found = scan_existing_files(watch_folder, conn, PROCESSING_QUEUE)
    print(f"[startup] Found {found} new files to process")

    # Start background processor
    processor = BackgroundProcessor(conn, PROCESSING_QUEUE)
    processor.start()

    # Set up watchdog observer
    event_handler = BookFileHandler(conn, PROCESSING_QUEUE)
    observer = Observer()
    observer.schedule(event_handler, str(watch_folder), recursive=True)
    observer.start()

    print("[watcher] Watching for new files... (Ctrl+C to stop)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[shutdown] Stopping watcher...")
        observer.stop()
        processor.stop()

    observer.join()
    processor.join(timeout=5)
    conn.close()
    print("[shutdown] Watcher stopped")

# ============================================================================
# CLI Interface
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Book Watcher Daemon')
    parser.add_argument('--folder', type=Path,
                        default=os.environ.get('BOOK_WATCH_FOLDER', DEFAULT_WATCH_FOLDER),
                        help='Folder to watch for new books')
    parser.add_argument('--status', action='store_true', help='Show watcher status')
    parser.add_argument('--process-now', action='store_true',
                        help='Process all pending files immediately')
    parser.add_argument('--list-books', action='store_true',
                        help='List all tracked books')

    args = parser.parse_args()

    if args.status:
        conn = init_watcher_db()
        status = get_status(conn)
        print(json.dumps(status, indent=2))
        conn.close()
    elif args.process_now:
        conn = init_watcher_db()
        process_pending_now(conn)
        # Start processor briefly
        processor = BackgroundProcessor(conn, PROCESSING_QUEUE)
        processor.start()
        PROCESSING_QUEUE.join()  # Wait for completion
        processor.stop()
        conn.close()
    elif args.list_books:
        conn = init_watcher_db()
        c = conn.cursor()
        c.execute('''SELECT file_name, status, book_id, processed_at
            FROM watched_files ORDER BY detected_at DESC''')
        print("\nTracked Books:")
        print("-" * 70)
        for row in c.fetchall():
            status_icon = {"completed": "+", "failed": "x", "pending": "o", "processing": "*"}.get(row[1], "?")
            print(f"  {status_icon} {row[0][:40]:<40} [{row[2] or 'N/A'}]")
        conn.close()
    else:
        start_watcher(Path(args.folder))

if __name__ == "__main__":
    main()
