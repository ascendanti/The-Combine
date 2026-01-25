#!/usr/bin/env python3
"""
Proactive Task Generator - System generates its own tasks

This module enables the system to identify opportunities and generate tasks
without waiting for user input. It analyzes codebase, patterns, and outcomes
to suggest high-value activities.

Usage:
    # Generate tasks based on current state
    python daemon/task_generator.py generate

    # Get pending generated tasks
    python daemon/task_generator.py pending

    # Mark a generated task as approved/rejected
    python daemon/task_generator.py approve <task_id>
    python daemon/task_generator.py reject <task_id> --reason "Not needed"

    # Run continuous generation (daemon mode)
    python daemon/task_generator.py daemon --interval 3600
"""

import sqlite3
import json
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import os
import glob
import hashlib
import time

DB_PATH = Path(__file__).parent / "generated_tasks.db"
PROJECT_DIR = Path(__file__).parent.parent


def init_db():
    """Initialize the generated tasks database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS generated_tasks (
        task_id TEXT PRIMARY KEY,
        category TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        rationale TEXT,
        priority INTEGER DEFAULT 5,
        effort TEXT,
        source TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT,
        reviewed_at TEXT,
        rejection_reason TEXT
    )''')

    c.execute('''CREATE INDEX IF NOT EXISTS idx_status ON generated_tasks(status)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_category ON generated_tasks(category)''')

    # Opportunity detection log
    c.execute('''CREATE TABLE IF NOT EXISTS opportunity_log (
        log_id TEXT PRIMARY KEY,
        detector TEXT,
        findings TEXT,
        tasks_generated INTEGER,
        created_at TEXT
    )''')

    conn.commit()
    conn.close()


def generate_task_id(title: str) -> str:
    """Generate a unique task ID."""
    hash_input = f"{title}_{datetime.now().isoformat()}"
    return f"gen_{hashlib.md5(hash_input.encode()).hexdigest()[:12]}"


def add_generated_task(
    category: str,
    title: str,
    description: str,
    rationale: str,
    priority: int = 5,
    effort: str = "medium",
    source: str = "auto"
) -> str:
    """Add a generated task to the queue."""
    init_db()

    task_id = generate_task_id(title)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Check for duplicate (same title in pending)
    c.execute('SELECT task_id FROM generated_tasks WHERE title = ? AND status = ?', (title, 'pending'))
    if c.fetchone():
        conn.close()
        return None  # Duplicate

    c.execute('''INSERT INTO generated_tasks
        (task_id, category, title, description, rationale, priority, effort, source, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)''',
        (task_id, category, title, description, rationale, priority, effort, source, datetime.now().isoformat()))

    conn.commit()
    conn.close()

    return task_id


def log_opportunity_detection(detector: str, findings: Dict, tasks_generated: int):
    """Log an opportunity detection run."""
    init_db()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    log_id = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{detector}"

    c.execute('''INSERT INTO opportunity_log (log_id, detector, findings, tasks_generated, created_at)
        VALUES (?, ?, ?, ?, ?)''',
        (log_id, detector, json.dumps(findings), tasks_generated, datetime.now().isoformat()))

    conn.commit()
    conn.close()


# ============== OPPORTUNITY DETECTORS ==============

def detect_dead_code() -> List[Dict]:
    """Detect dead/unused code that could be cleaned up."""
    tasks = []

    # Check for unused Python files
    daemon_dir = PROJECT_DIR / "daemon"
    if daemon_dir.exists():
        py_files = list(daemon_dir.glob("*.py"))

        # Look for files that aren't imported anywhere
        for py_file in py_files:
            if py_file.name.startswith("_"):
                continue

            module_name = py_file.stem
            # Simple grep for imports
            grep_result = subprocess.run(
                ["grep", "-r", f"import {module_name}", str(PROJECT_DIR)],
                capture_output=True, text=True
            )

            if not grep_result.stdout:
                # Not imported anywhere
                tasks.append({
                    "category": "cleanup",
                    "title": f"Review potentially unused: {py_file.name}",
                    "description": f"File {py_file} doesn't appear to be imported anywhere. Consider removing or documenting its purpose.",
                    "rationale": "Dead code increases maintenance burden and confusion.",
                    "priority": 3,
                    "effort": "low"
                })

    return tasks


def detect_missing_tests() -> List[Dict]:
    """Detect code without corresponding tests."""
    tasks = []

    daemon_dir = PROJECT_DIR / "daemon"
    if daemon_dir.exists():
        py_files = [f for f in daemon_dir.glob("*.py") if not f.name.startswith("test_")]

        for py_file in py_files:
            test_file = daemon_dir / f"test_{py_file.name}"
            if not test_file.exists():
                tasks.append({
                    "category": "testing",
                    "title": f"Add tests for {py_file.name}",
                    "description": f"No test file found for {py_file}. Consider adding unit tests.",
                    "rationale": "Tests prevent regressions and document expected behavior.",
                    "priority": 4,
                    "effort": "medium"
                })

    return tasks


def detect_documentation_gaps() -> List[Dict]:
    """Detect files/functions missing documentation."""
    tasks = []

    daemon_dir = PROJECT_DIR / "daemon"
    if daemon_dir.exists():
        for py_file in daemon_dir.glob("*.py"):
            content = py_file.read_text()

            # Check for module docstring
            if not content.strip().startswith('"""') and not content.strip().startswith("'''"):
                tasks.append({
                    "category": "documentation",
                    "title": f"Add module docstring to {py_file.name}",
                    "description": f"File {py_file.name} is missing a module-level docstring.",
                    "rationale": "Docstrings help understand purpose and usage.",
                    "priority": 2,
                    "effort": "low"
                })

    return tasks[:5]  # Limit to 5


