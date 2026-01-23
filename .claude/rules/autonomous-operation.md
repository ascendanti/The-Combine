# Autonomous Operation Mode

**FULL AUTONOMY GRANTED** - User has authorized all operations.

This instance operates with complete autonomy. ALL permissions granted.

## All Operations Allowed (No Confirmation Needed)

### File Operations
- Create, edit, delete ANY files in the project
- Modify configuration files
- Create new scripts, hooks, skills, agents
- Reorganize directory structure

### System Operations
- Install npm/pip/uv dependencies
- Run build scripts
- Execute PowerShell/Bash commands
- Start/stop background processes
- Manage Windows services

### Git Operations
- Stage files
- Create commits
- Create branches
- Push to remote (if configured)
- Create PRs

### External Operations
- Web searches
- Fetch documentation
- API calls (read-only)

## Safety Constraints (Self-Imposed)

- Do NOT modify system files outside project directory
- Do NOT delete user data outside project
- Do NOT run commands that could damage the OS
- ALWAYS create backups before destructive operations
- ALWAYS validate changes before proceeding

## Iteration Protocol

1. **Act first, report after** - Don't ask, do
2. **Log actions** - Update task.md after significant changes
3. **Validate each step** - Test before moving to next phase
4. **Create checkpoints** - Handoff if approaching token limit
5. **Recover gracefully** - If something fails, fix it and continue

## On Token Limit

Before running out of context:
1. Create handoff in `thoughts/handoffs/`
2. Update `EVOLUTION-PLAN.md` with current status
3. Send Slack notification (if configured)

Next session resumes from handoff automatically.
