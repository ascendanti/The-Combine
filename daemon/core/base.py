#!/usr/bin/env python3
"""
Base classes for unified subsystem architecture.

All daemon modules should implement these interfaces for coherence.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
import hashlib
import json


@dataclass
class Signal:
    """Universal signal type for all subsystems"""
    signal_id: str
    source: str          # Which subsystem generated
    type: str            # observation, decision, outcome, prediction, alert
    content: Any
    confidence: float = 1.0    # 0.0 - 1.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict = field(default_factory=dict)

    @classmethod
    def create(cls, source: str, type: str, content: Any, confidence: float = 1.0, metadata: Dict = None):
        """Factory method to create signal with auto-generated ID"""
        signal_id = f"sig_{hashlib.md5(f'{source}_{type}_{datetime.now().isoformat()}'.encode()).hexdigest()[:12]}"
        return cls(
            signal_id=signal_id,
            source=source,
            type=type,
            content=content,
            confidence=confidence,
            metadata=metadata or {}
        )

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class Action:
    """Universal action type"""
    action_id: str
    target: str          # Which subsystem or external
    operation: str
    parameters: Dict = field(default_factory=dict)
    priority: int = 5    # 1-10, higher = more urgent
    status: str = "pending"  # pending, in_progress, completed, failed
    deadline: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None

    @classmethod
    def create(cls, target: str, operation: str, parameters: Dict = None, priority: int = 5):
        """Factory method to create action with auto-generated ID"""
        action_id = f"act_{hashlib.md5(f'{target}_{operation}_{datetime.now().isoformat()}'.encode()).hexdigest()[:12]}"
        return cls(
            action_id=action_id,
            target=target,
            operation=operation,
            parameters=parameters or {},
            priority=priority
        )

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class Outcome:
    """Universal outcome type"""
    outcome_id: str
    action_id: str
    result: str          # success, partial, failure
    metrics: Dict = field(default_factory=dict)
    learnings: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @classmethod
    def create(cls, action_id: str, result: str, metrics: Dict = None, learnings: List[str] = None):
        """Factory method to create outcome with auto-generated ID"""
        outcome_id = f"out_{hashlib.md5(f'{action_id}_{result}_{datetime.now().isoformat()}'.encode()).hexdigest()[:12]}"
        return cls(
            outcome_id=outcome_id,
            action_id=action_id,
            result=result,
            metrics=metrics or {},
            learnings=learnings or []
        )

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class Learning:
    """Universal learning type"""
    learning_id: str
    source: str          # Which subsystem generated
    content: str         # The actual learning
    context: str = ""    # What it relates to
    confidence: float = 0.8
    applied: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: List[str] = field(default_factory=list)

    @classmethod
    def create(cls, source: str, content: str, context: str = "", confidence: float = 0.8, tags: List[str] = None):
        """Factory method to create learning with auto-generated ID"""
        learning_id = f"lrn_{hashlib.md5(f'{source}_{content[:50]}_{datetime.now().isoformat()}'.encode()).hexdigest()[:12]}"
        return cls(
            learning_id=learning_id,
            source=source,
            content=content,
            context=context,
            confidence=confidence,
            tags=tags or []
        )

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class Subsystem(ABC):
    """Base class for all subsystems.

    Implementing this interface ensures:
    - Consistent initialization patterns
    - Unified signal/action/outcome handling
    - Built-in learning and adaptation
    - Standardized health reporting
    """

    def __init__(self, name: str):
        self.name = name
        self.initialized = False
        self.signals_received = 0
        self.actions_generated = 0
        self.learnings_extracted = 0

    @abstractmethod
    def init(self) -> None:
        """Initialize subsystem resources.

        Called once at startup. Should:
        - Connect to databases
        - Load configuration
        - Initialize models/caches
        """
        pass

    @abstractmethod
    def process(self, signal: Signal) -> Optional[Action]:
        """Process incoming signal, optionally return action.

        This is the main processing logic:
        - Receive signal from bus
        - Analyze and decide
        - Optionally generate action

        Returns None if no action needed.
        """
        pass

    @abstractmethod
    def learn(self, outcome: Outcome) -> List[Learning]:
        """Learn from outcome, return learnings.

        Called after an action completes:
        - Analyze what happened
        - Extract patterns
        - Generate learnings for adaptation
        """
        pass

    @abstractmethod
    def adapt(self, learnings: List[Learning]) -> None:
        """Modify behavior based on learnings.

        Apply learnings to improve:
        - Update internal parameters
        - Modify decision rules
        - Adjust thresholds
        """
        pass

    @abstractmethod
    def report(self) -> Dict:
        """Return current state/insights.

        Provide summary of:
        - Current status
        - Key metrics
        - Recent insights
        """
        pass

    def health(self) -> Dict:
        """Return health metrics.

        Default implementation tracks basic metrics.
        Override for custom health checks.
        """
        return {
            "name": self.name,
            "initialized": self.initialized,
            "signals_received": self.signals_received,
            "actions_generated": self.actions_generated,
            "learnings_extracted": self.learnings_extracted,
            "status": "healthy" if self.initialized else "not_initialized"
        }

    def emit_signal(self, type: str, content: Any, confidence: float = 1.0, metadata: Dict = None) -> Signal:
        """Convenience method to emit a signal from this subsystem."""
        return Signal.create(
            source=self.name,
            type=type,
            content=content,
            confidence=confidence,
            metadata=metadata
        )

    def emit_action(self, target: str, operation: str, parameters: Dict = None, priority: int = 5) -> Action:
        """Convenience method to emit an action from this subsystem."""
        self.actions_generated += 1
        return Action.create(
            target=target,
            operation=operation,
            parameters=parameters,
            priority=priority
        )

    def emit_learning(self, content: str, context: str = "", confidence: float = 0.8, tags: List[str] = None) -> Learning:
        """Convenience method to emit a learning from this subsystem."""
        self.learnings_extracted += 1
        return Learning.create(
            source=self.name,
            content=content,
            context=context,
            confidence=confidence,
            tags=tags
        )


class SubsystemRegistry:
    """Registry for all active subsystems."""

    _instance = None
    _subsystems: Dict[str, Subsystem] = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, subsystem: Subsystem) -> None:
        """Register a subsystem."""
        self._subsystems[subsystem.name] = subsystem

    def get(self, name: str) -> Optional[Subsystem]:
        """Get subsystem by name."""
        return self._subsystems.get(name)

    def all(self) -> List[Subsystem]:
        """Get all registered subsystems."""
        return list(self._subsystems.values())

    def health_check(self) -> Dict:
        """Run health check on all subsystems."""
        return {
            name: subsystem.health()
            for name, subsystem in self._subsystems.items()
        }
