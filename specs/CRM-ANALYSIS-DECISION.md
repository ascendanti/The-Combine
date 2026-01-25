# CRM Analysis & Decision

*Comparing open-source CRMs for Atlas Companies*

---

## Requirements

| Feature | Priority | Notes |
|---------|----------|-------|
| Lead generation | High | Capture from web, social, email |
| Automated employees/office | High | AI agents handling routine tasks |
| Target client research | High | Company/contact enrichment |
| Proposal building | High | Template-based, AI-assisted |
| Deal management | High | Pipeline, stages, forecasting |
| Deal closing | High | Contracts, signatures, handoff |
| Self-hosted | Required | Data sovereignty |
| Claude integration | Required | MCP/API for AI automation |

---

## Candidates Analyzed

### 1. Twenty CRM (YOUR SELECTION)

| Aspect | Rating | Details |
|--------|--------|---------|
| **GitHub Stars** | 39,000+ | Most popular open-source CRM |
| **Tech Stack** | React, NestJS, PostgreSQL | Matches our infrastructure |
| **API** | GraphQL + REST | Full programmatic access |
| **Claude Integration** | MCP Server exists | Direct AI assistant integration |
| **Customization** | Excellent | Custom objects, fields, workflows |
| **Community** | 575+ contributors | Very active |
| **Last Release** | Jan 24, 2026 | Actively maintained |

**Pros:**
- Modern UI/UX (Salesforce-quality)
- Full API for automation
- MCP server for Claude integration
- PostgreSQL (same as our stack)
- Highly customizable data models

**Cons:**
- No built-in lead capture (need to build)
- No native proposal generation (need to build)
- Relatively new (less enterprise battle-testing)

---

### 2. Frappe CRM / ERPNext

| Aspect | Rating | Details |
|--------|--------|---------|
| **GitHub Stars** | 2,000 (CRM) / 22,000 (ERPNext) | Strong ecosystem |
| **Tech Stack** | Python, Vue, MariaDB | Different from ours |
| **API** | REST | Good but not GraphQL |
| **Claude Integration** | AI extensions available | Frappe AI module |
| **Customization** | Excellent | Full ERP integration |

**Pros:**
- Complete ERP+CRM ecosystem
- Invoicing, inventory, HR built-in
- Strong accounting integration
- AI module for content generation

**Cons:**
- Heavier (full ERP when you may only need CRM)
- Different tech stack (Python/MariaDB)
- Steeper learning curve

---

### 3. EspoCRM

| Aspect | Rating | Details |
|--------|--------|---------|
| **GitHub Stars** | 2,300 | Smaller community |
| **Tech Stack** | PHP, MySQL | Legacy stack |
| **API** | REST | Basic |
| **Customization** | Good | BPMN 2.0 workflows |

**Pros:**
- Simple, lightweight
- Email-to-Case automation
- Lower resource requirements

**Cons:**
- PHP (maintenance burden)
- Limited AI capabilities
- Smaller community

---

### 4. SuiteCRM

| Aspect | Rating | Details |
|--------|--------|---------|
| **GitHub Stars** | 4,500 | Established |
| **Tech Stack** | PHP, MySQL | Legacy |
| **API** | REST v8 | Adequate |
| **Customization** | Enterprise-grade | Module builder |

**Pros:**
- Enterprise features
- Salesforce migration tools
- Workflow automation

**Cons:**
- PHP legacy codebase
- Dated UI
- Resource-heavy

---

### 5. Odoo CRM

| Aspect | Rating | Details |
|--------|--------|---------|
| **GitHub Stars** | 40,000+ (full Odoo) | Massive ecosystem |
| **Tech Stack** | Python, PostgreSQL | Familiar DB |
| **API** | XML-RPC, JSON-RPC | Older API styles |
| **Customization** | Excellent | App marketplace |

**Pros:**
- Complete business suite
- AI lead scoring
- Massive app ecosystem

**Cons:**
- Complex licensing (Community vs Enterprise)
- Many features require paid apps
- Heavy resource requirements

---

## Decision Matrix

