#!/usr/bin/env python3
"""
Strategy Operations - Business Operationalization Module

Extends strategy_evolution.py with:
- Operationalization (deploy strategies to production)
- Measurement (KPIs, metrics, dashboards)
- Drift Recognition (detect when strategies degrade)
- Competitor Analysis (reverse engineer best practices)

This module turns strategy management into business-running software.

Usage:
    # Deploy a strategy to production
    python daemon/strategy_ops.py deploy --strategy "quick-fix" --environment production

    # Measure strategy performance
    python daemon/strategy_ops.py measure --strategy "quick-fix" --period 7d

    # Check for drift
    python daemon/strategy_ops.py drift --threshold 0.1

    # Analyze competitor
    python daemon/strategy_ops.py competitor --repo "owner/repo"

    # Full operations dashboard
    python daemon/strategy_ops.py dashboard
"""

import sqlite3
import json
import hashlib
import statistics
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import math

DB_PATH = Path(__file__).parent / "strategy_ops.db"
STRATEGY_DB = Path(__file__).parent / "strategies.db"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Deployment:
    """Strategy deployment record."""
    deployment_id: str
    strategy_id: str
    strategy_version: int
    environment: str           # development, staging, production
    status: str               # pending, active, paused, retired
    config: Dict
    deployed_at: str
    deployed_by: str
    metrics_baseline: Dict
    current_metrics: Dict
    last_health_check: str


@dataclass
class Measurement:
    """Strategy measurement record."""
    measurement_id: str
    strategy_id: str
    deployment_id: str
    period_start: str
    period_end: str
    kpis: Dict                 # Key Performance Indicators
    raw_metrics: Dict
    computed_scores: Dict
    anomalies: List[str]
    recommendations: List[str]


@dataclass
class DriftEvent:
    """Strategy drift detection event."""
    drift_id: str
    strategy_id: str
    deployment_id: str
    drift_type: str            # performance, behavior, context, sudden, gradual
    severity: str              # low, medium, high, critical
    baseline_value: float
    current_value: float
    change_percent: float
    detected_at: str
    description: str
    suggested_action: str
    resolved: bool
    resolved_at: Optional[str]


@dataclass
class CompetitorInsight:
    """Insight from competitor analysis."""
    insight_id: str
    source_repo: str
    insight_type: str          # pattern, practice, architecture, tool
    title: str
    description: str
    applicability: float       # 0-1: how applicable to our system
    priority: str              # low, medium, high, critical
    extracted_at: str
    applied: bool
    applied_strategy: Optional[str]


# =============================================================================
# DATABASE
# =============================================================================

