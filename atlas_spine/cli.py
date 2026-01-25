#!/usr/bin/env python3
"""
Atlas CLI - Single entry point for all Atlas operations

Usage:
    atlas route "find the ingest code"
    atlas map build
    atlas map query "ingest"
    atlas audit last
    atlas loop
    atlas daily
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from atlas_spine.map import AtlasMap
from atlas_spine.router import AtlasRouter
from atlas_spine.events import EventStore
from atlas_spine.operators import Operators


def cmd_route(args):
    """Route a request."""
    router = AtlasRouter(args.repo)
    request = ' '.join(args.request)
    result = router.execute(request)

    print(json.dumps(result['result'], indent=2))
    if result.get('next_suggestion'):
        print(f"\nNext: {result['next_suggestion']}")


def cmd_map(args):
    """Map operations."""
    atlas_map = AtlasMap(args.repo)

    if args.map_cmd == 'build':
        result = atlas_map.build(verbose=args.verbose)
        print(json.dumps(result, indent=2))
    elif args.map_cmd == 'query':
        query = ' '.join(args.args) if args.args else ''
        results = atlas_map.query(query)
        for r in results[:10]:
            print(f"{r['score']:2d} {r['path']}")
            print(f"   {r['description'][:60]}")
    elif args.map_cmd == 'stats':
        print(json.dumps(atlas_map.stats(), indent=2))


def cmd_audit(args):
    """Audit operations."""
    store = EventStore(args.repo)

    if args.audit_cmd == 'last':
        events = store.last(args.n)
        for e in events:
            status = '✓' if e['status'] == 'success' else '✗'
            print(f"{status} {e['ts'][:19]} [{e['operator']}] {e['command_text'][:40]}")
    elif args.audit_cmd == 'trace':
        if args.args:
            event = store.trace(args.args[0])
            print(json.dumps(event, indent=2))
    elif args.audit_cmd == 'search':
        keyword = ' '.join(args.args) if args.args else ''
        results = store.search(keyword)
        for e in results:
            print(f"{e['ts'][:19]} [{e['operator']}] {e['command_text'][:40]}")
    elif args.audit_cmd == 'stats':
        print(json.dumps(store.stats(), indent=2))


def cmd_loop(args):
    """Interactive loop."""
    router = AtlasRouter(args.repo)

    print("Atlas Loop (type 'exit' to quit)")
    while True:
        try:
            request = input("\n> ").strip()
            if request.lower() in ['exit', 'quit', 'q']:
                break
            if not request:
                continue

            result = router.execute(request)
            print(json.dumps(result['result'], indent=2)[:1000])
            if result.get('next_suggestion'):
                print(f"\nSuggested: {result['next_suggestion']}")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")


def cmd_daily(args):
    """Run daily improvement loop."""
    repo_path = args.repo or Path.cwd()
    atlas_dir = repo_path / '.atlas'
    atlas_dir.mkdir(exist_ok=True)

    results = {'timestamp': datetime.now().isoformat(), 'steps': []}

    # Step 1: Rebuild map
    print("1. Rebuilding map...")
    atlas_map = AtlasMap(repo_path)
    map_result = atlas_map.build()
    results['steps'].append({'name': 'map_build', 'result': map_result})

    # Step 2: Check for pending repairs
    print("2. Checking repair queue...")
    repair_path = atlas_dir / 'repair_queue.jsonl'
    repairs_pending = 0
    if repair_path.exists():
        repairs_pending = len(repair_path.read_text().strip().split('\n'))
    results['steps'].append({'name': 'repairs_check', 'pending': repairs_pending})

    # Step 3: Run bench questions
    print("3. Running bench questions...")
    bench_path = atlas_dir / 'bench_questions.yaml'
    if bench_path.exists():
        import yaml
        questions = yaml.safe_load(bench_path.read_text())
        router = AtlasRouter(repo_path)

        correct = 0
        for q in questions.get('questions', [])[:5]:  # Limit to 5 for speed
            result = router.execute(q.get('question', ''))
            if result['result'].get('count', 0) > 0:
                correct += 1

        results['steps'].append({'name': 'bench', 'questions': len(questions.get('questions', [])), 'correct': correct})
    else:
        results['steps'].append({'name': 'bench', 'skipped': 'No bench_questions.yaml'})

    # Step 4: Log daily run
    print("4. Logging results...")
    events = EventStore(repo_path)
    events.log(
        command_text='atlas daily',
        route={'operator': 'DAILY', 'method': 'scheduled'},
        operator='DAILY',
        inputs={},
        outputs=results,
        status='success',
        next_suggestion='Review repair_queue.jsonl'
    )

    # Summary
    print(f"\n=== Daily Loop Complete ===")
    print(f"Map: {map_result.get('files_indexed', 0)} files indexed")
    print(f"Repairs pending: {repairs_pending}")
    print(json.dumps(results, indent=2))


class AtlasCLI:
    """Atlas Spine CLI - Deterministic orchestration layer."""

    def __init__(self, repo: str = None):
        self.repo_path = Path(repo) if repo else Path.cwd()

    def route(self, *request):
        """Route a request to the appropriate operator."""
        router = AtlasRouter(self.repo_path)
        request_text = ' '.join(request)
        result = router.execute(request_text)
        print(json.dumps(result['result'], indent=2))
        if result.get('next_suggestion'):
            print(f"\nNext: {result['next_suggestion']}")

    def map(self, cmd: str, *args):
        """Map operations: build, query, stats."""
        atlas_map = AtlasMap(self.repo_path)
        if cmd == 'build':
            print(json.dumps(atlas_map.build(), indent=2))
        elif cmd == 'query':
            for r in atlas_map.query(' '.join(args))[:10]:
                print(f"{r['score']:2d} {r['path']}")
        elif cmd == 'stats':
            print(json.dumps(atlas_map.stats(), indent=2))

    def audit(self, cmd: str, *args, n: int = 10):
        """Audit operations: last, trace, search, stats."""
        store = EventStore(self.repo_path)
        if cmd == 'last':
            for e in store.last(n):
                status = '✓' if e['status'] == 'success' else '✗'
                print(f"{status} {e['ts'][:19]} [{e['operator']}] {e['command_text'][:40]}")
        elif cmd == 'trace' and args:
            print(json.dumps(store.trace(args[0]), indent=2))
        elif cmd == 'search':
            for e in store.search(' '.join(args)):
                print(f"{e['ts'][:19]} [{e['operator']}] {e['command_text'][:40]}")
        elif cmd == 'stats':
            print(json.dumps(store.stats(), indent=2))

    def loop(self):
        """Interactive routing loop."""
        router = AtlasRouter(self.repo_path)
        print("Atlas Loop (type 'exit' to quit)")
        while True:
            try:
                request = input("\n> ").strip()
                if request.lower() in ['exit', 'quit', 'q']:
                    break
                if request:
                    result = router.execute(request)
                    print(json.dumps(result['result'], indent=2)[:1000])
            except KeyboardInterrupt:
                break

    def daily(self):
        """Run daily improvement loop."""
        class Args:
            repo = self.repo_path
        cmd_daily(Args())

    def status(self):
        """Quick system status."""
        atlas_map = AtlasMap(self.repo_path)
        store = EventStore(self.repo_path)
        print(f"Map: {atlas_map.stats().get('total_files', 0)} files indexed")
        print(f"Events: {store.stats().get('total_events', 0)} logged")
        print(f"Repo: {self.repo_path}")


def main():
    """Entry point - uses python-fire pattern for simplicity."""
    try:
        import fire
        fire.Fire(AtlasCLI)
    except ImportError:
        # Fallback to argparse if fire not installed
        parser = argparse.ArgumentParser(description='Atlas Spine CLI')
        parser.add_argument('--repo', type=Path, default=Path.cwd())
        parser.add_argument('command', nargs='?', default='status')
        parser.add_argument('args', nargs='*')
        args = parser.parse_args()

        cli = AtlasCLI(str(args.repo))
        if hasattr(cli, args.command):
            getattr(cli, args.command)(*args.args)
        else:
            print("Commands: route, map, audit, loop, daily, status")


if __name__ == '__main__':
    main()
