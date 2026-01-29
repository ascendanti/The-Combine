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

# WIRED (2026-01-28): Token compression for context building
try:
    from headroom_optimizer import compress_tool_output

    HEADROOM_AVAILABLE = True
except ImportError:
    HEADROOM_AVAILABLE = False
    compress_tool_output = None

ROUTER_DB = Path(__file__).parent / "router.db"

# ============================================================================
# Configuration
# ============================================================================


class Provider(str, Enum):
    LOCALAI = "localai"  # Free, local inference ($0)
    CODEX = "codex"  # Code tasks, cheaper than Claude ($)
    OPENAI = "openai"  # General fallback ($$)
    CLAUDE = "claude"  # Premium, complex tasks ($$$)
    CLAWDBOT = "clawdbot"  # OAuth gateway - Claude/ChatGPT/Grok via subscription ($0 API)


@dataclass
class RoutingConfig:
    """Configuration for model routing."""

    localai_url: str = os.environ.get("LOCALAI_URL", "http://localhost:8080/v1")
    openai_api_key: Optional[str] = os.environ.get("OPENAI_API_KEY")
    dragonfly_url: str = os.environ.get("DRAGONFLY_URL", "redis://localhost:6379")

    # Clawdbot OAuth Gateway (routes to Claude/ChatGPT/Grok via subscriptions)
    # Load from central config if env vars not set
    clawdbot_url: str = None
    clawdbot_token: str = None
    use_clawdbot: bool = True

    def __post_init__(self):
        # Load Clawdbot config from central config.py if not set via env
        from config import cfg
        if self.clawdbot_url is None:
            self.clawdbot_url = os.environ.get("CLAWDBOT_URL", cfg.CLAWDBOT_URL)
        if self.clawdbot_token is None:
            self.clawdbot_token = os.environ.get("CLAWDBOT_TOKEN", cfg.CLAWDBOT_TOKEN)
        self.use_clawdbot = os.environ.get("USE_CLAWDBOT", str(cfg.USE_CLAWDBOT)).lower() not in ("0", "false", "no")

    # Token budgets
    max_context_tokens: int = 8000
    max_output_tokens: int = 2000

    # Routing thresholds
    complexity_threshold: float = 0.7  # Above this → Claude
    cost_sensitivity: float = 0.5  # Higher = prefer LocalAI

    # Model mappings (ordered by cost: LocalAI < Codex < OpenAI < Claude)
    localai_model: str = "mistral-7b-instruct-v0.3"
    codex_model: str = "gpt-4o-mini"  # Best for code tasks, cheaper than Claude
    openai_model: str = "gpt-4o"  # General fallback
    claude_model: str = "claude-sonnet-4-20250514"  # Premium, complex only

    # Token-precious mode: aggressively prefer cheaper providers
    token_precious_mode: bool = True


# ============================================================================
# Task Classification
# ============================================================================


class TaskType(str, Enum):
    SUMMARIZE = "summarize"  # → LocalAI
    EMBED = "embed"  # → LocalAI
    TRANSLATE = "translate"  # → LocalAI
    QA_SIMPLE = "qa_simple"  # → LocalAI
    QA_COMPLEX = "qa_complex"  # → Claude
    CODE_GENERATE = "code_generate"  # → Claude
    CODE_REVIEW = "code_review"  # → Claude
    ARCHITECTURE = "architecture"  # → Claude
    REASONING = "reasoning"  # → Claude
    UNKNOWN = "unknown"  # → Claude (safe default)


# Task → Provider mapping (Token-Precious: prefer cheaper when capable)
# Cost order: LocalAI ($0) < Codex ($) < OpenAI ($$) < Claude ($$$)
TASK_ROUTING = {
    # FREE tier (LocalAI)
    TaskType.SUMMARIZE: Provider.LOCALAI,
    TaskType.EMBED: Provider.LOCALAI,
    TaskType.TRANSLATE: Provider.LOCALAI,
    TaskType.QA_SIMPLE: Provider.LOCALAI,
    # CHEAP tier (Codex/gpt-4o-mini) - code tasks
    TaskType.CODE_GENERATE: Provider.CODEX,
    TaskType.CODE_REVIEW: Provider.CODEX,
    # PREMIUM tier (Claude) - complex reasoning only
    TaskType.QA_COMPLEX: Provider.CLAUDE,
    TaskType.ARCHITECTURE: Provider.CLAUDE,
    TaskType.REASONING: Provider.CLAUDE,
    TaskType.UNKNOWN: Provider.CODEX,  # Default to cheaper, escalate if needed
}

