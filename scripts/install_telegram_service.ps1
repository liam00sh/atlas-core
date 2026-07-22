[CmdletBinding()]

param(
    [string]$TaskName = 'Proyecto Atlas - Telegram',
    [int]$DelaySeconds = 45
)

$ErrorActionPreference = 'Stop'

Write-Warning (
    'Este instalador se mantiene por compatibilidad. ' +
    'Usa install_telegram_autostart.ps1.'
)

& (Join-Path $PSScriptRoot 'install_telegram_autostart.ps1') `
    -TaskName $TaskName `
    -DelaySeconds $DelaySeconds
