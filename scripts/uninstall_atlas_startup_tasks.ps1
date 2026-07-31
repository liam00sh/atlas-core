$names = @(
    "Proyecto Atlas - Telegram",
    "Proyecto Atlas - Avisos de ciclo de vida",
    "Proyecto Atlas - Monitor PC",
    "Proyecto Atlas - Monitor RPI y Banner"
)

foreach ($name in $names) {
    if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $name -Confirm:$false
        Write-Host "Eliminada: $name"
    }
}
