[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$OutputEncoding = [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $ProjectRoot 'logs\monitoring'
$LogPath = Join-Path $LogDir 'monitoring_background.log'
$PythonPathFile = Join-Path $ProjectRoot 'data\integrations\telegram\python_path.txt'
$Monitor = Join-Path $ProjectRoot 'monitoring\run_supervisor.py'

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Set-Location $ProjectRoot

$python = $null

if (Test-Path $PythonPathFile) {
    $candidate = (Get-Content $PythonPathFile -Raw).Trim()
    if ($candidate -and (Test-Path $candidate)) {
        $python = $candidate
    }
}

if (-not $python) {
    $venvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
    if (Test-Path $venvPython) {
        $python = $venvPython
    }
}

if (-not $python) {
    $command = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $command) {
        $command = Get-Command python -ErrorAction SilentlyContinue
    }
    if ($command) {
        $python = $command.Source
    }
}

if (-not $python) {
    "$(Get-Date -Format o) No se encontro Python." |
        Add-Content -Encoding UTF8 -Path $LogPath
    exit 11
}

if (-not (Test-Path $Monitor)) {
    "$(Get-Date -Format o) No existe el supervisor: $Monitor" |
        Add-Content -Encoding UTF8 -Path $LogPath
    exit 12
}

"$(Get-Date -Format o) Iniciando monitorizacion: $Monitor" |
    Add-Content -Encoding UTF8 -Path $LogPath

& $python -m monitoring.run_supervisor *>> $LogPath
$exitCode = $LASTEXITCODE

"$(Get-Date -Format o) Monitorizacion finalizada con codigo $exitCode." |
    Add-Content -Encoding UTF8 -Path $LogPath

exit $exitCode
