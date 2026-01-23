#!/usr/bin/env python3
"""Simple task submission script.

Usage:
    python daemon/submit.py "Your task prompt here"
    python daemon/submit.py "Urgent task" --priority urgent
    python daemon/submit.py --list
    python daemon/submit.py --status <task_id>
"""

import sys
from pathlib import Path

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent))

from queue import TaskQueue, TaskPriority


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Submit tasks to Claude daemon")
    parser.add_argument("prompt", nargs="?", help="Task prompt")
    parser.add_argument("--priority", "-p",
                       choices=["low", "normal", "high", "urgent"],
                       default="normal",
                       help="Task priority (default: normal)")
    parser.add_argument("--list", "-l", action="store_true",
                       help="List recent tasks")
    parser.add_argument("--pending", action="store_true",
                       help="List pending tasks only")
    parser.add_argument("--status", "-s", metavar="TASK_ID",
                       help="Get status of specific task")
    parser.add_argument("--cancel", "-c", metavar="TASK_ID",
                       help="Cancel a pending task")

    args = parser.parse_args()
    queue = TaskQueue()

    if args.list:
        tasks = queue.get_recent_tasks(20)
        if not tasks:
            print("No tasks found")
            return

        print(f"{'STATUS':<12} {'ID':<10} {'CREATED':<20} {'PROMPT'}")
        print("-" * 70)
        for t in tasks:
            created = t.created_at[:19] if t.created_at else ""
            print(f"{t.status.value:<12} {t.id[:8]:<10} {created:<20} {t.prompt[:40]}")

    elif args.pending:
        tasks = queue.get_pending_tasks(20)
        if not tasks:
            print("No pending tasks")
            return

        print(f"{'PRIORITY':<10} {'ID':<10} {'CREATED':<20} {'PROMPT'}")
        print("-" * 70)
        for t in tasks:
            created = t.created_at[:19] if t.created_at else ""
            pri = ["LOW", "NORMAL", "HIGH", "URGENT"][t.priority.value]
            print(f"{pri:<10} {t.id[:8]:<10} {created:<20} {t.prompt[:40]}")

    elif args.status:
        task = queue.get_task(args.status)
        if task:
            print(f"ID:        {task.id}")
            print(f"Status:    {task.status.value}")
            print(f"Priority:  {task.priority.name}")
            print(f"Created:   {task.created_at}")
            print(f"Started:   {task.started_at or 'N/A'}")
            print(f"Completed: {task.completed_at or 'N/A'}")
            print(f"Prompt:    {task.prompt}")
            if task.result:
                print(f"\nResult:\n{task.result[:500]}")
            if task.error:
                print(f"\nError:\n{task.error}")
        else:
            # Try partial match
            all_tasks = queue.get_recent_tasks(100)
            matches = [t for t in all_tasks if t.id.startswith(args.status)]
            if matches:
                task = matches[0]
                print(f"Found: {task.id}")
                print(f"Status: {task.status.value}")
                print(f"Prompt: {task.prompt}")
            else:
                print(f"Task not found: {args.status}")

    elif args.cancel:
        # Handle partial IDs
        all_tasks = queue.get_pending_tasks(100)
        matches = [t for t in all_tasks if t.id.startswith(args.cancel)]

        if not matches:
            print(f"No pending task found matching: {args.cancel}")
        elif len(matches) > 1:
            print(f"Multiple matches, be more specific:")
            for t in matches:
                print(f"  {t.id}")
        else:
            if queue.cancel_task(matches[0].id):
                print(f"Cancelled: {matches[0].id}")
            else:
                print(f"Could not cancel: {matches[0].id}")

    elif args.prompt:
        priority_map = {
            "low": TaskPriority.LOW,
            "normal": TaskPriority.NORMAL,
            "high": TaskPriority.HIGH,
            "urgent": TaskPriority.URGENT
        }
        task = queue.add_task(args.prompt, priority_map[args.priority])
        print(f"Task submitted: {task.id}")
        print(f"Priority: {args.priority}")
        print(f"Prompt: {task.prompt[:60]}...")
        print(f"\nStart daemon with: python daemon/runner.py")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
