#!/usr/bin/env python3
"""Seed strategies linked to Evolution Plan + Sci-Fi List"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "strategies.db"

def seed():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    strategies = [
        ("S001", "Phase14-TokenOpt", "token_efficiency", "Enforce token-optimizer-MCP",
         ["enforce smart_read hook", "redirect Grep to smart_grep", "measure savings"],
         {"token_savings": 0.7, "context_reduction": 0.6}),

        ("S002", "Phase14-Bisim", "learning", "Wire bisimulation to decisions.py",
         ["add bisim check to decisions", "transfer policies on match", "track transfer rate"],
         {"transfer_rate": 0.3, "learning_speed": 2.0}),

        ("S003", "Phase15-Memory", "architecture", "Unify memory systems",
         ["consolidate DBs", "implement 3-tier", "single search interface"],
         {"query_latency_ms": 10, "cache_hit_rate": 0.8}),

        ("S004", "Phase15-MAPE", "automation", "Enable continuous MAPE daemon",
         ["run hourly cycles", "auto-detect drift", "self-tune parameters"],
         {"drift_detection": 0.9, "self_optimization": 0.5}),

        ("S005", "SciFi-Jarvis", "capability", "Voice interface with Whisper + Piper",
         ["add Whisper to LocalAI", "integrate Piper TTS", "WebSocket streaming"],
         {"voice_accuracy": 0.95, "response_time_ms": 500}),

        ("S006", "SciFi-Data", "insight", "Cross-domain pattern detection",
         ["unified embeddings", "HDBSCAN clustering", "correlation scoring"],
         {"patterns_found": 20, "insight_value": 0.7}),

        ("S007", "SciFi-Oracle", "prediction", "Predictive analytics with forecasting",
         ["Prophet for trends", "Monte Carlo simulation", "calibration tracking"],
         {"prediction_accuracy": 0.7, "lead_time_days": 7}),
    ]

    for sid, name, stype, desc, actions, metrics in strategies:
        c.execute('''INSERT OR REPLACE INTO strategies
            (strategy_id, name, version, type, status, description, actions,
             preconditions, postconditions, constraints, metrics, generation,
             created_at, updated_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (sid, name, 1, stype, "active", desc, json.dumps(actions),
             "[]", "[]", "[]", json.dumps(metrics), 0,
             datetime.now().isoformat(), datetime.now().isoformat(), "{}"))
        print(f"Created: {sid} - {name} ({stype})")

    conn.commit()
    conn.close()
    print("\nSeeded 7 strategies linked to Evolution Plan + Sci-Fi List")

if __name__ == "__main__":
    seed()
