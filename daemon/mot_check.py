#!/usr/bin/env python3
"""MOT - System Health Check for Atlas"""

import sys
from pathlib import Path
from datetime import datetime
import json
import sqlite3

PROJECT_ROOT = Path(__file__).parent.parent

def check_skills():
    """Audit skills directory."""
    print("=== SKILLS AUDIT ===")
    skills_dir = PROJECT_ROOT / ".claude" / "skills"
    skill_files = list(skills_dir.rglob("SKILL.md"))
    print(f"Found {len(skill_files)} skill files")

    frontmatter_fail = 0
    for skill in skill_files:
        first_line = skill.read_text(encoding='utf-8', errors='ignore').split('\n')[0]
        if not first_line.strip().startswith('---'):
            print(f"FAIL: No frontmatter: {skill.relative_to(PROJECT_ROOT)}")
            frontmatter_fail += 1

    print(f"Frontmatter: {len(skill_files) - frontmatter_fail} pass, {frontmatter_fail} fail")
    return len(skill_files) - frontmatter_fail, frontmatter_fail

def check_agents():
    """Audit agents directory."""
    print("\n=== AGENTS AUDIT ===")
    agents_dir = PROJECT_ROOT / ".claude" / "agents"
    agent_files = list(agents_dir.glob("*.md"))
    print(f"Found {len(agent_files)} agent files")

    agent_fail = 0
    for agent in agent_files:
        content = agent.read_text(encoding='utf-8', errors='ignore')
        if 'name:' not in content:
            print(f"FAIL: Missing name: {agent.name}")
            agent_fail += 1

    print(f"Agent validation: {len(agent_files) - agent_fail} pass, {agent_fail} fail")
    return len(agent_files) - agent_fail, agent_fail

def check_hooks():
    """Audit hooks directory."""
    print("\n=== HOOKS AUDIT ===")
    hooks_dir = PROJECT_ROOT / ".claude" / "hooks"

    ts_files = list((hooks_dir / "src").glob("*.ts")) if (hooks_dir / "src").exists() else []
    mjs_files = list((hooks_dir / "dist").glob("*.mjs")) if (hooks_dir / "dist").exists() else []
    sh_files = list(hooks_dir.glob("*.sh"))
    py_files = list(hooks_dir.glob("*.py"))

    print(f"TypeScript sources: {len(ts_files)}")
    print(f"Built bundles: {len(mjs_files)}")
    print(f"Shell wrappers: {len(sh_files)}")
    print(f"Python hooks: {len(py_files)}")

    return len(ts_files) + len(py_files), 0

def check_databases():
    """Audit daemon databases."""
    print("\n=== DATABASES ===")
    daemon_dir = PROJECT_ROOT / "daemon"
    db_files = list(daemon_dir.glob("*.db"))

    print(f"Found {len(db_files)} SQLite databases")

    total_size = 0
    for db in sorted(db_files):
        size_kb = db.stat().st_size / 1024
        total_size += size_kb
        print(f"  {db.name:30s} {size_kb:>8.1f} KB")

    print(f"Total: {total_size:.1f} KB")

    # Check key databases
    key_dbs = {
        'utf_knowledge.db': ['sources', 'excerpts', 'claims', 'concepts'],
        'outcomes.db': ['outcomes'],
        'strategies.db': ['strategies'],
    }

    for db_name, tables in key_dbs.items():
        db_path = daemon_dir / db_name
        if db_path.exists():
            try:
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                for table in tables:
                    c.execute(f"SELECT COUNT(*) FROM {table}")
                    count = c.fetchone()[0]
                    print(f"  {db_name}:{table} = {count} rows")
                conn.close()
            except Exception as e:
                print(f"  {db_name}: ERROR - {e}")

    return len(db_files), 0

def check_utf_knowledge():
    """Check UTF knowledge database specifically."""
    print("\n=== UTF KNOWLEDGE ===")
    db_path = PROJECT_ROOT / "daemon" / "utf_knowledge.db"

    if not db_path.exists():
        print("WARN: utf_knowledge.db not found")
        return 0, 1

    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM sources")
        sources = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM excerpts")
        excerpts = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM claims")
        claims = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM concepts")
        concepts = c.fetchone()[0]

        print(f"Sources: {sources}")
        print(f"Excerpts: {excerpts}")
        print(f"Claims: {claims}")
        print(f"Concepts: {concepts}")

        conn.close()
        return 4, 0
    except Exception as e:
        print(f"ERROR: {e}")
        return 0, 1

def check_docker():
    """Check Docker containers."""
    print("\n=== DOCKER CONTAINERS ===")
    import subprocess

    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            containers = result.stdout.strip().split('\n')
            print(f"Running: {len(containers)} containers")
            for container in containers:
                if container:
                    print(f"  {container}")
            return len(containers), 0
        else:
            print("Docker not available")
            return 0, 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 0, 1

def generate_report(results):
    """Generate MOT report."""
    timestamp = datetime.now().isoformat()

    report = f"""# MOT Health Report
Generated: {timestamp}

## Summary
| Category | Pass | Fail | Warn |
|----------|------|------|------|
"""

    for category, (pass_count, fail_count) in results.items():
        report += f"| {category:12s} | {pass_count:4d} | {fail_count:4d} | 0    |\n"

    # Write report
    cache_dir = PROJECT_ROOT / ".claude" / "cache" / "mot"
    cache_dir.mkdir(parents=True, exist_ok=True)

    report_file = cache_dir / f"report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    report_file.write_text(report, encoding='utf-8')

    print(f"\n\nReport saved: {report_file.relative_to(PROJECT_ROOT)}")
    return report

def main():
    print("=" * 60)
    print("MOT - System Health Check")
    print("=" * 60)
    print()

    results = {}

    results['Skills'] = check_skills()
    results['Agents'] = check_agents()
    results['Hooks'] = check_hooks()
    results['Databases'] = check_databases()
    results['UTF Knowledge'] = check_utf_knowledge()
    results['Docker'] = check_docker()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    total_pass = sum(p for p, _ in results.values())
    total_fail = sum(f for _, f in results.values())

    print(f"Total Pass: {total_pass}")
    print(f"Total Fail: {total_fail}")

    report = generate_report(results)

    return 1 if total_fail > 0 else 0

if __name__ == "__main__":
    sys.exit(main())