def init_db():
    """Initialize operations database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Deployments
    c.execute('''CREATE TABLE IF NOT EXISTS deployments (
        deployment_id TEXT PRIMARY KEY,
        strategy_id TEXT NOT NULL,
        strategy_version INTEGER,
        environment TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        config TEXT,
        deployed_at TEXT,
        deployed_by TEXT,
        metrics_baseline TEXT,
        current_metrics TEXT,
        last_health_check TEXT
    )''')

    # Measurements
    c.execute('''CREATE TABLE IF NOT EXISTS measurements (
        measurement_id TEXT PRIMARY KEY,
        strategy_id TEXT NOT NULL,
        deployment_id TEXT,
        period_start TEXT,
        period_end TEXT,
        kpis TEXT,
        raw_metrics TEXT,
        computed_scores TEXT,
        anomalies TEXT,
        recommendations TEXT
    )''')

    # Drift events
    c.execute('''CREATE TABLE IF NOT EXISTS drift_events (
        drift_id TEXT PRIMARY KEY,
        strategy_id TEXT NOT NULL,
        deployment_id TEXT,
        drift_type TEXT,
        severity TEXT,
        baseline_value REAL,
        current_value REAL,
        change_percent REAL,
        detected_at TEXT,
        description TEXT,
        suggested_action TEXT,
        resolved INTEGER DEFAULT 0,
        resolved_at TEXT
    )''')

    # Competitor insights
    c.execute('''CREATE TABLE IF NOT EXISTS competitor_insights (
        insight_id TEXT PRIMARY KEY,
        source_repo TEXT,
        insight_type TEXT,
        title TEXT,
        description TEXT,
        applicability REAL,
        priority TEXT,
        extracted_at TEXT,
        applied INTEGER DEFAULT 0,
        applied_strategy TEXT
    )''')

    # KPI definitions
    c.execute('''CREATE TABLE IF NOT EXISTS kpi_definitions (
        kpi_id TEXT PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        formula TEXT,
        target_value REAL,
        warning_threshold REAL,
        critical_threshold REAL,
        unit TEXT,
        higher_is_better INTEGER DEFAULT 1
    )''')

    # Health checks
    c.execute('''CREATE TABLE IF NOT EXISTS health_checks (
        check_id TEXT PRIMARY KEY,
        deployment_id TEXT,
        timestamp TEXT,
        status TEXT,
        checks_passed INTEGER,
        checks_failed INTEGER,
        details TEXT
    )''')

    conn.commit()
    conn.close()

    # Seed KPIs
    _seed_kpis()


def _seed_kpis():
    """Seed standard KPI definitions."""
    kpis = [
        ("success_rate", "Strategy Success Rate", "successes / total_executions",
         0.85, 0.70, 0.50, "percentage", 1),
        ("avg_duration", "Average Execution Time", "total_duration / executions",
         5000, 10000, 30000, "milliseconds", 0),
        ("token_efficiency", "Token Efficiency", "value_delivered / tokens_used",
         0.1, 0.05, 0.01, "value/token", 1),
        ("error_rate", "Error Rate", "errors / total_executions",
         0.05, 0.15, 0.30, "percentage", 0),
        ("user_satisfaction", "User Satisfaction Score", "positive_feedback / total_feedback",
         0.9, 0.7, 0.5, "percentage", 1),
        ("cost_per_execution", "Cost Per Execution", "total_cost / executions",
         0.02, 0.05, 0.10, "dollars", 0),
        ("throughput", "Executions Per Hour", "executions / hours",
         10, 5, 2, "executions/hour", 1),
        ("context_utilization", "Context Window Utilization", "tokens_used / context_limit",
         0.6, 0.8, 0.95, "percentage", 0)
    ]

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for kpi in kpis:
        c.execute('''INSERT OR IGNORE INTO kpi_definitions
            (kpi_id, name, description, formula, target_value,
             warning_threshold, critical_threshold, unit, higher_is_better)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (f"kpi_{kpi[0]}", *kpi))

    conn.commit()
    conn.close()


# =============================================================================
# OPERATIONALIZATION
# =============================================================================

def deploy_strategy(
    strategy_id: str,
    environment: str = "production",
    config: Dict = None,
    deployed_by: str = "system"
) -> str:
    """Deploy a strategy to an environment."""
    init_db()

    deployment_id = f"dep_{datetime.now().strftime('%Y%m%d%H%M%S')}_{environment[:3]}"

    # Get baseline metrics from strategy DB
    baseline = _get_strategy_metrics(strategy_id)

    deployment = Deployment(
        deployment_id=deployment_id,
        strategy_id=strategy_id,
        strategy_version=1,
        environment=environment,
        status="active",
        config=config or {},
        deployed_at=datetime.now().isoformat(),
        deployed_by=deployed_by,
        metrics_baseline=baseline,
        current_metrics={},
        last_health_check=datetime.now().isoformat()
    )

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''INSERT INTO deployments
        (deployment_id, strategy_id, strategy_version, environment, status,
         config, deployed_at, deployed_by, metrics_baseline, current_metrics,
         last_health_check)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (deployment.deployment_id, deployment.strategy_id, deployment.strategy_version,
         deployment.environment, deployment.status, json.dumps(deployment.config),
         deployment.deployed_at, deployment.deployed_by,
         json.dumps(deployment.metrics_baseline), json.dumps(deployment.current_metrics),
         deployment.last_health_check))

    conn.commit()
    conn.close()

    return deployment_id


def _get_strategy_metrics(strategy_id: str) -> Dict:
    """Get metrics from strategy database."""
    try:
        conn = sqlite3.connect(STRATEGY_DB)
        c = conn.cursor()
        c.execute('SELECT metrics FROM strategies WHERE strategy_id = ?', (strategy_id,))
        row = c.fetchone()
        conn.close()
        return json.loads(row[0]) if row and row[0] else {}
    except:
        return {}


def pause_deployment(deployment_id: str):
    """Pause a deployment."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE deployments SET status = "paused" WHERE deployment_id = ?',
              (deployment_id,))
    conn.commit()
    conn.close()


