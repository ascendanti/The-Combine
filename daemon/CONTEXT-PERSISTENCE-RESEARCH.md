# Context Persistence Research

Reference repos for improving context management, memory, and proactive capabilities.

## Compaction/Handoff Fixes

| Repo | Purpose | URL |
|------|---------|-----|
| **claude-compaction-fix** | Fix for Claude autocompact context persistence | https://github.com/ajjucoder/claude-compaction-fix |
| **handoff-plugin** | Handoff management between sessions | https://github.com/winstonwxi/handoff-plugin |
| **mindcontext-core** | Core context management | https://github.com/tmsjngx0/mindcontext-core |
| **continue-witty** | Continue session across compaction | https://github.com/freyjay/continue-witty |

## Scheduling & Proactive Agents

| Repo | Purpose | URL |
|------|---------|-----|
| **ProActive Scheduling** | Multi-platform Scheduling and Workflows Engine | https://github.com/ow2-proactive/scheduling |
| **ProactiveAgent** | Transform AI from reactive to proactive with intelligent timing and context-aware wake-up patterns | https://github.com/leomariga/ProactiveAgent |

## Memory & Organization

| Repo | Purpose | URL |
|------|---------|-----|
| **memU** | Memory for 24/7 proactive agents (moltbot/clawdbot) | https://github.com/NevaMind-AI/memU |
| **ai-file-organizer** | Intelligent file organization with CV, audio analysis, proactive AI-powered analysis, adaptive learning | https://github.com/thebearwithabite/ai-file-organizer |

## Relevance to Atlas

### Context Persistence
- Current gap: Session context is lost on compaction despite `pre-compact-handoff.py`
- Research: claude-compaction-fix, handoff-plugin, mindcontext-core, continue-witty

### Proactive Capabilities
- Current gap: Claude is reactive, waits for prompts
- Research: ProactiveAgent (wake-up patterns), ProActive Scheduling (workflow engine)

### Memory Management
- Current: memory_router.py + Dragonfly cache + SQLite
- Research: memU (24/7 agent memory patterns)

### Adaptive Learning
- Current: emergent.py + feedback_loop.py
- Research: ai-file-organizer (adaptive learning patterns)

## Integration Ideas

1. **Wake-up Patterns (ProactiveAgent)**
   - Schedule Claude to "wake up" and check for pending tasks
   - Context-aware triggers based on time/events
   - Could wire into continuous_executor.py

2. **Workflow Engine (ProActive Scheduling)**
   - Enterprise-grade job scheduling
   - Could replace/enhance task_queue.py
   - Multi-step workflow orchestration

3. **24/7 Memory (memU)**
   - Persistent memory across sessions
   - Could enhance memory_router.py
   - Better cross-session continuity

4. **Adaptive Classification (ai-file-organizer)**
   - Learn from user corrections
   - Could enhance autonomous_ingest.py
   - Smart routing based on file type

---
*Created: 2026-01-27*
*Status: Research phase - pending implementation*
