param(
  [switch]$Staged
)

function Get-ChangedFiles {
  if ($Staged) {
    $out = git diff --name-only --cached
  } else {
    $out = git diff --name-only HEAD
  }
  return $out | Where-Object { $_ -ne "" }
}

$changed = Get-ChangedFiles
if (-not $changed) {
  Write-Host "No changed files detected."
  exit 0
}

$testFiles = @()
foreach ($p in $changed) {
  if ($p -like "src/*") {
    $dir = Split-Path $p -Parent
    $name = [System.IO.Path]::GetFileNameWithoutExtension($p)
    $testsDir = Join-Path $dir "__tests__"
    $candidates = @(
      (Join-Path $testsDir ("$name.spec.ts")),
      (Join-Path $testsDir ("$name.spec.tsx")),
      (Join-Path $testsDir ("$name.test.ts")),
      (Join-Path $testsDir ("$name.test.tsx"))
    )
    foreach ($c in $candidates) {
      if (Test-Path $c) { $testFiles += $c }
    }
  }
}

$testFiles = $testFiles | Sort-Object -Unique
if (-not $testFiles) {
  Write-Host "No targeted vitest files found."
  exit 0
}

Write-Host "Running vitest for:" ($testFiles -join ", ")
pnpm vitest run @testFiles $testFiles
exit $LASTEXITCODE
