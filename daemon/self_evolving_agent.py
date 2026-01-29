#!/usr/bin/env python3
"""
Self-Evolving Agent - Adaptive workflow and prompt optimization

Based on: EvoAgentX (https://github.com/Shubhamsaboo/awesome-llm-apps/tree/main/advanced_ai_agents/multi_agent_apps/ai_Self-Evolving_agent)

Key concepts integrated:
1. WorkFlow Generation - Transform goals into executable agent workflows
2. Agent Management - Coordinate multiple specialized agents
3. Prompt Refinement - Gradient-based prompt optimization (TextGrad pattern)
4. Workflow Evolution - Optimize both prompts and workflow structure (AFlow pattern)

Usage:
    from self_evolving_agent import SelfEvolvingAgent, Workflow, WorkflowNode

    agent = SelfEvolvingAgent()
    workflow = agent.generate_workflow("Analyze this codebase and fix bugs")
    result = agent.execute(workflow)

    # After execution, optimize based on outcomes
    agent.evolve(workflow, feedback="success")
"""

import os
import sys
import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

DAEMON_DIR = Path(__file__).parent
sys.path.insert(0, str(DAEMON_DIR))

# Graceful imports
try:
    from outcome_tracker import record_outcome, get_outcomes
    OUTCOME_TRACKER_AVAILABLE = True
except ImportError:
    OUTCOME_TRACKER_AVAILABLE = False

try:
    from strategy_evolution import StrategyEvolver
    STRATEGY_EVOLUTION_AVAILABLE = True
except ImportError:
    STRATEGY_EVOLUTION_AVAILABLE = False

try:
    from model_router import ModelRouter, classify_task
    MODEL_ROUTER_AVAILABLE = True
except ImportError:
    MODEL_ROUTER_AVAILABLE = False

EVOLVING_DB = DAEMON_DIR / "evolving_agent.db"


# ============================================================================
# Data Structures
# ============================================================================

class NodeType(str, Enum):
    """Types of workflow nodes."""
    AGENT = "agent"          # Delegate to specialized agent
    TOOL = "tool"            # Use a specific tool
    LLM = "llm"              # Direct LLM call
    CONDITION = "condition"  # Branching logic
    PARALLEL = "parallel"    # Execute children in parallel
    SEQUENCE = "sequence"    # Execute children in sequence


@dataclass
class WorkflowNode:
    """Single node in a workflow graph."""
    id: str
    type: NodeType
    name: str
    prompt: str                    # The instruction/prompt for this node
    dependencies: List[str] = field(default_factory=list)  # Node IDs this depends on
    agent_type: Optional[str] = None  # For AGENT nodes
    tool_name: Optional[str] = None   # For TOOL nodes
    children: List[str] = field(default_factory=list)      # For PARALLEL/SEQUENCE
    condition: Optional[str] = None   # For CONDITION nodes

    # Evolution tracking
    version: int = 1
    fitness: float = 0.5
    execution_count: int = 0
    success_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "prompt": self.prompt,
            "dependencies": self.dependencies,
            "agent_type": self.agent_type,
            "tool_name": self.tool_name,
            "children": self.children,
            "condition": self.condition,
            "version": self.version,
            "fitness": self.fitness,
            "execution_count": self.execution_count,
            "success_count": self.success_count
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'WorkflowNode':
        return cls(
            id=data["id"],
            type=NodeType(data["type"]),
            name=data["name"],
            prompt=data["prompt"],
            dependencies=data.get("dependencies", []),
            agent_type=data.get("agent_type"),
            tool_name=data.get("tool_name"),
            children=data.get("children", []),
            condition=data.get("condition"),
            version=data.get("version", 1),
            fitness=data.get("fitness", 0.5),
            execution_count=data.get("execution_count", 0),
            success_count=data.get("success_count", 0)
        )


