#!/usr/bin/env python3
"""
UTF Context Filter Hook - Taxonomy-Based Context Retrieval

PreToolUse hook that augments Read operations with relevant UTF knowledge
filtered by taxonomy (domain, level, claim_form, confidence).

Based on claude-context-extender pattern: inject, don't block.
"""

import os
import sys
import json
import sqlite3
from pathlib import Path

# UTF Knowledge DB
PROJECT_DIR = Path(__file__).parent.parent.parent
DB_PATH = PROJECT_DIR / "daemon" / "utf_knowledge.db"

def get_relevant_context(file_path: str, max_items: int = 5) -> dict:
    """
    Get relevant UTF knowledge for a file being read.
    Uses taxonomy filtering to find related claims/concepts.
    """
    if not DB_PATH.exists():
        return {"status": "no_db"}

    # Infer domain from file path
    path_lower = file_path.lower()
    domain = None
    if any(x in path_lower for x in ["ml", "model", "neural", "train"]):
        domain = "machine_learning"
    elif any(x in path_lower for x in ["math", "calc", "algebra"]):
        domain = "mathematics"
    elif any(x in path_lower for x in ["physics", "quantum"]):
        domain = "physics"

    # Get file keywords from path
    keywords = Path(file_path).stem.replace("-", " ").replace("_", " ").split()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    context = {
        "related_claims": [],
        "related_concepts": [],
        "assumptions_to_watch": [],
        "domain_inferred": domain
    }

    try:
        # Find related concepts by keyword matching
        for keyword in keywords[:3]:
            if len(keyword) < 3:
                continue

            # Search concepts
            c.execute('''
                SELECT concept_id, name, definition_1liner, scaffold_what, domain
                FROM concepts
                WHERE name LIKE ? OR definition_1liner LIKE ?
                LIMIT 3
            ''', (f'%{keyword}%', f'%{keyword}%'))

            for row in c.fetchall():
                context["related_concepts"].append({
                    "name": row[1],
                    "definition": row[2] or row[3],
                    "domain": row[4]
                })

            # Search claims with high confidence
            c.execute('''
                SELECT claim_id, statement, claim_form, confidence, domain
                FROM claims
                WHERE statement LIKE ? AND confidence >= 0.6
                LIMIT 3
            ''', (f'%{keyword}%',))

            for row in c.fetchall():
                context["related_claims"].append({
                    "statement": row[1],
                    "form": row[2],
                    "confidence": row[3],
                    "domain": row[4]
                })

        # Get critical assumptions if we have claims
        if context["related_claims"]:
            c.execute('''
                SELECT statement, assumption_type, violations
                FROM assumptions
                WHERE assumption_type IN ('Causal', 'Distribution', 'Data')
                LIMIT 3
            ''')

            for row in c.fetchall():
                context["assumptions_to_watch"].append({
                    "statement": row[0],
                    "type": row[1],
                    "violations": row[2]
                })

    except Exception as e:
        context["error"] = str(e)

    conn.close()
    return context

def format_context_injection(context: dict) -> str:
    """Format context as concise injection."""
    if not context.get("related_concepts") and not context.get("related_claims"):
        return ""

    parts = ["<utf-context>"]

    if context.get("related_concepts"):
        parts.append("Concepts:")
        for c in context["related_concepts"][:3]:
            parts.append(f"  - {c['name']}: {c['definition'][:100]}")

    if context.get("related_claims"):
        parts.append("Claims:")
        for c in context["related_claims"][:3]:
            parts.append(f"  - [{c['form']}] {c['statement'][:100]} (conf:{c['confidence']:.1f})")

    if context.get("assumptions_to_watch"):
        parts.append("Watch assumptions:")
        for a in context["assumptions_to_watch"][:2]:
            parts.append(f"  - {a['statement'][:80]} (if violated: {a['violations'][:50]})")

    parts.append("</utf-context>")
    return "\n".join(parts)

def main():
    """Hook entry point - read from stdin, write to stdout."""
    try:
        input_data = json.loads(sys.stdin.read())
    except:
        # No input or invalid JSON
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

    # Get UTF context
    context = get_relevant_context(file_path)
    injection = format_context_injection(context)

    if injection:
        print(json.dumps({
            "additionalContext": injection
        }))
    else:
        print(json.dumps({}))

if __name__ == "__main__":
    main()
