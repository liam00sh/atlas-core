[CmdletBinding()]
param(
    [string]$TelegramTaskName = 'Proyecto Atlas - Telegram',
    [string]$MonitorTaskName = 'Proyecto Atlas - Monitorizacion'
)

$ErrorActionPreference = 'Continue'

foreach ($name in @($TelegramTaskName, $MonitorTaskName)) {
    Stop-ScheduledTask `
        -TaskName $name `
        -ErrorAction SilentlyContinue
}

Get-CimInstance Win32_Process |
Where-Object {
    $_.CommandLine -and (
        $_.CommandLine -match 'run_telegram_bot|run_telegram_supervisor' -or
        $_.CommandLine -match 'monitoring.run_supervisor'
    )
} |
ForEach-Object {
    Stop-Process `
        -Id $_.ProcessId `
        -Force `
        -ErrorAction SilentlyContinue
}

Write-Host 'Telegram y monitorizacion detenidos.' -ForegroundColor Yellow
