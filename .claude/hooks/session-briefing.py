#!/usr/bin/env python3
"""
Session Briefing Hook - Architecture-Aware Version

CRITICAL: This hook injects mandatory architecture awareness on every session start.
Without this, Claude operates without knowledge of its full capabilities.

Outputs:
1. MANDATORY read directive for ARCHITECTURE-LIVE.md
2. Daemon system status (what's wired vs unused)
3. Memory recall of relevant learnings (NEWLY WIRED)
4. Phase progress and current task
5. Handoff pointer for continuity
"""

import json
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent
CLAUDE_DIR = PROJECT_ROOT / ".claude"
DAEMON_DIR = PROJECT_ROOT / "daemon"

# Wire in memory_router for context recall
sys.path.insert(0, str(DAEMON_DIR))
try:
    from memory_router import MemoryRouter
    MEMORY_ROUTER_AVAILABLE = True
except ImportError:
    MEMORY_ROUTER_AVAILABLE = False
    MemoryRouter = None

# WIRED: unified_spine for backbone coordination
try:
    from unified_spine import UnifiedSpine
    UNIFIED_SPINE_AVAILABLE = True
except ImportError:
    UNIFIED_SPINE_AVAILABLE = False
    UnifiedSpine = None

# WIRED: deferred_tasks for surfacing pending recommendations
try:
    from deferred_tasks import DeferredTaskCapture
    DEFERRED_AVAILABLE = True
except ImportError:
    DEFERRED_AVAILABLE = False
    DeferredTaskCapture = None

# Hard limits for token efficiency
MAX_TASK_LINES = 20


def get_architecture_directive() -> str:
    """
    MANDATORY: Return directive to read architecture file.
    This ensures every session starts with full system awareness.
    """
    arch_file = CLAUDE_DIR / "ARCHITECTURE-LIVE.md"
    if arch_file.exists():
        return f"""⚠️ MANDATORY: Read {arch_file.name} BEFORE any work.
This file is your brain map - it shows what exists and what's wired.
Path: .claude/ARCHITECTURE-LIVE.md"""
    return ""


def get_directives() -> str:
    """
    MANDATORY: Return standing directives from user.
    These are orders that MUST be followed every session.
    """
    directives_file = CLAUDE_DIR / "DIRECTIVES.md"
    if not directives_file.exists():
        return ""

    try:
        content = directives_file.read_text(encoding='utf-8', errors='ignore')
        # Extract just the core directives section (first 30 lines)
        lines = content.split('\n')[:30]
        # Find the "## Core Directives" section
        in_core = False
        core_lines = []
        for line in lines:
            if "## Core Directives" in line:
                in_core = True
                continue
            if in_core and line.startswith("## "):
                break
            if in_core and line.strip():
                core_lines.append(line)

        if core_lines:
            return "Standing Orders:\n" + "\n".join(core_lines[:10])  # First 10 lines only
        return "Read .claude/DIRECTIVES.md for standing orders"
    except Exception:
        return ""


def get_deferred_tasks() -> str:
    """
    WIRED: Surface pending deferred tasks/recommendations.
    Ensures user recommendations aren't forgotten.
    """
    if not DEFERRED_AVAILABLE or DeferredTaskCapture is None:
        return ""

    try:
        capture = DeferredTaskCapture()
        summary = capture.summary()

        if summary["pending"] == 0:
            return ""

        # Get top priority items
        pending = capture.get_pending(limit=3)
        if not pending:
            return ""

        items = []
        for task in pending[:3]:
            priority_mark = "!" * min(task.priority, 3)
            items.append(f"  {priority_mark} {task.content[:60]}...")

        return f"Pending ({summary['pending']} total, {summary['high_priority']} high-priority):\n" + "\n".join(items)
    except Exception as e:
        return ""


def get_daemon_status() -> str:
    """Get quick status of daemon systems."""
    status_lines = []

    # Core systems to check
    core_systems = [
        ("unified_spine.py", "Backbone", "UNUSED - not wired"),
        ("memory_router.py", "Memory", "UNUSED - not wired"),
        ("emergent.py", "Learning", "UNUSED - not wired"),
        ("orchestrator.py", "Brain", "PARTIAL - has fast_classify()"),
        ("deterministic_router.py", "Router", "ACTIVE - UserPromptSubmit"),
    ]

    active = 0
    unused = 0
    for filename, name, status in core_systems:
        if (DAEMON_DIR / filename).exists():
            if "ACTIVE" in status:
                active += 1
            elif "UNUSED" in status:
                unused += 1

    return f"Daemon: {active} active, {unused} unused (wire them!)"


def get_integration_status() -> str:
    """Check pending integrations."""
    pending_path = DAEMON_DIR / "integrations" / "pending_repos.json"
    if not pending_path.exists():
        return ""
    try:
        with open(pending_path) as f:
            data = json.load(f)
        adopted = len(data.get("adopted_for_architecture", []))
        pending = len(data.get("pending_integration", []))
        return f"Integrations: {adopted} adopted, {pending} pending"
    except Exception:
        return ""


