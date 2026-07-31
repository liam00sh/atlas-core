$ProjectRoot = Split-Path -Parent $PSScriptRoot
$StateDir = Join-Path $ProjectRoot "data\launcher"
$Monitoring = Join-Path $ProjectRoot "data\monitoring\supervisor_status.json"

Get-ScheduledTask `
    -TaskName "Proyecto Atlas - Servicio","Proyecto Atlas - Escritorio" `
    -ErrorAction SilentlyContinue |
    Select-Object TaskName, State

Write-Host ""
Get-ChildItem $StateDir -Filter "*status.json" -ErrorAction SilentlyContinue |
    ForEach-Object {
        Write-Host "=== $($_.Name) ==="
        Get-Content $_.FullName -Raw
    }

if (Test-Path $Monitoring) {
    Write-Host "=== supervisor_status.json ==="
    Get-Content $Monitoring -Raw
}
