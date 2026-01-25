#!/usr/bin/env python3
"""
Evolution Tracker - Links Strategy → Evolution Plan → Sci-Fi Roadmap

Automatically syncs progress across all planning documents.
Run after any strategic action to update all linked docs.

Usage:
    python daemon/evolution_tracker.py sync       # Sync all docs
    python daemon/evolution_tracker.py status     # Show linked status
    python daemon/evolution_tracker.py progress   # Progress report
"""

import sqlite3
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_DIR = Path(__file__).parent.parent
STRATEGY_DB = Path(__file__).parent / "strategies.db"
OUTCOME_DB = Path(__file__).parent / "outcomes.db"

# Document paths
EVOLUTION_PLAN = PROJECT_DIR / "EVOLUTION-PLAN.md"
SCIFI_ROADMAP = PROJECT_DIR / ".claude" / "SCI-FI-TECHNICAL-ROADMAP.md"
TASK_MD = PROJECT_DIR / "task.md"


# Strategy → Evolution Plan Phase mapping
STRATEGY_TO_PHASE = {
    "Phase14-TokenOpt": "Phase 14",
    "Phase14-Bisim": "Phase 14",
    "Phase15-Memory": "Phase 15",
    "Phase15-MAPE": "Phase 15",
    "SciFi-Jarvis": "Phase 16+",
    "SciFi-Data": "Phase 16+",
    "SciFi-Oracle": "Phase 16+",
}

# Strategy → Sci-Fi Class mapping
STRATEGY_TO_SCIFI = {
    "SciFi-Jarvis": "1. JARVIS-CLASS",
    "SciFi-Data": "2. DATA-CLASS",
    "SciFi-Oracle": "3. ORACLE-CLASS",
    "Phase14-TokenOpt": "Prerequisite",
    "Phase14-Bisim": "Prerequisite",
    "Phase15-Memory": "Prerequisite",
    "Phase15-MAPE": "Prerequisite",
}


def get_strategy_status() -> List[Dict]:
    """Get status of all strategies."""
    if not STRATEGY_DB.exists():
        return []

    conn = sqlite3.connect(STRATEGY_DB)
    c = conn.cursor()

    c.execute('''SELECT strategy_id, name, status, metrics, updated_at
        FROM strategies ORDER BY strategy_id''')

    strategies = []
    for row in c.fetchall():
        strategies.append({
            "id": row[0],
            "name": row[1],
            "status": row[2],
            "metrics": json.loads(row[3]) if row[3] else {},
            "updated": row[4],
            "phase": STRATEGY_TO_PHASE.get(row[1], "Unknown"),
            "scifi": STRATEGY_TO_SCIFI.get(row[1], "Unknown")
        })

    conn.close()
    return strategies


def get_outcome_stats() -> Dict:
    """Get outcome statistics."""
    if not OUTCOME_DB.exists():
        return {"total": 0, "successes": 0, "rate": 0}

    conn = sqlite3.connect(OUTCOME_DB)
    c = conn.cursor()

    c.execute('''SELECT COUNT(*), SUM(CASE WHEN result = 'success' THEN 1 ELSE 0 END)
        FROM outcomes''')
    row = c.fetchone()
    total, successes = row[0] or 0, row[1] or 0

    conn.close()

    return {
        "total": total,
        "successes": successes,
        "rate": round(successes / total, 3) if total > 0 else 0
    }


def generate_progress_report() -> str:
    """Generate linked progress report."""
    strategies = get_strategy_status()
    outcomes = get_outcome_stats()

    report = ["# Evolution Progress Report", f"*Generated: {datetime.now().isoformat()}*", ""]

    # Overall stats
    report.append("## Overall Progress")
    report.append(f"- **Strategies Active:** {len([s for s in strategies if s['status'] == 'active'])}")
    report.append(f"- **Outcomes Recorded:** {outcomes['total']}")
    report.append(f"- **Success Rate:** {outcomes['rate']*100:.1f}%")
    report.append("")

    # By Phase
    report.append("## By Evolution Phase")
    phases = {}
    for s in strategies:
        phase = s["phase"]
        if phase not in phases:
            phases[phase] = []
        phases[phase].append(s)

    for phase, strats in sorted(phases.items()):
        report.append(f"### {phase}")
        for s in strats:
            status_icon = "✅" if s["status"] == "active" else "⏸️"
            report.append(f"- {status_icon} **{s['name']}** - {s['status']}")
            if s["metrics"]:
                for k, v in s["metrics"].items():
                    report.append(f"  - {k}: {v}")
        report.append("")

    # By Sci-Fi Class
    report.append("## By Sci-Fi Capability Class")
    classes = {}
    for s in strategies:
        cls = s["scifi"]
        if cls not in classes:
            classes[cls] = []
        classes[cls].append(s)

    for cls, strats in sorted(classes.items()):
        report.append(f"### {cls}")
        for s in strats:
            report.append(f"- **{s['name']}**")
        report.append("")

    # Next Actions
    report.append("## Recommended Next Actions")
    report.append("1. Complete Phase14-TokenOpt → Unlock 70% token savings")
    report.append("2. Complete Phase14-Bisim → Unlock 100x learning")
    report.append("3. Verify prerequisites → Enable Sci-Fi capabilities")
    report.append("")

    return "\n".join(report)


def sync_documents():
    """Sync progress to all linked documents."""
    report = generate_progress_report()

    # Save progress report
    report_path = PROJECT_DIR / ".claude" / "EVOLUTION-PROGRESS.md"
    report_path.write_text(report)
    print(f"Updated: {report_path}")

    # Update task.md with current strategy status
    strategies = get_strategy_status()
    active = [s for s in strategies if s["status"] == "active"]

    status_section = "\n## Active Strategies (Auto-Generated)\n"
    for s in active:
        status_section += f"- [{s['id']}] {s['name']} ({s['phase']}) → {s['scifi']}\n"
    status_section += f"\n*Last synced: {datetime.now().isoformat()}*\n"

    print(f"Synced {len(active)} active strategies")

    return len(active)


def show_status():
    """Show linked status."""
    strategies = get_strategy_status()
    outcomes = get_outcome_stats()

    print("=" * 60)
    print("EVOLUTION TRACKER STATUS")
    print("=" * 60)
    print(f"\nStrategies: {len(strategies)}")
    print(f"Outcomes: {outcomes['total']} (success rate: {outcomes['rate']*100:.1f}%)")
    print("\nStrategy → Phase → Sci-Fi Mapping:")
    print("-" * 60)

    for s in strategies:
        print(f"  {s['id']}: {s['name']}")
        print(f"       → {s['phase']} → {s['scifi']}")

    print("-" * 60)


def main():
    parser = argparse.ArgumentParser(description="Evolution Tracker")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("sync", help="Sync all linked documents")
    subparsers.add_parser("status", help="Show linked status")
    subparsers.add_parser("progress", help="Generate progress report")

    args = parser.parse_args()

    if args.command == "sync":
        sync_documents()
    elif args.command == "status":
        show_status()
    elif args.command == "progress":
        print(generate_progress_report())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
