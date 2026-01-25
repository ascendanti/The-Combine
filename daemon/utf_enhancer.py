#!/usr/bin/env python3
"""
UTF Enhancer - Post-Processing Layer for Docker Workers

Architecture:
1. autonomous_ingest.py (Docker) -> extracts basic facts via HiRAG/LeanRAG
2. utf_enhancer.py (this) -> enhances with UTF taxonomy:
   - Classifies claims by claim_form
   - Builds comprehension scaffolds
   - Extracts assumptions/limitations
   - Adds DKCS coordinates

Runs periodically to enhance existing knowledge, not replace extraction.

Usage:
    python utf_enhancer.py                # Enhance unprocessed entries
    python utf_enhancer.py --watch        # Continuous enhancement
    python utf_enhancer.py --status       # Show enhancement stats
    python utf_enhancer.py --scaffold <concept_id>  # Complete scaffold
"""

import os
import sys
import json
import sqlite3
import requests
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

# Configuration
LOCALAI_URL = os.environ.get("LOCALAI_URL", "http://localhost:8080/v1")
LOCALAI_MODEL = "mistral-7b-instruct-v0.3"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"

# Paths
PROJECT_DIR = Path(__file__).parent.parent
HIRAG_DB = Path(__file__).parent / "ingest.db"
UTF_DB = Path(__file__).parent / "utf_knowledge.db"
KG_PATH = Path.home() / ".claude" / "memory" / "knowledge-graph.jsonl"

# UTF Enums
CLAIM_FORMS = [
    "Definition", "Measurement", "EmpiricalRegularity", "CausalMechanism",
    "Theorem", "Algorithm", "NegativeResult", "Limitation", "Conjecture", "SurveySynthesis"
]

ASSUMPTION_TYPES = ["Data", "Compute", "Distribution", "Causal", "Measurement", "Social", "Normative"]

# ============================================================================
# Database
# ============================================================================

def init_utf_db() -> sqlite3.Connection:
    """Initialize UTF enhancement database."""
    conn = sqlite3.connect(UTF_DB)
    c = conn.cursor()

    # Enhancement tracking
    c.execute('''CREATE TABLE IF NOT EXISTS enhanced_facts (
        fact_id TEXT PRIMARY KEY,
        source_doc TEXT,
        original_content TEXT,
        claim_form TEXT,
        confidence REAL,
        stability_class TEXT,
        domain TEXT,
        dkcs_coordinates TEXT,
        enhanced_at TEXT
    )''')

    # Scaffolds for concepts
    c.execute('''CREATE TABLE IF NOT EXISTS concept_scaffolds (
        concept_id TEXT PRIMARY KEY,
        name TEXT,
        domain TEXT,
        definition_1liner TEXT,
        scaffold_what TEXT,
        scaffold_how TEXT,
        scaffold_when_scope TEXT,
        scaffold_why_stakes TEXT,
        scaffold_how_to_use TEXT,
        scaffold_boundary_conditions TEXT,
        scaffold_failure_modes TEXT,
        completeness INTEGER,
        last_updated TEXT
    )''')

    # Extracted assumptions
    c.execute('''CREATE TABLE IF NOT EXISTS assumptions (
        assumption_id TEXT PRIMARY KEY,
        source_doc TEXT,
        statement TEXT,
        assumption_type TEXT,
        violations TEXT,
        dependent_facts TEXT,
        created_at TEXT
    )''')

    # Extracted limitations
    c.execute('''CREATE TABLE IF NOT EXISTS limitations (
        limitation_id TEXT PRIMARY KEY,
        source_doc TEXT,
        statement TEXT,
        severity TEXT,
        created_at TEXT
    )''')

    # Enhancement queue
    c.execute('''CREATE TABLE IF NOT EXISTS enhancement_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fact_id TEXT,
        enhancement_type TEXT,
        status TEXT,
        created_at TEXT,
        completed_at TEXT
    )''')

    conn.commit()
    return conn

def get_hirag_conn() -> Optional[sqlite3.Connection]:
    """Get connection to HiRAG database (created by autonomous_ingest)."""
    if HIRAG_DB.exists():
        return sqlite3.connect(HIRAG_DB)
    return None