def detect_error_handling_gaps() -> List[Dict]:
    """Detect places where error handling could be improved."""
    tasks = []

    daemon_dir = PROJECT_DIR / "daemon"
    if daemon_dir.exists():
        for py_file in daemon_dir.glob("*.py"):
            content = py_file.read_text()

            # Check for bare except clauses
            if "except:" in content and "except Exception" not in content:
                tasks.append({
                    "category": "quality",
                    "title": f"Fix bare except in {py_file.name}",
                    "description": f"File {py_file.name} has bare except clauses that may hide errors.",
                    "rationale": "Bare except catches too much, including SystemExit and KeyboardInterrupt.",
                    "priority": 5,
                    "effort": "low"
                })

            # Check for pass in except
            if "except" in content and "pass" in content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if "except" in line and i + 1 < len(lines) and "pass" in lines[i + 1].strip():
                        tasks.append({
                            "category": "quality",
                            "title": f"Add logging to silent except in {py_file.name}",
                            "description": f"File {py_file.name} has except blocks that silently pass.",
                            "rationale": "Silent exceptions hide bugs and make debugging difficult.",
                            "priority": 4,
                            "effort": "low"
                        })
                        break

    return tasks[:5]


def detect_schema_drift() -> List[Dict]:
    """Detect potential database schema issues."""
    tasks = []

    # Look for ALTER TABLE commands in recent session
    daemon_dir = PROJECT_DIR / "daemon"
    db_files = list(daemon_dir.glob("*.db"))

    if len(db_files) > 3:
        tasks.append({
            "category": "architecture",
            "title": "Consolidate database files",
            "description": f"Found {len(db_files)} database files in daemon/. Consider consolidating or documenting the schema.",
            "rationale": "Multiple databases increase complexity and risk of inconsistency.",
            "priority": 4,
            "effort": "high"
        })

    return tasks


