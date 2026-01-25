#!/usr/bin/env python3
"""
UTF Semantic RAG Hook - Token-Efficient Context Retrieval

PreToolUse hook for Read operations that:
1. Checks if file is in a known domain
2. Searches UTF vectors for relevant pre-processed knowledge
3. Injects compact context (200 tokens vs 5000 raw)

Goal: Reduce token spend on comprehension by serving pre-digested claims.
"""

import os
import sys
import json
from pathlib import Path

# Add scripts to path for imports
PROJECT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_DIR / ".claude" / "scripts"))

def get_semantic_context(file_path: str, max_tokens: int = 300) -> str:
    """Get semantically relevant UTF knowledge for a file."""
    try:
        # Import embedding search
        from utf_embeddings import semantic_search, format_search_for_context

        # Build query from file path
        path = Path(file_path)
        query_parts = []

        # Extract meaningful terms from path
        query_parts.append(path.stem.replace("-", " ").replace("_", " "))

        # Infer domain from path
        domain = None
        path_str = str(path).lower()
        if "ml" in path_str or "model" in path_str or "neural" in path_str:
            domain = "machine_learning"
        elif "math" in path_str:
            domain = "mathematics"

        query = " ".join(query_parts)

        # Search for relevant knowledge
        results = semantic_search(query, k=5, domain=domain, min_score=0.35)

        if not results:
            return ""

        # Format as compact context
        return format_search_for_context(results, max_tokens=max_tokens)

    except ImportError:
        return ""  # Embeddings not available
    except Exception as e:
        return f"<!-- UTF RAG error: {e} -->"

def main():
    """Hook entry point."""
    try:
        input_data = json.loads(sys.stdin.read())
    except:
        print(json.dumps({}))
        return

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only augment Read operations
    if tool_name != "Read":
        print(json.dumps({}))
        return

    file_path = tool_input.get("file_path", "")
    if not file_path:
        print(json.dumps({}))
        return

    # Skip certain file types
    path = Path(file_path)
    if path.suffix.lower() in [".json", ".yaml", ".yml", ".lock", ".env"]:
        print(json.dumps({}))
        return

    # Get semantic context
    context = get_semantic_context(file_path)

    if context:
        print(json.dumps({
            "additionalContext": context
        }))
    else:
        print(json.dumps({}))

if __name__ == "__main__":
    main()
