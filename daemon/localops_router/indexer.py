"""
RepoIndexer - Fast indexing via ripgrep and universal-ctags
"""

import json
import subprocess
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import hashlib

class RepoIndexer:
    """Index repository for fast symbol/file lookup."""

    def __init__(self, repo_path: Path, storage_path: Optional[Path] = None):
        self.repo_path = Path(repo_path)
        self.storage_path = storage_path or (self.repo_path / '.localops' / 'storage')
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.db_path = self.storage_path / 'index.db'
        self.artifacts_path = self.repo_path / '.repo_artifacts'
        self.artifacts_path.mkdir(exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite storage."""
        conn = sqlite3.connect(self.db_path)
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                hash TEXT,
                size INTEGER,
                mtime REAL,
                indexed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS symbols (
                name TEXT,
                kind TEXT,
                file_path TEXT,
                line INTEGER,
                scope TEXT,
                signature TEXT,
                PRIMARY KEY (name, file_path, line)
            );
            CREATE TABLE IF NOT EXISTS search_cache (
                query TEXT PRIMARY KEY,
                results TEXT,
                cached_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
            CREATE INDEX IF NOT EXISTS idx_symbols_kind ON symbols(kind);
        ''')
        conn.commit()
        conn.close()

    def _file_hash(self, path: Path) -> str:
        """Quick hash for change detection."""
        stat = path.stat()
        return hashlib.md5(f"{stat.st_size}:{stat.st_mtime}".encode()).hexdigest()[:12]

    def index_files(self) -> Dict:
        """Index all files using ripgrep for speed."""
        try:
            # Use ripgrep to list files (respects .gitignore)
            result = subprocess.run(
                ['rg', '--files', '--hidden', '--glob', '!.git'],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            files = result.stdout.strip().split('\n') if result.stdout else []
        except FileNotFoundError:
            # Fallback if rg not available
            files = [str(p.relative_to(self.repo_path))
                    for p in self.repo_path.rglob('*')
                    if p.is_file() and '.git' not in str(p)]

        conn = sqlite3.connect(self.db_path)
        indexed = 0
        for file_path in files:
            if not file_path:
                continue
            full_path = self.repo_path / file_path
            if full_path.exists():
                file_hash = self._file_hash(full_path)
                conn.execute('''
                    INSERT OR REPLACE INTO files (path, hash, size, mtime, indexed_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (file_path, file_hash, full_path.stat().st_size,
                     full_path.stat().st_mtime, datetime.now().isoformat()))
                indexed += 1

        conn.commit()
        conn.close()
        return {'indexed': indexed, 'total_files': len(files)}

    def index_symbols(self) -> Dict:
        """Extract symbols using universal-ctags."""
        try:
            result = subprocess.run(
                ['ctags', '-R', '--output-format=json', '--fields=+nKS', '.'],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                return {'error': 'ctags failed', 'stderr': result.stderr}
        except FileNotFoundError:
            return {'error': 'ctags not installed', 'hint': 'Install universal-ctags'}

        conn = sqlite3.connect(self.db_path)
        symbols = 0
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                tag = json.loads(line)
                conn.execute('''
                    INSERT OR REPLACE INTO symbols (name, kind, file_path, line, scope, signature)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    tag.get('name', ''),
                    tag.get('kind', ''),
                    tag.get('path', ''),
                    tag.get('line', 0),
                    tag.get('scope', ''),
                    tag.get('signature', '')
                ))
                symbols += 1
            except json.JSONDecodeError:
                continue

        conn.commit()
        conn.close()

        # Generate human-readable artifact
        self._generate_symbol_artifact()
        return {'symbols_indexed': symbols}

    def _generate_symbol_artifact(self):
        """Create .repo_artifacts/symbols.md for human review."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute('''
            SELECT kind, COUNT(*) as count FROM symbols GROUP BY kind ORDER BY count DESC
        ''')
        summary = cursor.fetchall()

        cursor = conn.execute('''
            SELECT name, kind, file_path, line FROM symbols ORDER BY kind, name LIMIT 500
        ''')
        symbols = cursor.fetchall()
        conn.close()

        content = f"# Repository Symbols\n\nGenerated: {datetime.now().isoformat()}\n\n"
        content += "## Summary\n\n| Kind | Count |\n|------|-------|\n"
        for kind, count in summary:
            content += f"| {kind} | {count} |\n"

        content += "\n## Symbols (first 500)\n\n"
        current_kind = None
        for name, kind, file_path, line in symbols:
            if kind != current_kind:
                content += f"\n### {kind}\n\n"
                current_kind = kind
            content += f"- `{name}` ({file_path}:{line})\n"

        (self.artifacts_path / 'symbols.md').write_text(content)

    def search(self, pattern: str, file_glob: str = '*') -> List[Dict]:
        """Search using ripgrep with caching."""
        cache_key = f"{pattern}:{file_glob}"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            'SELECT results FROM search_cache WHERE query = ?', (cache_key,)
        )
        cached = cursor.fetchone()
        if cached:
            conn.close()
            return json.loads(cached[0])

        try:
            cmd = ['rg', '--json', '-g', file_glob, pattern]
            result = subprocess.run(cmd, cwd=self.repo_path, capture_output=True, text=True)

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

            # Cache results
            conn.execute(
                'INSERT OR REPLACE INTO search_cache (query, results, cached_at) VALUES (?, ?, ?)',
                (cache_key, json.dumps(matches), datetime.now().isoformat())
            )
            conn.commit()
            conn.close()
            return matches

        except FileNotFoundError:
            conn.close()
            return [{'error': 'ripgrep not installed'}]

    def find_symbol(self, name: str, kind: Optional[str] = None) -> List[Dict]:
        """Find symbol by name."""
        conn = sqlite3.connect(self.db_path)
        if kind:
            cursor = conn.execute(
                'SELECT name, kind, file_path, line, scope, signature FROM symbols WHERE name LIKE ? AND kind = ?',
                (f'%{name}%', kind)
            )
        else:
            cursor = conn.execute(
                'SELECT name, kind, file_path, line, scope, signature FROM symbols WHERE name LIKE ?',
                (f'%{name}%',)
            )
        results = [
            {'name': r[0], 'kind': r[1], 'file': r[2], 'line': r[3], 'scope': r[4], 'signature': r[5]}
            for r in cursor.fetchall()
        ]
        conn.close()
        return results

    def get_status(self) -> Dict:
        """Get index status."""
        conn = sqlite3.connect(self.db_path)
        files = conn.execute('SELECT COUNT(*) FROM files').fetchone()[0]
        symbols = conn.execute('SELECT COUNT(*) FROM symbols').fetchone()[0]
        cache_entries = conn.execute('SELECT COUNT(*) FROM search_cache').fetchone()[0]
        conn.close()

        return {
            'repo_path': str(self.repo_path),
            'files_indexed': files,
            'symbols_indexed': symbols,
            'cache_entries': cache_entries,
            'storage_path': str(self.storage_path),
            'artifacts_path': str(self.artifacts_path)
        }

    def refresh(self) -> Dict:
        """Refresh entire index."""
        file_result = self.index_files()
        symbol_result = self.index_symbols()
        return {**file_result, **symbol_result, 'refreshed_at': datetime.now().isoformat()}
