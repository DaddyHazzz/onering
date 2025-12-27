param(
    [string]$Mode
)

# Safety: hooks are DISABLED by default. Require ONERING_HOOKS=1 AND ONERING_GATE to run.
# Recursion guard: if ONERING_HOOK_RUNNING already set, skip to prevent loops.

if ($env:ONERING_HOOK_RUNNING -eq "1") {
    Write-Host "[pre-commit] Already running (recursion guard); skipping." -ForegroundColor Gray
    exit 0
}

if ($env:ONERING_HOOKS -ne "1") {
    Write-Host "[pre-commit] Hooks disabled by default. Enable with: ONERING_HOOKS=1 ONERING_GATE=fast|full|docs" -ForegroundColor Yellow
    exit 0
}

$env:ONERING_HOOK_RUNNING = "1"

$repoRoot = git rev-parse --show-toplevel
Push-Location $repoRoot

Write-Host "[pre-commit] Secret scan (staged)..." -ForegroundColor Cyan
python tools/secret_scan.py --staged
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    $env:ONERING_HOOK_RUNNING = ""
    exit $LASTEXITCODE
}

$resolvedMode = $Mode
if (-not $resolvedMode -and $env:ONERING_GATE) { $resolvedMode = $env:ONERING_GATE }
if (-not $resolvedMode) {
    Write-Host "[pre-commit] ONERING_GATE not set; skipping tests." -ForegroundColor Yellow
    Pop-Location
    $env:ONERING_HOOK_RUNNING = ""
    exit 0
}
$resolvedMode = $resolvedMode.ToLower()

switch ($resolvedMode) {
    "docs" {
        Write-Host "[pre-commit] DOCS mode: running docs gate (no tests)." -ForegroundColor Yellow
        pnpm gate -- --mode docs
    }
    "fast" {
        Write-Host "[pre-commit] FAST mode: running changed-only gate." -ForegroundColor Cyan
        pnpm gate -- --mode fast
    }
    "full" {
        Write-Host "[pre-commit] FULL mode: running full gate." -ForegroundColor Cyan
        pnpm gate -- --mode full
    }
    default {
        Write-Host "[pre-commit] Unknown ONERING_GATE '$resolvedMode'. Use docs|fast|full." -ForegroundColor Red
        Pop-Location
        exit 1
    }
}

$status = $LASTEXITCODE

if ($status -eq 0) {
    Write-Host "[pre-commit] Gate passed." -ForegroundColor Green
} else {
    Write-Host "[pre-commit] Gate failed." -ForegroundColor Red
}

Pop-Location
$env:ONERING_HOOK_RUNNING = ""
exit $status
