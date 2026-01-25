#!/usr/bin/env python3
"""
Feedback Loop - Self-Analytics & Continuous Improvement

Closes the loop: Outcome → Analysis → Strategy → Better Decisions → Better Outcomes

Includes:
- Component health tracking
- Workflow efficiency metrics
- Automatic weak-point detection
- Atlas spine daily loop integration
"""

import sqlite3
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Paths
DAEMON_DIR = Path(__file__).parent
REPO_ROOT = DAEMON_DIR.parent
OUTCOME_DB = DAEMON_DIR / "outcomes.db"
STRATEGY_DB = DAEMON_DIR / "strategies.db"
MEMORY_DB = Path.home() / ".claude" / "memory" / "learnings.db"
ANALYTICS_DB = DAEMON_DIR / "analytics.db"
ATLAS_DIR = REPO_ROOT / ".atlas"
REPAIR_QUEUE = ATLAS_DIR / "repair_queue.jsonl"

# Imports
try:
    from telegram_notify import notify
except ImportError:
    def notify(*args, **kwargs): pass

# Atlas spine integration
try:
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    from atlas_spine.map import AtlasMap
    from atlas_spine.events import EventStore
    ATLAS_AVAILABLE = True
except ImportError:
    ATLAS_AVAILABLE = False

# ============================================================================
# Core Loop
# ============================================================================

def get_recent_outcomes(hours: int = 24) -> List[Dict]:
    """Get outcomes from the last N hours."""
    if not OUTCOME_DB.exists():
        return []

    conn = sqlite3.connect(OUTCOME_DB)
    c = conn.cursor()

    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

    try:
        c.execute('''SELECT action_type, result, context, timestamp
                     FROM outcomes WHERE timestamp > ? ORDER BY timestamp DESC''', (cutoff,))
        outcomes = [{"action": r[0], "result": r[1], "context": r[2], "time": r[3]}
                    for r in c.fetchall()]
    except:
        outcomes = []

    conn.close()
    return outcomes


def analyze_patterns(outcomes: List[Dict]) -> Dict:
    """Find patterns in outcomes."""
    if not outcomes:
        return {"patterns": [], "success_rate": 0, "top_failures": []}

    # Success rate by action type
    action_stats = {}
    for o in outcomes:
        action = o["action"]
        if action not in action_stats:
            action_stats[action] = {"success": 0, "fail": 0}
        if o["result"] == "success":
            action_stats[action]["success"] += 1
        else:
            action_stats[action]["fail"] += 1

    # Overall success rate
    total_success = sum(s["success"] for s in action_stats.values())
    total = len(outcomes)
    success_rate = total_success / total if total else 0

    # Top failures
    failures = [(a, s["fail"] / (s["success"] + s["fail"]))
                for a, s in action_stats.items() if s["fail"] > 0]
    failures.sort(key=lambda x: x[1], reverse=True)

    # Patterns
    patterns = []
    for action, stats in action_stats.items():
        rate = stats["success"] / (stats["success"] + stats["fail"])
        if rate > 0.8:
            patterns.append({"action": action, "pattern": "high_success", "rate": rate})
        elif rate < 0.3:
            patterns.append({"action": action, "pattern": "needs_improvement", "rate": rate})

    return {
        "patterns": patterns,
        "success_rate": success_rate,
        "top_failures": failures[:5],
        "action_stats": action_stats
    }


def update_strategies(analysis: Dict) -> int:
    """Update strategies based on analysis."""
    if not STRATEGY_DB.exists():
        return 0

    conn = sqlite3.connect(STRATEGY_DB)
    c = conn.cursor()

    updates = 0

    # Boost successful strategies
    for pattern in analysis.get("patterns", []):
        if pattern["pattern"] == "high_success":
            try:
                c.execute('''UPDATE strategies SET fitness = fitness * 1.1
                             WHERE name LIKE ?''', (f"%{pattern['action']}%",))
                updates += c.rowcount
            except:
                pass
        elif pattern["pattern"] == "needs_improvement":
            try:
                c.execute('''UPDATE strategies SET fitness = fitness * 0.9
                             WHERE name LIKE ?''', (f"%{pattern['action']}%",))
                updates += c.rowcount
            except:
                pass

    conn.commit()
    conn.close()
    return updates


