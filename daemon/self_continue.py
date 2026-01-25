#!/usr/bin/env python3
"""
Self-Continue System - Automatic continuation after context compaction

This module enables Claude to automatically resume work after conversation
is compacted due to limited context. It reads plans, strategies, and handoffs
to determine the next action.

Usage:
    # Get continuation instructions
    python daemon/self_continue.py resume

    # Record current state for continuation
    python daemon/self_continue.py checkpoint --phase "Phase 13" --task "Paper ingestion"

    # Get full context for resumption
    python daemon/self_continue.py context
"""

import sqlite3
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import os
import glob

DB_PATH = Path(__file__).parent / "continue.db"
PROJECT_DIR = Path(__file__).parent.parent


def init_db():
    """Initialize the continuation database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Checkpoints table - snapshots of work state
    c.execute('''CREATE TABLE IF NOT EXISTS checkpoints (
        checkpoint_id TEXT PRIMARY KEY,
        phase TEXT,
        task TEXT,
        status TEXT,
        context TEXT,
        next_actions TEXT,
        blockers TEXT,
        priority INTEGER DEFAULT 5,
        created_at TEXT
    )''')

    # Continuation queue - tasks to resume
    c.execute('''CREATE TABLE IF NOT EXISTS continuation_queue (
        queue_id TEXT PRIMARY KEY,
        source TEXT,
        action TEXT,
        priority INTEGER,
        context TEXT,
        completed INTEGER DEFAULT 0,
        created_at TEXT,
        completed_at TEXT
    )''')

    # Session state - track what was happening
    c.execute('''CREATE TABLE IF NOT EXISTS session_state (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TEXT
    )''')

    conn.commit()
    conn.close()


def save_state(key: str, value: str):
    """Save session state for continuation."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''INSERT OR REPLACE INTO session_state (key, value, updated_at)
        VALUES (?, ?, ?)''', (key, value, datetime.now().isoformat()))

    conn.commit()
    conn.close()


def get_state(key: str) -> Optional[str]:
    """Get session state."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('SELECT value FROM session_state WHERE key = ?', (key,))
    row = c.fetchone()
    conn.close()

    return row[0] if row else None


def create_checkpoint(
    phase: str,
    task: str,
    status: str = "in_progress",
    context: str = "",
    next_actions: List[str] = None,
    blockers: List[str] = None,
    priority: int = 5
) -> str:
    """Create a checkpoint for continuation."""
    init_db()

    checkpoint_id = f"chk_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''INSERT INTO checkpoints
        (checkpoint_id, phase, task, status, context, next_actions, blockers, priority, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (checkpoint_id, phase, task, status, context,
         json.dumps(next_actions or []), json.dumps(blockers or []),
         priority, datetime.now().isoformat()))

    conn.commit()
    conn.close()

    return checkpoint_id


def get_latest_checkpoint() -> Optional[Dict]:
    """Get the most recent checkpoint."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''SELECT checkpoint_id, phase, task, status, context, next_actions, blockers, priority, created_at
        FROM checkpoints ORDER BY created_at DESC LIMIT 1''')

    row = c.fetchone()
    conn.close()

    if row:
        return {
            "checkpoint_id": row[0],
            "phase": row[1],
            "task": row[2],
            "status": row[3],
            "context": row[4],
            "next_actions": json.loads(row[5]) if row[5] else [],
            "blockers": json.loads(row[6]) if row[6] else [],
            "priority": row[7],
            "created_at": row[8]
        }
    return None


