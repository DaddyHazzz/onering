param(
  [string]$Mode
)

# Safety: hooks are DISABLED by default. Require ONERING_HOOKS=1 AND ONERING_GATE=full to run full gate.
# Recursion guard: if ONERING_HOOK_RUNNING already set, skip to prevent loops.

if ($env:ONERING_HOOK_RUNNING -eq "1") {
  Write-Host "[pre-push] Already running (recursion guard); skipping." -ForegroundColor Gray
  exit 0
}

if ($env:ONERING_HOOKS -ne "1") {
  Write-Host "[pre-push] Hooks disabled by default. Enable with: ONERING_HOOKS=1 ONERING_GATE=full" -ForegroundColor Yellow
  exit 0
}

$env:ONERING_HOOK_RUNNING = "1"

$repoRoot = git rev-parse --show-toplevel
Push-Location $repoRoot

$resolvedMode = $Mode

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
$env:ONERING_HOOK_RUNNING = ""
exit $status
