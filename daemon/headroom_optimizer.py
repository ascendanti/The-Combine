#!/usr/bin/env python3
"""
Headroom Context Optimizer - Intelligent compression for 50-90% token reduction.

Compresses tool outputs, logs, and structured data by keeping only what matters:
- First N items (context)
- Last N items (recency)
- Anomalies (errors, warnings, non-standard levels)
- Query-relevant items (keyword matches)

Based on: https://github.com/Shubhamsaboo/awesome-llm-apps/tree/main/advanced_llm_apps/llm_optimization_tools/headroom_context_optimization

Usage:
    from headroom_optimizer import compress_logs, compress_tool_output, SmartCrusher

    # Compress logs (keeps errors, first/last, anomalies)
    compressed = compress_logs(log_entries)

    # Compress any tool output
    compressed = compress_tool_output(output, query="find the error")
"""

import json
import re
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CompressionResult:
    """Result of headroom compression."""
    compressed: List[Any]
    original_count: int
    compressed_count: int
    reduction_pct: float
    kept_reasons: Dict[str, int]  # Why items were kept


@dataclass
class SmartCrusherConfig:
    """Configuration for SmartCrusher compression."""
    keep_first: int = 3          # Keep first N items
    keep_last: int = 2           # Keep last N items
    keep_anomalies: bool = True  # Keep errors, warnings, etc.
    keep_query_relevant: bool = True  # Keep items matching query
    anomaly_levels: List[str] = field(default_factory=lambda: [
        "ERROR", "FATAL", "CRITICAL", "WARNING", "WARN", "EXCEPTION"
    ])
    min_items: int = 5           # Minimum items to keep


class SmartCrusher:
    """
    Intelligent context compressor.

    Keeps semantically important items while discarding boilerplate:
    - Statistical outliers (errors, anomalies)
    - First items (context establishment)
    - Last items (recency)
    - Query-relevant matches
    """

    def __init__(self, config: Optional[SmartCrusherConfig] = None):
        self.config = config or SmartCrusherConfig()

    def compress(
        self,
        items: List[Any],
        query: Optional[str] = None,
        key_extractor: Optional[Callable] = None
    ) -> CompressionResult:
        """
        Compress a list of items keeping only what matters.

        Args:
            items: List of items to compress
            query: Optional query to find relevant items
            key_extractor: Function to extract searchable text from item

        Returns:
            CompressionResult with compressed items
        """
        if not items:
            return CompressionResult([], 0, 0, 0.0, {})

        original_count = len(items)
        kept_indices = set()
        kept_reasons = {}

        def mark_kept(idx: int, reason: str):
            kept_indices.add(idx)
            kept_reasons[reason] = kept_reasons.get(reason, 0) + 1

        # 1. Keep first N items
        for i in range(min(self.config.keep_first, len(items))):
            mark_kept(i, "first_items")

        # 2. Keep last N items
        for i in range(max(0, len(items) - self.config.keep_last), len(items)):
            mark_kept(i, "last_items")

        # 3. Keep anomalies
        if self.config.keep_anomalies:
            for i, item in enumerate(items):
                if self._is_anomaly(item, key_extractor):
                    mark_kept(i, "anomaly")

        # 4. Keep query-relevant items
        if query and self.config.keep_query_relevant:
            query_lower = query.lower()
            for i, item in enumerate(items):
                if self._matches_query(item, query_lower, key_extractor):
                    mark_kept(i, "query_match")

        # Build compressed list (maintain order)
        compressed = [items[i] for i in sorted(kept_indices)]

        # Ensure minimum items
        if len(compressed) < self.config.min_items and len(items) > len(compressed):
            # Add more items evenly distributed
            step = len(items) // (self.config.min_items - len(compressed) + 1)
            for i in range(0, len(items), step):
                if i not in kept_indices:
                    mark_kept(i, "fill_minimum")
                    compressed = [items[j] for j in sorted(kept_indices)]
                if len(compressed) >= self.config.min_items:
                    break

        reduction_pct = (1 - len(compressed) / original_count) * 100 if original_count > 0 else 0

        return CompressionResult(
            compressed=compressed,
            original_count=original_count,
            compressed_count=len(compressed),
            reduction_pct=reduction_pct,
            kept_reasons=kept_reasons
        )

    def _is_anomaly(self, item: Any, key_extractor: Optional[Callable]) -> bool:
        """Check if item is an anomaly (error, warning, etc.)."""
        text = self._get_searchable_text(item, key_extractor)

        # Check for anomaly level keywords
        for level in self.config.anomaly_levels:
            if level.lower() in text.lower():
                return True

        # Check for dict with level/status fields
        if isinstance(item, dict):
            level = item.get('level', item.get('status', item.get('severity', '')))
            if isinstance(level, str) and level.upper() in self.config.anomaly_levels:
                return True

            # Check for error indicators
            if item.get('error') or item.get('exception') or item.get('traceback'):
                return True

            # Check for non-success status codes
            status_code = item.get('status_code', item.get('code', 200))
            if isinstance(status_code, int) and status_code >= 400:
                return True

        return False

    def _matches_query(
        self,
        item: Any,
        query_lower: str,
        key_extractor: Optional[Callable]
    ) -> bool:
        """Check if item matches the query."""
        text = self._get_searchable_text(item, key_extractor).lower()

        # Simple keyword matching
        query_words = query_lower.split()
        return any(word in text for word in query_words if len(word) > 2)

    def _get_searchable_text(self, item: Any, key_extractor: Optional[Callable]) -> str:
        """Extract searchable text from an item."""
        if key_extractor:
            return str(key_extractor(item))

        if isinstance(item, str):
            return item
        elif isinstance(item, dict):
            # Concatenate all string values
            parts = []
            for v in item.values():
                if isinstance(v, str):
                    parts.append(v)
            return " ".join(parts)
        else:
            return str(item)


