"""Proselint adapter - Prose quality checking.

Runs proselint locally via subprocess to check prose quality.
No MCP required - all local execution.

Features:
- 100+ writing issue detections
- JSON output format
- Configurable checks
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
import logging

from .base_adapter import LocalToolAdapter, AdapterResult

log = logging.getLogger(__name__)


class ProselintAdapter(LocalToolAdapter):
    """Adapter for proselint prose quality checker.

    Usage:
        adapter = ProselintAdapter()
        result = adapter.execute(
            {"content": "This is very unique content."},
            budget_tokens=500
        )
        # result.output = {"issues": [...], "score": 0.85}
    """

    # Issue severity weights for scoring
    SEVERITY_WEIGHTS = {
        "error": 1.0,
        "warning": 0.5,
        "suggestion": 0.2,
    }

    @property
    def tool_name(self) -> str:
        return "proselint"

    def _invoke_local(self, input_data: Dict, budget: int) -> Dict:
        """Run proselint on content.

        Args:
            input_data: {"content": str, "checks": Optional[List[str]]}
            budget: Token budget

        Returns:
            {"issues": List[Dict], "score": float, "summary": str}
        """
        content = input_data.get("content", "")
        if not content:
            return {"issues": [], "score": 1.0, "summary": "No content to check"}

        # Track input tokens
        self._track_tokens(len(content) // 4)

        # Write content to temp file for proselint
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            # Run proselint with JSON output
            result = subprocess.run(
                ["proselint", "--json", temp_path],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Parse JSON output
            if result.stdout:
                try:
                    lint_result = json.loads(result.stdout)
                    issues = self._parse_issues(lint_result)
                except json.JSONDecodeError:
                    issues = self._parse_text_output(result.stdout)
            else:
                issues = []

            # Calculate quality score
            score = self._calculate_score(issues, len(content))

            # Track output tokens
            output = {
                "issues": issues,
                "score": score,
                "issue_count": len(issues),
                "summary": self._generate_summary(issues, score),
            }
            self._track_tokens(len(json.dumps(output)) // 4)

            return output

        except subprocess.TimeoutExpired:
            log.warning("proselint_timeout")
            return {
                "issues": [],
                "score": 0.5,
                "summary": "Proselint timed out",
                "error": "timeout",
            }

        except FileNotFoundError:
            log.warning("proselint_not_installed")
            # Fallback: basic checks without proselint
            return self._fallback_check(content)

        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)

    def _parse_issues(self, lint_result: Dict) -> List[Dict]:
        """Parse proselint JSON output into issue list."""
        issues = []
        data = lint_result.get("data", {})
        errors = data.get("errors", [])

        for error in errors:
            issues.append(
                {
                    "line": error.get("line", 0),
                    "column": error.get("column", 0),
                    "message": error.get("message", ""),
                    "check": error.get("check", "unknown"),
                    "severity": error.get("severity", "warning"),
                    "replacement": error.get("replacements", None),
                }
            )

        return issues

    def _parse_text_output(self, output: str) -> List[Dict]:
        """Parse proselint text output as fallback."""
        issues = []
        for line in output.strip().split("\n"):
            if line and ":" in line:
                parts = line.split(":", 3)
                if len(parts) >= 4:
                    issues.append(
                        {
                            "line": int(parts[1]) if parts[1].isdigit() else 0,
                            "column": int(parts[2]) if parts[2].isdigit() else 0,
                            "message": parts[3].strip(),
                            "severity": "warning",
                        }
                    )
        return issues

    def _calculate_score(self, issues: List[Dict], content_length: int) -> float:
        """Calculate quality score from 0.0 to 1.0."""
        if not issues or content_length == 0:
            return 1.0

        # Weight issues by severity
        weighted_issues = sum(
            self.SEVERITY_WEIGHTS.get(issue.get("severity", "warning"), 0.5)
            for issue in issues
        )

        # Normalize by content length (issues per 1000 chars)
        issues_per_1k = (weighted_issues / content_length) * 1000

        # Score: 1.0 for 0 issues, decreases logarithmically
        import math

        score = max(0.0, 1.0 - (math.log1p(issues_per_1k) / 5))

        return round(score, 2)

    def _generate_summary(self, issues: List[Dict], score: float) -> str:
        """Generate human-readable summary."""
        if not issues:
            return "No issues found. Prose quality is excellent."

        severity_counts = {}
        for issue in issues:
            sev = issue.get("severity", "warning")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        parts = []
        for sev, count in sorted(severity_counts.items()):
            parts.append(f"{count} {sev}{'s' if count > 1 else ''}")

        return f"Found {', '.join(parts)}. Quality score: {score:.0%}"

    def _fallback_check(self, content: str) -> Dict:
        """Basic prose checks when proselint not available."""
        issues = []

        # Check for common issues
        checks = [
            ("very unique", "Remove 'very' - unique is absolute"),
            ("more perfect", "Remove 'more' - perfect is absolute"),
            ("completely destroyed", "Remove 'completely' - destroyed is absolute"),
            ("  ", "Double space detected"),
            ("...", "Consider using proper ellipsis (…)"),
        ]

        for pattern, message in checks:
            if pattern.lower() in content.lower():
                issues.append(
                    {
                        "message": message,
                        "check": "fallback",
                        "severity": "suggestion",
                    }
                )

        score = self._calculate_score(issues, len(content))
        return {
            "issues": issues,
            "score": score,
            "summary": f"Fallback check: {len(issues)} potential issues",
            "fallback": True,
        }