def queue_continuation(source: str, action: str, priority: int = 5, context: str = ""):
    """Add a task to the continuation queue."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    queue_id = f"q_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(action) % 10000}"

    c.execute('''INSERT INTO continuation_queue
        (queue_id, source, action, priority, context, created_at)
        VALUES (?, ?, ?, ?, ?, ?)''',
        (queue_id, source, action, priority, context, datetime.now().isoformat()))

    conn.commit()
    conn.close()


def get_pending_continuations() -> List[Dict]:
    """Get pending continuation tasks."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''SELECT queue_id, source, action, priority, context, created_at
        FROM continuation_queue
        WHERE completed = 0
        ORDER BY priority DESC, created_at ASC''')

    tasks = []
    for row in c.fetchall():
        tasks.append({
            "queue_id": row[0],
            "source": row[1],
            "action": row[2],
            "priority": row[3],
            "context": row[4],
            "created_at": row[5]
        })

    conn.close()
    return tasks


def mark_continuation_done(queue_id: str):
    """Mark a continuation task as completed."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''UPDATE continuation_queue
        SET completed = 1, completed_at = ?
        WHERE queue_id = ?''', (datetime.now().isoformat(), queue_id))

    conn.commit()
    conn.close()


def get_latest_handoff() -> Optional[Dict]:
    """Get the latest handoff file."""
    handoffs_dir = PROJECT_DIR / "thoughts" / "handoffs"
    if not handoffs_dir.exists():
        return None

    handoff_files = sorted(handoffs_dir.glob("*.yaml"), key=os.path.getmtime, reverse=True)
    if not handoff_files:
        return None

    latest = handoff_files[0]
    try:
        import yaml
        with open(latest) as f:
            content = yaml.safe_load(f)
        return {
            "file": str(latest),
            "content": content
        }
    except:
        # Return raw content if YAML parsing fails
        return {
            "file": str(latest),
            "content": latest.read_text()
        }


def get_evolution_plan_status() -> Optional[Dict]:
    """Get current status from EVOLUTION-PLAN.md."""
    plan_path = PROJECT_DIR / "EVOLUTION-PLAN.md"
    if not plan_path.exists():
        return None

    content = plan_path.read_text()

    # Extract current phase
    current_phase = None
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if '**Current:**' in line or 'Status: IN PROGRESS' in line.upper():
            current_phase = line
            break
        if '## Phase' in line and ('IN PROGRESS' in content[content.find(line):content.find(line)+200].upper()):
            current_phase = line
            break

    return {
        "file": str(plan_path),
        "current_phase": current_phase,
        "preview": content[:1000]
    }


def get_task_status() -> Optional[Dict]:
    """Get current task from task.md."""
    task_path = PROJECT_DIR / "task.md"
    if not task_path.exists():
        return None

    content = task_path.read_text()

    # Find in-progress items
    in_progress = []
    for line in content.split('\n'):
        if '- [ ]' in line or 'In Progress' in line:
            in_progress.append(line.strip())

    return {
        "file": str(task_path),
        "in_progress": in_progress[:5],
        "preview": content[:800]
    }


def get_strategy_context() -> Optional[Dict]:
    """Get current strategy from strategy_evolution.py."""
    try:
        from strategy_evolution import get_active_strategies
        strategies = get_active_strategies()
        return {
            "active_strategies": strategies[:3] if strategies else []
        }
    except:
        return None


def generate_continuation_context() -> Dict:
    """Generate full context for session continuation."""
    context = {
        "generated_at": datetime.now().isoformat(),
        "checkpoint": get_latest_checkpoint(),
        "handoff": get_latest_handoff(),
        "evolution_plan": get_evolution_plan_status(),
        "task": get_task_status(),
        "pending_queue": get_pending_continuations(),
        "strategy": get_strategy_context()
    }

    # Generate continuation instructions
    instructions = []

    if context["checkpoint"]:
        chk = context["checkpoint"]
        instructions.append(f"Resume {chk['task']} in {chk['phase']}")
        if chk["next_actions"]:
            instructions.extend([f"  - {a}" for a in chk["next_actions"][:3]])

    if context["pending_queue"]:
        instructions.append("Pending tasks:")
        for task in context["pending_queue"][:3]:
            instructions.append(f"  - [{task['source']}] {task['action']}")

    if context["handoff"]:
        instructions.append(f"Latest handoff: {context['handoff']['file']}")

    context["continuation_instructions"] = instructions

    return context


