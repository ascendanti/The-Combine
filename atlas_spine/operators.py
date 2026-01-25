"""
Atlas Operators - Deterministic Functions

Operators:
- LOOKUP: Find files/symbols in map
- OPEN: Read file content
- PATCH: Apply code changes (requires confirmation)
- DIAGNOSE: Check playbooks for known issues
- TEST: Run tests/commands
- THINK: Use LocalAI for complex reasoning (fallback)
"""

import json
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml

class Operators:
    """Deterministic operators for Atlas routing."""

    def __init__(self, repo_path: Optional[Path] = None, atlas_map=None, localai_url: str = 'http://localhost:8080/v1'):
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.atlas_map = atlas_map
        self.localai_url = localai_url
        self.playbooks_dir = self.repo_path / 'atlas_spine' / 'playbooks'

    def lookup(self, query: str) -> Dict:
        """LOOKUP: Find files/symbols matching query."""
        results = {'operator': 'LOOKUP', 'query': query, 'results': []}

        # Try map query first
        if self.atlas_map:
            map_results = self.atlas_map.query(query)
            results['results'] = map_results[:10]

        # Supplement with ripgrep
        if len(results['results']) < 5:
            try:
                rg_result = subprocess.run(
                    ['rg', '-l', '-i', query],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if rg_result.stdout:
                    for path in rg_result.stdout.strip().split('\n')[:10]:
                        if path and not any(r['path'] == path for r in results['results']):
                            results['results'].append({'path': path, 'source': 'ripgrep'})
            except:
                pass

        results['count'] = len(results['results'])
        return results

    def open(self, file_path: str, line_start: int = 1, line_end: int = 50) -> Dict:
        """OPEN: Read file content."""
        full_path = self.repo_path / file_path
        results = {'operator': 'OPEN', 'file': file_path}

        if not full_path.exists():
            results['error'] = f'File not found: {file_path}'
            return results

        try:
            content = full_path.read_text(errors='ignore')
            lines = content.split('\n')
            selected = lines[line_start-1:line_end]
            results['content'] = '\n'.join(f'{i+line_start}: {line}' for i, line in enumerate(selected))
            results['total_lines'] = len(lines)
            results['showing'] = f'{line_start}-{min(line_end, len(lines))}'
        except Exception as e:
            results['error'] = str(e)

        return results

    def diagnose(self, error_text: str) -> Dict:
        """DIAGNOSE: Check playbooks for known issues."""
        results = {'operator': 'DIAGNOSE', 'error': error_text[:200], 'matches': []}

        # Load all playbooks
        playbooks = self._load_playbooks()

        error_lower = error_text.lower()

        for playbook_name, playbook in playbooks.items():
            for pattern in playbook.get('patterns', []):
                if pattern.lower() in error_lower:
                    results['matches'].append({
                        'playbook': playbook_name,
                        'pattern': pattern,
                        'diagnosis': playbook.get('diagnosis', 'Unknown'),
                        'fix': playbook.get('fix', 'See playbook'),
                        'commands': playbook.get('commands', [])
                    })

        if not results['matches']:
            results['suggestion'] = 'No known playbook match. Consider THINK operator.'

        return results

    def _load_playbooks(self) -> Dict:
        """Load all playbooks from directory."""
        playbooks = {}

        if not self.playbooks_dir.exists():
            return playbooks

        for pb_file in self.playbooks_dir.glob('*.yaml'):
            try:
                content = yaml.safe_load(pb_file.read_text())
                if content:
                    playbooks[pb_file.stem] = content
            except:
                pass

        for pb_file in self.playbooks_dir.glob('*.json'):
            try:
                content = json.loads(pb_file.read_text())
                if content:
                    playbooks[pb_file.stem] = content
            except:
                pass

        return playbooks

    def test(self, command: str, timeout: int = 30) -> Dict:
        """TEST: Run a test command."""
        results = {'operator': 'TEST', 'command': command}

        # Safety: block dangerous commands
        dangerous = ['rm -rf', 'del /f', 'format', 'mkfs', ':(){']
        if any(d in command.lower() for d in dangerous):
            results['error'] = 'Command blocked for safety'
            return results

        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            results['stdout'] = proc.stdout[:2000] if proc.stdout else ''
            results['stderr'] = proc.stderr[:500] if proc.stderr else ''
            results['exit_code'] = proc.returncode
            results['success'] = proc.returncode == 0
        except subprocess.TimeoutExpired:
            results['error'] = f'Command timed out after {timeout}s'
        except Exception as e:
            results['error'] = str(e)

        return results

    def think(self, question: str, context: str = '') -> Dict:
        """THINK: Use LocalAI for reasoning (fallback)."""
        results = {'operator': 'THINK', 'question': question}

        try:
            import urllib.request

            prompt = f"""You are a helpful assistant. Answer concisely in JSON format.
Context: {context[:1000]}
Question: {question}

Respond with JSON: {{"answer": "...", "next_action": "LOOKUP|OPEN|TEST|DONE", "next_params": {{}}}}"""

            payload = json.dumps({
                'model': 'mistral',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.1,
                'max_tokens': 500
            }).encode()

            req = urllib.request.Request(
                f'{self.localai_url}/chat/completions',
                data=payload,
                headers={'Content-Type': 'application/json'}
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')

                # Try to parse JSON from response
                try:
                    results['response'] = json.loads(content)
                except:
                    results['response'] = {'answer': content, 'next_action': 'DONE'}

                results['tokens_used'] = data.get('usage', {}).get('total_tokens', 0)

        except Exception as e:
            results['error'] = str(e)
            results['fallback'] = 'LocalAI unavailable. Manual intervention needed.'

        return results

    def patch(self, file_path: str, old_text: str, new_text: str, confirm: bool = False) -> Dict:
        """PATCH: Apply code changes (requires confirmation)."""
        results = {'operator': 'PATCH', 'file': file_path}

        if not confirm:
            results['status'] = 'pending_confirmation'
            results['preview'] = {
                'file': file_path,
                'old': old_text[:200],
                'new': new_text[:200]
            }
            results['message'] = 'Run with confirm=True to apply'
            return results

        full_path = self.repo_path / file_path
        if not full_path.exists():
            results['error'] = f'File not found: {file_path}'
            return results

        try:
            content = full_path.read_text()
            if old_text not in content:
                results['error'] = 'Old text not found in file'
                return results

            new_content = content.replace(old_text, new_text, 1)
            full_path.write_text(new_content)
            results['status'] = 'applied'
            results['message'] = f'Patched {file_path}'
        except Exception as e:
            results['error'] = str(e)

        return results

    def execute(self, operator: str, params: Dict) -> Dict:
        """Execute an operator with params."""
        handlers = {
            'LOOKUP': lambda p: self.lookup(p.get('query', '')),
            'OPEN': lambda p: self.open(p.get('file', ''), p.get('line_start', 1), p.get('line_end', 50)),
            'DIAGNOSE': lambda p: self.diagnose(p.get('error', '')),
            'TEST': lambda p: self.test(p.get('command', ''), p.get('timeout', 30)),
            'THINK': lambda p: self.think(p.get('question', ''), p.get('context', '')),
            'PATCH': lambda p: self.patch(p.get('file', ''), p.get('old', ''), p.get('new', ''), p.get('confirm', False)),
        }

        operator = operator.upper()
        if operator not in handlers:
            return {'error': f'Unknown operator: {operator}', 'available': list(handlers.keys())}

        return handlers[operator](params)