@dataclass
class Workflow:
    """Complete workflow graph."""
    id: str
    goal: str
    nodes: Dict[str, WorkflowNode]  # id -> node
    entry_nodes: List[str]          # Starting nodes (no dependencies)

    # Metadata
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    fitness: float = 0.5
    execution_count: int = 0
    success_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "goal": self.goal,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "entry_nodes": self.entry_nodes,
            "version": self.version,
            "created_at": self.created_at,
            "fitness": self.fitness,
            "execution_count": self.execution_count,
            "success_count": self.success_count
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Workflow':
        return cls(
            id=data["id"],
            goal=data["goal"],
            nodes={k: WorkflowNode.from_dict(v) for k, v in data["nodes"].items()},
            entry_nodes=data["entry_nodes"],
            version=data.get("version", 1),
            created_at=data.get("created_at", datetime.now().isoformat()),
            fitness=data.get("fitness", 0.5),
            execution_count=data.get("execution_count", 0),
            success_count=data.get("success_count", 0)
        )

    def save(self, path: Path):
        """Save workflow to JSON file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> 'Workflow':
        """Load workflow from JSON file."""
        with open(path) as f:
            return cls.from_dict(json.load(f))


# ============================================================================
# Workflow Templates (Pre-defined patterns)
# ============================================================================

WORKFLOW_TEMPLATES = {
    "code_analysis": {
        "description": "Analyze codebase and generate insights",
        "nodes": [
            {"id": "explore", "type": "agent", "agent_type": "scout",
             "prompt": "Explore the codebase structure and identify key components"},
            {"id": "analyze", "type": "agent", "agent_type": "architect",
             "prompt": "Analyze architecture patterns and dependencies",
             "dependencies": ["explore"]},
            {"id": "report", "type": "llm",
             "prompt": "Generate comprehensive analysis report",
             "dependencies": ["analyze"]}
        ]
    },
    "bug_fix": {
        "description": "Investigate and fix bugs",
        "nodes": [
            {"id": "investigate", "type": "agent", "agent_type": "sleuth",
             "prompt": "Investigate the root cause of the issue"},
            {"id": "plan", "type": "agent", "agent_type": "architect",
             "prompt": "Plan the fix approach",
             "dependencies": ["investigate"]},
            {"id": "implement", "type": "agent", "agent_type": "kraken",
             "prompt": "Implement the fix using TDD",
             "dependencies": ["plan"]},
            {"id": "verify", "type": "agent", "agent_type": "arbiter",
             "prompt": "Run tests and verify the fix",
             "dependencies": ["implement"]}
        ]
    },
    "feature_build": {
        "description": "Build a new feature end-to-end",
        "nodes": [
            {"id": "research", "type": "agent", "agent_type": "oracle",
             "prompt": "Research best practices and patterns"},
            {"id": "design", "type": "agent", "agent_type": "architect",
             "prompt": "Design the feature architecture",
             "dependencies": ["research"]},
            {"id": "implement", "type": "agent", "agent_type": "kraken",
             "prompt": "Implement the feature",
             "dependencies": ["design"]},
            {"id": "test", "type": "agent", "agent_type": "arbiter",
             "prompt": "Write and run tests",
             "dependencies": ["implement"]},
            {"id": "review", "type": "agent", "agent_type": "critic",
             "prompt": "Code review and refinement",
             "dependencies": ["test"]}
        ]
    }
}


# ============================================================================
# Database
# ============================================================================

def init_db():
    """Initialize the self-evolving agent database."""
    conn = sqlite3.connect(EVOLVING_DB)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS workflows (
            id TEXT PRIMARY KEY,
            goal TEXT,
            workflow_json TEXT,
            version INTEGER DEFAULT 1,
            fitness REAL DEFAULT 0.5,
            execution_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS prompt_versions (
            id TEXT PRIMARY KEY,
            node_id TEXT,
            workflow_id TEXT,
            prompt_text TEXT,
            version INTEGER,
            fitness REAL DEFAULT 0.5,
            execution_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            parent_version TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS execution_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workflow_id TEXT,
            node_id TEXT,
            input_data TEXT,
            output_data TEXT,
            success INTEGER,
            latency_ms INTEGER,
            feedback TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS evolution_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workflow_id TEXT,
            evolution_type TEXT,  -- 'prompt_refine', 'workflow_restructure', 'node_replace'
            old_value TEXT,
            new_value TEXT,
            reason TEXT,
            fitness_before REAL,
            fitness_after REAL,
            created_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_workflow_fitness ON workflows(fitness DESC);
        CREATE INDEX IF NOT EXISTS idx_prompt_fitness ON prompt_versions(fitness DESC);
        CREATE INDEX IF NOT EXISTS idx_exec_workflow ON execution_logs(workflow_id);
    """)
    conn.commit()
    conn.close()


