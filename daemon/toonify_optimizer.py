#!/usr/bin/env python3
"""
Toonify Token Optimizer - TOON format for 60%+ token reduction.

Converts JSON data to Token-Oriented Object Notation (TOON) format
which dramatically reduces token usage when sending structured data to LLMs.

Based on: https://github.com/Shubhamsaboo/awesome-llm-apps/tree/main/advanced_llm_apps/llm_optimization_tools/toonify_token_optimization

Usage:
    from toonify_optimizer import toonify_data, detoonify_data, estimate_savings

    # Convert to TOON (saves 60%+ tokens)
    toon_str = toonify_data(my_dict_or_list)

    # Convert back
    original = detoonify_data(toon_str)
"""

import json
import re
from typing import Any, Dict, List, Union, Optional
from dataclasses import dataclass


@dataclass
class ToonifyResult:
    """Result of TOON conversion."""
    toon_str: str
    original_size: int
    toon_size: int
    savings_pct: float
    estimated_token_savings: int


def toonify_data(
    data: Union[Dict, List],
    delimiter: str = ',',
    key_folding: bool = False
) -> str:
    """
    Convert Python data to TOON format.

    TOON Format Example:
    JSON: [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
    TOON: [2]{id,name}:
           1,A
           2,B

    Args:
        data: Dict or List to convert
        delimiter: Field separator (comma, tab, pipe)
        key_folding: Collapse nested keys (a.b.c instead of nested braces)

    Returns:
        TOON-formatted string
    """
    if isinstance(data, dict):
        return _encode_dict(data, delimiter, key_folding)
    elif isinstance(data, list):
        return _encode_list(data, delimiter, key_folding)
    else:
        return str(data)


def _encode_list(items: List, delimiter: str, key_folding: bool) -> str:
    """Encode a list of objects to TOON format."""
    if not items:
        return "[]"

    # Check if uniform structure (same keys in all items)
    if isinstance(items[0], dict):
        keys = set(items[0].keys())
        is_uniform = all(isinstance(item, dict) and set(item.keys()) == keys for item in items)

        if is_uniform:
            # TOON array format: [count]{keys}:\n values
            key_list = list(items[0].keys())
            header = f"[{len(items)}]{{{delimiter.join(key_list)}}}:"

            rows = []
            for item in items:
                values = [_encode_value(item[k], delimiter, key_folding) for k in key_list]
                rows.append(delimiter.join(values))

            return header + "\n " + "\n ".join(rows)

    # Non-uniform - just encode each item
    encoded = [_encode_value(item, delimiter, key_folding) for item in items]
    return "[" + delimiter.join(encoded) + "]"


def _encode_dict(obj: Dict, delimiter: str, key_folding: bool) -> str:
    """Encode a dict to TOON format."""
    if not obj:
        return "{}"

    parts = []
    for key, value in obj.items():
        encoded_value = _encode_value(value, delimiter, key_folding)

        # Check if value is a uniform list (common case)
        if isinstance(value, list) and value and isinstance(value[0], dict):
            # Let _encode_list handle it
            encoded_value = _encode_list(value, delimiter, key_folding)
            parts.append(f"{key}{encoded_value}")
        else:
            parts.append(f"{key}:{encoded_value}")

    return "\n".join(parts)


def _encode_value(value: Any, delimiter: str, key_folding: bool) -> str:
    """Encode a single value."""
    if value is None:
        return ""
    elif isinstance(value, bool):
        return "1" if value else "0"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        # Escape delimiters if present
        if delimiter in value or '\n' in value:
            return f'"{value}"'
        return value
    elif isinstance(value, dict):
        return _encode_dict(value, delimiter, key_folding)
    elif isinstance(value, list):
        return _encode_list(value, delimiter, key_folding)
    else:
        return str(value)


def detoonify_data(toon_str: str) -> Union[Dict, List]:
    """
    Convert TOON format back to Python data.

    Args:
        toon_str: TOON-formatted string

    Returns:
        Decoded Python dict or list
    """
    toon_str = toon_str.strip()

    if not toon_str:
        return {}

    # Check for array format: [count]{keys}:\n values
    array_match = re.match(r'^(\w+)?\[(\d+)\]\{([^}]+)\}:', toon_str)
    if array_match:
        prefix = array_match.group(1) or ""
        count = int(array_match.group(2))
        keys = array_match.group(3).split(',')

        # Get data rows
        data_start = array_match.end()
        data_part = toon_str[data_start:].strip()
        rows = [row.strip() for row in data_part.split('\n') if row.strip()]

        items = []
        for row in rows:
            values = _parse_row(row, ',')
            item = {}
            for i, key in enumerate(keys):
                if i < len(values):
                    item[key] = _parse_value(values[i])
            items.append(item)

        if prefix:
            return {prefix: items}
        return items

    # Check for dict-like format
    if ':' in toon_str and not toon_str.startswith('['):
        result = {}
        for line in toon_str.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Check for key with array
            arr_match = re.match(r'^(\w+)\[(\d+)\]\{([^}]+)\}:', line)
            if arr_match:
                key = arr_match.group(1)
                # Recursively decode
                result[key] = detoonify_data(line)
            elif ':' in line:
                key, value = line.split(':', 1)
                result[key.strip()] = _parse_value(value.strip())

        return result

    # Simple list
    if toon_str.startswith('[') and toon_str.endswith(']'):
        inner = toon_str[1:-1]
        return [_parse_value(v.strip()) for v in inner.split(',')]

    return _parse_value(toon_str)


