"""Base adapter class for external tools.

All external tool adapters inherit from ExternalToolAdapter and implement:
- tool_name(): Returns the tool identifier
- requires_mcp(): Whether tool needs MCP connection
- _invoke_local(): Execute tool locally (subprocess/library)
- _invoke_with_mcp(): Execute tool via MCP (if applicable)

Token Efficiency:
- Budget enforcement with hard limits
- End-after-task cleanup via _active flag
- Automatic resource release
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging
import time

if TYPE_CHECKING:
    from ..mcp_pool import MCPPool, MCPConnection

log = logging.getLogger(__name__)


@dataclass
class AdapterResult:
    """Result from external tool execution."""

    success: bool
    output: Any
    error: Optional[str] = None
    tokens_used: int = 0
    execution_time: float = 0.0
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "tokens_used": self.tokens_used,
            "execution_time": self.execution_time,
            "metadata": self.metadata,
        }


class BudgetExceededError(Exception):
    """Raised when token budget is exceeded."""

    pass


class ExternalToolAdapter(ABC):
    """Base wrapper for external tools with budget enforcement.

    Subclasses must implement:
    - tool_name(): Return tool identifier string
    - requires_mcp(): Return True if tool needs MCP connection
    - _invoke_local(): Execute tool locally

    Optional overrides:
    - _invoke_with_mcp(): Execute tool via MCP (required if requires_mcp=True)
    - cleanup(): Custom cleanup logic

    Usage:
        class MyToolAdapter(ExternalToolAdapter):
            def tool_name(self) -> str:
                return "my-tool"

            def requires_mcp(self) -> bool:
                return False

            def _invoke_local(self, input_data, budget) -> Dict:
                # Call external tool
                result = my_tool.process(input_data)
                self._track_tokens(len(str(result)))
                return {"output": result}

        adapter = MyToolAdapter(mcp_pool)
        result = adapter.execute({"content": "..."}, budget_tokens=1000)
    """

    def __init__(self, mcp_pool: Optional["MCPPool"] = None):
        """Initialize adapter.

        Args:
            mcp_pool: MCP connection pool (required if requires_mcp=True)
        """
        self._pool = mcp_pool
        self._active = False
        self._tokens_used = 0
        self._budget_tokens = 0
        self._start_time: Optional[float] = None

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Return tool identifier."""
        ...

    @property
    @abstractmethod
    def requires_mcp(self) -> bool:
        """Return True if tool needs MCP connection."""
        ...

    @property
    def is_active(self) -> bool:
        """Return True if adapter is currently executing."""
        return self._active

    @property
    def tokens_used(self) -> int:
        """Return tokens used in current/last execution."""
        return self._tokens_used

    @property
    def budget_remaining(self) -> int:
        """Return remaining token budget."""
        return max(0, self._budget_tokens - self._tokens_used)

    def _track_tokens(self, count: int):
        """Track token usage, raise if budget exceeded.

        Args:
            count: Number of tokens to track

        Raises:
            BudgetExceededError: If budget would be exceeded
        """
        if self._tokens_used + count > self._budget_tokens:
            raise BudgetExceededError(
                f"{self.tool_name} exceeded token budget: "
                f"{self._tokens_used + count} > {self._budget_tokens}"
            )
        self._tokens_used += count

    def _reset_state(self, budget_tokens: int):
        """Reset adapter state for new execution."""
        self._tokens_used = 0
        self._budget_tokens = budget_tokens
        self._start_time = time.time()
        self._active = True

    def execute(self, input_data: Dict, budget_tokens: int) -> AdapterResult:
        """Execute external tool with budget enforcement.

        Args:
            input_data: Input data for tool
            budget_tokens: Maximum tokens allowed

        Returns:
            AdapterResult with output and metrics
        """
        self._reset_state(budget_tokens)
        log.debug(
            "adapter_execute_start",
            tool=self.tool_name,
            budget=budget_tokens,
        )

        try:
            if self.requires_mcp:
                if not self._pool:
                    raise ValueError(
                        f"{self.tool_name} requires MCP but no pool provided"
                    )
                conn = self._pool.acquire(self.tool_name())
                try:
                    output = self._invoke_with_mcp(conn, input_data, budget_tokens)
                finally:
                    self._pool.release(self.tool_name())
            else:
                output = self._invoke_local(input_data, budget_tokens)

            execution_time = time.time() - (self._start_time or 0)
            log.debug(
                "adapter_execute_success",
                tool=self.tool_name,
                tokens_used=self._tokens_used,
                execution_time=execution_time,
            )

            return AdapterResult(
                success=True,
                output=output,
                tokens_used=self._tokens_used,
                execution_time=execution_time,
                metadata={"tool": self.tool_name},
            )

        except BudgetExceededError as e:
            log.warning("adapter_budget_exceeded", tool=self.tool_name, error=str(e))
            return AdapterResult(
                success=False,
                output=None,
                error=str(e),
                tokens_used=self._tokens_used,
                execution_time=time.time() - (self._start_time or 0),
                metadata={"tool": self.tool_name, "budget_exceeded": True},
            )

        except Exception as e:
            log.error("adapter_execute_error", tool=self.tool_name, error=str(e))
            return AdapterResult(
                success=False,
                output=None,
                error=str(e),
                tokens_used=self._tokens_used,
                execution_time=time.time() - (self._start_time or 0),
                metadata={"tool": self.tool_name},
            )

        finally:
            self._active = False  # END-AFTER-TASK
            log.debug("adapter_execute_end", tool=self.tool_name)

    @abstractmethod
    def _invoke_local(self, input_data: Dict, budget: int) -> Dict:
        """Execute tool locally (subprocess or library).

        Args:
            input_data: Input data for tool
            budget: Token budget

        Returns:
            Dict with tool output
        """
        ...

    def _invoke_with_mcp(
        self, conn: "MCPConnection", input_data: Dict, budget: int
    ) -> Dict:
        """Execute tool via MCP connection.

        Override this method for MCP-based tools.

        Args:
            conn: Active MCP connection
            input_data: Input data for tool
            budget: Token budget

        Returns:
            Dict with tool output
        """
        raise NotImplementedError(
            f"{self.tool_name} requires MCP but _invoke_with_mcp not implemented"
        )

    def cleanup(self):
        """Release any held resources.

        Override for custom cleanup logic.
        """
        self._active = False
        log.debug("adapter_cleanup", tool=self.tool_name)

    def health(self) -> Dict:
        """Return adapter health status."""
        return {
            "tool": self.tool_name,
            "requires_mcp": self.requires_mcp,
            "is_active": self._active,
            "tokens_used": self._tokens_used,
            "budget_tokens": self._budget_tokens,
        }


class LocalToolAdapter(ExternalToolAdapter):
    """Convenience base class for local-only tools (no MCP)."""

    @property
    def requires_mcp(self) -> bool:
        return False


class MCPToolAdapter(ExternalToolAdapter):
    """Convenience base class for MCP-based tools."""

    @property
    def requires_mcp(self) -> bool:
        return True
