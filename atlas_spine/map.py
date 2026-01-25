"""
Atlas MAP - Structured Knowledge Representation

Builds and queries a machine-readable index of:
- Files with tags and descriptions
- Capabilities (what the system can do)
- Domains (knowledge areas)

Output: .atlas/map.json
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import re

class AtlasMap:
    """Structured knowledge map of the repository."""

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.atlas_dir = self.repo_path / '.atlas'
        self.atlas_dir.mkdir(exist_ok=True)
        self.map_path = self.atlas_dir / 'map.json'
        self._map = self._load_map()

    def _load_map(self) -> Dict:
        """Load existing map or create empty."""
        if self.map_path.exists():
            try:
                return json.loads(self.map_path.read_text())
            except json.JSONDecodeError:
                pass
        return {'files': {}, 'capabilities': {}, 'domains': {}, 'built_at': None}

    def _save_map(self):
        """Save map to disk."""
        self._map['built_at'] = datetime.now().isoformat()
        self.map_path.write_text(json.dumps(self._map, indent=2))

    def _infer_tags(self, path: str, content: str = '') -> List[str]:
        """Infer tags from path and content."""
        tags = []
        path_lower = path.lower()

        # Path-based tags
        if 'daemon/' in path_lower:
            tags.append('daemon')
        if 'hook' in path_lower:
            tags.append('hooks')
        if 'skill' in path_lower:
            tags.append('skills')
        if 'agent' in path_lower:
            tags.append('agents')
        if 'test' in path_lower:
            tags.append('tests')
        if 'spec' in path_lower or 'specs/' in path_lower:
            tags.append('specs')
        if '.claude/' in path_lower:
            tags.append('claude-config')

        # Extension-based
        ext = Path(path).suffix.lower()
        ext_tags = {
            '.py': 'python',
            '.ts': 'typescript',
            '.js': 'javascript',
            '.md': 'docs',
            '.yaml': 'config',
            '.yml': 'config',
            '.json': 'config',
            '.sql': 'database',
            '.sh': 'shell',
            '.ps1': 'powershell',
        }
        if ext in ext_tags:
            tags.append(ext_tags[ext])

        # Content-based inference
        if content:
            if 'class ' in content or 'def ' in content:
                tags.append('code')
            if 'import sqlite3' in content or 'sqlite' in content.lower():
                tags.append('sqlite')
            if 'async def' in content or 'await ' in content:
                tags.append('async')
            if 'docker' in content.lower():
                tags.append('docker')
            if 'api' in content.lower():
                tags.append('api')

        return list(set(tags))

    def _infer_description(self, path: str, content: str = '') -> str:
        """Infer description from file content."""
        # Try to extract docstring or first comment
        if content:
            # Python docstring
            match = re.search(r'^"""(.+?)"""', content, re.DOTALL)
            if match:
                desc = match.group(1).strip().split('\n')[0]
                return desc[:100]

            # Comment header
            match = re.search(r'^#\s*(.+)$', content, re.MULTILINE)
            if match:
                return match.group(1).strip()[:100]

            # TypeScript/JS comment
            match = re.search(r'^//\s*(.+)$', content, re.MULTILINE)
            if match:
                return match.group(1).strip()[:100]

            # Block comment
            match = re.search(r'/\*\*?\s*\n?\s*\*?\s*(.+?)[\n\*]', content)
            if match:
                return match.group(1).strip()[:100]

        # Fallback: infer from path
        name = Path(path).stem.replace('_', ' ').replace('-', ' ').title()
        return name

    def build(self, verbose: bool = False) -> Dict:
        """Build the map by scanning repository."""
        files_indexed = 0
        capabilities = {}
        domains = set()

        # Get all files (respecting .gitignore)
        try:
            result = subprocess.run(
                ['git', 'ls-files'],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            file_list = result.stdout.strip().split('\n') if result.stdout else []
        except:
            file_list = [str(p.relative_to(self.repo_path))
                        for p in self.repo_path.rglob('*')
                        if p.is_file() and '.git' not in str(p)]

        self._map['files'] = {}

        for file_path in file_list:
            if not file_path:
                continue

            full_path = self.repo_path / file_path
            if not full_path.exists() or full_path.stat().st_size > 500000:
                continue

            try:
                content = full_path.read_text(errors='ignore')[:5000]
            except:
                content = ''

            tags = self._infer_tags(file_path, content)
            desc = self._infer_description(file_path, content)

            self._map['files'][file_path] = {
                'tags': tags,
                'description': desc,
                'size': full_path.stat().st_size
            }
            files_indexed += 1

            # Track domains
            domains.update(tags)

            # Track capabilities
            if 'daemon/' in file_path:
                cap_name = Path(file_path).stem
                capabilities[cap_name] = {
                    'file': file_path,
                    'type': 'daemon',
                    'description': desc
                }

            if verbose:
                print(f"  {file_path}: {tags}")

        self._map['capabilities'] = capabilities
        self._map['domains'] = list(domains)
        self._save_map()

        return {
            'files_indexed': files_indexed,
            'capabilities': len(capabilities),
            'domains': len(domains),
            'map_path': str(self.map_path)
        }

    def query(self, search: str) -> List[Dict]:
        """Query the map for files matching search."""
        results = []
        search_lower = search.lower()
        terms = search_lower.split()

        for path, info in self._map.get('files', {}).items():
            score = 0

            # Path match
            if search_lower in path.lower():
                score += 10

            # Tag match
            for term in terms:
                if term in info.get('tags', []):
                    score += 5

            # Description match
            if search_lower in info.get('description', '').lower():
                score += 3

            if score > 0:
                results.append({
                    'path': path,
                    'tags': info.get('tags', []),
                    'description': info.get('description', ''),
                    'score': score
                })

        return sorted(results, key=lambda x: -x['score'])[:20]

    def get_capability(self, name: str) -> Optional[Dict]:
        """Get capability by name."""
        return self._map.get('capabilities', {}).get(name)

    def list_capabilities(self) -> List[str]:
        """List all capabilities."""
        return list(self._map.get('capabilities', {}).keys())

    def list_domains(self) -> List[str]:
        """List all domains/tags."""
        return self._map.get('domains', [])

    def get_files_by_tag(self, tag: str) -> List[str]:
        """Get files with a specific tag."""
        return [
            path for path, info in self._map.get('files', {}).items()
            if tag in info.get('tags', [])
        ]

    def stats(self) -> Dict:
        """Get map statistics."""
        files = self._map.get('files', {})
        tags_count = {}
        for info in files.values():
            for tag in info.get('tags', []):
                tags_count[tag] = tags_count.get(tag, 0) + 1

        return {
            'total_files': len(files),
            'capabilities': len(self._map.get('capabilities', {})),
            'domains': len(self._map.get('domains', [])),
            'top_tags': sorted(tags_count.items(), key=lambda x: -x[1])[:10],
            'built_at': self._map.get('built_at')
        }


def main():
    """CLI for map operations."""
    import argparse
    parser = argparse.ArgumentParser(description='Atlas MAP')
    parser.add_argument('command', choices=['build', 'query', 'stats', 'capabilities'])
    parser.add_argument('args', nargs='*')
    parser.add_argument('--repo', type=str, help='Repository path')
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()
    atlas_map = AtlasMap(Path(args.repo) if args.repo else None)

    if args.command == 'build':
        result = atlas_map.build(verbose=args.verbose)
        print(json.dumps(result, indent=2))
    elif args.command == 'query':
        search = ' '.join(args.args) if args.args else ''
        results = atlas_map.query(search)
        print(json.dumps(results, indent=2))
    elif args.command == 'stats':
        print(json.dumps(atlas_map.stats(), indent=2))
    elif args.command == 'capabilities':
        print(json.dumps(atlas_map.list_capabilities(), indent=2))


if __name__ == '__main__':
    main()
