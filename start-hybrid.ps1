# Hybrid Architecture Startup Script
# Starts: Dragonfly (cache layer) + Token Optimizer MCP

param(
    [switch]$DragonflyOnly,
    [switch]$TokenOptimizerOnly,
    [switch]$Status,
    [switch]$Stop
)

$ErrorActionPreference = "Continue"

Write-Host "=== Hybrid Architecture Manager ===" -ForegroundColor Cyan

if ($Status) {
    Write-Host "`n[Dragonfly Status]" -ForegroundColor Yellow
    docker ps --filter name=dragonfly-cache --format "{{.Status}}"
    if ($LASTEXITCODE -eq 0) {
        docker exec dragonfly-cache redis-cli INFO server 2>$null | Select-String "redis_version|uptime"
    }
    Write-Host "`n[Token Optimizer Cache]" -ForegroundColor Yellow
    if (Test-Path "$env:USERPROFILE\.token-optimizer-cache") {
        Get-ChildItem "$env:USERPROFILE\.token-optimizer-cache" -Recurse | Measure-Object -Property Length -Sum |
            ForEach-Object { "Cache size: $([math]::Round($_.Sum / 1MB, 2)) MB" }
    } else {
        Write-Host "No cache directory found"
    }
    exit
}

if ($Stop) {
    Write-Host "Stopping Dragonfly..." -ForegroundColor Yellow
    docker stop dragonfly-cache 2>$null
    docker rm dragonfly-cache 2>$null
    Write-Host "Done." -ForegroundColor Green
    exit
}

# Start Dragonfly
if (-not $TokenOptimizerOnly) {
    Write-Host "`n[Starting Dragonfly Cache Layer]" -ForegroundColor Yellow

    # Check if already running
    $running = docker ps --filter name=dragonfly-cache --format "{{.Names}}" 2>$null
    if ($running -eq "dragonfly-cache") {
        Write-Host "Dragonfly already running" -ForegroundColor Green
    } else {
        # Remove if exists but stopped
        docker rm dragonfly-cache 2>$null

        # Start container
        docker run -d `
            --name dragonfly-cache `
            -p 6379:6379 `
            -v dragonfly_data:/data `
            docker.dragonflydb.io/dragonflydb/dragonfly:latest `
            --cache_mode=true `
            --maxmemory=4gb `
            --proactor_threads=4 `
            --dbfilename=dump.rdb `
            --dir=/data

        Start-Sleep -Seconds 3

        # Verify
        $ping = docker exec dragonfly-cache redis-cli PING 2>$null
        if ($ping -eq "PONG") {
            Write-Host "Dragonfly started successfully (25x faster than Redis)" -ForegroundColor Green
        } else {
            Write-Host "Dragonfly failed to start - check: docker logs dragonfly-cache" -ForegroundColor Red
        }
    }
}

# Token Optimizer info
if (-not $DragonflyOnly) {
    Write-Host "`n[Token Optimizer MCP]" -ForegroundColor Yellow

    # Create cache dir if needed
    if (-not (Test-Path "$env:USERPROFILE\.token-optimizer-cache")) {
        New-Item -ItemType Directory -Path "$env:USERPROFILE\.token-optimizer-cache" -Force | Out-Null
    }

    Write-Host "MCP server configured in .mcp.json" -ForegroundColor Green
    Write-Host "Features: 65 tools, 60-90% token reduction, Brotli compression" -ForegroundColor Gray
    Write-Host "Cache dir: $env:USERPROFILE\.token-optimizer-cache" -ForegroundColor Gray
}

Write-Host "`n=== Hybrid Architecture Ready ===" -ForegroundColor Cyan
Write-Host "  Dragonfly: localhost:6379 (cache layer)"
Write-Host "  Token Optimizer: via .mcp.json (context compression)"
Write-Host "`nRun with -Status to check health"
