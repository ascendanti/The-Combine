"""
Atlas Spine - Deterministic Orchestration Layer

Provides:
- MAP: Structured knowledge representation
- Operators: LOOKUP, OPEN, PATCH, DIAGNOSE, TEST, THINK
- Router: Rule-based first, LocalAI fallback
- Event Store: Append-only audit logs
- Playbooks: No-think diagnosis guides
- CLI: atlas route "request"

Token-efficient: Uses LLM only when necessary.
"""

from .map import AtlasMap
from .router import AtlasRouter
from .events import EventStore
from .operators import Operators

__all__ = ['AtlasMap', 'AtlasRouter', 'EventStore', 'Operators']
__version__ = '1.0.0'
