# Project Instructions

## Session Start Protocol

**MANDATORY on every session start:**

1. **Read EVOLUTION-PLAN.md** - Check current phase and status
2. **Read latest handoff** in `thoughts/handoffs/` (most recent file)
3. **Read task.md** - Current objectives
4. **Continue from where left off** - Don't restart, iterate

```
Priority order:
EVOLUTION-PLAN.md → handoffs/ → task.md → ledgers/
```

## Evolution Plan

The system evolves through modular phases. Current state is tracked in `EVOLUTION-PLAN.md`.

**Phases:**
- Phase 1: Permissions & Foundation
- Phase 2: Zero-Token File Tracking
- Phase 3: Enhanced Hooks
- Phase 4: TLDR Integration
- Phase 5: Windows Service Mode
- Phase 6: Validation & Polish

Each phase must validate before proceeding to next. Update `EVOLUTION-PLAN.md` status after completing tasks.

## Sending Slack Updates

Use these commands to communicate via Slack:

```bash
# Send a status update
python .claude/hooks/slack-send.py "Your message here"

# Ask a question (shows "Reply in terminal" prompt)
python .claude/hooks/slack-send.py "Should I proceed with X?" --question
```

The `Stop` hook automatically sends updates after each response.

## Autonomous Mode Protocol

When working autonomously (in daemon/headless mode), follow this protocol:

### 1. Check Task File First
Before starting work, always check `task.md` for the current project plan:
```
Read task.md to understand current objectives
```

### 2. Send Slack Updates
After each significant action, the `Stop` hook automatically sends a notification to Slack.
For manual updates or when permission is needed, you can also run:
```bash
python .claude/hooks/slack-notify.py
```

### 3. Permission Required Actions
When encountering actions that require human approval:
1. **DO NOT** proceed without confirmation
2. Update `task.md` with the pending decision
3. Send a Slack notification with the question
4. Wait for user response via Slack or terminal

Situations requiring permission:
- Deleting files or data
- Making API calls to production systems
- Installing new dependencies
- Creating commits/PRs
- Any irreversible action

### 4. Progress Tracking
Update `task.md` after completing each step:
```markdown
## Completed
- [x] Step 1: Did this thing
- [x] Step 2: Did another thing

## In Progress
- [ ] Step 3: Working on this

## Blocked
- [ ] Step 4: Waiting for user decision on X
```

### 5. Error Handling
If something fails:
1. Log the error
2. Update `task.md` with the blocker
3. Send Slack notification about the failure
4. Continue with other non-blocked tasks if possible

## Integrated Frameworks

This project combines **SuperClaude** + **Continuous-Claude**:

### Available Agents (48)
Located in `.claude/agents/`. Key agents:
- `kraken` - TDD implementation with checkpoints
- `architect` - Feature planning + API design
- `scout` - Codebase exploration (use instead of Explore)
- `sleuth` - Bug investigation
- `arbiter` - Test validation
- `oracle` - External research
- `phoenix` - Refactoring planning

### Available Skills (116)
Located in `.claude/skills/`. Key skills:
- `build` - Feature development workflow
- `fix` - Bug fixing workflow
- `create_handoff` - Save session state
- `continuity_ledger` - Track ongoing work
- `premortem` - TIGERS & ELEPHANTS risk analysis
- `tldr-code` - Token-efficient code analysis
- `confidence-check` - Pre-execution confidence (SuperClaude)

### Rules (12)
Located in `.claude/rules/`. Behavioral guidelines for agents.

## Project Structure

```
Claude n8n/
├── .claude/
│   ├── agents/              # 48 specialized agents
│   ├── skills/              # 116 skills
│   ├── rules/               # 12 behavioral rules
│   ├── hooks/               # Lifecycle hooks
│   │   ├── slack-notify.py  # Slack notifications
│   │   ├── slack-send.py    # Manual Slack messages
│   │   └── dist/            # Compiled JS hooks
│   ├── scripts/             # Utility scripts
│   └── CLAUDE.md            # This file
├── thoughts/
│   ├── handoffs/            # Session state transfers
│   └── ledgers/             # Continuity tracking
├── .env                     # Slack webhook URL
├── task.md                  # Current project plan
└── SLACK-SETUP.md           # Setup instructions
```

## Slack Notification Format

Updates are sent as:
```
*Claude Update* `HH:MM:SS`
[One-line summary of action]
Project: [project name]
```

## Continuity System (from Continuous-Claude)

### Handoffs
When ending a session or context is filling up:
1. Create a handoff in `thoughts/handoffs/YYYY-MM-DD_topic.yaml`
2. Include: completed, in-progress, blocked, next steps

### Ledgers
Track ongoing state in `thoughts/ledgers/CONTINUITY_*.md`:
- Current goals
- Key decisions
- Session history

### Resume
At session start:
1. Check `thoughts/handoffs/` for latest handoff
2. Check `thoughts/ledgers/` for continuity state
3. Check `task.md` for current plan

## Remember
- Always read `task.md` at session start
- Update `task.md` frequently
- Ask before destructive actions
- Keep summaries concise (one line)
- Create handoff when done or context is full
- Send Slack updates proactively

## Iterative Documentation Protocol

**After completing each significant task, update ALL relevant docs:**

