[CmdletBinding()]

param(
    [string]$TaskName = 'Proyecto Atlas - Telegram',
    [int]$DelaySeconds = 45,
    [int]$WatchdogMinutes = 5
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EnvPath = Join-Path $ProjectRoot '.env'
$ProjectLauncher = Join-Path $ProjectRoot 'scripts\start_telegram_background.ps1'
$Supervisor = Join-Path $ProjectRoot 'scripts\run_telegram_supervisor.py'
$RuntimeDir = Join-Path $env:LOCALAPPDATA 'ProyectoAtlas\Telegram'
$Bootstrap = Join-Path $RuntimeDir 'telegram_bootstrap.ps1'
$PythonDir = Join-Path $ProjectRoot 'data\integrations\telegram'
$PythonPathFile = Join-Path $PythonDir 'python_path.txt'

if (-not (Test-Path $EnvPath)) {
    throw "Falta $EnvPath. Ejecuta primero scripts\configure_telegram_env.ps1"
}

if (-not (Test-Path $ProjectLauncher)) {
    throw "No existe el lanzador: $ProjectLauncher"
}

if (-not (Test-Path $Supervisor)) {
    throw "No existe el supervisor: $Supervisor"
}

$pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue

if (-not $pythonCommand) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
}

if (-not $pythonCommand) {
    throw 'No se encontró Python en PATH.'
}

New-Item -ItemType Directory -Force -Path $PythonDir | Out-Null

[IO.File]::WriteAllText(
    $PythonPathFile,
    $pythonCommand.Source,
    [Text.UTF8Encoding]::new($false)
)

New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

$escapedLauncher = $ProjectLauncher.Replace("'", "''")

# IMPORTANTE:
# La llamada al PowerShell secundario debe escribirse en una sola línea.
# La versión anterior generaba varias líneas sin acentos graves y terminaba
# abriendo una consola de PowerShell vacía sin ejecutar el lanzador.
$bootstrapContent = @"
`$ErrorActionPreference = 'Stop'
`$launcher = '$escapedLauncher'
`$deadline = (Get-Date).AddMinutes(30)

while (-not (Test-Path `$launcher)) {
    if ((Get-Date) -ge `$deadline) {
        exit 20
    }

    Start-Sleep -Seconds 5
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "`$launcher"
exit `$LASTEXITCODE
"@

[IO.File]::WriteAllText(
    $Bootstrap,
    $bootstrapContent,
    [Text.UTF8Encoding]::new($false)
)

$arguments = (
    "-NoProfile -ExecutionPolicy Bypass " +
    "-WindowStyle Hidden -File `"$Bootstrap`""
)

$action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument $arguments `
    -WorkingDirectory $RuntimeDir

$logonTrigger = New-ScheduledTaskTrigger `
    -AtLogOn `
    -User $env:USERNAME

if ($DelaySeconds -gt 0) {
    $logonTrigger.Delay = "PT${DelaySeconds}S"
}

$watchdogStart = (Get-Date).AddMinutes(1)

$watchdogTrigger = New-ScheduledTaskTrigger `
    -Once `
    -At $watchdogStart `
    -RepetitionInterval (
        New-TimeSpan -Minutes (
            [Math]::Max(1, $WatchdogMinutes)
        )
    ) `
    -RepetitionDuration (
        New-TimeSpan -Days 3650
    )

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
    -Trigger @($logonTrigger, $watchdogTrigger) `
    -Settings $settings `
    -Principal $principal `
    -Description (
        'Supervisor residente de Atlas Telegram con arranque ' +
        'al iniciar sesión, watchdog y reinicio automático.'
    )

Stop-ScheduledTask `
    -TaskName $TaskName `
    -ErrorAction SilentlyContinue

Unregister-ScheduledTask `
    -TaskName $TaskName `
    -Confirm:$false `
    -ErrorAction SilentlyContinue

Remove-Item (
    Join-Path $ProjectRoot 'data\integrations\telegram\supervisor.lock'
) -Force -ErrorAction SilentlyContinue

Remove-Item (
    Join-Path $ProjectRoot 'data\integrations\telegram\polling.lock'
) -Force -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName $TaskName `
    -InputObject $task `
    -Force | Out-Null

Enable-ScheduledTask `
    -TaskName $TaskName | Out-Null

Start-ScheduledTask `
    -TaskName $TaskName

Start-Sleep -Seconds 8

Write-Host "Tarea instalada y arrancada: $TaskName" -ForegroundColor Green
Write-Host (
    "Se iniciará ${DelaySeconds}s después de entrar en Windows " +
    "y el watchdog comprobará cada ${WatchdogMinutes} min."
)
Write-Host 'El proceso es independiente de esta terminal.'

Get-ScheduledTask `
    -TaskName $TaskName |
    Select-Object TaskName, State

Get-ScheduledTaskInfo `
    -TaskName $TaskName |
    Select-Object LastRunTime, LastTaskResult, NextRunTime
