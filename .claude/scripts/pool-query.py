#!/usr/bin/env python3
"""
Pool Query Utility
Query and filter the instance pool for debugging and coordination.

Usage:
  pool-query.py --since 5m           # Last 5 minutes
  pool-query.py --instance B         # Instance B's activity
  pool-query.py --action blocked     # Show blocked items
  pool-query.py --topic visual       # Topic contains "visual"
  pool-query.py --all                # Show all entries
"""
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Pool file location (project-local preferred, global fallback)
PROJECT_POOL = Path(".claude/pool/instance_state.jsonl")
GLOBAL_POOL = Path.home() / ".claude/pool/instance_state.jsonl"

def get_pool_file():
    """Get pool file (project-local first, global fallback)."""
    if PROJECT_POOL.parent.parent.exists():  # Check if .claude/ exists
        return PROJECT_POOL if PROJECT_POOL.exists() else GLOBAL_POOL
    return GLOBAL_POOL

POOL_FILE = get_pool_file()

def parse_time_delta(time_str):
    """Parse time strings like '5m', '2h', '30s' into seconds."""
    unit = time_str[-1]
    value = int(time_str[:-1])

    if unit == 's':
        return value
    elif unit == 'm':
        return value * 60
    elif unit == 'h':
        return value * 3600
    elif unit == 'd':
        return value * 86400
    else:
        raise ValueError(f"Unknown time unit: {unit}")

def load_pool(filters):
    """Load and filter pool entries."""
    if not POOL_FILE.exists():
        return []

    now = datetime.now().timestamp()
    entries = []

    # Parse filters
    since_seconds = None
    if filters.get('since'):
        since_seconds = parse_time_delta(filters['since'])

    with open(POOL_FILE) as f:
        for line in f:
            try:
                entry = json.loads(line)

                # Apply filters
                if since_seconds:
                    entry_age = now - entry.get("timestamp", 0)
                    if entry_age > since_seconds:
                        continue

                if filters.get('instance'):
                    if entry.get("source_instance") != filters['instance']:
                        continue

                if filters.get('action'):
                    if entry.get("action") != filters['action']:
                        continue

                if filters.get('topic'):
                    topic_search = filters['topic'].lower()
                    if topic_search not in entry.get("topic", "").lower() and \
                       topic_search not in entry.get("summary", "").lower() and \
                       topic_search not in entry.get("affects", "").lower():
                        continue

                entries.append(entry)

            except json.JSONDecodeError:
                continue

    return entries

def format_entry(entry, verbose=False):
    """Format a single entry for display."""
    ts = datetime.fromtimestamp(entry.get("timestamp", 0))
    time_str = ts.strftime("%H:%M:%S")

    source = entry.get("source_instance", "?")
    action = entry.get("action", "")
    topic = entry.get("topic", "")
    summary = entry.get("summary", "")
    affects = entry.get("affects", "")
    blocks = entry.get("blocks", "")

    lines = [
        f"[{time_str}] [{source}] {action.upper()}: {topic}",
        f"  {summary}"
    ]

    if affects:
        lines.append(f"  Affects: {affects}")

    if blocks:
        lines.append(f"  Unblocks: {blocks}")

    if verbose:
        relevance = entry.get("relevance", {})
        lines.append(f"  Relevance: {relevance}")
        lines.append(f"  ID: {entry.get('id', 'unknown')}")

    return "\n".join(lines)

def print_summary(entries):
    """Print summary statistics."""
    if not entries:
        print("No entries found.")
        return

    # Counts by instance
    by_instance = {}
    by_action = {}

    for entry in entries:
        instance = entry.get("source_instance", "?")
        action = entry.get("action", "unknown")

        by_instance[instance] = by_instance.get(instance, 0) + 1
        by_action[action] = by_action.get(action, 0) + 1

    print(f"Total entries: {len(entries)}\n")

    print("By instance:")
    for instance, count in sorted(by_instance.items()):
        print(f"  {instance}: {count}")

    print("\nBy action:")
    for action, count in sorted(by_action.items()):
        print(f"  {action}: {count}")

    print()

def main():
    parser = argparse.ArgumentParser(description="Query instance pool")
    parser.add_argument("--since", help="Time window (e.g., 5m, 2h, 1d)")
    parser.add_argument("--instance", help="Filter by instance ID")
    parser.add_argument("--action", help="Filter by action type")
    parser.add_argument("--topic", help="Filter by topic (substring match)")
    parser.add_argument("--all", action="store_true", help="Show all entries (no time filter)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--summary", "-s", action="store_true", help="Show summary only")

    args = parser.parse_args()

    # Build filters
    filters = {}
    if args.since:
        filters['since'] = args.since
    elif not args.all:
        filters['since'] = '1h'  # Default: last hour

    if args.instance:
        filters['instance'] = args.instance
    if args.action:
        filters['action'] = args.action
    if args.topic:
        filters['topic'] = args.topic

    # Load entries
    entries = load_pool(filters)

    # Sort by timestamp (newest first)
    entries.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

    # Display
    if args.summary:
        print_summary(entries)
    else:
        print_summary(entries)
        print("Entries:\n")
        for entry in entries:
            print(format_entry(entry, verbose=args.verbose))
            print()

if __name__ == "__main__":
    main()
