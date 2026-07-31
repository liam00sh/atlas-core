$Task = Get-ScheduledTask `
    -TaskName "Proyecto Atlas" `
    -ErrorAction SilentlyContinue

if ($null -eq $Task) {
    Write-Host "La tarea Proyecto Atlas no existe."
    exit 1
}

$Info = Get-ScheduledTaskInfo -TaskName "Proyecto Atlas"

[PSCustomObject]@{
    Tarea = $Task.TaskName
    Estado = $Task.State
    UltimaEjecucion = $Info.LastRunTime
    Resultado = $Info.LastTaskResult
    ProximaEjecucion = $Info.NextRunTime
} | Format-List

$StatusPath = Join-Path `
    "REDACTED_001b039044f8\04 - Python\atlas_core" `
    "data\launcher\launcher_status.json"

if (Test-Path $StatusPath) {
    Write-Host ""
    Write-Host "Estado del launcher:"
    Get-Content $StatusPath
}