# Fallback chain for when preferred provider is unavailable
FALLBACK_CHAIN = {
    Provider.LOCALAI: [Provider.CODEX, Provider.OPENAI, Provider.CLAUDE],
    Provider.CODEX: [Provider.OPENAI, Provider.CLAUDE],
    Provider.OPENAI: [Provider.CLAUDE],
    Provider.CLAUDE: [],  # No fallback, it's the last resort
}


def estimate_complexity(task: str, content: str) -> float:
    """Estimate task complexity (0-1). Higher = needs Claude."""
    score = 0.0

    # Content size factor
    content_len = len(content)
    if content_len > 10000:
        score += 0.3
    elif content_len > 5000:
        score += 0.15

    # Complexity keywords in task
    complex_keywords = [
        "complex",
        "sophisticated",
        "intricate",
        "multi-step",
        "architectural",
        "refactor entire",
        "redesign",
        "optimize performance",
        "security audit",
        "debug race condition",
        "memory leak",
        "concurrent",
        "distributed",
    ]
    if any(kw in task.lower() for kw in complex_keywords):
        score += 0.4

    # Code complexity indicators in content
    complexity_indicators = [
        "async",
        "await",
        "threading",
        "multiprocess",
        "mutex",
        "semaphore",
        "decorator",
        "metaclass",
        "generics",
        "type system",
        "dependency injection",
    ]
    indicator_count = sum(1 for ind in complexity_indicators if ind in content.lower())
    score += min(0.3, indicator_count * 0.05)

    return min(1.0, score)


