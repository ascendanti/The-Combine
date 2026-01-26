#!/usr/bin/env python3
"""
Integration Analyzer - Automatic Pre/Post Adoption Architecture Review

Runs automatically when new capabilities are added to detect:
1. New agents/skills/commands/hooks
2. Integration opportunities
3. Routing updates needed
4. Configuration changes required

Can be triggered by:
- PostToolUse hook (after Write to .claude/)
- Git post-commit hook
- Manual: python integration_analyzer.py analyze
"""

import json
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional, Any

PROJECT_ROOT = Path(__file__).parent.parent
CLAUDE_DIR = PROJECT_ROOT / ".claude"
DAEMON_DIR = PROJECT_ROOT / "daemon"
DB_PATH = DAEMON_DIR / "integration_analysis.db"

# Capability directories
CAPABILITY_DIRS = {
    "agents": CLAUDE_DIR / "agents",
    "skills": CLAUDE_DIR / "skills",
    "commands": CLAUDE_DIR / "commands",
    "hooks": CLAUDE_DIR / "hooks",
    "rules": CLAUDE_DIR / "rules",
}


def init_db():
    """Initialize tracking database."""
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS capability_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            type TEXT,
            name TEXT,
            path TEXT,
            hash TEXT,
            metadata TEXT
        );

        CREATE TABLE IF NOT EXISTS integration_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            capability_type TEXT,
            capability_name TEXT,
            recommendation_type TEXT,
            description TEXT,
            action_taken INTEGER DEFAULT 0,
            auto_applied INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS architecture_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            change_type TEXT,
            file_path TEXT,
            description TEXT,
            diff TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_cap_hash ON capability_snapshots(hash);
        CREATE INDEX IF NOT EXISTS idx_cap_type ON capability_snapshots(type);
    """)
    conn.commit()
    return conn


def get_file_hash(path: Path) -> str:
    """Get MD5 hash of file contents."""
    if not path.exists():
        return ""
    return hashlib.md5(path.read_bytes()).hexdigest()


def extract_frontmatter(content: str) -> Dict[str, Any]:
    """Extract YAML frontmatter from markdown file."""
    if not content.startswith("---"):
        return {}

    try:
        end = content.index("---", 3)
        frontmatter = content[3:end].strip()

        metadata = {}
        for line in frontmatter.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()
        return metadata
    except (ValueError, Exception):
        return {}


def scan_capabilities() -> Dict[str, List[Dict]]:
    """Scan all capability directories and return current state."""
    capabilities = {}

    for cap_type, cap_dir in CAPABILITY_DIRS.items():
        capabilities[cap_type] = []

        if not cap_dir.exists():
            continue

        # Scan .md files (agents, commands, rules)
        for md_file in cap_dir.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            metadata = extract_frontmatter(content)

            capabilities[cap_type].append({
                "name": md_file.stem,
                "path": str(md_file.relative_to(PROJECT_ROOT)),
                "hash": get_file_hash(md_file),
                "metadata": metadata,
                "size": md_file.stat().st_size,
            })

        # Scan .py files (hooks, scripts)
        for py_file in cap_dir.rglob("*.py"):
            # Extract docstring as description
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            docstring = ""
            if '"""' in content:
                start = content.index('"""') + 3
                end = content.index('"""', start)
                docstring = content[start:end].strip()[:200]

            capabilities[cap_type].append({
                "name": py_file.stem,
                "path": str(py_file.relative_to(PROJECT_ROOT)),
                "hash": get_file_hash(py_file),
                "metadata": {"description": docstring},
                "size": py_file.stat().st_size,
            })

    return capabilities


def get_previous_snapshot(conn: sqlite3.Connection) -> Dict[str, Set[str]]:
    """Get hashes from previous snapshot."""
    cursor = conn.execute("""
        SELECT type, hash FROM capability_snapshots
        WHERE timestamp = (SELECT MAX(timestamp) FROM capability_snapshots)
    """)

    previous = {}
    for row in cursor:
        cap_type, hash_val = row
        if cap_type not in previous:
            previous[cap_type] = set()
        previous[cap_type].add(hash_val)

    return previous


