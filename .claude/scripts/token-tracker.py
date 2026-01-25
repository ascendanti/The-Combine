#!/usr/bin/env python3
"""
Token Tracker - Python port of claudelytics core functionality.

Reads Claude Code session JSONL files and provides:
- Daily/session token usage reports
- Cost tracking with current pricing
- Export to CSV

Usage:
    python token-tracker.py                 # Show today's usage
    python token-tracker.py --daily         # Daily breakdown
    python token-tracker.py --session       # Per-session breakdown
    python token-tracker.py --cost          # Cost summary
    python token-tracker.py --export        # Export to CSV
    python token-tracker.py --watch         # Real-time monitoring
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import csv


# Claude pricing (per 1M tokens) - Jan 2025
PRICING = {
    "claude-opus-4-5-20251101": {"input": 15.00, "output": 75.00, "cache_read": 1.50, "cache_write": 18.75},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
    "claude-3-5-sonnet-20240620": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25, "cache_read": 0.03, "cache_write": 0.30},
    # Default fallback
    "default": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
}


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation: int = 0
    cache_read: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens + self.cache_creation + self.cache_read

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_creation=self.cache_creation + other.cache_creation,
            cache_read=self.cache_read + other.cache_read,
        )


@dataclass
class SessionStats:
    session_id: str
    project: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    cost_usd: float = 0.0
    first_timestamp: Optional[datetime] = None
    last_timestamp: Optional[datetime] = None
    model: str = "unknown"
    message_count: int = 0


def get_pricing(model: str) -> Dict[str, float]:
    """Get pricing for a model, with fallback to default."""
    for key in PRICING:
        if key in model.lower():
            return PRICING[key]
    return PRICING["default"]


def calculate_cost(usage: TokenUsage, model: str) -> float:
    """Calculate cost in USD for given token usage."""
    prices = get_pricing(model)
    cost = 0.0
    cost += (usage.input_tokens / 1_000_000) * prices["input"]
    cost += (usage.output_tokens / 1_000_000) * prices["output"]
    cost += (usage.cache_read / 1_000_000) * prices["cache_read"]
    cost += (usage.cache_creation / 1_000_000) * prices["cache_write"]
    return cost


def parse_jsonl_file(filepath: Path) -> List[Tuple[datetime, TokenUsage, str, float]]:
    """Parse a JSONL session file and extract token usage."""
    results = []

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)

                    # Extract timestamp
                    ts_str = data.get("timestamp")
                    if ts_str:
                        try:
                            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        except:
                            ts = datetime.now()
                    else:
                        ts = datetime.now()

                    # Extract model
                    model = data.get("model", "unknown")

                    # Extract cost if provided
                    cost_usd = data.get("costUSD", 0.0) or 0.0

                    # Extract usage from message.usage
                    usage_data = data.get("message", {}).get("usage", {})
                    if not usage_data:
                        # Try direct usage field
                        usage_data = data.get("usage", {})

                    if usage_data:
                        usage = TokenUsage(
                            input_tokens=usage_data.get("input_tokens", 0) or 0,
                            output_tokens=usage_data.get("output_tokens", 0) or 0,
                            cache_creation=usage_data.get("cache_creation_input_tokens", 0) or 0,
                            cache_read=usage_data.get("cache_read_input_tokens", 0) or 0,
                        )

                        if usage.total > 0:
                            results.append((ts, usage, model, cost_usd))

                except json.JSONDecodeError:
                    continue

    except Exception as e:
        pass  # Skip files that can't be read

    return results


def scan_claude_directory(claude_dir: Path, since: Optional[date] = None) -> Dict[str, SessionStats]:
    """Scan Claude directory for all session data."""
    sessions: Dict[str, SessionStats] = {}

    projects_dir = claude_dir / "projects"
    if not projects_dir.exists():
        return sessions

    # Find all JSONL files
    for jsonl_file in projects_dir.rglob("*.jsonl"):
        # Extract project and session from path
        rel_path = jsonl_file.relative_to(projects_dir)
        parts = list(rel_path.parts)

        if len(parts) >= 2:
            project = parts[0]
            session_id = parts[-2] if parts[-2] != project else jsonl_file.stem
        else:
            project = "unknown"
            session_id = jsonl_file.stem

        # Parse the file
        entries = parse_jsonl_file(jsonl_file)

        if not entries:
            continue

        # Initialize or update session stats
        key = f"{project}/{session_id}"
        if key not in sessions:
            sessions[key] = SessionStats(
                session_id=session_id,
                project=project,
            )

        session = sessions[key]

        for ts, usage, model, cost in entries:
            # Date filter
            if since and ts.date() < since:
                continue

            session.usage = session.usage + usage
            session.cost_usd += cost if cost > 0 else calculate_cost(usage, model)
            session.message_count += 1
            session.model = model

            if session.first_timestamp is None or ts < session.first_timestamp:
                session.first_timestamp = ts
            if session.last_timestamp is None or ts > session.last_timestamp:
                session.last_timestamp = ts

    return sessions


def format_tokens(n: int) -> str:
    """Format token count with K/M suffix."""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def format_cost(cost: float) -> str:
    """Format cost in USD."""
    return f"${cost:.2f}"


def print_daily_report(sessions: Dict[str, SessionStats], today_only: bool = False):
    """Print daily usage breakdown."""
    # Group by date
    by_date: Dict[date, TokenUsage] = defaultdict(TokenUsage)
    cost_by_date: Dict[date, float] = defaultdict(float)

    for session in sessions.values():
        if session.first_timestamp:
            d = session.first_timestamp.date()
            if today_only and d != date.today():
                continue
            by_date[d] = by_date[d] + session.usage
            cost_by_date[d] += session.cost_usd

    if not by_date:
        print("No usage data found.")
        return

    # Calculate totals
    total_usage = TokenUsage()
    total_cost = 0.0
    for d in by_date:
        total_usage = total_usage + by_date[d]
        total_cost += cost_by_date[d]

    print("\n" + "=" * 70)
    print("  CLAUDE CODE TOKEN USAGE REPORT")
    print("=" * 70)
    print(f"  Total Cost: {format_cost(total_cost)}  |  Total Tokens: {format_tokens(total_usage.total)}")
    print(f"  Input: {format_tokens(total_usage.input_tokens)}  |  Output: {format_tokens(total_usage.output_tokens)}")
    print(f"  Cache Read: {format_tokens(total_usage.cache_read)}  |  Cache Write: {format_tokens(total_usage.cache_creation)}")
    print("=" * 70)

    print("\n  Date           | Tokens      | Cost     | In/Out Ratio")
    print("  " + "-" * 60)

    for d in sorted(by_date.keys(), reverse=True):
        usage = by_date[d]
        cost = cost_by_date[d]
        ratio = usage.input_tokens / max(usage.output_tokens, 1)

        marker = " [TODAY]" if d == date.today() else ""
        print(f"  {d}    | {format_tokens(usage.total):>10} | {format_cost(cost):>8} | {ratio:.2f}:1{marker}")

    print()


def print_session_report(sessions: Dict[str, SessionStats], today_only: bool = False):
    """Print per-session usage breakdown."""
    # Filter sessions
    filtered = []
    for key, session in sessions.items():
        if today_only and session.first_timestamp and session.first_timestamp.date() != date.today():
            continue
        filtered.append((key, session))

    if not filtered:
        print("No sessions found.")
        return

    # Sort by last activity
    filtered.sort(key=lambda x: x[1].last_timestamp or datetime.min, reverse=True)

    print("\n" + "=" * 80)
    print("  SESSION USAGE REPORT")
    print("=" * 80)

    total_cost = sum(s.cost_usd for _, s in filtered)
    total_tokens = sum(s.usage.total for _, s in filtered)

    print(f"  Sessions: {len(filtered)}  |  Total Cost: {format_cost(total_cost)}  |  Tokens: {format_tokens(total_tokens)}")
    print("=" * 80)

    print("\n  Project/Session                    | Tokens     | Cost    | Msgs | Last Activity")
    print("  " + "-" * 75)

    for key, session in filtered[:20]:  # Show top 20
        short_key = key[:35] + "..." if len(key) > 38 else key
        last_time = session.last_timestamp.strftime("%H:%M") if session.last_timestamp else "N/A"

        print(f"  {short_key:<38} | {format_tokens(session.usage.total):>9} | {format_cost(session.cost_usd):>7} | {session.message_count:>4} | {last_time}")

    if len(filtered) > 20:
        print(f"\n  ... and {len(filtered) - 20} more sessions")

    print()


def print_cost_summary(sessions: Dict[str, SessionStats], today_only: bool = False):
    """Print cost summary."""
    if today_only:
        sessions = {k: v for k, v in sessions.items()
                   if v.first_timestamp and v.first_timestamp.date() == date.today()}

    total_cost = sum(s.cost_usd for s in sessions.values())
    total_tokens = sum(s.usage.total for s in sessions.values())

    label = "Today's" if today_only else "Total"

    print(f"\n  {label} Usage Cost")
    print("  " + "-" * 30)
    print(f"  Cost: {format_cost(total_cost)}")
    print(f"  Tokens: {format_tokens(total_tokens)}")
    print()


def export_csv(sessions: Dict[str, SessionStats], output_dir: Path):
    """Export data to CSV files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Sessions CSV
    sessions_file = output_dir / f"sessions_{date.today().isoformat()}.csv"
    with open(sessions_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["project", "session_id", "input_tokens", "output_tokens",
                        "cache_read", "cache_write", "total_tokens", "cost_usd",
                        "messages", "first_activity", "last_activity", "model"])

        for key, s in sessions.items():
            writer.writerow([
                s.project,
                s.session_id,
                s.usage.input_tokens,
                s.usage.output_tokens,
                s.usage.cache_read,
                s.usage.cache_creation,
                s.usage.total,
                f"{s.cost_usd:.4f}",
                s.message_count,
                s.first_timestamp.isoformat() if s.first_timestamp else "",
                s.last_timestamp.isoformat() if s.last_timestamp else "",
                s.model,
            ])

    print(f"  Exported to: {sessions_file}")

    # Daily summary CSV
    by_date: Dict[date, TokenUsage] = defaultdict(TokenUsage)
    cost_by_date: Dict[date, float] = defaultdict(float)

    for session in sessions.values():
        if session.first_timestamp:
            d = session.first_timestamp.date()
            by_date[d] = by_date[d] + session.usage
            cost_by_date[d] += session.cost_usd

    daily_file = output_dir / f"daily_{date.today().isoformat()}.csv"
    with open(daily_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "input_tokens", "output_tokens", "cache_read",
                        "cache_write", "total_tokens", "cost_usd"])

        for d in sorted(by_date.keys()):
            usage = by_date[d]
            writer.writerow([
                d.isoformat(),
                usage.input_tokens,
                usage.output_tokens,
                usage.cache_read,
                usage.cache_creation,
                usage.total,
                f"{cost_by_date[d]:.4f}",
            ])

    print(f"  Exported to: {daily_file}")


