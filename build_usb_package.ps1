param(
    [string]$IsccPath = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    [string]$PythonPath = "python",
    [switch]$SkipAppBuild
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot

if (-not $SkipAppBuild) {
    & (Join-Path $projectRoot "build_windows.ps1") -PythonPath $PythonPath
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& $PythonPath -m PyInstaller --noconfirm --clean `
    --distpath (Join-Path $projectRoot "dist\activator") `
    --workpath (Join-Path $projectRoot "build\activator") `
    (Join-Path $projectRoot "CostProfitActivator.spec")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not (Test-Path -LiteralPath $IsccPath)) {
    throw "Inno Setup compiler not found: $IsccPath"
}
& $IsccPath (Join-Path $projectRoot "installer\CostProfitApp-USB.iss")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "USB installer: dist\installer\Invoice-Portable-Installer-1.1.0.exe"
Write-Host "Device information tool: dist\activator\InvoiceDeviceInfo.exe"
