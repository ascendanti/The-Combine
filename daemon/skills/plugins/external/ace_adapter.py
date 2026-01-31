"""Agentic Context Engine (ACE) adapter.

Self-improving agent capabilities:
- Learn from execution feedback
- Maintain evolving Skillbook
- Pattern detection from failures
- No fine-tuning required
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

from .base_adapter import LocalToolAdapter

log = logging.getLogger(__name__)


@dataclass
class SkillEntry:
    """An entry in the Skillbook."""

    skill_id: str
    name: str
    description: str
    success_count: int = 0
    failure_count: int = 0
    last_used: float = field(default_factory=time.time)
    patterns: List[str] = field(default_factory=list)
    context: Dict = field(default_factory=dict)
    confidence: float = 0.5

    def to_dict(self) -> Dict:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "last_used": self.last_used,
            "patterns": self.patterns,
            "context": self.context,
            "confidence": self.confidence,
        }

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.5


class ACEAdapter(LocalToolAdapter):
    """Adapter for Agentic Context Engine.

    Provides self-improving capabilities:
    - Record execution outcomes
    - Learn from successes and failures
    - Evolve Skillbook over time
    - Pattern detection

    Usage:
        adapter = ACEAdapter()

        # Record success
        adapter.execute({
            "operation": "record",
            "task_id": "write-chapter",
            "outcome": "success",
            "context": {"topic": "AI", "length": 500}
        }, budget_tokens=500)

        # Get recommendations
        adapter.execute({
            "operation": "recommend",
            "task_type": "write-chapter",
            "context": {"topic": "ML"}
        }, budget_tokens=1000)

        # Analyze patterns
        adapter.execute({
            "operation": "analyze",
            "focus": "failures"
        }, budget_tokens=1500)
    """

    def __init__(self, mcp_pool=None):
        super().__init__(mcp_pool)
        self._skillbook: Dict[str, SkillEntry] = {}
        self._execution_log: List[Dict] = []
        self._patterns: List[Dict] = []

    @property
    def tool_name(self) -> str:
        return "ace"

    def _invoke_local(self, input_data: Dict, budget: int) -> Dict:
        """Execute ACE operation.

        Args:
            input_data: {
                "operation": "record" | "recommend" | "analyze" | "reflect",
                ...task-specific params
            }
            budget: Token budget

        Returns:
            Operation-specific output
        """
        operation = input_data.get("operation", "record")
        self._track_tokens(50)

        if operation == "record":
            return self._record_outcome(input_data)
        elif operation == "recommend":
            return self._get_recommendations(input_data)
        elif operation == "analyze":
            return self._analyze_patterns(input_data)
        elif operation == "reflect":
            return self._reflect(input_data)
        elif operation == "skillbook":
            return self._get_skillbook()
        else:
            return {"error": f"Unknown operation: {operation}"}

    def _record_outcome(self, input_data: Dict) -> Dict:
        """Record task execution outcome."""
        task_id = input_data.get("task_id", "unknown")
        task_type = input_data.get("task_type", task_id.split("-")[0] if "-" in task_id else "generic")
        outcome = input_data.get("outcome", "unknown")  # success, failure, partial
        context = input_data.get("context", {})
        error = input_data.get("error")
        metrics = input_data.get("metrics", {})

        # Log execution
        log_entry = {
            "task_id": task_id,
            "task_type": task_type,
            "outcome": outcome,
            "context": context,
            "error": error,
            "metrics": metrics,
            "timestamp": time.time(),
        }
        self._execution_log.append(log_entry)

        # Update skillbook
        if task_type not in self._skillbook:
            self._skillbook[task_type] = SkillEntry(
                skill_id=f"skill-{task_type}",
                name=task_type,
                description=f"Skill for {task_type} tasks",
            )

        skill = self._skillbook[task_type]
        skill.last_used = time.time()

        if outcome == "success":
            skill.success_count += 1
            skill.confidence = min(1.0, skill.confidence + 0.05)
            # Extract success pattern
            if context:
                pattern = f"success:{json.dumps(context)[:50]}"
                if pattern not in skill.patterns:
                    skill.patterns.append(pattern)
        elif outcome == "failure":
            skill.failure_count += 1
            skill.confidence = max(0.1, skill.confidence - 0.1)
            # Extract failure pattern
            if error:
                pattern = f"failure:{error[:50]}"
                if pattern not in skill.patterns:
                    skill.patterns.append(pattern)
                # Record for pattern analysis
                self._patterns.append({
                    "type": "failure",
                    "task_type": task_type,
                    "error": error,
                    "context": context,
                    "timestamp": time.time(),
                })

        self._track_tokens(len(json.dumps(log_entry)) // 4)

        return {
            "recorded": True,
            "skill_updated": task_type,
            "current_confidence": skill.confidence,
            "success_rate": skill.success_rate,
        }

    def _get_recommendations(self, input_data: Dict) -> Dict:
        """Get recommendations for a task."""
        task_type = input_data.get("task_type", "")
        context = input_data.get("context", {})

        self._track_tokens(50)

        recommendations = []

        # Check skillbook for relevant skills
        if task_type in self._skillbook:
            skill = self._skillbook[task_type]
            recommendations.append({
                "source": "skillbook",
                "skill": skill.name,
                "confidence": skill.confidence,
                "success_rate": skill.success_rate,
                "suggestion": f"Use established approach (confidence: {skill.confidence:.0%})",
            })

            # Add pattern-based suggestions
            for pattern in skill.patterns:
                if pattern.startswith("success:"):
                    recommendations.append({
                        "source": "pattern",
                        "type": "success_pattern",
                        "suggestion": f"Previously worked with: {pattern[8:]}",
                    })
                elif pattern.startswith("failure:"):
                    recommendations.append({
                        "source": "pattern",
                        "type": "avoid_pattern",
                        "suggestion": f"Avoid: {pattern[8:]}",
                    })

        # Check for similar contexts in execution log
        similar = self._find_similar_contexts(task_type, context)
        for entry in similar[:3]:
            recommendations.append({
                "source": "history",
                "task_id": entry["task_id"],
                "outcome": entry["outcome"],
                "suggestion": f"Similar task had {entry['outcome']} outcome",
            })

        output = {
            "task_type": task_type,
            "recommendations": recommendations,
            "confidence_level": self._skillbook.get(task_type, SkillEntry("", "", "")).confidence,
        }

        self._track_tokens(len(json.dumps(output)) // 4)
        return output

    def _analyze_patterns(self, input_data: Dict) -> Dict:
        """Analyze patterns in execution history."""
        focus = input_data.get("focus", "all")  # all, failures, successes
        limit = input_data.get("limit", 10)

        self._track_tokens(100)

        analysis = {
            "total_executions": len(self._execution_log),
            "skills_learned": len(self._skillbook),
            "patterns_detected": [],
        }

        # Count outcomes
        outcomes = {"success": 0, "failure": 0, "partial": 0}
        for entry in self._execution_log:
            outcome = entry.get("outcome", "unknown")
            if outcome in outcomes:
                outcomes[outcome] += 1

        analysis["outcome_distribution"] = outcomes

        # Analyze failure patterns
        if focus in ["all", "failures"]:
            failure_patterns = self._detect_failure_patterns()
            analysis["patterns_detected"].extend(failure_patterns[:limit])

        # Analyze success patterns
        if focus in ["all", "successes"]:
            success_patterns = self._detect_success_patterns()
            analysis["patterns_detected"].extend(success_patterns[:limit])

        # Skills by confidence
        skills_ranked = sorted(
            self._skillbook.values(),
            key=lambda s: s.confidence,
            reverse=True
        )
        analysis["top_skills"] = [
            {"name": s.name, "confidence": s.confidence, "success_rate": s.success_rate}
            for s in skills_ranked[:5]
        ]

        self._track_tokens(len(json.dumps(analysis)) // 4)
        return analysis

    def _reflect(self, input_data: Dict) -> Dict:
        """Generate reflection on recent performance."""
        window = input_data.get("window", 10)  # Last N executions

        recent = self._execution_log[-window:] if self._execution_log else []
        if not recent:
            return {"reflection": "No execution history to reflect on."}

        # Calculate recent metrics
        successes = sum(1 for e in recent if e.get("outcome") == "success")
        failures = sum(1 for e in recent if e.get("outcome") == "failure")
        success_rate = successes / len(recent)

        # Generate insights
        insights = []

        if success_rate > 0.8:
            insights.append("Performance is strong. Current approaches are working well.")
        elif success_rate < 0.5:
            insights.append("Performance needs improvement. Consider reviewing failure patterns.")

        # Identify common failure contexts
        failure_contexts = [e.get("context", {}) for e in recent if e.get("outcome") == "failure"]
        if failure_contexts:
            common_keys = set.intersection(*[set(c.keys()) for c in failure_contexts if c])
            if common_keys:
                insights.append(f"Failures share common context keys: {list(common_keys)}")

        reflection = {
            "window": window,
            "recent_success_rate": success_rate,
            "successes": successes,
            "failures": failures,
            "insights": insights,
            "recommendation": "Continue current approach" if success_rate > 0.7 else "Review and adjust strategy",
        }

        self._track_tokens(len(json.dumps(reflection)) // 4)
        return reflection

    def _get_skillbook(self) -> Dict:
        """Return full skillbook."""
        skills = [skill.to_dict() for skill in self._skillbook.values()]
        self._track_tokens(len(json.dumps(skills)) // 4)
        return {
            "skill_count": len(skills),
            "skills": skills,
        }

    def _find_similar_contexts(self, task_type: str, context: Dict) -> List[Dict]:
        """Find executions with similar context."""
        similar = []
        context_keys = set(context.keys())

        for entry in reversed(self._execution_log):
            if entry.get("task_type") == task_type:
                entry_keys = set(entry.get("context", {}).keys())
                overlap = len(context_keys & entry_keys)
                if overlap > 0:
                    similar.append(entry)

        return similar[:5]

    def _detect_failure_patterns(self) -> List[Dict]:
        """Detect patterns in failures."""
        patterns = []
        error_counts = {}

        for pattern in self._patterns:
            if pattern.get("type") == "failure":
                error = pattern.get("error", "unknown")[:30]
                error_counts[error] = error_counts.get(error, 0) + 1

        for error, count in sorted(error_counts.items(), key=lambda x: -x[1]):
            if count >= 2:
                patterns.append({
                    "pattern_type": "recurring_error",
                    "description": error,
                    "occurrences": count,
                    "severity": "high" if count >= 5 else "medium",
                })

        return patterns

    def _detect_success_patterns(self) -> List[Dict]:
        """Detect patterns in successes."""
        patterns = []

        # Find high-confidence skills
        for skill in self._skillbook.values():
            if skill.success_rate > 0.8 and skill.success_count >= 3:
                patterns.append({
                    "pattern_type": "reliable_skill",
                    "skill": skill.name,
                    "success_rate": skill.success_rate,
                    "description": f"{skill.name} has proven reliable",
                })

        return patterns

    def cleanup(self):
        """Cleanup - persist skillbook if needed."""
        log.debug("ace_cleanup", skills=len(self._skillbook), logs=len(self._execution_log))
        super().cleanup()
