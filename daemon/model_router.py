#!/usr/bin/env python3
"""
Model Router - Intelligent routing between Claude, OpenAI, and LocalAI

Architecture (per Codex recommendations):
1. Pre-routing: Estimate token budget, select provider
2. Context building: Top-k recall, recent files, task notes
3. Execution: Stream to Dragonfly (cache) + LocalRecall (semantic)

Routing Policy:
- LocalAI: Bulk tasks, summarization, embeddings, offline (FREE)
- Claude: Complex reasoning, code generation, architecture (DEFAULT)
- OpenAI: Specific escalations, embeddings if LocalAI unavailable (FALLBACK)

Usage:
    from model_router import ModelRouter
    router = ModelRouter()
    response = router.route(task="summarize this chapter", content="...")
"""

import os
import json
import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List
from pathlib import Path
import sqlite3

# Try imports
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

ROUTER_DB = Path(__file__).parent / "router.db"

# ============================================================================
# Configuration
# ============================================================================

class Provider(str, Enum):
    LOCALAI = "localai"      # Free, local inference
    CLAUDE = "claude"        # Default for complex tasks
    OPENAI = "openai"        # Fallback/escalation

@dataclass
class RoutingConfig:
    """Configuration for model routing."""
    localai_url: str = "http://localhost:8080/v1"
    openai_api_key: Optional[str] = None
    dragonfly_url: str = "redis://localhost:6379"

    # Token budgets
    max_context_tokens: int = 8000
    max_output_tokens: int = 2000

    # Routing thresholds
    complexity_threshold: float = 0.7  # Above this → Claude
    cost_sensitivity: float = 0.5      # Higher = prefer LocalAI

    # Model mappings
    localai_model: str = "mistral-7b-instruct"
    openai_model: str = "gpt-4o-mini"
    claude_model: str = "claude-sonnet-4-20250514"

# ============================================================================
# Task Classification
# ============================================================================

class TaskType(str, Enum):
    SUMMARIZE = "summarize"           # → LocalAI
    EMBED = "embed"                   # → LocalAI
    TRANSLATE = "translate"           # → LocalAI
    QA_SIMPLE = "qa_simple"           # → LocalAI
    QA_COMPLEX = "qa_complex"         # → Claude
    CODE_GENERATE = "code_generate"   # → Claude
    CODE_REVIEW = "code_review"       # → Claude
    ARCHITECTURE = "architecture"     # → Claude
    REASONING = "reasoning"           # → Claude
    UNKNOWN = "unknown"               # → Claude (safe default)

# Task → Provider mapping
TASK_ROUTING = {
    TaskType.SUMMARIZE: Provider.LOCALAI,
    TaskType.EMBED: Provider.LOCALAI,
    TaskType.TRANSLATE: Provider.LOCALAI,
    TaskType.QA_SIMPLE: Provider.LOCALAI,
    TaskType.QA_COMPLEX: Provider.CLAUDE,
    TaskType.CODE_GENERATE: Provider.CLAUDE,
    TaskType.CODE_REVIEW: Provider.CLAUDE,
    TaskType.ARCHITECTURE: Provider.CLAUDE,
    TaskType.REASONING: Provider.CLAUDE,
    TaskType.UNKNOWN: Provider.CLAUDE,
}

def classify_task(task: str, content: str = "") -> TaskType:
    """Classify task to determine routing."""
    task_lower = task.lower()

    # Summarization patterns
    if any(kw in task_lower for kw in ["summarize", "summary", "tldr", "brief"]):
        return TaskType.SUMMARIZE

    # Embedding patterns
    if any(kw in task_lower for kw in ["embed", "vector", "encoding"]):
        return TaskType.EMBED

    # Translation patterns
    if any(kw in task_lower for kw in ["translate", "translation"]):
        return TaskType.TRANSLATE

    # Simple Q&A (factual, lookup)
    if any(kw in task_lower for kw in ["what is", "define", "list", "who is", "when"]):
        # Check if content is small (simple lookup)
        if len(content) < 2000:
            return TaskType.QA_SIMPLE
        return TaskType.QA_COMPLEX

    # Code patterns
    if any(kw in task_lower for kw in ["implement", "write code", "create function", "generate"]):
        return TaskType.CODE_GENERATE
    if any(kw in task_lower for kw in ["review", "audit", "check code"]):
        return TaskType.CODE_REVIEW

    # Architecture patterns
    if any(kw in task_lower for kw in ["architect", "design", "plan", "structure"]):
        return TaskType.ARCHITECTURE

    # Reasoning patterns
    if any(kw in task_lower for kw in ["why", "explain", "analyze", "compare", "reason"]):
        return TaskType.REASONING

    return TaskType.UNKNOWN

