Param()
$ErrorActionPreference = 'Stop'

# Backend tests
if (Test-Path "backend") {
  Write-Host "Running backend tests (pytest)" -ForegroundColor Cyan
  Push-Location "backend"
  try {
    python -m pytest -q
  } finally {
    Pop-Location
  }
}

# Frontend tests
Write-Host "Running frontend tests (vitest)" -ForegroundColor Cyan
pnpm test -- --run
