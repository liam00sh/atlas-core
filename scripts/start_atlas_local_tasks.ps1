[CmdletBinding()]
param(
    [string]$TelegramTaskName = 'Proyecto Atlas - Telegram',
    [string]$MonitorTaskName = 'Proyecto Atlas - Monitorizacion'
)

$ErrorActionPreference = 'Stop'

foreach ($name in @($TelegramTaskName, $MonitorTaskName)) {
    $task = Get-ScheduledTask `
        -TaskName $name `
        -ErrorAction SilentlyContinue

    if (-not $task) {
        Write-Warning "No existe la tarea: $name"
        continue
    }

    Start-ScheduledTask -TaskName $name
}

Start-Sleep -Seconds 6

Get-ScheduledTask |
Where-Object {
    $_.TaskName -in @($TelegramTaskName, $MonitorTaskName)
} |
Select-Object TaskName, State
