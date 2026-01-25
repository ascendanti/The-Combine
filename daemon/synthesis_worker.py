#!/usr/bin/env python3
"""
Synthesis Worker - Periodic knowledge growth via Codex

Architecture:
1. LocalAI: Persistent PDF processing → KG chunks/summaries (FREE)
2. Codex: Periodic synthesis → meta-learnings, patterns, connections ($)
3. Claude: Premium reasoning over synthesized knowledge ($$$)

This worker runs periodically (daily/weekly) to:
- Cross-reference new KG entries
- Identify patterns across documents
- Generate meta-learnings and insights
- Propose concept connections
- Update capability assessments

Usage:
    python synthesis_worker.py --cycle       # Run one synthesis cycle
    python synthesis_worker.py --watch       # Continuous mode (daily)
    python synthesis_worker.py --status      # Show synthesis status
"""

import argparse
import json
import sqlite3
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Add daemon to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

try:
    from model_router import ModelRouter, Provider, estimate_tokens
    ROUTER_AVAILABLE = True
except ImportError:
    ROUTER_AVAILABLE = False

# Paths
BOOKS_DB = Path(__file__).parent.parent / ".claude" / "scripts" / "books.db"
SYNTHESIS_DB = Path(__file__).parent / "synthesis.db"
KG_FILE = Path.home() / ".claude" / "memory" / "knowledge-graph.jsonl"


def init_synthesis_db():
    """Initialize synthesis database."""
    conn = sqlite3.connect(SYNTHESIS_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS synthesis_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            new_entries_processed INTEGER,
            patterns_found INTEGER,
            connections_proposed INTEGER,
            meta_learnings_generated INTEGER,
            tokens_used INTEGER,
            cost_estimate REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meta_learnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            source_entries TEXT,  -- JSON array of source IDs
            learning TEXT,
            confidence REAL,
            domain TEXT,
            applied INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS concept_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            concept_a TEXT,
            concept_b TEXT,
            relationship TEXT,
            strength REAL,
            source_run_id INTEGER
        )
    """)
    conn.commit()
    conn.close()


def get_recent_kg_entries(since_hours: int = 24) -> List[Dict]:
    """Get KG entries added in the last N hours."""
    entries = []
    if not KG_FILE.exists():
        return entries

    cutoff = datetime.now() - timedelta(hours=since_hours)

    with open(KG_FILE) as f:
        for line in f:
            try:
                entry = json.loads(line)
                # Check timestamp if present
                if "timestamp" in entry:
                    entry_time = datetime.fromisoformat(entry["timestamp"])
                    if entry_time > cutoff:
                        entries.append(entry)
                else:
                    entries.append(entry)  # Include if no timestamp
            except:
                pass

    return entries


def get_book_summaries(limit: int = 10) -> List[Dict]:
    """Get recent book summaries for synthesis."""
    if not BOOKS_DB.exists():
        return []

    conn = sqlite3.connect(BOOKS_DB)
    cursor = conn.execute("""
        SELECT book_id, level, content, created_at
        FROM summaries
        WHERE level IN ('chapter', 'book')
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))

    summaries = []
    for row in cursor.fetchall():
        summaries.append({
            "book_id": row[0],
            "level": row[1],
            "content": row[2],
            "created_at": row[3]
        })

    conn.close()
    return summaries


def synthesize_patterns(entries: List[Dict], router: ModelRouter) -> Dict[str, Any]:
    """Use Codex to find patterns across entries."""
    if not entries:
        return {"patterns": [], "tokens_used": 0}

    # Prepare synthesis prompt
    entry_summaries = []
    for i, entry in enumerate(entries[:20]):  # Limit to 20 for context
        summary = f"[{i+1}] "
        if "content" in entry:
            summary += entry["content"][:200]
        elif "summary" in entry:
            summary += entry["summary"][:200]
        elif "observation" in entry:
            summary += entry["observation"][:200]
        entry_summaries.append(summary)

    content = "\n".join(entry_summaries)

    task = """Analyze these knowledge entries and identify:
1. PATTERNS: Recurring themes or concepts (list 3-5)
2. CONNECTIONS: How concepts relate to each other (list 3-5 pairs)
3. META-LEARNINGS: Higher-order insights that emerge (list 2-3)
4. GAPS: What knowledge is missing or incomplete

Format as JSON:
{
  "patterns": [{"theme": "...", "evidence": "...", "confidence": 0.X}],
  "connections": [{"a": "...", "b": "...", "relationship": "..."}],
  "meta_learnings": [{"insight": "...", "domain": "...", "confidence": 0.X}],
  "gaps": ["..."]
}"""

    # Route to Codex
    result = router.route(task, content, force_provider=Provider.CODEX)

    if result.get("response"):
        try:
            # Parse JSON from response
            response = result["response"]
            # Find JSON block
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            else:
                json_str = response

            synthesis = json.loads(json_str)
            synthesis["tokens_used"] = result["tokens_used"]["input"] + estimate_tokens(response)
            return synthesis
        except json.JSONDecodeError:
            return {
                "patterns": [],
                "connections": [],
                "meta_learnings": [],
                "gaps": [],
                "tokens_used": result["tokens_used"]["input"],
                "raw_response": result["response"]
            }

    return {"patterns": [], "tokens_used": 0, "error": result.get("error")}


