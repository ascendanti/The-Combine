#!/usr/bin/env python3
"""
Deterministic Router

Routes requests without LLM when possible:
1. Ultrawork mode detection → 2. Slash commands → 3. atlas_spine (rule-based)
4. capability registry lookup → 5. Task complexity analysis → 6. Claude

This is the core of the Tripartite Integration - routing 80%+ without LLM.

Integrations:
- oh-my-opencode: ultrawork/ulw keyword detection
- create-claude: /commit, /review, /test, etc. commands
- claude-code-buddy: task complexity scoring and workflow guidance
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass, field

PROJECT_ROOT = Path(__file__).parent.parent
CLAUDE_DIR = PROJECT_ROOT / ".claude"
CONFIG_DIR = CLAUDE_DIR / "config"


@dataclass
class RouteResult:
    """Result of routing decision."""
    target: str  # agent, skill, hook, or 'escalate'
    target_type: str  # 'agent', 'skill', 'hook', 'action', 'escalate', 'command'
    confidence: float  # 0.0 - 1.0
    reason: str
    model_tier: str = "claude"  # localai, codex, claude, haiku
    mode: str = "normal"  # normal, ultrawork
    complexity: int = 2  # 1-10 task complexity
    workflow_hint: str = ""  # Next step suggestion


class DeterministicRouter:
    """Routes requests deterministically when possible."""

    # Slash commands (from create-claude)
    SLASH_COMMANDS = {
        '/commit': {'target': 'commit', 'type': 'command', 'model': 'haiku', 'complexity': 2},
        '/explain': {'target': 'explain', 'type': 'command', 'model': 'claude', 'complexity': 3},
        '/fix': {'target': 'fix', 'type': 'command', 'model': 'claude', 'complexity': 4},
        '/optimize': {'target': 'optimize', 'type': 'command', 'model': 'claude', 'complexity': 5},
        '/pr': {'target': 'pr', 'type': 'command', 'model': 'claude', 'complexity': 3},
        '/review': {'target': 'review', 'type': 'command', 'model': 'claude', 'complexity': 4},
        '/test': {'target': 'test', 'type': 'command', 'model': 'claude', 'complexity': 3},
        '/validate': {'target': 'validate', 'type': 'command', 'model': 'claude', 'complexity': 3},
    }

    # Production agents (from create-claude)
    PRODUCTION_AGENTS = {
        'pre-commit': {'triggers': ['before commit', 'validate commit', 'check commit'], 'complexity': 4},
        'refactor': {'triggers': ['simplify', 'reduce complexity', 'clean up'], 'complexity': 5},
        'debugger': {'triggers': ['root cause', 'debug error', 'find bug'], 'complexity': 5},
    }

    # Task complexity keywords (from claude-code-buddy)
    COMPLEXITY_MODIFIERS = {
        'simple': -2, 'quick': -2, 'small': -1, 'minor': -1,
        'complex': 2, 'comprehensive': 2, 'complete': 1, 'full': 1,
        'architecture': 3, 'system': 2, 'refactor entire': 3,
    }

    # Rule-based patterns (atlas_spine operators)
    OPERATORS = {
        'LOOKUP': [
            r'\bwhere\s+is\b', r'\bfind\s+file\b', r'\blocate\b',
            r'\bwhich\s+file\b', r'\bpath\s+to\b'
        ],
        'OPEN': [
            r'\bread\b.*\bfile\b', r'\bopen\b', r'\bshow\s+me\b',
            r'\bdisplay\b', r'\bview\b'
        ],
        'DIAGNOSE': [
            r'\berror\b', r'\bfail', r'\bnot\s+working\b', r'\bbug\b',
            r'\bbroken\b', r'\bdebug\b', r'\bissue\b'
        ],
        'TEST': [
            r'\btest\b', r'\bverify\b', r'\bcheck\s+if\b', r'\bvalidate\b',
            r'\brun\s+tests?\b'
        ],
        'THINK': [
            r'\bplan\b', r'\barchitect', r'\bdesign\b', r'\bstrategy\b',
            r'\bdecide\b', r'\bshould\s+i\b', r'\bhow\s+should\b'
        ],
        'PATCH': [
            r'\bfix\b', r'\bchange\b', r'\bupdate\b', r'\bmodify\b',
            r'\bedit\b', r'\brefactor\b'
        ],
        'SEARCH': [
            r'\bsearch\b', r'\bgrep\b', r'\blook\s+for\b', r'\bfind\s+all\b'
        ],
        'RESEARCH': [
            r'\bresearch\b', r'\blearn\s+about\b', r'\bwhat\s+is\b',
            r'\bexplain\b', r'\bhow\s+does\b', r'\bwhy\s+does\b'
        ]
    }

    # Operator to agent/skill mapping
    OPERATOR_ROUTES = {
        'LOOKUP': ('scout', 'agent'),
        'OPEN': ('read', 'action'),
        'DIAGNOSE': ('sleuth', 'agent'),
        'TEST': ('arbiter', 'agent'),
        'THINK': ('architect', 'agent'),
        'PATCH': ('kraken', 'agent'),
        'SEARCH': ('scout', 'agent'),
        'RESEARCH': ('oracle', 'agent'),
    }

    def __init__(self):
        self.capabilities = self._load_capabilities()
        self.routing_index = self._load_routing_index()

    def _load_capabilities(self) -> dict:
        """Load capability registry."""
        path = CONFIG_DIR / "capabilities.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return {"capabilities": []}

    def _load_routing_index(self) -> dict:
        """Load routing index."""
        path = CONFIG_DIR / "routing_index.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return {}

    def route(self, query: str) -> RouteResult:
        """
        Route a query to the appropriate handler.

        Returns RouteResult with target, confidence, and model tier.
        """
        query_lower = query.lower().strip()

        # Calculate task complexity
        complexity = self._calculate_complexity(query_lower)

        # Check for ultrawork mode (from oh-my-opencode)
        ultrawork_mode = self._detect_ultrawork(query_lower)

        # Stage 0: Slash command detection (from create-claude)
        result = self._match_slash_command(query_lower)
        if result:
            result.complexity = complexity
            result.mode = "ultrawork" if ultrawork_mode else "normal"
            return result

        # Stage 1: Production agent matching (from create-claude)
        result = self._match_production_agent(query_lower)
        if result and result.confidence >= 0.8:
            result.complexity = complexity
            result.mode = "ultrawork" if ultrawork_mode else "normal"
            return result

        # Stage 2: Rule-based operator matching (highest confidence)
        result = self._match_operator(query_lower)
        if result and result.confidence >= 0.8:
            result.complexity = complexity
            result.mode = "ultrawork" if ultrawork_mode else "normal"
            return result

        # Stage 3: Capability registry keyword lookup
        result = self._match_capabilities(query_lower)
        if result and result.confidence >= 0.7:
            result.complexity = complexity
            result.mode = "ultrawork" if ultrawork_mode else "normal"
            return result

        # Stage 4: Domain inference
        result = self._infer_domain(query_lower)
        if result and result.confidence >= 0.6:
            result.complexity = complexity
            result.mode = "ultrawork" if ultrawork_mode else "normal"
            return result

        # Stage 5: Escalate to LLM classification
        return RouteResult(
            target='escalate',
            target_type='escalate',
            confidence=0.0,
            reason='No deterministic match found',
            model_tier='localai',  # Try LocalAI first for classification
            complexity=complexity,
            mode="ultrawork" if ultrawork_mode else "normal"
        )

    def _detect_ultrawork(self, query: str) -> bool:
        """Detect ultrawork/ulw mode (from oh-my-opencode)."""
        ultrawork_patterns = [
            r'\bultrawork\b', r'\bulw\b',
            r'\bautonomous\b', r'\bkeep going\b',
            r'\buntil complete\b', r'\bdon\'t stop\b'
        ]
        return any(re.search(p, query, re.IGNORECASE) for p in ultrawork_patterns)

    def _calculate_complexity(self, query: str) -> int:
        """Calculate task complexity 1-10 (from claude-code-buddy)."""
        base_complexity = 3  # Default moderate complexity

        for keyword, modifier in self.COMPLEXITY_MODIFIERS.items():
            if keyword in query:
                base_complexity += modifier

        # Clamp to 1-10 range
        return max(1, min(10, base_complexity))

    def _match_slash_command(self, query: str) -> Optional[RouteResult]:
        """Match slash commands (from create-claude)."""
        for cmd, config in self.SLASH_COMMANDS.items():
            if query.startswith(cmd):
                return RouteResult(
                    target=config['target'],
                    target_type=config['type'],
                    confidence=1.0,
                    reason=f"Slash command: {cmd}",
                    model_tier=config.get('model', 'claude'),
                    complexity=config.get('complexity', 3)
                )
        return None

    def _match_production_agent(self, query: str) -> Optional[RouteResult]:
        """Match production agents (from create-claude)."""
        for agent, config in self.PRODUCTION_AGENTS.items():
            for trigger in config['triggers']:
                if trigger in query:
                    return RouteResult(
                        target=agent,
                        target_type='agent',
                        confidence=0.85,
                        reason=f"Production agent match: {agent}",
                        model_tier='claude',
                        complexity=config.get('complexity', 4)
                    )
        return None

    def _match_operator(self, query: str) -> Optional[RouteResult]:
        """Match against rule-based operators."""
        for operator, patterns in self.OPERATORS.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    target, target_type = self.OPERATOR_ROUTES.get(
                        operator, ('escalate', 'escalate')
                    )
                    return RouteResult(
                        target=target,
                        target_type=target_type,
                        confidence=0.9,
                        reason=f"Matched operator {operator}",
                        model_tier='codex' if operator == 'PATCH' else 'claude'
                    )
        return None

    def _match_capabilities(self, query: str) -> Optional[RouteResult]:
        """Match against capability registry keywords."""
        if not self.routing_index:
            return None

        # Check keyword index
        best_match = None
        best_score = 0

        for keyword, caps in self.routing_index.get("by_keyword", {}).items():
            if keyword in query:
                score = len(keyword) / len(query.split()[0]) if query.split() else 0.5
                if score > best_score and caps:
                    best_score = score
                    best_match = caps[0]

        if best_match and best_score > 0.3:
            return RouteResult(
                target=best_match["name"],
                target_type=best_match.get("type", "skill"),
                confidence=0.7 + (best_score * 0.2),
                reason=f"Keyword match: {best_match['name']}",
                model_tier=self._get_model_tier(best_match["name"])
            )

        return None

    def _infer_domain(self, query: str) -> Optional[RouteResult]:
        """Infer domain and route to appropriate handler."""
        domain_agents = {
            'research': 'oracle',
            'code': 'kraken',
            'planning': 'architect',
            'memory': 'memory-extractor',
            'analysis': 'critic',
            'security': 'aegis',
        }

        for domain, agent in domain_agents.items():
            if domain in query:
                return RouteResult(
                    target=agent,
                    target_type='agent',
                    confidence=0.6,
                    reason=f"Domain inference: {domain}",
                    model_tier=self._get_model_tier(agent)
                )

        return None

    def _get_model_tier(self, capability_name: str) -> str:
        """Get appropriate model tier for a capability."""
        # Find in capabilities
        for cap in self.capabilities.get("capabilities", []):
            if cap["name"] == capability_name:
                return cap.get("model_tier", "claude")
        return "claude"

    def get_suggested_tools(self, query: str) -> list:
        """Get list of suggested tools/agents for a query."""
        result = self.route(query)

        suggestions = [{
            "name": result.target,
            "type": result.target_type,
            "confidence": result.confidence,
            "model_tier": result.model_tier
        }]

        # Add fallbacks
        if result.target_type == 'agent':
            suggestions.append({
                "name": "scout",
                "type": "agent",
                "confidence": 0.5,
                "model_tier": "claude",
                "note": "fallback for exploration"
            })

        return suggestions


def get_workflow_hint(target: str, target_type: str) -> str:
    """Get workflow guidance based on target (from claude-code-buddy)."""
    hints = {
        ('commit', 'command'): "After commit, consider pushing or creating a PR",
        ('review', 'command'): "After review, address findings or commit if clean",
        ('test', 'command'): "If tests pass, ready for review or commit",
        ('validate', 'command'): "After validation, fix any issues before commit",
        ('pre-commit', 'agent'): "Ready for commit if validation passes",
        ('refactor', 'agent'): "Run tests after refactoring to verify",
        ('debugger', 'agent'): "Add tests for the bug fix",
        ('kraken', 'agent'): "Test changes after implementation",
    }
    return hints.get((target, target_type), "")


def route_query(query: str) -> dict:
    """Route a query and return JSON result."""
    router = DeterministicRouter()
    result = router.route(query)

    workflow_hint = get_workflow_hint(result.target, result.target_type)

    return {
        "target": result.target,
        "target_type": result.target_type,
        "confidence": result.confidence,
        "reason": result.reason,
        "model_tier": result.model_tier,
        "deterministic": result.confidence >= 0.6,
        "mode": result.mode,
        "complexity": result.complexity,
        "workflow_hint": workflow_hint
    }


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python deterministic_router.py route <query>")
        print("  python deterministic_router.py suggest <query>")
        print("  python deterministic_router.py test")
        return

    cmd = sys.argv[1]

    if cmd == "route":
        if len(sys.argv) < 3:
            print("Usage: python deterministic_router.py route <query>")
            return
        query = ' '.join(sys.argv[2:])
        result = route_query(query)
        print(json.dumps(result, indent=2))

    elif cmd == "suggest":
        if len(sys.argv) < 3:
            print("Usage: python deterministic_router.py suggest <query>")
            return
        query = ' '.join(sys.argv[2:])
        router = DeterministicRouter()
        suggestions = router.get_suggested_tools(query)
        print(json.dumps(suggestions, indent=2))

    elif cmd == "test":
        # Test cases including new patterns
        test_queries = [
            # Original tests
            "where is the memory.py file",
            "fix the bug in the router",
            "research how GCRL works",
            "plan the implementation of webhooks",
            "run the tests for daemon",
            "what files handle authentication",
            "debug the MCP server crash",
            "show me the evolution plan",
            # Slash commands (create-claude)
            "/commit add new feature",
            "/review check security issues",
            "/test run all tests",
            "/validate before commit",
            # Production agents (create-claude)
            "validate commit before pushing",
            "simplify this complex function",
            "find the root cause of this error",
            # Ultrawork mode (oh-my-opencode)
            "ultrawork implement the full feature",
            "ulw refactor the entire module",
            # Complex tasks (claude-code-buddy)
            "simple fix for typo",
            "comprehensive architecture redesign",
        ]

        router = DeterministicRouter()
        print("Testing deterministic routing:\n")
        print("=" * 70)

        for query in test_queries:
            result = router.route(query)
            det = "[OK]" if result.confidence >= 0.6 else "[--]"
            mode = "[ULW]" if result.mode == "ultrawork" else "[NRM]"
            print(f"{det} {mode} \"{query}\"")
            print(f"   -> {result.target} ({result.target_type}) [{result.confidence:.1%}]")
            print(f"   Reason: {result.reason}")
            print(f"   Model: {result.model_tier} | Complexity: {result.complexity}/10")
            workflow = get_workflow_hint(result.target, result.target_type)
            if workflow:
                print(f"   Workflow: {workflow}")
            print()

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
