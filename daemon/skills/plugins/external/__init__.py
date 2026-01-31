"""External tool adapters for Writer Suite.

This package contains adapters for external tools that integrate
with the Writer Suite facade. Each adapter wraps an external tool
with budget enforcement and end-after-task cleanup.

Adapters:
- proselint_adapter: Prose quality checking (local)
- tapestry_adapter: Content extraction (local)
- cortex_adapter: Claude Cortex memory (MCP)
- content_rw_adapter: Content Research Writer (local)
- ace_adapter: Agentic Context Engine (local)
- skill_seekers_adapter: Docs-to-skills converter (local)

Token Efficiency:
- All adapters enforce budget limits
- End-after-task cleanup via _active flag
- MCP pool limits concurrent connections to 2
- Lazy loading via WriterSuite facade
"""

from .base_adapter import ExternalToolAdapter, AdapterResult, LocalToolAdapter, MCPToolAdapter
from .proselint_adapter import ProselintAdapter
from .tapestry_adapter import TapestryAdapter
from .cortex_adapter import CortexAdapter
from .content_rw_adapter import ContentResearchWriterAdapter
from .ace_adapter import ACEAdapter
from .skill_seekers_adapter import SkillSeekersAdapter

__all__ = [
    # Base classes
    "ExternalToolAdapter",
    "AdapterResult",
    "LocalToolAdapter",
    "MCPToolAdapter",
    # Adapters
    "ProselintAdapter",
    "TapestryAdapter",
    "CortexAdapter",
    "ContentResearchWriterAdapter",
    "ACEAdapter",
    "SkillSeekersAdapter",
]