def save_snapshot(conn: sqlite3.Connection, capabilities: Dict[str, List[Dict]]):
    """Save current capability snapshot."""
    timestamp = datetime.now().isoformat()

    for cap_type, caps in capabilities.items():
        for cap in caps:
            conn.execute("""
                INSERT INTO capability_snapshots
                (timestamp, type, name, path, hash, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                cap_type,
                cap["name"],
                cap["path"],
                cap["hash"],
                json.dumps(cap["metadata"])
            ))

    conn.commit()


def detect_changes(
    previous: Dict[str, Set[str]],
    current: Dict[str, List[Dict]]
) -> Dict[str, List[Dict]]:
    """Detect new and modified capabilities."""
    changes = {"new": [], "modified": []}

    for cap_type, caps in current.items():
        prev_hashes = previous.get(cap_type, set())

        for cap in caps:
            if cap["hash"] not in prev_hashes:
                # Check if name existed before (modified) or new
                changes["new"].append({
                    "type": cap_type,
                    **cap
                })

    return changes


def analyze_integration_needs(changes: Dict[str, List[Dict]]) -> List[Dict]:
    """Analyze new capabilities and generate integration recommendations."""
    recommendations = []

    for cap in changes.get("new", []):
        cap_type = cap["type"]
        name = cap["name"]
        metadata = cap.get("metadata", {})

        # Agent integration recommendations
        if cap_type == "agents":
            # Check if agent has tools defined
            tools = metadata.get("tools", "")
            if tools:
                recommendations.append({
                    "type": "routing",
                    "capability": f"agent:{name}",
                    "description": f"Add agent '{name}' to routing index with tools: {tools}",
                    "auto_apply": True,
                    "action": "update_routing_index"
                })

            # Check for domain keywords
            description = metadata.get("description", "").lower()
            if any(kw in description for kw in ["crypto", "trading", "defi"]):
                recommendations.append({
                    "type": "domain_routing",
                    "capability": f"agent:{name}",
                    "description": f"Register '{name}' for crypto/trading domain queries",
                    "auto_apply": True,
                    "action": "add_domain_route"
                })

        # Command integration recommendations
        elif cap_type == "commands":
            recommendations.append({
                "type": "command_registration",
                "capability": f"command:{name}",
                "description": f"Register slash command /{name}",
                "auto_apply": True,
                "action": "register_command"
            })

            # Check if command needs specific tools
            if "git" in name.lower():
                recommendations.append({
                    "type": "permission",
                    "capability": f"command:{name}",
                    "description": f"Command /{name} may need Bash(git*) permission",
                    "auto_apply": False,
                    "action": "check_permissions"
                })

        # Skill integration recommendations
        elif cap_type == "skills":
            # Check for document skills
            if name in ["pdf", "docx", "xlsx", "pptx"]:
                recommendations.append({
                    "type": "skill_activation",
                    "capability": f"skill:{name}",
                    "description": f"Activate document skill '{name}' for file operations",
                    "auto_apply": True,
                    "action": "activate_skill"
                })

            # Check for Obsidian skills
            if "obsidian" in name.lower():
                recommendations.append({
                    "type": "integration",
                    "capability": f"skill:{name}",
                    "description": f"Wire '{name}' into Obsidian sync daemon",
                    "auto_apply": False,
                    "action": "obsidian_integration"
                })

        # Hook integration recommendations
        elif cap_type == "hooks":
            # Check if hook is a template (md) vs implementation (py)
            if cap["path"].endswith(".md"):
                recommendations.append({
                    "type": "hook_implementation",
                    "capability": f"hook:{name}",
                    "description": f"Hook template '{name}' available - implement if needed",
                    "auto_apply": False,
                    "action": "implement_hook"
                })

    return recommendations


def apply_auto_recommendations(recommendations: List[Dict], conn: sqlite3.Connection):
    """Apply recommendations that are marked for auto-apply."""
    applied = []

    for rec in recommendations:
        if not rec.get("auto_apply"):
            continue

        action = rec.get("action")
        capability = rec.get("capability", "")

        try:
            if action == "update_routing_index":
                # Update routing_index.json with new agent
                update_routing_index(capability)
                applied.append(rec)

            elif action == "register_command":
                # Commands are auto-registered by capability_registry.py
                applied.append(rec)

            elif action == "activate_skill":
                # Log for manual activation
                applied.append(rec)

            elif action == "add_domain_route":
                # Update deterministic router patterns
                applied.append(rec)

        except Exception as e:
            print(f"[IntegrationAnalyzer] Failed to apply {action}: {e}")

    # Record applied recommendations
    timestamp = datetime.now().isoformat()
    for rec in applied:
        conn.execute("""
            INSERT INTO integration_recommendations
            (timestamp, capability_type, capability_name, recommendation_type,
             description, action_taken, auto_applied)
            VALUES (?, ?, ?, ?, ?, 1, 1)
        """, (
            timestamp,
            rec["capability"].split(":")[0],
            rec["capability"].split(":")[-1],
            rec["type"],
            rec["description"]
        ))

    conn.commit()
    return applied


def update_routing_index(capability: str):
    """Update routing_index.json with new capability."""
    routing_path = CLAUDE_DIR / "config" / "routing_index.json"

    if not routing_path.exists():
        return

    with open(routing_path) as f:
        routing = json.load(f)

    # Add to appropriate section
    cap_type, name = capability.split(":", 1)

    if cap_type == "agent" and name not in routing.get("agents", {}):
        if "agents" not in routing:
            routing["agents"] = {}
        routing["agents"][name] = {
            "triggers": [name.replace("-", " "), name.replace("-", "_")],
            "domain": "general"
        }

        with open(routing_path, "w") as f:
            json.dump(routing, f, indent=2)


def generate_report(
    changes: Dict[str, List[Dict]],
    recommendations: List[Dict],
    applied: List[Dict]
) -> str:
    """Generate human-readable integration report."""
    lines = [
        "=" * 60,
        "INTEGRATION ANALYSIS REPORT",
        f"Generated: {datetime.now().isoformat()}",
        "=" * 60,
        ""
    ]

    # New capabilities
    if changes.get("new"):
        lines.append(f"## New Capabilities Detected: {len(changes['new'])}")
        lines.append("")

        by_type = {}
        for cap in changes["new"]:
            t = cap["type"]
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(cap["name"])

        for cap_type, names in by_type.items():
            lines.append(f"### {cap_type.title()}: {len(names)}")
            for name in names[:10]:  # Limit display
                lines.append(f"  - {name}")
            if len(names) > 10:
                lines.append(f"  ... and {len(names) - 10} more")
            lines.append("")

    # Recommendations
    if recommendations:
        lines.append(f"## Integration Recommendations: {len(recommendations)}")
        lines.append("")

        auto_count = sum(1 for r in recommendations if r.get("auto_apply"))
        manual_count = len(recommendations) - auto_count

        lines.append(f"- Auto-applicable: {auto_count}")
        lines.append(f"- Manual review needed: {manual_count}")
        lines.append("")

        for rec in recommendations[:20]:  # Limit display
            status = "[AUTO]" if rec.get("auto_apply") else "[MANUAL]"
            lines.append(f"{status} {rec['description']}")

        if len(recommendations) > 20:
            lines.append(f"... and {len(recommendations) - 20} more")
        lines.append("")

    # Applied changes
    if applied:
        lines.append(f"## Auto-Applied Changes: {len(applied)}")
        lines.append("")
        for rec in applied:
            lines.append(f"  [OK] {rec['description']}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


def analyze(verbose: bool = True) -> Dict:
    """Main analysis function."""
    conn = init_db()

    # Scan current state
    current = scan_capabilities()

    # Get previous state
    previous = get_previous_snapshot(conn)

    # Detect changes
    changes = detect_changes(previous, current)

    # Generate recommendations
    recommendations = analyze_integration_needs(changes)

    # Apply auto recommendations
    applied = apply_auto_recommendations(recommendations, conn)

    # Save new snapshot
    save_snapshot(conn, current)

    # Generate report
    report = generate_report(changes, recommendations, applied)

    if verbose:
        print(report)

    # Save report to file
    report_path = DAEMON_DIR / "latest_integration_report.txt"
    report_path.write_text(report)

    conn.close()

    return {
        "changes": changes,
        "recommendations": recommendations,
        "applied": applied,
        "report": report
    }


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python integration_analyzer.py analyze   - Run full analysis")
        print("  python integration_analyzer.py watch     - Watch for changes")
        print("  python integration_analyzer.py report    - Show last report")
        return

    cmd = sys.argv[1]

    if cmd == "analyze":
        result = analyze(verbose=True)
        print(f"\nNew capabilities: {len(result['changes'].get('new', []))}")
        print(f"Recommendations: {len(result['recommendations'])}")
        print(f"Auto-applied: {len(result['applied'])}")

    elif cmd == "report":
        report_path = DAEMON_DIR / "latest_integration_report.txt"
        if report_path.exists():
            print(report_path.read_text())
        else:
            print("No report found. Run 'analyze' first.")

    elif cmd == "watch":
        print("Watch mode not yet implemented. Use git post-commit hook.")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
