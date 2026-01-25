# Before Acting Protocol

**STOP before any action. Check these first:**

## 1. Check Index
```
.claude/REPOSITORY-INDEX.md → Know where things are
```

## 2. Available Tools (Use Instead of Searching)
| Need | Tool | NOT |
|------|------|-----|
| Code structure | `tldr structure .` | Grep/Glob |
| Find code | `tldr search "X"` | Grep |
| Understand flow | `tldr cfg/dfg` | Reading all files |
| Impact analysis | `tldr impact func` | Guessing |
| Dead code | `tldr dead .` | Manual review |

## 3. Available Agents (Delegate)
| Task | Agent |
|------|-------|
| Explore codebase | scout |
| External research | oracle |
| Implementation | kraken |
| Quick fix | spark |
| Debug | sleuth |

## 4. Before Adding Packages
```bash
npm view <package> version 2>/dev/null || echo "DOES NOT EXIST"
```

## 5. Memory Check
```bash
python daemon/memory.py search "<topic>"
```

## 6. Token Efficiency
- Use agents for multi-file work
- Use tldr for code analysis
- Check index before searching
- Batch parallel operations

**NEVER guess. ALWAYS verify.**
