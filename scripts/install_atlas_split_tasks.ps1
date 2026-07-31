# Proyecto Atlas
# Instala dos tareas coordinadas en la sesión interactiva del usuario.
# Ejecutar PowerShell como administrador.

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$PythonW = Join-Path $ProjectRoot ".venv\Scripts\pythonw.exe"
$ServiceLauncher = Join-Path $ProjectRoot "atlas_service_launcher.py"
$DesktopLauncher = Join-Path $ProjectRoot "atlas_desktop_launcher.py"
$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

foreach ($Path in @($Python, $PythonW, $ServiceLauncher, $DesktopLauncher)) {
    if (-not (Test-Path $Path)) {
        throw "No existe: $Path"
    }
}

function Install-AtlasTask {
    param(
        [string]$TaskName,
        [string]$Executable,
        [string]$Arguments,
        [int]$DelaySeconds = 5
    )

    $Action = New-ScheduledTaskAction `
        -Execute $Executable `
        -Argument $Arguments `
        -WorkingDirectory $ProjectRoot

    $Trigger = New-ScheduledTaskTrigger `
        -AtLogOn `
        -User $CurrentUser

    if ($DelaySeconds -gt 0) {
        $Trigger.Delay = "PT${DelaySeconds}S"
    }

    $Principal = New-ScheduledTaskPrincipal `
        -UserId $CurrentUser `
        -LogonType Interactive `
        -RunLevel Limited

    $Settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RestartCount 10 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit ([TimeSpan]::Zero) `
        -MultipleInstances IgnoreNew

    $Task = New-ScheduledTask `
        -Action $Action `
        -Trigger $Trigger `
        -Principal $Principal `
        -Settings $Settings

    Register-ScheduledTask `
        -TaskName $TaskName `
        -InputObject $Task `
        -Force | Out-Null
}

# El launcher técnico ya inicia Atlas Core, Telegram, avisos y supervisor.
# Se ejecuta en la sesión del usuario porque el proyecto puede residir en una
# unidad montada por Google Drive, no disponible para SYSTEM.
Install-AtlasTask `
    -TaskName "Proyecto Atlas - Servicio" `
    -Executable $Python `
    -Arguments "`"$ServiceLauncher`"" `
    -DelaySeconds 5

# El launcher gráfico inicia monitor PC y widgets/banner.
Install-AtlasTask `
    -TaskName "Proyecto Atlas - Escritorio" `
    -Executable $PythonW `
    -Arguments "`"$DesktopLauncher`"" `
    -DelaySeconds 12

# Eliminar tareas antiguas que pueden duplicar procesos o arrancar en sesión 0.
$LegacyTasks = @(
    "Proyecto Atlas",
    "Proyecto Atlas - Telegram",
    "Proyecto Atlas - Avisos de ciclo de vida",
    "Proyecto Atlas - Monitor PC",
    "Proyecto Atlas - Monitor RPI y Banner"
)

foreach ($TaskName in $LegacyTasks) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
}

Start-ScheduledTask -TaskName "Proyecto Atlas - Servicio"
Start-Sleep -Seconds 8
Start-ScheduledTask -TaskName "Proyecto Atlas - Escritorio"

Write-Host ""
Write-Host "Tareas instaladas correctamente."
Write-Host "Telegram, avisos, supervisor y Atlas Core arrancarán al iniciar sesión."
Write-Host "El banner y el monitor de PC arrancarán unos segundos después."
