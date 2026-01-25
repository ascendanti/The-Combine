# Operations Runbook

*Commands, debugging, and operational procedures*

---

## Quick Commands

### Memory & Learning

```bash
# Search memory
python daemon/memory.py search "<topic>"

# Add learning
python daemon/memory.py add "<learning>"

# Self-improvement insights
python daemon/self_improvement.py improvements
```

### Model Router

```bash
# Check router stats
python daemon/model_router.py --stats

# Test routing
python daemon/model_router.py --test "simple query"

# Force tier
python daemon/model_router.py --force-tier 3 "complex query"
```

### Task Queue

```bash
# Queue status
python daemon/runner.py status

# Add task
python daemon/submit.py "<task description>"

# Process next
python daemon/runner.py --once
```

### Google Drive

```bash
# Sync status
python daemon/gdrive/sync.py status

# Manual sync
python daemon/gdrive/sync.py pull

# Pack export
python daemon/gdrive/pack_sync.py export

# Watch for changes
python daemon/gdrive/change_watcher.py --watch
```

### Services

```bash
# Start all (Docker)
docker-compose up -d

# Start LocalAI only
docker-compose up -d localai

# Start Dragonfly cache
docker-compose up -d dragonfly

# Check health
curl http://localhost:8080/health  # LocalAI
curl http://localhost:8765/health  # API
```

---

## Debugging

### Hook Issues

```bash
# Test hook execution
cd .claude/hooks && npm test

# Check hook logs
type .claude\hooks\logs\*.log

# Rebuild hooks
cd .claude/hooks && npm run build
```

### Model Routing Failures

1. **LocalAI timeout**: Check `docker logs localai`
2. **Codex error**: Verify `CODEX_API_KEY` in `.env`
3. **Claude fallback**: Check API limits, balance

```bash
# Force skip LocalAI
python daemon/model_router.py --skip-localai "query"
```

### Database Issues

```bash
# Check SQLite integrity
sqlite3 daemon/tasks.db "PRAGMA integrity_check"

# List tables
sqlite3 daemon/tasks.db ".tables"

# Backup
copy daemon\tasks.db daemon\tasks.db.bak
```

### Token Optimization

```bash
# Check MCP server status
# (MCP runs via stdio, check Claude Code logs)

# Verify smart tools available
# In Claude: ToolSearch query="smart_read"

# Check cache stats
curl http://localhost:6379/INFO  # Dragonfly
```

---

## Emergency Procedures

### Context Overflow

1. Create handoff: `/create_handoff`
2. Save to `thoughts/handoffs/YYYY-MM-DD_<topic>.yaml`
3. Update `task.md` with current state
4. Clear context and resume from handoff

### Service Down

```bash
# Restart all
docker-compose down && docker-compose up -d

# Check what's running
docker ps

# View logs
docker-compose logs -f
```

### Database Corruption

```bash
# Export to SQL
sqlite3 daemon/tasks.db ".dump" > backup.sql

# Rebuild from backup
rm daemon/tasks.db
sqlite3 daemon/tasks.db < backup.sql
```

---

## Monitoring

### Key Metrics

| Metric | Check | Target |
|--------|-------|--------|
| Token usage | Session stats | <100K/session |
| Cache hit rate | Dragonfly stats | >70% |
| LocalAI latency | Router stats | <5s |
| Memory entries | `memory.py stats` | Growing |

### Health Checks

```bash
# Full system check
python daemon/api.py health

# Individual services
curl -s localhost:8080/health | jq .  # LocalAI
curl -s localhost:8765/health | jq .  # API
curl -s localhost:6379/ping          # Dragonfly
```

---

## Scheduled Tasks

| Task | Frequency | Command |
|------|-----------|---------|
| Pack sync | On change | `change_watcher.py --auto-sync` |
| Memory backup | Daily | `memory.py backup` |
| Log rotation | Weekly | Archive .claude/hooks/logs/ |
| Self-improvement | Per session | `self_improvement.py improvements` |
