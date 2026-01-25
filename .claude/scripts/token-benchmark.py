#!/usr/bin/env python3
"""
Token Efficiency Benchmark

Measures token consumption and quality across providers:
- LocalAI (FREE)
- Codex/gpt-4o-mini ($)
- Claude ($$$)

Usage:
    python token-benchmark.py --pdf "path/to/large.pdf"
    python token-benchmark.py --text "large text content"
    python token-benchmark.py --report
"""

import argparse
import json
import time
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add daemon to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "daemon"))

try:
    from model_router import ModelRouter, TaskType, Provider, estimate_tokens
    ROUTER_AVAILABLE = True
except ImportError:
    ROUTER_AVAILABLE = False
    print("[WARN] model_router not available")

# Benchmark database
BENCHMARK_DB = Path(__file__).parent.parent.parent / "daemon" / "benchmark.db"


def init_db():
    """Initialize benchmark database."""
    conn = sqlite3.connect(BENCHMARK_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS benchmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            test_name TEXT,
            provider TEXT,
            task_type TEXT,
            input_tokens INTEGER,
            output_tokens INTEGER,
            latency_ms INTEGER,
            cost_estimate REAL,
            quality_score REAL,
            content_hash TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_benchmark(test_name: str, provider: str, task_type: str,
                  input_tokens: int, output_tokens: int, latency_ms: int,
                  cost: float, quality: float, content_hash: str):
    """Log benchmark result."""
    conn = sqlite3.connect(BENCHMARK_DB)
    conn.execute("""
        INSERT INTO benchmarks
        (timestamp, test_name, provider, task_type, input_tokens, output_tokens,
         latency_ms, cost_estimate, quality_score, content_hash)
        VALUES (datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (test_name, provider, task_type, input_tokens, output_tokens,
          latency_ms, cost, quality, content_hash))
    conn.commit()
    conn.close()


def estimate_cost(provider: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost based on provider pricing."""
    costs = {
        "localai": (0, 0),           # FREE
        "codex": (0.15, 0.6),        # gpt-4o-mini per 1M tokens
        "openai": (2.5, 10.0),       # gpt-4o per 1M tokens
        "claude": (3.0, 15.0),       # Claude Sonnet per 1M tokens
    }
    if provider not in costs:
        return 0.0
    input_rate, output_rate = costs[provider]
    return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000


def benchmark_summarization(content: str, router: ModelRouter, test_name: str = "summarize"):
    """Benchmark summarization across all providers."""
    import hashlib
    content_hash = hashlib.md5(content[:1000].encode()).hexdigest()[:8]

    results = []
    task = "Summarize this content in 3-5 key points"

    for provider in [Provider.LOCALAI, Provider.CODEX, Provider.CLAUDE]:
        print(f"\n[TEST] {provider.value}...")

        start = time.time()
        try:
            result = router.route(task, content, force_provider=provider)
            latency = int((time.time() - start) * 1000)

            if result.get("response"):
                input_tokens = result["tokens_used"]["input"]
                output_tokens = estimate_tokens(result["response"])
                cost = estimate_cost(provider.value, input_tokens, output_tokens)

                # Quality heuristic: length and keyword coverage
                quality = min(1.0, len(result["response"]) / 500)  # Rough proxy

                log_benchmark(test_name, provider.value, "summarize",
                             input_tokens, output_tokens, latency, cost, quality, content_hash)

                results.append({
                    "provider": provider.value,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "latency_ms": latency,
                    "cost": cost,
                    "response_preview": result["response"][:200] + "..."
                })
                print(f"    Input: {input_tokens} tokens, Output: {output_tokens} tokens")
                print(f"    Latency: {latency}ms, Cost: ${cost:.6f}")
            else:
                print(f"    [SKIP] Provider returned no response (may be pass-through)")
                results.append({
                    "provider": provider.value,
                    "status": "pass-through",
                    "note": "Claude provider returns None for in-session execution"
                })

        except Exception as e:
            print(f"    [ERROR] {e}")
            results.append({"provider": provider.value, "error": str(e)})

    return results


def benchmark_code_task(code_content: str, router: ModelRouter, test_name: str = "code_review"):
    """Benchmark code review/generation across providers."""
    import hashlib
    content_hash = hashlib.md5(code_content[:1000].encode()).hexdigest()[:8]

    results = []
    task = "Review this code for potential issues, suggest improvements"

    for provider in [Provider.CODEX, Provider.CLAUDE]:  # Skip LocalAI for code
        print(f"\n[TEST] {provider.value}...")

        start = time.time()
        try:
            result = router.route(task, code_content, force_provider=provider)
            latency = int((time.time() - start) * 1000)

            if result.get("response"):
                input_tokens = result["tokens_used"]["input"]
                output_tokens = estimate_tokens(result["response"])
                cost = estimate_cost(provider.value, input_tokens, output_tokens)
                quality = min(1.0, len(result["response"]) / 800)

                log_benchmark(test_name, provider.value, "code_review",
                             input_tokens, output_tokens, latency, cost, quality, content_hash)

                results.append({
                    "provider": provider.value,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "latency_ms": latency,
                    "cost": cost,
                    "response_preview": result["response"][:200] + "..."
                })
                print(f"    Input: {input_tokens} tokens, Output: {output_tokens} tokens")
                print(f"    Latency: {latency}ms, Cost: ${cost:.6f}")
            else:
                print(f"    [SKIP] Pass-through")
                results.append({"provider": provider.value, "status": "pass-through"})

        except Exception as e:
            print(f"    [ERROR] {e}")
            results.append({"provider": provider.value, "error": str(e)})

    return results


def generate_report():
    """Generate benchmark report from database."""
    conn = sqlite3.connect(BENCHMARK_DB)

    # Summary by provider
    print("\n" + "=" * 60)
    print("TOKEN EFFICIENCY BENCHMARK REPORT")
    print("=" * 60)

    cursor = conn.execute("""
        SELECT
            provider,
            COUNT(*) as tests,
            SUM(input_tokens) as total_input,
            SUM(output_tokens) as total_output,
            AVG(latency_ms) as avg_latency,
            SUM(cost_estimate) as total_cost
        FROM benchmarks
        GROUP BY provider
        ORDER BY total_cost ASC
    """)

    print("\n[BY PROVIDER]")
    print(f"{'Provider':<12} {'Tests':<8} {'Input Tok':<12} {'Output Tok':<12} {'Avg Latency':<12} {'Total Cost':<12}")
    print("-" * 68)

    for row in cursor.fetchall():
        provider, tests, inp, out, latency, cost = row
        print(f"{provider:<12} {tests:<8} {inp or 0:<12} {out or 0:<12} {latency or 0:<12.0f}ms ${cost or 0:<11.6f}")

    # Token savings calculation
    cursor = conn.execute("""
        SELECT SUM(input_tokens + output_tokens) FROM benchmarks WHERE provider = 'localai'
    """)
    localai_tokens = cursor.fetchone()[0] or 0

    cursor = conn.execute("""
        SELECT SUM(input_tokens + output_tokens) FROM benchmarks WHERE provider = 'codex'
    """)
    codex_tokens = cursor.fetchone()[0] or 0

    # Calculate Claude equivalent cost
    claude_equiv_cost = (localai_tokens * 3 + localai_tokens * 15 +
                         codex_tokens * 3 + codex_tokens * 15) / 2_000_000

    cursor = conn.execute("SELECT SUM(cost_estimate) FROM benchmarks")
    actual_cost = cursor.fetchone()[0] or 0

    print("\n[SAVINGS ANALYSIS]")
    print(f"LocalAI tokens (FREE):       {localai_tokens:,}")
    print(f"Codex tokens (cheap):        {codex_tokens:,}")
    print(f"If all via Claude:           ${claude_equiv_cost:.4f}")
    print(f"Actual cost:                 ${actual_cost:.4f}")
    print(f"SAVINGS:                     ${claude_equiv_cost - actual_cost:.4f} ({((claude_equiv_cost - actual_cost) / max(claude_equiv_cost, 0.0001)) * 100:.1f}%)")

    conn.close()


def load_pdf_text(pdf_path: str) -> str:
    """Extract text from PDF for benchmarking."""
    try:
        # Try PyMuPDF first
        import fitz
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except ImportError:
        pass

    try:
        # Try pypdf
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except ImportError:
        print("[ERROR] Install pypdf or pymupdf: pip install pypdf")
        return ""


def main():
    parser = argparse.ArgumentParser(description="Token Efficiency Benchmark")
    parser.add_argument("--pdf", help="Path to PDF file to benchmark")
    parser.add_argument("--text", help="Text content to benchmark")
    parser.add_argument("--code", help="Path to code file to benchmark")
    parser.add_argument("--report", action="store_true", help="Generate report")
    parser.add_argument("--test-name", default="benchmark", help="Name for this test")

    args = parser.parse_args()

    init_db()

    if args.report:
        generate_report()
        return

    if not ROUTER_AVAILABLE:
        print("[ERROR] model_router not available")
        return

    router = ModelRouter()

    # Check providers
    print("[CHECKING PROVIDERS]")
    print(f"LocalAI: {'OK' if router.localai.available() else 'UNAVAILABLE'}")
    print(f"OpenAI:  {'OK' if router.openai_client.available() else 'UNAVAILABLE'}")

    content = ""
    if args.pdf:
        print(f"\n[LOADING PDF] {args.pdf}")
        content = load_pdf_text(args.pdf)
        print(f"Extracted {len(content)} characters ({estimate_tokens(content)} tokens)")

    elif args.text:
        content = args.text

    elif args.code:
        with open(args.code) as f:
            content = f.read()
        print(f"\n[BENCHMARKING CODE TASK]")
        results = benchmark_code_task(content, router, args.test_name)
        print("\n[RESULTS]")
        print(json.dumps(results, indent=2, default=str))
        return

    if not content:
        print("[ERROR] Provide --pdf, --text, or --code")
        return

    print(f"\n[BENCHMARKING SUMMARIZATION]")
    results = benchmark_summarization(content, router, args.test_name)

    print("\n[RESULTS]")
    print(json.dumps(results, indent=2, default=str))

    print("\n[REPORT]")
    generate_report()


if __name__ == "__main__":
    main()
