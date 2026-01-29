# Clawdbot Local Gateway Setup

Run Clawdbot locally, expose via Tailscale, run as Windows service.

## Quick Start

### 1. First-Time Setup

```powershell
# Run onboarding wizard (configures OAuth, channels, etc.)
clawdbot onboard --install-daemon
```

### 2. Install as Windows Service

```powershell
# Run as Administrator
.\setup-clawdbot-service.bat
```

### 3. Start the Service

```powershell
nssm start ClawdbotGateway
```

### 4. Expose via Tailscale

```powershell
# This makes localhost:8080 accessible to your tailnet
tailscale serve 8080
```

## Access from Anywhere

Once Tailscale Serve is running:

```
https://<your-pc-name>.<tailnet>.ts.net/
```

Get your tailnet name with:
```powershell
tailscale status
```

## Architecture

```
Your Device (tailnet)
        │
        ▼
Tailscale Serve (HTTPS)
        │
        ▼
localhost:8080 (Clawdbot Gateway)
        │
        ├── Claude Pro (OAuth)
        ├── ChatGPT Pro (OAuth)
        ├── Grok Super (OAuth)
        └── Local models
```

## Service Management

| Command | Action |
|---------|--------|
| `nssm status ClawdbotGateway` | Check status |
| `nssm start ClawdbotGateway` | Start |
| `nssm stop ClawdbotGateway` | Stop |
| `nssm restart ClawdbotGateway` | Restart |

## Logs

```powershell
# View recent logs
Get-Content "$env:USERPROFILE\.clawdbot\logs\gateway.log" -Tail 50

# Follow logs
Get-Content "$env:USERPROFILE\.clawdbot\logs\gateway.log" -Wait
```

## Important Settings

### Windows Power (Non-negotiable)

- Set **Sleep = Never** in Power Settings
- Prefer Ethernet over Wi-Fi
- Optional: Enable "auto-restart after power loss" in BIOS

### Tailscale

- **Serve** = tailnet only (private) ✓
- **Funnel** = public internet (DON'T USE)

## Atlas Integration

Wire Clawdbot into Atlas via `model_router.py`:

```python
# In daemon/model_router.py
CLAWDBOT_GATEWAY = "http://localhost:8080"

# Route OAuth-enabled requests through Clawdbot
if use_subscription_model:
    response = requests.post(f"{CLAWDBOT_GATEWAY}/v1/chat/completions", ...)
```

## Troubleshooting

### Service won't start

1. Check logs: `type %USERPROFILE%\.clawdbot\logs\gateway-error.log`
2. Run manually first: `clawdbot gateway --port 8080 --verbose`
3. Ensure port 8080 isn't in use: `netstat -ano | findstr :8080`

### Tailscale Serve not working

1. Check Tailscale is connected: `tailscale status`
2. Verify serve is active: `tailscale serve status`
3. Ensure gateway is running: `curl http://localhost:8080`

### OAuth setup

Run `clawdbot onboard` to configure OAuth for:
- Claude Pro
- ChatGPT Pro
- Grok Super
