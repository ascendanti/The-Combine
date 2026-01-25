#!/usr/bin/env python3
"""
Token Monitor - Spike Detection + Task Logging

Monitors Claude token usage for anomalies and logs spikes with context.
Purpose: Identify inefficiencies for architecture optimization.

Features:
- Real-time spike detection (>2 std dev above rolling average)
- Task context logging (what was happening during spike)
- Pattern analysis for optimization recommendations
- Feeds insights back to KG for learning

Usage:
    python token_monitor.py                 # Run once, report spikes
    python token_monitor.py --watch         # Continuous monitoring
    python token_monitor.py --analyze       # Analyze spike patterns
    python token_monitor.py --threshold 3   # Custom spike threshold (std devs)
"""

import json
import os
import sys
import time
import argparse
import statistics
from pathlib import Path
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import sqlite3


# Paths
CLAUDE_DIR = Path.home() / ".claude"
KG_FILE = Path.home() / ".claude" / "memory" / "knowledge-graph.jsonl"
MONITOR_DB = Path(__file__).parent / "token_monitor.db"


@dataclass
class TokenEvent:
    """A single token usage event."""
    timestamp: datetime
    input_tokens: int
    output_tokens: int
    cache_read: int
    cache_write: int
    model: str
    session_id: str
    project: str
    cost_usd: float = 0.0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens + self.cache_read + self.cache_write


@dataclass
class TokenSpike:
    """A detected spike in token usage."""
    timestamp: datetime
    event: TokenEvent
    rolling_avg: float
    spike_factor: float  # How many times above average
    context: str = ""
    tool_calls: List[str] = field(default_factory=list)
    files_read: List[str] = field(default_factory=list)


def init_db():
    """Initialize monitoring database."""
    conn = sqlite3.connect(MONITOR_DB)
    c = conn.cursor()

    # Spikes table
    c.execute("""
        CREATE TABLE IF NOT EXISTS spikes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            session_id TEXT,
            project TEXT,
            model TEXT,
            input_tokens INTEGER,
            output_tokens INTEGER,
            cache_read INTEGER,
            cache_write INTEGER,
            total_tokens INTEGER,
            cost_usd REAL,
            rolling_avg REAL,
            spike_factor REAL,
            context TEXT,
            tool_calls TEXT,
            files_read TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Optimization recommendations table
    c.execute("""
        CREATE TABLE IF NOT EXISTS optimizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            potential_savings_pct REAL,
            priority TEXT,
            source TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            applied INTEGER DEFAULT 0
        )
    """)

    # Rolling stats table
    c.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            date TEXT PRIMARY KEY,
            total_tokens INTEGER,
            total_cost REAL,
            spike_count INTEGER,
            avg_tokens_per_msg REAL,
            max_spike_factor REAL
        )
    """)

    conn.commit()
    conn.close()


def parse_session_jsonl(filepath: Path) -> List[TokenEvent]:
    """Parse a session JSONL file for token events."""
    events = []

    # Extract session/project from path
    rel_path = filepath.relative_to(CLAUDE_DIR / "projects")
    parts = list(rel_path.parts)
    project = parts[0] if parts else "unknown"
    session_id = filepath.stem

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or not line.startswith('{'):
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
                        continue

                    # Extract usage
                    usage = data.get("message", {}).get("usage", {})
                    if not usage:
                        usage = data.get("usage", {})

                    if not usage:
                        continue

                    event = TokenEvent(
                        timestamp=ts,
                        input_tokens=usage.get("input_tokens", 0) or 0,
                        output_tokens=usage.get("output_tokens", 0) or 0,
                        cache_read=usage.get("cache_read_input_tokens", 0) or 0,
                        cache_write=usage.get("cache_creation_input_tokens", 0) or 0,
                        model=data.get("model", "unknown"),
                        session_id=session_id,
                        project=project,
                        cost_usd=data.get("costUSD", 0.0) or 0.0,
                    )

                    if event.total > 0:
                        events.append(event)

                except json.JSONDecodeError:
                    continue

    except Exception:
        pass

    return events