def store_learnings(analysis: Dict):
    """Store learnings in memory for future recall."""
    MEMORY_DB.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(MEMORY_DB)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS learnings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        category TEXT,
        content TEXT,
        source TEXT
    )''')

    # Store high-level learning
    if analysis.get("patterns"):
        learning = f"Success rate: {analysis['success_rate']:.1%}. "
        learning += f"High performers: {[p['action'] for p in analysis['patterns'] if p['pattern'] == 'high_success']}. "
        learning += f"Needs work: {[p['action'] for p in analysis['patterns'] if p['pattern'] == 'needs_improvement']}."

        c.execute('''INSERT INTO learnings (timestamp, category, content, source)
                     VALUES (?, ?, ?, ?)''',
                  (datetime.now().isoformat(), "feedback_loop", learning, "feedback_loop.py"))

    conn.commit()
    conn.close()


# ============================================================================
# Self-Analytics: Component Health & Weak Point Detection
# ============================================================================

def init_analytics_db():
    """Initialize analytics database."""
    conn = sqlite3.connect(ANALYTICS_DB)
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS component_health (
            component TEXT PRIMARY KEY,
            last_success TEXT,
            last_failure TEXT,
            success_count INTEGER DEFAULT 0,
            failure_count INTEGER DEFAULT 0,
            avg_duration_ms REAL DEFAULT 0,
            health_score REAL DEFAULT 1.0,
            notes TEXT
        );
        CREATE TABLE IF NOT EXISTS workflow_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            workflow TEXT,
            duration_ms REAL,
            steps_completed INTEGER,
            steps_failed INTEGER,
            bottleneck TEXT
        );
        CREATE TABLE IF NOT EXISTS improvement_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            component TEXT,
            issue TEXT,
            severity TEXT,
            suggested_fix TEXT,
            status TEXT DEFAULT 'pending'
        );
    ''')
    conn.commit()
    conn.close()


def track_component(component: str, success: bool, duration_ms: float = 0, notes: str = ''):
    """Track component health."""
    init_analytics_db()
    conn = sqlite3.connect(ANALYTICS_DB)
    c = conn.cursor()

    now = datetime.now().isoformat()

    # Get current stats
    c.execute('SELECT success_count, failure_count, avg_duration_ms FROM component_health WHERE component = ?', (component,))
    row = c.fetchone()

    if row:
        success_count, failure_count, avg_dur = row
        if success:
            success_count += 1
            c.execute('UPDATE component_health SET last_success = ?, success_count = ? WHERE component = ?',
                     (now, success_count, component))
        else:
            failure_count += 1
            c.execute('UPDATE component_health SET last_failure = ?, failure_count = ?, notes = ? WHERE component = ?',
                     (now, failure_count, notes, component))

        # Update health score (success rate with decay)
        total = success_count + failure_count
        health = success_count / total if total > 0 else 1.0
        c.execute('UPDATE component_health SET health_score = ? WHERE component = ?', (health, component))

        # Update avg duration
        if duration_ms > 0:
            new_avg = (avg_dur * (total - 1) + duration_ms) / total
            c.execute('UPDATE component_health SET avg_duration_ms = ? WHERE component = ?', (new_avg, component))
    else:
        c.execute('''INSERT INTO component_health (component, last_success, success_count, failure_count, health_score)
                     VALUES (?, ?, ?, ?, ?)''',
                  (component, now if success else None, 1 if success else 0, 0 if success else 1, 1.0 if success else 0.0))

    conn.commit()
    conn.close()


def get_weak_components(threshold: float = 0.7) -> List[Dict]:
    """Get components with health below threshold."""
    init_analytics_db()
    conn = sqlite3.connect(ANALYTICS_DB)
    c = conn.cursor()

    c.execute('''SELECT component, health_score, failure_count, last_failure, notes
                 FROM component_health WHERE health_score < ? ORDER BY health_score ASC''', (threshold,))

    weak = [{'component': r[0], 'health': r[1], 'failures': r[2], 'last_failure': r[3], 'notes': r[4]}
            for r in c.fetchall()]
    conn.close()
    return weak


