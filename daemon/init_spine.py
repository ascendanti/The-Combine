#!/usr/bin/env python3
"""
Init Spine - Run on system startup to initialize all infrastructure.

Called automatically by:
- Docker container startup
- Windows startup script
- Session start hook

Initializes:
- Atlas map (repo index)
- Analytics database
- Event store
- Playbook validation
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent paths
DAEMON_DIR = Path(__file__).parent
REPO_ROOT = DAEMON_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

def init_atlas_spine():
    """Initialize Atlas Spine infrastructure."""
    print(f"[{datetime.now().isoformat()}] Initializing Atlas Spine...")

    try:
        from atlas_spine.map import AtlasMap
        from atlas_spine.events import EventStore

        # Build/refresh map
        atlas_map = AtlasMap(REPO_ROOT)
        result = atlas_map.build()
        print(f"  Map: {result.get('files_indexed', 0)} files indexed")

        # Initialize event store
        events = EventStore(REPO_ROOT)
        events.log(
            command_text='init_spine',
            route={'operator': 'INIT', 'method': 'startup'},
            operator='INIT',
            inputs={},
            outputs=result,
            status='success',
            next_suggestion=None
        )
        print(f"  Events: Initialized")

        return True
    except Exception as e:
        print(f"  Atlas Spine error: {e}")
        return False


def init_analytics():
    """Initialize self-analytics database."""
    print("  Initializing analytics...")

    try:
        from feedback_loop import init_analytics_db, track_component
        init_analytics_db()
        track_component('init_spine', True)
        print(f"  Analytics: Ready")
        return True
    except Exception as e:
        print(f"  Analytics error: {e}")
        return False


def validate_playbooks():
    """Validate playbook files exist and are valid."""
    print("  Validating playbooks...")

    playbooks_dir = REPO_ROOT / 'atlas_spine' / 'playbooks'
    if not playbooks_dir.exists():
        print(f"    Playbooks directory missing")
        return False

    import yaml
    valid = 0
    for pb in playbooks_dir.glob('*.yaml'):
        try:
            yaml.safe_load(pb.read_text())
            valid += 1
        except Exception as e:
            print(f"    Invalid playbook {pb.name}: {e}")

    print(f"  Playbooks: {valid} valid")
    return valid > 0


def check_dependencies():
    """Check required dependencies are available."""
    print("  Checking dependencies...")

    deps = {
        'fire': False,
        'yaml': False,
        'redis': False,
    }

    try:
        import fire
        deps['fire'] = True
    except ImportError:
        pass

    try:
        import yaml
        deps['yaml'] = True
    except ImportError:
        pass

    try:
        import redis
        deps['redis'] = True
    except ImportError:
        pass

    missing = [k for k, v in deps.items() if not v]
    if missing:
        print(f"    Missing: {missing}")
    else:
        print(f"  Dependencies: All present")

    return len(missing) == 0


def main():
    """Run full initialization."""
    print("=" * 50)
    print("ATLAS SPINE INITIALIZATION")
    print("=" * 50)

    results = {
        'atlas_spine': init_atlas_spine(),
        'analytics': init_analytics(),
        'playbooks': validate_playbooks(),
        'dependencies': check_dependencies(),
    }

    success = all(results.values())

    print()
    print("=" * 50)
    if success:
        print("INIT COMPLETE - All systems ready")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"INIT PARTIAL - Failed: {failed}")
    print("=" * 50)

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
