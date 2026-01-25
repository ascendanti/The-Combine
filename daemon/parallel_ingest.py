#!/usr/bin/env python3
"""
Parallel PDF Ingestion - Multi-process text extraction with queued LLM processing.

Optimizes throughput by:
1. Parallel text extraction (CPU-bound, can parallelize)
2. Parallel chunking and preprocessing
3. Sequential LLM calls (LocalAI bottleneck)
4. Parallel post-processing and storage

Usage:
    python parallel_ingest.py                    # Process all pending
    python parallel_ingest.py --workers 4        # Use 4 parallel workers
    python parallel_ingest.py --status           # Show queue status
"""

import os
import sys
import json
import hashlib
import sqlite3
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from queue import Queue
import threading
import time

# Import extraction modules
try:
    from markitdown import MarkItDown
    MARKITDOWN_AVAILABLE = True
except ImportError:
    MARKITDOWN_AVAILABLE = False

try:
    from utf_extractor import extract_utf_schema, export_to_obsidian
    UTF_AVAILABLE = True
except ImportError:
    UTF_AVAILABLE = False

# Configuration
WATCH_FOLDER = Path(os.environ.get("BOOK_WATCH_FOLDER", str(Path.home() / "Documents" / "GateofTruth")))
LOCALAI_URL = os.environ.get("LOCALAI_URL", "http://localhost:8080/v1")
DB_PATH = Path(__file__).parent / "parallel_ingest.db"
OBSIDIAN_VAULT = Path(os.environ.get("OBSIDIAN_VAULT", str(Path.home() / "Documents" / "Obsidian" / "ClaudeKnowledge")))
MAX_WORKERS = int(os.environ.get("INGEST_WORKERS", "4"))

SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.md', '.docx', '.pptx', '.html', '.epub'}

# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class PreprocessedDoc:
    """Document after text extraction (before LLM processing)."""
    file_path: str
    file_hash: str
    text: str
    char_count: int
    extraction_method: str
    preprocessed_at: str

@dataclass
class ProcessingResult:
    """Result of full document processing."""
    file_path: str
    file_hash: str
    success: bool
    claims_count: int
    concepts_count: int
    error: Optional[str] = None
    processed_at: str = ""

# ============================================================================
# Database
# ============================================================================

def init_db():
    """Initialize parallel ingest database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS preprocessing_queue (
            file_hash TEXT PRIMARY KEY,
            file_path TEXT,
            status TEXT DEFAULT 'pending',
            text TEXT,
            char_count INTEGER,
            queued_at TEXT,
            preprocessed_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processing_results (
            file_hash TEXT PRIMARY KEY,
            file_path TEXT,
            success INTEGER,
            claims_count INTEGER,
            concepts_count INTEGER,
            error TEXT,
            processed_at TEXT
        )
    """)

    conn.commit()
    conn.close()

def get_pending_files() -> List[Path]:
    """Get files that haven't been processed yet."""
    if not WATCH_FOLDER.exists():
        return []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT file_hash FROM processing_results WHERE success = 1")
    processed_hashes = {row[0] for row in cursor.fetchall()}
    conn.close()

    pending = []
    for ext in SUPPORTED_EXTENSIONS:
        for file_path in WATCH_FOLDER.glob(f"*{ext}"):
            file_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]
            if file_hash not in processed_hashes:
                pending.append(file_path)

    return pending

# ============================================================================
# Parallel Text Extraction (Phase 1)
# ============================================================================

def extract_text_from_file(file_path: Path) -> PreprocessedDoc:
    """Extract text from a single file (can run in parallel)."""
    file_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]

    text = ""
    method = "unknown"

    # Try MarkItDown first
    if MARKITDOWN_AVAILABLE:
        try:
            md = MarkItDown()
            result = md.convert(str(file_path))
            text = result.text_content
            method = "markitdown"
        except Exception as e:
            pass

    # Fallback to PyMuPDF for PDFs
    if not text and file_path.suffix.lower() == '.pdf':
        try:
            import fitz
            doc = fitz.open(file_path)
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            method = "pymupdf"
        except Exception as e:
            pass

    # Fallback to plain read for text files
    if not text and file_path.suffix.lower() in {'.txt', '.md'}:
        try:
            text = file_path.read_text(encoding='utf-8', errors='ignore')
            method = "plaintext"
        except:
            pass

    return PreprocessedDoc(
        file_path=str(file_path),
        file_hash=file_hash,
        text=text,
        char_count=len(text),
        extraction_method=method,
        preprocessed_at=datetime.now().isoformat()
    )

def parallel_extract_texts(files: List[Path], max_workers: int = MAX_WORKERS) -> List[PreprocessedDoc]:
    """Extract text from multiple files in parallel."""
    results = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(extract_text_from_file, f): f for f in files}

        for future in as_completed(futures):
            file_path = futures[future]
            try:
                result = future.result()
                results.append(result)
                print(f"  [OK] Extracted: {file_path.name} ({result.char_count} chars)")
            except Exception as e:
                print(f"  [ERR] Failed: {file_path.name} - {e}")

    return results

