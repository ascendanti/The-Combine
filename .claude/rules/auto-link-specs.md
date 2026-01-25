# Auto-Link Specs Rule

**MANDATORY: After creating any new spec, document, or significant file:**

## Standard Protocol

When you create ANY of these:
- `specs/*.md` - Business or architecture specs
- `thoughts/handoffs/*.yaml` - Session handoffs
- `modules/*` - New input sources
- `.claude/*.md` - Planning documents
- `daemon/*.py` - New modules

**You MUST immediately:**

1. **Update RESOURCE-MAP.md** - Add entry to appropriate section
2. **Update task.md** - Note the new document in progress
3. **Update relevant index** - If domain-specific (e.g., TELEGRAM-REPOS-TRACKER.md)

## Quick Template

After creating `specs/NEW-SPEC.md`:

```markdown
# In RESOURCE-MAP.md, add to appropriate section:
| `NEW-SPEC.md` | Purpose | Usage |

# In task.md, add to completed:
- [x] Created NEW-SPEC.md - [brief description]
```

## Why This Matters

- Unlinked specs are invisible and forgotten
- The collective (RESOURCE-MAP) is the single source of truth
- Future sessions won't know the spec exists
- Integration requires visibility

## Enforcement

This rule is self-enforced. If you create a spec without linking it:
- You've violated standard protocol
- The work may be lost or duplicated
- User will have to remind you (waste of their time)

**Don't wait to be asked. Link immediately.**
