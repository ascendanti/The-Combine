#!/usr/bin/env python3
"""
Essential Docs Briefing

Outputs a concise session briefing for SessionStart context injection.
Reads task.md, EVOLUTION-PLAN.md (current status only), and latest handoff.
Outputs JSON for hook compatibility.
"""

import json
from pathlib import Path
from typing import List

MAX_LINES_TASK = 60
MAX_LINES_HANDOFF = 30


def read_lines(path: Path, max_lines: int) -> List[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        lines = [line.rstrip() for line in handle][:max_lines]
    return lines


def extract_current_status(path: Path) -> List[str]:
    """Extract only the Current Status section from EVOLUTION-PLAN.md"""
    if not path.exists():
        return []
    lines = []
    in_status = False
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            stripped = line.rstrip()
            if "## Current Status" in stripped:
                in_status = True
                lines.append(stripped)
                continue
            if in_status:
                if stripped.startswith("## ") and "Current Status" not in stripped:
                    break
                lines.append(stripped)
                if len(lines) > 30:
                    lines.append("... (truncated)")
                    break
    return lines


def latest_handoff(handoff_dir: Path) -> Path:
    if not handoff_dir.exists():
        return Path()
    candidates = [p for p in handoff_dir.iterdir() if p.is_file()]
    if not candidates:
        return Path()
    return max(candidates, key=lambda p: p.stat().st_mtime)


def main() -> int:
    project_root = Path.cwd()
    task_file = project_root / "task.md"
    evolution_file = project_root / "EVOLUTION-PLAN.md"
    handoff_file = latest_handoff(project_root / "thoughts" / "handoffs")

    sections: List[str] = []

    # Task.md - current objectives (condensed)
    if task_file.exists():
        sections.append("=== CURRENT TASK ===")
        sections.extend(read_lines(task_file, MAX_LINES_TASK))

    # Evolution Plan - current status only (not full file)
    if evolution_file.exists():
        status_lines = extract_current_status(evolution_file)
        if status_lines:
            sections.append("\n=== EVOLUTION STATUS ===")
            sections.extend(status_lines)

    # Latest handoff
    if handoff_file and handoff_file.exists():
        sections.append(f"\n=== LATEST HANDOFF ({handoff_file.name}) ===")
        sections.extend(read_lines(handoff_file, MAX_LINES_HANDOFF))

    # Output JSON for hook compatibility
    output = {
        "continue": True,
        "stopReason": None
    }

    briefing = "\n".join(sections).strip()
    if briefing:
        output["message"] = briefing

    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
