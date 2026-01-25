#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""SessionStart Hook: Surface forgotten modules."""

import json
import sys
from pathlib import Path

DAEMON_DIR = Path(__file__).parent.parent.parent / "daemon"
sys.path.insert(0, str(DAEMON_DIR))

def main():
    try:
        from module_registry import get_dormant_modules, sync_modules
        sync_modules()
        dormant = get_dormant_modules(3)  # 3 days threshold

        if dormant:
            names = [m["name"] for m in dormant[:5]]
            print(f"[REMINDER] Unused modules: {', '.join(names)}", file=sys.stderr)

    except Exception as e:
        pass  # Fail silently

    print(json.dumps({"continue": True}))

if __name__ == "__main__":
    main()
