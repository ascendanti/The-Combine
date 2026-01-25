# Atlas-Claude Startup Script
# Run this on startup to enable continuous operation

$ProjectDir = "C:\Users\New Employee\Downloads\Atlas-OS-main\Claude n8n"

Write-Host "Starting Atlas-Claude services..." -ForegroundColor Cyan

# 1. Prevent sleep - set power plan to High Performance
Write-Host "Setting power plan to prevent sleep..."
powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c 2>$null
if ($LASTEXITCODE -ne 0) {
    # High Performance not available, modify current plan
    powercfg /change standby-timeout-ac 0
    powercfg /change monitor-timeout-ac 0
    powercfg /change hibernate-timeout-ac 0
}
Write-Host "  Sleep prevention: ACTIVE" -ForegroundColor Green

# 2. Start Telegram poller (single instance)
$telegramProcess = Get-Process -Name "node" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*telegram-polling*" }

if (-not $telegramProcess) {
    Write-Host "Starting Telegram poller..."
    $pollerPath = Join-Path $ProjectDir "remote-access\telegram-polling.js"
    if (Test-Path $pollerPath) {
        Start-Process -FilePath "node" -ArgumentList $pollerPath -WorkingDirectory (Split-Path $pollerPath) -WindowStyle Hidden
        Write-Host "  Telegram poller: STARTED" -ForegroundColor Green
    } else {
        Write-Host "  Telegram poller: NOT FOUND at $pollerPath" -ForegroundColor Yellow
    }
} else {
    Write-Host "  Telegram poller: ALREADY RUNNING" -ForegroundColor Yellow
}

# 3. Check Docker services
$dockerRunning = Get-Process -Name "com.docker*" -ErrorAction SilentlyContinue
if ($dockerRunning) {
    Write-Host "  Docker: RUNNING" -ForegroundColor Green
} else {
    Write-Host "  Docker: NOT RUNNING (start Docker Desktop if needed)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Atlas-Claude startup complete!" -ForegroundColor Cyan
Write-Host "Project: $ProjectDir"
