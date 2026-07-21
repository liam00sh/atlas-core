[CmdletBinding()]
param([string]$TaskName = 'Proyecto Atlas - Telegram')

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$SupervisorLock = Join-Path $ProjectRoot 'data\integrations\telegram\supervisor.lock'
$PollingLock = Join-Path $ProjectRoot 'data\integrations\telegram\polling.lock'
$SupervisorLog = Join-Path $ProjectRoot 'logs\telegram\telegram_supervisor.log'
$BotLog = Join-Path $ProjectRoot 'logs\telegram\telegram_service.log'

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host 'Tarea de inicio automático: no instalada' -ForegroundColor Yellow
} else {
    Write-Host "Tarea: $($task.TaskName)"
    Write-Host "Estado: $($task.State)"
    Get-ScheduledTaskInfo -TaskName $TaskName | Select-Object LastRunTime, LastTaskResult, NextRunTime
}

$processes = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -match '^pythonw?\.exe$' -and
    ($_.CommandLine -like '*run_telegram_supervisor.py*' -or $_.CommandLine -like '*run_telegram_bot.py*')
} | Select-Object ProcessId, Name, CommandLine

Write-Host "Supervisor lock: $(Test-Path $SupervisorLock)"
Write-Host "Polling lock: $(Test-Path $PollingLock)"
if ($processes) {
    Write-Host 'Procesos activos:' -ForegroundColor Green
    $processes | Format-Table -AutoSize
} else {
    Write-Host 'Procesos activos: ninguno' -ForegroundColor Red
}

if (Test-Path $SupervisorLog) {
    Write-Host "`nÚltimas líneas del supervisor:"
    Get-Content $SupervisorLog -Tail 20
}
if (Test-Path $BotLog) {
    Write-Host "`nÚltimas líneas del bot:"
    Get-Content $BotLog -Tail 20
}
