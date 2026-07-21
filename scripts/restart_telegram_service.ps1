[CmdletBinding()]
param([string]$TaskName = 'Proyecto Atlas - Telegram')
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'stop_telegram_service.ps1') -TaskName $TaskName
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 8
Write-Host 'Atlas Telegram reiniciado en segundo plano.' -ForegroundColor Green
