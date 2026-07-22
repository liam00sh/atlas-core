[CmdletBinding()]

param(
    [string]$TaskName = 'Proyecto Atlas - Ciclo de vida Windows'
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$StateDir = Join-Path $ProjectRoot 'data\integrations\telegram'
$ListenerLock = Join-Path $StateDir 'windows_shutdown_listener.lock'

Write-Host (
    "Desinstalando la integración de ciclo de vida de Windows..."
) -ForegroundColor Cyan

$task = Get-ScheduledTask `
    -TaskName $TaskName `
    -ErrorAction SilentlyContinue

if ($task) {
    Stop-ScheduledTask `
        -TaskName $TaskName `
        -ErrorAction SilentlyContinue

    Start-Sleep -Seconds 1

    Unregister-ScheduledTask `
        -TaskName $TaskName `
        -Confirm:$false `
        -ErrorAction SilentlyContinue

    Write-Host (
        "Tarea programada eliminada: $TaskName"
    ) -ForegroundColor Yellow
} else {
    Write-Host (
        "La tarea programada no existe: $TaskName"
    ) -ForegroundColor DarkYellow
}

$listenerProcesses = Get-CimInstance Win32_Process `
    -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -match '^pythonw?\.exe$' -and
        $_.CommandLine -like '*windows_shutdown_listener.py*'
    }

foreach ($process in $listenerProcesses) {
    Stop-Process `
        -Id $process.ProcessId `
        -Force `
        -ErrorAction SilentlyContinue

    Write-Host (
        "Listener detenido. PID=$($process.ProcessId)"
    ) -ForegroundColor Yellow
}

Start-Sleep -Milliseconds 500

Remove-Item `
    -Path $ListenerLock `
    -Force `
    -ErrorAction SilentlyContinue

Write-Host (
    "Integración de ciclo de vida de Windows desinstalada."
) -ForegroundColor Green
