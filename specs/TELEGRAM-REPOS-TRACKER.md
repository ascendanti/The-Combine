# Telegram Repos Tracker

*Git repositories received via Telegram for evaluation*

---

## Received & Analyzed

| # | Repo | Stars | Purpose | Status | Spec |
|---|------|-------|---------|--------|------|
| 1 | [twentyhq/twenty](https://github.com/twentyhq/twenty) | 39K | Open-source CRM | ✅ Selected | `ATLAS-CRM-SPEC.md` |
| 2 | [elie222/inbox-zero](https://github.com/elie222/inbox-zero) | 9.9K | AI email management | ✅ Spec'd | `INBOX-ZERO-INTEGRATION.md` |

---

## Analysis Summary

### 1. Twenty CRM
**Decision:** DEPLOY

| Aspect | Assessment |
|--------|------------|
| Tech Stack | React, NestJS, PostgreSQL (matches ours) |
| API | GraphQL + REST (excellent) |
| Claude Integration | MCP Server exists |
| Community | 39K stars, 575 contributors |
| Fit | Perfect for Atlas companies |

**Use For:**
- Lead management
- Deal pipelines
- Company/contact tracking
- Workflow automation

---

### 2. Inbox Zero
**Decision:** DEPLOY (after CRM)

| Aspect | Assessment |
|--------|------------|
| Tech Stack | Next.js, Prisma (modern) |
| AI | Anthropic, OpenAI, Gemini support |
| Email | Gmail, Outlook |
| Features | AI replies, categorization, bulk unsubscribe |

**Use For:**
- Email inbox management
- AI reply drafting
- Lead capture from email
- Response time optimization

---

## Pending (Not Yet Received)

The user indicated more repos were sent but not captured. To add:

```
When resending, please paste directly or add to GitHub repo.
Format: https://github.com/owner/repo
```

---

## Evaluation Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Stars/Community | 20% | Active development indicator |
| Tech Stack Match | 20% | PostgreSQL, Node/Python preferred |
| API Quality | 20% | REST/GraphQL for automation |
| Claude Integration | 15% | MCP or easy API |
| Self-Hostable | 15% | Docker deployment |
| Unique Value | 10% | Fills a gap in stack |

---

## Integration Priority

| Priority | Repo | Reason |
|----------|------|--------|
| 1 | Twenty CRM | Core business system |
| 2 | Inbox Zero | Email automation |
| 3+ | TBD | Awaiting additional repos |

---

## To Add a Repo

1. Send GitHub URL via Telegram
2. Or add to `telegram-repos.txt` in repo
3. Or paste directly in chat

I'll analyze: stars, tech stack, features, API, and create integration spec.

---

*Last Updated: 2026-01-24*