def detect_spikes(
    events: List[TokenEvent],
    threshold: float = 2.0,
    window_size: int = 20
) -> List[TokenSpike]:
    """
    Detect spikes in token usage.

    A spike is when usage exceeds rolling_avg + (threshold * std_dev).
    """
    if len(events) < window_size:
        return []

    # Sort by timestamp
    events = sorted(events, key=lambda e: e.timestamp)

    spikes = []
    window = []

    for event in events:
        window.append(event.total)

        if len(window) > window_size:
            window.pop(0)

        if len(window) >= window_size:
            avg = statistics.mean(window[:-1])  # Exclude current
            std = statistics.stdev(window[:-1]) if len(window) > 2 else avg * 0.5

            spike_threshold = avg + (threshold * std)

            if event.total > spike_threshold and event.total > avg * 1.5:
                spike_factor = event.total / avg if avg > 0 else 0

                spike = TokenSpike(
                    timestamp=event.timestamp,
                    event=event,
                    rolling_avg=avg,
                    spike_factor=spike_factor,
                )
                spikes.append(spike)

    return spikes


def log_spike_to_db(spike: TokenSpike):
    """Log a spike to the database."""
    conn = sqlite3.connect(MONITOR_DB)
    c = conn.cursor()

    c.execute("""
        INSERT INTO spikes (
            timestamp, session_id, project, model,
            input_tokens, output_tokens, cache_read, cache_write,
            total_tokens, cost_usd, rolling_avg, spike_factor,
            context, tool_calls, files_read
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        spike.timestamp.isoformat(),
        spike.event.session_id,
        spike.event.project,
        spike.event.model,
        spike.event.input_tokens,
        spike.event.output_tokens,
        spike.event.cache_read,
        spike.event.cache_write,
        spike.event.total,
        spike.event.cost_usd,
        spike.rolling_avg,
        spike.spike_factor,
        spike.context,
        json.dumps(spike.tool_calls),
        json.dumps(spike.files_read),
    ))

    conn.commit()
    conn.close()


def log_spike_to_kg(spike: TokenSpike):
    """Log spike as learning to knowledge graph."""
    entity = {
        "type": "entity",
        "name": f"spike:{spike.timestamp.strftime('%Y%m%d_%H%M%S')}",
        "entityType": "token_spike",
        "observations": [
            f"TOTAL_TOKENS:{spike.event.total}",
            f"SPIKE_FACTOR:{spike.spike_factor:.2f}x",
            f"ROLLING_AVG:{spike.rolling_avg:.0f}",
            f"MODEL:{spike.event.model}",
            f"PROJECT:{spike.event.project}",
            f"INPUT:{spike.event.input_tokens}",
            f"OUTPUT:{spike.event.output_tokens}",
            f"CACHE_READ:{spike.event.cache_read}",
            f"CACHE_WRITE:{spike.event.cache_write}",
            f"COST_USD:{spike.event.cost_usd:.4f}",
            f"TIMESTAMP:{spike.timestamp.isoformat()}",
            f"SOURCE:token_monitor",
        ],
    }

    # Append to KG
    KG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(KG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entity) + "\n")


def analyze_spike_patterns() -> Dict[str, any]:
    """Analyze logged spikes for patterns."""
    if not MONITOR_DB.exists():
        return {}

    conn = sqlite3.connect(MONITOR_DB)
    c = conn.cursor()

    analysis = {}

    # Most common spike models
    c.execute("""
        SELECT model, COUNT(*) as count, AVG(spike_factor) as avg_factor
        FROM spikes
        GROUP BY model
        ORDER BY count DESC
        LIMIT 5
    """)
    analysis["by_model"] = [
        {"model": r[0], "count": r[1], "avg_factor": r[2]}
        for r in c.fetchall()
    ]

    # Most common spike projects
    c.execute("""
        SELECT project, COUNT(*) as count, AVG(total_tokens) as avg_tokens
        FROM spikes
        GROUP BY project
        ORDER BY count DESC
        LIMIT 5
    """)
    analysis["by_project"] = [
        {"project": r[0], "count": r[1], "avg_tokens": r[2]}
        for r in c.fetchall()
    ]

    # Spike time patterns (hour of day)
    c.execute("""
        SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
        FROM spikes
        GROUP BY hour
        ORDER BY count DESC
        LIMIT 5
    """)
    analysis["by_hour"] = [
        {"hour": r[0], "count": r[1]}
        for r in c.fetchall()
    ]

    # Recent trends
    c.execute("""
        SELECT date(timestamp) as day, COUNT(*) as count, AVG(spike_factor) as avg_factor
        FROM spikes
        WHERE timestamp > date('now', '-7 days')
        GROUP BY day
        ORDER BY day DESC
    """)
    analysis["recent_daily"] = [
        {"date": r[0], "count": r[1], "avg_factor": r[2]}
        for r in c.fetchall()
    ]

    # Total stats
    c.execute("SELECT COUNT(*), AVG(spike_factor), MAX(spike_factor), SUM(cost_usd) FROM spikes")
    row = c.fetchone()
    analysis["totals"] = {
        "total_spikes": row[0],
        "avg_spike_factor": row[1],
        "max_spike_factor": row[2],
        "total_cost_during_spikes": row[3],
    }

    conn.close()
    return analysis


def generate_optimization_recommendations(analysis: Dict) -> List[Dict]:
    """Generate optimization recommendations from spike analysis."""
    recommendations = []

    if not analysis:
        return recommendations

    # High cache write → suggest pre-caching
    by_model = analysis.get("by_model", [])
    for entry in by_model:
        if entry.get("avg_factor", 0) > 3.0:
            recommendations.append({
                "pattern": f"High spikes on {entry['model']}",
                "recommendation": f"Model {entry['model']} has {entry['count']} spikes with {entry['avg_factor']:.1f}x avg factor. Consider routing complex tasks to LocalAI for preprocessing.",
                "potential_savings_pct": 30,
                "priority": "high",
            })

    # Project-specific patterns
    by_project = analysis.get("by_project", [])
    for entry in by_project:
        if entry.get("count", 0) > 5:
            recommendations.append({
                "pattern": f"Frequent spikes in {entry['project']}",
                "recommendation": f"Project {entry['project']} has {entry['count']} spikes averaging {entry['avg_tokens']:.0f} tokens. Review for large file reads or inefficient context.",
                "potential_savings_pct": 20,
                "priority": "medium",
            })

    # Time-based patterns
    by_hour = analysis.get("by_hour", [])
    if by_hour and by_hour[0].get("count", 0) > 10:
        peak_hour = by_hour[0]["hour"]
        recommendations.append({
            "pattern": f"Peak spike hour: {peak_hour}:00",
            "recommendation": f"Most spikes occur at {peak_hour}:00. Consider batching intensive tasks or pre-loading context during off-peak hours.",
            "potential_savings_pct": 15,
            "priority": "low",
        })

    return recommendations


def scan_for_spikes(threshold: float = 2.0, since_hours: int = 24) -> List[TokenSpike]:
    """Scan recent session files for spikes."""
    all_events = []

    projects_dir = CLAUDE_DIR / "projects"
    if not projects_dir.exists():
        return []

    cutoff = datetime.now() - timedelta(hours=since_hours)

    for jsonl_file in projects_dir.rglob("*.jsonl"):
        # Skip old files
        if jsonl_file.stat().st_mtime < cutoff.timestamp():
            continue

        events = parse_session_jsonl(jsonl_file)
        all_events.extend(events)

    if not all_events:
        return []

    # Filter to recent events
    all_events = [e for e in all_events if e.timestamp.replace(tzinfo=None) > cutoff]

    return detect_spikes(all_events, threshold=threshold)


def print_spike_report(spikes: List[TokenSpike]):
    """Print spike report to console."""
    if not spikes:
        print("\n  No spikes detected in recent activity.")
        return

    print(f"\n  TOKEN SPIKE REPORT")
    print(f"  {'='*60}")
    print(f"  Detected {len(spikes)} spike(s)")
    print()

    for spike in spikes[:10]:  # Show top 10
        print(f"  [{spike.timestamp.strftime('%H:%M:%S')}] {spike.spike_factor:.1f}x spike")
        print(f"    Tokens: {spike.event.total:,} (avg: {spike.rolling_avg:,.0f})")
        print(f"    Model: {spike.event.model}")
        print(f"    Project: {spike.event.project}")
        print(f"    Cost: ${spike.event.cost_usd:.4f}")
        print()

    if len(spikes) > 10:
        print(f"  ... and {len(spikes) - 10} more spikes")


def print_analysis_report(analysis: Dict, recommendations: List[Dict]):
    """Print analysis and recommendations."""
    if not analysis:
        print("\n  No spike data to analyze. Run monitoring first.")
        return

    totals = analysis.get("totals", {})

    print(f"\n  SPIKE PATTERN ANALYSIS")
    print(f"  {'='*60}")

    print(f"\n  Total Spikes: {totals.get('total_spikes', 0)}")
    print(f"  Avg Spike Factor: {totals.get('avg_spike_factor', 0):.1f}x")
    print(f"  Max Spike Factor: {totals.get('max_spike_factor', 0):.1f}x")
    print(f"  Cost During Spikes: ${totals.get('total_cost_during_spikes', 0):.2f}")

    # By model
    print(f"\n  TOP MODELS (by spike count):")
    for entry in analysis.get("by_model", [])[:3]:
        print(f"    {entry['model']}: {entry['count']} spikes ({entry['avg_factor']:.1f}x avg)")

    # Recommendations
    if recommendations:
        print(f"\n  OPTIMIZATION RECOMMENDATIONS")
        print(f"  {'-'*60}")

        for rec in recommendations:
            priority_icon = {"high": "!!", "medium": "!", "low": "-"}.get(rec["priority"], "-")
            print(f"\n  [{priority_icon}] {rec['pattern']}")
            print(f"      {rec['recommendation']}")
            print(f"      Potential savings: ~{rec['potential_savings_pct']}%")

    print()


def watch_mode(threshold: float = 2.0, interval: int = 30):
    """Continuous monitoring mode."""
    print(f"\n  TOKEN SPIKE MONITOR")
    print(f"  {'='*40}")
    print(f"  Threshold: {threshold} std devs")
    print(f"  Interval: {interval}s")
    print(f"  Press Ctrl+C to stop\n")

    init_db()
    last_check = datetime.now() - timedelta(hours=1)

    try:
        while True:
            # Scan for new spikes since last check
            hours_since = (datetime.now() - last_check).total_seconds() / 3600
            spikes = scan_for_spikes(threshold=threshold, since_hours=max(1, int(hours_since) + 1))

            # Filter to new spikes only
            new_spikes = [s for s in spikes if s.timestamp.replace(tzinfo=None) > last_check]

            if new_spikes:
                print(f"\n  [{datetime.now().strftime('%H:%M:%S')}] ALERT: {len(new_spikes)} new spike(s) detected!")

                for spike in new_spikes:
                    print(f"    {spike.spike_factor:.1f}x | {spike.event.total:,} tokens | {spike.event.project}")

                    # Log to database and KG
                    log_spike_to_db(spike)
                    log_spike_to_kg(spike)

                print(f"    -> Logged to DB and KG for learning")

            last_check = datetime.now()
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n  Monitoring stopped.\n")


def main():
    parser = argparse.ArgumentParser(description="Token Spike Monitor")
    parser.add_argument("--watch", action="store_true", help="Continuous monitoring")
    parser.add_argument("--analyze", action="store_true", help="Analyze spike patterns")
    parser.add_argument("--threshold", type=float, default=2.0, help="Spike threshold (std devs)")
    parser.add_argument("--interval", type=int, default=30, help="Watch interval (seconds)")
    parser.add_argument("--hours", type=int, default=24, help="Hours to scan back")

    args = parser.parse_args()

    init_db()

    if args.watch:
        watch_mode(threshold=args.threshold, interval=args.interval)
    elif args.analyze:
        analysis = analyze_spike_patterns()
        recommendations = generate_optimization_recommendations(analysis)
        print_analysis_report(analysis, recommendations)
    else:
        # One-time scan
        spikes = scan_for_spikes(threshold=args.threshold, since_hours=args.hours)
        print_spike_report(spikes)

        # Log new spikes
        for spike in spikes:
            log_spike_to_db(spike)

        print(f"  Logged {len(spikes)} spike(s) to database.")


if __name__ == "__main__":
    main()
