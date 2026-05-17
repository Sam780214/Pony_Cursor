@echo off
setlocal
echo ========================================
echo  Install pony CLI (opencode-cli)
echo ========================================
echo.

if not exist "D:\Pony\Pony_Cursor_repo\opencode\pyproject.toml" (
    echo [ERROR] Missing: D:\Pony\Pony_Cursor_repo\opencode
    echo.
    echo Run these commands ONE LINE AT A TIME in cmd:
    echo   cd /d D:\Pony
    echo   git clone https://github.com/Sam780214/Pony_Cursor.git Pony_Cursor_repo
    echo.
    pause
    exit /b 1
)

cd /d D:\Pony\Pony_Cursor_repo\opencode
if errorlevel 1 (
    echo [ERROR] Cannot cd to opencode folder
    pause
    exit /b 1
)
echo Current: %CD%
echo.

py -3 -m pip install -e .
if errorlevel 1 (
    python -m pip install -e .
)
if errorlevel 1 (
    echo [ERROR] pip install failed
    pause
    exit /b 1
)

echo.
echo [OK] Close this window. Open NEW cmd and run:
echo   pony help
echo   pony git --help
echo.
pause
exit /b 0