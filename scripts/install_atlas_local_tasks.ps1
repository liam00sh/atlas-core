[CmdletBinding()]
param(
    [string]$TelegramTaskName = 'Proyecto Atlas - Telegram',
    [string]$MonitorTaskName = 'Proyecto Atlas - Monitorizacion',
    [string]$DesktopTaskName = 'Proyecto Atlas - Escritorio',
    [int]$TelegramDelaySeconds = 45,
    [int]$MonitorDelaySeconds = 60,
    [int]$DesktopDelaySeconds = 20
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot

& (Join-Path $PSScriptRoot 'install_atlas_desktop.ps1') `
    -TaskName $DesktopTaskName `
    -DelaySeconds $DesktopDelaySeconds

# Telegram y supervisor interno ya se instalan mediante sus lanzadores actuales.
# Conserva las tareas existentes si ya están registradas.
foreach ($name in @($TelegramTaskName, $MonitorTaskName)) {
    $task = Get-ScheduledTask `
        -TaskName $name `
        -ErrorAction SilentlyContinue

    if (-not $task) {
        Write-Warning (
            "No existe $name. Ejecuta el instalador especifico correspondiente."
        )
        continue
    }

    Start-ScheduledTask `
        -TaskName $name `
        -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 8

Write-Host 'Servicios y escritorio de Atlas iniciados.' -ForegroundColor Green

Get-ScheduledTask |
Where-Object {
    $_.TaskName -in @(
        $TelegramTaskName,
        $MonitorTaskName,
        $DesktopTaskName
    )
} |
Select-Object TaskName, State
