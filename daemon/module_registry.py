#!/usr/bin/env python3
"""
Module Registry - Prevents capability amnesia.

Tracks ALL integrated modules/repos/patterns with:
1. Source repo origin
2. Current status (active, dormant, broken)
3. Last usage timestamp
4. Integration points

Run periodically to surface unused capabilities.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

DB_PATH = Path(__file__).parent / "module_registry.db"

@dataclass
class Module:
    id: str
    name: str
    source_repo: str
    category: str
    integration_points: List[str]
    status: str
    last_used: Optional[str]
    description: str

# Known integrated modules (hardcoded for persistence)
INTEGRATED_MODULES = [
    # From 12-factor-agents
    Module("12f-context", "Context Engineering", "humanlayer/12-factor-agents", "architecture",
           ["orchestrator.py", "model_router.py"], "active", None,
           "Factor 1: Own your context window"),
    Module("12f-tools", "Tool Library", "humanlayer/12-factor-agents", "architecture",
           [".claude/agents/", ".claude/skills/"], "active", None,
           "Factor 2: Tools as code"),
    Module("12f-state", "Execution State", "humanlayer/12-factor-agents", "architecture",
           [".ai/STATE.md", "daemon/task_queue.py"], "active", None,
           "Factor 5: Unified execution state"),
    Module("12f-cascade", "Cascade Routing", "humanlayer/12-factor-agents", "architecture",
           ["model_router.py:CascadeRouter"], "active", None,
           "Factor 11: Graceful degradation via cascade"),

    # From compound-engineering
    Module("ce-grep-first", "Grep-First Retrieval", "compound-engineering", "retrieval",
           [".claude/agents/learnings-researcher.md"], "dormant", None,
           "Search YAML frontmatter before reading full files"),
    Module("ce-authority", "Authority Memory", "compound-engineering/fat-controller", "memory",
           [".ai/QUICK.md", ".ai/solutions/"], "active", None,
           "Single source of truth per content type"),

    # From hooks-mastery
    Module("hm-uv-scripts", "UV Single-File Scripts", "disler/claude-code-hooks-mastery", "hooks",
           [".claude/hooks/*.py"], "active", None,
           "Inline dependencies with uv run --script"),
    Module("hm-sisyphus", "Sisyphus Pattern", "disler/claude-code-hooks-mastery", "persistence",
           ["daemon/self_continue.py"], "active", None,
           "Background task persistence"),

    # From CDK
    Module("cdk-mcp", "MCP Integration", "peterkrueck/Claude-Code-Development-Kit", "infrastructure",
           [".mcp.json", "daemon/mcp_server.py"], "active", None,
           "Model Context Protocol servers"),

    # From continuous-claude
    Module("cc-handoffs", "Session Handoffs", "continuous-claude", "continuity",
           ["thoughts/handoffs/"], "active", None,
           "State preservation across sessions"),
    Module("cc-ledgers", "Continuity Ledgers", "continuous-claude", "continuity",
           ["thoughts/ledgers/"], "active", None,
           "Long-term goal tracking"),
    Module("cc-self-continue", "Auto-Continuation", "continuous-claude", "execution",
           ["daemon/self_continue.py"], "active", None,
           "Resume from interruption"),

    # From SuperClaude
    Module("sc-agents", "Specialized Agents", "superclaude", "agents",
           [".claude/agents/"], "active", None,
           "48 specialized sub-agents (kraken, scout, etc)"),
    Module("sc-skills", "Skill Library", "superclaude", "skills",
           [".claude/skills/"], "active", None,
           "116 reusable skills"),
    Module("sc-rules", "Behavioral Rules", "superclaude", "rules",
           [".claude/rules/"], "active", None,
           "12 behavioral rules"),

    # From oh-my-opencode
    Module("omoc-optimizer", "Token Optimizer", "code-yeongyu/oh-my-opencode", "optimization",
           ["daemon/token_monitor.py", ".claude/hooks/smart-tool-redirect.py"], "active", None,
           "Token-precious patterns"),

    # Internal modules
    Module("int-orchestrator", "Central Orchestrator", "internal", "core",
           ["daemon/orchestrator.py"], "active", None,
           "Grand strategy unifier"),
    Module("int-router", "Model Router", "internal", "core",
           ["daemon/model_router.py"], "active", None,
           "Cost-aware provider selection"),
    Module("int-scheduler", "LocalAI Scheduler", "internal", "core",
           ["daemon/localai_scheduler.py"], "active", None,
           "Priority queue for local inference"),
    Module("int-memory", "Memory System", "internal", "memory",
           ["daemon/memory.py", ".claude/memory/"], "active", None,
           "Semantic memory with embeddings"),
    Module("int-strategies", "Strategy Evolution", "internal", "optimization",
           ["daemon/strategy_evolution.py"], "dormant", None,
           "Evolutionary approach optimization"),
    Module("int-outcomes", "Outcome Tracker", "internal", "feedback",
           ["daemon/outcome_tracker.py"], "dormant", None,
           "Decision feedback loop"),
    Module("int-tasks", "Task Generator", "internal", "planning",
           ["daemon/task_generator.py"], "active", None,
           "Automated work identification"),
]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS modules (
            id TEXT PRIMARY KEY,
            name TEXT,
            source_repo TEXT,
            category TEXT,
            integration_points TEXT,
            status TEXT,
            last_used TEXT,
            description TEXT,
            registered_at TEXT
        );

        CREATE TABLE IF NOT EXISTS usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id TEXT,
            timestamp TEXT,
            context TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_modules_status ON modules(status);
        CREATE INDEX IF NOT EXISTS idx_usage_module ON usage_log(module_id);
    """)
    conn.commit()
    conn.close()

