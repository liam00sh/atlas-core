[CmdletBinding()]
param(
    [string]$TaskName = 'Proyecto Atlas - Escritorio',
    [int]$DelaySeconds = 20
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Launcher = Join-Path $ProjectRoot 'atlas_desktop_launcher.py'

if (-not (Test-Path $Launcher)) {
    throw "No existe el lanzador grafico: $Launcher"
}

$pythonw = Join-Path $ProjectRoot '.venv\Scripts\pythonw.exe'

if (-not (Test-Path $pythonw)) {
    $command = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($command) {
        $pythonw = $command.Source
    }
}

if (-not $pythonw -or -not (Test-Path $pythonw)) {
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $python) {
        $python = Get-Command python -ErrorAction SilentlyContinue
    }
    if (-not $python) {
        throw 'No se encontro Python para el escritorio de Atlas.'
    }
    $pythonw = $python.Source
}

# El launcher grafico sustituye a la tarea separada Monitor PC.
foreach ($legacyName in @(
    'Proyecto Atlas - Monitor PC',
    'Proyecto Atlas - Escritorio',
    $TaskName
)) {
    Stop-ScheduledTask `
        -TaskName $legacyName `
        -ErrorAction SilentlyContinue

    Unregister-ScheduledTask `
        -TaskName $legacyName `
        -Confirm:$false `
        -ErrorAction SilentlyContinue
}

# Detiene instancias graficas antiguas antes de registrar la nueva.
Get-CimInstance Win32_Process |
Where-Object {
    $_.CommandLine -and (
        $_.CommandLine -match 'atlas_desktop_launcher.py' -or
        $_.CommandLine -match 'monitor_pc.py' -or
        $_.CommandLine -match 'monitoring.desktop_widgets'
    )
} |
ForEach-Object {
    Stop-Process `
        -Id $_.ProcessId `
        -Force `
        -ErrorAction SilentlyContinue
}

Remove-Item `
    (Join-Path $ProjectRoot 'data\launcher\atlas_desktop_launcher.lock') `
    -Force `
    -ErrorAction SilentlyContinue

$arguments = "`"$Launcher`""

$action = New-ScheduledTaskAction `
    -Execute $pythonw `
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
    -RestartCount 20 `
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
    -Description (
        'Lanzador grafico de Atlas: monitor PC, monitor Raspberry y banner.'
    )

Register-ScheduledTask `
    -TaskName $TaskName `
    -InputObject $task `
    -Force | Out-Null

Enable-ScheduledTask -TaskName $TaskName | Out-Null
Start-ScheduledTask -TaskName $TaskName

Start-Sleep -Seconds 8

Write-Host 'Escritorio de Atlas instalado e iniciado.' -ForegroundColor Green

Get-ScheduledTask -TaskName $TaskName |
Select-Object TaskName, State