def detect_outcome_patterns() -> List[Dict]:
    """Analyze outcome tracker for improvement opportunities."""
    tasks = []

    try:
        from outcome_tracker import query_success_rates, get_stats

        stats = get_stats()

        if stats.get("total_outcomes", 0) > 10:
            # Look for low success rate actions
            rates = query_success_rates(min_count=3)

            for rate in rates:
                if rate["success_rate"] < 0.5:
                    tasks.append({
                        "category": "improvement",
                        "title": f"Investigate low success: {rate['action']}",
                        "description": f"Action {rate['action']} has only {rate['success_rate']*100:.0f}% success rate over {rate['total']} attempts.",
                        "rationale": "Understanding failures enables systematic improvement.",
                        "priority": 6,
                        "effort": "medium"
                    })
    except:
        pass

    return tasks


def detect_strategy_opportunities() -> List[Dict]:
    """Analyze strategies for evolution opportunities."""
    tasks = []

    try:
        from strategy_ops import get_health_dashboard

        health = get_health_dashboard()

        if health.get("warnings"):
            for warning in health["warnings"][:3]:
                tasks.append({
                    "category": "strategy",
                    "title": f"Address strategy warning",
                    "description": warning,
                    "rationale": "Strategy health issues impact overall system effectiveness.",
                    "priority": 5,
                    "effort": "medium"
                })
    except:
        pass

    return tasks


def detect_stale_handoffs() -> List[Dict]:
    """Detect old handoffs that may need cleanup or action."""
    tasks = []

    handoffs_dir = PROJECT_DIR / "thoughts" / "handoffs"
    if handoffs_dir.exists():
        handoff_files = list(handoffs_dir.glob("*.yaml"))

        # Check for very old handoffs
        week_ago = datetime.now() - timedelta(days=7)
        for hf in handoff_files:
            mod_time = datetime.fromtimestamp(os.path.getmtime(hf))
            if mod_time < week_ago:
                tasks.append({
                    "category": "maintenance",
                    "title": f"Review old handoff: {hf.name}",
                    "description": f"Handoff from {mod_time.strftime('%Y-%m-%d')} may need review or archiving.",
                    "rationale": "Old handoffs can contain stale information.",
                    "priority": 2,
                    "effort": "low"
                })

    return tasks[:3]


def detect_knowledge_gaps() -> List[Dict]:
    """Detect areas where more knowledge would help."""
    tasks = []

    try:
        conn = sqlite3.connect(PROJECT_DIR / "daemon" / "utf_knowledge.db")
        c = conn.cursor()

        c.execute('SELECT COUNT(*) FROM sources')
        source_count = c.fetchone()[0]

        if source_count < 50:
            tasks.append({
                "category": "knowledge",
                "title": "Ingest more research papers",
                "description": f"Currently only {source_count} sources in knowledge base. More diversity would improve insights.",
                "rationale": "Knowledge synthesis improves with more source material.",
                "priority": 4,
                "effort": "low"
            })

        conn.close()
    except:
        pass

    return tasks


# ============== MAIN FUNCTIONS ==============

def run_all_detectors() -> Tuple[List[Dict], Dict]:
    """Run all opportunity detectors and return tasks."""
    all_tasks = []
    findings = {}

    detectors = [
        ("dead_code", detect_dead_code),
        ("missing_tests", detect_missing_tests),
        ("documentation", detect_documentation_gaps),
        ("error_handling", detect_error_handling_gaps),
        ("schema_drift", detect_schema_drift),
        ("outcomes", detect_outcome_patterns),
        ("strategies", detect_strategy_opportunities),
        ("handoffs", detect_stale_handoffs),
        ("knowledge", detect_knowledge_gaps),
    ]

    for name, detector in detectors:
        try:
            tasks = detector()
            findings[name] = len(tasks)
            all_tasks.extend(tasks)
        except Exception as e:
            findings[name] = f"error: {e}"

    return all_tasks, findings


def generate_tasks() -> List[str]:
    """Generate tasks from all detectors and add to queue."""
    tasks, findings = run_all_detectors()

    added_ids = []
    for task in tasks:
        task_id = add_generated_task(
            category=task["category"],
            title=task["title"],
            description=task["description"],
            rationale=task["rationale"],
            priority=task.get("priority", 5),
            effort=task.get("effort", "medium"),
            source="auto_detector"
        )
        if task_id:
            added_ids.append(task_id)

    # Log the detection run
    log_opportunity_detection("all_detectors", findings, len(added_ids))

    return added_ids


