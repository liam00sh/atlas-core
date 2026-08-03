[CmdletBinding()]
param(
    [string]$TaskName = 'Proyecto Atlas - Escritorio'
)

$ErrorActionPreference = 'Stop'

$task = Get-ScheduledTask `
    -TaskName $TaskName `
    -ErrorAction SilentlyContinue

if (-not $task) {
    throw "No existe la tarea: $TaskName"
}

Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 6

Get-ScheduledTask -TaskName $TaskName |
Select-Object TaskName, State
