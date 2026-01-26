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

**Workaround (DISCOVERED 2026-01-26):** Use Python subprocess to bypass hook entirely:
```python
python -c "import subprocess; r = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True, cwd=r'PATH'); print(r.stdout)"
```

**When to use:** Any bash command whose output is being garbled by FewWord sed processing - especially git commands with special characters in output.

---

## Import Path Issues

### daemon/ modules not found from project root

**Symptom:** `ModuleNotFoundError: No module named 'task_queue'`

**Cause:** Python can't find daemon modules when running from project root.

**Fix Applied:** Added `sys.path.insert(0, str(DAEMON_DIR))` at top of files that need cross-module imports.

---

## Windows Daemon Issues

### continuous_executor exits immediately (2026-01-26)

**Symptom:** Daemon starts but immediately exits. Status shows "running: false" even after start.

**Cause:** Windows kills child processes when parent shell closes. Background shell commands (`&`, `start /B`) don't create truly independent processes.

**Fix Applied:**
```python
# In main() for 'start' action:
if os.name == "nt" and not os.environ.get("CONTINUOUS_EXECUTOR_CHILD"):
    env = os.environ.copy()
    env["CONTINUOUS_EXECUTOR_CHILD"] = "1"
    proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "start"],
        cwd=str(DAEMON_DIR),
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
```

**Key elements:**
- `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` flags for true independence
- Environment marker prevents infinite spawn loop
- DEVNULL for stdio to prevent handle inheritance issues

---

### os.kill(pid, 0) fails on Windows (2026-01-26)

**Symptom:** Status check returns "running: false" even when process IS running.

**Cause:** `os.kill(pid, 0)` returns `[WinError 87] The parameter is incorrect` on Windows. Signal 0 isn't valid on Windows.

**Fix Applied:**
```python
def _is_process_running(pid: int) -> bool:
    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/fi", f"PID eq {pid}", "/nh"],
            capture_output=True, text=True, timeout=5
        )
        return str(pid) in result.stdout
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
```

---

### B:/ drive error popup (2026-01-26)

**Symptom:** Windows shows "B: the system cannot find the drive specified" dialog.

**Cause:** Using `start /B` bash command syntax. The `/B` flag can be misinterpreted by Windows.

**Fix:** Avoid `start /B` syntax. Use Python subprocess with proper flags instead.

---

## API Issues

### Claude API thinking block modification error

**Symptom:** `Error: 400 thinking or redacted_thinking blocks cannot have their text modified`

**Cause:** Hooks that modify message history may inadvertently touch thinking blocks.

**Fix:** Start fresh session. Don't modify message history in hooks.
