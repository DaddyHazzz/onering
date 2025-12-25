param(
    [string]$Mode
)

# Safety: hooks are opt-in. If ONERING_GATE is unset, skip. Set ONERING_HOOKS=0 to disable. No direct test commands here.

$repoRoot = git rev-parse --show-toplevel
Push-Location $repoRoot

if ($env:ONERING_HOOKS -eq "0") {
    Write-Host "[pre-commit] Hooks disabled via ONERING_HOOKS=0; skipping." -ForegroundColor Yellow
    Pop-Location
    exit 0
}

$resolvedMode = $Mode
if (-not $resolvedMode -and $env:ONERING_GATE) { $resolvedMode = $env:ONERING_GATE }
if (-not $resolvedMode) {
    Write-Host "[pre-commit] ONERING_GATE not set; skipping tests." -ForegroundColor Yellow
    Pop-Location
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
exit $status