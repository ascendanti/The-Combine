#!/usr/bin/env python3
"""
PostToolUse hook for Write operations.
Automatically updates ARCHITECTURE-LIVE.md when significant files are created.

Significant files:
- *.md in daemon/ (documentation)
- *.py in daemon/ (new modules)
- Files in .claude/ (skills, rules, agents)
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Significant paths to auto-index
SIGNIFICANT_PATTERNS = [
    ("daemon/*.md", "Reference Documents"),
    ("daemon/*.py", "Daemon Modules"),
    (".claude/skills/*/SKILL.md", "Skills"),
    (".claude/agents/*.md", "Agents"),
    (".claude/rules/*.md", "Rules"),
    (".claude/hooks/*.py", "Hooks"),
]

def get_architecture_path():
    """Get path to ARCHITECTURE-LIVE.md"""
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR', '')
    if project_dir:
        return Path(project_dir) / '.claude' / 'ARCHITECTURE-LIVE.md'
    return None

def is_significant_file(file_path: str) -> tuple:
    """Check if file should be auto-indexed. Returns (should_index, category)."""
    path = Path(file_path)
    name = path.name

    # Check for daemon docs
    if 'daemon' in str(path) and name.endswith('.md') and name != 'CLAUDE.md':
        return True, "Reference Documents"

    # Check for new daemon modules
    if 'daemon' in str(path) and name.endswith('.py') and not name.startswith('__'):
        return True, "Daemon Modules"

    # Check for skills
    if '.claude/skills' in str(path) and name == 'SKILL.md':
        return True, "Skills"

    # Check for agents
    if '.claude/agents' in str(path) and name.endswith('.md'):
        return True, "Agents"

    # Check for rules
    if '.claude/rules' in str(path) and name.endswith('.md'):
        return True, "Rules"

    # Check for hooks
    if '.claude/hooks' in str(path) and (name.endswith('.py') or name.endswith('.js')):
        return True, "Hooks"

    return False, None

def update_architecture(file_path: str, category: str):
    """Add file to ARCHITECTURE-LIVE.md Reference Documents section."""
    arch_path = get_architecture_path()
    if not arch_path or not arch_path.exists():
        return False

    try:
        content = arch_path.read_text(encoding='utf-8')
        path = Path(file_path)
        name = path.name
        today = datetime.now().strftime('%Y-%m-%d')

        # For Reference Documents section
        if category == "Reference Documents":
            marker = "## Reference Documents (daemon/)"
            if marker in content:
                # Find the table and add entry
                lines = content.split('\n')
                new_lines = []
                in_section = False
                entry_added = False

                for i, line in enumerate(lines):
                    new_lines.append(line)
                    if marker in line:
                        in_section = True
                    elif in_section and line.startswith('| `') and not entry_added:
                        # Check if file already exists
                        if f'| `{name}`' not in content:
                            # Add before first entry
                            new_entry = f"| `{name}` | Auto-indexed | {today} |"
                            new_lines.insert(-1, new_entry)
                            entry_added = True
                            in_section = False

                if entry_added:
                    arch_path.write_text('\n'.join(new_lines), encoding='utf-8')
                    return True

        return False
    except Exception:
        return False

def main():
    try:
        # Read hook input
        hook_input = json.load(sys.stdin)

        # Only process Write operations
        tool_name = hook_input.get('tool_name', '')
        if tool_name != 'Write':
            print(json.dumps({"continue": True}))
            return

        # Get file path from tool input
        tool_input = hook_input.get('tool_input', {})
        file_path = tool_input.get('file_path', '')

        if not file_path:
            print(json.dumps({"continue": True}))
            return

        # Check if significant
        should_index, category = is_significant_file(file_path)

        if should_index:
            updated = update_architecture(file_path, category)
            if updated:
                print(json.dumps({
                    "continue": True,
                    "message": f"[auto-index] Added {Path(file_path).name} to ARCHITECTURE-LIVE.md"
                }))
            else:
                print(json.dumps({"continue": True}))
        else:
            print(json.dumps({"continue": True}))

    except Exception as e:
        # Don't block on errors
        print(json.dumps({"continue": True}))

if __name__ == "__main__":
    main()