def sync_modules():
    """Sync hardcoded modules to database."""
    init_db()
    conn = sqlite3.connect(DB_PATH)

    for m in INTEGRATED_MODULES:
        conn.execute("""
            INSERT OR REPLACE INTO modules
            (id, name, source_repo, category, integration_points, status, last_used, description, registered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT registered_at FROM modules WHERE id = ?), ?))
        """, (
            m.id, m.name, m.source_repo, m.category,
            json.dumps(m.integration_points), m.status, m.last_used, m.description,
            m.id, datetime.now().isoformat()
        ))

    conn.commit()
    conn.close()

def log_usage(module_id: str, context: str = ""):
    """Log module usage."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO usage_log (module_id, timestamp, context) VALUES (?, ?, ?)
    """, (module_id, datetime.now().isoformat(), context))
    conn.execute("""
        UPDATE modules SET last_used = ?, status = 'active' WHERE id = ?
    """, (datetime.now().isoformat(), module_id))
    conn.commit()
    conn.close()

def get_dormant_modules(days: int = 7) -> List[Dict]:
    """Get modules not used in N days."""
    conn = sqlite3.connect(DB_PATH)
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    cursor = conn.execute("""
        SELECT id, name, source_repo, category, description, last_used
        FROM modules
        WHERE status != 'broken'
        AND (last_used IS NULL OR last_used < ?)
    """, (cutoff,))
    results = [
        {"id": r[0], "name": r[1], "source": r[2], "category": r[3], "desc": r[4], "last_used": r[5]}
        for r in cursor.fetchall()
    ]
    conn.close()
    return results

def get_module_stats() -> Dict:
    """Get module registry stats."""
    conn = sqlite3.connect(DB_PATH)

    cursor = conn.execute("SELECT status, COUNT(*) FROM modules GROUP BY status")
    by_status = {r[0]: r[1] for r in cursor.fetchall()}

    cursor = conn.execute("SELECT category, COUNT(*) FROM modules GROUP BY category")
    by_category = {r[0]: r[1] for r in cursor.fetchall()}

    cursor = conn.execute("SELECT COUNT(*) FROM modules WHERE last_used IS NULL OR last_used < datetime('now', '-7 days')")
    dormant_count = cursor.fetchone()[0]

    cursor = conn.execute("""
        SELECT module_id, COUNT(*) as uses FROM usage_log
        WHERE timestamp > datetime('now', '-7 days')
        GROUP BY module_id ORDER BY uses DESC LIMIT 5
    """)
    most_used = [{"id": r[0], "uses": r[1]} for r in cursor.fetchall()]

    conn.close()

    return {
        "total": sum(by_status.values()),
        "by_status": by_status,
        "by_category": by_category,
        "dormant_count": dormant_count,
        "most_used_7d": most_used
    }

def surface_forgotten() -> str:
    """Generate reminder of unused capabilities."""
    dormant = get_dormant_modules(7)
    if not dormant:
        return "All modules active."

    lines = ["FORGOTTEN CAPABILITIES (unused 7+ days):"]
    for m in dormant:
        lines.append(f"  [{m['id']}] {m['name']} ({m['source']})")
        lines.append(f"    → {m['desc']}")
    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    sync_modules()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "stats":
            print(json.dumps(get_module_stats(), indent=2))
        elif cmd == "dormant":
            print(json.dumps(get_dormant_modules(), indent=2))
        elif cmd == "forgotten":
            print(surface_forgotten())
        elif cmd == "use":
            if len(sys.argv) > 2:
                log_usage(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
                print(f"Logged usage of {sys.argv[2]}")
    else:
        print("Module Registry Stats:")
        print(json.dumps(get_module_stats(), indent=2))
        print("\n" + surface_forgotten())