def format_resume_message() -> str:
    """Format a message for Claude to resume work."""
    ctx = generate_continuation_context()

    msg = ["# Self-Continue: Resume Context", ""]

    if ctx["checkpoint"]:
        chk = ctx["checkpoint"]
        msg.append(f"## Last Checkpoint: {chk['phase']}")
        msg.append(f"**Task:** {chk['task']}")
        msg.append(f"**Status:** {chk['status']}")
        if chk["context"]:
            msg.append(f"**Context:** {chk['context']}")
        if chk["next_actions"]:
            msg.append("**Next Actions:**")
            for a in chk["next_actions"]:
                msg.append(f"- {a}")
        msg.append("")

    if ctx["evolution_plan"]:
        msg.append("## Evolution Plan Status")
        if ctx["evolution_plan"]["current_phase"]:
            msg.append(ctx["evolution_plan"]["current_phase"])
        msg.append("")

    if ctx["pending_queue"]:
        msg.append("## Pending Continuation Queue")
        for task in ctx["pending_queue"][:5]:
            msg.append(f"- **[{task['source']}]** {task['action']}")
        msg.append("")

    if ctx["handoff"]:
        msg.append(f"## Latest Handoff")
        msg.append(f"File: `{ctx['handoff']['file']}`")
        msg.append("")

    msg.append("## Instructions")
    msg.append("1. Read the latest handoff file")
    msg.append("2. Check task.md for current objectives")
    msg.append("3. Continue from the checkpoint above")
    msg.append("4. Process pending queue items")
    msg.append("")
    msg.append("**Do not ask what to do - continue where you left off.**")

    return "\n".join(msg)


def main():
    parser = argparse.ArgumentParser(description="Self-Continue System")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Resume command
    subparsers.add_parser("resume", help="Get continuation instructions")

    # Checkpoint command
    chk_parser = subparsers.add_parser("checkpoint", help="Create a checkpoint")
    chk_parser.add_argument("--phase", required=True, help="Current phase")
    chk_parser.add_argument("--task", required=True, help="Current task")
    chk_parser.add_argument("--status", default="in_progress", help="Status")
    chk_parser.add_argument("--context", default="", help="Additional context")
    chk_parser.add_argument("--next", nargs="*", help="Next actions")
    chk_parser.add_argument("--blockers", nargs="*", help="Blockers")
    chk_parser.add_argument("--priority", type=int, default=5, help="Priority (1-10)")

    # Queue command
    q_parser = subparsers.add_parser("queue", help="Add to continuation queue")
    q_parser.add_argument("--source", required=True, help="Source of task")
    q_parser.add_argument("--action", required=True, help="Action to take")
    q_parser.add_argument("--priority", type=int, default=5, help="Priority")
    q_parser.add_argument("--context", default="", help="Context")

    # Context command
    subparsers.add_parser("context", help="Get full continuation context")

    # Done command
    done_parser = subparsers.add_parser("done", help="Mark continuation done")
    done_parser.add_argument("--id", required=True, help="Queue ID")

    # State commands
    state_parser = subparsers.add_parser("state", help="Manage session state")
    state_parser.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"), help="Set state")
    state_parser.add_argument("--get", help="Get state")

    args = parser.parse_args()

    if args.command == "resume":
        print(format_resume_message())

    elif args.command == "checkpoint":
        checkpoint_id = create_checkpoint(
            phase=args.phase,
            task=args.task,
            status=args.status,
            context=args.context,
            next_actions=args.next,
            blockers=args.blockers,
            priority=args.priority
        )
        print(f"Created checkpoint: {checkpoint_id}")

    elif args.command == "queue":
        queue_continuation(
            source=args.source,
            action=args.action,
            priority=args.priority,
            context=args.context
        )
        print("Added to continuation queue")

    elif args.command == "context":
        ctx = generate_continuation_context()
        print(json.dumps(ctx, indent=2, default=str))

    elif args.command == "done":
        mark_continuation_done(args.id)
        print(f"Marked {args.id} as completed")

    elif args.command == "state":
        if args.set:
            save_state(args.set[0], args.set[1])
            print(f"Saved state: {args.set[0]}")
        elif args.get:
            value = get_state(args.get)
            print(value if value else "Not found")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
