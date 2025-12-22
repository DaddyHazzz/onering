Param()

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "OneRing Test Suite" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

$overallSuccess = $true

# Backend tests
Write-Host "BACKEND TESTS" -ForegroundColor Yellow
Write-Host "Running: cd backend && pytest -q" -ForegroundColor Gray
Push-Location "$PSScriptRoot/../backend"
pytest -q
$backendStatus = $LASTEXITCODE
Pop-Location

if ($backendStatus -eq 0) {
    Write-Host "✅ Backend tests passed" -ForegroundColor Green
} else {
    Write-Host "❌ Backend tests failed (exit code: $backendStatus)" -ForegroundColor Red
    $overallSuccess = $false
}

Write-Host ""

# Frontend tests
Write-Host "FRONTEND TESTS" -ForegroundColor Yellow
Write-Host "Running: pnpm test -- --run" -ForegroundColor Gray
Push-Location "$PSScriptRoot/.."
pnpm test -- --run
$frontendStatus = $LASTEXITCODE
Pop-Location

if ($frontendStatus -eq 0) {
    Write-Host "✅ Frontend tests passed" -ForegroundColor Green
} else {
    Write-Host "❌ Frontend tests failed (exit code: $frontendStatus)" -ForegroundColor Red
    $overallSuccess = $false
}

Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan

if ($overallSuccess) {
    Write-Host "✅ ALL TESTS PASSED" -ForegroundColor Green
    Write-Host "===========================================" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "❌ SOME TESTS FAILED" -ForegroundColor Red
    Write-Host "===========================================" -ForegroundColor Cyan
    exit 1
}
