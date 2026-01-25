#!/usr/bin/env python3
"""
Claude Cognitive History Viewer
Usage:
  python3 history.py                    # Last 20 turns
  python3 history.py --since 2h         # Last 2 hours
  python3 history.py --file ppe         # Filter by file pattern
  python3 history.py --instance A       # Filter by instance
  python3 history.py --transitions      # Show only turns with tier changes
  python3 history.py --stats            # Show summary statistics
  python3 history.py --format json      # Output raw JSON
"""

import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter
import re

HISTORY_FILE = Path.home() / ".claude" / "attention_history.jsonl"


def parse_duration(s: str) -> timedelta:
    """Parse '2h', '30m', '1d' into timedelta."""
    match = re.match(r'(\d+)([hdm])', s.lower())
    if not match:
        return timedelta(hours=1)
    val, unit = int(match.group(1)), match.group(2)
    if unit == 'h':
        return timedelta(hours=val)
    if unit == 'd':
        return timedelta(days=val)
    if unit == 'm':
        return timedelta(minutes=val)
    return timedelta(hours=1)


def load_history(
    since: timedelta = None,
    instance: str = None,
    file_pattern: str = None,
    transitions_only: bool = False
) -> list:
    """Load and filter history entries."""
    if not HISTORY_FILE.exists():
        return []

    cutoff = datetime.now() - since if since else None
    entries = []

    with open(HISTORY_FILE) as f:
        for line in f:
            try:
                entry = json.loads(line.strip())

                # Time filter
                if cutoff:
                    entry_time = datetime.fromisoformat(entry["timestamp"])
                    if entry_time < cutoff:
                        continue

                # Instance filter
                if instance and entry.get("instance_id") != instance:
                    continue

                # File pattern filter
                if file_pattern:
                    all_files = entry.get("hot", []) + entry.get("warm", []) + entry.get("activated", [])
                    if not any(file_pattern.lower() in f.lower() for f in all_files):
                        continue

                # Transitions filter
                if transitions_only:
                    trans = entry.get("transitions", {})
                    if not any(trans.get(k) for k in ["to_hot", "to_warm", "to_cold"]):
                        continue

                entries.append(entry)
            except json.JSONDecodeError:
                continue

    return entries


def format_stats(entries: list) -> str:
    """Format summary statistics."""
    if not entries:
        return "No entries to analyze."

    lines = []
    lines.append("\n╔══════════════════════════════════════════════════════════════╗")
    lines.append("║                    ATTENTION STATISTICS                      ║")
    lines.append("╚══════════════════════════════════════════════════════════════╝\n")

    # Basic counts
    lines.append(f"Total turns: {len(entries)}")
    lines.append(f"Time range: {entries[0]['timestamp'][:10]} to {entries[-1]['timestamp'][:10]}")

    # Instance breakdown
    instances = Counter(e.get("instance_id", "default") for e in entries)
    lines.append(f"\nInstances: {dict(instances)}")

    # Most HOT files
    hot_counter = Counter()
    for entry in entries:
        for f in entry.get("hot", []):
            hot_counter[f] += 1

    lines.append(f"\nMost frequently HOT:")
    for file, count in hot_counter.most_common(5):
        lines.append(f"  {count:3d} turns: {Path(file).name}")

    # Most transitions
    transition_counter = Counter()
    for entry in entries:
        trans = entry.get("transitions", {})
        for f in trans.get("to_hot", []):
            transition_counter[f] += 1

    lines.append(f"\nMost promoted to HOT:")
    for file, count in transition_counter.most_common(5):
        lines.append(f"  {count:3d} times: {Path(file).name}")

    # Daily activity
    daily_counter = Counter()
    for entry in entries:
        day = entry["timestamp"][:10]
        daily_counter[day] += 1

    lines.append(f"\nBusiest days:")
    for day, count in sorted(daily_counter.items(), key=lambda x: x[1], reverse=True)[:5]:
        lines.append(f"  {day}: {count} turns")

    # Average context size
    avg_chars = sum(e.get("total_chars", 0) for e in entries) / len(entries)
    lines.append(f"\nAverage context size: {avg_chars:,.0f} chars")

    return "\n".join(lines)


def format_changelog(entries: list) -> str:
    """Format entries as human-readable changelog."""
    lines = []
    current_day = None

    for entry in entries:
        ts = datetime.fromisoformat(entry["timestamp"])
        day = ts.strftime("%Y-%m-%d")

        if day != current_day:
            lines.append(f"\n{'='*60}")
            lines.append(f"  {day}")
            lines.append(f"{'='*60}")
            current_day = day

        time_str = ts.strftime("%H:%M:%S")
        instance = entry.get("instance_id", "?")
        turn = entry.get("turn", "?")

        lines.append(f"\n[{time_str}] Instance {instance} | Turn {turn}")

        # Keywords
        keywords = entry.get("prompt_keywords", [])
        if keywords:
            lines.append(f"  Query: {' '.join(keywords[:5])}")

        # HOT files
        hot = entry.get("hot", [])
        if hot:
            lines.append(f"  🔥 HOT: {', '.join(Path(f).name for f in hot)}")

        # WARM files
        warm = entry.get("warm", [])
        if warm:
            lines.append(f"  🌡️  WARM: {', '.join(Path(f).name for f in warm[:5])}" +
                        (f" (+{len(warm)-5} more)" if len(warm) > 5 else ""))

        # Transitions
        trans = entry.get("transitions", {})
        if trans.get("to_hot"):
            lines.append(f"  ⬆️  Promoted to HOT: {', '.join(Path(f).name for f in trans['to_hot'])}")
        if trans.get("to_cold"):
            lines.append(f"  ⬇️  Decayed to COLD: {', '.join(Path(f).name for f in trans['to_cold'])}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Claude Cognitive History Viewer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  history.py                      # Last 20 turns
  history.py --since 2h           # Last 2 hours
  history.py --file ppe           # Filter by file pattern
  history.py --transitions        # Only tier changes
  history.py --stats              # Summary statistics
  history.py --instance A         # Filter by instance
        """
    )
    parser.add_argument("--since", type=str, help="Time window (e.g., 2h, 30m, 1d)")
    parser.add_argument("--last", type=int, default=20, help="Last N entries (default: 20)")
    parser.add_argument("--instance", type=str, help="Filter by instance ID")
    parser.add_argument("--file", type=str, help="Filter by file pattern")
    parser.add_argument("--transitions", action="store_true", help="Show only turns with tier changes")
    parser.add_argument("--stats", action="store_true", help="Show summary statistics")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")

    args = parser.parse_args()

    since = parse_duration(args.since) if args.since else None
    entries = load_history(
        since=since,
        instance=args.instance,
        file_pattern=args.file,
        transitions_only=args.transitions
    )

    # Apply --last limit (unless --since specified)
    if not args.since:
        entries = entries[-args.last:]

    if not entries:
        print("No history entries found.")
        if not HISTORY_FILE.exists():
            print(f"\nHistory file not found: {HISTORY_FILE}")
            print("History tracking starts after first turn with updated router.")
        return

    if args.stats:
        print(format_stats(entries))
    elif args.format == "json":
        print(json.dumps(entries, indent=2))
    else:
        print(format_changelog(entries))
        print(f"\n[{len(entries)} entries]")


if __name__ == "__main__":
    main()
