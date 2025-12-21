# OneRing - Start All Services
# Run this script to start backend, frontend, and Stripe CLI in separate windows

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   OneRing - Starting All Services" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. Start Backend (FastAPI + uvicorn on port 8000)
Write-Host "[1/3] Starting FastAPI Backend..." -ForegroundColor Yellow
$backendCmd = "cd '$scriptDir'; Write-Host 'Starting Backend on http://localhost:8000' -ForegroundColor Green; C:\Python314\python.exe backend\start_backend.py"
Start-Process powershell -ArgumentList "-NoExit", "-NoProfile", "-Command", $backendCmd

Write-Host "      Waiting for backend to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 4

# 2. Start Next.js Frontend (port 3000)
Write-Host "[2/3] Starting Next.js Frontend..." -ForegroundColor Yellow
$frontendCmd = "cd '$scriptDir'; Write-Host 'Starting Frontend on http://localhost:3000' -ForegroundColor Green; pnpm dev"
Start-Process powershell -ArgumentList "-NoExit", "-NoProfile", "-Command", $frontendCmd

Write-Host "      Waiting for frontend to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 3

# 3. Start Stripe CLI (webhook forwarding)
Write-Host "[3/3] Starting Stripe CLI..." -ForegroundColor Yellow
$stripeCmd = "cd '$scriptDir'; Write-Host 'Starting Stripe webhook forwarding' -ForegroundColor Green; stripe listen --forward-to localhost:3000/api/stripe/webhook"
Start-Process powershell -ArgumentList "-NoExit", "-NoProfile", "-Command", $stripeCmd

Start-Sleep -Seconds 2

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   ✓ All Services Started Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor Yellow
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor Yellow
Write-Host "  Stripe:   Listening for webhooks" -ForegroundColor Yellow
Write-Host ""
Write-Host "Three terminal windows opened:" -ForegroundColor Gray
Write-Host "  - Backend (Python/FastAPI)" -ForegroundColor Gray
Write-Host "  - Frontend (Next.js)" -ForegroundColor Gray
Write-Host "  - Stripe CLI" -ForegroundColor Gray
Write-Host ""
Write-Host "Close those windows to stop the services." -ForegroundColor Gray
Write-Host "Press any key to close this launcher..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
