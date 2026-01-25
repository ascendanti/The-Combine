#!/usr/bin/env python3
"""MCP Server - Expose daemon capabilities as MCP tools.

Enables other Claude instances and MCP clients to:
- Submit tasks to the queue
- Query goals and coherence
- Make decisions
- Search memory
- Check capabilities

Usage:
    python mcp_server.py

MCP Tools exposed:
    submit_task: Submit async task to queue
    query_goals: Get goal hierarchy
    evaluate_decision: Run decision analysis
    check_coherence: Validate action against goals
    search_memory: Query persistent memory
    get_capabilities: List assessed capabilities
"""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from task_queue import TaskQueue, TaskPriority
from coherence import GoalCoherenceLayer, GoalTimeframe
from registry import create_default_registry
from decisions import DecisionEngine, Criterion
from metacognition import MetaCognitionEngine
from memory import Memory


class MCPServer:
    """MCP-compatible tool server."""

    def __init__(self):
        self.queue = TaskQueue()
        self.coherence = GoalCoherenceLayer()
        self.registry = create_default_registry()
        self.decisions = DecisionEngine()
        self.metacog = MetaCognitionEngine()
        self.memory = Memory()

        # Tool definitions (MCP format)
        self.tools = [
            {
                "name": "submit_task",
                "description": "Submit an async task to the daemon queue for processing",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "Task prompt/description"},
                        "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]},
                        "metadata": {"type": "object", "description": "Optional metadata"}
                    },
                    "required": ["prompt"]
                }
            },
            {
                "name": "query_goals",
                "description": "Get the goal hierarchy and constraints",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "root_id": {"type": "string", "description": "Start from specific goal"}
                    }
                }
            },
            {
                "name": "add_goal",
                "description": "Add a new goal to the hierarchy",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "timeframe": {"type": "string", "enum": ["long", "medium", "short", "task"]},
                        "domains": {"type": "array", "items": {"type": "string"}},
                        "parent_id": {"type": "string"}
                    },
                    "required": ["title"]
                }
            },
            {
                "name": "evaluate_decision",
                "description": "Evaluate a decision using multi-criteria analysis",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Decision title"},
                        "criteria": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "weight": {"type": "number"},
                                    "score": {"type": "number"},
                                    "confidence": {"type": "number"}
                                }
                            }
                        },
                        "context": {"type": "string"},
                        "risk_aversion": {"type": "number"}
                    },
                    "required": ["title", "criteria"]
                }
            },
            {
                "name": "check_coherence",
                "description": "Check if an action is coherent with goals and constraints",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string"},
                        "action": {"type": "object"}
                    },
                    "required": ["domain", "action"]
                }
            },
            {
                "name": "search_memory",
                "description": "Search persistent memory for relevant information",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "k": {"type": "integer", "default": 5}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "add_memory",
                "description": "Store information in persistent memory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "metadata": {"type": "object"}
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "get_capabilities",
                "description": "List assessed capabilities and their levels",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_calibration",
                "description": "Get confidence calibration metrics",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string"}
                    }
                }
            },
            {
                "name": "get_unified_context",
                "description": "Get context from all registered domain modules",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

    def handle_request(self, method: str, params: dict = None) -> dict:
        """Handle MCP request."""
        params = params or {}

        if method == "initialize":
            return {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "claude-daemon",
                    "version": "1.0.0"
                }
            }

        elif method == "tools/list":
            return {"tools": self.tools}

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            return self._call_tool(tool_name, arguments)

        else:
            return {"error": f"Unknown method: {method}"}

    def _call_tool(self, name: str, args: dict) -> dict:
        """Execute a tool call."""
        try:
            if name == "submit_task":
                priority_map = {
                    "low": TaskPriority.LOW, "normal": TaskPriority.NORMAL,
                    "high": TaskPriority.HIGH, "urgent": TaskPriority.URGENT
                }
                task = self.queue.add_task(
                    args["prompt"],
                    priority_map.get(args.get("priority", "normal"), TaskPriority.NORMAL),
                    args.get("metadata", {})
                )
                return {"content": [{"type": "text", "text": f"Task queued: {task.id}"}]}

            elif name == "query_goals":
                goals = self.coherence.get_goal_hierarchy(args.get("root_id"))
                return {"content": [{"type": "text", "text": json.dumps([g.to_dict() for g in goals], indent=2)}]}

            elif name == "add_goal":
                goal = self.coherence.add_goal(
                    title=args["title"],
                    description=args.get("description", ""),
                    timeframe=GoalTimeframe(args.get("timeframe", "medium")),
                    domains=args.get("domains", []),
                    parent_id=args.get("parent_id")
                )
                return {"content": [{"type": "text", "text": f"Goal created: {goal.id}"}]}

            elif name == "evaluate_decision":
                criteria = [
                    Criterion(c["name"], c["weight"], c["score"], c.get("confidence", 0.7))
                    for c in args["criteria"]
                ]
                decision = self.decisions.evaluate(
                    args["title"], criteria,
                    args.get("context", ""),
                    args.get("risk_aversion", 0.5)
                )
                return {"content": [{"type": "text", "text": json.dumps({
                    "id": decision.id,
                    "expected_value": decision.expected_value,
                    "risk_adjusted": decision.risk_adjusted_value,
                    "confidence": decision.confidence_level.value,
                    "recommendation": decision.recommendation
                }, indent=2)}]}

            elif name == "check_coherence":
                valid, issues = self.registry.check_action(args["domain"], args["action"])
                return {"content": [{"type": "text", "text": json.dumps({
                    "valid": valid, "issues": issues
                })}]}

            elif name == "search_memory":
                # Use correct Memory API: recall_learnings(query, k)
                learnings = self.memory.recall_learnings(args["query"], k=args.get("k", 5))
                results = [l.to_dict() for l in learnings]
                return {"content": [{"type": "text", "text": json.dumps(results, indent=2)}]}

            elif name == "add_memory":
                # Use correct Memory API: store_learning(content, context, tags, confidence)
                metadata = args.get("metadata", {})
                learning = self.memory.store_learning(
                    content=args["content"],
                    context=metadata.get('context', ''),
                    tags=metadata.get('tags', []),
                    confidence=metadata.get('confidence', 'medium')
                )
                return {"content": [{"type": "text", "text": f"Memory stored: {learning.id}"}]}

            elif name == "get_capabilities":
                caps = self.metacog.get_capabilities()
                return {"content": [{"type": "text", "text": json.dumps([{
                    "capability": c.capability,
                    "level": c.level.value,
                    "limitations": c.limitations
                } for c in caps], indent=2)}]}

            elif name == "get_calibration":
                result = self.metacog.get_calibration(args.get("domain"))
                return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

            elif name == "get_unified_context":
                context = self.registry.get_unified_context()
                return {"content": [{"type": "text", "text": json.dumps(context, indent=2)}]}

            else:
                return {"error": {"code": -32601, "message": f"Unknown tool: {name}"}}

        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def run_stdio(self):
        """Run as stdio MCP server."""
        import sys

        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                request = json.loads(line)
                method = request.get("method", "")
                params = request.get("params", {})
                req_id = request.get("id")

                result = self.handle_request(method, params)

                response = {"jsonrpc": "2.0", "id": req_id}
                if "error" in result:
                    response["error"] = result["error"]
                else:
                    response["result"] = result

                print(json.dumps(response), flush=True)

            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": str(e)}
                }), flush=True)


if __name__ == "__main__":
    server = MCPServer()

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Test mode - show available tools
        print("Available MCP tools:")
        for tool in server.tools:
            print(f"  {tool['name']}: {tool['description']}")
    else:
        # Run as stdio server
        server.run_stdio()
