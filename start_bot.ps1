# Запуск VEORA Music Bot и Cloudflare Tunnel
Set-Location $PSScriptRoot
Write-Host "🚀 Запуск Cloudflare Tunnel для HTTPS Mini App..." -ForegroundColor Cyan
Start-Process -FilePath ".\cloudflared.exe" -ArgumentList "tunnel --url http://localhost:8000" -WindowStyle Minimized

Write-Host "🤖 Запуск VEORA Telegram Bot & FastAPI сервера..." -ForegroundColor Green
& ".\.venv\Scripts\python.exe" -m src.main
