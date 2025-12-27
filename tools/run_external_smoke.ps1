param(
    [string]$AdminKey = ""
)

# Smoke test runner for External API platform
# Usage: .\tools\run_external_smoke.ps1 -AdminKey "your_key"

Write-Host "🔥 SMOKE TEST: External API Platform" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Validate prerequisites
Write-Host "📋 Checking prerequisites..." -ForegroundColor Yellow

# Check backend is running
$backendUrl = "http://localhost:8000"
try {
    $health = Invoke-WebRequest -Uri "$backendUrl/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
    Write-Host "✓ Backend running on $backendUrl" -ForegroundColor Green
} catch {
    Write-Host "✗ Backend not responding on $backendUrl" -ForegroundColor Red
    Write-Host "  Start with: cd backend && python -m uvicorn main:app --reload --port 8000" -ForegroundColor Yellow
    exit 1
}

# Check webhook_sink is available (optional)
Write-Host "✓ Prerequisites checked" -ForegroundColor Green
Write-Host ""

# Run external_smoke.py
Write-Host "🚀 Starting smoke tests..." -ForegroundColor Cyan
Write-Host ""

$pythonCmd = if ($PSVersionTable.OS -like "*Windows*") { "python" } else { "python3" }

$env:PYTHONPATH = "$PWD/backend"

# Run backend smoke tests
& $pythonCmd backend/scripts/external_smoke.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "🎉 SMOKE TEST PASSED" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Review metrics on http://localhost:3000/monitoring/external" -ForegroundColor White
    Write-Host "2. Test with real API key: curl -X GET http://localhost:8000/v1/external/me -H 'Authorization: Bearer \$KEY'" -ForegroundColor White
    Write-Host "3. Create webhooks on http://localhost:3000/admin/external" -ForegroundColor White
    exit 0
} else {
    Write-Host ""
    Write-Host "❌ SMOKE TEST FAILED" -ForegroundColor Red
    Write-Host "Check logs above for details" -ForegroundColor Yellow
    exit 1
}
