[CmdletBinding()]
param(
    [int]$WaitForProjectSeconds = 1800
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $env:LOCALAPPDATA 'ProyectoAtlas\Telegram'
$BootstrapLog = Join-Path $RuntimeDir 'telegram_bootstrap.log'
$PythonPathFile = Join-Path $ProjectRoot 'data\integrations\telegram\python_path.txt'
$Supervisor = Join-Path $ProjectRoot 'scripts\run_telegram_supervisor.py'

# IMPORTANTE: este directorio es local. No se escribe en H: hasta que Drive
# esté montado, porque hacerlo antes era una causa de salida silenciosa.
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
"$(Get-Date -Format o) Bootstrap iniciado. Esperando proyecto: $ProjectRoot" | Add-Content -Encoding UTF8 -Path $BootstrapLog

$deadline = (Get-Date).AddSeconds([Math]::Max(60, $WaitForProjectSeconds))
while (-not (Test-Path $Supervisor)) {
    if ((Get-Date) -ge $deadline) {
        "$(Get-Date -Format o) Proyecto no disponible tras la espera: $ProjectRoot" | Add-Content -Encoding UTF8 -Path $BootstrapLog
        exit 10
    }
    Start-Sleep -Seconds 5
}

$LogDir = Join-Path $ProjectRoot 'logs\telegram'
$LogPath = Join-Path $LogDir 'telegram_bootstrap.log'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Set-Location $ProjectRoot

$python = $null
if (Test-Path $PythonPathFile) {
    $candidate = (Get-Content $PythonPathFile -Raw).Trim()
    if ($candidate -and (Test-Path $candidate)) { $python = $candidate }
}
if (-not $python) {
    $command = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $command) { $command = Get-Command python -ErrorAction SilentlyContinue }
    if ($command) { $python = $command.Source }
}
if (-not $python) {
    "$(Get-Date -Format o) No se encontró Python." | Add-Content -Encoding UTF8 -Path $BootstrapLog
    exit 11
}

"$(Get-Date -Format o) Proyecto disponible. Iniciando supervisor con $python." | Add-Content -Encoding UTF8 -Path $BootstrapLog
"$(Get-Date -Format o) Iniciando supervisor de Atlas Telegram." | Add-Content -Encoding UTF8 -Path $LogPath
& $python $Supervisor *>> $LogPath
$exitCode = $LASTEXITCODE
"$(Get-Date -Format o) El supervisor terminó con código $exitCode." | Add-Content -Encoding UTF8 -Path $LogPath
"$(Get-Date -Format o) Supervisor terminado con código $exitCode." | Add-Content -Encoding UTF8 -Path $BootstrapLog
exit $exitCode