def add_to_repair_queue(component: str, issue: str, severity: str = 'medium', suggested_fix: str = ''):
    """Add item to repair queue."""
    ATLAS_DIR.mkdir(exist_ok=True)

    entry = {
        'timestamp': datetime.now().isoformat(),
        'component': component,
        'issue': issue,
        'severity': severity,
        'suggested_fix': suggested_fix,
        'status': 'pending'
    }

    with open(REPAIR_QUEUE, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def analyze_workflow_efficiency() -> Dict:
    """Analyze which parts of workflow are slow or failing."""
    results = {'bottlenecks': [], 'slow_components': [], 'failing_components': []}

    init_analytics_db()
    conn = sqlite3.connect(ANALYTICS_DB)
    c = conn.cursor()

    # Find slow components (> 2x average)
    c.execute('SELECT AVG(avg_duration_ms) FROM component_health WHERE avg_duration_ms > 0')
    avg_all = c.fetchone()[0] or 0

    if avg_all > 0:
        c.execute('SELECT component, avg_duration_ms FROM component_health WHERE avg_duration_ms > ?', (avg_all * 2,))
        results['slow_components'] = [{'component': r[0], 'duration_ms': r[1], 'vs_avg': r[1]/avg_all}
                                       for r in c.fetchall()]

    # Get failing components
    results['failing_components'] = get_weak_components(0.7)

    conn.close()
    return results


def check_critical_pipelines() -> List[Dict]:
    """Check for critical pipeline failures - things that silently break."""
    criticals = []

    # Check 1: Ingest vs UTF mismatch (CRITICAL)
    ingest_db = DAEMON_DIR / "ingest.db"
    utf_db = DAEMON_DIR / "utf_knowledge.db"

    if ingest_db.exists() and utf_db.exists():
        try:
            conn1 = sqlite3.connect(ingest_db)
            conn2 = sqlite3.connect(utf_db)

            marked_complete = conn1.execute(
                'SELECT COUNT(*) FROM processed_files WHERE status="completed"'
            ).fetchone()[0]
            actual_sources = conn2.execute('SELECT COUNT(*) FROM sources').fetchone()[0]

            # If more than 5 files marked complete but not in UTF = pipeline broken
            gap = marked_complete - actual_sources
            if gap > 5:
                criticals.append({
                    'component': 'ingest_pipeline',
                    'severity': 'CRITICAL',
                    'issue': f'{gap} files marked complete but not extracted to UTF',
                    'fix': 'Reset processed_files status to pending'
                })
                # Auto-fix: reset for reprocessing
                conn1.execute('UPDATE processed_files SET status="pending" WHERE status="completed"')
                conn1.commit()
                notify(f"CRITICAL: Reset {gap} files for reprocessing - UTF extraction was failing silently")

            conn1.close()
            conn2.close()
        except Exception as e:
            criticals.append({'component': 'ingest_check', 'severity': 'ERROR', 'issue': str(e)})

    # Check 2: Outcome tracking starvation
    if OUTCOME_DB.exists():
        try:
            conn = sqlite3.connect(OUTCOME_DB)
            count = conn.execute('SELECT COUNT(*) FROM outcomes').fetchone()[0]
            if count < 10:
                criticals.append({
                    'component': 'outcome_tracking',
                    'severity': 'WARNING',
                    'issue': f'Only {count} outcomes recorded - feedback loop starved',
                    'fix': 'Ensure outcome_tracker.record() is called after actions'
                })
            conn.close()
        except:
            pass

    # Check 3: Empty critical databases
    critical_dbs = ['synthesis.db', 'books.db']
    for db_name in critical_dbs:
        db_path = DAEMON_DIR / db_name
        if db_path.exists():
            try:
                conn = sqlite3.connect(db_path)
                tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                total = 0
                for t in tables[:3]:
                    if not t[0].startswith('sqlite_'):
                        total += conn.execute(f'SELECT COUNT(*) FROM {t[0]}').fetchone()[0]
                if total == 0:
                    criticals.append({
                        'component': db_name,
                        'severity': 'WARNING',
                        'issue': f'{db_name} is empty - pipeline not running',
                        'fix': f'Check {db_name.replace(".db", "")} worker'
                    })
                conn.close()
            except:
                pass

    return criticals


def run_self_diagnostics() -> Dict:
    """Run comprehensive self-diagnostics."""
    results = {
        'timestamp': datetime.now().isoformat(),
        'checks': [],
        'issues': [],
        'recommendations': [],
        'criticals': []
    }

    # Check CRITICAL pipelines first
    criticals = check_critical_pipelines()
    results['criticals'] = criticals
    for c in criticals:
        results['issues'].append(f"[{c['severity']}] {c['component']}: {c['issue']}")
        if c.get('fix'):
            results['recommendations'].append(c['fix'])

    # Alert on criticals
    if any(c['severity'] == 'CRITICAL' for c in criticals):
        notify("CRITICAL FAILURES DETECTED - check feedback_loop logs")

    # Check 1: Database files exist
    dbs = [OUTCOME_DB, STRATEGY_DB, ANALYTICS_DB]
    for db in dbs:
        if db.exists():
            results['checks'].append({'name': f'{db.name} exists', 'status': 'ok'})
        else:
            results['checks'].append({'name': f'{db.name} exists', 'status': 'missing'})
            results['issues'].append(f'Missing database: {db.name}')

    # Check 2: Docker containers running
    try:
        proc = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'],
                             capture_output=True, text=True, timeout=10)
        containers = proc.stdout.strip().split('\n') if proc.stdout else []
        expected = ['localai', 'dragonfly-cache']
        for c in expected:
            if c in containers:
                results['checks'].append({'name': f'Container {c}', 'status': 'running'})
                track_component(f'docker_{c}', True)
            else:
                results['checks'].append({'name': f'Container {c}', 'status': 'not running'})
                results['issues'].append(f'Container not running: {c}')
                track_component(f'docker_{c}', False, notes='Not running')
    except Exception as e:
        results['checks'].append({'name': 'Docker check', 'status': 'error', 'error': str(e)})

    # Check 3: Atlas map freshness
    map_path = ATLAS_DIR / 'map.json'
    if map_path.exists():
        age_hours = (datetime.now().timestamp() - map_path.stat().st_mtime) / 3600
        if age_hours > 24:
            results['issues'].append(f'Atlas map is {age_hours:.0f}h old - needs rebuild')
            results['recommendations'].append('Run: python atlas_spine/cli.py map build')
        else:
            results['checks'].append({'name': 'Atlas map', 'status': 'fresh', 'age_hours': age_hours})
    else:
        results['issues'].append('Atlas map not built')
        results['recommendations'].append('Run: python atlas_spine/cli.py map build')

    # Check 4: Weak components
    weak = get_weak_components()
    if weak:
        for w in weak:
            results['issues'].append(f"Weak component: {w['component']} ({w['health']:.0%} health)")
            add_to_repair_queue(w['component'], f"Health below threshold: {w['health']:.0%}", 'medium')

    # Check 5: Workflow efficiency
    efficiency = analyze_workflow_efficiency()
    if efficiency['slow_components']:
        for s in efficiency['slow_components']:
            results['recommendations'].append(f"Optimize {s['component']} - {s['vs_avg']:.1f}x slower than average")

    return results


