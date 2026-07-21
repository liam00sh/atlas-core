[CmdletBinding()]
param([string]$TaskName = 'Proyecto Atlas - Telegram')

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $env:LOCALAPPDATA 'ProyectoAtlas\Telegram'

Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Remove-Item $RuntimeDir -Recurse -Force -ErrorAction SilentlyContinue

$processes = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -match '^pythonw?\.exe$' -and
    ($_.CommandLine -like '*run_telegram_supervisor.py*' -or $_.CommandLine -like '*run_telegram_bot.py*')
}
foreach ($process in $processes) {
    Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
}
Write-Host 'Inicio automático supervisado de Atlas Telegram eliminado.' -ForegroundColor Green
