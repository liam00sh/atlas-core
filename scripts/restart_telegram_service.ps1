[CmdletBinding()]
param([string]$TaskName = 'Proyecto Atlas - Telegram')

$ErrorActionPreference = 'Stop'
$StopScript = Join-Path $PSScriptRoot 'stop_telegram_service.ps1'

if (-not (Test-Path $StopScript)) {
    throw 'No se encontró stop_telegram_service.ps1.'
}

& $StopScript -TaskName $TaskName
Start-Sleep -Seconds 3
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 8
Write-Host 'Atlas Telegram reiniciado en segundo plano.' -ForegroundColor Green
