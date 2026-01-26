#!/usr/bin/env python3
"""
Sequential Executor - Avoids tool_use ID conflict by executing one tool at a time.

The tool_use ID conflict bug occurs when Claude CLI makes parallel tool calls internally.
This executor:
1. Uses --output-format json to capture structured responses
2. Detects tool_use requests in the response
3. Executes ONE tool at a time
4. Continues the conversation with tool results
5. Repeats until no more tool calls needed

This approach avoids the bug by never allowing parallel tool execution.
"""

import os
import sys
import json
import subprocess
import uuid
import sqlite3
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

DAEMON_DIR = Path(__file__).parent
PROJECT_DIR = DAEMON_DIR.parent
DB_PATH = DAEMON_DIR / "sequential_executor.db"
LOG_FILE = DAEMON_DIR / "sequential_executor.log"

# Configuration
CLAUDE_CMD = "claude"
MAX_ITERATIONS = 20  # Max tool calls per task to prevent infinite loops
TASK_TIMEOUT = 120  # seconds per CLI call

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def init_db():
    """Initialize database for tracking executions."""
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sequential_tasks (
            id TEXT PRIMARY KEY,
            prompt TEXT,
            status TEXT DEFAULT 'pending',
            iterations INTEGER DEFAULT 0,
            created_at TEXT,
            completed_at TEXT,
            final_result TEXT,
            error TEXT
        );

        CREATE TABLE IF NOT EXISTS tool_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT,
            iteration INTEGER,
            tool_name TEXT,
            tool_input TEXT,
            tool_result TEXT,
            timestamp TEXT
        );
    """)
    conn.commit()
    conn.close()


init_db()


@dataclass
class ToolCall:
    """Represents a tool call from Claude."""
    id: str
    name: str
    input: Dict[str, Any]


def parse_tool_calls(response_json: Dict) -> List[ToolCall]:
    """Extract tool calls from JSON response."""
    tool_calls = []

    # Response format can vary - handle different structures
    content = response_json.get('result', response_json)

    # Check for tool_use blocks in the content
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get('type') == 'tool_use':
                tool_calls.append(ToolCall(
                    id=block.get('id', str(uuid.uuid4())),
                    name=block.get('name', ''),
                    input=block.get('input', {})
                ))
    elif isinstance(content, dict):
        # Single content block
        if content.get('type') == 'tool_use':
            tool_calls.append(ToolCall(
                id=content.get('id', str(uuid.uuid4())),
                name=content.get('name', ''),
                input=content.get('input', {})
            ))
        # Check nested content
        for block in content.get('content', []):
            if isinstance(block, dict) and block.get('type') == 'tool_use':
                tool_calls.append(ToolCall(
                    id=block.get('id', str(uuid.uuid4())),
                    name=block.get('name', ''),
                    input=block.get('input', {})
                ))

    return tool_calls


def extract_text_response(response_json: Dict) -> str:
    """Extract text content from JSON response."""
    content = response_json.get('result', response_json)

    if isinstance(content, str):
        return content

    texts = []
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get('type') == 'text':
                texts.append(block.get('text', ''))
    elif isinstance(content, dict):
        if content.get('type') == 'text':
            texts.append(content.get('text', ''))
        for block in content.get('content', []):
            if isinstance(block, dict) and block.get('type') == 'text':
                texts.append(block.get('text', ''))

    return '\n'.join(texts) if texts else str(content)


def execute_tool_locally(tool: ToolCall) -> Dict[str, Any]:
    """
    Execute a tool call locally and return the result.

    This handles basic tools that we can safely execute:
    - Bash: Run shell commands
    - Read: Read file contents
    - Glob: Find files
    - Grep: Search files

    For complex tools, we pass them back to Claude.
    """
    result = {"type": "tool_result", "tool_use_id": tool.id}

    try:
        if tool.name == "Bash":
            cmd = tool.input.get("command", "")
            timeout = min(tool.input.get("timeout", 30000) / 1000, 60)  # Max 60s

            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(PROJECT_DIR),
                encoding='utf-8',
                errors='replace'
            )

            output = proc.stdout
            if proc.returncode != 0 and proc.stderr:
                output += f"\n[stderr]: {proc.stderr}"

            result["content"] = output[:10000]  # Truncate large outputs

        elif tool.name == "Read":
            file_path = tool.input.get("file_path", "")
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                result["content"] = content[:50000]  # Truncate very large files
            except Exception as e:
                result["content"] = f"Error reading file: {e}"
                result["is_error"] = True

        elif tool.name == "Glob":
            pattern = tool.input.get("pattern", "")
            path = tool.input.get("path", str(PROJECT_DIR))

            from pathlib import Path
            matches = list(Path(path).glob(pattern))[:100]  # Limit results
            result["content"] = "\n".join(str(m) for m in matches) or "No matches found"

        elif tool.name == "Grep":
            # Use ripgrep if available, fall back to grep
            pattern = tool.input.get("pattern", "")
            path = tool.input.get("path", str(PROJECT_DIR))

            try:
                proc = subprocess.run(
                    ["rg", "--no-heading", "-n", pattern, path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    encoding='utf-8',
                    errors='replace'
                )
                result["content"] = proc.stdout[:20000] or "No matches found"
            except Exception:
                result["content"] = f"Grep not available for pattern: {pattern}"
                result["is_error"] = True

        elif tool.name == "Write":
            file_path = tool.input.get("file_path", "")
            content = tool.input.get("content", "")

            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            result["content"] = f"Successfully wrote {len(content)} bytes to {file_path}"

        elif tool.name == "Edit":
            file_path = tool.input.get("file_path", "")
            old_string = tool.input.get("old_string", "")
            new_string = tool.input.get("new_string", "")

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if old_string not in content:
                result["content"] = f"Error: old_string not found in {file_path}"
                result["is_error"] = True
            else:
                new_content = content.replace(old_string, new_string, 1)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                result["content"] = f"Successfully edited {file_path}"

        else:
            # Unknown tool - return error so Claude can handle
            result["content"] = f"Tool '{tool.name}' not supported in sequential mode"
            result["is_error"] = True

    except subprocess.TimeoutExpired:
        result["content"] = "Command timed out"
        result["is_error"] = True
    except Exception as e:
        result["content"] = f"Error executing {tool.name}: {str(e)}"
        result["is_error"] = True

    return result


class SequentialExecutor:
    """Execute tasks with sequential tool handling."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.iteration = 0
        self.tool_results: List[Dict] = []

    def execute(self, prompt: str, task_id: Optional[str] = None) -> str:
        """
        Execute a prompt with sequential tool handling.

        Returns the final text response after all tool calls are resolved.
        """
        task_id = task_id or f"seq_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.iteration = 0
        accumulated_text = []

        logger.info(f"Starting sequential execution: {task_id}")
        self._record_task(task_id, prompt)

        current_prompt = prompt

        while self.iteration < MAX_ITERATIONS:
            self.iteration += 1
            logger.info(f"Iteration {self.iteration}/{MAX_ITERATIONS}")

            # Build command
            cmd = self._build_command(current_prompt)

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=TASK_TIMEOUT,
                    cwd=str(PROJECT_DIR),
                    encoding='utf-8',
                    errors='replace'
                )

                if result.returncode != 0:
                    # Check for the tool_use ID error
                    if "tool_use" in result.stdout and "unique" in result.stdout:
                        logger.warning("Got tool_use ID conflict - trying simpler prompt")
                        # Try with a more explicit "one step at a time" instruction
                        current_prompt = f"Do exactly ONE action, then stop and report: {prompt}"
                        continue

                    logger.error(f"CLI error: {result.stdout[:500]}")
                    self._update_task(task_id, 'failed', error=result.stdout[:1000])
                    return f"Error: {result.stdout[:500]}"

                # Parse the response
                try:
                    response = json.loads(result.stdout)
                except json.JSONDecodeError:
                    # Plain text response - we're done
                    accumulated_text.append(result.stdout)
                    self._update_task(task_id, 'complete', result=result.stdout)
                    return result.stdout

                # Extract text and tool calls
                text = extract_text_response(response)
                if text:
                    accumulated_text.append(text)

                tool_calls = parse_tool_calls(response)

                if not tool_calls:
                    # No more tool calls - we're done
                    final_result = '\n'.join(accumulated_text)
                    self._update_task(task_id, 'complete', result=final_result)
                    logger.info(f"Completed after {self.iteration} iterations")
                    return final_result

                # Execute ONE tool (sequential!)
                tool = tool_calls[0]
                logger.info(f"Executing tool: {tool.name}")

                tool_result = execute_tool_locally(tool)
                self._record_tool(task_id, tool, tool_result)

                # Build continuation prompt with tool result
                current_prompt = self._build_continuation(tool, tool_result)

            except subprocess.TimeoutExpired:
                logger.error("CLI timeout")
                self._update_task(task_id, 'failed', error="Timeout")
                return "Error: Task timed out"
            except Exception as e:
                logger.error(f"Execution error: {e}")
                self._update_task(task_id, 'failed', error=str(e))
                return f"Error: {e}"

        # Max iterations reached
        final_result = '\n'.join(accumulated_text) + "\n[Max iterations reached]"
        self._update_task(task_id, 'complete', result=final_result)
        return final_result

    def _build_command(self, prompt: str) -> List[str]:
        """Build CLI command for this iteration."""
        cmd = [
            CLAUDE_CMD,
            "--print",
            "--output-format", "json",
            "--permission-mode", "bypassPermissions",
            "--session-id", self.session_id,
            "--system-prompt", "Execute ONE tool at a time. After each tool, stop and report the result. Do not make parallel tool calls.",
        ]

        if self.iteration == 1:
            # First iteration - fresh start
            cmd.extend(["--no-session-persistence"])
        else:
            # Continuation - resume session
            cmd.extend(["--continue"])

        cmd.extend(["--", prompt])
        return cmd

    def _build_continuation(self, tool: ToolCall, result: Dict) -> str:
        """Build continuation prompt with tool result."""
        result_text = result.get("content", "")
        is_error = result.get("is_error", False)

        if is_error:
            return f"Tool {tool.name} returned an error: {result_text}\n\nPlease handle this error or try a different approach."
        else:
            return f"Tool {tool.name} completed successfully.\n\nResult:\n{result_text[:5000]}\n\nContinue with the next step, or provide the final answer if done."

    def _record_task(self, task_id: str, prompt: str):
        """Record task in database."""
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT OR REPLACE INTO sequential_tasks (id, prompt, status, created_at)
            VALUES (?, ?, 'running', ?)
        """, (task_id, prompt, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def _update_task(self, task_id: str, status: str, result: str = None, error: str = None):
        """Update task status."""
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            UPDATE sequential_tasks
            SET status = ?, iterations = ?, completed_at = ?, final_result = ?, error = ?
            WHERE id = ?
        """, (status, self.iteration, datetime.now().isoformat(), result, error, task_id))
        conn.commit()
        conn.close()

    def _record_tool(self, task_id: str, tool: ToolCall, result: Dict):
        """Record tool execution."""
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO tool_executions (task_id, iteration, tool_name, tool_input, tool_result, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            task_id,
            self.iteration,
            tool.name,
            json.dumps(tool.input)[:2000],
            json.dumps(result)[:5000],
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()


def main():
    """CLI interface for sequential executor."""
    import argparse
    parser = argparse.ArgumentParser(description='Sequential Executor - avoids tool_use ID conflicts')
    parser.add_argument('action', choices=['run', 'test', 'status'])
    parser.add_argument('--prompt', '-p', type=str, help='Prompt to execute')
    parser.add_argument('--task-id', type=str, help='Task ID to check status')

    args = parser.parse_args()

    if args.action == 'run':
        if not args.prompt:
            print("Error: --prompt required")
            sys.exit(1)

        executor = SequentialExecutor()
        result = executor.execute(args.prompt)
        print("\n=== Result ===")
        print(result)

    elif args.action == 'test':
        # Test with a simple tool-using task
        executor = SequentialExecutor()
        result = executor.execute("List the Python files in the daemon directory")
        print("\n=== Test Result ===")
        print(result)

    elif args.action == 'status':
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("""
            SELECT id, status, iterations, created_at
            FROM sequential_tasks
            ORDER BY created_at DESC
            LIMIT 10
        """)
        print("\nRecent tasks:")
        for row in cursor.fetchall():
            print(f"  {row[0][:12]}... | {row[1]} | {row[2]} iters | {row[3]}")
        conn.close()


if __name__ == "__main__":
    main()
