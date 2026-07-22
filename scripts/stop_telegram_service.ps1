[CmdletBinding()]

param(
    [string]$TaskName = 'Proyecto Atlas - Telegram'
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$NotifyScript = Join-Path $PSScriptRoot 'notify_telegram_shutdown.py'
$PythonPathFile = Join-Path $ProjectRoot 'data\integrations\telegram\python_path.txt'

if (Test-Path $NotifyScript) {
    $PythonExe = $null

    if (Test-Path $PythonPathFile) {
        $PythonExe = (
            [IO.File]::ReadAllText($PythonPathFile)
        ).Trim()
    }

    if (-not $PythonExe -or -not (Test-Path $PythonExe)) {
        $PythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue

        if (-not $PythonCommand) {
            $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
        }

        if ($PythonCommand) {
            $PythonExe = $PythonCommand.Source
        }
    }

    if ($PythonExe) {
        & $PythonExe $NotifyScript
        Start-Sleep -Milliseconds 1200
    } else {
        Write-Warning (
            'No se encontró Python; no se pudo enviar ' +
            'el aviso de apagado.'
        )
    }
}

Stop-ScheduledTask `
    -TaskName $TaskName `
    -ErrorAction SilentlyContinue

Start-Sleep -Seconds 2

$processes = Get-CimInstance Win32_Process `
    -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -match '^pythonw?\.exe$' -and (
            $_.CommandLine -like '*telegram_bootstrap.py*' -or
            $_.CommandLine -like '*run_telegram_supervisor.py*' -or
            $_.CommandLine -like '*run_telegram_bot.py*'
        )
    }

$ordered = $processes |
    Sort-Object @{
        Expression = {
            if (
                $_.CommandLine -like '*run_telegram_bot.py*'
            ) {
                0
            } elseif (
                $_.CommandLine -like '*run_telegram_supervisor.py*'
            ) {
                1
            } else {
                2
            }
        }
    }

foreach ($process in $ordered) {
    Stop-Process `
        -Id $process.ProcessId `
        -Force `
        -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2

Remove-Item (
    Join-Path $ProjectRoot 'data\integrations\telegram\polling.lock'
) -Force -ErrorAction SilentlyContinue

Remove-Item (
    Join-Path $ProjectRoot 'data\integrations\telegram\supervisor.lock'
) -Force -ErrorAction SilentlyContinue

Write-Host (
    'Atlas Telegram detenido completamente.'
) -ForegroundColor Yellow
