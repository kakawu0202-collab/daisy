# Yumin 开机自启 — 三服务拉起 + 防双进程（端口占用则跳过）
# 线上 Portal 5050 / dev Portal 5051 / AI Assistant 5099
# 由 Startup 文件夹的 Yumin-AutoStart.vbs 隐藏调用；也可手动运行本脚本

function Test-Port($port) {
    $hit = netstat -ano | Select-String (":$port\s.*LISTENING")
    return [bool]$hit
}

if (-not (Test-Port 5050)) {
    Start-Process python -ArgumentList 'main.py' -WorkingDirectory 'd:\workspace\850-scos\portal' -WindowStyle Hidden
    Write-Host 'Started: 线上 Portal (5050)'
} else { Write-Host 'Skipped: 5050 已在运行' }

if (-not (Test-Port 5051)) {
    $env:SCOS_PORTAL_PORT = '5051'
    Start-Process python -ArgumentList 'main.py' -WorkingDirectory 'd:\workspace\850-scos-dev\portal' -WindowStyle Hidden
    Write-Host 'Started: dev Portal (5051)'
} else { Write-Host 'Skipped: 5051 已在运行' }

if (-not (Test-Port 5099)) {
    Start-Process python -ArgumentList 'web.py' -WorkingDirectory 'd:\workspace\850-scos-dev\ai-engine' -WindowStyle Hidden
    Write-Host 'Started: AI Assistant (5099)'
} else { Write-Host 'Skipped: 5099 已在运行' }
