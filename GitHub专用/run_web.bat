@echo off
cd /d "%~dp0"
echo 正在停止旧版 Web 服务（端口 8765）...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8765" ^| findstr "LISTENING"') do (
  taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul
echo 启动 Hi AI Web（完整版，含 DeepSeek 与显示名）...
python web_server.py
if errorlevel 1 pause
