@echo off
REM PyInstaller: keep on ONE line. Using ^ line-continuation can break; then "clean" runs as a wrong command.
cd /d "%~dp0"
chcp 65001 >nul

set "PY=py -3"
where py >nul 2>nul || set "PY=python"

echo [1/4] install deps...
%PY% -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo pip failed.
    pause
    exit /b 1
)

set "OUT=%~dp0..\local-only\desktop-pet"
if not exist "%OUT%\dist" mkdir "%OUT%\dist"
if not exist "%OUT%\build" mkdir "%OUT%\build"

echo [2/4] PyInstaller...
%PY% -m PyInstaller --noconfirm --clean --windowed --onedir --name DesktopPet --distpath "%OUT%\dist" --workpath "%OUT%\build" --hidden-import=pystray._win32 --hidden-import=PIL._imaging pet.py
if errorlevel 1 (
    echo PyInstaller failed. Run: %PY% -m pip install pyinstaller
    pause
    exit /b 1
)

echo [3/4] copy config...
if exist "software_modes.txt" copy /Y "software_modes.txt" "%OUT%\dist\DesktopPet\" >nul
if exist "..\open_programs.bat" copy /Y "..\open_programs.bat" "%OUT%\dist\DesktopPet\" >nul

echo [4/4] sync desktop folder...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0sync_desktop.ps1"
if errorlevel 1 (
    echo sync_desktop.ps1 failed.
    pause
    exit /b 1
)

echo.
echo Done. %OUT%\dist\DesktopPet\
echo.
pause