def classify_task(task: str, content: str = "") -> TaskType:
    """Classify task to determine routing. Uses complexity for escalation."""
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

    # Code patterns - Codex handles most, Claude for complex
    code_keywords = [
        "implement",
        "write code",
        "create function",
        "generate",
        "write a function",
        "write function",
        "code this",
        "build a",
        "create a class",
        "write a script",
        "fix this code",
        "add feature",
    ]
    if any(kw in task_lower for kw in code_keywords):
        complexity = estimate_complexity(task, content)
        if complexity > 0.6:  # High complexity → Claude
            return TaskType.ARCHITECTURE  # Routes to Claude
        return TaskType.CODE_GENERATE  # Routes to Codex

    # Refactoring - check complexity for routing
    if any(kw in task_lower for kw in ["refactor", "rewrite", "optimize code"]):
        complexity = estimate_complexity(task, content)
        if complexity > 0.5:
            return TaskType.ARCHITECTURE  # Complex refactor → Claude
        return TaskType.CODE_GENERATE  # Simple refactor → Codex

    if any(
        kw in task_lower for kw in ["review", "audit", "check code", "analyze code"]
    ):
        complexity = estimate_complexity(task, content)
        if complexity > 0.6:
            return TaskType.REASONING  # Complex review → Claude
        return TaskType.CODE_REVIEW  # Routine review → Codex

    # Architecture patterns (always Claude)
    if any(kw in task_lower for kw in ["architect", "design", "plan", "structure"]):
        return TaskType.ARCHITECTURE

    # Reasoning patterns
    if any(
        kw in task_lower for kw in ["why", "explain", "analyze", "compare", "reason"]
    ):
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

    def build(
        self,
        task: str,
        content: str,
        recall_items: List[str] = None,
        recent_files: List[str] = None,
    ) -> Dict[str, Any]:
        """Build optimized context."""

        # WIRED (2026-01-28): Compress large content before building context
        if HEADROOM_AVAILABLE and len(content) > 5000:
            try:
                compressed = compress_tool_output({"content": content}, max_items=30)
                if isinstance(compressed, dict) and "content" in compressed:
                    content = compressed["content"]
            except Exception:
                pass  # Keep original on error

        context = {
            "task": task,
            "content": content,
            "recall": [],
            "files": [],
            "total_tokens": 0,
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

    def __init__(self, base_url: str, model: str, timeout: float = 10.0):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.client = None
        if OPENAI_AVAILABLE:
            self.client = openai.OpenAI(
                base_url=base_url,
                api_key="not-needed",
                timeout=timeout,  # Fast timeout for local inference
            )

    def available(self) -> bool:
        """Check if LocalAI is running (fast check with 2s timeout)."""
        if not self.client:
            return False
        try:
            import httpx

            resp = httpx.get(f"{self.base_url}/models", timeout=2.0)
            return resp.status_code == 200
        except:
            return False

    def complete(self, messages: List[Dict], max_tokens: int = 1000) -> str:
        """Generate completion."""
        if not self.client:
            raise RuntimeError("LocalAI client not available")

        response = self.client.chat.completions.create(
            model=self.model, messages=messages, max_tokens=max_tokens
        )
        return response.choices[0].message.content

    def embed(self, text: str) -> List[float]:
        """Generate embeddings."""
        if not self.client:
            raise RuntimeError("LocalAI client not available")

        response = self.client.embeddings.create(
            model="all-MiniLM-L6-v2",  # Common embedding model
            input=text,
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
            model=self.model, messages=messages, max_tokens=max_tokens
        )
        return response.choices[0].message.content

    def embed(self, text: str) -> List[float]:
        """Generate embeddings."""
        if not self.client:
            raise RuntimeError("OpenAI client not available")

        response = self.client.embeddings.create(
            model="text-embedding-3-small", input=text
        )
        return response.data[0].embedding


class ClawdbotClient:
    """
    Client for Clawdbot OAuth gateway.

    Routes requests through Clawdbot which handles OAuth authentication
    for Claude Pro, ChatGPT Pro, and Grok Super subscriptions.

    Benefits:
    - $0 API cost (uses subscription)
    - Access to premium models without API keys
    - Automatic model selection by Clawdbot
    """

    def __init__(self, base_url: str, token: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def available(self) -> bool:
        """Check if Clawdbot gateway is running."""
        if not self.token:
            return False
        try:
            import requests
            # Quick connectivity check - just verify gateway responds
            resp = requests.get(
                f"{self.base_url}/",
                timeout=5
            )
            # Gateway returns 200 with HTML control UI when running
            return resp.status_code == 200
        except:
            return False

    def complete(self, messages: List[Dict], max_tokens: int = 2000, model: str = None) -> str:
        """
        Generate completion via Clawdbot OAuth gateway.

        Clawdbot will route to the best available OAuth provider
        (Claude Pro, ChatGPT Pro, or Grok Super).
        """
        import httpx

        payload = {
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if model:
            payload["model"] = model

        try:
            resp = httpx.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                },
                timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Clawdbot API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise RuntimeError(f"Clawdbot request failed: {e}")

    def notify_task_complete(self, task_id: str, result: str, success: bool = True):
        """
        Notify Clawdbot when a task completes (webhook for supervisor mode).

        This allows Clawdbot to track task outcomes and provide oversight.
        """
        import httpx

        try:
            resp = httpx.post(
                f"{self.base_url}/webhook/task-complete",
                json={
                    "task_id": task_id,
                    "result": result[:500],  # Truncate for efficiency
                    "success": success,
                    "source": "atlas-daemon"
                },
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                },
                timeout=10.0
            )
            return resp.status_code == 200
        except:
            return False  # Non-critical, don't fail on webhook error


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
        self.localai = LocalAIClient(self.config.localai_url, self.config.localai_model)
        self.openai_client = OpenAIClient(
            self.config.openai_api_key, self.config.openai_model
        )

        # Clawdbot OAuth gateway (routes to Claude/ChatGPT/Grok via subscriptions)
        self.clawdbot = ClawdbotClient(
            self.config.clawdbot_url,
            self.config.clawdbot_token
        ) if self.config.use_clawdbot else None

        # Context builder
        self.context_builder = ContextBuilder(self.config)

        # Stats tracking
        self._init_stats_db()

    def _init_stats_db(self):
        """Initialize routing stats database."""
        conn = sqlite3.connect(ROUTER_DB)
        conn.execute(
            """
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
        """
        )
        conn.commit()
        conn.close()

    def _log_routing(
        self,
        task_type: TaskType,
        provider: Provider,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        success: bool,
    ):
        """Log routing decision for analysis."""
        # Estimate cost (rough)
        cost = 0.0
        if provider == Provider.CLAUDE:
            cost = (input_tokens * 0.003 + output_tokens * 0.015) / 1000
        elif provider == Provider.OPENAI:
            cost = (input_tokens * 0.00015 + output_tokens * 0.0006) / 1000
        # LocalAI = $0

        conn = sqlite3.connect(ROUTER_DB)
        conn.execute(
            """
            INSERT INTO routing_stats
            (timestamp, task_type, provider, input_tokens, output_tokens,
             latency_ms, success, cost_estimate)
            VALUES (datetime('now'), ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                task_type.value,
                provider.value,
                input_tokens,
                output_tokens,
                latency_ms,
                1 if success else 0,
                cost,
            ),
        )
        conn.commit()
        conn.close()

    def select_provider(self, task_type: TaskType) -> Provider:
        """Select best available provider for task."""
        preferred = TASK_ROUTING.get(task_type, Provider.CLAUDE)

        # Check availability
        if preferred == Provider.LOCALAI:
            if self.localai.available():
                return Provider.LOCALAI
            # Fallback to Clawdbot if available (free via OAuth)
            if self.clawdbot and self.clawdbot.available():
                return Provider.CLAWDBOT
            # Fallback to OpenAI for embeddings, Claude for text
            if task_type == TaskType.EMBED and self.openai_client.available():
                return Provider.OPENAI
            return Provider.CLAUDE  # Final fallback

        # For Claude/OpenAI tasks, prefer Clawdbot if available (free via OAuth)
        if preferred in (Provider.CLAUDE, Provider.OPENAI, Provider.CODEX):
            if self.clawdbot and self.clawdbot.available():
                return Provider.CLAWDBOT

        return preferred

    def route(
        self,
        task: str,
        content: str = "",
        recall_items: List[str] = None,
        recent_files: List[str] = None,
        force_provider: Provider = None,
    ) -> Dict[str, Any]:
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
                "task_type": "cached",
            }

        # Classify and route
        task_type = classify_task(task, content)
        provider = force_provider or self.select_provider(task_type)

        # Build optimized context
        context = self.context_builder.build(task, content, recall_items, recent_files)

        # Prepare messages
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Be concise."},
            {"role": "user", "content": f"{task}\n\n{content}"},
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
                response = self.localai.complete(
                    messages, self.config.max_output_tokens
                )
            elif provider == Provider.OPENAI:
                response = self.openai_client.complete(
                    messages, self.config.max_output_tokens
                )
            elif provider == Provider.CLAWDBOT:
                # Route through Clawdbot OAuth gateway (free via subscription)
                response = self.clawdbot.complete(
                    messages, self.config.max_output_tokens
                )
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
                    "messages": messages,
                }

            output_tokens = estimate_tokens(response)
            latency = int((time.time() - start) * 1000)

            # Cache successful responses
            self.context_builder.cache_result(cache_key, response)

            # Log stats
            self._log_routing(
                task_type, provider, input_tokens, output_tokens, latency, True
            )

            return {
                "provider": provider.value,
                "response": response,
                "tokens_used": {"input": input_tokens, "output": output_tokens},
                "cached": False,
                "task_type": task_type.value,
            }

        except Exception as e:
            self._log_routing(task_type, provider, input_tokens, 0, 0, False)
            return {
                "provider": provider.value,
                "response": None,
                "error": str(e),
                "tokens_used": {"input": input_tokens, "output": 0},
                "cached": False,
                "task_type": task_type.value,
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
        cursor = conn.execute(
            """
            SELECT provider, COUNT(*), SUM(cost_estimate)
            FROM routing_stats
            GROUP BY provider
        """
        )
        by_provider = {
            row[0]: {"count": row[1], "cost": row[2]} for row in cursor.fetchall()
        }

        # Recent activity
        cursor = conn.execute(
            """
            SELECT provider, task_type, success, cost_estimate
            FROM routing_stats
            ORDER BY id DESC LIMIT 20
        """
        )
        recent = [
            {"provider": r[0], "task": r[1], "success": r[2], "cost": r[3]}
            for r in cursor.fetchall()
        ]

        # Total savings (LocalAI vs Claude equivalent)
        cursor = conn.execute(
            """
            SELECT SUM(input_tokens), SUM(output_tokens)
            FROM routing_stats WHERE provider = 'localai'
        """
        )
        row = cursor.fetchone()
        localai_tokens = (row[0] or 0, row[1] or 0)
        # Estimate what it would have cost on Claude
        claude_equivalent = (
            localai_tokens[0] * 0.003 + localai_tokens[1] * 0.015
        ) / 1000

        conn.close()

        return {
            "by_provider": by_provider,
            "recent": recent,
            "savings": {
                "localai_input_tokens": localai_tokens[0],
                "localai_output_tokens": localai_tokens[1],
                "claude_equivalent_cost": f"${claude_equivalent:.4f}",
                "actual_cost": "$0.00",
            },
        }


# ============================================================================
# CLI
# ============================================================================

# ============================================================================
# Phase 14.4: Thinking Budget Tiers & Cascade Routing
# ============================================================================

THINKING_BUDGETS = {
    # Task type → (min_tokens, max_tokens, default_tokens)
    TaskType.SUMMARIZE: (0, 1024, 512),
    TaskType.EMBED: (0, 0, 0),
    TaskType.TRANSLATE: (0, 512, 256),
    TaskType.QA_SIMPLE: (0, 1024, 0),
    TaskType.QA_COMPLEX: (1024, 4096, 2048),
    TaskType.CODE_GENERATE: (2048, 16384, 4096),
    TaskType.CODE_REVIEW: (1024, 8192, 2048),
    TaskType.ARCHITECTURE: (4096, 32000, 8192),
    TaskType.REASONING: (2048, 16384, 4096),
    TaskType.UNKNOWN: (1024, 8192, 2048),
}


def get_thinking_budget(task_type: TaskType, complexity: float = 0.5) -> int:
    """Get thinking token budget based on task type and complexity."""
    min_t, max_t, default = THINKING_BUDGETS.get(task_type, (1024, 8192, 2048))
    # Scale by complexity (0-1)
    budget = int(min_t + (max_t - min_t) * complexity)
    return max(min_t, min(max_t, budget))


class CascadeRouter:
    """
    Cascade routing: Try cheap providers first, escalate on failure.

    Pattern:
    1. Start with LocalAI (free)
    2. If quality check fails → escalate to Codex
    3. If still fails → escalate to Claude

    Quality checks:
    - Response length > minimum
    - No error indicators
    - Coherence score (optional)
    """

    def __init__(self, base_router: ModelRouter):
        self.router = base_router
        self.quality_threshold = 0.6

    def route_with_cascade(
        self, task: str, content: str = "", min_response_length: int = 50
    ) -> Dict[str, Any]:
        """Route with automatic escalation on quality failure."""
        task_type = classify_task(task, content)
        complexity = estimate_complexity(task, content)

        # Determine cascade order based on task type
        if task_type in [TaskType.SUMMARIZE, TaskType.TRANSLATE, TaskType.QA_SIMPLE]:
            cascade = [Provider.LOCALAI, Provider.CODEX, Provider.CLAUDE]
        elif task_type in [TaskType.CODE_GENERATE, TaskType.CODE_REVIEW]:
            cascade = [Provider.CODEX, Provider.CLAUDE]
        else:
            # Complex tasks go straight to premium
            cascade = [Provider.CLAUDE]

        # Try each provider in order
        last_result = None
        for provider in cascade:
            result = self.router.route(task, content, force_provider=provider)
            last_result = result

            # Check quality
            if self._check_quality(result, min_response_length):
                result["cascade_attempts"] = cascade.index(provider) + 1
                result["thinking_budget"] = get_thinking_budget(task_type, complexity)
                return result

            # Log escalation
            if provider != cascade[-1]:
                self._log_escalation(
                    task_type, provider, cascade[cascade.index(provider) + 1]
                )

        # Return last result even if quality check failed
        last_result["cascade_attempts"] = len(cascade)
        last_result["quality_warning"] = True
        return last_result

    def _check_quality(self, result: Dict, min_length: int) -> bool:
        """Check if response meets quality threshold."""
        if result.get("error"):
            return False

        response = result.get("response")
        if not response:
            return False

        # Length check
        if len(response) < min_length:
            return False

        # Error indicator check
        error_indicators = ["I cannot", "I'm unable", "Error:", "Exception:"]
        if any(ind in response for ind in error_indicators):
            return False

        return True

    def _log_escalation(
        self, task_type: TaskType, from_provider: Provider, to_provider: Provider
    ):
        """Log escalation event for analysis."""
        conn = sqlite3.connect(ROUTER_DB)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS escalations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                task_type TEXT,
                from_provider TEXT,
                to_provider TEXT
            )
        """
        )
        conn.execute(
            """
            INSERT INTO escalations (task_type, from_provider, to_provider)
            VALUES (?, ?, ?)
        """,
            (task_type.value, from_provider.value, to_provider.value),
        )
        conn.commit()
        conn.close()


def get_routing_summary() -> Dict[str, Any]:
    """Get comprehensive routing statistics including savings."""
    conn = sqlite3.connect(ROUTER_DB)

    # Total by provider
    cursor = conn.execute(
        """
        SELECT provider, COUNT(*), SUM(cost_estimate),
               SUM(input_tokens), SUM(output_tokens)
        FROM routing_stats GROUP BY provider
    """
    )
    by_provider = {}
    total_localai_tokens = 0
    for row in cursor.fetchall():
        by_provider[row[0]] = {
            "calls": row[1],
            "cost": row[2] or 0,
            "input_tokens": row[3] or 0,
            "output_tokens": row[4] or 0,
        }
        if row[0] == "localai":
            total_localai_tokens = (row[3] or 0) + (row[4] or 0)

    # Calculate savings (what LocalAI calls would have cost on Claude)
    claude_equivalent = total_localai_tokens * 0.009 / 1000  # ~$9/M tokens average
    actual_cost = sum(p.get("cost", 0) for p in by_provider.values())

    # Escalation stats
    try:
        cursor = conn.execute(
            """
            SELECT from_provider, to_provider, COUNT(*)
            FROM escalations GROUP BY from_provider, to_provider
        """
        )
        escalations = [
            {"from": r[0], "to": r[1], "count": r[2]} for r in cursor.fetchall()
        ]
    except:
        escalations = []

    conn.close()

    return {
        "by_provider": by_provider,
        "savings": {
            "localai_tokens": total_localai_tokens,
            "claude_equivalent_cost": round(claude_equivalent, 4),
            "actual_cost": round(actual_cost, 4),
            "saved": round(claude_equivalent - actual_cost, 4),
            "savings_percent": round((1 - actual_cost / claude_equivalent) * 100, 1)
            if claude_equivalent > 0
            else 0,
        },
        "escalations": escalations,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Model Router")
    parser.add_argument("--stats", action="store_true", help="Show routing stats")
    parser.add_argument("--test", action="store_true", help="Test routing")
    parser.add_argument(
        "--check", action="store_true", help="Check provider availability"
    )

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
            content="This is a test paragraph about machine learning and neural networks.",
        )
        print(json.dumps(result, indent=2, default=str))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