# Initialize on import
init_db()


# ============================================================================
# Prompt Evolution (TextGrad pattern)
# ============================================================================

class PromptEvolver:
    """
    Evolves prompts based on execution feedback.

    Implements TextGrad-like gradient descent on prompts:
    - Good outcomes → reinforce successful patterns
    - Bad outcomes → modify problematic patterns
    """

    def __init__(self):
        self.conn = sqlite3.connect(EVOLVING_DB)

    def refine_prompt(self, node_id: str, workflow_id: str,
                      original_prompt: str, feedback: str,
                      success: bool) -> str:
        """
        Refine a prompt based on execution feedback.

        Uses pattern-based modification instead of actual gradients.
        """
        # Record current version
        version = self._get_current_version(node_id, workflow_id)

        if success:
            # Reinforce: Store successful prompt version
            self._record_success(node_id, workflow_id, original_prompt, version)
            return original_prompt

        # Failure: Generate refined prompt
        refined = self._apply_refinements(original_prompt, feedback)

        # Store new version
        new_version = version + 1
        self._store_version(node_id, workflow_id, refined, new_version, original_prompt)

        return refined

    def _get_current_version(self, node_id: str, workflow_id: str) -> int:
        cursor = self.conn.execute("""
            SELECT MAX(version) FROM prompt_versions
            WHERE node_id = ? AND workflow_id = ?
        """, (node_id, workflow_id))
        row = cursor.fetchone()
        return row[0] if row[0] else 0

    def _record_success(self, node_id: str, workflow_id: str,
                        prompt: str, version: int):
        """Record successful prompt execution."""
        self.conn.execute("""
            INSERT OR REPLACE INTO prompt_versions
            (id, node_id, workflow_id, prompt_text, version, success_count,
             execution_count, fitness, created_at)
            VALUES (?, ?, ?, ?, ?,
                    COALESCE((SELECT success_count FROM prompt_versions WHERE id = ?), 0) + 1,
                    COALESCE((SELECT execution_count FROM prompt_versions WHERE id = ?), 0) + 1,
                    COALESCE((SELECT fitness FROM prompt_versions WHERE id = ?), 0.5) + 0.05,
                    ?)
        """, (
            f"{node_id}_{workflow_id}_v{version}",
            node_id, workflow_id, prompt, version,
            f"{node_id}_{workflow_id}_v{version}",
            f"{node_id}_{workflow_id}_v{version}",
            f"{node_id}_{workflow_id}_v{version}",
            datetime.now().isoformat()
        ))
        self.conn.commit()

    def _apply_refinements(self, prompt: str, feedback: str) -> str:
        """
        Apply heuristic refinements to prompt based on feedback.

        In production, this would use LLM-based refinement.
        """
        refinements = []

        # Pattern-based refinements
        feedback_lower = feedback.lower()

        if "unclear" in feedback_lower or "ambiguous" in feedback_lower:
            refinements.append("Be more specific and explicit in instructions.")

        if "missing" in feedback_lower or "incomplete" in feedback_lower:
            refinements.append("Ensure all required information is included.")

        if "error" in feedback_lower or "failed" in feedback_lower:
            refinements.append("Include error handling considerations.")

        if "slow" in feedback_lower or "timeout" in feedback_lower:
            refinements.append("Focus on efficiency and early termination.")

        if refinements:
            return f"{prompt}\n\nAdditional guidelines:\n" + "\n".join(f"- {r}" for r in refinements)

        return prompt

    def _store_version(self, node_id: str, workflow_id: str,
                       prompt: str, version: int, parent_prompt: str):
        """Store new prompt version."""
        version_id = f"{node_id}_{workflow_id}_v{version}"
        parent_id = f"{node_id}_{workflow_id}_v{version-1}" if version > 1 else None

        self.conn.execute("""
            INSERT INTO prompt_versions
            (id, node_id, workflow_id, prompt_text, version, parent_version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (version_id, node_id, workflow_id, prompt, version, parent_id,
              datetime.now().isoformat()))
        self.conn.commit()

    def get_best_prompt(self, node_id: str, workflow_id: str,
                        default_prompt: str) -> str:
        """Get the highest-fitness prompt for a node."""
        cursor = self.conn.execute("""
            SELECT prompt_text FROM prompt_versions
            WHERE node_id = ? AND workflow_id = ?
            ORDER BY fitness DESC, version DESC
            LIMIT 1
        """, (node_id, workflow_id))
        row = cursor.fetchone()
        return row[0] if row else default_prompt


# ============================================================================
# Workflow Evolution (AFlow pattern)
# ============================================================================

class WorkflowEvolver:
    """
    Evolves workflow structure based on execution patterns.

    Implements AFlow-like optimization:
    - Successful patterns → expand and reuse
    - Failing patterns → restructure or bypass
    """

    def __init__(self):
        self.conn = sqlite3.connect(EVOLVING_DB)

    def evolve_workflow(self, workflow: Workflow,
                        execution_results: Dict[str, bool]) -> Workflow:
        """
        Evolve workflow based on node execution results.

        Args:
            workflow: Current workflow
            execution_results: {node_id: success} mapping
        """
        # Calculate node-level fitness
        for node_id, success in execution_results.items():
            if node_id in workflow.nodes:
                node = workflow.nodes[node_id]
                node.execution_count += 1
                if success:
                    node.success_count += 1
                node.fitness = node.success_count / max(node.execution_count, 1)

        # Identify problematic nodes (fitness < 0.3 after 3+ executions)
        problem_nodes = [
            node_id for node_id, node in workflow.nodes.items()
            if node.execution_count >= 3 and node.fitness < 0.3
        ]

        # Restructure if needed
        if problem_nodes:
            workflow = self._restructure_workflow(workflow, problem_nodes)
            workflow.version += 1

        # Update overall fitness
        workflow.execution_count += 1
        if all(execution_results.values()):
            workflow.success_count += 1
        workflow.fitness = workflow.success_count / max(workflow.execution_count, 1)

        # Persist
        self._save_workflow(workflow)

        return workflow

    def _restructure_workflow(self, workflow: Workflow,
                              problem_nodes: List[str]) -> Workflow:
        """Restructure workflow to address problem nodes."""
        for node_id in problem_nodes:
            node = workflow.nodes[node_id]

            # Strategy 1: Add a preparation node
            if node.type == NodeType.AGENT:
                prep_id = f"prep_{node_id}"
                prep_node = WorkflowNode(
                    id=prep_id,
                    type=NodeType.LLM,
                    name=f"Prepare for {node.name}",
                    prompt=f"Prepare context and requirements for: {node.prompt}",
                    dependencies=node.dependencies
                )
                # Insert prep node
                workflow.nodes[prep_id] = prep_node
                node.dependencies = [prep_id]

            # Strategy 2: Log the evolution
            self._record_evolution(
                workflow.id, "node_restructure",
                f"Added preparation for {node_id}",
                f"Node {node_id} had fitness {node.fitness:.2f}"
            )

        return workflow

    def _save_workflow(self, workflow: Workflow):
        """Save workflow to database."""
        self.conn.execute("""
            INSERT OR REPLACE INTO workflows
            (id, goal, workflow_json, version, fitness, execution_count,
             success_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            workflow.id, workflow.goal, json.dumps(workflow.to_dict()),
            workflow.version, workflow.fitness, workflow.execution_count,
            workflow.success_count, workflow.created_at, datetime.now().isoformat()
        ))
        self.conn.commit()

    def _record_evolution(self, workflow_id: str, evolution_type: str,
                          new_value: str, reason: str):
        """Record evolution step in history."""
        self.conn.execute("""
            INSERT INTO evolution_history
            (workflow_id, evolution_type, new_value, reason, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (workflow_id, evolution_type, new_value, reason,
              datetime.now().isoformat()))
        self.conn.commit()

    def get_similar_workflows(self, goal: str, limit: int = 3) -> List[Workflow]:
        """Find workflows with similar goals (for transfer learning)."""
        # Simple keyword matching (would use embeddings in production)
        keywords = set(goal.lower().split())

        cursor = self.conn.execute("""
            SELECT workflow_json FROM workflows
            WHERE fitness > 0.5
            ORDER BY fitness DESC, execution_count DESC
            LIMIT ?
        """, (limit * 3,))  # Get more, then filter

        results = []
        for row in cursor.fetchall():
            wf = Workflow.from_dict(json.loads(row[0]))
            wf_keywords = set(wf.goal.lower().split())
            if keywords & wf_keywords:  # Intersection
                results.append(wf)
                if len(results) >= limit:
                    break

        return results


# ============================================================================
# Self-Evolving Agent
# ============================================================================

class SelfEvolvingAgent:
    """
    Main agent class implementing self-evolution patterns.

    Combines:
    - Workflow generation from goals
    - Agent coordination and execution
    - Prompt evolution (TextGrad)
    - Workflow evolution (AFlow)
    """

    def __init__(self):
        self.prompt_evolver = PromptEvolver()
        self.workflow_evolver = WorkflowEvolver()
        self.conn = sqlite3.connect(EVOLVING_DB)

    def generate_workflow(self, goal: str,
                          template: Optional[str] = None) -> Workflow:
        """
        Generate a workflow from a natural language goal.

        Args:
            goal: Natural language description of the objective
            template: Optional template name to use as base
        """
        # Check for existing similar workflows
        similar = self.workflow_evolver.get_similar_workflows(goal)
        if similar:
            # Adapt best similar workflow
            base = similar[0]
            workflow_id = hashlib.md5(f"{goal}_{datetime.now()}".encode()).hexdigest()[:12]
            return Workflow(
                id=workflow_id,
                goal=goal,
                nodes={k: WorkflowNode(
                    id=k, type=v.type, name=v.name,
                    prompt=v.prompt.replace(base.goal, goal),
                    dependencies=v.dependencies,
                    agent_type=v.agent_type,
                    tool_name=v.tool_name
                ) for k, v in base.nodes.items()},
                entry_nodes=base.entry_nodes
            )

        # Use template if specified
        if template and template in WORKFLOW_TEMPLATES:
            return self._from_template(goal, template)

        # Auto-detect template from goal
        template = self._detect_template(goal)
        if template:
            return self._from_template(goal, template)

        # Generate default single-node workflow
        workflow_id = hashlib.md5(f"{goal}_{datetime.now()}".encode()).hexdigest()[:12]
        return Workflow(
            id=workflow_id,
            goal=goal,
            nodes={
                "main": WorkflowNode(
                    id="main",
                    type=NodeType.LLM,
                    name="Execute Goal",
                    prompt=goal
                )
            },
            entry_nodes=["main"]
        )

    def _from_template(self, goal: str, template_name: str) -> Workflow:
        """Create workflow from template."""
        template = WORKFLOW_TEMPLATES[template_name]
        workflow_id = hashlib.md5(f"{goal}_{datetime.now()}".encode()).hexdigest()[:12]

        nodes = {}
        for node_data in template["nodes"]:
            node = WorkflowNode(
                id=node_data["id"],
                type=NodeType(node_data["type"]),
                name=node_data.get("name", node_data["id"]),
                prompt=node_data["prompt"],
                dependencies=node_data.get("dependencies", []),
                agent_type=node_data.get("agent_type"),
                tool_name=node_data.get("tool_name")
            )
            nodes[node.id] = node

        # Find entry nodes (no dependencies)
        entry_nodes = [n.id for n in nodes.values() if not n.dependencies]

        return Workflow(
            id=workflow_id,
            goal=goal,
            nodes=nodes,
            entry_nodes=entry_nodes
        )

    def _detect_template(self, goal: str) -> Optional[str]:
        """Auto-detect best template from goal keywords."""
        goal_lower = goal.lower()

        if any(k in goal_lower for k in ["bug", "fix", "debug", "error"]):
            return "bug_fix"
        if any(k in goal_lower for k in ["analyze", "review", "audit"]):
            return "code_analysis"
        if any(k in goal_lower for k in ["build", "create", "implement", "add"]):
            return "feature_build"

        return None

    def execute(self, workflow: Workflow,
                context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a workflow and return results.

        Args:
            workflow: Workflow to execute
            context: Optional initial context
        """
        context = context or {}
        results = {}
        execution_results = {}

        # Topological execution order
        order = self._topological_sort(workflow)

        for node_id in order:
            node = workflow.nodes[node_id]

            # Get best prompt version
            prompt = self.prompt_evolver.get_best_prompt(
                node_id, workflow.id, node.prompt
            )

            # Execute node
            start_time = datetime.now()
            try:
                result = self._execute_node(node, prompt, context)
                success = True
                context[node_id] = result
                results[node_id] = result
            except Exception as e:
                success = False
                results[node_id] = {"error": str(e)}

            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            execution_results[node_id] = success

            # Log execution
            self._log_execution(workflow.id, node_id, context, results[node_id],
                                success, latency_ms)

        # Evolve workflow based on results
        self.workflow_evolver.evolve_workflow(workflow, execution_results)

        return results

    def _execute_node(self, node: WorkflowNode, prompt: str,
                      context: Dict) -> Any:
        """Execute a single workflow node."""
        if node.type == NodeType.AGENT:
            # Would delegate to actual agent
            return {"agent": node.agent_type, "prompt": prompt, "status": "simulated"}

        elif node.type == NodeType.TOOL:
            # Would invoke actual tool
            return {"tool": node.tool_name, "prompt": prompt, "status": "simulated"}

        elif node.type == NodeType.LLM:
            # Would call LLM
            return {"llm_call": prompt, "context_keys": list(context.keys())}

        elif node.type == NodeType.CONDITION:
            # Evaluate condition
            return {"condition": node.condition, "result": True}

        elif node.type in (NodeType.PARALLEL, NodeType.SEQUENCE):
            # Container nodes - children would be executed
            return {"children": node.children, "status": "container"}

        return {"unknown": node.type}

    def _topological_sort(self, workflow: Workflow) -> List[str]:
        """Sort nodes in execution order respecting dependencies."""
        visited = set()
        order = []

        def visit(node_id):
            if node_id in visited:
                return
            visited.add(node_id)
            node = workflow.nodes.get(node_id)
            if node:
                for dep in node.dependencies:
                    visit(dep)
            order.append(node_id)

        for node_id in workflow.nodes:
            visit(node_id)

        return order

    def _log_execution(self, workflow_id: str, node_id: str,
                       input_data: Dict, output_data: Any,
                       success: bool, latency_ms: int):
        """Log node execution."""
        self.conn.execute("""
            INSERT INTO execution_logs
            (workflow_id, node_id, input_data, output_data, success, latency_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            workflow_id, node_id,
            json.dumps(input_data, default=str),
            json.dumps(output_data, default=str),
            1 if success else 0, latency_ms,
            datetime.now().isoformat()
        ))
        self.conn.commit()

    def evolve(self, workflow: Workflow, feedback: str):
        """
        Explicitly evolve workflow based on user feedback.

        Args:
            workflow: Workflow to evolve
            feedback: "success", "failure", or detailed feedback
        """
        success = feedback.lower() in ["success", "good", "yes", "correct"]

        # Update workflow fitness
        workflow.execution_count += 1
        if success:
            workflow.success_count += 1
        workflow.fitness = workflow.success_count / max(workflow.execution_count, 1)

        # Evolve prompts for all nodes
        for node_id, node in workflow.nodes.items():
            self.prompt_evolver.refine_prompt(
                node_id, workflow.id, node.prompt, feedback, success
            )

        # Save evolved workflow
        self.workflow_evolver._save_workflow(workflow)

        # Record in outcome tracker if available
        if OUTCOME_TRACKER_AVAILABLE:
            record_outcome(
                f"workflow_{workflow.id}",
                "success" if success else "failure",
                {"feedback": feedback, "fitness": workflow.fitness}
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get agent evolution statistics."""
        cursor = self.conn.execute("""
            SELECT COUNT(*), AVG(fitness), MAX(fitness)
            FROM workflows
        """)
        row = cursor.fetchone()

        cursor = self.conn.execute("""
            SELECT COUNT(*), SUM(success)
            FROM execution_logs
        """)
        exec_row = cursor.fetchone()

        cursor = self.conn.execute("""
            SELECT evolution_type, COUNT(*)
            FROM evolution_history
            GROUP BY evolution_type
        """)
        evolutions = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            "workflows": row[0] or 0,
            "avg_fitness": round(row[1] or 0, 3),
            "max_fitness": round(row[2] or 0, 3),
            "total_executions": exec_row[0] or 0,
            "successful_executions": exec_row[1] or 0,
            "success_rate": round((exec_row[1] or 0) / max(exec_row[0] or 1, 1), 3),
            "evolutions": evolutions
        }


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Self-Evolving Agent")
    subparsers = parser.add_subparsers(dest="command")

    # Generate workflow
    gen_parser = subparsers.add_parser("generate", help="Generate workflow from goal")
    gen_parser.add_argument("goal", help="Goal description")
    gen_parser.add_argument("--template", help="Template to use")
    gen_parser.add_argument("--output", help="Output file path")

    # Execute workflow
    exec_parser = subparsers.add_parser("execute", help="Execute workflow")
    exec_parser.add_argument("workflow_file", help="Workflow JSON file")

    # Stats
    subparsers.add_parser("stats", help="Show evolution statistics")

    # List templates
    subparsers.add_parser("templates", help="List available templates")

    args = parser.parse_args()

    agent = SelfEvolvingAgent()

    if args.command == "generate":
        workflow = agent.generate_workflow(args.goal, args.template)
        if args.output:
            workflow.save(Path(args.output))
            print(f"Saved workflow to {args.output}")
        else:
            print(json.dumps(workflow.to_dict(), indent=2))

    elif args.command == "execute":
        workflow = Workflow.load(Path(args.workflow_file))
        results = agent.execute(workflow)
        print("Execution Results:")
        print(json.dumps(results, indent=2, default=str))

    elif args.command == "stats":
        stats = agent.get_stats()
        print("=== Self-Evolving Agent Statistics ===")
        print(f"Workflows: {stats['workflows']}")
        print(f"Avg Fitness: {stats['avg_fitness']}")
        print(f"Max Fitness: {stats['max_fitness']}")
        print(f"Success Rate: {stats['success_rate']*100:.1f}%")
        print(f"Evolutions: {stats['evolutions']}")

    elif args.command == "templates":
        print("Available Templates:")
        for name, template in WORKFLOW_TEMPLATES.items():
            print(f"\n  {name}: {template['description']}")
            for node in template['nodes']:
                deps = f" (depends: {node.get('dependencies', [])})" if node.get('dependencies') else ""
                print(f"    - {node['id']}: {node.get('agent_type', node['type'])}{deps}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
