param(
  [string]$Mode
)

# Safety: hooks are opt-in; skip by default or when ONERING_HOOKS=0. Run full gate only when ONERING_GATE=full.

$repoRoot = git rev-parse --show-toplevel
Push-Location $repoRoot

$resolvedMode = $Mode
if ($env:ONERING_HOOKS -eq "0") {
  Write-Host "[pre-push] Hooks disabled via ONERING_HOOKS=0; skipping." -ForegroundColor Yellow
  Pop-Location
  exit 0
}

if (-not $resolvedMode -and $env:ONERING_GATE) { $resolvedMode = $env:ONERING_GATE }
if (-not $resolvedMode) { $resolvedMode = "skip" }
$resolvedMode = $resolvedMode.ToLower()

if ($resolvedMode -ne "full") {
  Write-Host "[pre-push] Skipping tests (set ONERING_GATE=full to run the full gate before push)." -ForegroundColor Yellow
  Pop-Location
  exit 0
}

Write-Host "[pre-push] Running FULL gate before push..." -ForegroundColor Cyan
pnpm gate -- --mode full
$status = $LASTEXITCODE

Pop-Location
exit $status