def detect_breakthroughs() -> List[Dict]:
    """Detect components performing significantly above baseline."""
    init_analytics_db()
    conn = sqlite3.connect(ANALYTICS_DB)
    c = conn.cursor()

    breakthroughs = []

    # Components with >95% health and significant usage
    c.execute('''SELECT component, health_score, success_count, avg_duration_ms
                 FROM component_health
                 WHERE health_score > 0.95 AND success_count > 10
                 ORDER BY health_score DESC''')

    for row in c.fetchall():
        component, health, successes, duration = row
        breakthroughs.append({
            'component': component,
            'health': health,
            'successes': successes,
            'insight': f'{component} is highly reliable - consider as template for others'
        })

    # Detect improving trends (compare recent vs older)
    c.execute('SELECT component, health_score FROM component_health')
    # In a real system, we'd track historical health scores to detect trends

    conn.close()
    return breakthroughs


def extract_optimization_insights() -> List[Dict]:
    """Extract actionable optimization insights from analytics."""
    insights = []

    # Get efficiency data
    efficiency = analyze_workflow_efficiency()

    # Insight 1: Slow components could benefit from caching
    for slow in efficiency.get('slow_components', []):
        insights.append({
            'type': 'optimization',
            'target': slow['component'],
            'insight': f"Consider caching for {slow['component']} - {slow['vs_avg']:.1f}x slower than average",
            'potential_gain': f"{(slow['vs_avg'] - 1) * 100:.0f}% speedup possible"
        })

    # Insight 2: Frequently failing components need redesign
    for fail in efficiency.get('failing_components', []):
        if fail['failures'] > 5:
            insights.append({
                'type': 'reliability',
                'target': fail['component'],
                'insight': f"{fail['component']} has {fail['failures']} failures - root cause analysis needed",
                'potential_gain': f"Could improve overall reliability by {fail['failures'] * 2}%"
            })

    # Insight 3: Breakthrough patterns to replicate
    breakthroughs = detect_breakthroughs()
    for b in breakthroughs:
        insights.append({
            'type': 'breakthrough',
            'target': b['component'],
            'insight': b['insight'],
            'potential_gain': 'Apply pattern to struggling components'
        })

    return insights