def retire_deployment(deployment_id: str):
    """Retire a deployment."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE deployments SET status = "retired" WHERE deployment_id = ?',
              (deployment_id,))
    conn.commit()
    conn.close()


def list_deployments(environment: str = None, status: str = None) -> List[Dict]:
    """List deployments with optional filters."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    query = 'SELECT * FROM deployments WHERE 1=1'
    params = []

    if environment:
        query += ' AND environment = ?'
        params.append(environment)
    if status:
        query += ' AND status = ?'
        params.append(status)

    query += ' ORDER BY deployed_at DESC'
    c.execute(query, params)

    deployments = []
    for row in c.fetchall():
        deployments.append({
            "deployment_id": row[0],
            "strategy_id": row[1],
            "environment": row[3],
            "status": row[4],
            "deployed_at": row[6],
            "last_health_check": row[10]
        })

    conn.close()
    return deployments


# =============================================================================
# MEASUREMENT
# =============================================================================

def measure_strategy(
    strategy_id: str,
    period_days: int = 7,
    deployment_id: str = None
) -> Dict:
    """Measure strategy performance over a period."""
    init_db()

    period_end = datetime.now()
    period_start = period_end - timedelta(days=period_days)

    # Get performance data from strategy DB
    try:
        conn = sqlite3.connect(STRATEGY_DB)
        c = conn.cursor()

        c.execute('''SELECT result, duration_ms, tokens_used, quality_score
                     FROM performance
                     WHERE strategy_id = ?
                     AND timestamp >= ? AND timestamp <= ?''',
                  (strategy_id, period_start.isoformat(), period_end.isoformat()))

        rows = c.fetchall()
        conn.close()
    except:
        rows = []

    if not rows:
        return {"error": "No data for period"}

    # Calculate raw metrics
    total = len(rows)
    successes = sum(1 for r in rows if r[0] == "success")
    durations = [r[1] for r in rows if r[1]]
    tokens = [r[2] for r in rows if r[2]]
    qualities = [r[3] for r in rows if r[3]]

    raw_metrics = {
        "total_executions": total,
        "successes": successes,
        "failures": total - successes,
        "total_duration_ms": sum(durations),
        "total_tokens": sum(tokens),
        "avg_quality": statistics.mean(qualities) if qualities else 0
    }

    # Calculate KPIs
    kpis = {
        "success_rate": successes / total if total else 0,
        "avg_duration": statistics.mean(durations) if durations else 0,
        "token_efficiency": raw_metrics["avg_quality"] / (sum(tokens) / total) if tokens else 0,
        "throughput": total / (period_days * 24) if period_days else 0
    }

    # Compute scores (normalized 0-100)
    scores = {}
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT name, target_value, higher_is_better FROM kpi_definitions')

    for kpi_name, target, higher_better in c.fetchall():
        if kpi_name in kpis:
            value = kpis[kpi_name]
            if higher_better:
                score = min(100, (value / target) * 100) if target else 0
            else:
                score = min(100, (target / value) * 100) if value else 100
            scores[kpi_name] = round(score, 1)

    conn.close()

    # Detect anomalies
    anomalies = []
    if kpis["success_rate"] < 0.7:
        anomalies.append("Low success rate")
    if kpis.get("avg_duration", 0) > 30000:
        anomalies.append("High latency")

    # Generate recommendations
    recommendations = []
    if kpis["success_rate"] < 0.85:
        recommendations.append("Consider A/B testing alternative strategies")
    if scores.get("token_efficiency", 100) < 50:
        recommendations.append("Optimize token usage with caching or compression")

    # Store measurement
    measurement_id = f"meas_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO measurements
        (measurement_id, strategy_id, deployment_id, period_start, period_end,
         kpis, raw_metrics, computed_scores, anomalies, recommendations)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (measurement_id, strategy_id, deployment_id,
         period_start.isoformat(), period_end.isoformat(),
         json.dumps(kpis), json.dumps(raw_metrics), json.dumps(scores),
         json.dumps(anomalies), json.dumps(recommendations)))
    conn.commit()
    conn.close()

    return {
        "measurement_id": measurement_id,
        "period": f"{period_start.date()} to {period_end.date()}",
        "kpis": kpis,
        "scores": scores,
        "anomalies": anomalies,
        "recommendations": recommendations
    }


# =============================================================================
# DRIFT RECOGNITION
# =============================================================================