def cross_reference_concepts(summaries: List[Dict], router: ModelRouter) -> List[Dict]:
    """Cross-reference concepts from different books/documents."""
    if len(summaries) < 2:
        return []

    # Prepare comparison prompt
    summary_texts = []
    for i, s in enumerate(summaries[:5]):
        summary_texts.append(f"[Doc {i+1}] {s['content'][:300]}...")

    content = "\n\n".join(summary_texts)

    task = """Compare these document summaries and identify:
1. SHARED CONCEPTS: Ideas that appear in multiple documents
2. COMPLEMENTARY IDEAS: Concepts that enhance each other
3. CONTRADICTIONS: Conflicting information (if any)

Format as JSON array:
[
  {"type": "shared", "concept": "...", "docs": [1, 2], "synthesis": "..."},
  {"type": "complementary", "from_doc": 1, "to_doc": 2, "connection": "..."}
]"""

    result = router.route(task, content, force_provider=Provider.CODEX)

    if result.get("response"):
        try:
            response = result["response"]
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            else:
                json_str = response
            return json.loads(json_str)
        except:
            return []

    return []


def store_synthesis_results(run_id: int, synthesis: Dict, connections: List[Dict]):
    """Store synthesis results in database."""
    conn = sqlite3.connect(SYNTHESIS_DB)

    # Store meta-learnings
    for learning in synthesis.get("meta_learnings", []):
        conn.execute("""
            INSERT INTO meta_learnings (timestamp, source_entries, learning, confidence, domain)
            VALUES (datetime('now'), ?, ?, ?, ?)
        """, (
            json.dumps([]),
            learning.get("insight", ""),
            learning.get("confidence", 0.5),
            learning.get("domain", "general")
        ))

    # Store concept connections
    for conn_item in synthesis.get("connections", []) + connections:
        if "a" in conn_item and "b" in conn_item:
            conn.execute("""
                INSERT INTO concept_connections
                (timestamp, concept_a, concept_b, relationship, strength, source_run_id)
                VALUES (datetime('now'), ?, ?, ?, ?, ?)
            """, (
                conn_item.get("a", ""),
                conn_item.get("b", ""),
                conn_item.get("relationship", ""),
                conn_item.get("strength", 0.5),
                run_id
            ))

    conn.commit()
    conn.close()


