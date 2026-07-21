$TaskName = "Proyecto Atlas - Monitor PC"
Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false
& (Join-Path $PSScriptRoot "stop_pc_monitor.ps1")
Write-Host "Monitor de Atlas desinstalado."
