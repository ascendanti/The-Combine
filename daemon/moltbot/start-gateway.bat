@echo off
REM Clawdbot Gateway - Bound to localhost only
REM Exposed via Tailscale Serve (tailnet-only, no public access)

cd /d "%USERPROFILE%\.clawdbot"

REM Start gateway on localhost:8080
clawdbot gateway --port 8080 --host 127.0.0.1 --verbose
