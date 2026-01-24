# Career Manager Function - Specification

*AI-Powered Career Orchestration*

---

## Vision

An autonomous career management system that:
- Tracks opportunities across all domains
- Optimizes for short-term cash + long-term wealth
- Maintains professional relationships
- Identifies and acts on career inflection points

---

## Core Functions

### 1. Opportunity Radar

```python
# daemon/career_manager.py
class OpportunityRadar:
    """Continuously scan for career opportunities."""

    sources = [
        "linkedin_jobs",      # Job postings in domain
        "linkedin_posts",     # Network activity
        "twitter_mentions",   # Industry conversations
        "email_inbox",        # Inbound opportunities
        "news_feeds",         # Industry developments
        "conference_calendars", # Speaking opportunities
    ]

    def scan(self):
        """Daily scan for opportunities."""
        opportunities = []
        for source in self.sources:
            raw = fetch(source)
            filtered = self.filter_relevant(raw)
            scored = self.score_opportunities(filtered)
            opportunities.extend(scored)
        return sorted(opportunities, key=lambda x: x.score)

    def score_opportunities(self, items):
        """Score by: revenue potential, strategic fit, effort required."""
        for item in items:
            item.score = (
                item.revenue_potential * 0.4 +
                item.strategic_fit * 0.3 +
                (1 - item.effort_required) * 0.2 +
                item.time_sensitivity * 0.1
            )
        return items
```

### 2. Relationship Manager

```python
class RelationshipManager:
    """Track and nurture professional relationships."""

    def __init__(self):
        self.contacts = ContactDB()
        self.interactions = InteractionLog()

    def get_neglected_contacts(self, days=90):
        """Find high-value contacts not contacted recently."""
        return self.contacts.query(
            "SELECT * FROM contacts "
            "WHERE value_score > 7 "
            "AND last_contact < date('now', '-? days')",
            days
        )

    def suggest_touchpoints(self, contact):
        """Suggest personalized outreach."""
        context = self.get_context(contact)
        return generate_touchpoint(
            contact=contact,
            context=context,
            style="warm",
            goal="maintain_relationship"
        )

    def track_interaction(self, contact_id, type, notes):
        """Log interaction for future reference."""
        self.interactions.add(
            contact_id=contact_id,
            type=type,  # email, call, meeting, social
            notes=notes,
            timestamp=now()
        )
```

### 3. Revenue Optimizer

```python
class RevenueOptimizer:
    """Optimize across revenue streams."""

    streams = {
        "consulting": {"capacity": 40, "rate": 200},  # hours/month, $/hour
        "ghostwriting": {"capacity": 4, "rate": 5000},  # pieces/month
        "speaking": {"capacity": 4, "rate": 5000},  # events/month
        "content": {"capacity": "unlimited", "rate": "variable"},
        "passive": {"capacity": "unlimited", "rate": "variable"},
    }

    def optimize_allocation(self, goals):
        """Find optimal time allocation across streams."""
        # Linear programming to maximize revenue
        # Subject to: time constraints, energy constraints, strategic goals
        pass

    def forecast_revenue(self, horizon_months=12):
        """Project revenue based on current trajectory."""
        pass

    def identify_bottlenecks(self):
        """Find constraints limiting revenue growth."""
        pass
```

### 4. Skill Development Tracker

```python
class SkillTracker:
    """Track and optimize skill development."""

    def assess_skills(self):
        """Map current skills vs. market demand."""
        current = self.get_current_skills()
        demanded = self.get_market_demand()
        gaps = self.identify_gaps(current, demanded)
        return {
            "current": current,
            "demanded": demanded,
            "gaps": gaps,
            "recommendations": self.recommend_learning(gaps)
        }

    def track_learning(self, skill, activity, duration):
        """Log learning activities."""
        pass

    def validate_skill(self, skill, evidence):
        """Record proof of skill (project, certification, etc.)."""
        pass
```

### 5. Strategic Positioning

