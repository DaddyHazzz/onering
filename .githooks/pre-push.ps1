param(
  [string]$Mode
)

# Safety: skip by default; run full gate only when ONERING_GATE=full. No direct test commands here.

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
exit $status