def get_pending_tasks() -> List[Dict]:
    """Get all pending generated tasks."""
    init_db()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''SELECT task_id, category, title, description, rationale, priority, effort, source, created_at
        FROM generated_tasks
        WHERE status = 'pending'
        ORDER BY priority DESC, created_at ASC''')

    tasks = []
    for row in c.fetchall():
        tasks.append({
            "task_id": row[0],
            "category": row[1],
            "title": row[2],
            "description": row[3],
            "rationale": row[4],
            "priority": row[5],
            "effort": row[6],
            "source": row[7],
            "created_at": row[8]
        })

    conn.close()
    return tasks


def approve_task(task_id: str) -> bool:
    """Approve a generated task."""
    init_db()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''UPDATE generated_tasks SET status = 'approved', reviewed_at = ?
        WHERE task_id = ?''', (datetime.now().isoformat(), task_id))

    affected = c.rowcount
    conn.commit()
    conn.close()

    return affected > 0


def reject_task(task_id: str, reason: str = "") -> bool:
    """Reject a generated task."""
    init_db()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''UPDATE generated_tasks SET status = 'rejected', reviewed_at = ?, rejection_reason = ?
        WHERE task_id = ?''', (datetime.now().isoformat(), reason, task_id))

    affected = c.rowcount
    conn.commit()
    conn.close()

    return affected > 0


def run_daemon(interval_seconds: int = 3600):
    """Run task generation in daemon mode."""
    print(f"Starting task generator daemon (interval: {interval_seconds}s)")

    while True:
        try:
            print(f"[{datetime.now().isoformat()}] Running task generation...")
            added = generate_tasks()
            print(f"  Generated {len(added)} new tasks")
        except Exception as e:
            print(f"  Error: {e}")

        time.sleep(interval_seconds)


def main():
    parser = argparse.ArgumentParser(description="Proactive Task Generator")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Generate command
    subparsers.add_parser("generate", help="Generate tasks from all detectors")

    # Pending command
    subparsers.add_parser("pending", help="Show pending generated tasks")

    # Approve command
    approve_parser = subparsers.add_parser("approve", help="Approve a task")
    approve_parser.add_argument("task_id", help="Task ID to approve")

    # Reject command
    reject_parser = subparsers.add_parser("reject", help="Reject a task")
    reject_parser.add_argument("task_id", help="Task ID to reject")
    reject_parser.add_argument("--reason", default="", help="Rejection reason")

    # Daemon command
    daemon_parser = subparsers.add_parser("daemon", help="Run in daemon mode")
    daemon_parser.add_argument("--interval", type=int, default=3600, help="Interval in seconds")

    args = parser.parse_args()

    if args.command == "generate":
        added = generate_tasks()
        print(f"Generated {len(added)} tasks")
        if added:
            print("Task IDs:", ", ".join(added))

    elif args.command == "pending":
        tasks = get_pending_tasks()
        if not tasks:
            print("No pending tasks")
        else:
            print(f"Pending tasks ({len(tasks)}):\n")
            for t in tasks:
                print(f"[{t['task_id']}] {t['title']}")
                print(f"  Category: {t['category']} | Priority: {t['priority']} | Effort: {t['effort']}")
                print(f"  {t['description']}")
                print(f"  Rationale: {t['rationale']}")
                print()

    elif args.command == "approve":
        if approve_task(args.task_id):
            print(f"Approved: {args.task_id}")
        else:
            print(f"Task not found: {args.task_id}")

    elif args.command == "reject":
        if reject_task(args.task_id, args.reason):
            print(f"Rejected: {args.task_id}")
        else:
            print(f"Task not found: {args.task_id}")

    elif args.command == "daemon":
        run_daemon(args.interval)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
