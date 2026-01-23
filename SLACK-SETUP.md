# Claude Code Slack Notifications Setup

Send a one-line summary to Slack after each Claude Code iteration/response.

## Quick Setup

### Option 1: Direct Slack Webhook (Simplest)

1. **Create a Slack Incoming Webhook:**
   - Go to https://api.slack.com/apps
   - Create a new app (or use existing)
   - Enable "Incoming Webhooks"
   - Click "Add New Webhook to Workspace"
   - Select your channel (e.g., `#claude-updates`)
   - Copy the webhook URL

2. **Configure the environment:**
   ```bash
   # Copy the template
   copy .env.template .env

   # Edit .env and add your webhook URL
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00.../B00.../xxx...
   ```

3. **Test it:**
   ```bash
   # From the project directory
   python .claude/hooks/slack-notify.py
   ```

### Option 2: n8n Webhook (More Flexible)

Use this if you want to customize notifications, add conditions, or send to multiple channels.

1. **Create n8n Workflow:**

   In n8n, create a new workflow:

   ```
   [Webhook Trigger] -> [IF Node: filter events] -> [Slack Node: send message]
   ```

   **Webhook node settings:**
   - HTTP Method: POST
   - Path: `claude-updates`

   **Slack node settings:**
   - Message: `{{ $json.summary }} ({{ $json.project }})`
   - Channel: `#claude-updates`

2. **Configure environment:**
   ```bash
   # In .env
   N8N_WEBHOOK_URL=https://your-n8n.com/webhook/claude-updates
   ```

3. **Update settings.local.json:**
   Change the hook command to use n8n-notify.py instead:
   ```json
   "command": "python \".claude/hooks/n8n-notify.py\""
   ```

## Webhook Payload

When using n8n, you'll receive this JSON:

```json
{
  "timestamp": "2026-01-22T15:30:00.000000",
  "event": "Stop",
  "project": "Claude n8n",
  "session_id": "abc123...",
  "summary": "Claude finished responding",
  "tool_name": "Edit",
  "tool_input": {"file_path": "..."},
  "working_directory": "C:/Users/..."
}
```

## Sample n8n Workflow (JSON Import)

Create a file `claude-slack-workflow.json` and import into n8n:

```json
{
  "name": "Claude Slack Notifications",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "claude-updates"
      },
      "type": "n8n-nodes-base.webhook",
      "name": "Webhook",
      "position": [250, 300]
    },
    {
      "parameters": {
        "channel": "#claude-updates",
        "text": "=*Claude Update* `{{ $json.timestamp.split('T')[1].split('.')[0] }}`\n{{ $json.summary }}\n_Project: {{ $json.project }}_"
      },
      "type": "n8n-nodes-base.slack",
      "name": "Slack",
      "position": [450, 300]
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{"node": "Slack", "type": "main", "index": 0}]]
    }
  }
}
```

## Event Types

The hook triggers on different events:

| Event | When | Example Summary |
|-------|------|-----------------|
| `Stop` | After Claude finishes responding | "Claude finished responding" |
| `PostToolUse` | After each tool use | "Edited src/app.js" |
| `SessionStart` | When session begins | "Claude session started" |
| `SessionEnd` | When session ends | "Claude session ended" |

## Customizing

To change which events trigger notifications, edit `.claude/settings.local.json`:

```json
{
  "hooks": {
    "Stop": [...],           // After each response
    "PostToolUse": [...],    // After each tool (more frequent)
    "SessionEnd": [...]      // Only when closing
  }
}
```

## Troubleshooting

**No notifications?**
- Check `.env` file exists and has correct URL
- Test webhook manually: `curl -X POST -H "Content-Type: application/json" -d '{"text":"test"}' YOUR_WEBHOOK_URL`
- Check Python is in PATH: `python --version`

**Too many notifications?**
- Use `Stop` hook only (not `PostToolUse`)
- Add filtering in n8n workflow

**Permission errors?**
- Ensure the hook command is allowed in `settings.local.json` permissions