def run_feedback_cycle():
    """Run one complete feedback cycle with self-analytics."""
    print(f"[{datetime.now().isoformat()}] Running feedback cycle...")
    track_component('feedback_loop', True)
    start_time = datetime.now()

    # 1. Get outcomes
    outcomes = get_recent_outcomes(hours=24)
    print(f"  Outcomes (24h): {len(outcomes)}")

    # 2. Analyze patterns
    if outcomes:
        analysis = analyze_patterns(outcomes)
        print(f"  Success rate: {analysis['success_rate']:.1%}")
        print(f"  Patterns found: {len(analysis['patterns'])}")

        # 3. Update strategies
        updates = update_strategies(analysis)
        print(f"  Strategies updated: {updates}")

        # 4. Store learnings
        store_learnings(analysis)
        print(f"  Learnings stored")
    else:
        analysis = {'success_rate': 0, 'patterns': []}
        print("  No outcomes to analyze")

    # 5. Self-diagnostics
    print("  Running self-diagnostics...")
    diagnostics = run_self_diagnostics()
    print(f"  Issues found: {len(diagnostics['issues'])}")

    # 6. Optimization insights
    print("  Extracting optimization insights...")
    insights = extract_optimization_insights()
    print(f"  Insights: {len(insights)}")

    # 7. Detect breakthroughs
    breakthroughs = detect_breakthroughs()
    if breakthroughs:
        print(f"  Breakthroughs detected: {len(breakthroughs)}")
        for b in breakthroughs:
            print(f"    ✓ {b['component']}: {b['insight'][:50]}")

    # 8. Atlas daily loop (if available)
    if ATLAS_AVAILABLE:
        print("  Running Atlas daily loop...")
        try:
            atlas_map = AtlasMap(REPO_ROOT)
            map_result = atlas_map.build()
            print(f"    Map: {map_result.get('files_indexed', 0)} files indexed")
            track_component('atlas_map', True, duration_ms=(datetime.now() - start_time).total_seconds() * 1000)
        except Exception as e:
            print(f"    Atlas error: {e}")
            track_component('atlas_map', False, notes=str(e))

    # 9. Log events
    if ATLAS_AVAILABLE:
        try:
            events = EventStore(REPO_ROOT)
            events.log(
                command_text='feedback_cycle',
                route={'operator': 'FEEDBACK', 'method': 'scheduled'},
                operator='FEEDBACK',
                inputs={'outcomes_count': len(outcomes)},
                outputs={
                    'success_rate': analysis.get('success_rate', 0),
                    'issues': len(diagnostics['issues']),
                    'insights': len(insights),
                    'breakthroughs': len(breakthroughs)
                },
                status='success',
                next_suggestion='Review repair_queue.jsonl' if diagnostics['issues'] else None
            )
        except:
            pass

    # 10. Notify if significant
    duration_ms = (datetime.now() - start_time).total_seconds() * 1000
    track_component('feedback_cycle', True, duration_ms)

    if diagnostics['issues'] or insights:
        summary = f"📊 Feedback: {len(diagnostics['issues'])} issues, {len(insights)} insights"
        if breakthroughs:
            summary += f", {len(breakthroughs)} breakthroughs"
        notify(summary)

    return {
        'analysis': analysis,
        'diagnostics': diagnostics,
        'insights': insights,
        'breakthroughs': breakthroughs
    }


def run_continuous(interval: int = 3600):
    """Run feedback loop continuously."""
    print("=" * 60)
    print("FEEDBACK LOOP - Closing the cycle")
    print("=" * 60)
    print(f"Interval: {interval}s")
    print()

    notify("Feedback loop started")

    while True:
        try:
            run_feedback_cycle()
        except Exception as e:
            print(f"  Error: {e}")

        print(f"  Sleeping {interval}s...")
        time.sleep(interval)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Feedback Loop")
    parser.add_argument("--watch", action="store_true", help="Continuous mode")
    parser.add_argument("--interval", type=int, default=3600, help="Cycle interval")

    args = parser.parse_args()

    if args.watch:
        run_continuous(args.interval)
    else:
        run_feedback_cycle()