def watch_mode(claude_dir: Path, interval: int = 5):
    """Real-time monitoring mode."""
    print("\n  REAL-TIME TOKEN MONITORING")
    print("  " + "-" * 40)
    print(f"  Watching: {claude_dir}")
    print(f"  Refresh: every {interval}s")
    print("  Press Ctrl+C to stop\n")

    last_total = 0

    try:
        while True:
            # Clear screen (cross-platform)
            os.system('cls' if os.name == 'nt' else 'clear')

            sessions = scan_claude_directory(claude_dir, since=date.today())

            total_tokens = sum(s.usage.total for s in sessions.values())
            total_cost = sum(s.cost_usd for s in sessions.values())

            delta = total_tokens - last_total
            burn_rate = delta / interval if last_total > 0 else 0

            print("\n  CLAUDE CODE - LIVE MONITOR")
            print("  " + "=" * 50)
            print(f"  Time: {datetime.now().strftime('%H:%M:%S')}")
            print(f"  Today's Tokens: {format_tokens(total_tokens)}")
            print(f"  Today's Cost: {format_cost(total_cost)}")
            print(f"  Burn Rate: {format_tokens(int(burn_rate * 60))}/min")
            print("  " + "=" * 50)

            # Show active sessions (activity in last 5 min)
            cutoff = datetime.now() - timedelta(minutes=5)
            active = [(k, s) for k, s in sessions.items()
                     if s.last_timestamp and s.last_timestamp.replace(tzinfo=None) > cutoff]

            if active:
                print("\n  ACTIVE SESSIONS:")
                for key, session in active[:5]:
                    short_key = key[:40] + "..." if len(key) > 43 else key
                    print(f"    {short_key}")
            else:
                print("\n  No active sessions in last 5 minutes")

            last_total = total_tokens
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n  Monitoring stopped.\n")


