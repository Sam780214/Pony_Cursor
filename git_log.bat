@echo off
if not exist "D:\Pony\Pony_Cursor_repo\.git" (
    echo [ERROR] Missing D:\Pony\Pony_Cursor_repo
    echo Run install_pony.bat after git clone
    pause
    exit /b 1
)
cd /d D:\Pony\Pony_Cursor_repo
git log -1 --oneline
pause