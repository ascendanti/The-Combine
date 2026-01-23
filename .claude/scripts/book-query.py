#!/usr/bin/env python3
"""
Quick book query interface.

Usage:
    python book-query.py "What is gradient descent?"
    python book-query.py --book <id> "query"
    python book-query.py --concepts  # List all concepts
    python book-query.py --summary <book_id>  # Get book summary tree
"""

import sys
import json
import sqlite3
import argparse
from pathlib import Path

BOOKS_DB = Path(__file__).parent.parent.parent / "daemon" / "books.db"

def query_all_books(query: str) -> dict:
    """Search across all ingested books."""
    if not BOOKS_DB.exists():
        return {"error": "No books database. Run book-ingest.py first."}

    conn = sqlite3.connect(BOOKS_DB)
    c = conn.cursor()

    results = {"query": query, "matches": []}

    # Search chunks via FTS
    c.execute('''SELECT c.book_id, b.title, c.content, c.chunk_type
        FROM chunks c
        JOIN chunks_fts fts ON c.rowid = fts.rowid
        JOIN books b ON c.book_id = b.id
        WHERE chunks_fts MATCH ?
        LIMIT 10''', (query,))

    for row in c.fetchall():
        results["matches"].append({
            "book_id": row[0],
            "book": row[1],
            "content": row[2][:400] + "..." if len(row[2]) > 400 else row[2],
            "type": row[3]
        })

    # Search concepts
    c.execute('''SELECT c.book_id, b.title, c.name, c.definition
        FROM concepts c
        JOIN books b ON c.book_id = b.id
        WHERE c.name LIKE ? OR c.definition LIKE ?
        LIMIT 5''', (f'%{query}%', f'%{query}%'))

    for row in c.fetchall():
        results["matches"].append({
            "book_id": row[0],
            "book": row[1],
            "concept": row[2],
            "definition": row[3][:300]
        })

    conn.close()
    return results

def get_summary_tree(book_id: str) -> dict:
    """Get hierarchical summary of a book."""
    conn = sqlite3.connect(BOOKS_DB)
    c = conn.cursor()

    c.execute('SELECT title, book_summary FROM books WHERE id = ?', (book_id,))
    book = c.fetchone()
    if not book:
        return {"error": f"Book {book_id} not found"}

    tree = {"title": book[0], "summary": book[1], "sections": []}

    # Get chapter-level summaries
    c.execute('''SELECT title, summary, key_concepts FROM summaries
        WHERE book_id = ? AND level IN ('chapter', 'part')
        ORDER BY rowid''', (book_id,))

    for row in c.fetchall():
        tree["sections"].append({
            "title": row[0],
            "summary": row[1],
            "concepts": json.loads(row[2]) if row[2] else []
        })

    conn.close()
    return tree

def list_concepts(book_id: str = None) -> list:
    """List all extracted concepts."""
    conn = sqlite3.connect(BOOKS_DB)
    c = conn.cursor()

    if book_id:
        c.execute('''SELECT c.name, c.definition, b.title
            FROM concepts c JOIN books b ON c.book_id = b.id
            WHERE c.book_id = ?''', (book_id,))
    else:
        c.execute('''SELECT c.name, c.definition, b.title
            FROM concepts c JOIN books b ON c.book_id = b.id''')

    concepts = []
    for row in c.fetchall():
        concepts.append({
            "name": row[0],
            "definition": row[1][:200],
            "book": row[2]
        })

    conn.close()
    return concepts

def main():
    parser = argparse.ArgumentParser(description='Query ingested books')
    parser.add_argument('query', nargs='?', help='Search query')
    parser.add_argument('--book', help='Specific book ID')
    parser.add_argument('--concepts', action='store_true', help='List concepts')
    parser.add_argument('--summary', help='Get book summary tree')

    args = parser.parse_args()

    if args.concepts:
        concepts = list_concepts(args.book)
        print(json.dumps(concepts, indent=2))
    elif args.summary:
        tree = get_summary_tree(args.summary)
        print(json.dumps(tree, indent=2))
    elif args.query:
        results = query_all_books(args.query)
        print(json.dumps(results, indent=2))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
