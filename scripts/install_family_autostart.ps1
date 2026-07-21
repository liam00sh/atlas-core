[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$TelegramInstaller = Join-Path $PSScriptRoot 'install_telegram_autostart.ps1'
$MonitorInstaller = Join-Path $PSScriptRoot 'install_pc_monitor.ps1'

if (-not (Test-Path $TelegramInstaller)) { throw "Falta $TelegramInstaller" }
if (-not (Test-Path $MonitorInstaller)) { throw "Falta $MonitorInstaller" }

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $TelegramInstaller
if ($LASTEXITCODE -ne 0) { throw "Falló la instalación del arranque automático de Telegram." }

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $MonitorInstaller
if ($LASTEXITCODE -ne 0) { throw "Falló la instalación del monitor del PC." }

Write-Host 'Arranque automático familiar instalado: Telegram + monitor del PC.' -ForegroundColor Green
Get-ScheduledTask -TaskName 'Proyecto Atlas - Telegram','Proyecto Atlas - Monitor PC' |
    Select-Object TaskName, State
