$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$processList = @(Get-CimInstance Win32_Process)
$owned = @($processList | Where-Object {
    ($_.Name -eq 'python.exe' -and $_.ExecutablePath -eq "$projectRoot\.venv\Scripts\python.exe" -and ($_.CommandLine -like '*uvicorn src.main:app*' -or $_.CommandLine -like '*celery -A src.worker.celery_app worker*')) -or
    ($_.Name -eq 'node.exe' -and $_.CommandLine -like "*$projectRoot\frontend\node_modules\vite\bin\vite.js*")
})
$ownedIds = @($owned | ForEach-Object { $_.ProcessId })
$children = @($processList | Where-Object { $_.ParentProcessId -in $ownedIds -and $_.Name -in @('python.exe', 'node.exe') })
foreach ($serviceProcess in @($children + $owned)) {
    Stop-Process -Id $serviceProcess.ProcessId -Force -ErrorAction SilentlyContinue
}
Write-Host '已停止本项目的本地服务。'
