"""
SymbolExplorer - Navigate code structure deterministically
"""

import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import json

class SymbolExplorer:
    """Explore repository structure and symbols."""

    def __init__(self, repo_path: Path, indexer=None):
        self.repo_path = Path(repo_path)
        self.indexer = indexer

    def get_structure(self, max_depth: int = 3) -> Dict:
        """Get directory structure."""
        def build_tree(path: Path, depth: int) -> Dict:
            if depth > max_depth or not path.is_dir():
                return {}

            result = {'type': 'dir', 'children': {}}
            try:
                for item in sorted(path.iterdir()):
                    if item.name.startswith('.') and item.name not in ['.claude']:
                        continue
                    if item.is_dir():
                        result['children'][item.name] = build_tree(item, depth + 1)
                    else:
                        result['children'][item.name] = {
                            'type': 'file',
                            'size': item.stat().st_size
                        }
            except PermissionError:
                pass
            return result

        return build_tree(self.repo_path, 0)

    def find_symbol(self, name: str, kind: Optional[str] = None) -> List[Dict]:
        """Find symbol definitions."""
        if self.indexer:
            return self.indexer.find_symbol(name, kind)

        # Fallback: use ripgrep
        patterns = {
            'function': f'(def|function|fn|func)\\s+{name}',
            'class': f'(class|struct|type)\\s+{name}',
            'variable': f'(const|let|var|val)\\s+{name}',
        }

        if kind and kind in patterns:
            pattern = patterns[kind]
        else:
            pattern = f'(def|function|class|struct)\\s+{name}'

        try:
            result = subprocess.run(
                ['rg', '--json', '-e', pattern],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )

            matches = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get('type') == 'match':
                        match_data = data.get('data', {})
                        matches.append({
                            'file': match_data.get('path', {}).get('text', ''),
                            'line': match_data.get('line_number', 0),
                            'text': match_data.get('lines', {}).get('text', '').strip()
                        })
                except json.JSONDecodeError:
                    continue
            return matches
        except FileNotFoundError:
            return [{'error': 'ripgrep not available'}]

    def get_file_outline(self, file_path: str) -> List[Dict]:
        """Get outline of a specific file."""
        full_path = self.repo_path / file_path
        if not full_path.exists():
            return [{'error': f'File not found: {file_path}'}]

        try:
            result = subprocess.run(
                ['ctags', '-f', '-', '--output-format=json', '--fields=+nKS', str(full_path)],
                capture_output=True,
                text=True
            )

            outline = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    tag = json.loads(line)
                    outline.append({
                        'name': tag.get('name', ''),
                        'kind': tag.get('kind', ''),
                        'line': tag.get('line', 0),
                        'scope': tag.get('scope', ''),
                        'signature': tag.get('signature', '')
                    })
                except json.JSONDecodeError:
                    continue
            return sorted(outline, key=lambda x: x.get('line', 0))
        except FileNotFoundError:
            return [{'error': 'ctags not available'}]

    def find_references(self, symbol: str, file_glob: str = '*') -> List[Dict]:
        """Find all references to a symbol."""
        try:
            result = subprocess.run(
                ['rg', '--json', '-w', '-g', file_glob, symbol],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )

            refs = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get('type') == 'match':
                        match_data = data.get('data', {})
                        refs.append({
                            'file': match_data.get('path', {}).get('text', ''),
                            'line': match_data.get('line_number', 0),
                            'text': match_data.get('lines', {}).get('text', '').strip()
                        })
                except json.JSONDecodeError:
                    continue
            return refs
        except FileNotFoundError:
            return [{'error': 'ripgrep not available'}]

    def get_imports(self, file_path: str) -> List[str]:
        """Extract imports from a file."""
        full_path = self.repo_path / file_path
        if not full_path.exists():
            return []

        content = full_path.read_text(errors='ignore')
        imports = []

        # Python imports
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                imports.append(line)
            elif line.startswith('const ') and ' require(' in line:
                imports.append(line)
            elif line.startswith('import ') or ('import ' in line and 'from ' in line):
                imports.append(line)

        return imports[:50]  # Limit to first 50
