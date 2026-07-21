[CmdletBinding()]
param([string]$TaskName = 'Proyecto Atlas - Telegram')
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue | Select-Object TaskName, State
Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction SilentlyContinue | Select-Object LastRunTime, LastTaskResult
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -match '^pythonw?\.exe$' -and (
        $_.CommandLine -like '*telegram_bootstrap.py*' -or
        $_.CommandLine -like '*run_telegram_supervisor.py*' -or
        $_.CommandLine -like '*run_telegram_bot.py*'
    )
} | Select-Object ProcessId, Name, CommandLine
Write-Host "Polling lock: $(Test-Path (Join-Path $ProjectRoot 'data\integrations\telegram\polling.lock'))"
Write-Host "Supervisor lock: $(Test-Path (Join-Path $ProjectRoot 'data\integrations\telegram\supervisor.lock'))"
