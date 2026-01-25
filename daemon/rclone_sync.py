#!/usr/bin/env python3
"""
Rclone Sync - Delta-efficient sync between local and Google Drive.

Uses rclone for proven delta handling without mounting.

Usage:
    python rclone_sync.py inbox     # Sync PDFs from Drive inbox to local
    python rclone_sync.py models    # Sync models from Drive to local
    python rclone_sync.py backup    # Backup handoffs/embeddings to Drive
    python rclone_sync.py full      # Run all syncs
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Rclone path
RCLONE = Path.home() / "AppData/Local/Microsoft/WinGet/Links/rclone.exe"
if not RCLONE.exists():
    RCLONE = Path("rclone")  # Assume on PATH

# Local paths
LOCAL_GATE_OF_TRUTH = Path(r"C:\Users\New Employee\Documents\GateofTruth")
LOCAL_MODELS = Path(r"C:\Users\New Employee\.atlas\models")
LOCAL_HANDOFFS = Path(r"C:\Users\New Employee\Downloads\Atlas-OS-main\Claude n8n\thoughts\handoffs")
LOCAL_DAEMON = Path(r"C:\Users\New Employee\Downloads\Atlas-OS-main\Claude n8n\daemon")

# Drive remotes (defined in rclone.conf)
REMOTE_INBOX = "atlas:Inbox/PDFs"
REMOTE_MODELS = "atlas:Models"
REMOTE_HANDOFFS = "atlas:Backup/Handoffs"
REMOTE_EMBEDDINGS = "atlas:Cache/Embeddings"


def run_rclone(args: List[str], dry_run: bool = False) -> Dict:
    """Run rclone command and return result."""
    cmd = [str(RCLONE)] + args
    if dry_run:
        cmd.append("--dry-run")

    cmd.extend([
        "--progress",
        "--stats-one-line",
        "-v"
    ])

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    return {
        "success": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "command": " ".join(cmd)
    }


def sync_inbox_to_local(dry_run: bool = False) -> Dict:
    """
    Sync PDFs from Drive inbox to local GateofTruth.
    Only copies new files (delta sync).
    """
    LOCAL_GATE_OF_TRUTH.mkdir(parents=True, exist_ok=True)

    result = run_rclone([
        "copy",
        REMOTE_INBOX,
        str(LOCAL_GATE_OF_TRUTH),
        "--include", "*.pdf",
        "--ignore-existing"  # Don't re-download existing files
    ], dry_run)

    return {
        "operation": "inbox_to_local",
        "source": REMOTE_INBOX,
        "dest": str(LOCAL_GATE_OF_TRUTH),
        **result
    }


def sync_models_to_local(model_name: str = None, dry_run: bool = False) -> Dict:
    """
    Sync LLM models from Drive to local.
    Optionally specify a specific model to download.
    """
    LOCAL_MODELS.mkdir(parents=True, exist_ok=True)

    args = [
        "copy",
        REMOTE_MODELS,
        str(LOCAL_MODELS),
    ]

    if model_name:
        args.extend(["--include", f"*{model_name}*"])

    result = run_rclone(args, dry_run)

    return {
        "operation": "models_to_local",
        "source": REMOTE_MODELS,
        "dest": str(LOCAL_MODELS),
        "model_filter": model_name,
        **result
    }


def backup_handoffs_to_drive(dry_run: bool = False) -> Dict:
    """
    Backup local handoffs to Drive.
    Uses copy (not sync) to preserve Drive history.
    """
    if not LOCAL_HANDOFFS.exists():
        return {"operation": "backup_handoffs", "error": "Handoffs directory not found"}

    result = run_rclone([
        "copy",
        str(LOCAL_HANDOFFS),
        REMOTE_HANDOFFS,
        "--include", "*.yaml",
        "--ignore-existing"
    ], dry_run)

    return {
        "operation": "backup_handoffs",
        "source": str(LOCAL_HANDOFFS),
        "dest": REMOTE_HANDOFFS,
        **result
    }


def backup_embeddings_to_drive(dry_run: bool = False) -> Dict:
    """
    Backup embedding databases to Drive with timestamp.
    """
    timestamp = datetime.now().strftime("%Y%m%d")

    results = []
    db_files = ["utf_knowledge.db", "synthesis.db", "router.db", "books.db"]

    for db_file in db_files:
        local_path = LOCAL_DAEMON / db_file
        if local_path.exists():
            # Copy with timestamp in name
            dest_name = f"{local_path.stem}_{timestamp}{local_path.suffix}"
            result = run_rclone([
                "copyto",
                str(local_path),
                f"{REMOTE_EMBEDDINGS}/{dest_name}"
            ], dry_run)
            results.append({
                "file": db_file,
                "dest": dest_name,
                **result
            })

    return {
        "operation": "backup_embeddings",
        "results": results
    }


def list_remote(remote: str) -> Dict:
    """List files in a remote location."""
    result = run_rclone(["lsf", remote, "--format", "pst"])
    if result["success"]:
        lines = result["stdout"].strip().split("\n") if result["stdout"].strip() else []
        files = []
        for line in lines:
            if line:
                parts = line.split(";")
                if len(parts) >= 3:
                    files.append({
                        "path": parts[0],
                        "size": parts[1],
                        "time": parts[2]
                    })
        return {"success": True, "files": files}
    return result


def full_sync(dry_run: bool = False) -> Dict:
    """Run all sync operations."""
    results = {
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "operations": []
    }

    print("=== Syncing inbox PDFs from Drive ===")
    results["operations"].append(sync_inbox_to_local(dry_run))

    print("\n=== Backing up handoffs to Drive ===")
    results["operations"].append(backup_handoffs_to_drive(dry_run))

    print("\n=== Backing up embeddings to Drive ===")
    results["operations"].append(backup_embeddings_to_drive(dry_run))

    # Count successes
    successes = sum(1 for op in results["operations"]
                    if op.get("success") or (isinstance(op.get("results"), list) and
                                             all(r.get("success") for r in op["results"])))
    results["summary"] = f"{successes}/{len(results['operations'])} operations successful"

    return results


# CLI
if __name__ == "__main__":
    import fire

    class CLI:
        """Rclone Sync CLI."""

        def inbox(self, dry_run: bool = False):
            """Sync PDFs from Drive inbox to local GateofTruth."""
            result = sync_inbox_to_local(dry_run)
            print(f"\nResult: {'OK' if result['success'] else 'FAILED'}")
            if result.get("stderr"):
                print(result["stderr"][-500:])

        def models(self, name: str = None, dry_run: bool = False):
            """Sync models from Drive to local."""
            result = sync_models_to_local(name, dry_run)
            print(f"\nResult: {'OK' if result['success'] else 'FAILED'}")

        def backup(self, dry_run: bool = False):
            """Backup handoffs and embeddings to Drive."""
            print("=== Handoffs ===")
            backup_handoffs_to_drive(dry_run)
            print("\n=== Embeddings ===")
            backup_embeddings_to_drive(dry_run)

        def full(self, dry_run: bool = False):
            """Run full sync (all operations)."""
            result = full_sync(dry_run)
            print(f"\n{result['summary']}")

        def ls(self, path: str = ""):
            """List files at remote path."""
            remote = f"atlas:{path}" if path else "atlas:"
            result = list_remote(remote)
            if result.get("files"):
                for f in result["files"]:
                    print(f"{f['size']:>12}  {f['time']}  {f['path']}")
            elif result.get("success"):
                print("(empty)")
            else:
                print(f"Error: {result.get('stderr', 'Unknown')}")

        def size(self):
            """Show size of atlas remote."""
            result = run_rclone(["size", "atlas:"])
            print(result["stdout"] if result["success"] else result["stderr"])

    fire.Fire(CLI)
