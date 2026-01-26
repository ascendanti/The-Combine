#!/usr/bin/env python3
"""
Session Briefing Hook - Token-Efficient Version

Outputs MINIMAL briefing on session start.
Follows context engineering principles:
- Just-in-time context loading (pointers over content)
- Minimal footprint (identifiers, not full text)
- Progressive disclosure (load on demand)
"""

import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent

# Hard limits for token efficiency
MAX_TASK_LINES = 20  # Reduced from 60
MAX_STATUS_LINES = 15  # Just the highlights


def extract_phase_and_progress(evolution_path: Path) -> str:
    """Extract ONLY phase number and key metrics, not full status."""
    if not evolution_path.exists():
        return ""
    try:
        content = evolution_path.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')

        # Find current phase
        phase_line = ""
        in_progress_count = 0
        for line in lines:
            if 'Phase' in line and ('IN PROGRESS' in line or 'COMPLETE' in line):
                phase_line = line.strip()
            if 'IN PROGRESS' in line:
                in_progress_count += 1

        if phase_line:
            return f"{phase_line} | {in_progress_count} active items"
        return ""
    except Exception:
        return ""


def extract_task_objective(task_path: Path) -> str:
    """Extract just objective + current focus, not full task."""
    if not task_path.exists():
        return ""
    try:
        lines = task_path.read_text(encoding='utf-8', errors='ignore').split('\n')
        result = []
        line_count = 0

        for line in lines:
            result.append(line)
            line_count += 1
            # Stop at first section break after getting header
            if line_count > MAX_TASK_LINES:
                break
            if line_count > 5 and line.startswith('## '):
                break

        return '\n'.join(result).strip()
    except Exception:
        return ""


def get_handoff_pointer() -> str:
    """Return pointer to latest handoff, not content."""
    handoffs_dir = PROJECT_ROOT / "thoughts" / "handoffs"
    if not handoffs_dir.exists():
        return ""

    files = sorted(handoffs_dir.glob("*.yaml"), key=lambda f: f.stat().st_mtime, reverse=True)
    if files:
        latest = files[0]
        age_hours = (datetime.now().timestamp() - latest.stat().st_mtime) / 3600
        return f"Latest: {latest.name} ({age_hours:.0f}h ago) - Read if resuming work"
    return ""


def get_capability_summary() -> str:
    """One-line capability count."""
    caps_path = PROJECT_ROOT / ".claude" / "config" / "capabilities.json"
    if not caps_path.exists():
        return ""
    try:
        with open(caps_path) as f:
            caps = json.load(f)
        c = caps['counts']
        return f"A:{c['agents']} S:{c['skills']} R:{c['rules']} H:{c['hooks']}"
    except Exception:
        return ""


def main():
    output = {"continue": True}
    parts = []

    # 1. Phase progress (one line)
    phase = extract_phase_and_progress(PROJECT_ROOT / "EVOLUTION-PLAN.md")
    if phase:
        parts.append(f"[PHASE] {phase}")

    # 2. Current task objective (minimal)
    task = extract_task_objective(PROJECT_ROOT / "task.md")
    if task:
        parts.append(f"[TASK]\n{task}")

    # 3. Handoff pointer (not content)
    handoff = get_handoff_pointer()
    if handoff:
        parts.append(f"[HANDOFF] {handoff}")

    # 4. Capability summary (one line)
    caps = get_capability_summary()
    if caps:
        parts.append(f"[CAPS] {caps}")

    # Compose compact output
    if parts:
        output["message"] = "\n".join(parts)

    print(json.dumps(output))


if __name__ == "__main__":
    main()
