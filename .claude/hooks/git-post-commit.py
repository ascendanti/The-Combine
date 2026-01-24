#!/usr/bin/env python3
"""
Git Post-Commit Hook - Historian Checkpoint
Automatically creates a checkpoint after each commit.

Install: cp .claude/hooks/git-post-commit.py .git/hooks/post-commit && chmod +x .git/hooks/post-commit
"""
import subprocess
import json
from datetime import datetime
from pathlib import Path

def get_commit_info():
    """Get info about the latest commit."""
    result = subprocess.run(
        ['git', 'log', '-1', '--format=%H|%s|%an|%ae'],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None

    parts = result.stdout.strip().split('|')
    if len(parts) < 4:
        return None

    return {
        'hash': parts[0][:8],
        'message': parts[1],
        'author': parts[2],
        'email': parts[3]
    }

def get_changed_files():
    """Get files changed in the latest commit."""
    result = subprocess.run(
        ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD'],
        capture_output=True, text=True
    )
    return result.stdout.strip().split('\n') if result.returncode == 0 else []

def create_checkpoint():
    """Create a historian checkpoint."""
    commit = get_commit_info()
    if not commit:
        return

    files = get_changed_files()
    timestamp = datetime.now().isoformat()

    checkpoint = {
        'type': 'git-commit',
        'timestamp': timestamp,
        'commit': commit,
        'files_changed': files,
        'file_count': len(files)
    }

    # Save to history
    history_dir = Path(__file__).parent.parent.parent / 'thoughts' / 'history'
    history_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_file = history_dir / f"{datetime.now().strftime('%Y-%m-%d')}_commits.jsonl"
    with open(checkpoint_file, 'a') as f:
        f.write(json.dumps(checkpoint) + '\n')

    print(f"[Historian] Checkpoint: {commit['hash']} - {commit['message'][:50]}")

if __name__ == '__main__':
    create_checkpoint()
