param(
  [switch]$Full
)

Write-Host "Starting test gate..." -ForegroundColor Cyan

if ($Full) {
  Write-Host "Running FULL suites (backend + frontend)..." -ForegroundColor Yellow
  # Backend full
  pytest -q --tb=no
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  # Frontend full
  pnpm vitest run
  exit $LASTEXITCODE
} else {
  Write-Host "Running FAST lane (changed-only) ..." -ForegroundColor Yellow
  python scripts/test_changed.py
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  Write-Host "FAST lane passed. Consider -Full for CI or before push." -ForegroundColor Green
  exit 0
}