def consolidate_kg(router: ModelRouter) -> Dict[str, Any]:
    """
    KG Consolidation - Grow without bloating.

    1. Find duplicate/similar concepts
    2. Merge redundant entries
    3. Promote patterns (many specifics -> one generalization)
    4. Archive rarely-accessed entries
    """
    print("\n[KG CONSOLIDATION] Analyzing knowledge graph...")

    results = {
        "duplicates_found": 0,
        "merged": 0,
        "promoted": 0,
        "archived": 0
    }

    if not KG_FILE.exists():
        print("    [SKIP] No KG file found")
        return results

    # Load all KG entries
    entries = []
    with open(KG_FILE) as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except:
                pass

    if len(entries) < 10:
        print(f"    [SKIP] Only {len(entries)} entries - no consolidation needed")
        return results

    print(f"    Loaded {len(entries)} entries")

    # Group by entity type
    by_type = {}
    for e in entries:
        etype = e.get("entityType", "unknown")
        if etype not in by_type:
            by_type[etype] = []
        by_type[etype].append(e)

    print(f"    Entity types: {list(by_type.keys())}")

    # Find potential duplicates (same name or very similar observations)
    seen_names = {}
    potential_dupes = []

    for e in entries:
        name = e.get("name", "").lower()
        if name in seen_names:
            potential_dupes.append((seen_names[name], e))
            results["duplicates_found"] += 1
        else:
            seen_names[name] = e

    if potential_dupes:
        print(f"    Found {len(potential_dupes)} potential duplicates")

        # For now, just report - merging requires LLM to decide
        # In future: use LocalAI to compare and merge

    # Identify consolidation opportunities
    # Group similar concepts for promotion to patterns
    concept_entries = [e for e in entries if e.get("entityType") == "concept"]
    if len(concept_entries) >= 5:
        print(f"    {len(concept_entries)} concepts - checking for patterns...")

        # Use LocalAI to identify consolidation candidates
        concept_names = [e.get("name", "")[:50] for e in concept_entries[:20]]

        prompt = f"""These are concept names from a knowledge graph.
Identify any that should be MERGED (same thing, different names) or
PROMOTED (specific instances that could become a general pattern).

Concepts:
{chr(10).join(concept_names)}

Respond in JSON:
{{"merge": [["name1", "name2"]], "promote": [{{"from": ["specific1", "specific2"], "to": "general_pattern"}}]}}
"""

        try:
            import requests
            response = requests.post(
                "http://localhost:8080/v1/chat/completions",
                json={
                    "model": "mistral-7b-instruct-v0.3",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 400
                },
                timeout=60
            )

            result = response.json()
            content = result['choices'][0]['message']['content']

            # Parse suggestions (just log for now - manual review)
            print(f"    [LocalAI] Consolidation suggestions: {content[:200]}...")
        except Exception as e:
            print(f"    [WARN] LocalAI consolidation check failed: {e}")

    print(f"    [DONE] Duplicates: {results['duplicates_found']}")
    return results


def run_synthesis_cycle(router: ModelRouter) -> Dict[str, Any]:
    """Run one synthesis cycle."""
    print("\n[SYNTHESIS CYCLE] Starting...")
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = {
        "timestamp": datetime.now().isoformat(),
        "new_entries_processed": 0,
        "patterns_found": 0,
        "connections_proposed": 0,
        "meta_learnings_generated": 0,
        "duplicates_found": 0,
        "tokens_used": 0,
        "cost_estimate": 0.0
    }

    # 0. Consolidate KG first (prevent bloat)
    print("\n[0/4] Consolidating knowledge graph...")
    consolidation = consolidate_kg(router)
    results["duplicates_found"] = consolidation.get("duplicates_found", 0)

    # 1. Get recent KG entries
    print("\n[1/4] Fetching recent knowledge entries...")
    entries = get_recent_kg_entries(since_hours=168)  # Last week
    results["new_entries_processed"] = len(entries)
    print(f"    Found {len(entries)} entries")

    # 2. Get book summaries
    print("\n[2/4] Fetching book summaries...")
    summaries = get_book_summaries(limit=10)
    print(f"    Found {len(summaries)} summaries")

    # 3. Synthesize patterns
    print("\n[3/4] Synthesizing patterns via Codex...")
    all_content = entries + [{"content": s["content"]} for s in summaries]

    if all_content:
        synthesis = synthesize_patterns(all_content, router)
        results["patterns_found"] = len(synthesis.get("patterns", []))
        results["meta_learnings_generated"] = len(synthesis.get("meta_learnings", []))
        results["tokens_used"] += synthesis.get("tokens_used", 0)

        print(f"    Patterns found: {results['patterns_found']}")
        print(f"    Meta-learnings: {results['meta_learnings_generated']}")

        # Cross-reference if we have summaries
        connections = []
        if summaries:
            print("\n[BONUS] Cross-referencing documents...")
            connections = cross_reference_concepts(summaries, router)
            results["connections_proposed"] = len(connections)
            print(f"    Connections: {results['connections_proposed']}")

        # Store results
        conn = sqlite3.connect(SYNTHESIS_DB)
        cursor = conn.execute("""
            INSERT INTO synthesis_runs
            (timestamp, new_entries_processed, patterns_found, connections_proposed,
             meta_learnings_generated, tokens_used, cost_estimate)
            VALUES (datetime('now'), ?, ?, ?, ?, ?, ?)
        """, (
            results["new_entries_processed"],
            results["patterns_found"],
            results["connections_proposed"],
            results["meta_learnings_generated"],
            results["tokens_used"],
            results["tokens_used"] * 0.15 / 1_000_000  # gpt-4o-mini input rate
        ))
        run_id = cursor.lastrowid
        conn.commit()
        conn.close()

        store_synthesis_results(run_id, synthesis, connections)

        # Print synthesis results
        print("\n[SYNTHESIS RESULTS]")
        if synthesis.get("patterns"):
            print("\nPatterns:")
            for p in synthesis["patterns"][:5]:
                print(f"  - {p.get('theme', p)}")

        if synthesis.get("meta_learnings"):
            print("\nMeta-Learnings:")
            for ml in synthesis["meta_learnings"]:
                print(f"  - {ml.get('insight', ml)}")

        if synthesis.get("gaps"):
            print("\nKnowledge Gaps:")
            for gap in synthesis["gaps"][:3]:
                print(f"  - {gap}")

    else:
        print("    [SKIP] No content to synthesize")

    # Cost estimate
    results["cost_estimate"] = results["tokens_used"] * 0.15 / 1_000_000
    print(f"\n[COMPLETE] Tokens: {results['tokens_used']}, Cost: ${results['cost_estimate']:.6f}")

    return results


