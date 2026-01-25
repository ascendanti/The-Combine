"""
Atlas Event Store - Append-only Audit Logs

Events are stored in .atlas/events.jsonl

Each event:
- ts: timestamp
- command_text: original request
- route_json: routing decision
- operator: which operator was used
- inputs: operator inputs
- outputs_summary: result summary
- status: success/error
- error: error message if any
- next_suggestion: suggested next action
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import uuid

class EventStore:
    """Append-only event log for auditing."""

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.atlas_dir = self.repo_path / '.atlas'
        self.atlas_dir.mkdir(exist_ok=True)
        self.events_path = self.atlas_dir / 'events.jsonl'

    def log(self, command_text: str, route: Dict, operator: str,
            inputs: Dict, outputs: Dict, status: str = 'success',
            error: Optional[str] = None, next_suggestion: Optional[str] = None) -> str:
        """Log an event. Returns event_id."""
        event_id = str(uuid.uuid4())[:8]

        # Summarize outputs (avoid huge logs)
        outputs_summary = self._summarize(outputs)

        event = {
            'id': event_id,
            'ts': datetime.now().isoformat(),
            'command_text': command_text[:500],
            'route_json': route,
            'operator': operator,
            'inputs': inputs,
            'outputs_summary': outputs_summary,
            'status': status,
            'error': error,
            'next_suggestion': next_suggestion
        }

        with open(self.events_path, 'a') as f:
            f.write(json.dumps(event) + '\n')

        return event_id

    def _summarize(self, outputs: Dict, max_len: int = 500) -> Dict:
        """Create summary of outputs for logging."""
        summary = {}
        for key, value in outputs.items():
            if isinstance(value, str):
                summary[key] = value[:max_len] + '...' if len(value) > max_len else value
            elif isinstance(value, list):
                summary[key] = f'[{len(value)} items]'
            elif isinstance(value, dict):
                summary[key] = f'{{...{len(value)} keys}}'
            else:
                summary[key] = value
        return summary

    def last(self, n: int = 10) -> List[Dict]:
        """Get last n events."""
        if not self.events_path.exists():
            return []

        events = []
        for line in self.events_path.read_text().strip().split('\n'):
            if line:
                try:
                    events.append(json.loads(line))
                except:
                    pass

        return events[-n:]

    def trace(self, job_id: str) -> Optional[Dict]:
        """Get event by ID."""
        if not self.events_path.exists():
            return None

        for line in self.events_path.read_text().strip().split('\n'):
            if line:
                try:
                    event = json.loads(line)
                    if event.get('id') == job_id:
                        return event
                except:
                    pass
        return None

    def search(self, keyword: str, limit: int = 20) -> List[Dict]:
        """Search events by keyword."""
        if not self.events_path.exists():
            return []

        keyword_lower = keyword.lower()
        results = []

        for line in self.events_path.read_text().strip().split('\n'):
            if line and keyword_lower in line.lower():
                try:
                    results.append(json.loads(line))
                except:
                    pass

        return results[-limit:]

    def stats(self) -> Dict:
        """Get event statistics."""
        if not self.events_path.exists():
            return {'total_events': 0}

        events = self.last(1000)

        operators_count = {}
        status_count = {'success': 0, 'error': 0}

        for e in events:
            op = e.get('operator', 'unknown')
            operators_count[op] = operators_count.get(op, 0) + 1
            status_count[e.get('status', 'unknown')] = status_count.get(e.get('status', 'unknown'), 0) + 1

        return {
            'total_events': len(events),
            'operators': operators_count,
            'status': status_count,
            'last_event': events[-1]['ts'] if events else None
        }


def main():
    """CLI for event operations."""
    import argparse
    parser = argparse.ArgumentParser(description='Atlas Event Store')
    parser.add_argument('command', choices=['last', 'trace', 'search', 'stats'])
    parser.add_argument('args', nargs='*')
    parser.add_argument('--repo', type=str, help='Repository path')
    parser.add_argument('-n', type=int, default=10)

    args = parser.parse_args()
    store = EventStore(Path(args.repo) if args.repo else None)

    if args.command == 'last':
        events = store.last(args.n)
        for e in events:
            print(f"{e['ts']} [{e['operator']}] {e['command_text'][:50]} -> {e['status']}")
    elif args.command == 'trace':
        if args.args:
            event = store.trace(args.args[0])
            print(json.dumps(event, indent=2))
    elif args.command == 'search':
        keyword = ' '.join(args.args) if args.args else ''
        results = store.search(keyword)
        for e in results:
            print(f"{e['ts']} [{e['operator']}] {e['command_text'][:50]}")
    elif args.command == 'stats':
        print(json.dumps(store.stats(), indent=2))


if __name__ == '__main__':
    main()
