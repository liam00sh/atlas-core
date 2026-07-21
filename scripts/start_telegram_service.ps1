[CmdletBinding()]
param([string]$TaskName = 'Proyecto Atlas - Telegram')
$ErrorActionPreference = 'Stop'
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 6
Write-Host 'Atlas Telegram iniciado en segundo plano.' -ForegroundColor Green
