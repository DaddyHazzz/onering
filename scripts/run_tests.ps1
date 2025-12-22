Param(
    [switch]$NoBackend = $false,
    [switch]$NoFrontend = $false
)

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "OneRing Test Suite (Phase 3.7)" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

$overallSuccess = $true
$repoRoot = "$PSScriptRoot/.."

# Detect venv and set up Python
Write-Host "Detecting Python environment..." -ForegroundColor Gray
$venvPython = "$repoRoot/.venv/Scripts/python.exe"
if (Test-Path $venvPython) {
    Write-Host "✅ Using venv at .venv" -ForegroundColor Green
    $pythonExe = $venvPython
} else {
    Write-Host "⚠️  No venv found, using system python" -ForegroundColor Yellow
    $pythonExe = "python"
}

# Backend tests
if (-not $NoBackend) {
    Write-Host ""
    Write-Host "BACKEND TESTS" -ForegroundColor Yellow
    Write-Host "Running backend tests with DATABASE_URL..." -ForegroundColor Gray
    
    $env:DATABASE_URL = "postgresql://onering:onering@localhost:5432/onering"
    $env:PYTHONPATH = $repoRoot
    
    Push-Location $repoRoot
    & $pythonExe -m pytest backend/tests/ -q --tb=no
    $backendStatus = $LASTEXITCODE
    Pop-Location
    
    if ($backendStatus -eq 0) {
        Write-Host "✅ Backend tests passed" -ForegroundColor Green
    } else {
        Write-Host "❌ Backend tests failed (exit code: $backendStatus)" -ForegroundColor Red
        $overallSuccess = $false
    }
}

# Frontend tests
if (-not $NoFrontend) {
    Write-Host ""
    Write-Host "FRONTEND TESTS" -ForegroundColor Yellow
    Write-Host "Running: pnpm test -- --run" -ForegroundColor Gray
    Push-Location $repoRoot
    pnpm test -- --run
    $frontendStatus = $LASTEXITCODE
    Pop-Location
    
    if ($frontendStatus -eq 0) {
        Write-Host "✅ Frontend tests passed" -ForegroundColor Green
    } else {
        Write-Host "❌ Frontend tests failed (exit code: $frontendStatus)" -ForegroundColor Red
        $overallSuccess = $false
    }
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

