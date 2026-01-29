# Moltbot Setup Script for Windows
# Binds to localhost, exposes via Tailscale, runs as Windows service

$ErrorActionPreference = "Stop"
$MoltbotPort = 8080
$MoltbotDir = "$env:USERPROFILE\.clawdbot"
$ServiceName = "MoltbotGateway"

Write-Host "=== Moltbot + Tailscale Setup ===" -ForegroundColor Cyan

# Step 1: Check prerequisites
Write-Host "`n[1/6] Checking prerequisites..." -ForegroundColor Yellow

$nodeVersion = node --version 2>$null
if (-not $nodeVersion) {
    Write-Error "Node.js not found. Install Node >= 22 first."
    exit 1
}
Write-Host "  Node.js: $nodeVersion" -ForegroundColor Green

# Step 2: Install Tailscale if needed
Write-Host "`n[2/6] Checking Tailscale..." -ForegroundColor Yellow
$tailscale = Get-Command tailscale -ErrorAction SilentlyContinue
if (-not $tailscale) {
    Write-Host "  Tailscale not found. Installing via winget..." -ForegroundColor Yellow
    winget install --id Tailscale.Tailscale --accept-source-agreements --accept-package-agreements
    Write-Host "  Please sign in to Tailscale after installation completes." -ForegroundColor Cyan
    Write-Host "  Then re-run this script." -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "  Tailscale installed" -ForegroundColor Green
    tailscale status 2>$null
}

# Step 3: Install NSSM if needed
Write-Host "`n[3/6] Checking NSSM..." -ForegroundColor Yellow
$nssm = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssm) {
    Write-Host "  NSSM not found. Installing via winget..." -ForegroundColor Yellow
    winget install --id NSSM.NSSM --accept-source-agreements --accept-package-agreements
    # Add to PATH
    $nssmPath = "C:\Program Files\NSSM\win64"
    if (Test-Path $nssmPath) {
        $env:PATH += ";$nssmPath"
    }
}
Write-Host "  NSSM ready" -ForegroundColor Green

# Step 4: Install Moltbot
Write-Host "`n[4/6] Installing Moltbot..." -ForegroundColor Yellow
npm install -g moltbot@latest
Write-Host "  Moltbot installed" -ForegroundColor Green

# Step 5: Create startup script
Write-Host "`n[5/6] Creating startup script..." -ForegroundColor Yellow

$startScript = @"
@echo off
cd /d "$MoltbotDir"
moltbot gateway --port $MoltbotPort --host 127.0.0.1 --verbose
"@

$scriptPath = "$MoltbotDir\start-gateway.bat"
New-Item -ItemType Directory -Force -Path $MoltbotDir | Out-Null
Set-Content -Path $scriptPath -Value $startScript
Write-Host "  Created: $scriptPath" -ForegroundColor Green

# Step 6: Create Windows service
Write-Host "`n[6/6] Creating Windows service..." -ForegroundColor Yellow

# Remove existing service if present
nssm stop $ServiceName 2>$null
nssm remove $ServiceName confirm 2>$null

# Install new service
nssm install $ServiceName "cmd.exe" "/c `"$scriptPath`""
nssm set $ServiceName AppDirectory "$MoltbotDir"
nssm set $ServiceName DisplayName "Moltbot Gateway"
nssm set $ServiceName Description "Moltbot AI Gateway - bound to localhost, exposed via Tailscale"
nssm set $ServiceName Start SERVICE_AUTO_START
nssm set $ServiceName AppStdout "$MoltbotDir\logs\gateway.log"
nssm set $ServiceName AppStderr "$MoltbotDir\logs\gateway-error.log"

New-Item -ItemType Directory -Force -Path "$MoltbotDir\logs" | Out-Null

Write-Host "  Service '$ServiceName' created" -ForegroundColor Green

# Instructions
Write-Host "`n=== Setup Complete ===" -ForegroundColor Cyan
Write-Host @"

NEXT STEPS:

1) Run onboarding (first time only):
   moltbot onboard --install-daemon

2) Start the service:
   nssm start $ServiceName

3) Expose via Tailscale (from this PC):
   tailscale serve $MoltbotPort

4) Access from any tailnet device:
   https://<your-pc-name>.<tailnet>.ts.net/

MANAGEMENT:
  - Stop service:   nssm stop $ServiceName
  - Restart:        nssm restart $ServiceName
  - View logs:      Get-Content "$MoltbotDir\logs\gateway.log" -Tail 50
  - Service status: nssm status $ServiceName

IMPORTANT:
  - Set Windows Sleep = Never in Power Settings
  - Tailscale Serve = private (tailnet only)
  - Do NOT use Tailscale Funnel (that's public)

"@ -ForegroundColor White
