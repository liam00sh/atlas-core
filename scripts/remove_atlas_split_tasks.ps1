$Names = @(
    "Proyecto Atlas - Servicio",
    "Proyecto Atlas - Escritorio"
)

foreach ($Name in $Names) {
    if (
        Get-ScheduledTask `
            -TaskName $Name `
            -ErrorAction SilentlyContinue
    ) {
        Stop-ScheduledTask `
            -TaskName $Name `
            -ErrorAction SilentlyContinue

        Unregister-ScheduledTask `
            -TaskName $Name `
            -Confirm:$false

        Write-Host "Eliminada: $Name"
    }
}
