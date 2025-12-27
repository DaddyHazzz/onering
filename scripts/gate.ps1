Param()

$resolvedMode = $null

# Parse args like: --mode full  OR full
if ($args.Count -gt 0) {
  for ($i = 0; $i -lt $args.Count; $i++) {
    $arg = $args[$i]
    if ($arg -eq "--") { continue }
    if ($arg -eq "--mode" -and ($i + 1) -lt $args.Count) {
      $resolvedMode = $args[$i + 1]
      break
    }
    if (-not $resolvedMode) {
      $resolvedMode = $arg
    }
  }
}
if (-not $resolvedMode -and $env:ONERING_GATE) {
  $resolvedMode = $env:ONERING_GATE
}
if (-not $resolvedMode) {
  $resolvedMode = "fast"
}

$resolvedMode = $resolvedMode.ToLower()
Write-Host "Starting test gate (mode: $resolvedMode)..." -ForegroundColor Cyan

Write-Host "Running secret scan..." -ForegroundColor Yellow
python tools/secret_scan.py --all
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

switch ($resolvedMode) {
  "docs" {
    Write-Host "DOCS mode: skipping automated tests." -ForegroundColor Yellow
    exit 0
  }
  "full" {
    Write-Host "Running FULL suites (backend + frontend)..." -ForegroundColor Yellow
    python -m pytest backend/tests -q --tb=no
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    pnpm vitest run
    exit $LASTEXITCODE
  }
  "fast" {
    Write-Host "Running FAST lane (changed-only)..." -ForegroundColor Yellow
    python scripts/test_changed.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "FAST lane passed. Use --mode full before final push." -ForegroundColor Green
    exit 0
  }
  default {
    Write-Host "Unknown gate mode '$resolvedMode'. Use fast|full|docs." -ForegroundColor Red
    exit 1
  }
}
