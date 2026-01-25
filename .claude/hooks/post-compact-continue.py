#!/usr/bin/env python3
"""
Post-Compact Continue Hook

Triggers after conversation compaction to inject continuation context.
This ensures Claude automatically resumes work without asking what to do.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add daemon to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "daemon"))

def main():
    try:
        from self_continue import format_resume_message, create_checkpoint, get_latest_checkpoint

        # Generate continuation message
        resume_msg = format_resume_message()

        # Output as system reminder for Claude
        output = {
            "result": "continue",
            "message": resume_msg,
            "timestamp": datetime.now().isoformat()
        }

        # Print as system context injection
        print(f"""
<self-continue>
{resume_msg}
</self-continue>

IMPORTANT: This session was compacted. Continue from where you left off.
Do NOT ask what to do next - read the context above and proceed.
""")

    except Exception as e:
        # Fail silently but log
        print(f"# Self-continue: {e}", file=sys.stderr)
        print("Continue from latest handoff in thoughts/handoffs/")


if __name__ == "__main__":
    main()
