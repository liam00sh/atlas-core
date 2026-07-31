# Proyecto Atlas
# Instala una única tarea programada: "Proyecto Atlas".
# Ejecutar PowerShell como administrador.

$ErrorActionPreference = "Stop"

$ProjectRoot = "REDACTED_001b039044f8\04 - Python\atlas_core"
$PythonW = Join-Path $ProjectRoot ".venv\Scripts\pythonw.exe"
$Launcher = Join-Path $ProjectRoot "atlas_launcher.py"
$TaskName = "Proyecto Atlas"
$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

if (-not (Test-Path $PythonW)) {
    throw "No existe pythonw.exe en: $PythonW"
}

if (-not (Test-Path $Launcher)) {
    throw "No existe atlas_launcher.py en: $Launcher"
}

$Action = New-ScheduledTaskAction `
    -Execute $PythonW `
    -Argument "`"$Launcher`"" `
    -WorkingDirectory $ProjectRoot

# AtLogOn es obligatorio para que los widgets aparezcan en el escritorio.
# El launcher inicia inmediatamente todos los servicios y mantiene todo oculto.
$Trigger = New-ScheduledTaskTrigger `
    -AtLogOn `
    -User $CurrentUser

$Principal = New-ScheduledTaskPrincipal `
    -UserId $CurrentUser `
    -LogonType Interactive `
    -RunLevel Limited

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
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

Write-Host "Tarea instalada o actualizada: $TaskName"
Write-Host "Ejecutable: $PythonW"
Write-Host "Launcher: $Launcher"