def detect_drift(
    threshold: float = 0.1,
    lookback_days: int = 7
) -> List[Dict]:
    """Detect strategy drift across all active deployments."""
    init_db()

    drifts_detected = []

    # Get active deployments
    deployments = list_deployments(status="active")

    for dep in deployments:
        drift = _check_deployment_drift(dep["deployment_id"], dep["strategy_id"], threshold)
        if drift:
            drifts_detected.append(drift)

    return drifts_detected


def _check_deployment_drift(
    deployment_id: str,
    strategy_id: str,
    threshold: float
) -> Optional[Dict]:
    """Check a single deployment for drift."""

    # Get baseline from deployment
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT metrics_baseline FROM deployments WHERE deployment_id = ?',
              (deployment_id,))
    row = c.fetchone()
    conn.close()

    if not row or not row[0]:
        return None

    baseline = json.loads(row[0])
    baseline_success = baseline.get("success_rate", 0.8)

    # Get current metrics
    current = _get_strategy_metrics(strategy_id)
    current_success = current.get("success_rate", baseline_success)

    # Calculate drift
    if baseline_success > 0:
        change = (current_success - baseline_success) / baseline_success
    else:
        change = 0

    # Detect significant drift
    if abs(change) > threshold:
        drift_type = "performance"
        if change < 0:
            severity = "high" if abs(change) > 0.2 else "medium"
            description = f"Success rate dropped {abs(change)*100:.1f}%"
            action = "Review recent changes, consider rollback"
        else:
            severity = "low"
            description = f"Success rate improved {change*100:.1f}%"
            action = "Document changes as best practice"

        drift_id = f"drift_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Record drift event
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO drift_events
            (drift_id, strategy_id, deployment_id, drift_type, severity,
             baseline_value, current_value, change_percent, detected_at,
             description, suggested_action)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (drift_id, strategy_id, deployment_id, drift_type, severity,
             baseline_success, current_success, change * 100,
             datetime.now().isoformat(), description, action))
        conn.commit()
        conn.close()

        return {
            "drift_id": drift_id,
            "strategy_id": strategy_id,
            "drift_type": drift_type,
            "severity": severity,
            "change_percent": round(change * 100, 2),
            "description": description,
            "suggested_action": action
        }

    return None


def get_drift_history(strategy_id: str = None, resolved: bool = None) -> List[Dict]:
    """Get drift event history."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    query = 'SELECT * FROM drift_events WHERE 1=1'
    params = []

    if strategy_id:
        query += ' AND strategy_id = ?'
        params.append(strategy_id)
    if resolved is not None:
        query += ' AND resolved = ?'
        params.append(1 if resolved else 0)

    query += ' ORDER BY detected_at DESC LIMIT 50'
    c.execute(query, params)

    events = []
    for row in c.fetchall():
        events.append({
            "drift_id": row[0],
            "strategy_id": row[1],
            "drift_type": row[3],
            "severity": row[4],
            "change_percent": row[7],
            "detected_at": row[8],
            "description": row[9],
            "resolved": bool(row[11])
        })

    conn.close()
    return events


def resolve_drift(drift_id: str, notes: str = ""):
    """Mark a drift event as resolved."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''UPDATE drift_events SET resolved = 1, resolved_at = ?
                 WHERE drift_id = ?''',
              (datetime.now().isoformat(), drift_id))
    conn.commit()
    conn.close()


# =============================================================================
# COMPETITOR ANALYSIS
# =============================================================================

def analyze_competitor(repo: str) -> List[Dict]:
    """Analyze a competitor repository for best practices."""
    init_db()

    # This would normally fetch from GitHub, but we'll create a framework
    # for manual/semi-automated analysis

    insights = []

    # Define analysis categories
    categories = [
        ("architecture", "System Architecture Patterns"),
        ("automation", "Automation & CI/CD Practices"),
        ("testing", "Testing Strategies"),
        ("documentation", "Documentation Patterns"),
        ("tooling", "Tool Selection & Integration")
    ]

    for cat_type, cat_name in categories:
        insight_id = f"ins_{repo.replace('/', '_')}_{cat_type}"

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Check if already analyzed
        c.execute('SELECT * FROM competitor_insights WHERE insight_id = ?', (insight_id,))
        if c.fetchone():
            conn.close()
            continue

        # Create placeholder for analysis
        c.execute('''INSERT INTO competitor_insights
            (insight_id, source_repo, insight_type, title, description,
             applicability, priority, extracted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (insight_id, repo, cat_type, f"{cat_name} from {repo}",
             f"Pending analysis of {cat_name.lower()} patterns",
             0.5, "medium", datetime.now().isoformat()))

        conn.commit()
        conn.close()

        insights.append({
            "insight_id": insight_id,
            "type": cat_type,
            "title": f"{cat_name} from {repo}",
            "status": "pending_analysis"
        })

    return insights


