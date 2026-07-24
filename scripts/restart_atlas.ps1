[CmdletBinding()]
param(
    [string]$TelegramTaskName = 'Proyecto Atlas - Telegram',
    [int]$WaitBeforeStartSeconds = 4
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$StopTelegram = Join-Path $PSScriptRoot 'stop_telegram_service.ps1'
$MainScript = Join-Path $ProjectRoot 'main.py'
$PythonPathFile = Join-Path $ProjectRoot 'data\integrations\telegram\python_path.txt'

if (Test-Path $StopTelegram) {
    & $StopTelegram -TaskName $TelegramTaskName
}

Start-Sleep -Seconds ([Math]::Max(2, $WaitBeforeStartSeconds))

$python = $null
if (Test-Path $PythonPathFile) {
    $candidate = ([IO.File]::ReadAllText($PythonPathFile)).Trim()
    if ($candidate -and (Test-Path $candidate)) {
        $python = $candidate
    }
}
if (-not $python) {
    $command = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $command) {
        $command = Get-Command python -ErrorAction SilentlyContinue
    }
    if ($command) {
        $python = $command.Source
    }
}
if (-not $python) {
    throw 'No se encontró Python para reiniciar Atlas.'
}
if (-not (Test-Path $MainScript)) {
    throw "No se encontró main.py en $ProjectRoot"
}

# Arranca Atlas en una nueva consola visible.
Start-Process -FilePath $python -ArgumentList @($MainScript) -WorkingDirectory $ProjectRoot

# Reactiva la tarea del supervisor de Telegram después de iniciar Atlas.
Start-Sleep -Seconds 3
Start-ScheduledTask -TaskName $TelegramTaskName -ErrorAction SilentlyContinue
