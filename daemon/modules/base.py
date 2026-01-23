"""Base module template implementing CoherenceInterface."""

from typing import List, Dict, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
import sys
sys.path.append('..')
from coherence import Constraint


class BaseModule(ABC):
    """Base class for domain modules. Implements CoherenceInterface."""

    def __init__(self, name: str):
        self.name = name
        self._constraints: List[Constraint] = []

    @abstractmethod
    def get_constraints(self) -> List[Constraint]:
        """Return active constraints from this domain."""
        return self._constraints

    @abstractmethod
    def validate_action(self, action: Dict[str, Any]) -> tuple[bool, str]:
        """Validate if action is coherent with domain rules."""
        pass

    @abstractmethod
    def get_context_for(self, domain: str) -> Dict[str, Any]:
        """Return context relevant to another domain."""
        pass

    def add_constraint(self, constraint: Constraint):
        self._constraints.append(constraint)


class FinanceModule(BaseModule):
    """Finance domain module."""

    def __init__(self):
        super().__init__("finance")
        self.budget_remaining = 0
        self.monthly_target = 0

    def get_constraints(self) -> List[Constraint]:
        return self._constraints

    def validate_action(self, action: Dict[str, Any]) -> tuple[bool, str]:
        if "cost" in action:
            if action["cost"] > self.budget_remaining:
                return False, f"Exceeds budget by {action['cost'] - self.budget_remaining}"
        return True, ""

    def get_context_for(self, domain: str) -> Dict[str, Any]:
        return {
            "budget_remaining": self.budget_remaining,
            "monthly_target": self.monthly_target,
            "constraint": "minimize spending" if self.budget_remaining < 500 else "normal"
        }


class CalendarModule(BaseModule):
    """Calendar domain module."""

    def __init__(self):
        super().__init__("calendar")
        self.busy_times = []
        self.preferences = {}

    def get_constraints(self) -> List[Constraint]:
        return self._constraints

    def validate_action(self, action: Dict[str, Any]) -> tuple[bool, str]:
        if "time" in action:
            for start, end in self.busy_times:
                if start <= action["time"] <= end:
                    return False, f"Time conflict with existing event"
        return True, ""

    def get_context_for(self, domain: str) -> Dict[str, Any]:
        return {
            "busy_times": self.busy_times,
            "next_free_slot": self._find_next_free(),
            "preferences": self.preferences
        }

    def _find_next_free(self):
        # Simplified - would check calendar
        return "tomorrow 2pm"


class TasksModule(BaseModule):
    """Tasks domain module."""

    def __init__(self):
        super().__init__("tasks")
        self.pending = []
        self.energy_level = "normal"

    def get_constraints(self) -> List[Constraint]:
        return self._constraints

    def validate_action(self, action: Dict[str, Any]) -> tuple[bool, str]:
        if action.get("requires_energy") == "high" and self.energy_level == "low":
            return False, "Energy too low for high-energy task"
        return True, ""

    def get_context_for(self, domain: str) -> Dict[str, Any]:
        return {
            "pending_count": len(self.pending),
            "energy_level": self.energy_level,
            "top_priority": self.pending[0] if self.pending else None
        }
