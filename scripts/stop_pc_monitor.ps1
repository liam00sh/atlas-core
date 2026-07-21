Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*monitor_pc.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
