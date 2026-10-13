$ErrorActionPreference = "Stop"

$Dir = Join-Path $env:LOCALAPPDATA "Rupert"
$Bin = Join-Path $Dir "bin"
New-Item -ItemType Directory -Force -Path $Bin | Out-Null
foreach ($sub in "rupert", "shared") {
    $dest = Join-Path $Dir $sub
    if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
}
Copy-Item -Recurse (Join-Path $PSScriptRoot "rupert") (Join-Path $Dir "rupert")
Copy-Item -Recurse (Join-Path $PSScriptRoot "..\shared") (Join-Path $Dir "shared")
Remove-Item -ErrorAction SilentlyContinue (Join-Path $Dir "rupert.py")

$VenvPy = Join-Path $Dir "venv\Scripts\python.exe"
if (-not (Test-Path $VenvPy)) {
    Write-Host "Setting up Python environment (one time, ~1 min)..."
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv (Join-Path $Dir "venv") }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { & python -m venv (Join-Path $Dir "venv") }
    else { throw "Python 3 not found. Install it from https://www.python.org/downloads/ (tick 'Add to PATH'), then run install.cmd again." }
}
& $VenvPy -m pip install -q --upgrade pip
& $VenvPy -m pip install -q "PySide6>=6.4"

$env:PYTHONPATH = $Dir
& $VenvPy -m rupert --sync-commands

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (($UserPath -split ";") -notcontains $Bin) {
    [Environment]::SetEnvironmentVariable("Path", (($UserPath.TrimEnd(";")) + ";" + $Bin).TrimStart(";"), "User")
}

Write-Host ""
Write-Host "Installed. Open a NEW terminal window, then type: rupert on"
