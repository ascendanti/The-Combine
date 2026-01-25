#!/usr/bin/env python3
"""
Usage Tracker Stop Hook
Runs after each conversation turn to track which files were actually accessed.

Analyzes:
- Tool calls (Read, Edit, Write, Grep, etc.)
- Source files affected
- Which .claude/*.md files were useful

Feeds data to UsageTracker for learning.
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add scripts to path for importing
sys.path.insert(0, str(Path(__file__).parent))

try:
    from usage_tracker import UsageTracker
    TRACKER_AVAILABLE = True
except ImportError:
    TRACKER_AVAILABLE = False

# Session environment
SESSION_ENV = Path(os.environ.get("CLAUDE_SESSION_ENV", ""))

def get_transcript_path():
    """Get path to transcript.jsonl."""
    if SESSION_ENV and SESSION_ENV.exists():
        return SESSION_ENV / "transcript.jsonl"
    return None

def extract_tool_calls(transcript_path):
    """
    Extract all tool calls from the last assistant response.
    Returns list of {tool, target, success} dicts.
    """
    if not transcript_path or not transcript_path.exists():
        return []

    tool_calls = []

    try:
        with open(transcript_path) as f:
            lines = f.readlines()

        # Find last assistant message
        for line in reversed(lines):
            try:
                entry = json.loads(line)
                if entry.get("type") == "assistant" or entry.get("role") == "assistant":
                    # Extract content blocks
                    content = entry.get("message", {}).get("content", [])
                    if not content:
                        content = entry.get("content", [])

                    # Look for tool_use blocks
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "tool_use":
                                tool_name = block.get("name", "")
                                tool_input = block.get("input", {})

                                # Extract target file/path
                                target = None
                                if "file_path" in tool_input:
                                    target = tool_input["file_path"]
                                elif "path" in tool_input:
                                    target = tool_input["path"]
                                elif "pattern" in tool_input:
                                    # Grep pattern - we'll track as search operation
                                    target = tool_input.get("path", "*")

                                if target:
                                    tool_calls.append({
                                        'tool': tool_name,
                                        'target': target,
                                        'success': True  # Assume success if in transcript
                                    })

                    # Also check for function_results in subsequent messages
                    # to determine if tool calls succeeded
                    break

            except (json.JSONDecodeError, KeyError, TypeError):
                continue

    except Exception as e:
        # Silent failure
        pass

    return tool_calls

def get_last_response_text(transcript_path):
    """Get last assistant response text for mention detection."""
    if not transcript_path or not transcript_path.exists():
        return ""

    try:
        with open(transcript_path) as f:
            lines = f.readlines()

        for line in reversed(lines):
            try:
                entry = json.loads(line)
                if entry.get("type") == "assistant" or entry.get("role") == "assistant":
                    content = entry.get("message", {}).get("content", [])
                    if not content:
                        content = entry.get("content", [])

                    text_parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif isinstance(block, str):
                            text_parts.append(block)

                    return "\n".join(text_parts)
            except:
                continue
    except:
        pass

    return ""

def main():
    """Main entry point."""
    if not TRACKER_AVAILABLE:
        return  # Silent fail if tracker not available

    try:
        # Initialize tracker
        tracker = UsageTracker(mode='observe')

        # Get transcript path
        transcript_path = get_transcript_path()
        if not transcript_path:
            return

        # Extract tool calls from last response
        tool_calls = extract_tool_calls(transcript_path)

        # Get response text for mention detection
        response_text = get_last_response_text(transcript_path)

        # Track usage if we have data
        if tool_calls or response_text:
            tracker.track_turn_usage(tool_calls, response_text)

    except Exception as e:
        # Silent failure - don't block conversation
        error_log = Path.home() / ".claude/usage_tracking_errors.log"
        error_log.parent.mkdir(parents=True, exist_ok=True)
        with open(error_log, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] {e}\n")

if __name__ == "__main__":
    main()
