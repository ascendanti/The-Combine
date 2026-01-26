#!/usr/bin/env python3
"""
Essential Docs Briefing

Outputs a concise session briefing to stdout for SessionStart context injection.
Reads task.md, EVOLUTION-PLAN.md, and latest handoff (if present) and trims
content to a configurable length.
"""

from pathlib import Path
from typing import List

MAX_LINES = 80


def read_lines(path: Path, max_lines: int) -> List[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        lines = [line.rstrip() for line in handle][:max_lines]
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

    sections.append("# Session Briefing (Auto-loaded)")

    if task_file.exists():
        sections.append("\n## task.md (current objectives)")
        sections.extend(read_lines(task_file, MAX_LINES))

    if evolution_file.exists():
        sections.append("\n## EVOLUTION-PLAN.md (current phase)")
        sections.extend(read_lines(evolution_file, MAX_LINES))

    if handoff_file and handoff_file.exists():
        sections.append(f"\n## Latest Handoff ({handoff_file.name})")
        sections.extend(read_lines(handoff_file, MAX_LINES))

    output = "\n".join(sections).strip()
    if output:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
