[CmdletBinding()]
param([string]$TaskName = 'Proyecto Atlas - Telegram')

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$SupervisorLock = Join-Path $ProjectRoot 'data\integrations\telegram\supervisor.lock'
$PollingLock = Join-Path $ProjectRoot 'data\integrations\telegram\polling.lock'

Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Start-Sleep -Seconds 5

# Solo retiramos bloqueos si ya no queda ningún proceso relacionado.
$atlasProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -match '^pythonw?\.exe$' -and
    ($_.CommandLine -like '*run_telegram_supervisor.py*' -or $_.CommandLine -like '*run_telegram_bot.py*')
}
if (-not $atlasProcesses) {
    Remove-Item $SupervisorLock -Force -ErrorAction SilentlyContinue
    Remove-Item $PollingLock -Force -ErrorAction SilentlyContinue
}

Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 6
Write-Host 'Atlas Telegram reiniciado. El supervisor y el código actual ya están cargados.' -ForegroundColor Green
