[CmdletBinding()]
param(
    [string]$TelegramTaskName = 'Proyecto Atlas - Telegram',
    [string]$MonitorTaskName = 'Proyecto Atlas - Monitorizacion'
)

Write-Host 'Tareas programadas:' -ForegroundColor Cyan

Get-ScheduledTask |
Where-Object {
    $_.TaskName -in @($TelegramTaskName, $MonitorTaskName)
} |
Select-Object TaskName, State

Write-Host ''
Write-Host 'Procesos Atlas activos:' -ForegroundColor Cyan

Get-CimInstance Win32_Process |
Where-Object {
    $_.CommandLine -and (
        $_.CommandLine -match 'run_telegram_bot|run_telegram_supervisor' -or
        $_.CommandLine -match 'monitoring.run_supervisor'
    )
} |
Select-Object ProcessId, ExecutablePath, CommandLine
