Param()

Write-Host "🔍 Pre-commit checks..." -ForegroundColor Cyan
Write-Host ""

$repoRoot = git rev-parse --show-toplevel
Push-Location $repoRoot

# Backend tests
Write-Host "Running backend tests..." -ForegroundColor Yellow
Push-Location "backend"
pytest -q 2>&1 | Out-String | ForEach-Object { Write-Host $_ -ForegroundColor Gray }
$backendStatus = $LASTEXITCODE
Pop-Location

if ($backendStatus -ne 0) {
    Write-Host ""
    Write-Host "❌ Backend tests failed. Commit aborted." -ForegroundColor Red
    Pop-Location
    exit 1
}

# Frontend tests
Write-Host ""
Write-Host "Running frontend tests..." -ForegroundColor Yellow
pnpm test -- --run 2>&1 | Out-String | ForEach-Object { Write-Host $_ -ForegroundColor Gray }
$frontendStatus = $LASTEXITCODE

if ($frontendStatus -ne 0) {
    Write-Host ""
    Write-Host "❌ Frontend tests failed. Commit aborted." -ForegroundColor Red
    Pop-Location
    exit 1
}

Write-Host ""
Write-Host "✅ All pre-commit checks passed. Proceeding with commit." -ForegroundColor Green

Pop-Location
exit 0