# System Constraints

*Hard limitations. Do NOT attempt workarounds without understanding impact.*

---

## Token Limits

| Constraint | Limit | Consequence |
|------------|-------|-------------|
| Claude context window | 200K tokens | Session truncation, need handoff |
| Claude output | 64K tokens | Response cut off |
| LocalAI context | 8K tokens | Overflow to Codex tier |
| Single file read | ~50K chars | Use chunked reading |

**Mitigation:** Use smart tools, delta handoffs, L-RAG gating.

---

## API Rate Limits

| Service | Limit | Reset |
|---------|-------|-------|
| Claude API | Varies by plan | Per-minute rolling |
| Codex | 20 req/min | 1 minute |
| GitHub API | 5000 req/hour | Hourly |
| Google Drive | 1000 req/100s | 100 seconds |

**Mitigation:** Queue requests, exponential backoff.

---

## Local Resources

| Resource | Constraint | Impact |
|----------|------------|--------|
| LocalAI GPU | Requires CUDA | Falls back to CPU (10x slower) |
| Dragonfly memory | 512MB default | Eviction at limit |
| SQLite concurrent writes | Single writer | Lock contention |

**Mitigation:** Connection pooling, batch writes.

---

## Windows-Specific

| Constraint | Impact | Workaround |
|------------|--------|------------|
| Path length | 260 char max | Use short paths |
| File locking | Stricter than Unix | Ensure files closed |
| Line endings | CRLF vs LF | Git autocrlf=true |
| PowerShell encoding | UTF-16 default | Explicit UTF-8 |

---

## Hook Limitations

| Constraint | Details |
|------------|---------|
| Execution time | Hooks should complete <5s |
| No async in PreToolUse | Must return synchronously |
| Stdio communication | JSON only, no streaming |
| No network in some hooks | Security sandbox |

---

## Model Limitations

| Model | Cannot Do |
|-------|-----------|
| LocalAI (qwen2.5) | Complex reasoning, long context |
| Codex | Multi-step planning, ambiguous tasks |
| Haiku | Anything requiring accuracy (banned) |

**Rule:** When in doubt, escalate to higher tier.

---

## Integration Constraints

### Google Drive
- **Pack size:** Keep <50MB for reliable sync
- **Polling interval:** Min 60s (API quota)
- **Manifest format:** Must be valid JSON

### Telegram
- **Message length:** 4096 chars max
- **Rate limit:** 30 msg/sec to same chat
- **File upload:** 50MB max

### GitHub
- **PR description:** 65536 chars max
- **Webhook payload:** 25MB max
- **Actions minutes:** Based on plan

---

## Security Constraints

| What | Constraint |
|------|------------|
| API keys | Never in code, always .env |
| User data | Never in logs or commits |
| External URLs | Validate before fetching |
| Bash commands | Sandboxed, no system modification |

---

## What We CAN'T Do

1. **Real-time streaming** - Claude API doesn't support true streaming in hooks
2. **Cross-session state** - Each Claude session starts fresh (use handoffs)
3. **GPU inference on CPU-only** - LocalAI requires GPU for acceptable speed
4. **Modify system files** - Sandboxed to project directory
5. **Unlimited context** - Must manage with handoffs and summarization
