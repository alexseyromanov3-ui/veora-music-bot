@echo off
cd /d "%~dp0"

echo ===================================================
echo           VEORA Music Bot Launcher
echo ===================================================
echo.

:: Free port 8000 if already occupied by an old process
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo Freeing port 8000 (PID %%a)...
    taskkill /f /pid %%a >nul 2>&1
)

echo [1/2] Starting Cloudflare Tunnel...
start "Cloudflare Tunnel" cmd /c ".\cloudflared.exe tunnel --url http://localhost:8000"

echo [2/2] Starting VEORA Bot and Server...
.\.venv\Scripts\python.exe -m src.main

pause