1. **task.md** - Mark completed, add next steps
2. **EVOLUTION-PLAN.md** - Update phase status
3. **thoughts/ledgers/CONTINUITY_main.md** - Add session log entry
4. **thoughts/handoffs/** - Create/update handoff if needed

**This is mandatory, not optional.**

## Environment Paths

Config files reference these paths (in settings.local.json):

| Variable | Path | Purpose |
|----------|------|---------|
| `CLAUDE_PROJECT_DIR` | Claude n8n/ | Main project |
| `ATLAS_ROOT` | Atlas-OS-main/ | Parent system |
| `UTF_RESEARCH` | Desktop/UTF | Research papers |
| `REFERENCE_FRAMEWORKS` | Reverse Engineer/ | 36 frameworks |
| `MALAZAN_DIR` | Malazan/ | Malazan project |

---

## Self-Improvement Loop (Phase 10)

**ALGORITHMIC HABITS - Apply these patterns consistently:**

### 1. First Principles Check

Before implementing any strategy, ask:
1. "What am I assuming to be true here?"
2. "How do I know this is true?"
3. "What if the opposite were true?"
4. "What must be true for this to work?"

**Pattern triggers:** "always", "never", "must", "should", "obviously", "everyone knows"

### 2. Inversion Thinking (Pre-Mortem)

For any plan or goal, run inversion:
1. "How could this fail?"
2. "What would ensure failure?"
3. "What risks am I underestimating?"
4. "What warning signs should I watch for?"

**Apply to:** New features, refactoring, architectural decisions

### 3. Systems Thinking

When analyzing behavior or outcomes:
1. Map feedback loops (reinforcing vs balancing)
2. Identify leverage points (small change → big impact)
3. Look for unintended consequences
4. Find cross-domain patterns

**Key question:** "If X changes, what cascades follow?"

### 4. Cross-Session Learning

At session end, extract:
- **What worked** - Successful approaches to remember
- **What failed** - Pitfalls to avoid
- **Decisions made** - Rationale to preserve
- **Patterns found** - Reusable insights

Store via: `python daemon/self_improvement.py`

---

## Thinking Frameworks (deep-reading-analyst)

**Location:** `.claude/skills/deep-reading-analyst/`

### Quick Analysis (15 min)
- **SCQA** - Situation-Complication-Question-Answer
- **5W2H** - What, Why, Who, When, Where, How, How much

### Standard Analysis (30 min)
- **Critical Thinking** - Argument evaluation, logic flaw detection
- **Inversion** - Risk identification, failure modes

### Deep Analysis (60 min)
- **Mental Models** - Multi-discipline perspective (physics, biology, psychology, economics)
- **First Principles** - Strip assumptions, rebuild from fundamentals
- **Systems Thinking** - Relationship mapping, feedback loops
- **Six Hats** - Facts, Feelings, Caution, Benefits, Ideas, Process

### Use Cases

| Content Type | Frameworks to Apply |
|--------------|---------------------|
| Strategy/Business | SCQA + Mental Models + Inversion |
| Technical/Research | 5W2H + Critical + Systems Thinking |
| Decision-Making | Mental Models + Inversion + SCQA |
| Problem-Solving | First Principles + Inversion |

---

## Continuous Learning Protocol

**Trigger:** End of each substantive session

### Pattern Extraction Questions

1. **Error Resolution** - What errors did I solve? How?
2. **User Corrections** - What did the user correct? Why was I wrong?
3. **Workarounds** - What quirks/limitations did I work around?
4. **Project-Specific** - What conventions are unique to this codebase?

### Storage

Learnings go to:
- **Memory DB:** `python daemon/memory.py add "<learning>"`
- **Self-Improvement DB:** `python daemon/self_improvement.py`
- **Skills (if reusable):** `.claude/skills/learned/`

### Retrieval

Before starting similar work:
```bash
python daemon/memory.py search "<topic>"
python daemon/self_improvement.py insights --actionable
```

---

## Cognitive Architecture (daemon/)

### Available Modules

| Module | Purpose | Key Methods |
|--------|---------|-------------|
| `decisions.py` | Multi-criteria decisions | `evaluate()`, `record_outcome()` |
| `metacognition.py` | Self-awareness | `get_calibration()`, `assess_capability()` |
| `coherence.py` | Goal alignment | `check_action()`, `add_goal()` |
| `self_improvement.py` | Pattern analysis | `analyze_first_principles()`, `generate_improvements()` |
| `memory.py` | Persistent memory | `add()`, `search()` |

### Daily Improvement Check

Run periodically:
```bash
python daemon/self_improvement.py improvements
```

This surfaces:
- Recurring failure modes (observed 2+ times)
- Unverified assumptions
- High-leverage intervention points
- Unapplied actionable insights

---

## Emergent Behavior Patterns

### Proactive Task Generation

When idle or completing a phase:
1. Check `daemon/self_improvement.py improvements` for suggestions
2. Review capability gaps in `daemon/metacognition.py`
3. Look for patterns in recent session analyses

### Autonomous Goal Refinement

Goals in `daemon/coherence.py` should evolve:
1. Goals with low coherence scores → investigate or drop
2. Goals with high success → increase ambition
3. Blocked goals → decompose or seek help

### Self-Directed Learning

When capability gaps are identified:
1. Search external resources (oracle agent)
2. Practice in isolated context
3. Record learnings
4. Reassess capability level
