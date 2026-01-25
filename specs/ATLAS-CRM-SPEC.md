# Atlas CRM System Specification

*Twenty CRM + Claude Automation for Atlas Companies*

---

## Overview

A unified CRM system powering all Atlas companies with AI-driven automation for lead generation, client research, proposal building, and deal management.

---

## Core Components

### 1. Twenty CRM (Base Platform)
- Contact & company management
- Deal pipelines
- Activity tracking
- Email integration
- GraphQL/REST API

### 2. Claude Integration Layer
- Lead research automation
- Proposal generation
- Deal scoring
- Automated follow-ups

### 3. Atlas Extensions
- Multi-company pipelines
- Industry-specific workflows
- Revenue tracking
- Performance dashboards

---

## Feature Specifications

### Feature 1: Lead Generation

#### 1.1 Web Form Capture
```yaml
Sources:
  - Atlas Analytics website contact form
  - Atlas Consulting inquiry form
  - Algiers Bay product inquiry
  - Atlas Content subscription form
  - Atlas Publishing submission form

Flow:
  1. Form submitted on website
  2. Webhook sends to daemon/crm_ingest.py
  3. Create lead in Twenty via GraphQL
  4. Assign to appropriate company pipeline
  5. Trigger lead research automation
```

#### 1.2 Email Capture
```yaml
Sources:
  - adam.a.bensaid@gmail.com
  - info@atlasanalytics.com
  - hello@atlasconsulting.ca

Flow:
  1. Email received with new contact
  2. daemon/email_trigger.py parses
  3. Extract contact info (name, company, domain)
  4. Create/update lead in Twenty
  5. Log email as activity
```

#### 1.3 LinkedIn Capture
```yaml
Sources:
  - Connection requests
  - InMail messages
  - Post engagement

Flow:
  1. Manual import or browser extension
  2. Parse LinkedIn profile URL
  3. Scrape public info (Phantombuster/Clay)
  4. Create lead with enriched data
```

#### 1.4 Referral Tracking
```yaml
Flow:
  1. Referrer submits introduction
  2. Create lead with referrer tag
  3. Track referral source
  4. Calculate referral value over time
```

---

### Feature 2: Automated Research (AI Employee)

#### 2.1 Company Research
```python
# daemon/crm_research.py
class LeadResearcher:
    """AI employee for lead research."""

    def research_company(self, domain: str) -> dict:
        """Research company when lead created."""
        return {
            "company_size": self.estimate_size(domain),
            "industry": self.classify_industry(domain),
            "tech_stack": self.detect_tech(domain),
            "recent_news": self.find_news(domain),
            "social_presence": self.analyze_social(domain),
            "decision_makers": self.find_contacts(domain),
            "pain_points": self.infer_needs(domain),
            "fit_score": self.calculate_fit(domain)
        }

    def estimate_size(self, domain):
        # LinkedIn company size, employee count
        pass

    def classify_industry(self, domain):
        # Analyze website, categorize
        pass

    def detect_tech(self, domain):
        # BuiltWith, Wappalyzer data
        pass

    def find_news(self, domain):
        # Recent press releases, news mentions
        pass

    def analyze_social(self, domain):
        # Twitter, LinkedIn activity
        pass

    def find_contacts(self, domain):
        # Apollo, Hunter.io, LinkedIn
        pass

    def infer_needs(self, domain):
        # Based on industry + size + tech
        pass

    def calculate_fit(self, domain):
        # Score 1-100 based on ICP
        pass
```

#### 2.2 Contact Research
```python
def research_contact(self, email: str, linkedin_url: str) -> dict:
    """Deep research on individual contact."""
    return {
        "full_name": str,
        "current_role": str,
        "company": str,
        "seniority": str,  # C-level, VP, Director, Manager, IC
        "department": str,  # Sales, Marketing, Ops, Tech, Finance
        "tenure": int,  # months
        "previous_roles": list,
        "education": list,
        "publications": list,
        "social_activity": dict,
        "mutual_connections": list,
        "communication_style": str,  # formal, casual, technical
        "best_approach": str  # suggested outreach strategy
    }
```

#### 2.3 Research Triggers
```yaml
Triggers:
  - New lead created → Full research
  - Deal stage changed → Update research
  - Weekly refresh → Stale leads
  - Manual request → On-demand

Output:
  - Research summary in Twenty notes
  - Fit score updated
  - Suggested next action
  - Telegram notification
```

---

### Feature 3: Proposal Building

#### 3.1 Proposal Templates

```yaml
Templates by Company:

Atlas Analytics:
  - Intelligence Retainer Proposal
  - Custom Research Proposal
  - Advisory Services Proposal

Atlas Consulting:
  - Strategy Consulting Proposal
  - AI Automation Proposal
  - Growth Advisory Proposal

Atlas Content:
  - Content Partnership Proposal
  - Sponsored Content Proposal
  - White-Label Content Proposal

Atlas Media Production:
  - Documentary Pitch Deck
  - Branded Content Proposal
  - Production Services Proposal

Algiers Bay:
  - Wholesale Pricing Sheet
  - Distribution Agreement
  - Custom Sourcing Proposal

Atlas Publishing:
  - Author Agreement
  - Co-Publishing Proposal
  - Licensing Agreement
```

