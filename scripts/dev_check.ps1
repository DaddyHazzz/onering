# scripts/dev_check.ps1
# Quick dev check: run all tests + print SUCCESS

Write-Host "🚀 Starting dev check..." -ForegroundColor Cyan
Write-Host ""

& "$PSScriptRoot/run_tests.ps1"
$testStatus = $LASTEXITCODE

if ($testStatus -eq 0) {
    Write-Host ""
    Write-Host "🎉 DEV CHECK PASSED - Ready to code!" -ForegroundColor Green
    exit 0
} else {
    Write-Host ""
    Write-Host "❌ DEV CHECK FAILED - Fix tests before proceeding" -ForegroundColor Red
    exit 1
}
