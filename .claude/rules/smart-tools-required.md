# Smart Tools Required

**MANDATORY**: Always use token-optimized MCP tools instead of native tools.

## Tool Mapping

| Instead of | Use | Savings |
|------------|-----|---------|
| `Read` | `mcp__token-optimizer__smart_read` | 70-80% |
| `Grep` | `mcp__token-optimizer__smart_grep` | 60-70% |
| `Glob` | `mcp__token-optimizer__smart_glob` | 50-60% |

## How to Use

```
# Instead of Read:
mcp__token-optimizer__smart_read with {"path": "file/path"}

# Instead of Grep:
mcp__token-optimizer__smart_grep with {"pattern": "search", "cwd": "."}

# Instead of Glob:
mcp__token-optimizer__smart_glob with {"pattern": "**/*.py", "cwd": "."}
```

## Exceptions (use native tools)

- Small config files (<1KB): .env, package.json, settings.json
- Files being edited (need exact content for Edit tool)
- When MCP server is unavailable

## Why This Matters

Native tools return full content every time. Smart tools:
- Cache results (instant on repeat reads)
- Return diffs (only changes since last read)
- Compress output (syntax-aware truncation)
- Track token savings

## Enforcement

The `smart-tool-redirect` hook will log violations. Target: 0 violations per session.
