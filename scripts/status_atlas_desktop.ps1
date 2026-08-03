[CmdletBinding()]
param(
    [string]$TaskName = 'Proyecto Atlas - Escritorio'
)

Write-Host 'Tarea grafica:' -ForegroundColor Cyan

Get-ScheduledTask `
    -TaskName $TaskName `
    -ErrorAction SilentlyContinue |
Select-Object TaskName, State

Write-Host ''
Write-Host 'Procesos graficos:' -ForegroundColor Cyan

Get-CimInstance Win32_Process |
Where-Object {
    $_.CommandLine -and (
        $_.CommandLine -match 'atlas_desktop_launcher.py' -or
        $_.CommandLine -match 'monitor_pc.py' -or
        $_.CommandLine -match 'monitoring.desktop_widgets'
    )
} |
Select-Object ProcessId, ExecutablePath, CommandLine

Write-Host ''
Write-Host 'Estado del launcher:' -ForegroundColor Cyan

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$StatusPath = Join-Path `
    $ProjectRoot `
    'data\launcher\desktop_launcher_status.json'

if (Test-Path $StatusPath) {
    Get-Content $StatusPath
}
else {
    Write-Warning 'Todavia no existe el estado del launcher.'
}
