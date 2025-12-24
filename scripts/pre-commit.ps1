Param()
$ErrorActionPreference = 'Stop'

Push-Location (Join-Path $PSScriptRoot '..')

# Frontend gates
pnpm lint
pnpm typecheck
pnpm test -- --run

# Backend gates (optional if DATABASE_URL not set)
if ($Env:DATABASE_URL) {
  python -m pytest backend/tests -q
} else {
  Write-Host "Skipping backend tests (DATABASE_URL not set)."
}

Pop-Location
