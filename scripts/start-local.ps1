$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$vitePath = Join-Path $projectRoot 'frontend\node_modules\vite\bin\vite.js'
if (!(Test-Path -LiteralPath $pythonPath) -or !(Test-Path -LiteralPath $vitePath)) {
    throw '请先按 README.md 的使用说明安装项目依赖。'
}
& (Join-Path $PSScriptRoot 'stop-local.ps1')
foreach ($port in @(8001, 5173)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "端口 $port 被其他进程占用，请先处理占用后再启动。"
    }
}
$logPath = Join-Path $projectRoot 'logs'
New-Item -ItemType Directory -Force -Path $logPath | Out-Null
Start-Process -FilePath $pythonPath -ArgumentList '-m uvicorn src.main:app --host 127.0.0.1 --port 8001' -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput "$logPath\backend.log" -RedirectStandardError "$logPath\backend-error.log"
Start-Process -FilePath (Get-Command node).Source -ArgumentList ('"' + $vitePath + '" --host 127.0.0.1 --strictPort') -WorkingDirectory "$projectRoot\frontend" -WindowStyle Hidden -RedirectStandardOutput "$logPath\frontend.log" -RedirectStandardError "$logPath\frontend-error.log"
Start-Process -FilePath $pythonPath -ArgumentList '-m celery -A src.worker.celery_app worker --loglevel=info -P solo --without-gossip --without-mingle --without-heartbeat' -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput "$logPath\worker.log" -RedirectStandardError "$logPath\worker-error.log"
Write-Host '服务已启动。页面：http://127.0.0.1:5173  API：http://127.0.0.1:8001/docs'
Write-Host '启动日志保存在 logs/。'