| Criterion | Weight | Twenty | Frappe | EspoCRM | SuiteCRM | Odoo |
|-----------|--------|--------|--------|---------|----------|------|
| API Quality | 20% | 10 | 7 | 6 | 6 | 5 |
| Claude Integration | 20% | 10 | 7 | 4 | 4 | 5 |
| Modern Stack | 15% | 10 | 8 | 4 | 4 | 7 |
| Customization | 15% | 9 | 9 | 7 | 8 | 9 |
| Community | 10% | 10 | 7 | 6 | 7 | 9 |
| Resource Efficiency | 10% | 8 | 6 | 9 | 5 | 4 |
| Learning Curve | 10% | 8 | 6 | 9 | 6 | 5 |
| **TOTAL** | 100% | **9.3** | 7.2 | 6.0 | 5.7 | 6.2 |

---

## RECOMMENDATION: Twenty CRM

**Decision:** Proceed with Twenty CRM

**Rationale:**
1. **Best API** - GraphQL + REST enables full automation
2. **MCP Integration** - Claude can directly interact with CRM data
3. **Same Stack** - PostgreSQL, Node.js matches our infrastructure
4. **Most Active** - 39K stars, 575 contributors, updated today
5. **Customizable** - Can build lead gen, proposals, research on top

---

## What We Need to Build on Top

Twenty provides core CRM. We'll build these extensions:

### 1. Lead Generation Module
```
Web forms → Twenty API → Lead created
LinkedIn scraping → Twenty API → Lead created
Email parsing → Twenty API → Lead created
```

### 2. AI Research Agent (Claude Integration)
```
New lead detected → Claude researches company
→ Enriches contact with findings
→ Scores lead
→ Suggests approach
```

### 3. Proposal Builder
```
Deal reaches "Proposal" stage
→ Claude generates proposal from template
→ Sends for review
→ Tracks opens/engagement
```

### 4. Automated Office Functions
```
Scheduling → Calendar integration
Follow-ups → Automated email sequences
Reminders → Telegram notifications
Reporting → Daily/weekly digests
```

### 5. Deal Closing Workflow
```
Verbal agreement → Generate contract
Contract signed → Create invoice
Payment received → Onboard client
```

---

## Implementation Plan

### Phase 1: Deploy Twenty (Week 1)
- [ ] Docker compose setup
- [ ] PostgreSQL integration
- [ ] Initial configuration
- [ ] Import existing contacts

### Phase 2: API Integration (Week 2)
- [ ] Connect Twenty MCP server to Claude
- [ ] Build lead capture webhooks
- [ ] Connect to Atlas websites

### Phase 3: AI Automation (Week 3-4)
- [ ] Lead research automation
- [ ] Lead scoring model
- [ ] Proposal generation
- [ ] Email sequences

### Phase 4: Company Integration (Week 5-6)
- [ ] Atlas Analytics pipeline
- [ ] Atlas Consulting pipeline
- [ ] Atlas Content pipeline
- [ ] Algiers Bay pipeline

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     TWENTY CRM                               │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ Leads   │  │Contacts │  │ Deals   │  │Companies│        │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘        │
│       └────────────┴────────────┴────────────┘              │
│                         │ GraphQL API                        │
└─────────────────────────┼───────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────┐
│                   MCP SERVER                                 │
│           (Twenty ↔ Claude Bridge)                          │
└─────────────────────────┼───────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────┐
│                  CLAUDE COGNITIVE                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │Lead Research│  │Proposal Gen │  │Deal Scoring │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────┐
│               ATLAS COMPANIES                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │Analytics │ │Consulting│ │ Content  │ │Algiers   │       │
│  │ Pipeline │ │ Pipeline │ │ Pipeline │ │Pipeline  │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
```

---

## Sources

- [Twenty CRM GitHub](https://github.com/twentyhq/twenty)
- [Top 20 Open-Source CRMs 2026](https://growcrm.io/2026/01/04/top-20-open-source-self-hosted-crms-in-2025/)
- [Open Source CRM Benchmark 2025](https://marmelab.com/blog/2025/02/03/open-source-crm-benchmark-for-2025.html)
- [Twenty vs Frappe Comparison](https://openalternative.co/compare/frappe-crm/vs/twenty)
- [Top Open Source AI CRM Tools](https://superagi.com/top-10-open-source-ai-crm-tools-for-2025-features-benefits-and-user-reviews/)

---

*Decision: Twenty CRM with Claude automation layer*
*Generated: 2026-01-24*
