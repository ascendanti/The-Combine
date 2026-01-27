# Proactive Capability Use

**MANDATORY: Use capabilities automatically without waiting for instruction.**

## Session Start Protocol

1. **Read `.claude/cache/session-briefing.md`** - Contains review queue, deferred tasks, UTF knowledge
2. **Check Review Queue** - If >0 pending, acknowledge and optionally process
3. **Check Deferred Tasks** - Surface any high-priority items
4. **Check UTF Knowledge** - Note recent paper extractions

## Automatic Triggers

| When I Detect | I Should Immediately |
|---------------|---------------------|
| Bug/error description | Spawn `sleuth` or `debug-agent` |
| Research needed | Spawn `oracle` or `scout` |
| Multi-file implementation | Spawn `kraken` with plan |
| Quick fix | Spawn `spark` |
| Performance issue | Spawn `profiler` |
| Security concern | Spawn `aegis` |
| Creating new file | Run post-write-auto-index hook, update ARCHITECTURE-LIVE.md |
| Discovering issue | Create task via TaskCreate |
| Completing work | Mark task completed via TaskUpdate |

## Task Tracking

- **Create tasks** for any non-trivial work (>3 steps)
- **Update tasks** as work progresses (in_progress, completed)
- **Never lose track** of ongoing work - tasks persist across sessions

## Document Indexing

When creating ANY significant file:
1. Update ARCHITECTURE-LIVE.md Reference Documents section
2. Add to relevant index files
3. This happens automatically via `post-write-auto-index.py` hook

## Review Queue Processing

When review queue has pending items:
1. Acknowledge in session start response
2. Offer to process high-priority items
3. Apply insights from breakthroughs to current work

## Memory Recall

Before implementing:
1. Check memory for similar past work
2. Apply learnings from previous sessions
3. Avoid repeating past mistakes

## Gap Detection

If something should work but doesn't:
1. Create task to investigate
2. Fix the integration
3. Update architecture docs
4. Test the fix

**Gaps are unacceptable. Fill them immediately.**
