# Proyecto Atlas
# Instala o actualiza las tareas de inicio automático de Windows.
# Ejecutar PowerShell como administrador.

$ErrorActionPreference = "Stop"

$ProjectRoot = "REDACTED_001b039044f8\04 - Python\atlas_core"
$PythonW = "REDACTED_001b039044f8\04 - Python\atlas_core\.venv\Scripts\pythonw.exe"
$Python = "REDACTED_001b039044f8\04 - Python\atlas_core\.venv\Scripts\python.exe"
$UserId = "$env:USERDOMAIN\$env:USERNAME"

function New-AtlasTask {
    param(
        [string]$TaskName,
        [string]$Executable,
        [string]$Arguments,
        [ValidateSet("AtStartup","AtLogOn")]
        [string]$TriggerType,
        [switch]$Interactive
    )

    $action = New-ScheduledTaskAction `
        -Execute $Executable `
        -Argument $Arguments `
        -WorkingDirectory $ProjectRoot

    if ($TriggerType -eq "AtStartup") {
        $trigger = New-ScheduledTaskTrigger -AtStartup
    }
    else {
        $trigger = New-ScheduledTaskTrigger -AtLogOn -User $UserId
    }

    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit ([TimeSpan]::Zero) `
        -MultipleInstances IgnoreNew

    if ($Interactive) {
        $principal = New-ScheduledTaskPrincipal `
            -UserId $UserId `
            -LogonType Interactive `
            -RunLevel Limited
    }
    else {
        $principal = New-ScheduledTaskPrincipal `
            -UserId "SYSTEM" `
            -LogonType ServiceAccount `
            -RunLevel Highest
    }

    $task = New-ScheduledTask `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal

    Register-ScheduledTask `
        -TaskName $TaskName `
        -InputObject $task `
        -Force | Out-Null

    Write-Host "Tarea instalada: $TaskName"
}

# Procesos técnicos: pueden arrancar antes del inicio de sesión.
New-AtlasTask `
    -TaskName "Proyecto Atlas - Telegram" `
    -Executable $Python `
    -Arguments "scripts\run_telegram_supervisor.py" `
    -TriggerType AtStartup

New-AtlasTask `
    -TaskName "Proyecto Atlas - Avisos de ciclo de vida" `
    -Executable $Python `
    -Arguments "scripts\windows_shutdown_listener.py" `
    -TriggerType AtStartup

# Procesos con interfaz gráfica: deben arrancar en sesión interactiva.
# Windows no muestra widgets del escritorio iniciados en la sesión 0/SYSTEM.
New-AtlasTask `
    -TaskName "Proyecto Atlas - Monitor PC" `
    -Executable $PythonW `
    -Arguments "scripts\monitor_pc.py" `
    -TriggerType AtLogOn `
    -Interactive

New-AtlasTask `
    -TaskName "Proyecto Atlas - Monitor RPI y Banner" `
    -Executable $PythonW `
    -Arguments "-m monitoring.desktop_widgets" `
    -TriggerType AtLogOn `
    -Interactive

Write-Host ""
Write-Host "Tareas de Atlas instaladas o actualizadas."
Write-Host "Telegram y avisos arrancan con Windows."
Write-Host "Los monitores y el banner arrancan al iniciar sesión."
