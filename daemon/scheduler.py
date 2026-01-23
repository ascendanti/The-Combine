#!/usr/bin/env python3
"""Task Scheduler - Cron-like scheduled task submission.

Supports:
- Periodic tasks (every N minutes/hours/days)
- Daily tasks at specific times
- Weekly tasks on specific days
- One-time scheduled tasks

Usage:
    python scheduler.py add "Daily summary" --daily 09:00
    python scheduler.py add "Weekly review" --weekly monday 10:00
    python scheduler.py add "Hourly check" --every 1h
    python scheduler.py list
    python scheduler.py run
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum
import sys

sys.path.insert(0, str(Path(__file__).parent))
from queue import TaskQueue, TaskPriority


class ScheduleType(str, Enum):
    PERIODIC = "periodic"  # Every N seconds
    DAILY = "daily"        # At specific time each day
    WEEKLY = "weekly"      # On specific day at time
    ONCE = "once"          # One-time at datetime


@dataclass
class ScheduledTask:
    id: str
    name: str
    prompt: str
    schedule_type: ScheduleType
    schedule_value: str  # JSON: {"interval": 3600} or {"time": "09:00"} or {"day": "monday", "time": "10:00"}
    priority: TaskPriority
    last_run: Optional[str]
    next_run: str
    enabled: bool


class TaskScheduler:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(__file__).parent / "scheduler.db"
        self.queue = TaskQueue()
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                prompt TEXT NOT NULL,
                schedule_type TEXT NOT NULL,
                schedule_value TEXT NOT NULL,
                priority TEXT DEFAULT 'normal',
                last_run TEXT,
                next_run TEXT NOT NULL,
                enabled INTEGER DEFAULT 1
            )
        """)
        conn.commit()
        conn.close()

    def add(
        self,
        name: str,
        prompt: str,
        schedule_type: ScheduleType,
        schedule_value: dict,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> ScheduledTask:
        import uuid
        task_id = str(uuid.uuid4())
        next_run = self._calculate_next_run(schedule_type, schedule_value, None)

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO scheduled_tasks (id, name, prompt, schedule_type, schedule_value, priority, next_run)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (task_id, name, prompt, schedule_type.value, json.dumps(schedule_value),
              priority.name.lower(), next_run.isoformat()))
        conn.commit()
        conn.close()

        return ScheduledTask(
            id=task_id, name=name, prompt=prompt, schedule_type=schedule_type,
            schedule_value=json.dumps(schedule_value), priority=priority,
            last_run=None, next_run=next_run.isoformat(), enabled=True
        )

    def list_tasks(self) -> List[ScheduledTask]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM scheduled_tasks ORDER BY next_run").fetchall()
        conn.close()

        priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL,
                        "high": TaskPriority.HIGH, "urgent": TaskPriority.URGENT}
        return [ScheduledTask(
            id=r['id'], name=r['name'], prompt=r['prompt'],
            schedule_type=ScheduleType(r['schedule_type']),
            schedule_value=r['schedule_value'],
            priority=priority_map.get(r['priority'], TaskPriority.NORMAL),
            last_run=r['last_run'], next_run=r['next_run'],
            enabled=bool(r['enabled'])
        ) for r in rows]

    def check_and_submit(self) -> int:
        """Check for due tasks and submit them. Returns count submitted."""
        now = datetime.now()
        submitted = 0

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        due_tasks = conn.execute("""
            SELECT * FROM scheduled_tasks
            WHERE enabled = 1 AND next_run <= ?
        """, (now.isoformat(),)).fetchall()

        priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL,
                        "high": TaskPriority.HIGH, "urgent": TaskPriority.URGENT}
        for row in due_tasks:
            # Submit to queue
            self.queue.add_task(
                row['prompt'],
                priority_map.get(row['priority'], TaskPriority.NORMAL),
                metadata={"source": "scheduler", "scheduled_task": row['name']}
            )

            # Calculate next run
            schedule_value = json.loads(row['schedule_value'])
            schedule_type = ScheduleType(row['schedule_type'])

            if schedule_type == ScheduleType.ONCE:
                # Disable one-time tasks
                conn.execute("UPDATE scheduled_tasks SET enabled = 0 WHERE id = ?", (row['id'],))
            else:
                next_run = self._calculate_next_run(schedule_type, schedule_value, now)
                conn.execute("""
                    UPDATE scheduled_tasks SET last_run = ?, next_run = ? WHERE id = ?
                """, (now.isoformat(), next_run.isoformat(), row['id']))

            submitted += 1

        conn.commit()
        conn.close()
        return submitted

    def _calculate_next_run(self, schedule_type: ScheduleType, value: dict, after: Optional[datetime]) -> datetime:
        now = after or datetime.now()

        if schedule_type == ScheduleType.PERIODIC:
            interval = value.get("interval", 3600)
            return now + timedelta(seconds=interval)

        elif schedule_type == ScheduleType.DAILY:
            time_str = value.get("time", "09:00")
            hour, minute = map(int, time_str.split(":"))
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run

        elif schedule_type == ScheduleType.WEEKLY:
            day_name = value.get("day", "monday").lower()
            time_str = value.get("time", "09:00")
            hour, minute = map(int, time_str.split(":"))

            days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            target_day = days.index(day_name)
            current_day = now.weekday()

            days_ahead = target_day - current_day
            if days_ahead <= 0:
                days_ahead += 7

            next_run = now + timedelta(days=days_ahead)
            next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return next_run

        elif schedule_type == ScheduleType.ONCE:
            # Value should contain full datetime
            return datetime.fromisoformat(value.get("datetime", now.isoformat()))

        return now + timedelta(hours=1)

    def run(self, check_interval: int = 60):
        """Run scheduler loop."""
        print(f"Scheduler running. Checking every {check_interval}s")
        try:
            while True:
                submitted = self.check_and_submit()
                if submitted:
                    print(f"Submitted {submitted} scheduled task(s)")
                time.sleep(check_interval)
        except KeyboardInterrupt:
            print("\nScheduler stopped")


