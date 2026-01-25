# Technical Debt Registry

*Structured tracking of deferred issues from code reviews*

---

## Active Tech Debt

### TD-001: Multiple SQLite Databases
**Severity:** MEDIUM
**Source:** System review 2026-01-25
**Files:** daemon/*.db (19 databases)
**Issue:** Each module creates own connection, no pooling
**Suggested Fix:** Consolidate to connection pool or single db
**Effort:** 3 days
**Blocked By:** None

---

### TD-002: Hook Error Isolation
**Severity:** LOW
**Source:** Code review 2026-01-24
**Files:** .claude/hooks/src/*.ts
**Issue:** Single hook failure can crash entire chain
**Suggested Fix:** Add try/catch per hook with continue-on-error
**Effort:** 2 hours
**Blocked By:** None

---

### TD-003: Handoff Format Inconsistency
**Severity:** LOW
**Source:** Pattern analysis 2026-01-25
**Files:** thoughts/handoffs/*.yaml
**Issue:** Some handoffs use different schemas
**Suggested Fix:** Standardize on delta_handoff.py format
**Effort:** 1 hour
**Blocked By:** None

---

## Resolved Tech Debt

| ID | Issue | Resolved | How |
|----|-------|----------|-----|
| - | - | - | - |

---

## Tech Debt by Severity

| Severity | Count | Oldest |
|----------|-------|--------|
| HIGH | 0 | - |
| MEDIUM | 1 | TD-001 |
| LOW | 2 | TD-002 |

---

## Adding New Tech Debt

When discovering tech debt during code review:

```markdown
### TD-XXX: [Title]
**Severity:** HIGH/MEDIUM/LOW
**Source:** [How discovered]
**Files:** [Affected files]
**Issue:** [Description]
**Suggested Fix:** [Approach]
**Effort:** [Estimate]
**Blocked By:** [Dependencies]
```
