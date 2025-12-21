# OneRing - Stop All Services
# This script kills all running OneRing services

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   OneRing - Stopping All Services" -ForegroundColor Red
Write-Host "========================================`n" -ForegroundColor Cyan

# Stop all Python processes (backend)
Write-Host "[1/4] Stopping Backend (Python)..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "      ✓ Backend stopped" -ForegroundColor Gray

# Stop all Node processes (Next.js frontend)
Write-Host "[2/4] Stopping Frontend (Node)..." -ForegroundColor Yellow
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "      ✓ Frontend stopped" -ForegroundColor Gray

# Stop Stripe CLI
Write-Host "[3/4] Stopping Stripe CLI..." -ForegroundColor Yellow
Get-Process stripe -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "      ✓ Stripe CLI stopped" -ForegroundColor Gray

# Clean up ports (optional)
Write-Host "[4/4] Cleaning up ports..." -ForegroundColor Yellow
$ports = @(3000, 8000)
foreach ($port in $ports) {
    $process = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    if ($process) {
        Stop-Process -Id $process -Force -ErrorAction SilentlyContinue
    }
}
Write-Host "      ✓ Ports cleared" -ForegroundColor Gray

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   ✓ All Services Stopped" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Start-Sleep -Seconds 2
