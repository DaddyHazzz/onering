Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "OneRing Shutdown" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

Write-Host "Stopping..." -ForegroundColor Yellow
Get-Process | Where-Object { $_.Name -like "*node*" -or $_.Name -like "*python*" -or $_.Name -like "*stripe*" } | Stop-Process -EA SilentlyContinue
Start-Sleep 2

Write-Host "=" * 70 -ForegroundColor Green
Write-Host "Stopped" -ForegroundColor Green
Write-Host "=" * 70 -ForegroundColor Green
