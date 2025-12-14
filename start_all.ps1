param([switch]$SkipDocker, [switch]$SkipStripe, [switch]$NoOpen)
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "OneRing Startup" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

# Check tools
$missing = @()
if (-not (Get-Command python -EA SilentlyContinue)) { $missing += "Python" }
if (-not (Get-Command node -EA SilentlyContinue)) { $missing += "Node.js" }
if (-not (Get-Command pnpm -EA SilentlyContinue)) { $missing += "pnpm" }

if ($missing) {
    Write-Host "Error: Missing $($missing -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host " Prerequisites OK" -ForegroundColor Green
Write-Host ""

# Docker
if (-not $SkipDocker) {
    Write-Host "Starting Docker..." -ForegroundColor Cyan
    if (docker ps 2>$null | Select-String postgres) {
        Write-Host " Docker running" -ForegroundColor Green
    } else {
        docker-compose -f "$Root\infra\docker-compose.yml" up -d
        Start-Sleep 3
        Write-Host " Docker started" -ForegroundColor Green
    }
    Write-Host ""
}

# Services
Write-Host "Starting Backend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root\backend'; python run_with_error_handling.py" -WindowStyle Normal
Start-Sleep 4
Write-Host " Backend started" -ForegroundColor Green
Write-Host ""

Write-Host "Starting Worker..." -ForegroundColor Cyan
Start-Process python -ArgumentList "-m", "rq", "worker", "-u", "redis://localhost:6379", "default" -WorkingDirectory $Root -WindowStyle Minimized
Start-Sleep 2
Write-Host " Worker started" -ForegroundColor Green
Write-Host ""

Write-Host "Starting Frontend..." -ForegroundColor Cyan
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "cd /d $Root && pnpm dev" -WindowStyle Normal
Start-Sleep 5
Write-Host " Frontend started" -ForegroundColor Green
Write-Host ""

if (-not $SkipStripe) {
    if (Get-Command stripe -EA SilentlyContinue) {
        Write-Host "Starting Stripe..." -ForegroundColor Cyan
        Start-Process stripe -ArgumentList "listen", "--forward-to", "localhost:3000/api/stripe/webhook" -NoNewWindow
        Write-Host " Stripe started" -ForegroundColor Green
        Write-Host ""
    }
}

Write-Host "=" * 70 -ForegroundColor Green
Write-Host "Ready! http://localhost:3000" -ForegroundColor Green
Write-Host "=" * 70 -ForegroundColor Green

if (-not $NoOpen) {
    Start-Sleep 2
    Start-Process "http://localhost:3000"
}
