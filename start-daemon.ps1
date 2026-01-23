# Start Claude Daemon Stack (Windows)

$ErrorActionPreference = "Stop"

# Check Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker not found. Install Docker Desktop first."
    exit 1
}

# Check for .env file
if (-not (Test-Path ".env")) {
    Write-Warning ".env file not found. Creating template..."
    @"
ANTHROPIC_API_KEY=your-key-here
GITHUB_WEBHOOK_SECRET=optional-secret
"@ | Out-File -FilePath ".env" -Encoding utf8
    Write-Host "Edit .env with your API key, then run this script again."
    exit 0
}

# Build and start
Write-Host "Starting Claude Daemon Stack..." -ForegroundColor Cyan
docker-compose up -d --build

# Show status
Write-Host ""
Write-Host "Services:" -ForegroundColor Green
docker-compose ps

Write-Host ""
Write-Host "Commands:" -ForegroundColor Yellow
Write-Host "  Logs:   docker-compose logs -f"
Write-Host "  Stop:   docker-compose down"
Write-Host "  Submit: python daemon/submit.py 'Your task here'"
Write-Host ""
Write-Host "GitHub webhook: http://localhost:8080/webhook" -ForegroundColor Cyan
