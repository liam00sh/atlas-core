Stop-ScheduledTask `
    -TaskName "Proyecto Atlas" `
    -ErrorAction SilentlyContinue

$StatusPath = "REDACTED_001b039044f8\04 - Python\atlas_core\data\launcher\launcher_status.json"

if (Test-Path $StatusPath) {
    try {
        $State = Get-Content $StatusPath -Raw | ConvertFrom-Json
        $Pid = [int]$State.launcher_pid
        if ($Pid -gt 0) {
            Stop-Process -Id $Pid -Force -ErrorAction SilentlyContinue
        }
    }
    catch {
    }
}

Write-Host "Proyecto Atlas detenido."
