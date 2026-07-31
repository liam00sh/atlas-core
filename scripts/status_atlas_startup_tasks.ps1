$names = @(
    "Proyecto Atlas - Telegram",
    "Proyecto Atlas - Avisos de ciclo de vida",
    "Proyecto Atlas - Monitor PC",
    "Proyecto Atlas - Monitor RPI y Banner"
)

Get-ScheduledTask |
    Where-Object { $names -contains $_.TaskName } |
    ForEach-Object {
        $info = Get-ScheduledTaskInfo -TaskName $_.TaskName
        [PSCustomObject]@{
            Tarea = $_.TaskName
            Estado = $_.State
            UltimaEjecucion = $info.LastRunTime
            Resultado = $info.LastTaskResult
            ProximaEjecucion = $info.NextRunTime
        }
    } |
    Format-Table -AutoSize
