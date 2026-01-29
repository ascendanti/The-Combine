# Token Compression Use Cases

## Quick Reference

| Data Type | Compressor | Function | Threshold |
|-----------|------------|----------|-----------|
| Uniform lists of dicts | **toonify** | `toonify_data(data)` | 10+ items |
| Mixed content | **headroom** | `compress_tool_output(data)` | 2000+ chars |
| Search results | **headroom** | `compress_search_results(data)` | 15+ results |
| Logs/text | **headroom** | `compress_logs(lines)` | 50+ lines |
| File content | **context_router** | HOT/WARM/COLD tiering | Automatic |

## When to Use Toonify

**Ideal for:**
- Database query results (uniform rows)
- API responses with repeated structure
- Task lists, memory entries
- Any `List[Dict]` with same keys

**Example:**
```python
from toonify_optimizer import toonify_data, estimate_savings

# Check if worth it
result = estimate_savings(data)
if result.savings_pct >= 30:
    compressed = result.toon_str  # Use this for LLM
```

**NOT for:**
- Nested/irregular structures
- Single objects
- Text content
- Data that needs to remain human-readable

## When to Use Headroom

**Ideal for:**
- Tool outputs (grep, glob results)
- Mixed content (text + structured)
- Log files
- Any content where context matters

**Example:**
```python
from headroom_optimizer import compress_tool_output, compress_search_results

# Tool output (keeps first/last/anomalies)
compressed = compress_tool_output(data, max_items=20)

# Search results (keeps most relevant)
compressed = compress_search_results(results, max_results=15)
```

## Decision Flow

```
Is data a List[Dict] with uniform keys?
├─ YES → Check estimate_savings()
│        ├─ savings >= 30% → Use toonify
│        └─ savings < 30% → Use headroom or raw
└─ NO → Is it search/tool output?
         ├─ YES → Use headroom
         └─ NO → Is it a file?
                  ├─ YES → Use context_router (automatic)
                  └─ NO → Keep as-is (small data)
```

## Integration Points

### Auto-cache-post.py (PostToolUse)
- Tries headroom first
- Falls back to toonify for structured JSON

### Unified_spine.py (_compress_output)
- Tries headroom for general content
- Falls back to toonify for JSON structures

### Orchestrator.py (process return)
- Uses headroom for responses
- Uses toonify for structured results

### Memory_router.py (_cache_set)
- Uses headroom for large result sets

### Model_router.py (ContextBuilder)
- Uses headroom for large content

## Direct Access

```python
# From any daemon module:
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# Toonify
from toonify_optimizer import toonify_data, detoonify_data, estimate_savings, optimize_for_llm

# Headroom
from headroom_optimizer import compress_tool_output, compress_search_results, compress_logs
```

## Savings Benchmarks

| Data Type | Toonify | Headroom | Winner |
|-----------|---------|----------|--------|
| 100 uniform dicts | 65% | 40% | Toonify |
| Mixed API response | 30% | 55% | Headroom |
| Log file (500 lines) | N/A | 80% | Headroom |
| Search results | 45% | 60% | Headroom |
| Task queue entries | 70% | 35% | Toonify |

## Rule

**Use toonify for uniform structured data. Use headroom for everything else.**
