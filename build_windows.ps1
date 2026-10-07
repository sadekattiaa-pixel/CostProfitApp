param(
    [string]$DistPath = "dist",
    [string]$WorkPath = "build",
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"
$env:PYTHONDONTWRITEBYTECODE = "1"

# Build tools can add unrelated native DLL folders to PATH. PyInstaller may
# otherwise bundle their Windows runtime files, which can break the app on the
# target Windows version (for example, Windows 11 UCRT files on Windows 10).
$env:PATH = (($env:PATH -split ";") | Where-Object {
    $_ -and $_ -notmatch "codex-runtimes|\\.codex\\tmp|OpenAI\\Codex"
}) -join ";"

$projectPython = if ($PythonPath) {
    $PythonPath
} else {
    Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
}
if (-not (Test-Path $projectPython)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $projectPython = $pythonCommand.Source
        Write-Host "Project virtual environment was not found; using $projectPython"
    } else {
        throw "Missing Python environment. Create .venv or pass -PythonPath with a configured Python executable."
    }
}

& $projectPython -c "import PySide6, shiboken6; from PySide6 import QtCore; print('Building with PySide6', PySide6.__version__, 'from', PySide6.__file__)"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $projectPython -B -m PyInstaller `
    --noconfirm `
    --clean `
    --distpath $DistPath `
    --workpath $WorkPath `
    (Join-Path $PSScriptRoot "CostProfitApp.spec")

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Some image/PDF toolchains expose private copies of the Windows Universal CRT
# to PyInstaller's DLL scanner. Bundling those copies makes them override the
# operating-system CRT and can prevent PySide6.QtCore from loading on Windows
# 10. The supported Windows runtime must come from System32 instead.
$internalPath = Join-Path $DistPath "Invoice\_internal"
$distFullPath = if ([IO.Path]::IsPathRooted($DistPath)) {
    [IO.Path]::GetFullPath($DistPath)
} else {
    [IO.Path]::GetFullPath((Join-Path $PSScriptRoot $DistPath))
}
$internalFullPath = Join-Path $distFullPath "Invoice\_internal"
if (-not $internalFullPath.StartsWith($distFullPath, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to clean runtime files outside the build output: $internalFullPath"
}

$conflictingRuntimeFiles = Get-ChildItem -LiteralPath $internalFullPath -File | Where-Object {
    $_.Name -eq "ucrtbase.dll" -or
    $_.Name -like "api-ms-win-*.dll" -or
    $_.Name -eq "icuuc.dll" -or
    $_.Name -like "icudt*.dll"
}
foreach ($runtimeFile in $conflictingRuntimeFiles) {
    Remove-Item -LiteralPath $runtimeFile.FullName -Force
}

Write-Host "Removed $($conflictingRuntimeFiles.Count) conflicting Windows runtime file(s)."
Write-Host "Build completed: $DistPath\Invoice"
