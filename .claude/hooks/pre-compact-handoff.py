#!/usr/bin/env python3
"""PreCompact hook - auto-saves state before context compaction.

When context is about to be compacted, saves current state to handoff.
Based on Continuous-Claude pattern.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime


def main():
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        project_dir = os.getcwd()

    handoffs_dir = Path(project_dir) / "thoughts" / "handoffs"
    handoffs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    handoff_file = handoffs_dir / f"{timestamp}_pre-compact.yaml"

    # Check for dirty files
    dirty_file = Path(project_dir) / ".claude" / "auto-memory" / "dirty-files"
    modified_files = []
    if dirty_file.exists():
        with open(dirty_file) as f:
            modified_files = [line.strip() for line in f if line.strip()]

    # Check for task.md
    task_file = Path(project_dir) / "task.md"
    current_task = ""
    if task_file.exists():
        current_task = task_file.read_text()[:500]  # First 500 chars

    # Create handoff
    handoff_content = f"""---
date: {datetime.now().isoformat()}
type: pre-compact
status: auto-saved
---

# Pre-Compact Handoff

## Trigger
Context was about to be compacted. This handoff preserves state.

## Modified Files This Session
{chr(10).join(f'- {f}' for f in modified_files[:20]) if modified_files else '- None tracked'}

## Current Task
```
{current_task if current_task else 'No task.md found'}
```

## Resume Instructions
1. Check task.md for current objectives
2. Review modified files above
3. Continue where left off
"""

    handoff_file.write_text(handoff_content)

    print(f"[PreCompact] Handoff saved: {handoff_file.name}")


if __name__ == "__main__":
    main()