# ============================================================================
# LocalAI Calls (Memory-Friendly)
# ============================================================================

def localai_classify(content: str, task: str, max_tokens: int = 200) -> Dict:
    """Call LocalAI for classification tasks."""
    try:
        response = requests.post(
            f"{LOCALAI_URL}/chat/completions",
            json={
                "model": LOCALAI_MODEL,
                "messages": [{"role": "user", "content": f"{task}\n\nContent: {content[:1500]}"}],
                "max_tokens": max_tokens,
                "temperature": 0.2
            },
            timeout=60
        )
        result = response.json()
        return {
            "content": result['choices'][0]['message']['content'],
            "tokens": result['usage']['total_tokens'],
            "success": True
        }
    except Exception as e:
        return {"content": "", "tokens": 0, "success": False, "error": str(e)}

def openai_scaffold(concept_name: str, context: str, missing_slots: List[str]) -> Dict:
    """Use OpenAI (sparingly) to complete scaffold slots."""
    if not OPENAI_API_KEY:
        return {"success": False, "error": "No API key"}

    slots_needed = ", ".join(missing_slots)
    prompt = f"""Complete the comprehension scaffold for this concept.

Concept: {concept_name}
Context: {context[:2000]}

Fill in ONLY these missing slots:
{slots_needed}

Format your response as:
SLOT_NAME: <content>

Be concise (1-3 sentences per slot).
"""

    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.3
        )
        return {
            "content": response.choices[0].message.content,
            "tokens": response.usage.total_tokens,
            "success": True
        }
    except Exception as e:
        return {"content": "", "tokens": 0, "success": False, "error": str(e)}

# ============================================================================
# Enhancement Functions
# ============================================================================

def classify_claim_form(fact_content: str) -> str:
    """Classify a fact into UTF claim_form."""
    prompt = f"""Classify this statement into ONE of these claim forms:
- Definition (defines a term)
- Measurement (quantitative observation)
- EmpiricalRegularity (X correlates with Y)
- CausalMechanism (X causes Y because Z)
- Theorem (proven logical statement)
- Algorithm (step-by-step procedure)
- NegativeResult (X does not work/hold)
- Limitation (constraint on applicability)
- Conjecture (unproven hypothesis)
- SurveySynthesis (summary of multiple sources)

Statement: {fact_content}

Respond with ONLY the claim form name."""

    result = localai_classify(fact_content, prompt)
    if result["success"]:
        form = result["content"].strip()
        # Validate
        for f in CLAIM_FORMS:
            if f.lower() in form.lower():
                return f
    return "EmpiricalRegularity"  # Default

def extract_assumptions(fact_content: str) -> List[Dict]:
    """Extract implicit assumptions from a fact."""
    prompt = f"""Identify any ASSUMPTIONS this statement relies on.
Look for:
- Data assumptions (IID, distribution)
- Causal assumptions (X causes Y)
- Scope assumptions (in this context)

Statement: {fact_content}

For each assumption:
ASSUMPTION: <what is assumed>
TYPE: <Data|Compute|Distribution|Causal|Measurement|Social|Normative>
VIOLATION: <what breaks if false>

If no assumptions, respond "NONE"."""

    result = localai_classify(fact_content, prompt, max_tokens=300)
    assumptions = []

    if result["success"] and "NONE" not in result["content"].upper():
        current = {}
        for line in result["content"].split('\n'):
            line = line.strip()
            if line.startswith("ASSUMPTION:"):
                if current.get("statement"):
                    assumptions.append(current)
                current = {"statement": line[11:].strip()}
            elif line.startswith("TYPE:"):
                current["assumption_type"] = line[5:].strip()
            elif line.startswith("VIOLATION:"):
                current["violations"] = line[10:].strip()

        if current.get("statement"):
            assumptions.append(current)

    return assumptions

