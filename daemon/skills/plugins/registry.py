#!/usr/bin/env python3
"""
Plugin Registry - Plugin Discovery and Management

Manages plugin lifecycle:
- Discovery from vendor/plugins directory
- Registration with MessageBus
- Wiring configuration loading
- Plugin instantiation and health tracking

WIRED: 2026-01-30 - International Student Handbook Plugin System
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Type, Any
import yaml
import importlib
from dataclasses import dataclass

# Early binding - CRITICAL for import stability
SKILLS_DIR = Path(__file__).parent
DAEMON_DIR = SKILLS_DIR.parent.parent
sys.path.insert(0, str(DAEMON_DIR))

from core.bus import MessageBus, get_bus, PluginEventType
from config import cfg, setup_logging

log = setup_logging("plugin_registry")


@dataclass
class PluginWiring:
    """Wiring configuration for a plugin."""

    plugin_name: str
    subscribes_to: List[str]
    emits: List[str]
    triggers: List[str]

    @classmethod
    def from_dict(cls, name: str, data: Dict) -> "PluginWiring":
        return cls(
            plugin_name=name,
            subscribes_to=data.get("subscribes", []),
            emits=data.get("emits", []),
            triggers=data.get("triggers", []),
        )


class PluginRegistry:
    """
    Central registry for all plugins.

    Singleton that manages:
    - Plugin discovery and loading
    - Wiring configuration
    - Event subscriptions
    - Health monitoring
    """

    _instance: Optional["PluginRegistry"] = None
    _plugins: Dict[str, "PluginSkill"] = {}
    _wiring: Dict[str, PluginWiring] = {}
    _plugin_classes: Dict[str, Type["PluginSkill"]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._plugins = {}
        self._wiring = {}
        self._plugin_classes = {}
        self._bus = None
        self._initialized = True

    def initialize(self, bus: Optional[MessageBus] = None):
        """Initialize registry with message bus."""
        self._bus = bus or get_bus()
        self._load_wiring()
        self._register_builtin_plugins()
        log.info("plugin_registry_initialized", plugin_count=len(self._plugin_classes))

    def _load_wiring(self):
        """Load wiring configuration from config.yaml."""
        config_path = SKILLS_DIR / "config.yaml"
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
                wiring_config = config.get("wiring", {})
                for name, data in wiring_config.items():
                    self._wiring[name] = PluginWiring.from_dict(name, data)
            log.info("wiring_loaded", plugin_count=len(self._wiring))

    def _register_builtin_plugins(self):
        """Register built-in plugin wrapper classes."""
        # Import plugin wrapper modules
        plugin_modules = [
            # Document Lifecycle (Group A)
            ("document_skills", "DocumentSkillsPlugin"),
            ("book_writer", "BookWriterPlugin"),
            ("ralph_wiggum", "RalphWiggumPlugin"),
            ("claude_mem", "ClaudeMemPlugin"),
            ("context_management", "ContextManagementPlugin"),
            # Visual/Design (Group B)
            ("frontend_design", "FrontendDesignPlugin"),
            ("ui_designer", "UIDesignerPlugin"),
            ("canvas_design", "CanvasDesignPlugin"),
            ("frontend_excellence", "FrontendExcellencePlugin"),
            # Code Quality (Group C)
            ("compound_engineering", "CompoundEngineeringPlugin"),
            ("code_refactoring", "CodeRefactoringPlugin"),
            ("dev_accelerator", "DevAcceleratorPlugin"),
            # Orchestration & Analytics (Group D)
            ("cognitive_orchestration", "CognitiveOrchestrationPlugin"),
            ("queue_orchestrator", "QueueOrchestratorPlugin"),
            ("insight_engine", "InsightEnginePlugin"),
            ("adaptive_learning", "AdaptiveLearningPlugin"),
            # Publishing - WeasyPrint integration
            ("weasyprint_publisher", "WeasyPrintPublisherPlugin"),
            # Writer Suite (Group E) - Unified writing pipeline
            ("writer_suite", "WriterSuite"),
        ]

        for module_name, class_name in plugin_modules:
            try:
                module = importlib.import_module(
                    f"skills.plugins.{module_name}", package="daemon"
                )
                plugin_class = getattr(module, class_name)
                # Register with canonical name (dashes)
                canonical_name = module_name.replace("_", "-")
                self._plugin_classes[canonical_name] = plugin_class
                log.debug("plugin_class_registered", plugin=canonical_name)
            except (ImportError, AttributeError) as e:
                # Plugin not yet implemented - this is OK during development
                log.debug("plugin_class_not_found", plugin=module_name, error=str(e))

    def register_class(self, name: str, plugin_class: Type["PluginSkill"]):
        """Register a plugin class manually."""
        self._plugin_classes[name] = plugin_class
        log.info("plugin_class_registered", plugin=name)

    def get(self, name: str) -> Optional["PluginSkill"]:
        """Get an instantiated plugin by name."""
        # Normalize name (convert underscores to dashes)
        canonical = name.replace("_", "-")

        if canonical not in self._plugins:
            if canonical in self._plugin_classes:
                # Instantiate plugin
                plugin_class = self._plugin_classes[canonical]
                plugin = plugin_class(bus=self._bus)

                # Apply wiring if configured
                if canonical in self._wiring:
                    wiring = self._wiring[canonical]
                    # Override manifest subscriptions with wiring config
                    for event in wiring.subscribes_to:
                        self._bus.subscribe(event, plugin._on_subscribed_event)

                plugin.init()
                self._plugins[canonical] = plugin
                log.info("plugin_instantiated", plugin=canonical)
            else:
                log.warn("plugin_not_found", plugin=canonical)
                return None

        return self._plugins[canonical]

    def get_wiring(self, name: str) -> Optional[PluginWiring]:
        """Get wiring configuration for a plugin."""
        canonical = name.replace("_", "-")
        return self._wiring.get(canonical)

    def list_plugins(self) -> List[str]:
        """List all registered plugin names."""
        return list(self._plugin_classes.keys())

    def list_instantiated(self) -> List[str]:
        """List all instantiated plugin names."""
        return list(self._plugins.keys())

    def health_check(self) -> Dict[str, Dict]:
        """Run health check on all instantiated plugins."""
        return {name: plugin.health() for name, plugin in self._plugins.items()}

    def trigger_plugins(self, plugin_names: List[str], event_data: Dict):
        """
        Trigger a list of plugins with event data.

        Used by wiring system to cascade events.
        """
        for name in plugin_names:
            plugin = self.get(name)
            if plugin:
                plugin._on_subscribed_event(event_data)


# Global registry instance
_registry: Optional[PluginRegistry] = None


def get_registry() -> PluginRegistry:
    """Get or create global registry instance."""
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry


def initialize_plugins(bus: Optional[MessageBus] = None) -> Dict[str, "PluginSkill"]:
    """
    Initialize all plugins and return instantiated dict.

    Args:
        bus: MessageBus to use (global if None)

    Returns:
        Dict mapping plugin names to instances
    """
    registry = get_registry()
    registry.initialize(bus)

    # Instantiate all registered plugins
    plugins = {}
    for name in registry.list_plugins():
        plugin = registry.get(name)
        if plugin:
            plugins[name] = plugin

    log.info("plugins_initialized", count=len(plugins))
    return plugins


def get_plugin(name: str, bus: Optional[MessageBus] = None) -> Optional["PluginSkill"]:
    """
    Get a plugin by name.

    Args:
        name: Plugin name (e.g., "document-skills" or "document_skills")
        bus: MessageBus to use for initialization if needed

    Returns:
        PluginSkill instance or None
    """
    registry = get_registry()
    if not registry._initialized:
        registry.initialize(bus)
    return registry.get(name)


def load_wiring() -> Dict[str, Dict]:
    """
    Load and return wiring configuration.

    Returns:
        Dict mapping plugin names to wiring config dicts
    """
    registry = get_registry()
    if not registry._initialized:
        registry._load_wiring()

    return {
        name: {
            "subscribes": w.subscribes_to,
            "emits": w.emits,
            "triggers": w.triggers,
        }
        for name, w in registry._wiring.items()
    }


# Import PluginSkill for type hints (avoid circular import)
from .wrapper import PluginSkill
