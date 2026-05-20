@echo off
cd /d "%~dp0"
echo Hi AI Web for Subtext: http://127.0.0.1:8765
python web_server.py
if errorlevel 1 pause