def _parse_row(row: str, delimiter: str) -> List[str]:
    """Parse a row respecting quoted strings."""
    values = []
    current = ""
    in_quotes = False

    for char in row:
        if char == '"':
            in_quotes = not in_quotes
        elif char == delimiter and not in_quotes:
            values.append(current)
            current = ""
        else:
            current += char

    values.append(current)
    return values


def _parse_value(value: str) -> Any:
    """Parse a value to its appropriate type."""
    value = value.strip()

    if not value:
        return None

    # Remove quotes
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]

    # Try int
    try:
        return int(value)
    except ValueError:
        pass

    # Try float
    try:
        return float(value)
    except ValueError:
        pass

    # Boolean
    if value == '1':
        return True
    elif value == '0':
        return False

    return value


def estimate_savings(data: Union[Dict, List]) -> ToonifyResult:
    """
    Estimate token savings from TOON conversion.

    Args:
        data: Data to analyze

    Returns:
        ToonifyResult with size comparisons and savings
    """
    json_str = json.dumps(data)
    toon_str = toonify_data(data)

    json_size = len(json_str.encode('utf-8'))
    toon_size = len(toon_str.encode('utf-8'))

    savings_pct = ((json_size - toon_size) / json_size) * 100 if json_size > 0 else 0

    # Rough token estimate (4 chars per token)
    json_tokens = json_size // 4
    toon_tokens = toon_size // 4

    return ToonifyResult(
        toon_str=toon_str,
        original_size=json_size,
        toon_size=toon_size,
        savings_pct=savings_pct,
        estimated_token_savings=json_tokens - toon_tokens
    )


# ============================================================================
# Integration with Atlas Daemon
# ============================================================================

def optimize_for_llm(data: Union[Dict, List], min_savings_pct: float = 20.0) -> str:
    """
    Optimize data for LLM consumption.

    Only converts to TOON if savings exceed threshold.

    Args:
        data: Data to optimize
        min_savings_pct: Minimum savings to use TOON (default 20%)

    Returns:
        TOON string if beneficial, else JSON string
    """
    result = estimate_savings(data)

    if result.savings_pct >= min_savings_pct:
        return result.toon_str
    else:
        return json.dumps(data)


def batch_toonify(items: List[Dict], batch_size: int = 100) -> List[str]:
    """
    Process large datasets in batches.

    Args:
        items: List of dicts to convert
        batch_size: Items per batch

    Returns:
        List of TOON strings, one per batch
    """
    batches = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batches.append(toonify_data(batch))
    return batches


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("TOONIFY TOKEN OPTIMIZER")
    print("=" * 60)

    # Demo data
    products = {
        "products": [
            {"id": 101, "name": "Laptop Pro", "price": 1299.99, "stock": 45},
            {"id": 102, "name": "Magic Mouse", "price": 79.99, "stock": 120},
            {"id": 103, "name": "USB-C Cable", "price": 19.99, "stock": 350},
            {"id": 104, "name": "Keyboard", "price": 89.99, "stock": 85},
            {"id": 105, "name": "Monitor Stand", "price": 45.99, "stock": 60},
        ]
    }

    result = estimate_savings(products)

    print("\n📄 JSON Format:")
    print(json.dumps(products, indent=2))
    print(f"\nSize: {result.original_size} bytes")

    print("\n🎯 TOON Format:")
    print(result.toon_str)
    print(f"\nSize: {result.toon_size} bytes")

    print("\n💰 SAVINGS:")
    print(f"  Size reduction: {result.savings_pct:.1f}%")
    print(f"  Token savings: ~{result.estimated_token_savings} tokens")

    # Roundtrip test
    decoded = detoonify_data(result.toon_str)
    if decoded == products:
        print("\n✅ Roundtrip: PASSED")
    else:
        print("\n❌ Roundtrip: FAILED")
        print(f"Decoded: {decoded}")
