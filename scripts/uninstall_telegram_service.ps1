[CmdletBinding()]
param([string]$TaskName = 'Proyecto Atlas - Telegram')
& (Join-Path $PSScriptRoot 'stop_telegram_service.ps1') -TaskName $TaskName
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Write-Host 'Tarea de Atlas Telegram eliminada. Los datos y vinculaciones se conservan.' -ForegroundColor Yellow