```python
class StrategicPositioner:
    """Optimize market positioning."""

    def analyze_positioning(self):
        """Current position in professional landscape."""
        return {
            "unique_value": self.identify_unique_value(),
            "competitors": self.map_competitors(),
            "market_gaps": self.find_market_gaps(),
            "positioning_options": self.generate_positioning_options()
        }

    def track_reputation(self):
        """Monitor online reputation and brand."""
        return {
            "mentions": self.get_mentions(),
            "sentiment": self.analyze_sentiment(),
            "reach": self.measure_reach(),
            "authority_score": self.calculate_authority()
        }
```

---

## Data Model

```sql
-- Core tables
CREATE TABLE contacts (
    id INTEGER PRIMARY KEY,
    name TEXT,
    company TEXT,
    role TEXT,
    email TEXT,
    linkedin_url TEXT,
    value_score INTEGER,  -- 1-10
    relationship_strength INTEGER,  -- 1-10
    last_contact DATE,
    tags TEXT,  -- JSON array
    notes TEXT
);

CREATE TABLE opportunities (
    id INTEGER PRIMARY KEY,
    type TEXT,  -- job, speaking, consulting, collaboration
    source TEXT,
    title TEXT,
    description TEXT,
    revenue_potential INTEGER,
    effort_required INTEGER,
    deadline DATE,
    status TEXT,  -- new, evaluating, pursuing, won, lost, passed
    score REAL
);

CREATE TABLE revenue_events (
    id INTEGER PRIMARY KEY,
    stream TEXT,
    amount REAL,
    date DATE,
    client TEXT,
    notes TEXT
);

CREATE TABLE skills (
    id INTEGER PRIMARY KEY,
    skill TEXT,
    level INTEGER,  -- 1-10
    evidence TEXT,  -- JSON array of proofs
    last_used DATE
);

CREATE TABLE goals (
    id INTEGER PRIMARY KEY,
    type TEXT,  -- revenue, skill, network, positioning
    target TEXT,
    deadline DATE,
    progress REAL,
    status TEXT
);
```

---

## Automation Flows

### Daily (6 AM)
1. Scan opportunity sources
2. Check neglected contacts
3. Review day's commitments
4. Generate daily brief → Telegram

### Weekly (Sunday)
1. Revenue tracking update
2. Relationship health check
3. Opportunity pipeline review
4. Strategic positioning check
5. Generate weekly report

### Monthly
1. Full skill assessment
2. Revenue optimization
3. Goal progress review
4. Network analysis
5. Strategic recommendations

---

## Integration Points

| System | Integration | Purpose |
|--------|-------------|---------|
| LinkedIn | API/Scraping | Opportunities, network |
| Email | IMAP/API | Inbound opportunities |
| Calendar | Google/Outlook | Availability, commitments |
| CRM | Custom DB | Contact management |
| Banking | Plaid/API | Revenue tracking |
| Telegram | Bot API | Notifications, commands |
| Claude | API | Analysis, generation |

---

## Commands (Telegram)

```
/career status     - Overall career dashboard
/career opps       - Top opportunities
/career contacts   - Who to reach out to
/career revenue    - Revenue tracking
/career skills     - Skill gaps
/career goals      - Goal progress
/career suggest    - What should I do today?
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- Contact database with import
- Opportunity tracker
- Basic daily brief

### Phase 2: Intelligence (Week 3-4)
- LinkedIn scanning
- Opportunity scoring
- Relationship suggestions

### Phase 3: Optimization (Week 5-6)
- Revenue optimization
- Skill tracking
- Goal setting

### Phase 4: Automation (Week 7-8)
- Automated scanning
- Proactive notifications
- Full Telegram integration

---

## Success Metrics

| Metric | Baseline | Target (6 mo) |
|--------|----------|---------------|
| Monthly revenue | ? | +50% |
| Active relationships | ? | 50+ touchpoints/mo |
| Opportunities captured | ? | 80% response rate |
| Skill gaps closed | ? | 3 new skills |
| Network growth | ? | +20% valuable contacts |

---

*To implement: Create `daemon/career_manager.py` with core functions.*
*Generated: 2026-01-24*
