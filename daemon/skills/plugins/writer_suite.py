"""Writer Suite - Unified facade for all writing capabilities.

Token-Efficient Design:
- Stages load lazily (only when needed)
- Each stage closes after completion (end-after-task)
- Max 2 concurrent MCPs via pool
- Event-driven, no polling
- Budget enforcement per stage
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging

# Early binding for import stability
import sys
from pathlib import Path

PLUGINS_DIR = Path(__file__).parent
DAEMON_DIR = PLUGINS_DIR.parent.parent
if str(DAEMON_DIR) not in sys.path:
    sys.path.insert(0, str(DAEMON_DIR))

from skills.plugins.wrapper import PluginSkill, PluginManifest, SkillResult
from skills.plugins.mcp_pool import MCPPool, get_mcp_pool
from core.bus import MessageBus, get_bus, PluginEventType

log = logging.getLogger(__name__)


@dataclass
class StageResult:
    """Result from a pipeline stage."""

    stage: str
    success: bool
    output: Any
    tokens_used: int = 0
    execution_time: float = 0.0
    adapters_used: List[str] = field(default_factory=list)


class WriterSuite(PluginSkill):
    """Unified facade for all writing capabilities.

    Routes tasks to appropriate pipeline stages:
    - research: Content extraction, source analysis
    - write: Draft generation, outlining
    - quality: Prose checking, enhancement
    - memory: Persistent storage across sessions

    Token Efficiency:
    - Lazy stage loading (adapters created on-demand)
    - Stage cleanup after completion
    - Budget allocation per stage
    - MCP pool limits concurrent connections

    Usage:
        suite = WriterSuite(bus)

        # Full writing pipeline
        result = suite.execute({
            "task_type": "full",
            "content": "Topic to write about...",
            "options": {"format": "markdown"}
        }, budget_tokens=10000, budget_tools=50)

        # Quick quality check only
        result = suite.execute({
            "task_type": "quality_check",
            "content": "Text to check..."
        }, budget_tokens=2000, budget_tools=10)

        # Research only
        result = suite.execute({
            "task_type": "research_only",
            "url": "https://example.com/article"
        }, budget_tokens=3000, budget_tools=15)
    """

    # Stage definitions with adapters and budget allocation
    STAGES = {
        "research": {
            "adapters": ["tapestry", "skill-seekers"],
            "budget_ratio": 0.3,  # 30% of total budget
            "timeout": 120,
        },
        "write": {
            "adapters": ["content-research-writer", "book-writer"],
            "budget_ratio": 0.5,  # 50% of total budget
            "timeout": 180,
        },
        "quality": {
            "adapters": ["proselint", "ralph-wiggum"],
            "budget_ratio": 0.15,  # 15% of total budget
            "timeout": 60,
        },
        "memory": {
            "adapters": ["claude-cortex"],
            "budget_ratio": 0.05,  # 5% of total budget
            "timeout": 30,
        },
    }

    # Task type to stage mapping
    TASK_ROUTES = {
        "full": ["research", "write", "quality", "memory"],
        "research_only": ["research"],
        "write_only": ["write"],
        "quality_check": ["quality"],
        "research_write": ["research", "write"],
        "write_quality": ["write", "quality"],
    }

    def __init__(self, bus: Optional[MessageBus] = None):
        super().__init__(bus)
        self._mcp_pool = get_mcp_pool(max_connections=2)
        self._loaded_stages: Dict[str, List] = {}
        self._active_stage: Optional[str] = None
        self._stage_results: List[StageResult] = []

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="writer-suite",
            version="1.0.0",
            description="Unified facade for writing capabilities with token-efficient staging",
            category="publish",
            plato_tier="IV.B",
            task_types=["write", "research", "quality", "full_pipeline"],
            input_formats=["text", "url", "structured_json"],
            output_formats=["markdown", "html", "structured_json"],
            default_token_budget=10000,
            default_tool_budget=50,
            max_execution_time=600,
            subscribes_to=["task.write", "task.research", "task.quality"],
            emits=[
                "writer.stage_started",
                "writer.stage_completed",
                "writer.pipeline_done",
            ],
            triggers=["book-writer", "ralph-wiggum", "weasyprint-publisher"],
        )

    def _invoke_plugin(
        self, input_data: Dict, budget_tokens: int, budget_tools: int
    ) -> Dict:
        """Execute writing pipeline.

        Args:
            input_data: {
                "task_type": str - Route selector (full, research_only, etc.)
                "content": str - Content to process
                "url": str - URL to extract (for research)
                "options": Dict - Additional options
            }
            budget_tokens: Total token budget
            budget_tools: Total tool budget

        Returns:
            Combined results from all stages
        """
        task_type = input_data.get("task_type", "full")
        stages = self.TASK_ROUTES.get(task_type, ["full"])

        log.info(
            "writer_suite_start",
            task_type=task_type,
            stages=stages,
            budget_tokens=budget_tokens,
        )

        # Track overall metrics
        self._stage_results = []
        total_tokens = 0
        pipeline_start = time.time()

        # Execute each stage
        stage_data = input_data.copy()
        final_output = {}

        for stage_name in stages:
            if total_tokens >= budget_tokens:
                log.warning("writer_suite_budget_exhausted", stage=stage_name)
                break

            # Calculate stage budget
            stage_config = self.STAGES.get(stage_name, {})
            stage_budget = int(budget_tokens * stage_config.get("budget_ratio", 0.25))
            remaining_budget = budget_tokens - total_tokens
            stage_budget = min(stage_budget, remaining_budget)

            # Run stage
            stage_result = self._run_stage(
                stage_name, stage_data, stage_budget, budget_tools
            )
            self._stage_results.append(stage_result)
            total_tokens += stage_result.tokens_used

            # Pass output to next stage
            if stage_result.success and stage_result.output:
                stage_data.update(stage_result.output)
                final_output[stage_name] = stage_result.output

        # Compile final result
        pipeline_time = time.time() - pipeline_start

        result = {
            "task_type": task_type,
            "stages_completed": [r.stage for r in self._stage_results if r.success],
            "stages_failed": [r.stage for r in self._stage_results if not r.success],
            "total_tokens_used": total_tokens,
            "pipeline_time": pipeline_time,
            "output": final_output,
            "stage_details": [
                {
                    "stage": r.stage,
                    "success": r.success,
                    "tokens": r.tokens_used,
                    "time": r.execution_time,
                    "adapters": r.adapters_used,
                }
                for r in self._stage_results
            ],
        }

        # Emit pipeline completion
        self.emit_domain_event("writer.pipeline_done", {
            "task_type": task_type,
            "stages_completed": len([r for r in self._stage_results if r.success]),
            "total_tokens": total_tokens,
            "execution_time": pipeline_time,
        })

        log.info(
            "writer_suite_complete",
            task_type=task_type,
            stages_completed=len([r for r in self._stage_results if r.success]),
            total_tokens=total_tokens,
        )

        return result

    def _run_stage(
        self, stage_name: str, data: Dict, budget: int, tool_budget: int
    ) -> StageResult:
        """Run a single pipeline stage.

        Args:
            stage_name: Name of stage to run
            data: Input data for stage
            budget: Token budget for stage
            tool_budget: Tool budget for stage

        Returns:
            StageResult with output and metrics
        """
        self._active_stage = stage_name
        start_time = time.time()
        tokens_used = 0
        adapters_used = []

        log.debug("writer_stage_start", stage=stage_name, budget=budget)

        # Emit stage start
        self.emit_domain_event("writer.stage_started", {
            "stage": stage_name,
            "budget_tokens": budget,
        })

        try:
            # Lazy load adapters for this stage
            adapters = self._lazy_load_stage(stage_name)

            # Execute adapters in sequence
            stage_output = {}
            adapter_data = data.copy()

            for adapter in adapters:
                if tokens_used >= budget:
                    log.warning("stage_budget_exhausted", stage=stage_name)
                    break

                adapter_budget = (budget - tokens_used) // max(1, len(adapters) - len(adapters_used))

                try:
                    result = adapter.execute(adapter_data, adapter_budget)
                    tokens_used += result.tokens_used
                    adapters_used.append(adapter.tool_name)

                    if result.success and result.output:
                        adapter_data.update(result.output)
                        stage_output.update(result.output)

                except Exception as e:
                    log.warning(
                        "adapter_error",
                        stage=stage_name,
                        adapter=adapter.tool_name,
                        error=str(e),
                    )

            # Emit stage completion
            execution_time = time.time() - start_time
            self.emit_domain_event("writer.stage_completed", {
                "stage": stage_name,
                "tokens_used": tokens_used,
                "execution_time": execution_time,
                "adapters": adapters_used,
            })

            return StageResult(
                stage=stage_name,
                success=True,
                output=stage_output,
                tokens_used=tokens_used,
                execution_time=execution_time,
                adapters_used=adapters_used,
            )

        except Exception as e:
            log.error("stage_error", stage=stage_name, error=str(e))
            return StageResult(
                stage=stage_name,
                success=False,
                output={"error": str(e)},
                tokens_used=tokens_used,
                execution_time=time.time() - start_time,
                adapters_used=adapters_used,
            )

        finally:
            # END-AFTER-TASK: Close stage resources
            self._close_stage(stage_name)
            self._active_stage = None

    def _lazy_load_stage(self, stage_name: str) -> List:
        """Lazy load adapters for a stage.

        Args:
            stage_name: Name of stage to load

        Returns:
            List of adapter instances
        """
        if stage_name in self._loaded_stages:
            return self._loaded_stages[stage_name]

        stage_config = self.STAGES.get(stage_name, {})
        adapter_names = stage_config.get("adapters", [])
        adapters = []

        for adapter_name in adapter_names:
            adapter = self._create_adapter(adapter_name)
            if adapter:
                adapters.append(adapter)

        self._loaded_stages[stage_name] = adapters
        log.debug("stage_loaded", stage=stage_name, adapters=len(adapters))

        return adapters

    def _create_adapter(self, adapter_name: str):
        """Create adapter instance by name.

        Args:
            adapter_name: Name of adapter to create

        Returns:
            Adapter instance or None
        """
        try:
            if adapter_name == "proselint":
                from skills.plugins.external.proselint_adapter import ProselintAdapter
                return ProselintAdapter(self._mcp_pool)

            elif adapter_name == "tapestry":
                from skills.plugins.external.tapestry_adapter import TapestryAdapter
                return TapestryAdapter(self._mcp_pool)

            elif adapter_name == "claude-cortex":
                from skills.plugins.external.cortex_adapter import CortexAdapter
                return CortexAdapter(self._mcp_pool)

            elif adapter_name == "content-research-writer":
                from skills.plugins.external.content_rw_adapter import ContentResearchWriterAdapter
                return ContentResearchWriterAdapter(self._mcp_pool)

            elif adapter_name == "ace":
                from skills.plugins.external.ace_adapter import ACEAdapter
                return ACEAdapter(self._mcp_pool)

            elif adapter_name == "skill-seekers":
                from skills.plugins.external.skill_seekers_adapter import SkillSeekersAdapter
                return SkillSeekersAdapter(self._mcp_pool)

            elif adapter_name == "book-writer":
                # Use existing plugin
                from skills.plugins.registry import get_plugin
                return get_plugin("book-writer", self.bus)

            elif adapter_name == "ralph-wiggum":
                # Use existing plugin
                from skills.plugins.registry import get_plugin
                return get_plugin("ralph-wiggum", self.bus)

            else:
                log.warning("unknown_adapter", adapter=adapter_name)
                return None

        except ImportError as e:
            log.warning("adapter_import_error", adapter=adapter_name, error=str(e))
            return None

    def _close_stage(self, stage_name: str):
        """Close stage and release resources.

        Args:
            stage_name: Name of stage to close
        """
        if stage_name in self._loaded_stages:
            for adapter in self._loaded_stages[stage_name]:
                try:
                    if hasattr(adapter, "cleanup"):
                        adapter.cleanup()
                except Exception as e:
                    log.warning(
                        "adapter_cleanup_error",
                        stage=stage_name,
                        error=str(e),
                    )

            del self._loaded_stages[stage_name]
            log.debug("stage_closed", stage=stage_name)

        # Emit stage closed event
        self.emit_domain_event(f"writer.{stage_name}_closed", {
            "stage": stage_name,
            "resources_released": True,
        })

    def _run_full_pipeline(self, data: Dict, budget: int) -> Dict:
        """Run complete writing pipeline.

        Shortcut for task_type="full".
        """
        return self._invoke_plugin(
            {"task_type": "full", **data},
            budget,
            50,
        )

    def get_stage_status(self) -> Dict:
        """Get current status of all stages."""
        return {
            "active_stage": self._active_stage,
            "loaded_stages": list(self._loaded_stages.keys()),
            "mcp_pool": self._mcp_pool.status(),
            "stage_results": [
                {"stage": r.stage, "success": r.success, "tokens": r.tokens_used}
                for r in self._stage_results
            ],
        }

    def cleanup(self):
        """Cleanup all resources."""
        # Close all loaded stages
        for stage_name in list(self._loaded_stages.keys()):
            self._close_stage(stage_name)

        # Reset state
        self._stage_results = []
        self._active_stage = None

        log.info("writer_suite_cleanup")


# Convenience functions
def get_writer_suite(bus: Optional[MessageBus] = None) -> WriterSuite:
    """Get WriterSuite instance."""
    return WriterSuite(bus or get_bus())


def write_content(
    content: str,
    task_type: str = "full",
    budget_tokens: int = 10000,
    options: Optional[Dict] = None,
) -> Dict:
    """Convenience function for writing content.

    Args:
        content: Content to process
        task_type: Pipeline route (full, quality_check, etc.)
        budget_tokens: Token budget
        options: Additional options

    Returns:
        Pipeline result dict
    """
    suite = get_writer_suite()
    return suite.execute(
        {
            "task_type": task_type,
            "content": content,
            "options": options or {},
        },
        budget_tokens=budget_tokens,
        budget_tools=50,
    ).output