def add_competitor_insight(
    source_repo: str,
    insight_type: str,
    title: str,
    description: str,
    applicability: float = 0.5,
    priority: str = "medium"
) -> str:
    """Add a competitor insight manually."""
    init_db()

    insight_id = f"ins_{hashlib.md5(f'{source_repo}{title}'.encode()).hexdigest()[:12]}"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''INSERT OR REPLACE INTO competitor_insights
        (insight_id, source_repo, insight_type, title, description,
         applicability, priority, extracted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (insight_id, source_repo, insight_type, title, description,
         applicability, priority, datetime.now().isoformat()))

    conn.commit()
    conn.close()

    return insight_id


def get_competitor_insights(
    applied: bool = None,
    priority: str = None
) -> List[Dict]:
    """Get competitor insights."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    query = 'SELECT * FROM competitor_insights WHERE 1=1'
    params = []

    if applied is not None:
        query += ' AND applied = ?'
        params.append(1 if applied else 0)
    if priority:
        query += ' AND priority = ?'
        params.append(priority)

    query += ' ORDER BY applicability DESC, extracted_at DESC'
    c.execute(query, params)

    insights = []
    for row in c.fetchall():
        insights.append({
            "insight_id": row[0],
            "source_repo": row[1],
            "type": row[2],
            "title": row[3],
            "description": row[4],
            "applicability": row[5],
            "priority": row[6],
            "applied": bool(row[8])
        })

    conn.close()
    return insights


def apply_insight(insight_id: str, strategy_id: str):
    """Mark an insight as applied to a strategy."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''UPDATE competitor_insights
                 SET applied = 1, applied_strategy = ?
                 WHERE insight_id = ?''',
              (strategy_id, insight_id))
    conn.commit()
    conn.close()


# =============================================================================
# OPERATIONS DASHBOARD
# =============================================================================

def get_dashboard() -> Dict:
    """Get full operations dashboard."""
    init_db()

    dashboard = {
        "timestamp": datetime.now().isoformat(),
        "deployments": {},
        "health": {},
        "drift": {},
        "kpis": {},
        "insights": {}
    }

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Deployment summary
    c.execute('''SELECT environment, status, COUNT(*)
                 FROM deployments GROUP BY environment, status''')
    dep_summary = {}
    for env, status, count in c.fetchall():
        if env not in dep_summary:
            dep_summary[env] = {}
        dep_summary[env][status] = count
    dashboard["deployments"] = dep_summary

    # Active deployments health
    active = list_deployments(status="active")
    dashboard["health"]["active_deployments"] = len(active)

    # Unresolved drift events
    c.execute('SELECT COUNT(*) FROM drift_events WHERE resolved = 0')
    dashboard["drift"]["unresolved_count"] = c.fetchone()[0]

    c.execute('''SELECT severity, COUNT(*) FROM drift_events
                 WHERE resolved = 0 GROUP BY severity''')
    dashboard["drift"]["by_severity"] = dict(c.fetchall())

    # Recent measurements (last 24h)
    c.execute('''SELECT COUNT(*), AVG(json_extract(kpis, '$.success_rate'))
                 FROM measurements
                 WHERE period_end > datetime('now', '-1 day')''')
    row = c.fetchone()
    dashboard["kpis"]["measurements_24h"] = row[0] or 0
    dashboard["kpis"]["avg_success_rate"] = round(row[1] or 0, 4)

    # Unapplied high-priority insights
    c.execute('''SELECT COUNT(*) FROM competitor_insights
                 WHERE applied = 0 AND priority IN ('high', 'critical')''')
    dashboard["insights"]["actionable_count"] = c.fetchone()[0]

    conn.close()

    return dashboard


def run_health_check(deployment_id: str) -> Dict:
    """Run health check on a deployment."""
    init_db()

    checks = []
    passed = 0
    failed = 0

    # Get deployment info
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT strategy_id, metrics_baseline FROM deployments WHERE deployment_id = ?',
              (deployment_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return {"error": "Deployment not found"}

    strategy_id, baseline_json = row
    baseline = json.loads(baseline_json) if baseline_json else {}
    current = _get_strategy_metrics(strategy_id)

    # Check 1: Success rate above threshold
    success_rate = current.get("success_rate", 0)
    if success_rate >= 0.7:
        checks.append({"name": "success_rate", "status": "pass", "value": success_rate})
        passed += 1
    else:
        checks.append({"name": "success_rate", "status": "fail", "value": success_rate})
        failed += 1

    # Check 2: No major drift
    baseline_rate = baseline.get("success_rate", 0.8)
    drift = abs(success_rate - baseline_rate) / baseline_rate if baseline_rate else 0
    if drift < 0.2:
        checks.append({"name": "drift_check", "status": "pass", "value": drift})
        passed += 1
    else:
        checks.append({"name": "drift_check", "status": "fail", "value": drift})
        failed += 1

    # Check 3: Sample count (enough data)
    sample_count = current.get("sample_count", 0)
    if sample_count >= 5:
        checks.append({"name": "sample_count", "status": "pass", "value": sample_count})
        passed += 1
    else:
        checks.append({"name": "sample_count", "status": "warn", "value": sample_count})

    # Record health check
    check_id = f"hc_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    status = "healthy" if failed == 0 else "degraded" if failed < 2 else "unhealthy"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO health_checks
        (check_id, deployment_id, timestamp, status, checks_passed, checks_failed, details)
        VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (check_id, deployment_id, datetime.now().isoformat(), status, passed, failed,
         json.dumps(checks)))

    # Update deployment
    c.execute('UPDATE deployments SET last_health_check = ? WHERE deployment_id = ?',
              (datetime.now().isoformat(), deployment_id))

    conn.commit()
    conn.close()

    return {
        "check_id": check_id,
        "deployment_id": deployment_id,
        "status": status,
        "passed": passed,
        "failed": failed,
        "checks": checks
    }


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Strategy Operations")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Deploy
    deploy_parser = subparsers.add_parser("deploy", help="Deploy a strategy")
    deploy_parser.add_argument("--strategy", required=True)
    deploy_parser.add_argument("--environment", default="production",
                               choices=["development", "staging", "production"])

    # Measure
    measure_parser = subparsers.add_parser("measure", help="Measure strategy")
    measure_parser.add_argument("--strategy", required=True)
    measure_parser.add_argument("--period", default="7d", help="e.g., 7d, 30d")

    # Drift
    drift_parser = subparsers.add_parser("drift", help="Check for drift")
    drift_parser.add_argument("--threshold", type=float, default=0.1)

    # Competitor
    comp_parser = subparsers.add_parser("competitor", help="Analyze competitor")
    comp_parser.add_argument("--repo", required=True)

    # Dashboard
    subparsers.add_parser("dashboard", help="Full dashboard")

    # Health check
    health_parser = subparsers.add_parser("health", help="Run health check")
    health_parser.add_argument("--deployment", required=True)

    # List deployments
    list_parser = subparsers.add_parser("list", help="List deployments")
    list_parser.add_argument("--environment")
    list_parser.add_argument("--status")

    args = parser.parse_args()

    if args.command == "deploy":
        dep_id = deploy_strategy(args.strategy, args.environment)
        print(f"Deployed: {dep_id}")

    elif args.command == "measure":
        period = int(args.period.replace("d", ""))
        result = measure_strategy(args.strategy, period)
        print(json.dumps(result, indent=2))

    elif args.command == "drift":
        drifts = detect_drift(args.threshold)
        if drifts:
            print(f"Found {len(drifts)} drift events:")
            for d in drifts:
                print(f"  [{d['severity']}] {d['strategy_id']}: {d['description']}")
        else:
            print("No significant drift detected")

    elif args.command == "competitor":
        insights = analyze_competitor(args.repo)
        print(f"Created {len(insights)} insight placeholders for {args.repo}")

    elif args.command == "dashboard":
        dashboard = get_dashboard()
        print(json.dumps(dashboard, indent=2))

    elif args.command == "health":
        result = run_health_check(args.deployment)
        print(f"Status: {result['status']}")
        print(f"Passed: {result['passed']}, Failed: {result['failed']}")
        for check in result['checks']:
            print(f"  {check['name']}: {check['status']} ({check['value']})")

    elif args.command == "list":
        deployments = list_deployments(args.environment, args.status)
        print(f"Found {len(deployments)} deployments:")
        for d in deployments:
            print(f"  [{d['status']}] {d['deployment_id']} - {d['strategy_id']} ({d['environment']})")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