def show_status():
    """Show synthesis status."""
    if not SYNTHESIS_DB.exists():
        print("[STATUS] No synthesis runs yet")
        return

    conn = sqlite3.connect(SYNTHESIS_DB)

    # Recent runs
    cursor = conn.execute("""
        SELECT timestamp, new_entries_processed, patterns_found,
               meta_learnings_generated, tokens_used, cost_estimate
        FROM synthesis_runs
        ORDER BY id DESC LIMIT 5
    """)

    print("\n[RECENT SYNTHESIS RUNS]")
    print(f"{'Timestamp':<20} {'Entries':<10} {'Patterns':<10} {'Learnings':<10} {'Cost':<10}")
    print("-" * 60)

    for row in cursor.fetchall():
        print(f"{row[0]:<20} {row[1]:<10} {row[2]:<10} {row[3]:<10} ${row[5]:.6f}")

    # Meta-learnings count
    cursor = conn.execute("SELECT COUNT(*) FROM meta_learnings")
    learning_count = cursor.fetchone()[0]

    cursor = conn.execute("SELECT COUNT(*) FROM concept_connections")
    connection_count = cursor.fetchone()[0]

    print(f"\n[TOTALS]")
    print(f"Total meta-learnings: {learning_count}")
    print(f"Total connections: {connection_count}")

    # Recent learnings
    cursor = conn.execute("""
        SELECT learning, domain, confidence
        FROM meta_learnings
        ORDER BY id DESC LIMIT 5
    """)

    print("\n[RECENT META-LEARNINGS]")
    for row in cursor.fetchall():
        print(f"  [{row[1]}] {row[0][:100]}... (conf: {row[2]:.2f})")

    conn.close()


def watch_mode(interval_hours: int = 24):
    """Run synthesis periodically."""
    print(f"[WATCH MODE] Running synthesis every {interval_hours} hours")
    print("Press Ctrl+C to stop")

    router = ModelRouter()

    while True:
        try:
            run_synthesis_cycle(router)
            print(f"\n[SLEEPING] Next run in {interval_hours} hours...")
            time.sleep(interval_hours * 3600)
        except KeyboardInterrupt:
            print("\n[STOPPED]")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(300)  # Wait 5 min on error


def main():
    parser = argparse.ArgumentParser(description="Synthesis Worker - Knowledge Growth via Codex")
    parser.add_argument("--cycle", action="store_true", help="Run one synthesis cycle")
    parser.add_argument("--watch", action="store_true", help="Continuous mode")
    parser.add_argument("--interval", type=int, default=24, help="Hours between runs (default: 24)")
    parser.add_argument("--status", action="store_true", help="Show synthesis status")

    args = parser.parse_args()

    init_synthesis_db()

    if args.status:
        show_status()
        return

    if not ROUTER_AVAILABLE:
        print("[ERROR] model_router not available")
        return

    if args.watch:
        watch_mode(args.interval)
    elif args.cycle:
        router = ModelRouter()
        run_synthesis_cycle(router)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
