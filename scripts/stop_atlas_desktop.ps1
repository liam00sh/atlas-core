[CmdletBinding()]
param(
    [string]$TaskName = 'Proyecto Atlas - Escritorio'
)

$ErrorActionPreference = 'Continue'

Stop-ScheduledTask `
    -TaskName $TaskName `
    -ErrorAction SilentlyContinue

Get-CimInstance Win32_Process |
Where-Object {
    $_.CommandLine -and (
        $_.CommandLine -match 'atlas_desktop_launcher.py' -or
        $_.CommandLine -match 'monitor_pc.py' -or
        $_.CommandLine -match 'monitoring.desktop_widgets'
    )
} |
ForEach-Object {
    Stop-Process `
        -Id $_.ProcessId `
        -Force `
        -ErrorAction SilentlyContinue
}

Write-Host 'Escritorio de Atlas detenido.' -ForegroundColor Yellow
