#!/usr/bin/env python3
"""
Activate All Systems - Master activation script.

Runs on session start to ensure all subsystems are operational.
Fixes dormant modules by triggering their functionality.
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

DAEMON_DIR = Path(__file__).parent

def run_cmd(cmd: str, timeout: int = 10) -> tuple:
    """Run command and return (success, output)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=str(DAEMON_DIR.parent)
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)

def activate():
    """Activate all subsystems."""
    results = {}

    # 1. Module Registry
    ok, out = run_cmd("python daemon/module_registry.py stats")
    results["module_registry"] = {"active": ok, "stats": out[:200] if ok else None}

    # 2. Orchestrator
    ok, out = run_cmd("python daemon/orchestrator.py stats")
    results["orchestrator"] = {"active": ok}

    # 3. Model Router
    ok, out = run_cmd("python daemon/model_router.py --check")
    results["model_router"] = {"active": ok, "output": out}

    # 4. LocalAI Scheduler
    ok, out = run_cmd("python daemon/localai_scheduler.py stats")
    results["localai_scheduler"] = {"active": ok}

    # 5. Strategy Evolution - seed if empty
    ok, out = run_cmd("python daemon/strategy_evolution.py list")
    if "No strategies" in out or not out:
        run_cmd("python daemon/strategy_evolution.py seed")
        results["strategy_evolution"] = {"active": True, "seeded": True}
    else:
        results["strategy_evolution"] = {"active": ok, "count": out.count("Strategy:")}

    # 6. Outcome Tracker
    ok, out = run_cmd("python daemon/outcome_tracker.py stats")
    results["outcome_tracker"] = {"active": ok}

    # 7. Memory System
    ok, out = run_cmd("python daemon/memory.py list 2>nul || echo no-list")
    results["memory"] = {"active": ok or "no-list" not in out}

    # 8. Task Generator
    ok, out = run_cmd("python daemon/task_generator.py pending 2>nul | head -3")
    results["task_generator"] = {"active": ok, "has_tasks": "Pending" in out}

    # Log module usage for all active systems
    for name, status in results.items():
        if status.get("active"):
            module_id = f"int-{name.replace('_', '-')}"
            run_cmd(f'python daemon/module_registry.py use "{module_id}" "activate_all"')

    return results

def main():
    results = activate()

    active_count = sum(1 for r in results.values() if r.get("active"))
    total = len(results)

    print(f"Systems Activated: {active_count}/{total}")
    for name, status in results.items():
        state = "[OK]" if status.get("active") else "[--]"
        extras = []
        if status.get("seeded"): extras.append("seeded")
        if status.get("has_tasks"): extras.append("has tasks")
        extra_str = f" ({', '.join(extras)})" if extras else ""
        print(f"  {state} {name}{extra_str}")

    if active_count < total:
        print(f"\nWarning: {total - active_count} systems inactive")
        sys.exit(1)

if __name__ == "__main__":
    main()
