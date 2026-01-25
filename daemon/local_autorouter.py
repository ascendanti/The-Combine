#!/usr/bin/env python3
"""
Local AI AutoRouter - Minimize Claude Token Usage

Smart routing using FREE LocalAI to decide what needs Claude vs what LocalAI can handle.
Runs iteratively/cyclically to continuously optimize routing decisions.

Architecture:
    User Request → LocalAI Classifier → Route Decision → Execute
                         ↑                    ↓
                         └── Outcome Feedback ←┘

Key Insight: Use "dumb" local AI for smart routing decisions because:
1. Routing is a classification task (LocalAI is good at this)
2. LocalAI is FREE (no token cost)
3. Routing decisions don't need complex reasoning
4. We can learn from outcomes to improve routing

Cyclic Processes:
1. Request Classification (per request)
2. Outcome Learning (per response)
3. Route Optimization (hourly)
4. Pattern Discovery (daily)

Usage:
    # Route a request
    python daemon/local_autorouter.py route "help me fix a bug in auth.py"

    # Run optimization cycle
    python daemon/local_autorouter.py optimize

    # Check routing stats
    python daemon/local_autorouter.py stats

    # Start daemon (continuous optimization)
    python daemon/local_autorouter.py daemon
"""

import sqlite3
import json
import hashlib
import time
import requests
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re

DB_PATH = Path(__file__).parent / "router.db"
LOCALAI_URL = "http://localhost:8080/v1"
LOCALAI_MODEL = "mistral-7b-instruct-v0.3"


# =============================================================================
# ROUTE DEFINITIONS
# =============================================================================

# Routes define where requests should go
ROUTES = {
    # LocalAI can handle (FREE)
    "localai": {
        "intents": ["summarize", "extract", "translate", "format", "simple_qa"],
        "max_complexity": 3,  # 1-10 scale
        "cost": 0.0
    },
    # Codex for code tasks (cheap)
    "codex": {
        "intents": ["code_generate", "code_review", "code_fix", "refactor"],
        "max_complexity": 6,
        "cost": 0.01
    },
    # Claude for complex reasoning (expensive)
    "claude": {
        "intents": ["architecture", "complex_reasoning", "novel_task", "judgment"],
        "max_complexity": 10,
        "cost": 0.10
    },
    # Agents (delegated complexity)
    "agent:scout": {
        "intents": ["explore", "find_code", "understand_codebase"],
        "max_complexity": 7,
        "cost": 0.05  # Estimated
    },
    "agent:oracle": {
        "intents": ["research", "external_docs", "web_search"],
        "max_complexity": 5,
        "cost": 0.03
    },
    "agent:kraken": {
        "intents": ["implement", "tdd", "complex_code"],
        "max_complexity": 8,
        "cost": 0.08
    },
    "agent:spark": {
        "intents": ["quick_fix", "simple_edit", "typo"],
        "max_complexity": 3,
        "cost": 0.02
    },
    # Skills (workflow shortcuts)
    "skill:commit": {
        "intents": ["commit", "git_commit", "save_changes"],
        "max_complexity": 2,
        "cost": 0.01
    },
    "skill:fix": {
        "intents": ["fix_bug", "debug", "resolve_error"],
        "max_complexity": 5,
        "cost": 0.04
    }
}

# Intent keywords for fast classification
INTENT_KEYWORDS = {
    "summarize": ["summarize", "summary", "tldr", "brief", "overview"],
    "extract": ["extract", "get", "pull out", "find the"],
    "translate": ["translate", "convert", "transform"],
    "format": ["format", "prettify", "clean up"],
    "simple_qa": ["what is", "define", "explain simply"],
    "code_generate": ["write code", "create function", "implement"],
    "code_review": ["review", "check code", "audit"],
    "code_fix": ["fix code", "fix bug", "correct"],
    "refactor": ["refactor", "improve code", "clean code"],
    "architecture": ["architecture", "design system", "structure"],
    "complex_reasoning": ["analyze", "evaluate", "compare", "decide"],
    "novel_task": ["new approach", "creative", "innovative"],
    "judgment": ["should i", "is it good", "which is better"],
    "explore": ["explore", "find where", "locate"],
    "find_code": ["find function", "where is", "search for"],
    "understand_codebase": ["how does", "understand", "explain code"],
    "research": ["research", "look up", "find docs"],
    "external_docs": ["documentation", "api docs", "library"],
    "web_search": ["search web", "google", "latest"],
    "implement": ["implement feature", "build", "create"],
    "tdd": ["test driven", "write tests", "tdd"],
    "complex_code": ["complex feature", "multi-file"],
    "quick_fix": ["quick fix", "simple fix", "easy fix"],
    "simple_edit": ["edit", "change", "modify"],
    "typo": ["typo", "spelling", "rename"],
    "commit": ["commit", "save", "git commit"],
    "fix_bug": ["fix bug", "debug", "error"],
    "resolve_error": ["resolve", "fix error"]
}


