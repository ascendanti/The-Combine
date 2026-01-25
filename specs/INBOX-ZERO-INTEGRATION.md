# Inbox Zero Integration

*AI Email Assistant for Atlas Companies*

---

## Overview

[Inbox Zero](https://github.com/elie222/inbox-zero) - Open source AI email management with 9,900+ GitHub stars. Complements Twenty CRM by handling email automation.

---

## Key Features

| Feature | Benefit |
|---------|---------|
| **AI Reply Drafting** | Responds in your tone/style |
| **Plain English Rules** | "Cursor Rules for email" |
| **Reply Zero** | Track emails needing response |
| **Smart Categorization** | Auto-sort by sender type |
| **Bulk Unsubscribe** | One-click cleanup |
| **Cold Email Blocker** | Filter outreach spam |
| **Email Analytics** | Activity tracking |
| **Meeting Briefs** | Context from email/calendar |
| **Smart Filing** | Auto-save attachments |

---

## Tech Stack

- **Frontend:** Next.js, Tailwind, shadcn/ui
- **Backend:** Prisma, Upstash
- **LLM Providers:** Anthropic, OpenAI, Gemini, Groq
- **Email:** Gmail, Outlook/M365

---

## Integration with Atlas Stack

```
┌─────────────────────────────────────────────────────────────┐
│                     INBOX ZERO                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Gmail    │  │ Outlook  │  │ AI Draft │  │ Analytics│    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       └─────────────┴─────────────┴─────────────┘           │
│                         │                                    │
└─────────────────────────┼────────────────────────────────────┘
                          │
                    Webhook / API
                          │
┌─────────────────────────┼────────────────────────────────────┐
│                   TWENTY CRM                                 │
│  New email from unknown → Create Lead                        │
│  Email from contact → Log as Activity                        │
│  Reply sent → Update contact timeline                        │
└─────────────────────────┼────────────────────────────────────┘
                          │
┌─────────────────────────┼────────────────────────────────────┐
│                 CLAUDE COGNITIVE                             │
│  Lead research triggered                                     │
│  Proposal generation                                         │
│  Follow-up scheduling                                        │
└──────────────────────────────────────────────────────────────┘
```

---

## Email Accounts to Connect

| Account | Company | Purpose |
|---------|---------|---------|
| adam.a.bensaid@gmail.com | Personal | Primary inbox |
| info@atlasanalytics.com | Atlas Analytics | Intelligence inquiries |
| hello@atlasconsulting.ca | Atlas Consulting | Advisory inquiries |
| contact@atlascontent.com | Atlas Content | Content partnerships |
| press@atlasmedia.co | Atlas Media | Production inquiries |
| orders@algiersbay.com | Algiers Bay | Product orders |
| submissions@atlaspublishing.com | Atlas Publishing | Author submissions |

---

## AI Rules (Plain English)

### General Rules
```
1. Newsletters and promotional emails → Archive immediately
2. Cold sales pitches → Block sender, archive
3. Meeting requests → Add to calendar, draft acceptance
4. Invoice/receipt emails → Label "Finance", archive
5. Personal emails from known contacts → Keep in inbox
```

### Lead Detection Rules
```
1. If email mentions "consulting", "advisory", or "strategy"
   → Label "Lead:Consulting", keep in inbox, notify Telegram

2. If email mentions "research", "intelligence", or "analysis"
   → Label "Lead:Analytics", keep in inbox, notify Telegram

3. If email mentions "documentary", "production", or "video"
   → Label "Lead:Media", keep in inbox, notify Telegram

4. If email mentions "wholesale", "import", or "products"
   → Label "Lead:AlgiersBay", keep in inbox, notify Telegram

5. If email mentions "manuscript", "publish", or "book"
   → Label "Lead:Publishing", keep in inbox, notify Telegram
```

### Reply Rules
```
1. First-time inquiries → Draft friendly intro, mention next steps
2. Follow-ups on proposals → Draft update, ask for questions
3. Meeting confirmations → Draft brief acknowledgment
4. Thank you emails → Draft gracious response
5. Urgent requests → Flag, draft immediate response, notify Telegram
```

---

## Docker Deployment

```yaml
# Add to docker-compose.yaml
  inbox-zero:
    image: inboxzero/inbox-zero:latest
    ports:
      - "3001:3000"
    environment:
      - DATABASE_URL=postgres://claude:claude_dev@postgres:5432/inbox_zero
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      - MICROSOFT_CLIENT_ID=${MICROSOFT_CLIENT_ID}
      - MICROSOFT_CLIENT_SECRET=${MICROSOFT_CLIENT_SECRET}
    depends_on:
      - postgres
    volumes:
      - inbox_zero_data:/app/data

volumes:
  inbox_zero_data:
```

---

## CRM Integration Flow

### New Email → Lead Creation

```python
# daemon/email_to_crm.py
def handle_new_email(email: dict):
    """Process new email from Inbox Zero webhook."""

    sender = email["from"]
    subject = email["subject"]
    body = email["body"]

    # Check if sender exists in CRM
    contact = twenty_api.find_contact(sender)

    if contact:
        # Log as activity on existing contact
        twenty_api.add_activity(
            contact_id=contact.id,
            type="email_received",
            subject=subject,
            content=body[:500]
        )
    else:
        # Create new lead
        lead = twenty_api.create_lead(
            email=sender,
            source="email",
            notes=f"Subject: {subject}\n\n{body[:1000]}"
        )

        # Trigger research
        research_queue.add(lead.id)

        # Notify
        telegram.send(f"New lead from email: {sender}")
```

### Reply Sent → Activity Logged

```python
def handle_reply_sent(email: dict):
    """Log reply as activity in CRM."""

    recipient = email["to"]
    contact = twenty_api.find_contact(recipient)

    if contact:
        twenty_api.add_activity(
            contact_id=contact.id,
            type="email_sent",
            subject=email["subject"],
            content=email["body"][:500]
        )

        # Update last contact date
        twenty_api.update_contact(
            contact.id,
            last_contact=datetime.now()
        )
```

---

## Automation Workflows

### Morning Briefing
```
6:00 AM:
1. Inbox Zero processes overnight emails
2. Categorizes and archives low-priority
3. Drafts replies for high-priority
4. Generates summary → Telegram

You wake up to:
- Clean inbox (only important)
- Pre-drafted replies ready to send
- New leads already in CRM
- Daily briefing on Telegram
```

### Lead Response SLA
```
New lead email arrives:
0 min: Inbox Zero categorizes
1 min: Webhook → CRM creates lead
2 min: Research triggered
5 min: AI drafts personalized response
10 min: You review and send (or auto-send)

Result: <10 min response time
```

### Follow-up Automation
```
Proposal sent (logged in CRM):
Day 3: Inbox Zero drafts follow-up
Day 3: "Checking in on the proposal..."
Day 7: If no reply, second follow-up
Day 14: Break-up email drafted
```

---

## Analytics Integration

| Metric | Source | Use |
|--------|--------|-----|
| Response time | Inbox Zero | Track SLA |
| Email volume | Inbox Zero | Capacity planning |
| Open rates | Inbox Zero | Engagement tracking |
| Lead source | CRM | Attribution |
| Conversion rate | CRM | Email effectiveness |

---

## Implementation Steps

### Week 1: Deploy
- [ ] Docker compose setup
- [ ] Connect Gmail accounts
- [ ] Configure AI provider (Anthropic)
- [ ] Test basic inbox management

### Week 2: Rules
- [ ] Create plain English rules
- [ ] Set up lead detection
- [ ] Configure reply templates
- [ ] Test categorization

### Week 3: Integration
- [ ] Build webhook handlers
- [ ] Connect to Twenty CRM
- [ ] Test lead creation flow
- [ ] Set up Telegram notifications

---

## Combined System

With **Twenty CRM** + **Inbox Zero**:

| Function | Tool |
|----------|------|
| Contact management | Twenty |
| Deal pipeline | Twenty |
| Email inbox | Inbox Zero |
| AI replies | Inbox Zero |
| Lead research | Claude |
| Proposals | Claude |
| Notifications | Telegram |
| Scheduling | Calendar (via Inbox Zero) |

**Result:** Fully automated sales office with minimal human intervention.

---

*Source: [Inbox Zero GitHub](https://github.com/elie222/inbox-zero)*
*Generated: 2026-01-24*
