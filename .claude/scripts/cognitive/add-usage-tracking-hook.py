#!/usr/bin/env python3
"""
Add usage tracking stop hook to Claude Code settings.
Safely appends to existing Stop hook configuration.
"""
import json
from pathlib import Path

settings_file = Path.home() / ".claude/settings.json"

# Load existing settings
if settings_file.exists():
    with open(settings_file) as f:
        settings = json.load(f)
else:
    settings = {}

# Ensure hooks structure exists
if "hooks" not in settings:
    settings["hooks"] = {}

if "Stop" not in settings["hooks"]:
    settings["hooks"]["Stop"] = [{"hooks": []}]

# Check if usage tracking hook already exists
usage_hook = {"type": "command", "command": "python3 ~/.claude/scripts/usage-track-stop.py"}
existing_hooks = settings["hooks"]["Stop"][0]["hooks"]

if usage_hook not in existing_hooks:
    # Add usage tracking hook
    existing_hooks.append(usage_hook)

    # Write back
    with open(settings_file, "w") as f:
        json.dump(settings, f, indent=2)

    print("✅ Added usage tracking stop hook to Claude Code settings")
    print(f"   Location: {settings_file}")
    print("\nStop hooks now configured:")
    for hook in existing_hooks:
        print(f"   - {hook['command']}")
else:
    print("⏭️  Usage tracking hook already configured")

print("\n💡 The hook will run automatically after each conversation turn.")
print("   Data will be written to .claude/usage_history.jsonl")
