@echo off
setlocal
cd /d "%~dp0"
py -3 install_helper.py 2>nul || python install_helper.py
if errorlevel 1 pause
