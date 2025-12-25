param(
    [string]$Mode
)

# Safety: default to fast gate; docs mode skips; full only when ONERING_GATE=full. Do not run tests directly here.

$repoRoot = git rev-parse --show-toplevel
Push-Location $repoRoot

$resolvedMode = $Mode
if (-not $resolvedMode -and $env:ONERING_GATE) { $resolvedMode = $env:ONERING_GATE }
if (-not $resolvedMode) { $resolvedMode = "fast" }
$resolvedMode = $resolvedMode.ToLower()

switch ($resolvedMode) {
    "docs" {
        Write-Host "[pre-commit] DOCS mode: skipping automated tests." -ForegroundColor Yellow
        Pop-Location
        exit 0
    }
    "fast" { }
    "full" { }
    default {
        Write-Host "[pre-commit] Unknown ONERING_GATE '$resolvedMode'. Use fast|full|docs." -ForegroundColor Red
        Pop-Location
        exit 1
    }
}

Write-Host "[pre-commit] Running gate (mode=$resolvedMode)..." -ForegroundColor Cyan
pnpm gate -- --mode $resolvedMode
$status = $LASTEXITCODE

if ($status -eq 0) {
    Write-Host "[pre-commit] Gate passed." -ForegroundColor Green
} else {
    Write-Host "[pre-commit] Gate failed." -ForegroundColor Red
}

Pop-Location
exit $status