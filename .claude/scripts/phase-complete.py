#!/usr/bin/env python3
"""Phase Completion - Send multiple choice options to Telegram.

Call this when completing a phase/cycle to let user choose next iteration.

Usage:
    python phase-complete.py "Phase 11 Complete" "option1" "option2" "option3"
    python phase-complete.py --from-task   # Read options from task.md
"""

import sys
import json
import urllib.request
from pathlib import Path

BOT_TOKEN = "8031397990:AAEr6hUi1XKEJWTM1HLgKTriSfssBAJzLZI"
CHAT_ID = "8266225191"

def send_options(title: str, options: list, summary: str = "") -> bool:
    """Send multiple choice options to Telegram."""

    msg = f"✅ *{title}*\n\n"

    if summary:
        msg += f"{summary}\n\n"

    msg += "*Choose next development iteration:*\n\n"

    for i, opt in enumerate(options, 1):
        msg += f"*{i}.* {opt}\n"

    msg += "\n_Reply with number (1-" + str(len(options)) + ") or describe custom direction_"

    data = json.dumps({
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }).encode('utf-8')

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("ok", False)
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr)
        return False


def get_options_from_task() -> tuple:
    """Read potential next steps from task.md."""
    project_dir = Path(__file__).parent.parent.parent
    task_file = project_dir / "task.md"

    if not task_file.exists():
        return "Phase Complete", ["Continue current work", "Review and refactor", "Start new feature"]

    content = task_file.read_text()

    # Extract current phase
    title = "Phase Complete"
    for line in content.split('\n'):
        if 'Phase' in line and ('IN PROGRESS' in line or '->>' in line):
            title = line.strip().replace('->>', '').replace('IN PROGRESS', '').strip()
            break

    # Look for TODO or Next sections
    options = []
    in_next_section = False
    for line in content.split('\n'):
        if 'TODO' in line.upper() or 'NEXT' in line.upper() or 'UPCOMING' in line.upper():
            in_next_section = True
            continue
        if in_next_section and line.strip().startswith('- '):
            opt = line.strip()[2:].strip()
            if opt and len(opt) < 100:
                options.append(opt)
            if len(options) >= 4:
                break
        if in_next_section and line.strip() and not line.strip().startswith('-'):
            if not line.strip().startswith('#'):
                in_next_section = False

    if not options:
        options = [
            "Continue current implementation",
            "Fix bugs and stabilize",
            "Add tests and documentation",
            "Start next major feature"
        ]

    return title, options[:4]


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--from-task":
        title, options = get_options_from_task()
        summary = ""
    else:
        title = sys.argv[1]
        options = sys.argv[2:] if len(sys.argv) > 2 else [
            "Continue current work",
            "Review and optimize",
            "Start new feature"
        ]
        summary = ""

    if send_options(title, options, summary):
        print(f"Sent options for: {title}")
    else:
        print("Failed to send", file=sys.stderr)
        sys.exit(1)