def extract_phase_and_progress(evolution_path: Path) -> str:
    """Extract ONLY phase number and key metrics, not full status."""
    if not evolution_path.exists():
        return ""
    try:
        content = evolution_path.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')

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
    caps_path = CLAUDE_DIR / "config" / "capabilities.json"
    if not caps_path.exists():
        return ""
    try:
        with open(caps_path) as f:
            caps = json.load(f)
        c = caps['counts']
        return f"A:{c['agents']} S:{c['skills']} R:{c['rules']} H:{c['hooks']}"
    except Exception:
        return ""


def get_wiring_priorities() -> str:
    """Return immediate wiring priorities."""
    wiring_file = CLAUDE_DIR / "INTEGRATION-WIRING-PLAN.md"
    if wiring_file.exists():
        return "Wiring plan: .claude/INTEGRATION-WIRING-PLAN.md"
    return ""


def recall_recent_context() -> str:
    """
    WIRED: Use memory_router to recall recent learnings/decisions.
    This provides session continuity even after context compaction.
    """
    if not MEMORY_ROUTER_AVAILABLE or MemoryRouter is None:
        return ""

    try:
        router = MemoryRouter()
        # Search for recent session-relevant memories
        results = router.search("session learning decision", k=3)

        if not results:
            return ""

        # Format concisely
        summaries = []
        for r in results[:3]:  # Top 3 only for token efficiency
            source = r.source.split(":")[-1] if ":" in r.source else r.source
            content = r.content[:80] + "..." if len(r.content) > 80 else r.content
            summaries.append(f"  [{source}] {content}")

        if summaries:
            return "Recent context:\n" + "\n".join(summaries)
        return ""
    except Exception as e:
        return f"Memory recall unavailable: {e}"


def run_spine_cycle() -> str:
    """
    WIRED: Run unified_spine cycle on session start.
    Checks for pending handoffs and processes any queued tasks.
    """
    if not UNIFIED_SPINE_AVAILABLE or UnifiedSpine is None:
        return ""

    try:
        spine = UnifiedSpine()
        results = spine.run_cycle()

        # Only report if something happened
        if results.get("handoff_resumed") or results.get("tasks_generated") or results.get("tasks_executed"):
            parts = []
            if results.get("handoff_resumed"):
                parts.append("handoff resumed")
            if results.get("tasks_generated"):
                parts.append(f"{results['tasks_generated']} tasks generated")
            if results.get("tasks_executed"):
                parts.append(f"{results['tasks_executed']} tasks executed")
            return "Spine: " + ", ".join(parts)
        return ""
    except Exception as e:
        return ""  # Silent failure - don't block session start


def main():
    output = {"continue": True}
    parts = []

    # CRITICAL: Architecture awareness directive (ALWAYS FIRST)
    arch = get_architecture_directive()
    if arch:
        parts.append(f"[ARCHITECTURE]\n{arch}")

    # CRITICAL: Standing directives from user (SECOND)
    directives = get_directives()
    if directives:
        parts.append(f"[DIRECTIVES]\n{directives}")

    # CRITICAL: Deferred tasks/recommendations (THIRD)
    deferred = get_deferred_tasks()
    if deferred:
        parts.append(f"[DEFERRED]\n{deferred}")

    # Daemon status (quick view of what's wired)
    daemon = get_daemon_status()
    if daemon:
        parts.append(f"[DAEMON] {daemon}")

    # Integration status
    integrations = get_integration_status()
    if integrations:
        parts.append(f"[INTEGRATIONS] {integrations}")

    # Wiring plan pointer
    wiring = get_wiring_priorities()
    if wiring:
        parts.append(f"[WIRING] {wiring}")

    # WIRED: Memory recall for session continuity
    memory_context = recall_recent_context()
    if memory_context and "unavailable" not in memory_context:
        parts.append(f"[MEMORY]\n{memory_context}")

    # WIRED: Run unified_spine cycle (check handoffs, process tasks)
    spine_result = run_spine_cycle()
    if spine_result:
        parts.append(f"[SPINE] {spine_result}")

    # Phase progress (one line)
    phase = extract_phase_and_progress(PROJECT_ROOT / "EVOLUTION-PLAN.md")
    if phase:
        parts.append(f"[PHASE] {phase}")

    # Current task objective (minimal)
    task = extract_task_objective(PROJECT_ROOT / "task.md")
    if task:
        parts.append(f"[TASK]\n{task}")

    # Handoff pointer (not content)
    handoff = get_handoff_pointer()
    if handoff:
        parts.append(f"[HANDOFF] {handoff}")

    # Capability summary (one line)
    caps = get_capability_summary()
    if caps:
        parts.append(f"[CAPS] {caps}")

    # Compose compact output
    if parts:
        output["message"] = "\n".join(parts)
    else:
        output["message"] = "[ARCHITECTURE] Read .claude/ARCHITECTURE-LIVE.md first!"

    print(json.dumps(output))


if __name__ == "__main__":
    main()
