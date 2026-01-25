"""
GitHistorian - Track repository history and changes
"""

import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class GitHistorian:
    """Analyze git history for insights."""

    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path)

    def _run_git(self, *args) -> str:
        """Run git command and return output."""
        try:
            result = subprocess.run(
                ['git', *args],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            return result.stdout.strip() if result.returncode == 0 else ''
        except FileNotFoundError:
            return ''

    def get_recent_commits(self, limit: int = 20) -> List[Dict]:
        """Get recent commit history."""
        output = self._run_git('log', f'-{limit}', '--pretty=format:%H|%an|%ae|%at|%s')
        if not output:
            return []

        commits = []
        for line in output.split('\n'):
            if '|' in line:
                parts = line.split('|', 4)
                if len(parts) >= 5:
                    commits.append({
                        'hash': parts[0][:8],
                        'author': parts[1],
                        'email': parts[2],
                        'date': datetime.fromtimestamp(int(parts[3])).isoformat(),
                        'message': parts[4]
                    })
        return commits

    def get_file_history(self, file_path: str, limit: int = 10) -> List[Dict]:
        """Get history of a specific file."""
        output = self._run_git('log', f'-{limit}', '--pretty=format:%H|%an|%at|%s', '--', file_path)
        if not output:
            return []

        history = []
        for line in output.split('\n'):
            if '|' in line:
                parts = line.split('|', 3)
                if len(parts) >= 4:
                    history.append({
                        'hash': parts[0][:8],
                        'author': parts[1],
                        'date': datetime.fromtimestamp(int(parts[2])).isoformat(),
                        'message': parts[3]
                    })
        return history

    def get_changed_files(self, since: Optional[str] = None) -> List[str]:
        """Get files changed since a commit or date."""
        if since:
            output = self._run_git('diff', '--name-only', since, 'HEAD')
        else:
            output = self._run_git('diff', '--name-only', 'HEAD~10', 'HEAD')
        return output.split('\n') if output else []

    def get_blame(self, file_path: str, line_start: int = 1, line_end: int = 20) -> List[Dict]:
        """Get blame info for lines in a file."""
        output = self._run_git('blame', '-L', f'{line_start},{line_end}', '--line-porcelain', file_path)
        if not output:
            return []

        blames = []
        current = {}
        for line in output.split('\n'):
            if line.startswith('author '):
                current['author'] = line[7:]
            elif line.startswith('author-time '):
                current['date'] = datetime.fromtimestamp(int(line[12:])).isoformat()
            elif line.startswith('summary '):
                current['message'] = line[8:]
            elif line.startswith('\t'):
                current['line'] = line[1:]
                blames.append(current)
                current = {}
        return blames

    def get_contributors(self, limit: int = 10) -> List[Dict]:
        """Get top contributors."""
        output = self._run_git('shortlog', '-sne', f'--max-count={limit * 10}', 'HEAD')
        if not output:
            return []

        contributors = []
        for line in output.strip().split('\n')[:limit]:
            parts = line.strip().split('\t', 1)
            if len(parts) >= 2:
                count = int(parts[0].strip())
                name_email = parts[1]
                contributors.append({
                    'commits': count,
                    'name': name_email.split('<')[0].strip() if '<' in name_email else name_email
                })
        return contributors

    def get_stats(self) -> Dict:
        """Get repository statistics."""
        total_commits = self._run_git('rev-list', '--count', 'HEAD')
        branch = self._run_git('branch', '--show-current')
        remote = self._run_git('remote', 'get-url', 'origin')

        # File count by extension
        files_output = self._run_git('ls-files')
        files = files_output.split('\n') if files_output else []

        ext_counts = {}
        for f in files:
            ext = Path(f).suffix.lower() or '(no ext)'
            ext_counts[ext] = ext_counts.get(ext, 0) + 1

        return {
            'total_commits': int(total_commits) if total_commits.isdigit() else 0,
            'current_branch': branch,
            'remote': remote,
            'total_files': len(files),
            'extensions': dict(sorted(ext_counts.items(), key=lambda x: -x[1])[:10])
        }

    def find_commits_touching(self, symbol: str, limit: int = 5) -> List[Dict]:
        """Find commits that mention a symbol."""
        output = self._run_git('log', f'-{limit}', '-S', symbol, '--pretty=format:%H|%an|%at|%s')
        if not output:
            return []

        commits = []
        for line in output.split('\n'):
            if '|' in line:
                parts = line.split('|', 3)
                if len(parts) >= 4:
                    commits.append({
                        'hash': parts[0][:8],
                        'author': parts[1],
                        'date': datetime.fromtimestamp(int(parts[2])).isoformat(),
                        'message': parts[3]
                    })
        return commits
