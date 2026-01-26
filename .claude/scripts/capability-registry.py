#!/usr/bin/env python3
"""
Capability Registry Generator

Scans agents, skills, hooks, and rules to build a canonical registry for routing.
Outputs:
  - .claude/config/capabilities.json (machine readable)
  - .claude/config/capabilities.md (human readable)
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional


ROOT = Path(".claude")
OUTPUT_JSON = ROOT / "config" / "capabilities.json"
OUTPUT_MD = ROOT / "config" / "capabilities.md"

SKIP_DIRS = {
    "node_modules",
    "dist",
    "tsc-cache",
    "__pycache__",
    ".git",
}

HOOK_EXTENSIONS = {".py", ".sh", ".mjs", ".js", ".ts"}


def is_skipped(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def read_first_meaningful_line(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                return stripped
    except FileNotFoundError:
        return ""
    return ""


def clean_description(text: str) -> str:
    if not text:
        return ""
    cleaned = text.strip()
    for prefix in ("# ", "## ", "### ", "//", "/*", "* "):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
    if cleaned.endswith("*/"):
        cleaned = cleaned[:-2].strip()
    return cleaned


def extract_md_summary(path: Path) -> str:
    lines: List[str] = []
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped:
                    lines.append(stripped)
                if len(lines) >= 3:
                    break
    except FileNotFoundError:
        return ""

    if not lines:
        return ""

    if lines[0].startswith("#"):
        if len(lines) > 1:
            return clean_description(lines[1])
        return clean_description(lines[0])
    return clean_description(lines[0])


def collect_agent_entries() -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    seen_names = set()
    agents_dir = ROOT / "agents"
    if not agents_dir.exists():
        return entries

    for path in sorted(agents_dir.iterdir()):
        if path.is_dir():
            continue
        if path.suffix == ".json":
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {}
            name = payload.get("name", path.stem)
            description = payload.get("description", "").strip()
            model = payload.get("model", "")
            entries.append({
                "type": "agent",
                "name": name,
                "path": str(path),
                "description": description,
                "model": model,
            })
            seen_names.add(name)
        elif path.suffix == ".md":
            if path.stem in seen_names:
                continue
            description = extract_md_summary(path)
            entries.append({
                "type": "agent",
                "name": path.stem,
                "path": str(path),
                "description": description,
                "model": "",
            })
            seen_names.add(path.stem)

    return entries


def collect_skill_entries() -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    skills_dir = ROOT / "skills"
    if not skills_dir.exists():
        return entries

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        description = extract_md_summary(skill_file)
        entries.append({
            "type": "skill",
            "name": skill_dir.name,
            "path": str(skill_file),
            "description": description,
        })

    return entries


def collect_hook_entries() -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    hooks_dir = ROOT / "hooks"
    if not hooks_dir.exists():
        return entries

    for path in hooks_dir.rglob("*"):
        if not path.is_file():
            continue
        if is_skipped(path):
            continue
        if path.suffix not in HOOK_EXTENSIONS:
            continue
        description = clean_description(read_first_meaningful_line(path))
        entries.append({
            "type": "hook",
            "name": path.stem,
            "path": str(path),
            "description": description,
        })

    return entries


def collect_rule_entries() -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    rules_dir = ROOT / "rules"
    if not rules_dir.exists():
        return entries

    for path in sorted(rules_dir.glob("*")):
        if not path.is_file():
            continue
        description = extract_md_summary(path)
        entries.append({
            "type": "rule",
            "name": path.stem,
            "path": str(path),
            "description": description,
        })

    return entries


def render_markdown(entries: Iterable[Dict[str, str]]) -> str:
    grouped: Dict[str, List[Dict[str, str]]] = {}
    for entry in entries:
        grouped.setdefault(entry["type"], []).append(entry)

    generated_at = datetime.now(timezone.utc).isoformat()
    lines = ["# Capability Registry", "", f"Generated: {generated_at}", ""]
    for category in ("agent", "skill", "hook", "rule"):
        items = grouped.get(category, [])
        if not items:
            continue
        lines.append(f"## {category.title()}s")
        lines.append("")
        header = "| Name | Path | Description |"
        separator = "| --- | --- | --- |"
        lines.extend([header, separator])
        for item in sorted(items, key=lambda x: x["name"]):
            name = item["name"]
            path = item["path"]
            description = item.get("description", "")
            lines.append(f"| {name} | `{path}` | {description} |")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    entries: List[Dict[str, str]] = []
    entries.extend(collect_agent_entries())
    entries.extend(collect_skill_entries())
    entries.extend(collect_hook_entries())
    entries.extend(collect_rule_entries())

    registry = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "agents": len([e for e in entries if e["type"] == "agent"]),
            "skills": len([e for e in entries if e["type"] == "skill"]),
            "hooks": len([e for e in entries if e["type"] == "hook"]),
            "rules": len([e for e in entries if e["type"] == "rule"]),
        },
        "entries": entries,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(entries), encoding="utf-8")

    print(f"Wrote {OUTPUT_JSON}")
    print(f"Wrote {OUTPUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
