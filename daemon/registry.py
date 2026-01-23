#!/usr/bin/env python3
"""Module Registry - Cross-domain integration for unified personal AI.

Registers domain modules with GoalCoherenceLayer and enables:
- Cross-domain constraint propagation
- Coherence checking across all modules
- Context sharing between domains
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from coherence import GoalCoherenceLayer, GoalTimeframe, Constraint
from modules.base import BaseModule, FinanceModule, CalendarModule, TasksModule


class ModuleRegistry:
    """Central registry for all domain modules."""

    def __init__(self, coherence_layer: Optional[GoalCoherenceLayer] = None):
        self.gcl = coherence_layer or GoalCoherenceLayer()
        self._modules: Dict[str, BaseModule] = {}

    def register(self, module: BaseModule) -> None:
        """Register a module and wire it to coherence layer."""
        self._modules[module.name] = module
        self.gcl.register_module(module.name, module)

    def get(self, name: str) -> Optional[BaseModule]:
        return self._modules.get(name)

    def all_modules(self) -> List[str]:
        return list(self._modules.keys())

    def check_action(self, domain: str, action: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Check action coherence across all domains."""
        issues = []

        # Check domain-specific
        if domain in self._modules:
            valid, reason = self._modules[domain].validate_action(action)
            if not valid:
                issues.append(f"[{domain}] {reason}")

        # Check cross-domain via coherence layer
        coherent, gcl_issues = self.gcl.check_coherence(domain, action)
        issues.extend(gcl_issues)

        # Check other modules that might be affected
        for name, module in self._modules.items():
            if name != domain:
                context = module.get_context_for(domain)
                if context.get("constraint") == "minimize spending" and action.get("cost", 0) > 100:
                    issues.append(f"[{name}] Budget tight - cost exceeds threshold")

        return len(issues) == 0, issues

    def get_unified_context(self) -> Dict[str, Any]:
        """Get context from all modules for decision making."""
        context = {}
        for name, module in self._modules.items():
            context[name] = module.get_context_for("unified")
        return context

    def propagate_constraint(self, constraint: Constraint, to_domains: List[str]) -> None:
        """Propagate a constraint to multiple domains."""
        for domain in to_domains:
            if domain in self._modules:
                self._modules[domain].add_constraint(constraint)


def create_default_registry() -> ModuleRegistry:
    """Create registry with standard modules."""
    registry = ModuleRegistry()
    registry.register(FinanceModule())
    registry.register(CalendarModule())
    registry.register(TasksModule())
    return registry


# --- CLI ---

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Module Registry CLI")
    subparsers = parser.add_subparsers(dest="command")

    # List modules
    subparsers.add_parser("list", help="List registered modules")

    # Check action
    check_parser = subparsers.add_parser("check", help="Check action coherence")
    check_parser.add_argument("domain", help="Domain performing action")
    check_parser.add_argument("--action", required=True, help="Action as JSON")

    # Get context
    subparsers.add_parser("context", help="Get unified context")

    # Test constraint propagation
    prop_parser = subparsers.add_parser("propagate", help="Test constraint propagation")
    prop_parser.add_argument("--type", required=True, help="Constraint type")
    prop_parser.add_argument("--value", required=True, help="Constraint value")
    prop_parser.add_argument("--domains", required=True, help="Comma-separated domains")

    args = parser.parse_args()
    registry = create_default_registry()

    if args.command == "list":
        print("Registered modules:")
        for name in registry.all_modules():
            print(f"  - {name}")

    elif args.command == "check":
        action = json.loads(args.action)
        valid, issues = registry.check_action(args.domain, action)
        print(f"Valid: {valid}")
        if issues:
            print("Issues:")
            for issue in issues:
                print(f"  - {issue}")

    elif args.command == "context":
        context = registry.get_unified_context()
        print(json.dumps(context, indent=2))

    elif args.command == "propagate":
        domains = [d.strip() for d in args.domains.split(",")]
        constraint = Constraint(
            id="test",
            source_goal="manual",
            domain="all",
            type=args.type,
            value=args.value,
            priority=1,
            active=True
        )
        registry.propagate_constraint(constraint, domains)
        print(f"Propagated {args.type} constraint to: {domains}")

    else:
        parser.print_help()
