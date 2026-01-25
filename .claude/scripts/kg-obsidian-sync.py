#!/usr/bin/env python3
"""
Knowledge Graph to Obsidian Sync

Exports knowledge graph entities as Obsidian-compatible markdown files.
Each entity becomes a note with:
- Frontmatter (metadata)
- Observations as bullet points
- Relations as [[wikilinks]]

This creates a "second brain" structure mirroring neural clusters.

Usage:
    python kg-obsidian-sync.py                    # One-time export
    python kg-obsidian-sync.py --watch            # Continuous sync
    python kg-obsidian-sync.py --vault /path      # Custom vault path
    python kg-obsidian-sync.py --dry-run          # Preview changes
"""

import json
import os
import re
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field


# Default paths
DEFAULT_KG_PATH = Path.home() / ".claude" / "memory" / "knowledge-graph.jsonl"
DEFAULT_VAULT_PATH = Path.home() / "Documents" / "Obsidian" / "ClaudeKnowledge"


@dataclass
class KGEntity:
    """Represents an entity from the knowledge graph."""
    name: str
    entity_type: str
    observations: List[str] = field(default_factory=list)
    source: str = ""
    path: str = ""
    timestamp: str = ""


@dataclass
class KGRelation:
    """Represents a relation between entities."""
    from_entity: str
    to_entity: str
    relation_type: str


def sanitize_filename(name: str) -> str:
    """Convert entity name to valid filename."""
    # Remove invalid characters
    clean = re.sub(r'[<>:"/\\|?*]', '', name)
    # Replace spaces with underscores
    clean = clean.replace(' ', '_')
    # Limit length
    if len(clean) > 100:
        clean = clean[:97] + "..."
    return clean


def parse_observation(obs: str) -> Dict[str, str]:
    """Parse an observation string into key-value pairs."""
    result = {}

    # Try KEY:VALUE format
    if ':' in obs:
        parts = obs.split(':', 1)
        if len(parts) == 2 and len(parts[0]) < 30:  # Likely a key
            result[parts[0].strip().lower()] = parts[1].strip()
            return result

    # Otherwise treat as content
    result['content'] = obs
    return result


