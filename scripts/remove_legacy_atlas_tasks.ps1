# Elimina o deshabilita tareas antiguas sustituidas por "Proyecto Atlas".
# Ejecutar PowerShell como administrador.

$OldTasks = @(
    "Proyecto Atlas - Telegram",
    "Proyecto Atlas - Monitor PC",
    "Proyecto Atlas - Monitor RPI y Banner",
    "Proyecto Atlas - Avisos de ciclo de vida",
    "Proyecto Atlas - Ciclo de vida Windows",
    "Atlas - Telegram",
    "Atlas - Monitor PC",
    "Atlas - Monitor Raspberry",
    "Atlas - Banner"
)

foreach ($TaskName in $OldTasks) {
    $Task = Get-ScheduledTask `
        -TaskName $TaskName `
        -ErrorAction SilentlyContinue

    if ($null -ne $Task) {
        Stop-ScheduledTask `
            -TaskName $TaskName `
            -ErrorAction SilentlyContinue

        Unregister-ScheduledTask `
            -TaskName $TaskName `
            -Confirm:$false

        Write-Host "Eliminada tarea antigua: $TaskName"
    }
}

Write-Host "Limpieza terminada."