def parse_interval(s: str) -> int:
    """Parse interval string like '1h', '30m', '1d' to seconds."""
    s = s.lower().strip()
    if s.endswith('s'):
        return int(s[:-1])
    elif s.endswith('m'):
        return int(s[:-1]) * 60
    elif s.endswith('h'):
        return int(s[:-1]) * 3600
    elif s.endswith('d'):
        return int(s[:-1]) * 86400
    return int(s)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task Scheduler")
    subparsers = parser.add_subparsers(dest="command")

    # Add task
    add_parser = subparsers.add_parser("add", help="Add scheduled task")
    add_parser.add_argument("name", help="Task name")
    add_parser.add_argument("--prompt", default="", help="Task prompt (or use name)")
    add_parser.add_argument("--every", help="Periodic interval (e.g., 1h, 30m)")
    add_parser.add_argument("--daily", help="Daily at time (e.g., 09:00)")
    add_parser.add_argument("--weekly", nargs=2, metavar=("DAY", "TIME"), help="Weekly (e.g., monday 09:00)")
    add_parser.add_argument("--priority", choices=["low", "normal", "high", "urgent"], default="normal")

    # List
    subparsers.add_parser("list", help="List scheduled tasks")

    # Run
    run_parser = subparsers.add_parser("run", help="Run scheduler")
    run_parser.add_argument("--interval", type=int, default=60, help="Check interval in seconds")

    args = parser.parse_args()
    scheduler = TaskScheduler()

    if args.command == "add":
        prompt = args.prompt or args.name
        priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL,
                        "high": TaskPriority.HIGH, "urgent": TaskPriority.URGENT}
        priority = priority_map.get(args.priority, TaskPriority.NORMAL)

        if args.every:
            interval = parse_interval(args.every)
            task = scheduler.add(args.name, prompt, ScheduleType.PERIODIC,
                                {"interval": interval}, priority)
            print(f"Added periodic task: {task.name} (every {args.every})")

        elif args.daily:
            task = scheduler.add(args.name, prompt, ScheduleType.DAILY,
                                {"time": args.daily}, priority)
            print(f"Added daily task: {task.name} at {args.daily}")

        elif args.weekly:
            day, time = args.weekly
            task = scheduler.add(args.name, prompt, ScheduleType.WEEKLY,
                                {"day": day, "time": time}, priority)
            print(f"Added weekly task: {task.name} on {day} at {time}")

        else:
            print("Specify --every, --daily, or --weekly")

    elif args.command == "list":
        tasks = scheduler.list_tasks()
        if not tasks:
            print("No scheduled tasks")
        else:
            for t in tasks:
                status = "[ON]" if t.enabled else "[OFF]"
                print(f"{status} [{t.schedule_type.value:8}] {t.name}")
                print(f"  Next: {t.next_run}")

    elif args.command == "run":
        scheduler.run(args.interval)

    else:
        parser.print_help()
