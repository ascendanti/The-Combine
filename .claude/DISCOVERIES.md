# Codebase Discoveries

Patterns, workarounds, and learnings discovered during development. These are institutionalized to avoid re-discovery.

---

## Bash/Shell Workarounds

### FewWord Hook Bypass (2026-01-26)

**Problem:** FewWord hook intercepts bash output and runs sed transformations that fail on certain patterns.

**Symptom:**
```
sed: -e expression #1, char 8: unterminated 's' command
```

**Root Cause:** FewWord processes command output through sed for formatting, but special characters in git/command output break the sed pattern.

**Solution:** Use Python subprocess to bypass hooks entirely:
```python
python -c "import subprocess; r = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True, cwd=r'PATH'); print(r.stdout)"
```

**When to use:** Any bash command whose output is garbled by hook processing.

---

## Import Path Patterns

### Daemon Module Cross-Imports (2026-01-26)

**Problem:** Python can't find daemon modules when running from project root.

**Symptom:** `ModuleNotFoundError: No module named 'task_queue'`

**Solution:** Add at top of files that need cross-module imports:
```python
import sys
from pathlib import Path
DAEMON_DIR = Path(__file__).parent
sys.path.insert(0, str(DAEMON_DIR))
```

---

## API Patterns

### Claude Thinking Block Errors (2026-01-26)

**Problem:** Hooks that modify message history touch thinking blocks.

**Symptom:** `Error: 400 thinking or redacted_thinking blocks cannot have their text modified`

**Solution:** Start fresh session. Don't modify message history in hooks.

---

## Dependency Patterns

### numpy Binary Incompatibility (2026-01-26)

**Problem:** Installing packages that upgrade numpy breaks pandas/sklearn.

**Symptom:**
```
ValueError: numpy.dtype size changed, may indicate binary incompatibility
```

**Root Cause:** C extensions compiled against different numpy versions have incompatible binary sizes.

**Solutions:**
1. Downgrade numpy: `pip install numpy==1.26.4`
2. Rebuild dependent packages: `pip install --force-reinstall pandas`
3. Use package as MCP server only (avoid Python import)

---

## Git Patterns

### Porcelain Output for Parsing (2026-01-26)

**Discovery:** Use `--porcelain` flag for machine-parseable git output:
```bash
git status --porcelain
git diff --stat HEAD
```

This avoids formatting that can break when piped through hooks.

---

## Memory/Cache Patterns

### Semantic Cache Without Embeddings (2026-01-26)

**Discovery:** Jaccard similarity on normalized word sets provides lightweight semantic matching without requiring embedding models:

```python
def semantic_similarity(q1, q2):
    words1 = set(q1.lower().split()) - stop_words
    words2 = set(q2.lower().split()) - stop_words
    return len(words1 & words2) / len(words1 | words2)
```

**Thresholds:**
- >0.85: High confidence match (return cached)
- 0.5-0.85: Acceptable match (use cached)
- <0.5: Too different (bypass cache)

**Limitation:** Word-based only, doesn't capture semantic meaning. Consider embedding-based cache for production (see: prompt-cache, oasysdb).

---

## Adding New Discoveries

When you discover a pattern or workaround:

1. Add it to this file with date and context
2. Store in memory: `python daemon/memory.py store-learning "DISCOVERY" --tags discovery,CATEGORY`
3. Update KNOWN-ISSUES.md if it's a recurring problem
4. Update relevant code comments

**Tags to use:** `discovery`, `workaround`, `pattern`, `gotcha`, plus category (bash, import, api, etc.)