def load_knowledge_graph(kg_path: Path) -> Tuple[List[KGEntity], List[KGRelation]]:
    """Load entities and relations from knowledge graph JSONL."""
    entities = []
    relations = []

    if not kg_path.exists():
        print(f"  Warning: KG file not found: {kg_path}")
        return entities, relations

    with open(kg_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Skip plain text lines
            if not line.startswith('{'):
                continue

            try:
                data = json.loads(line)

                # Check if it's an entity
                if data.get('type') == 'entity' or 'entityType' in data:
                    entity = KGEntity(
                        name=data.get('name', 'unknown'),
                        entity_type=data.get('entityType', data.get('type', 'unknown')),
                        observations=data.get('observations', []),
                        source=data.get('source', ''),
                        path=data.get('path', ''),
                        timestamp=data.get('timestamp', ''),
                    )
                    entities.append(entity)

                # Check if it's a relation
                elif data.get('type') == 'relation' or 'relationType' in data:
                    relation = KGRelation(
                        from_entity=data.get('from', data.get('from_entity', '')),
                        to_entity=data.get('to', data.get('to_entity', '')),
                        relation_type=data.get('relationType', data.get('relation', '')),
                    )
                    relations.append(relation)

            except json.JSONDecodeError:
                continue

    return entities, relations


def generate_markdown(
    entity: KGEntity,
    relations: List[KGRelation],
    all_entities: Set[str]
) -> str:
    """Generate Obsidian-compatible markdown for an entity."""
    lines = []

    # Frontmatter
    lines.append("---")
    lines.append(f"type: {entity.entity_type}")
    if entity.source:
        lines.append(f"source: {entity.source}")
    if entity.timestamp:
        lines.append(f"created: {entity.timestamp}")
    lines.append(f"synced: {datetime.now().isoformat()}")
    lines.append("tags:")
    lines.append(f"  - kg/{entity.entity_type.replace(' ', '_')}")
    lines.append("---")
    lines.append("")

    # Title
    display_name = entity.name.replace('_', ' ').replace('book:', '').replace('file:', '')
    lines.append(f"# {display_name}")
    lines.append("")

    # Parse observations into categories
    summary = None
    title = None
    keywords = []
    concepts = []
    other_obs = []

    for obs in entity.observations:
        parsed = parse_observation(obs)

        if 'summary' in parsed:
            summary = parsed['summary']
        elif 'title' in parsed:
            title = parsed['title']
        elif 'keywords' in parsed:
            keywords = [k.strip() for k in parsed['keywords'].split(',')]
        elif 'key_concepts' in parsed:
            concepts = [c.strip() for c in parsed['key_concepts'].split(',')]
        elif 'content' in parsed:
            other_obs.append(parsed['content'])
        else:
            # Generic key-value
            for k, v in parsed.items():
                other_obs.append(f"**{k.title()}**: {v}")

    # Summary section
    if summary:
        lines.append("## Summary")
        lines.append(summary)
        lines.append("")

    # Title if different from name
    if title and title != display_name:
        lines.append(f"> **Full Title**: {title}")
        lines.append("")

    # Key Concepts as wikilinks
    if concepts:
        lines.append("## Key Concepts")
        concept_links = []
        for concept in concepts:
            clean_concept = concept.strip()
            if clean_concept:
                # Create wikilink to concept
                concept_links.append(f"[[{sanitize_filename(clean_concept)}|{clean_concept}]]")
        lines.append(" | ".join(concept_links))
        lines.append("")

    # Keywords as tags
    if keywords:
        lines.append("## Keywords")
        tag_line = " ".join([f"#{k.strip().replace(' ', '_').replace('.', '_')}" for k in keywords if k.strip()])
        lines.append(tag_line)
        lines.append("")

    # Other observations
    if other_obs:
        lines.append("## Observations")
        for obs in other_obs:
            lines.append(f"- {obs}")
        lines.append("")

    # Relations (outgoing)
    outgoing = [r for r in relations if r.from_entity == entity.name]
    if outgoing:
        lines.append("## Relations")
        for rel in outgoing:
            target = sanitize_filename(rel.to_entity)
            display_target = rel.to_entity.replace('_', ' ')
            lines.append(f"- **{rel.relation_type}**: [[{target}|{display_target}]]")
        lines.append("")

    # Incoming relations (backlinks)
    incoming = [r for r in relations if r.to_entity == entity.name]
    if incoming:
        lines.append("## Referenced By")
        for rel in incoming:
            source = sanitize_filename(rel.from_entity)
            display_source = rel.from_entity.replace('_', ' ')
            lines.append(f"- [[{source}|{display_source}]] ({rel.relation_type})")
        lines.append("")

    # Source path
    if entity.path:
        lines.append("## Source")
        lines.append(f"```")
        lines.append(entity.path)
        lines.append(f"```")
        lines.append("")

    return "\n".join(lines)


def sync_to_obsidian(
    kg_path: Path,
    vault_path: Path,
    dry_run: bool = False
) -> Tuple[int, int, int]:
    """
    Sync knowledge graph to Obsidian vault.

    Returns: (created, updated, unchanged) counts
    """
    # Load KG
    print(f"  Loading KG from: {kg_path}")
    entities, relations = load_knowledge_graph(kg_path)

    if not entities:
        print("  No entities found in knowledge graph.")
        return 0, 0, 0

    print(f"  Found {len(entities)} entities, {len(relations)} relations")

    # Create vault directory structure
    if not dry_run:
        vault_path.mkdir(parents=True, exist_ok=True)

        # Create type-based folders
        types_seen = set(e.entity_type for e in entities)
        for entity_type in types_seen:
            folder = vault_path / sanitize_filename(entity_type)
            folder.mkdir(exist_ok=True)

    # Track all entity names for wikilink validation
    all_entity_names = set(e.name for e in entities)

    created = 0
    updated = 0
    unchanged = 0

    for entity in entities:
        # Determine file path
        type_folder = sanitize_filename(entity.entity_type)
        filename = sanitize_filename(entity.name) + ".md"
        file_path = vault_path / type_folder / filename

        # Generate markdown
        markdown = generate_markdown(entity, relations, all_entity_names)

        if dry_run:
            print(f"  [DRY RUN] Would create/update: {file_path}")
            created += 1
            continue

        # Check if file exists and has changed
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                existing = f.read()

            # Compare content (ignore synced timestamp)
            existing_lines = [l for l in existing.split('\n') if not l.startswith('synced:')]
            new_lines = [l for l in markdown.split('\n') if not l.startswith('synced:')]

            if existing_lines == new_lines:
                unchanged += 1
                continue
            else:
                updated += 1
        else:
            created += 1

        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(markdown)

    # Create index file
    if not dry_run:
        create_index(vault_path, entities, relations)

    return created, updated, unchanged


def create_index(vault_path: Path, entities: List[KGEntity], relations: List[KGRelation]):
    """Create an index/MOC (Map of Content) file."""
    lines = []

    lines.append("---")
    lines.append("type: index")
    lines.append(f"synced: {datetime.now().isoformat()}")
    lines.append("---")
    lines.append("")
    lines.append("# Knowledge Graph Index")
    lines.append("")
    lines.append(f"**Total Entities**: {len(entities)}")
    lines.append(f"**Total Relations**: {len(relations)}")
    lines.append(f"**Last Sync**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    # Group by type
    by_type: Dict[str, List[KGEntity]] = {}
    for entity in entities:
        t = entity.entity_type
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(entity)

    lines.append("## By Type")
    lines.append("")

    for entity_type, type_entities in sorted(by_type.items()):
        lines.append(f"### {entity_type.replace('_', ' ').title()}")
        lines.append("")

        for entity in sorted(type_entities, key=lambda e: e.name):
            filename = sanitize_filename(entity.name)
            display = entity.name.replace('_', ' ').replace('book:', '').replace('file:', '')
            type_folder = sanitize_filename(entity_type)
            lines.append(f"- [[{type_folder}/{filename}|{display[:50]}]]")

        lines.append("")

    # Recent additions
    timestamped = [e for e in entities if e.timestamp]
    if timestamped:
        timestamped.sort(key=lambda e: e.timestamp, reverse=True)

        lines.append("## Recent Additions")
        lines.append("")

        for entity in timestamped[:10]:
            filename = sanitize_filename(entity.name)
            display = entity.name.replace('_', ' ')[:40]
            type_folder = sanitize_filename(entity.entity_type)
            ts = entity.timestamp[:10] if entity.timestamp else ""
            lines.append(f"- {ts} [[{type_folder}/{filename}|{display}]]")

        lines.append("")

    index_path = vault_path / "_Knowledge_Graph_Index.md"
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))