def main():
    parser = argparse.ArgumentParser(description="Claude Code Token Tracker")
    parser.add_argument("--daily", action="store_true", help="Show daily breakdown")
    parser.add_argument("--session", action="store_true", help="Show session breakdown")
    parser.add_argument("--cost", action="store_true", help="Show cost summary")
    parser.add_argument("--today", action="store_true", help="Filter to today only")
    parser.add_argument("--export", action="store_true", help="Export to CSV")
    parser.add_argument("--watch", action="store_true", help="Real-time monitoring")
    parser.add_argument("--since", type=str, help="Filter since date (YYYYMMDD)")
    parser.add_argument("--path", type=str, help="Custom Claude directory path")
    parser.add_argument("-o", "--output", type=str, default="./reports", help="Export output directory")

    args = parser.parse_args()

    # Determine Claude directory
    claude_dir = Path(args.path) if args.path else Path.home() / ".claude"

    if not claude_dir.exists():
        print(f"Error: Claude directory not found: {claude_dir}")
        sys.exit(1)

    # Parse since date
    since_date = None
    if args.since:
        try:
            since_date = datetime.strptime(args.since, "%Y%m%d").date()
        except ValueError:
            print(f"Error: Invalid date format. Use YYYYMMDD")
            sys.exit(1)

    if args.today:
        since_date = date.today()

    # Watch mode
    if args.watch:
        watch_mode(claude_dir)
        return

    # Scan directory
    print(f"\n  Scanning: {claude_dir}...")
    sessions = scan_claude_directory(claude_dir, since=since_date)

    if not sessions:
        print("  No session data found.")
        return

    # Generate reports
    if args.export:
        export_csv(sessions, Path(args.output))
    elif args.cost:
        print_cost_summary(sessions, args.today)
    elif args.session:
        print_session_report(sessions, args.today)
    else:
        # Default: daily report
        print_daily_report(sessions, args.today)


if __name__ == "__main__":
    main()
