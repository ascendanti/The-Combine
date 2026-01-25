#!/usr/bin/env python3
"""
Docling → Knowledge Graph Integration

Ingests documents (PDF, DOCX, etc.) using Docling, extracts entities,
and stores them in the local knowledge graph via MCP.

Usage:
    python docling-ingest.py <file_or_url>
    python docling-ingest.py --batch <directory>
"""

import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime

try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False

KNOWLEDGE_GRAPH_PATH = Path.home() / ".claude" / "memory" / "knowledge-graph.jsonl"

def extract_entities(text: str, source: str) -> list[dict]:
    """Extract key entities from document text."""
    entities = []

    # Document entity
    doc_hash = hashlib.md5(text.encode()).hexdigest()[:12]
    entities.append({
        "name": f"doc_{doc_hash}",
        "entityType": "document",
        "observations": [
            f"Source: {source}",
            f"Ingested: {datetime.now().isoformat()}",
            f"Length: {len(text)} chars",
            text[:500] + "..." if len(text) > 500 else text
        ]
    })

    # Extract sections (headers)
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            title = line.lstrip('# ').strip()
            if title:
                entities.append({
                    "name": f"section_{title[:30].lower().replace(' ', '_')}",
                    "entityType": "section",
                    "observations": [
                        f"Level: {level}",
                        f"Document: doc_{doc_hash}",
                        f"Title: {title}"
                    ]
                })

    return entities

def store_in_knowledge_graph(entities: list[dict]):
    """Store entities in local JSONL knowledge graph."""
    KNOWLEDGE_GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(KNOWLEDGE_GRAPH_PATH, 'a') as f:
        for entity in entities:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "type": "entity",
                "data": entity
            }
            f.write(json.dumps(entry) + '\n')

    return len(entities)

def ingest_document(path_or_url: str) -> dict:
    """Ingest a document and store in knowledge graph."""
    if not DOCLING_AVAILABLE:
        return {"error": "Docling not installed. Run: pip install docling"}

    try:
        converter = DocumentConverter()
        result = converter.convert(path_or_url)
        markdown = result.document.export_to_markdown()

        entities = extract_entities(markdown, path_or_url)
        stored = store_in_knowledge_graph(entities)

        return {
            "success": True,
            "source": path_or_url,
            "entities_stored": stored,
            "preview": markdown[:300] + "..." if len(markdown) > 300 else markdown
        }
    except Exception as e:
        return {"error": str(e), "source": path_or_url}

def main():
    if len(sys.argv) < 2:
        print("Usage: python docling-ingest.py <file_or_url>")
        print("       python docling-ingest.py --batch <directory>")
        sys.exit(1)

    if sys.argv[1] == "--batch":
        if len(sys.argv) < 3:
            print("Batch mode requires directory path")
            sys.exit(1)

        directory = Path(sys.argv[2])
        results = []
        for f in directory.glob("**/*"):
            if f.suffix.lower() in ['.pdf', '.docx', '.pptx', '.xlsx', '.html']:
                print(f"Processing: {f}")
                results.append(ingest_document(str(f)))
        print(json.dumps({"batch_results": results}, indent=2))
    else:
        result = ingest_document(sys.argv[1])
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