#### 3.2 Proposal Generation Flow

```python
# daemon/proposal_generator.py
class ProposalGenerator:
    """AI-powered proposal generation."""

    def generate_proposal(self, deal_id: str) -> str:
        # 1. Get deal context from Twenty
        deal = twenty_api.get_deal(deal_id)
        company = twenty_api.get_company(deal.company_id)
        contact = twenty_api.get_contact(deal.contact_id)
        research = self.get_research(company.domain)

        # 2. Select template based on company + deal type
        template = self.select_template(
            atlas_company=deal.pipeline,
            deal_type=deal.type,
            deal_size=deal.amount
        )

        # 3. Generate proposal with Claude
        proposal = claude.generate(
            template=template,
            context={
                "client_name": company.name,
                "contact_name": contact.name,
                "pain_points": research.pain_points,
                "proposed_solution": deal.description,
                "pricing": self.calculate_pricing(deal),
                "timeline": self.estimate_timeline(deal),
                "case_studies": self.relevant_cases(company.industry)
            }
        )

        # 4. Save to Twenty + Google Docs
        doc_url = google_docs.create(proposal)
        twenty_api.add_note(deal_id, f"Proposal: {doc_url}")

        return doc_url

    def calculate_pricing(self, deal):
        """Dynamic pricing based on scope."""
        pass

    def estimate_timeline(self, deal):
        """Project timeline estimation."""
        pass

    def relevant_cases(self, industry):
        """Find matching case studies."""
        pass
```

#### 3.3 Proposal Tracking

```yaml
Tracking:
  - Document opens (via tracking pixel)
  - Time spent viewing
  - Sections viewed
  - Forwarded to others
  - Comments/questions

Actions:
  - Open detected → Notify via Telegram
  - Long view time → Schedule follow-up
  - Forwarded → Research new contacts
  - No open after 3 days → Send reminder
```

---

### Feature 4: Deal Management

#### 4.1 Pipeline Stages

```yaml
Standard Pipeline:
  1. Lead (New)
     - Auto-created from sources
     - Research triggered

  2. Qualified
     - Research complete
     - Fit score > 60
     - Initial contact made

  3. Discovery
     - Meeting scheduled
     - Needs understood
     - Budget confirmed

  4. Proposal
     - Proposal generated
     - Sent to client
     - Tracking active

  5. Negotiation
     - Feedback received
     - Terms discussed
     - Revisions made

  6. Closed Won
     - Agreement signed
     - Invoice sent
     - Onboarding triggered

  7. Closed Lost
     - Reason captured
     - Follow-up scheduled
     - Learnings recorded
```

#### 4.2 Deal Scoring

```python
def score_deal(deal: Deal) -> int:
    """Calculate deal score 0-100."""
    score = 0

    # Fit score (from research)
    score += deal.company.fit_score * 0.3

    # Engagement score
    score += calculate_engagement(deal) * 0.25

    # Budget match
    score += budget_match_score(deal) * 0.2

    # Timeline alignment
    score += timeline_score(deal) * 0.15

    # Champion strength
    score += champion_score(deal.contact) * 0.1

    return min(100, score)
```

#### 4.3 Automated Actions by Stage

```yaml
Stage Actions:

Lead:
  - Research company + contact
  - Calculate fit score
  - Suggest outreach template
  - Schedule follow-up task

Qualified:
  - Send intro email (template)
  - Add to nurture sequence
  - Set reminder for follow-up

Discovery:
  - Prepare meeting agenda
  - Research recent news
  - Generate questions list
  - Send calendar invite

Proposal:
  - Generate proposal
  - Send with tracking
  - Schedule follow-up
  - Alert on document open

Negotiation:
  - Track revision requests
  - Generate updated proposal
  - Prepare contract draft

Closed Won:
  - Generate contract
  - Create invoice
  - Trigger onboarding
  - Update revenue forecast
  - Notify team (Telegram)

Closed Lost:
  - Capture loss reason
  - Schedule 6-month follow-up
  - Add to win-back campaign
  - Record learnings
```

---

### Feature 5: Automated Office Functions

#### 5.1 Email Automation

```yaml
Sequences:

New Lead Nurture (7 emails over 30 days):
  Day 0: Welcome + value intro
  Day 3: Case study
  Day 7: Industry insight
  Day 14: Offer consultation
  Day 21: Social proof
  Day 28: Final push
  Day 30: Long-term nurture

Re-engagement (5 emails over 14 days):
  Day 0: "Checking in"
  Day 3: New relevant content
  Day 7: Limited offer
  Day 10: Different angle
  Day 14: Break-up email

Post-Meeting (3 emails over 7 days):
  Day 0: Thank you + summary
  Day 3: Additional resources
  Day 7: Next steps reminder
```

#### 5.2 Task Automation

```yaml
Auto-generated Tasks:

Daily:
  - Follow up on proposals > 3 days old
  - Research new leads
  - Review stale deals (no activity > 7 days)

Weekly:
  - Pipeline review
  - Win/loss analysis
  - Forecast update

Monthly:
  - Inactive contact outreach
  - Referral requests
  - Case study collection
```