def watch_mode(kg_path: Path, vault_path: Path, interval: int = 60):
    """Continuously sync KG to Obsidian."""
    print(f"\n  CONTINUOUS KG-OBSIDIAN SYNC")
    print(f"  {'='*40}")
    print(f"  KG: {kg_path}")
    print(f"  Vault: {vault_path}")
    print(f"  Interval: {interval}s")
    print(f"  Press Ctrl+C to stop\n")

    last_mtime = 0

    try:
        while True:
            # Check if KG file changed
            if kg_path.exists():
                mtime = kg_path.stat().st_mtime

                if mtime > last_mtime:
                    print(f"  [{datetime.now().strftime('%H:%M:%S')}] Syncing...")
                    created, updated, unchanged = sync_to_obsidian(kg_path, vault_path)
                    print(f"    Created: {created}, Updated: {updated}, Unchanged: {unchanged}")
                    last_mtime = mtime

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n  Sync stopped.\n")


def main():
    parser = argparse.ArgumentParser(description="KG to Obsidian Sync")
    parser.add_argument("--kg", type=str, help="Knowledge graph JSONL path")
    parser.add_argument("--vault", type=str, help="Obsidian vault path")
    parser.add_argument("--watch", action="store_true", help="Continuous sync mode")
    parser.add_argument("--interval", type=int, default=60, help="Sync interval in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")

    args = parser.parse_args()

    kg_path = Path(args.kg) if args.kg else DEFAULT_KG_PATH
    vault_path = Path(args.vault) if args.vault else DEFAULT_VAULT_PATH

    print(f"\n  KG-OBSIDIAN SYNC")
    print(f"  {'='*40}")

    if args.watch:
        watch_mode(kg_path, vault_path, args.interval)
    else:
        created, updated, unchanged = sync_to_obsidian(kg_path, vault_path, args.dry_run)

        print(f"\n  Results:")
        print(f"    Created: {created}")
        print(f"    Updated: {updated}")
        print(f"    Unchanged: {unchanged}")
        print(f"\n  Vault: {vault_path}")
        print()


if __name__ == "__main__":
    main()
