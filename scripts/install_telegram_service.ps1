[CmdletBinding()]
param(
    [string]$TaskName = 'Proyecto Atlas - Telegram',
    [int]$DelaySeconds = 45
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EnvPath = Join-Path $ProjectRoot '.env'
$Supervisor = Join-Path $ProjectRoot 'scripts\run_telegram_supervisor.py'
$RuntimeDir = Join-Path $env:LOCALAPPDATA 'ProyectoAtlas\Telegram'
$Bootstrap = Join-Path $RuntimeDir 'telegram_bootstrap.py'
$BootstrapConfig = Join-Path $RuntimeDir 'bootstrap.json'
$BootstrapLog = Join-Path $RuntimeDir 'bootstrap.log'

if (-not (Test-Path $EnvPath)) { throw "Falta $EnvPath" }
if (-not (Test-Path $Supervisor)) { throw "Falta $Supervisor" }

$python = (Get-Command python.exe -ErrorAction SilentlyContinue)
if (-not $python) { $python = Get-Command python -ErrorAction SilentlyContinue }
if (-not $python) { throw 'No se encontró Python.' }
$pythonExe = $python.Source
$pythonwExe = Join-Path (Split-Path $pythonExe -Parent) 'pythonw.exe'
if (-not (Test-Path $pythonwExe)) { $pythonwExe = $pythonExe }

New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
$config = @{
    project_root = $ProjectRoot
    python_exe = $pythonExe
    supervisor = $Supervisor
    wait_minutes = 20
} | ConvertTo-Json
[IO.File]::WriteAllText($BootstrapConfig, $config, [Text.UTF8Encoding]::new($false))

$bootstrapCode = @'
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "bootstrap.json"
LOG = HERE / "bootstrap.log"

def log(text: str) -> None:
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write(time.strftime("%Y-%m-%dT%H:%M:%S ") + text + "\n")

try:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
except Exception as exc:
    log(f"Configuración inválida: {type(exc).__name__}")
    raise SystemExit(20)

root = Path(cfg["project_root"])
python_exe = Path(cfg["python_exe"])
supervisor = Path(cfg["supervisor"])
deadline = time.monotonic() + max(60, int(cfg.get("wait_minutes", 20)) * 60)
while not root.is_dir() or not supervisor.is_file() or not python_exe.is_file():
    if time.monotonic() >= deadline:
        log("Proyecto o Python no disponible tras la espera.")
        raise SystemExit(21)
    time.sleep(5)

log("Iniciando supervisor.")
completed = subprocess.run(
    [str(python_exe), str(supervisor)],
    cwd=str(root),
    stdin=subprocess.DEVNULL,
    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
)
log(f"Supervisor finalizado con código {completed.returncode}.")
raise SystemExit(completed.returncode)
'@
[IO.File]::WriteAllText($Bootstrap, $bootstrapCode, [Text.UTF8Encoding]::new($false))

& (Join-Path $PSScriptRoot 'stop_telegram_service.ps1') -TaskName $TaskName
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$arguments = "`"$Bootstrap`""
$action = New-ScheduledTaskAction -Execute $pythonwExe -Argument $arguments -WorkingDirectory $RuntimeDir
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
if ($DelaySeconds -gt 0) { $trigger.Delay = "PT${DelaySeconds}S" }
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -RestartCount 99 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited
$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Description 'Atlas Telegram residente, supervisado y multiusuario.'
Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 8
Write-Host "Servicio instalado y arrancado: $TaskName" -ForegroundColor Green
Write-Host "Bootstrap: $Bootstrap"
Write-Host "Registro: $BootstrapLog"