# ============================================================================
# Token Estimation
# ============================================================================

def estimate_tokens(text: str) -> int:
    """Rough token estimate (words * 1.3)."""
    return int(len(text.split()) * 1.3)

def should_compress(content: str, max_tokens: int) -> bool:
    """Check if content needs compression."""
    return estimate_tokens(content) > max_tokens

# ============================================================================
# Context Builder
# ============================================================================

class ContextBuilder:
    """Build optimized context for model calls."""

    def __init__(self, config: RoutingConfig):
        self.config = config
        self.dragonfly = None
        if REDIS_AVAILABLE:
            try:
                self.dragonfly = redis.from_url(config.dragonfly_url)
                self.dragonfly.ping()
            except:
                self.dragonfly = None

    def build(self, task: str, content: str,
              recall_items: List[str] = None,
              recent_files: List[str] = None) -> Dict[str, Any]:
        """Build optimized context."""

        context = {
            "task": task,
            "content": content,
            "recall": [],
            "files": [],
            "total_tokens": 0
        }

        # Start with task + content
        context["total_tokens"] = estimate_tokens(task) + estimate_tokens(content)
        budget_remaining = self.config.max_context_tokens - context["total_tokens"]

        # Add recall items (top-k by relevance, fit in budget)
        if recall_items:
            for item in recall_items:
                item_tokens = estimate_tokens(item)
                if item_tokens < budget_remaining:
                    context["recall"].append(item)
                    budget_remaining -= item_tokens
                    context["total_tokens"] += item_tokens

        # Add recent files (fit in budget)
        if recent_files:
            for file_content in recent_files:
                file_tokens = estimate_tokens(file_content)
                if file_tokens < budget_remaining:
                    context["files"].append(file_content)
                    budget_remaining -= file_tokens
                    context["total_tokens"] += file_tokens

        return context

    def cache_result(self, key: str, result: str, ttl: int = 3600):
        """Cache result in Dragonfly."""
        if self.dragonfly:
            cache_key = f"router:{hashlib.md5(key.encode()).hexdigest()}"
            self.dragonfly.setex(cache_key, ttl, result)

    def get_cached(self, key: str) -> Optional[str]:
        """Get cached result from Dragonfly."""
        if self.dragonfly:
            cache_key = f"router:{hashlib.md5(key.encode()).hexdigest()}"
            result = self.dragonfly.get(cache_key)
            return result.decode() if result else None
        return None

# ============================================================================
# Model Clients
# ============================================================================

class LocalAIClient:
    """Client for LocalAI inference."""

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model
        self.client = None
        if OPENAI_AVAILABLE:
            self.client = openai.OpenAI(
                base_url=base_url,
                api_key="not-needed"
            )

    def available(self) -> bool:
        """Check if LocalAI is running."""
        if not self.client:
            return False
        try:
            self.client.models.list()
            return True
        except:
            return False

    def complete(self, messages: List[Dict], max_tokens: int = 1000) -> str:
        """Generate completion."""
        if not self.client:
            raise RuntimeError("LocalAI client not available")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content

    def embed(self, text: str) -> List[float]:
        """Generate embeddings."""
        if not self.client:
            raise RuntimeError("LocalAI client not available")

        response = self.client.embeddings.create(
            model="all-MiniLM-L6-v2",  # Common embedding model
            input=text
        )
        return response.data[0].embedding


class OpenAIClient:
    """Client for OpenAI API."""

    def __init__(self, api_key: str, model: str):
        self.model = model
        self.client = None
        if OPENAI_AVAILABLE and api_key:
            self.client = openai.OpenAI(api_key=api_key)

    def available(self) -> bool:
        return self.client is not None

    def complete(self, messages: List[Dict], max_tokens: int = 1000) -> str:
        """Generate completion."""
        if not self.client:
            raise RuntimeError("OpenAI client not available")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content

    def embed(self, text: str) -> List[float]:
        """Generate embeddings."""
        if not self.client:
            raise RuntimeError("OpenAI client not available")

        response = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding

