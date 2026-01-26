#!/usr/bin/env python3
"""
Session Briefing Hook

Loads essential documents into context on session start.
Outputs condensed briefing to be injected into Claude's context.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent

def read_truncated(filepath: Path, max_lines: int = 50) -> str:
    """Read file, truncate to max lines."""
    try:
        lines = filepath.read_text(encoding='utf-8', errors='ignore').split('\n')
        if len(lines) > max_lines:
            return '\n'.join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"
        return '\n'.join(lines)
    except Exception:
        return ""


def extract_current_status(evolution_plan: str) -> str:
    """Extract just the Current Status section from evolution plan."""
    lines = evolution_plan.split('\n')
    in_status = False
    status_lines = []

    for line in lines:
        if '## Current Status' in line:
            in_status = True
            status_lines.append(line)
            continue
        if in_status:
            if line.startswith('## ') and 'Current Status' not in line:
                break
            status_lines.append(line)

    return '\n'.join(status_lines) if status_lines else ""


def extract_task_summary(task_md: str) -> str:
    """Extract objective and status from task.md."""
    lines = task_md.split('\n')
    summary_lines = []
    line_count = 0

    for line in lines:
        summary_lines.append(line)
        line_count += 1
        if line_count > 60:  # First 60 lines
            summary_lines.append("... (truncated)")
            break

    return '\n'.join(summary_lines)


def get_pending_tasks() -> str:
    """Get pending tasks from task generator."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "daemon"))
        from task_generator import TaskGenerator
        gen = TaskGenerator()
        pending = gen.get_pending_tasks(limit=5)
        if pending:
            return "Pending auto-generated tasks:\n" + '\n'.join([f"- {t['description'][:80]}" for t in pending])
    except Exception:
        pass
    return ""


def main():
    output = {"continue": True}
    briefing_parts = []

    # 1. Evolution Plan - Current Status only
    evolution_path = PROJECT_ROOT / "EVOLUTION-PLAN.md"
    if evolution_path.exists():
        content = evolution_path.read_text(encoding='utf-8', errors='ignore')
        status = extract_current_status(content)
        if status:
            briefing_parts.append("=== EVOLUTION STATUS ===\n" + status)

    # 2. Task.md - Summary
    task_path = PROJECT_ROOT / "task.md"
    if task_path.exists():
        content = task_path.read_text(encoding='utf-8', errors='ignore')
        summary = extract_task_summary(content)
        if summary:
            briefing_parts.append("=== CURRENT TASK ===\n" + summary)

    # 3. Latest handoff (if exists)
    handoffs_dir = PROJECT_ROOT / "thoughts" / "handoffs"
    if handoffs_dir.exists():
        files = sorted(handoffs_dir.glob("*.yaml"), key=lambda f: f.stat().st_mtime, reverse=True)
        if files:
            latest = files[0]
            content = read_truncated(latest, 30)
            briefing_parts.append(f"=== LATEST HANDOFF ({latest.name}) ===\n" + content)

    # 4. Capability counts
    caps_path = PROJECT_ROOT / ".claude" / "config" / "capabilities.json"
    if caps_path.exists():
        try:
            with open(caps_path) as f:
                caps = json.load(f)
            briefing_parts.append(
                f"=== CAPABILITIES LOADED ===\n"
                f"Agents: {caps['counts']['agents']} | Skills: {caps['counts']['skills']} | "
                f"Rules: {caps['counts']['rules']} | Hooks: {caps['counts']['hooks']}"
            )
        except Exception:
            pass

    # 5. Pending tasks
    pending = get_pending_tasks()
    if pending:
        briefing_parts.append("=== PENDING TASKS ===\n" + pending)

    # Compose output
    if briefing_parts:
        output["message"] = "\n\n".join(briefing_parts)

    print(json.dumps(output))


if __name__ == "__main__":
    main()