# =============================================================================
# DATABASE
# =============================================================================

def init_db():
    """Initialize router database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Routing decisions
    c.execute('''CREATE TABLE IF NOT EXISTS routing_decisions (
        decision_id TEXT PRIMARY KEY,
        request_hash TEXT,
        request_text TEXT,
        detected_intent TEXT,
        complexity_score REAL,
        chosen_route TEXT,
        confidence REAL,
        actual_route TEXT,
        outcome TEXT,
        tokens_saved INTEGER,
        timestamp TEXT
    )''')

    # Route performance
    c.execute('''CREATE TABLE IF NOT EXISTS route_performance (
        route TEXT PRIMARY KEY,
        total_uses INTEGER DEFAULT 0,
        successes INTEGER DEFAULT 0,
        avg_tokens REAL DEFAULT 0,
        avg_duration_ms REAL DEFAULT 0,
        last_used TEXT,
        last_updated TEXT
    )''')

    # Intent patterns (learned)
    c.execute('''CREATE TABLE IF NOT EXISTS intent_patterns (
        pattern_id TEXT PRIMARY KEY,
        pattern TEXT,
        intent TEXT,
        confidence REAL,
        sample_count INTEGER DEFAULT 0,
        last_updated TEXT
    )''')

    # Optimization history
    c.execute('''CREATE TABLE IF NOT EXISTS optimization_runs (
        run_id TEXT PRIMARY KEY,
        timestamp TEXT,
        decisions_analyzed INTEGER,
        patterns_updated INTEGER,
        routes_adjusted INTEGER,
        estimated_savings REAL
    )''')

    conn.commit()
    conn.close()


# =============================================================================
# LOCALAI CLASSIFICATION
# =============================================================================

def classify_with_localai(text: str) -> Dict:
    """Use LocalAI to classify intent and complexity."""

    prompt = f"""Classify this request. Respond with JSON only.

Request: "{text[:500]}"

Classify:
1. intent: One of [summarize, extract, code_generate, code_fix, refactor, explore, research, implement, quick_fix, complex_reasoning, architecture]
2. complexity: 1-10 (1=trivial, 5=moderate, 10=very complex)
3. needs_context: true/false (needs codebase knowledge?)
4. needs_reasoning: true/false (needs multi-step thinking?)