# ============================================================================
# Main Router
# ============================================================================

class ModelRouter:
    """
    Intelligent model router with budget-aware routing.

    Routing policy:
    1. Classify task type
    2. Check provider availability
    3. Estimate token budget
    4. Build optimized context
    5. Route to best provider
    6. Cache result
    """

    def __init__(self, config: RoutingConfig = None):
        self.config = config or RoutingConfig(
            openai_api_key=os.environ.get("OPENAI_API_KEY")
        )

        # Initialize clients
        self.localai = LocalAIClient(
            self.config.localai_url,
            self.config.localai_model
        )
        self.openai_client = OpenAIClient(
            self.config.openai_api_key,
            self.config.openai_model
        )

        # Context builder
        self.context_builder = ContextBuilder(self.config)

        # Stats tracking
        self._init_stats_db()

    def _init_stats_db(self):
        """Initialize routing stats database."""
        conn = sqlite3.connect(ROUTER_DB)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS routing_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                task_type TEXT,
                provider TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                latency_ms INTEGER,
                success INTEGER,
                cost_estimate REAL
            )
        """)
        conn.commit()
        conn.close()

    def _log_routing(self, task_type: TaskType, provider: Provider,
                     input_tokens: int, output_tokens: int,
                     latency_ms: int, success: bool):
        """Log routing decision for analysis."""
        # Estimate cost (rough)
        cost = 0.0
        if provider == Provider.CLAUDE:
            cost = (input_tokens * 0.003 + output_tokens * 0.015) / 1000
        elif provider == Provider.OPENAI:
            cost = (input_tokens * 0.00015 + output_tokens * 0.0006) / 1000
        # LocalAI = $0

        conn = sqlite3.connect(ROUTER_DB)
        conn.execute("""
            INSERT INTO routing_stats
            (timestamp, task_type, provider, input_tokens, output_tokens,
             latency_ms, success, cost_estimate)
            VALUES (datetime('now'), ?, ?, ?, ?, ?, ?, ?)
        """, (task_type.value, provider.value, input_tokens, output_tokens,
              latency_ms, 1 if success else 0, cost))
        conn.commit()
        conn.close()

    def select_provider(self, task_type: TaskType) -> Provider:
        """Select best available provider for task."""
        preferred = TASK_ROUTING.get(task_type, Provider.CLAUDE)

        # Check availability
        if preferred == Provider.LOCALAI:
            if self.localai.available():
                return Provider.LOCALAI
            # Fallback to OpenAI for embeddings, Claude for text
            if task_type == TaskType.EMBED and self.openai_client.available():
                return Provider.OPENAI
            return Provider.CLAUDE  # Final fallback

        # Claude tasks stay with Claude (we're already in Claude)
        return preferred

    def route(self, task: str, content: str = "",
              recall_items: List[str] = None,
              recent_files: List[str] = None,
              force_provider: Provider = None) -> Dict[str, Any]:
        """
        Route task to appropriate model.

        Returns:
            {
                "provider": "localai|claude|openai",
                "response": "...",
                "tokens_used": {"input": N, "output": M},
                "cached": bool,
                "task_type": "..."
            }
        """
        import time
        start = time.time()

        # Check cache first
        cache_key = f"{task}:{content[:500]}"
        cached = self.context_builder.get_cached(cache_key)
        if cached:
            return {
                "provider": "cache",
                "response": cached,
                "tokens_used": {"input": 0, "output": 0},
                "cached": True,
                "task_type": "cached"
            }

        # Classify and route
        task_type = classify_task(task, content)
        provider = force_provider or self.select_provider(task_type)

        # Build optimized context
        context = self.context_builder.build(
            task, content, recall_items, recent_files
        )

        # Prepare messages
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Be concise."},
            {"role": "user", "content": f"{task}\n\n{content}"}
        ]

        # Add recall context if present
        if context["recall"]:
            recall_text = "\n".join(context["recall"])
            messages[0]["content"] += f"\n\nRelevant context:\n{recall_text}"

        # Execute based on provider
        response = ""
        input_tokens = context["total_tokens"]

        try:
            if provider == Provider.LOCALAI:
                response = self.localai.complete(messages, self.config.max_output_tokens)
            elif provider == Provider.OPENAI:
                response = self.openai_client.complete(messages, self.config.max_output_tokens)
            else:
                # Claude - return instruction to use Claude directly
                # (We're already in Claude, so this is a pass-through indicator)
                return {
                    "provider": "claude",
                    "response": None,  # Signal to use Claude directly
                    "tokens_used": {"input": input_tokens, "output": 0},
                    "cached": False,
                    "task_type": task_type.value,
                    "context": context,
                    "messages": messages
                }

            output_tokens = estimate_tokens(response)
            latency = int((time.time() - start) * 1000)

            # Cache successful responses
            self.context_builder.cache_result(cache_key, response)

            # Log stats
            self._log_routing(task_type, provider, input_tokens, output_tokens, latency, True)

            return {
                "provider": provider.value,
                "response": response,
                "tokens_used": {"input": input_tokens, "output": output_tokens},
                "cached": False,
                "task_type": task_type.value
            }

        except Exception as e:
            self._log_routing(task_type, provider, input_tokens, 0, 0, False)
            return {
                "provider": provider.value,
                "response": None,
                "error": str(e),
                "tokens_used": {"input": input_tokens, "output": 0},
                "cached": False,
                "task_type": task_type.value
            }

    def embed(self, text: str) -> Dict[str, Any]:
        """Generate embeddings via best available provider."""
        if self.localai.available():
            try:
                embedding = self.localai.embed(text)
                return {"provider": "localai", "embedding": embedding}
            except:
                pass

        if self.openai_client.available():
            try:
                embedding = self.openai_client.embed(text)
                return {"provider": "openai", "embedding": embedding}
            except:
                pass

        return {"provider": None, "error": "No embedding provider available"}

    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        conn = sqlite3.connect(ROUTER_DB)

        # Provider distribution
        cursor = conn.execute("""
            SELECT provider, COUNT(*), SUM(cost_estimate)
            FROM routing_stats
            GROUP BY provider
        """)
        by_provider = {row[0]: {"count": row[1], "cost": row[2]}
                       for row in cursor.fetchall()}

        # Recent activity
        cursor = conn.execute("""
            SELECT provider, task_type, success, cost_estimate
            FROM routing_stats
            ORDER BY id DESC LIMIT 20
        """)
        recent = [{"provider": r[0], "task": r[1], "success": r[2], "cost": r[3]}
                  for r in cursor.fetchall()]

        # Total savings (LocalAI vs Claude equivalent)
        cursor = conn.execute("""
            SELECT SUM(input_tokens), SUM(output_tokens)
            FROM routing_stats WHERE provider = 'localai'
        """)
        row = cursor.fetchone()
        localai_tokens = (row[0] or 0, row[1] or 0)
        # Estimate what it would have cost on Claude
        claude_equivalent = (localai_tokens[0] * 0.003 + localai_tokens[1] * 0.015) / 1000

        conn.close()

        return {
            "by_provider": by_provider,
            "recent": recent,
            "savings": {
                "localai_input_tokens": localai_tokens[0],
                "localai_output_tokens": localai_tokens[1],
                "claude_equivalent_cost": f"${claude_equivalent:.4f}",
                "actual_cost": "$0.00"
            }
        }

# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Model Router')
    parser.add_argument('--stats', action='store_true', help='Show routing stats')
    parser.add_argument('--test', action='store_true', help='Test routing')
    parser.add_argument('--check', action='store_true', help='Check provider availability')

    args = parser.parse_args()
    router = ModelRouter()

    if args.stats:
        stats = router.get_stats()
        print(json.dumps(stats, indent=2))
    elif args.check:
        print(f"LocalAI available: {router.localai.available()}")
        print(f"OpenAI available: {router.openai_client.available()}")
    elif args.test:
        # Test routing
        result = router.route(
            task="Summarize this text",
            content="This is a test paragraph about machine learning and neural networks."
        )
        print(json.dumps(result, indent=2, default=str))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