# ============================================================================
# Sequential LLM Processing (Phase 2 - Bottleneck)
# ============================================================================

def process_with_llm(doc: PreprocessedDoc) -> ProcessingResult:
    """Process document with LLM (sequential due to LocalAI bottleneck)."""
    if not doc.text:
        return ProcessingResult(
            file_path=doc.file_path,
            file_hash=doc.file_hash,
            success=False,
            claims_count=0,
            concepts_count=0,
            error="No text extracted",
            processed_at=datetime.now().isoformat()
        )

    try:
        if UTF_AVAILABLE:
            result = extract_utf_schema(doc.text, doc.file_hash, classify=True)

            # Export to Obsidian
            if result.quality_gate_passed:
                export_to_obsidian(result, OBSIDIAN_VAULT)

            return ProcessingResult(
                file_path=doc.file_path,
                file_hash=doc.file_hash,
                success=True,
                claims_count=len(result.claims),
                concepts_count=len(result.concepts),
                processed_at=datetime.now().isoformat()
            )
        else:
            return ProcessingResult(
                file_path=doc.file_path,
                file_hash=doc.file_hash,
                success=False,
                claims_count=0,
                concepts_count=0,
                error="UTF extractor not available",
                processed_at=datetime.now().isoformat()
            )
    except Exception as e:
        return ProcessingResult(
            file_path=doc.file_path,
            file_hash=doc.file_hash,
            success=False,
            claims_count=0,
            concepts_count=0,
            error=str(e),
            processed_at=datetime.now().isoformat()
        )

def save_result(result: ProcessingResult):
    """Save processing result to database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO processing_results
        (file_hash, file_path, success, claims_count, concepts_count, error, processed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        result.file_hash, result.file_path, 1 if result.success else 0,
        result.claims_count, result.concepts_count, result.error, result.processed_at
    ))
    conn.commit()
    conn.close()

# ============================================================================
# Orchestrator
# ============================================================================

def run_parallel_ingest(max_workers: int = MAX_WORKERS, batch_size: int = 10):
    """Run parallel ingestion pipeline."""
    init_db()

    print("=" * 60)
    print("Parallel PDF Ingestion")
    print("=" * 60)
    print(f"Watch folder: {WATCH_FOLDER}")
    print(f"Workers: {max_workers}")
    print(f"Batch size: {batch_size}")
    print()

    pending_files = get_pending_files()
    print(f"Found {len(pending_files)} pending files")

    if not pending_files:
        print("No files to process")
        return

    total_claims = 0
    total_concepts = 0
    processed = 0

    # Process in batches
    for i in range(0, len(pending_files), batch_size):
        batch = pending_files[i:i+batch_size]
        print(f"\n--- Batch {i//batch_size + 1} ({len(batch)} files) ---")

        # Phase 1: Parallel text extraction
        print("\n[Phase 1] Parallel text extraction...")
        preprocessed = parallel_extract_texts(batch, max_workers)

        # Phase 2: Sequential LLM processing (bottleneck)
        print("\n[Phase 2] LLM processing (sequential)...")
        for doc in preprocessed:
            if doc.text:
                print(f"  Processing: {Path(doc.file_path).name}...")
                result = process_with_llm(doc)
                save_result(result)

                if result.success:
                    processed += 1
                    total_claims += result.claims_count
                    total_concepts += result.concepts_count
                    print(f"    [OK] {result.claims_count} claims, {result.concepts_count} concepts")
                else:
                    print(f"    [ERR] {result.error}")

        # Progress update
        print(f"\n  Batch complete: {processed}/{len(pending_files)} processed")
        print(f"  Running totals: {total_claims} claims, {total_concepts} concepts")

    print("\n" + "=" * 60)
    print(f"COMPLETE: {processed} files, {total_claims} claims, {total_concepts} concepts")
    print("=" * 60)

def get_status() -> Dict[str, Any]:
    """Get current processing status."""
    init_db()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM processing_results WHERE success = 1")
    successful = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM processing_results WHERE success = 0")
    failed = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(claims_count), SUM(concepts_count) FROM processing_results WHERE success = 1")
    row = cursor.fetchone()
    total_claims = row[0] or 0
    total_concepts = row[1] or 0

    conn.close()

    pending = len(get_pending_files())

    return {
        "pending": pending,
        "successful": successful,
        "failed": failed,
        "total_claims": total_claims,
        "total_concepts": total_concepts
    }

# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Parallel PDF Ingestion")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS, help="Number of parallel workers")
    parser.add_argument("--batch", type=int, default=10, help="Batch size")
    parser.add_argument("--status", action="store_true", help="Show status")

    args = parser.parse_args()

    if args.status:
        status = get_status()
        print("\nParallel Ingest Status:")
        print(f"  Pending: {status['pending']}")
        print(f"  Successful: {status['successful']}")
        print(f"  Failed: {status['failed']}")
        print(f"  Total claims: {status['total_claims']}")
        print(f"  Total concepts: {status['total_concepts']}")
    else:
        run_parallel_ingest(args.workers, args.batch)

if __name__ == "__main__":
    main()