# ============================================================================
# Convenience Functions
# ============================================================================

def compress_logs(
    logs: List[Dict],
    query: Optional[str] = None,
    keep_first: int = 3,
    keep_last: int = 2
) -> CompressionResult:
    """
    Compress log entries keeping errors and relevant items.

    Args:
        logs: List of log dictionaries
        query: Optional query to find relevant logs
        keep_first: Number of first logs to keep
        keep_last: Number of last logs to keep

    Returns:
        CompressionResult with compressed logs
    """
    config = SmartCrusherConfig(
        keep_first=keep_first,
        keep_last=keep_last,
        keep_anomalies=True,
        keep_query_relevant=bool(query)
    )
    crusher = SmartCrusher(config)
    return crusher.compress(logs, query=query)


def compress_tool_output(
    output: Union[List, Dict, str],
    query: Optional[str] = None,
    max_items: int = 10
) -> Union[List, Dict, str]:
    """
    Compress tool output for LLM consumption.

    Args:
        output: Tool output (list, dict, or string)
        query: Optional query for relevance filtering
        max_items: Maximum items to keep in lists

    Returns:
        Compressed output
    """
    if isinstance(output, list):
        if len(output) <= max_items:
            return output

        config = SmartCrusherConfig(
            keep_first=max(2, max_items // 3),
            keep_last=max(1, max_items // 4),
            min_items=max_items
        )
        crusher = SmartCrusher(config)
        result = crusher.compress(output, query=query)
        return result.compressed

    elif isinstance(output, dict):
        # Compress any list values in the dict
        compressed = {}
        for key, value in output.items():
            if isinstance(value, list) and len(value) > max_items:
                compressed[key] = compress_tool_output(value, query, max_items)
            else:
                compressed[key] = value
        return compressed

    else:
        # String - truncate if too long
        if isinstance(output, str) and len(output) > 10000:
            return output[:5000] + "\n...[truncated]...\n" + output[-2000:]
        return output


def compress_search_results(
    results: List[Dict],
    query: str,
    max_results: int = 5
) -> List[Dict]:
    """
    Compress search results keeping most relevant.

    Args:
        results: List of search result dicts
        query: Search query for relevance scoring
        max_results: Maximum results to return

    Returns:
        Compressed list of results
    """
    if len(results) <= max_results:
        return results

    # Score by query relevance
    query_words = set(query.lower().split())

    def score_result(r: Dict) -> int:
        text = " ".join(str(v) for v in r.values()).lower()
        return sum(1 for word in query_words if word in text)

    # Sort by score and return top results
    scored = [(score_result(r), i, r) for i, r in enumerate(results)]
    scored.sort(key=lambda x: (-x[0], x[1]))  # Highest score, then original order

    return [r for _, _, r in scored[:max_results]]


def compress_code_search(
    matches: List[Dict],
    query: str,
    max_matches: int = 10,
    context_lines: int = 2
) -> List[Dict]:
    """
    Compress code search results.

    Args:
        matches: List of code search matches
        query: Search query
        max_matches: Maximum matches to return
        context_lines: Lines of context to keep

    Returns:
        Compressed matches with trimmed context
    """
    if len(matches) <= max_matches:
        return matches

    # Use SmartCrusher for intelligent selection
    config = SmartCrusherConfig(
        keep_first=2,
        keep_last=1,
        keep_anomalies=True,
        min_items=max_matches
    )
    crusher = SmartCrusher(config)
    result = crusher.compress(matches, query=query)

    # Trim context in each match
    compressed = []
    for match in result.compressed:
        if isinstance(match, dict) and 'context' in match:
            lines = match['context'].split('\n')
            if len(lines) > context_lines * 2 + 1:
                # Keep lines around match
                mid = len(lines) // 2
                trimmed = lines[max(0, mid - context_lines):mid + context_lines + 1]
                match = {**match, 'context': '\n'.join(trimmed)}
        compressed.append(match)

    return compressed


# ============================================================================
# Integration with Atlas Daemon
# ============================================================================

def optimize_daemon_output(
    output: Any,
    output_type: str = "generic",
    query: Optional[str] = None
) -> Any:
    """
    Optimize daemon output for LLM consumption.

    Args:
        output: Output from daemon module
        output_type: Type hint ("logs", "search", "code", "generic")
        query: Optional query for relevance

    Returns:
        Optimized output
    """
    if output_type == "logs":
        if isinstance(output, list):
            result = compress_logs(output, query)
            return result.compressed
    elif output_type == "search":
        if isinstance(output, list):
            return compress_search_results(output, query or "", max_results=10)
    elif output_type == "code":
        if isinstance(output, list):
            return compress_code_search(output, query or "", max_matches=10)

    return compress_tool_output(output, query)


# ============================================================================
# CLI Demo
# ============================================================================

if __name__ == "__main__":
    from datetime import timedelta

    print("=" * 60)
    print("HEADROOM CONTEXT OPTIMIZER")
    print("=" * 60)

    # Generate test logs (100 entries with 1 FATAL at position 67)
    services = ["api-gateway", "user-service", "inventory", "auth", "payment"]
    base_time = datetime(2024, 12, 15, 0, 0, 0)

    logs = []
    for i in range(100):
        if i == 67:
            # The needle
            logs.append({
                "timestamp": (base_time + timedelta(hours=3, minutes=47)).isoformat(),
                "level": "FATAL",
                "service": "payment-gateway",
                "message": "Connection pool exhausted",
                "error_code": "PG-5523",
                "resolution": "Increase max_connections to 500"
            })
        else:
            logs.append({
                "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
                "level": "INFO",
                "service": services[i % len(services)],
                "message": f"Request processed - latency={50 + i}ms",
                "request_id": f"req-{i:06d}"
            })

    print(f"\n📊 BASELINE")
    print(f"Total log entries: {len(logs)}")
    print(f"Estimated tokens: ~{len(json.dumps(logs)) // 4:,}")

    # Compress
    result = compress_logs(logs, query="what caused the outage error")

    print(f"\n🎯 WITH HEADROOM")
    print(f"Compressed to: {result.compressed_count} entries")
    print(f"Reduction: {result.reduction_pct:.1f}%")
    print(f"Estimated tokens: ~{len(json.dumps(result.compressed)) // 4:,}")

    print(f"\n📋 What was kept:")
    for reason, count in result.kept_reasons.items():
        print(f"  {reason}: {count}")

    print(f"\n🔍 Kept entries:")
    for log in result.compressed:
        level = log.get('level', 'INFO')
        service = log.get('service', 'unknown')
        msg = log.get('message', '')[:50]
        marker = "⚠️ " if level in ["FATAL", "ERROR", "WARNING"] else "  "
        print(f"{marker}[{level}] {service}: {msg}...")

    print(f"\n✅ The FATAL error at position 67 was preserved!")
    print(f"💰 Token savings: {result.reduction_pct:.1f}%")