#### 5.3 Notifications

```yaml
Telegram Notifications:

Immediate:
  - New lead from website
  - Proposal opened
  - Deal closed (won or lost)
  - High-value activity

Daily Digest:
  - Pipeline summary
  - Tasks due today
  - Deals at risk
  - Revenue forecast

Weekly Report:
  - Won/lost breakdown
  - Pipeline health
  - Activity metrics
  - Top opportunities
```

---

### Feature 6: Multi-Company Support

#### 6.1 Pipeline per Company

```yaml
Pipelines:

Atlas Analytics:
  - Target: Intelligence buyers
  - Deal size: $2.5K-25K/month
  - Cycle: 2-6 weeks

Atlas Consulting:
  - Target: Growth-stage companies
  - Deal size: $5K-50K/project
  - Cycle: 2-4 weeks

Atlas Content:
  - Target: Media buyers, brands
  - Deal size: $500-10K/campaign
  - Cycle: 1-3 weeks

Atlas Media Production:
  - Target: Broadcasters, brands
  - Deal size: $50K-500K/project
  - Cycle: 1-6 months

Algiers Bay:
  - Target: Retailers, distributors
  - Deal size: $5K-100K/order
  - Cycle: 2-8 weeks

Atlas Publishing:
  - Target: Authors, co-publishers
  - Deal size: $5K-50K/book
  - Cycle: 1-3 months
```

#### 6.2 Unified Dashboard

```yaml
Dashboard Views:

Executive:
  - Total pipeline value
  - Revenue this month
  - Win rate trend
  - Top opportunities

By Company:
  - Company-specific pipeline
  - Revenue attribution
  - Activity metrics

By Contact:
  - Full history across companies
  - Cross-sell opportunities
  - Lifetime value
```

---

## Technical Architecture

### Docker Compose Addition

```yaml
# Add to docker-compose.yaml
  twenty:
    image: twentycrm/twenty:latest
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgres://claude:claude_dev@postgres:5432/twenty
      - REDIS_URL=redis://dragonfly:6379
      - SECRET_KEY=${TWENTY_SECRET_KEY}
    depends_on:
      - postgres
      - dragonfly
    volumes:
      - twenty_data:/app/data

  twenty-worker:
    image: twentycrm/twenty:latest
    command: ["yarn", "worker:prod"]
    environment:
      - DATABASE_URL=postgres://claude:claude_dev@postgres:5432/twenty
      - REDIS_URL=redis://dragonfly:6379
    depends_on:
      - twenty
      - postgres
      - dragonfly

volumes:
  twenty_data:
```

### MCP Server Configuration

```json
// Add to .mcp.json
{
  "mcpServers": {
    "twenty": {
      "command": "npx",
      "args": ["-y", "@twentyhq/mcp-server"],
      "env": {
        "TWENTY_API_URL": "http://localhost:3000",
        "TWENTY_API_KEY": "${TWENTY_API_KEY}"
      }
    }
  }
}
```

### Integration Files

```
daemon/
├── crm/
│   ├── __init__.py
│   ├── twenty_client.py      # GraphQL client
│   ├── lead_generator.py     # Lead capture
│   ├── lead_researcher.py    # AI research
│   ├── proposal_generator.py # Proposal builder
│   ├── deal_manager.py       # Pipeline automation
│   ├── email_sequences.py    # Automated emails
│   ├── notifications.py      # Telegram alerts
│   └── dashboard.py          # Analytics
```

---

## Implementation Roadmap

### Week 1: Foundation
- [ ] Deploy Twenty CRM via Docker
- [ ] Configure PostgreSQL database
- [ ] Set up MCP server
- [ ] Create initial pipelines

### Week 2: Lead Generation
- [ ] Build web form integration
- [ ] Configure email capture
- [ ] Set up LinkedIn import
- [ ] Test lead creation flow

### Week 3: AI Automation
- [ ] Build lead researcher
- [ ] Implement scoring model
- [ ] Create proposal templates
- [ ] Test Claude integration

### Week 4: Deal Management
- [ ] Configure stage automations
- [ ] Build email sequences
- [ ] Set up notifications
- [ ] Test full workflow

### Week 5: Multi-Company
- [ ] Create company pipelines
- [ ] Build unified dashboard
- [ ] Configure cross-sell logic
- [ ] Test multi-tenant flow

### Week 6: Polish
- [ ] Performance optimization
- [ ] Documentation
- [ ] Training materials
- [ ] Go-live

---

## Success Metrics

| Metric | Baseline | Target (3mo) | Target (6mo) |
|--------|----------|--------------|--------------|
| Leads/month | Manual | 50 | 200 |
| Research time | 30 min | 5 min | 1 min |
| Proposal time | 2 hours | 15 min | 5 min |
| Win rate | Unknown | 25% | 35% |
| Pipeline value | $0 | $100K | $500K |
| Response time | Days | Hours | Minutes |

---

*System designed for maximum automation with minimal human intervention.*
*Generated: 2026-01-24*