JSON:"""

    try:
        response = requests.post(
            f"{LOCALAI_URL}/chat/completions",
            json={
                "model": LOCALAI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 150,
                "temperature": 0.1
            },
            timeout=30
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]

        # Parse JSON from response
        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())

    except Exception as e:
        print(f"[LocalAI Classification Error] {e}")

    # Fallback to keyword classification
    return classify_with_keywords(text)


def classify_with_keywords(text: str) -> Dict:
    """Fast keyword-based classification (no LLM needed)."""
    text_lower = text.lower()

    # Find matching intents
    intent_scores = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            intent_scores[intent] = score

    # Best intent
    if intent_scores:
        best_intent = max(intent_scores, key=intent_scores.get)
    else:
        best_intent = "complex_reasoning"  # Default to Claude

    # Estimate complexity from text length and keywords
    complexity = 3  # Base
    if len(text) > 500:
        complexity += 2
    if any(kw in text_lower for kw in ["architecture", "design", "system"]):
        complexity += 3
    if any(kw in text_lower for kw in ["simple", "quick", "easy", "just"]):
        complexity -= 2
    complexity = max(1, min(10, complexity))

    return {
        "intent": best_intent,
        "complexity": complexity,
        "needs_context": "code" in text_lower or "file" in text_lower,
        "needs_reasoning": complexity > 5
    }


# =============================================================================
# ROUTING LOGIC
# =============================================================================

def route_request(text: str, use_localai: bool = True) -> Dict:
    """Route a request to the best handler."""
    init_db()

    # Classify
    if use_localai:
        classification = classify_with_localai(text)
    else:
        classification = classify_with_keywords(text)

    intent = classification.get("intent", "complex_reasoning")
    complexity = classification.get("complexity", 5)
    needs_reasoning = classification.get("needs_reasoning", False)

    # Find best route
    best_route = None
    best_score = -1

    for route, config in ROUTES.items():
        if intent in config["intents"]:
            if complexity <= config["max_complexity"]:
                # Score: prefer cheaper routes that can handle it
                score = (config["max_complexity"] - complexity) + (1 / (config["cost"] + 0.001))
                if score > best_score:
                    best_score = score
                    best_route = route

    # Fallback logic
    if not best_route:
        if needs_reasoning or complexity > 6:
            best_route = "claude"
        elif complexity <= 3:
            best_route = "localai"
        else:
            best_route = "codex"

    # Calculate confidence
    confidence = min(1.0, best_score / 100) if best_score > 0 else 0.5

    # Check historical performance
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT successes, total_uses FROM route_performance WHERE route = ?',
              (best_route,))
    row = c.fetchone()
    if row and row[1] > 10:
        historical_rate = row[0] / row[1]
        confidence = (confidence + historical_rate) / 2
    conn.close()

    # Record decision
    decision_id = f"dec_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hashlib.md5(text.encode()).hexdigest()[:8]}"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO routing_decisions
        (decision_id, request_hash, request_text, detected_intent, complexity_score,
         chosen_route, confidence, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (decision_id, hashlib.md5(text.encode()).hexdigest(), text[:500],
         intent, complexity, best_route, confidence, datetime.now().isoformat()))
    conn.commit()
    conn.close()

    return {
        "decision_id": decision_id,
        "route": best_route,
        "intent": intent,
        "complexity": complexity,
        "confidence": round(confidence, 3),
        "estimated_cost": ROUTES.get(best_route, {}).get("cost", 0.1),
        "reasoning": f"Intent={intent}, Complexity={complexity}/10"
    }


def record_outcome(decision_id: str, outcome: str, actual_route: str = None,
                   tokens_used: int = 0):
    """Record the outcome of a routing decision."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Get original decision
    c.execute('SELECT chosen_route FROM routing_decisions WHERE decision_id = ?',
              (decision_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return

    chosen_route = row[0]
    actual_route = actual_route or chosen_route

    # Estimate tokens saved vs Claude
    claude_estimate = 5000  # Estimated Claude tokens for average task
    tokens_saved = claude_estimate - tokens_used if actual_route != "claude" else 0

    # Update decision
    c.execute('''UPDATE routing_decisions SET
        actual_route = ?, outcome = ?, tokens_saved = ?
        WHERE decision_id = ?''',
        (actual_route, outcome, tokens_saved, decision_id))

    # Update route performance
    c.execute('''INSERT OR REPLACE INTO route_performance
        (route, total_uses, successes, avg_tokens, last_used, last_updated)
        VALUES (
            ?,
            COALESCE((SELECT total_uses FROM route_performance WHERE route = ?), 0) + 1,
            COALESCE((SELECT successes FROM route_performance WHERE route = ?), 0) + ?,
            COALESCE((SELECT (avg_tokens * total_uses + ?) / (total_uses + 1)
                     FROM route_performance WHERE route = ?), ?),
            ?, ?
        )''',
        (actual_route, actual_route, actual_route, 1 if outcome == "success" else 0,
         tokens_used, actual_route, tokens_used,
         datetime.now().isoformat(), datetime.now().isoformat()))

    conn.commit()
    conn.close()


# =============================================================================
# CYCLIC OPTIMIZATION
# =============================================================================

def run_optimization_cycle():
    """Run optimization cycle to improve routing."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    print("[Optimization] Starting cycle...")

    # 1. Analyze recent decisions
    c.execute('''SELECT detected_intent, chosen_route, outcome, complexity_score
                 FROM routing_decisions
                 WHERE timestamp > datetime('now', '-24 hours')
                 AND outcome IS NOT NULL''')

    decisions = c.fetchall()
    print(f"  Analyzing {len(decisions)} recent decisions")

    # 2. Find patterns
    intent_route_success = {}  # (intent, route) -> [success_rate, count]
    for intent, route, outcome, complexity in decisions:
        key = (intent, route)
        if key not in intent_route_success:
            intent_route_success[key] = [0, 0]
        intent_route_success[key][1] += 1
        if outcome == "success":
            intent_route_success[key][0] += 1

    # 3. Update intent patterns
    patterns_updated = 0
    for (intent, route), (successes, total) in intent_route_success.items():
        if total >= 3:  # Minimum samples
            success_rate = successes / total
            pattern_id = f"pat_{intent}_{route}"

            c.execute('''INSERT OR REPLACE INTO intent_patterns
                (pattern_id, pattern, intent, confidence, sample_count, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (pattern_id, f"{intent}:{route}", intent, success_rate, total,
                 datetime.now().isoformat()))
            patterns_updated += 1

    # 4. Calculate estimated savings
    c.execute('''SELECT SUM(tokens_saved) FROM routing_decisions
                 WHERE timestamp > datetime('now', '-24 hours')''')
    total_saved = c.fetchone()[0] or 0

    # 5. Record optimization run
    run_id = f"opt_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    c.execute('''INSERT INTO optimization_runs
        (run_id, timestamp, decisions_analyzed, patterns_updated, routes_adjusted, estimated_savings)
        VALUES (?, ?, ?, ?, ?, ?)''',
        (run_id, datetime.now().isoformat(), len(decisions), patterns_updated, 0, total_saved))

    conn.commit()
    conn.close()

    print(f"  Patterns updated: {patterns_updated}")
    print(f"  Estimated tokens saved (24h): {total_saved}")

    return {
        "decisions_analyzed": len(decisions),
        "patterns_updated": patterns_updated,
        "tokens_saved_24h": total_saved
    }


def run_daemon(interval_minutes: int = 60):
    """Run continuous optimization daemon."""
    print(f"[AutoRouter Daemon] Starting (interval: {interval_minutes}min)")

    while True:
        try:
            result = run_optimization_cycle()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Cycle complete: {result}")
        except Exception as e:
            print(f"[Error] {e}")

        time.sleep(interval_minutes * 60)


# =============================================================================
# STATS AND REPORTING
# =============================================================================

def get_stats() -> Dict:
    """Get routing statistics."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Overall stats
    c.execute('''SELECT
        COUNT(*) as total,
        SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) as successes,
        SUM(tokens_saved) as total_saved
        FROM routing_decisions WHERE outcome IS NOT NULL''')
    row = c.fetchone()

    # Route breakdown
    c.execute('''SELECT route, total_uses, successes, avg_tokens
                 FROM route_performance ORDER BY total_uses DESC''')
    routes = [{"route": r[0], "uses": r[1], "success_rate": r[2]/r[1] if r[1] else 0,
               "avg_tokens": r[3]} for r in c.fetchall()]

    # Recent patterns
    c.execute('''SELECT pattern, confidence, sample_count FROM intent_patterns
                 ORDER BY sample_count DESC LIMIT 10''')
    patterns = [{"pattern": r[0], "confidence": r[1], "samples": r[2]}
                for r in c.fetchall()]

    conn.close()

    return {
        "total_decisions": row[0] or 0,
        "success_rate": round(row[1] / row[0], 4) if row[0] else 0,
        "total_tokens_saved": row[2] or 0,
        "estimated_cost_saved": round((row[2] or 0) * 0.00001, 2),  # ~$0.01/1000 tokens
        "routes": routes,
        "top_patterns": patterns
    }


def get_routing_recommendation(text: str) -> str:
    """Get a simple routing recommendation string."""
    result = route_request(text, use_localai=False)  # Fast, no LLM call
    route = result["route"]

    recommendations = {
        "localai": "Use LocalAI (FREE) - simple task",
        "codex": "Use Codex ($0.01) - code task",
        "claude": "Use Claude - complex reasoning needed",
        "agent:scout": "Delegate to scout agent - exploration task",
        "agent:oracle": "Delegate to oracle agent - research task",
        "agent:kraken": "Delegate to kraken agent - implementation task",
        "agent:spark": "Delegate to spark agent - quick fix",
        "skill:commit": "Use commit skill - git operation",
        "skill:fix": "Use fix skill - bug fixing workflow"
    }

    return recommendations.get(route, f"Route to {route}")


# =============================================================================
# SMART FUNCTIONS FOR HOOKS
# =============================================================================

def should_use_localai(text: str) -> bool:
    """Quick check if LocalAI can handle this request."""
    classification = classify_with_keywords(text)
    return classification["complexity"] <= 3 and not classification["needs_reasoning"]


def get_best_agent(text: str) -> Optional[str]:
    """Get the best agent for this request, or None if no agent needed."""
    result = route_request(text, use_localai=False)
    if result["route"].startswith("agent:"):
        return result["route"].replace("agent:", "")
    return None


def estimate_token_cost(text: str) -> Dict:
    """Estimate token cost for different routing options."""
    result = route_request(text, use_localai=False)

    return {
        "recommended_route": result["route"],
        "estimated_cost": result["estimated_cost"],
        "if_localai": 0.0,
        "if_claude": 0.10,
        "savings_vs_claude": round(0.10 - result["estimated_cost"], 3)
    }


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Local AI AutoRouter")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Route command
    route_parser = subparsers.add_parser("route", help="Route a request")
    route_parser.add_argument("text", help="Request text")
    route_parser.add_argument("--fast", action="store_true", help="Skip LocalAI, use keywords only")

    # Optimize command
    subparsers.add_parser("optimize", help="Run optimization cycle")

    # Stats command
    subparsers.add_parser("stats", help="Show routing statistics")

    # Daemon command
    daemon_parser = subparsers.add_parser("daemon", help="Run continuous daemon")
    daemon_parser.add_argument("--interval", type=int, default=60, help="Minutes between cycles")

    # Record command
    rec_parser = subparsers.add_parser("record", help="Record outcome")
    rec_parser.add_argument("--decision", required=True, help="Decision ID")
    rec_parser.add_argument("--outcome", required=True, choices=["success", "partial", "failure"])
    rec_parser.add_argument("--tokens", type=int, default=0)

    args = parser.parse_args()

    if args.command == "route":
        result = route_request(args.text, use_localai=not args.fast)
        print(f"\nRouting Decision:")
        print(f"  Route: {result['route']}")
        print(f"  Intent: {result['intent']}")
        print(f"  Complexity: {result['complexity']}/10")
        print(f"  Confidence: {result['confidence']*100:.1f}%")
        print(f"  Est. Cost: ${result['estimated_cost']:.3f}")
        print(f"\n  Decision ID: {result['decision_id']}")

    elif args.command == "optimize":
        result = run_optimization_cycle()
        print(f"\nOptimization Complete:")
        print(f"  Decisions analyzed: {result['decisions_analyzed']}")
        print(f"  Patterns updated: {result['patterns_updated']}")
        print(f"  Tokens saved (24h): {result['tokens_saved_24h']}")

    elif args.command == "stats":
        stats = get_stats()
        print(f"\nRouting Statistics:")
        print(f"  Total decisions: {stats['total_decisions']}")
        print(f"  Success rate: {stats['success_rate']*100:.1f}%")
        print(f"  Tokens saved: {stats['total_tokens_saved']}")
        print(f"  Est. cost saved: ${stats['estimated_cost_saved']:.2f}")
        print(f"\nRoute Usage:")
        for r in stats['routes'][:5]:
            print(f"  {r['route']}: {r['uses']} uses, {r['success_rate']*100:.0f}% success")

    elif args.command == "daemon":
        run_daemon(args.interval)

    elif args.command == "record":
        record_outcome(args.decision, args.outcome, tokens_used=args.tokens)
        print(f"Recorded outcome: {args.outcome}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