def generate_dkcs_coordinates(fact_content: str, claim_form: str) -> str:
    """Generate DKCS coordinate string for a fact."""
    # Infer domain from content
    domain = "other"
    content_lower = fact_content.lower()
    if any(x in content_lower for x in ["neural", "model", "training", "learning"]):
        domain = "machine_learning"
    elif any(x in content_lower for x in ["theorem", "proof", "equation"]):
        domain = "mathematics"
    elif any(x in content_lower for x in ["physics", "quantum", "energy"]):
        domain = "physics"

    # Infer epistemic status
    epistemic = "Supported"
    if any(x in content_lower for x in ["proven", "established", "well-known"]):
        epistemic = "Established"
    elif any(x in content_lower for x in ["suggest", "may", "could"]):
        epistemic = "Speculative"

    # Build coordinate string
    return f"L2:{domain}:{claim_form}:{epistemic}"

def enhance_fact(fact_id: str, content: str, source_doc: str, utf_conn: sqlite3.Connection):
    """Enhance a single fact with UTF taxonomy."""
    # Classify claim form
    claim_form = classify_claim_form(content)

    # Generate DKCS coordinates
    dkcs = generate_dkcs_coordinates(content, claim_form)

    # Extract assumptions
    assumptions = extract_assumptions(content)

    # Store enhanced fact
    c = utf_conn.cursor()
    c.execute('''INSERT OR REPLACE INTO enhanced_facts
        (fact_id, source_doc, original_content, claim_form, confidence, stability_class, domain, dkcs_coordinates, enhanced_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (fact_id, source_doc, content, claim_form, 0.7, "ContextStable",
         dkcs.split(":")[1], dkcs, datetime.now().isoformat()))

    # Store assumptions
    for i, asmp in enumerate(assumptions):
        asmp_id = f"{fact_id}_asm_{i}"
        c.execute('''INSERT OR IGNORE INTO assumptions
            (assumption_id, source_doc, statement, assumption_type, violations, dependent_facts, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (asmp_id, source_doc, asmp.get("statement", ""),
             asmp.get("assumption_type", "Data"), asmp.get("violations", ""),
             json.dumps([fact_id]), datetime.now().isoformat()))

    utf_conn.commit()
    return {"claim_form": claim_form, "dkcs": dkcs, "assumptions": len(assumptions)}

def complete_scaffold(concept_id: str, utf_conn: sqlite3.Connection) -> Dict:
    """Complete missing slots in a concept scaffold using OpenAI."""
    c = utf_conn.cursor()
    c.execute('SELECT * FROM concept_scaffolds WHERE concept_id = ?', (concept_id,))
    row = c.fetchone()

    if not row:
        return {"success": False, "error": "Concept not found"}

    # Check which slots are missing
    slots = [
        ("scaffold_what", 4),
        ("scaffold_how", 5),
        ("scaffold_when_scope", 6),
        ("scaffold_why_stakes", 7),
        ("scaffold_how_to_use", 8),
        ("scaffold_boundary_conditions", 9),
        ("scaffold_failure_modes", 10)
    ]

    missing = [name for name, idx in slots if not row[idx]]

    if not missing:
        return {"success": True, "message": "Scaffold complete"}

    # Get context
    concept_name = row[1]
    context = row[3] or row[4] or ""  # definition_1liner or scaffold_what

    # Use OpenAI to complete
    result = openai_scaffold(concept_name, context, missing)

    if not result["success"]:
        return result

    # Parse response and update
    updates = {}
    for line in result["content"].split('\n'):
        line = line.strip()
        for slot_name, _ in slots:
            key = slot_name.replace("scaffold_", "").upper()
            if line.startswith(f"{key}:") or line.startswith(f"SCAFFOLD_{key}:"):
                updates[slot_name] = line.split(":", 1)[1].strip()

    if updates:
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [len([s for s, _ in slots if row[_] or updates.get(s)]), concept_id]
        c.execute(f'''UPDATE concept_scaffolds SET {set_clause}, completeness = ?, last_updated = datetime('now')
            WHERE concept_id = ?''', values)
        utf_conn.commit()

    return {"success": True, "slots_filled": list(updates.keys()), "tokens": result.get("tokens", 0)}

# ============================================================================
# Main Enhancement Pipeline
# ============================================================================

def run_enhancement(watch: bool = False, interval: int = 600):
    """Main enhancement loop."""
    print("=" * 60)
    print("UTF Enhancer - Post-Processing Layer")
    print("=" * 60)

    utf_conn = init_utf_db()
    hirag_conn = get_hirag_conn()

    if not hirag_conn:
        print("[WARN] HiRAG database not found. Waiting for autonomous_ingest...")

    stats = {"enhanced": 0, "assumptions": 0, "errors": 0}

    while True:
        # Reconnect if needed
        if not hirag_conn and HIRAG_DB.exists():
            hirag_conn = get_hirag_conn()
            print("[OK] Connected to HiRAG database")

        if hirag_conn:
            # Get unenhanced facts from HiRAG
            hc = hirag_conn.cursor()
            uc = utf_conn.cursor()

            # Find facts not yet enhanced
            hc.execute('''SELECT id, content, document_id FROM local_knowledge LIMIT 50''')

            for row in hc.fetchall():
                fact_id, content, doc_id = row

                # Check if already enhanced
                uc.execute('SELECT 1 FROM enhanced_facts WHERE fact_id = ?', (fact_id,))
                if uc.fetchone():
                    continue

                try:
                    result = enhance_fact(fact_id, content, doc_id, utf_conn)
                    stats["enhanced"] += 1
                    stats["assumptions"] += result["assumptions"]
                    print(f"  [+] {fact_id[:12]}: {result['claim_form']} ({result['dkcs']})")
                except Exception as e:
                    stats["errors"] += 1
                    print(f"  [!] Error: {e}")

        # Status
        print(f"\n[Stats] Enhanced: {stats['enhanced']}, Assumptions: {stats['assumptions']}, Errors: {stats['errors']}")

        if not watch:
            break

        print(f"\nSleeping {interval}s...")
        time.sleep(interval)

    utf_conn.close()
    if hirag_conn:
        hirag_conn.close()

def show_status():
    """Show enhancement statistics."""
    utf_conn = init_utf_db()
    c = utf_conn.cursor()

    print("=" * 60)
    print("UTF Enhancement Status")
    print("=" * 60)

    # Enhanced facts
    c.execute("SELECT COUNT(*) FROM enhanced_facts")
    enhanced = c.fetchone()[0]

    c.execute("SELECT claim_form, COUNT(*) FROM enhanced_facts GROUP BY claim_form ORDER BY COUNT(*) DESC")
    forms = c.fetchall()

    print(f"Enhanced facts: {enhanced}")
    if forms:
        print(f"  Forms: {', '.join(f'{f[0]}({f[1]})' for f in forms)}")

    # Assumptions
    c.execute("SELECT COUNT(*) FROM assumptions")
    assumptions = c.fetchone()[0]
    print(f"Assumptions extracted: {assumptions}")

    # Scaffolds
    c.execute("SELECT COUNT(*), AVG(completeness) FROM concept_scaffolds")
    scaffolds = c.fetchone()
    print(f"Concept scaffolds: {scaffolds[0] or 0} (avg completeness: {scaffolds[1] or 0:.1f}/7)")

    # HiRAG stats
    hirag_conn = get_hirag_conn()
    if hirag_conn:
        hc = hirag_conn.cursor()
        hc.execute("SELECT COUNT(*) FROM local_knowledge")
        total_facts = hc.fetchone()[0]
        print(f"\nHiRAG facts (total): {total_facts}")
        print(f"Enhancement coverage: {enhanced/max(total_facts,1)*100:.1f}%")
        hirag_conn.close()

    utf_conn.close()

# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='UTF Enhancer')
    parser.add_argument('--watch', action='store_true', help='Continuous enhancement')
    parser.add_argument('--interval', type=int, default=600, help='Check interval (seconds)')
    parser.add_argument('--status', action='store_true', help='Show enhancement stats')
    parser.add_argument('--scaffold', type=str, help='Complete scaffold for concept ID')

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.scaffold:
        utf_conn = init_utf_db()
        result = complete_scaffold(args.scaffold, utf_conn)
        print(json.dumps(result, indent=2))
        utf_conn.close()
    else:
        run_enhancement(watch=args.watch, interval=args.interval)
