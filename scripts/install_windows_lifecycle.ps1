[CmdletBinding()]
param(
    [string]$TaskName = 'Proyecto Atlas - Ciclo de vida Windows'
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Listener = Join-Path $PSScriptRoot 'windows_shutdown_listener.py'
$Notifier = Join-Path $PSScriptRoot 'notify_telegram_shutdown.py'
$PythonPathFile = Join-Path $ProjectRoot 'data\integrations\telegram\python_path.txt'
$ListenerLock = Join-Path $ProjectRoot 'data\integrations\telegram\windows_shutdown_listener.lock'

if (-not (Test-Path $Listener)) { throw "No existe el listener: $Listener" }
if (-not (Test-Path $Notifier)) { throw "No existe el notificador: $Notifier" }

$PythonExe = $null
if (Test-Path $PythonPathFile) {
    $PythonExe = ([IO.File]::ReadAllText($PythonPathFile)).Trim()
}

if (-not $PythonExe -or -not (Test-Path $PythonExe)) {
    $PythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $PythonCommand) { $PythonCommand = Get-Command python -ErrorAction SilentlyContinue }
    if (-not $PythonCommand) { throw 'No se encontró Python.' }
    $PythonExe = $PythonCommand.Source
}

$PythonDirectory = Split-Path -Parent $PythonExe
$PythonwExe = Join-Path $PythonDirectory 'pythonw.exe'
$Executable = if (Test-Path $PythonwExe) { $PythonwExe } else { $PythonExe }
$Arguments = "`"$Listener`""

$Action = New-ScheduledTaskAction `
    -Execute $Executable `
    -Argument $Arguments `
    -WorkingDirectory $ProjectRoot

$Trigger = New-ScheduledTaskTrigger `
    -AtLogOn `
    -User "$env:USERDOMAIN\$env:USERNAME"

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -RestartCount 50 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -WakeToRun

$Principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Highest

$Task = New-ScheduledTask `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description 'Escucha apagado, reinicio, suspensión y reanudación de Windows y avisa por Telegram.'

Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Remove-Item $ListenerLock -Force -ErrorAction SilentlyContinue

Register-ScheduledTask -TaskName $TaskName -InputObject $Task -Force | Out-Null
Enable-ScheduledTask -TaskName $TaskName | Out-Null
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 3

Write-Host "Integración instalada: $TaskName" -ForegroundColor Green
Write-Host "Listener: $Listener"
Write-Host "Notificador: $Notifier"
Write-Host "Python: $Executable"

Get-ScheduledTask -TaskName $TaskName |
    Select-Object TaskName, State

Get-ScheduledTaskInfo -TaskName $TaskName |
    Select-Object LastRunTime, LastTaskResult, NextRunTime
