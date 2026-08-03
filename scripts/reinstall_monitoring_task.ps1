[CmdletBinding()]
param(
    [string]$TaskName = 'Proyecto Atlas - Monitorizacion',
    [int]$DelaySeconds = 60
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Launcher = Join-Path $ProjectRoot 'scripts\run_monitoring_background.ps1'

Get-ScheduledTask |
Where-Object {
    $_.TaskName -like 'Proyecto Atlas - Monitor*'
} |
ForEach-Object {
    Stop-ScheduledTask `
        -TaskName $_.TaskName `
        -ErrorAction SilentlyContinue

    Unregister-ScheduledTask `
        -TaskName $_.TaskName `
        -Confirm:$false `
        -ErrorAction SilentlyContinue
}

$arguments = (
    '-NoProfile -ExecutionPolicy Bypass ' +
    "-WindowStyle Hidden -File `"$Launcher`""
)

$action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument $arguments `
    -WorkingDirectory $ProjectRoot

$trigger = New-ScheduledTaskTrigger `
    -AtLogOn `
    -User $env:USERNAME

if ($DelaySeconds -gt 0) {
    $trigger.Delay = "PT${DelaySeconds}S"
}

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -RestartCount 50 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

$task = New-ScheduledTask `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description 'Monitorizacion residente de Atlas desde C:\Proyectos\Atlas\atlas_core.'

Register-ScheduledTask `
    -TaskName $TaskName `
    -InputObject $task `
    -Force | Out-Null

Enable-ScheduledTask -TaskName $TaskName | Out-Null
Start-ScheduledTask -TaskName $TaskName

Start-Sleep -Seconds 6

Get-ScheduledTask -TaskName $TaskName |
Select-Object TaskName, State

Get-ScheduledTaskInfo -TaskName $TaskName |
Select-Object LastRunTime, LastTaskResult, NextRunTime
