#!/usr/bin/env python3
"""
Capability Registry Generator

Scans .claude/agents, skills, hooks, rules and generates:
- .claude/config/capabilities.json (machine-readable)
- .claude/config/capabilities.md (human-readable)

This is the single source of truth for deterministic routing.
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
CLAUDE_DIR = PROJECT_ROOT / ".claude"

@dataclass
class Capability:
    """A registered capability (agent, skill, hook, or rule)."""
    name: str
    type: str  # agent, skill, hook, rule
    path: str
    description: str = ""
    domain: str = "general"  # e.g., research, code, planning, memory
    triggers: list = None  # keywords/patterns that trigger this
    model_tier: str = "claude"  # localai, codex, claude
    risk_level: str = "low"  # low, medium, high

    def __post_init__(self):
        if self.triggers is None:
            self.triggers = []


def extract_description_from_md(filepath: Path) -> str:
    """Extract first meaningful paragraph from markdown file."""
    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
        # Skip YAML frontmatter
        if content.startswith('---'):
            end = content.find('---', 3)
            if end > 0:
                content = content[end+3:]

        # Find first paragraph after headers
        lines = content.strip().split('\n')
        desc_lines = []
        in_desc = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if in_desc:
                    break
                continue
            if stripped.startswith('#'):
                in_desc = True
                continue
            if in_desc and not stripped.startswith(('-', '*', '|', '`', '>')):
                desc_lines.append(stripped)
                if len(' '.join(desc_lines)) > 150:
                    break

        return ' '.join(desc_lines)[:200] if desc_lines else ""
    except Exception:
        return ""


def extract_triggers_from_md(filepath: Path) -> list:
    """Extract trigger keywords from file."""
    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore').lower()
        triggers = []

        # Look for common trigger patterns
        trigger_patterns = [
            r'use\s+(?:this|when|for)\s+([^.]+)',
            r'triggers?:\s*([^\n]+)',
            r'keywords?:\s*([^\n]+)',
        ]

        for pattern in trigger_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                words = re.findall(r'\b\w+\b', match)
                triggers.extend([w for w in words if len(w) > 3])

        return list(set(triggers))[:10]
    except Exception:
        return []


def infer_domain(name: str, description: str) -> str:
    """Infer domain from name and description."""
    text = (name + ' ' + description).lower()

    domains = {
        'research': ['research', 'oracle', 'search', 'web', 'fetch', 'explore'],
        'code': ['code', 'kraken', 'build', 'test', 'debug', 'implement', 'fix'],
        'planning': ['architect', 'plan', 'design', 'strategy', 'decision'],
        'memory': ['memory', 'recall', 'handoff', 'continuity', 'ledger'],
        'analysis': ['analyze', 'critic', 'review', 'validate', 'judge'],
        'documentation': ['doc', 'scribe', 'chronicle', 'write', 'document'],
        'security': ['security', 'aegis', 'sentinel', 'warden', 'guard'],
    }

    for domain, keywords in domains.items():
        if any(kw in text for kw in keywords):
            return domain

    return 'general'


def infer_model_tier(name: str, domain: str) -> str:
    """Infer appropriate model tier."""
    # LocalAI for bulk/simple tasks
    localai_patterns = ['embed', 'summarize', 'classify', 'chunk', 'extract']
    if any(p in name.lower() for p in localai_patterns):
        return 'localai'

    # Codex for code tasks
    if domain == 'code':
        return 'codex'

    # Claude for complex reasoning
    return 'claude'


def scan_agents() -> list:
    """Scan .claude/agents/ for agent definitions."""
    capabilities = []
    agents_dir = CLAUDE_DIR / "agents"

    if not agents_dir.exists():
        return capabilities

    for filepath in agents_dir.glob("*.md"):
        name = filepath.stem
        desc = extract_description_from_md(filepath)
        triggers = extract_triggers_from_md(filepath)
        domain = infer_domain(name, desc)

        cap = Capability(
            name=name,
            type="agent",
            path=str(filepath.relative_to(PROJECT_ROOT)),
            description=desc,
            domain=domain,
            triggers=triggers,
            model_tier=infer_model_tier(name, domain),
            risk_level="medium" if domain in ['code', 'security'] else "low"
        )
        capabilities.append(cap)

    return capabilities


def scan_skills() -> list:
    """Scan .claude/skills/ for skill definitions."""
    capabilities = []
    skills_dir = CLAUDE_DIR / "skills"

    if not skills_dir.exists():
        return capabilities

    # Skills can be .md files or directories with SKILL.md
    for item in skills_dir.iterdir():
        if item.name.startswith('_'):
            continue

        if item.is_file() and item.suffix == '.md':
            name = item.stem
            filepath = item
        elif item.is_dir():
            skill_file = item / "SKILL.md"
            if not skill_file.exists():
                # Look for any .md file
                md_files = list(item.glob("*.md"))
                if md_files:
                    skill_file = md_files[0]
                else:
                    continue
            name = item.name
            filepath = skill_file
        else:
            continue

        desc = extract_description_from_md(filepath)
        triggers = extract_triggers_from_md(filepath)
        domain = infer_domain(name, desc)

        cap = Capability(
            name=name,
            type="skill",
            path=str(filepath.relative_to(PROJECT_ROOT)),
            description=desc,
            domain=domain,
            triggers=triggers,
            model_tier=infer_model_tier(name, domain),
            risk_level="low"
        )
        capabilities.append(cap)

    return capabilities


def scan_rules() -> list:
    """Scan .claude/rules/ for behavioral rules."""
    capabilities = []
    rules_dir = CLAUDE_DIR / "rules"

    if not rules_dir.exists():
        return capabilities

    for filepath in rules_dir.glob("*.md"):
        name = filepath.stem
        desc = extract_description_from_md(filepath)

        cap = Capability(
            name=name,
            type="rule",
            path=str(filepath.relative_to(PROJECT_ROOT)),
            description=desc,
            domain="behavior",
            triggers=[],
            model_tier="n/a",
            risk_level="low"
        )
        capabilities.append(cap)

    return capabilities


def scan_hooks() -> list:
    """Scan .claude/hooks/ for lifecycle hooks."""
    capabilities = []
    hooks_dir = CLAUDE_DIR / "hooks"

    if not hooks_dir.exists():
        return capabilities

    for filepath in hooks_dir.glob("*.py"):
        name = filepath.stem

        # Try to extract description from docstring
        try:
            content = filepath.read_text(encoding='utf-8', errors='ignore')
            docstring_match = re.search(r'"""([^"]+)"""', content)
            desc = docstring_match.group(1).strip()[:200] if docstring_match else ""
        except Exception:
            desc = ""

        cap = Capability(
            name=name,
            type="hook",
            path=str(filepath.relative_to(PROJECT_ROOT)),
            description=desc,
            domain="lifecycle",
            triggers=[],
            model_tier="n/a",
            risk_level="low"
        )
        capabilities.append(cap)

    return capabilities


def generate_registry():
    """Generate the complete capability registry."""
    print("Scanning capabilities...")

    agents = scan_agents()
    print(f"  Found {len(agents)} agents")

    skills = scan_skills()
    print(f"  Found {len(skills)} skills")

    rules = scan_rules()
    print(f"  Found {len(rules)} rules")

    hooks = scan_hooks()
    print(f"  Found {len(hooks)} hooks")

    all_capabilities = agents + skills + rules + hooks

    # Create config directory
    config_dir = CLAUDE_DIR / "config"
    config_dir.mkdir(exist_ok=True)

    # Generate JSON
    registry = {
        "generated": datetime.now().isoformat(),
        "total": len(all_capabilities),
        "counts": {
            "agents": len(agents),
            "skills": len(skills),
            "rules": len(rules),
            "hooks": len(hooks)
        },
        "capabilities": [asdict(c) for c in all_capabilities]
    }

    json_path = config_dir / "capabilities.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(registry, f, indent=2)
    print(f"\nGenerated: {json_path}")

    # Generate Markdown
    md_path = config_dir / "capabilities.md"
    generate_markdown(all_capabilities, md_path)
    print(f"Generated: {md_path}")

    # Generate routing index (for fast lookup)
    routing_index = generate_routing_index(all_capabilities)
    routing_path = config_dir / "routing_index.json"
    with open(routing_path, 'w', encoding='utf-8') as f:
        json.dump(routing_index, f, indent=2)
    print(f"Generated: {routing_path}")

    return registry


def generate_markdown(capabilities: list, output_path: Path):
    """Generate human-readable markdown."""
    lines = [
        "# Capability Registry",
        "",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "## Summary",
        "",
        f"| Type | Count |",
        f"|------|-------|",
    ]

    type_counts = {}
    for cap in capabilities:
        type_counts[cap.type] = type_counts.get(cap.type, 0) + 1

    for t, c in sorted(type_counts.items()):
        lines.append(f"| {t} | {c} |")

    lines.extend(["", "---", ""])

    # Group by type
    for cap_type in ['agent', 'skill', 'rule', 'hook']:
        type_caps = [c for c in capabilities if c.type == cap_type]
        if not type_caps:
            continue

        lines.append(f"## {cap_type.title()}s ({len(type_caps)})")
        lines.append("")

        # Table header
        if cap_type in ['agent', 'skill']:
            lines.append("| Name | Domain | Model | Description |")
            lines.append("|------|--------|-------|-------------|")
            for cap in sorted(type_caps, key=lambda x: x.name):
                desc = cap.description[:60] + "..." if len(cap.description) > 60 else cap.description
                lines.append(f"| `{cap.name}` | {cap.domain} | {cap.model_tier} | {desc} |")
        else:
            lines.append("| Name | Description |")
            lines.append("|------|-------------|")
            for cap in sorted(type_caps, key=lambda x: x.name):
                desc = cap.description[:80] + "..." if len(cap.description) > 80 else cap.description
                lines.append(f"| `{cap.name}` | {desc} |")

        lines.append("")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def generate_routing_index(capabilities: list) -> dict:
    """Generate routing index for fast lookup by keyword/domain."""
    index = {
        "by_domain": {},
        "by_type": {},
        "by_keyword": {},
        "by_model_tier": {}
    }

    for cap in capabilities:
        # Index by domain
        if cap.domain not in index["by_domain"]:
            index["by_domain"][cap.domain] = []
        index["by_domain"][cap.domain].append(cap.name)

        # Index by type
        if cap.type not in index["by_type"]:
            index["by_type"][cap.type] = []
        index["by_type"][cap.type].append(cap.name)

        # Index by model tier
        if cap.model_tier not in index["by_model_tier"]:
            index["by_model_tier"][cap.model_tier] = []
        index["by_model_tier"][cap.model_tier].append(cap.name)

        # Index by trigger keywords
        for trigger in cap.triggers:
            if trigger not in index["by_keyword"]:
                index["by_keyword"][trigger] = []
            index["by_keyword"][trigger].append({
                "name": cap.name,
                "type": cap.type
            })

    return index


def lookup(query: str) -> list:
    """Lookup capabilities matching a query."""
    config_dir = CLAUDE_DIR / "config"
    routing_path = config_dir / "routing_index.json"
    caps_path = config_dir / "capabilities.json"

    if not routing_path.exists():
        print("Registry not generated. Run: python capability_registry.py generate")
        return []

    with open(routing_path) as f:
        index = json.load(f)

    with open(caps_path) as f:
        registry = json.load(f)

    query_lower = query.lower()
    matches = []

    # Check keywords
    for keyword, caps in index["by_keyword"].items():
        if keyword in query_lower:
            matches.extend(caps)

    # Check domains
    for domain in index["by_domain"]:
        if domain in query_lower:
            for name in index["by_domain"][domain]:
                matches.append({"name": name, "type": "domain_match"})

    # Deduplicate
    seen = set()
    unique = []
    for m in matches:
        if m["name"] not in seen:
            seen.add(m["name"])
            unique.append(m)

    return unique[:10]


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python capability_registry.py generate  - Generate registry")
        print("  python capability_registry.py lookup <query>  - Find capabilities")
        print("  python capability_registry.py stats  - Show statistics")
        return

    cmd = sys.argv[1]

    if cmd == "generate":
        registry = generate_registry()
        print(f"\nTotal capabilities: {registry['total']}")

    elif cmd == "lookup":
        if len(sys.argv) < 3:
            print("Usage: python capability_registry.py lookup <query>")
            return
        query = ' '.join(sys.argv[2:])
        results = lookup(query)
        if results:
            print(f"Found {len(results)} matches for '{query}':")
            for r in results:
                print(f"  - {r['name']} ({r.get('type', 'match')})")
        else:
            print(f"No matches for '{query}'")

    elif cmd == "stats":
        caps_path = CLAUDE_DIR / "config" / "capabilities.json"
        if not caps_path.exists():
            print("Registry not generated. Run: python capability_registry.py generate")
            return

        with open(caps_path) as f:
            registry = json.load(f)

        print(f"Total: {registry['total']} capabilities")
        for t, c in registry['counts'].items():
            print(f"  {t}: {c}")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
