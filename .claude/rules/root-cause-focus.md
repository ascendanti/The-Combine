# Root Cause Focus

**LESSON LEARNED:** Treating symptoms instead of identifying root cause wastes time and doesn't fix the problem.

## The Pattern That Failed

```
Symptom: tool_use ID conflict errors
Attempted fixes (treating symptoms):
  - Clear session cache
  - Fresh session IDs
  - --no-session-persistence flag
  - Temp directories
  - Disabled MCP
Result: Bug persisted

Root cause: Claude's native tool_use mechanism generates IDs that can conflict
Actual fix: Bypass tool_use entirely with JSON protocol
```

## Before Attempting Fixes

Ask these questions in order:

### 1. What is the actual error?
- Read the full error message
- Understand what component is complaining
- Don't assume based on keywords

### 2. Where does this error originate?
- Trace the error to its source
- Is it client-side, server-side, API-level?
- What system/mechanism produces this error?

### 3. What mechanism is involved?
- Understand the underlying mechanism
- Don't just patch around it
- Ask: "What would have to change for this error to be impossible?"

### 4. Is my fix addressing the mechanism or the symptom?
| Fix Type | Example | Outcome |
|----------|---------|---------|
| Symptom | "Clear cache when IDs conflict" | Bug returns |
| Workaround | "Retry on ID conflict" | Bug masked |
| Root cause | "Don't use the ID-generating mechanism" | Bug eliminated |

## Anti-Patterns

| Anti-Pattern | Why It Fails |
|--------------|--------------|
| "Clear the cache" | Symptom treatment unless cache IS the root cause |
| "Restart the service" | Hides the real issue |
| "Add a retry loop" | Masks intermittent failures |
| "Use a fresh session" | Only works if session state IS the problem |
| "Disable the feature" | Avoids the problem instead of solving it |

## The "Mechanical" Test

When the user says something should work "like an abacus" or "mechanically":
- They're pointing at unnecessary complexity
- Strip the system to its essential mechanism
- Rebuild only what's needed
- Often the simplest solution bypasses the problematic subsystem entirely

## Enforcement

Before implementing any fix:
1. State the root cause in one sentence
2. Explain why your fix addresses that cause
3. If you can't do both, investigate more
