# Known Issues & Fixes

## Package Dependency Conflicts

### MARM numpy/pandas Incompatibility (2026-01-26)

**Symptom:**
```
ValueError: numpy.dtype size changed, may indicate binary incompatibility.
Expected 96 from C header, got 88 from PyObject
```

**Cause:** MARM installation upgraded numpy to 2.4.1, but pandas/sklearn were compiled against older numpy. The C extension binary sizes don't match.

**Fix Options:**
1. Downgrade numpy: `pip install numpy==1.26.4`
2. Rebuild pandas: `pip install --force-reinstall pandas`
3. Use MARM as MCP server only (avoid Python import)

**Workaround Applied:** Implemented lightweight semantic caching using Jaccard similarity instead of sentence_transformers embeddings.

---

## Hook Integration Issues

### FewWord sed Errors

**Symptom:** `sed: -e expression #1, char 8: unterminated 's' command`

**Cause:** FewWord hook intercepts bash output and runs sed transformations that fail on certain output patterns.

**Fix:** Use `python -X utf8` for Python scripts, or redirect stderr.

---

## Import Path Issues

### daemon/ modules not found from project root

**Symptom:** `ModuleNotFoundError: No module named 'task_queue'`

**Cause:** Python can't find daemon modules when running from project root.

**Fix Applied:** Added `sys.path.insert(0, str(DAEMON_DIR))` at top of files that need cross-module imports.

---

## API Issues

### Claude API thinking block modification error

**Symptom:** `Error: 400 thinking or redacted_thinking blocks cannot have their text modified`

**Cause:** Hooks that modify message history may inadvertently touch thinking blocks.

**Fix:** Start fresh session. Don't modify message history in hooks.
