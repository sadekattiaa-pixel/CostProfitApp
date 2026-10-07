param(
    [string]$IsccPath = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    [switch]$SkipAppBuild
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$appExe = Join-Path $projectRoot "dist\Invoice\Invoice.exe"
$installerScript = Join-Path $projectRoot "installer\CostProfitApp.iss"

if (-not $SkipAppBuild) {
    & (Join-Path $projectRoot "build_windows.ps1")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not (Test-Path -LiteralPath $appExe)) {
    throw "Packaged application not found: $appExe"
}
if (-not (Test-Path -LiteralPath $IsccPath)) {
    throw "Inno Setup compiler not found. Pass its location with -IsccPath."
}

& $IsccPath $installerScript
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Installer completed: dist\installer\Invoice-Setup-1.1.0.exe"
