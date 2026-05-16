@echo off
cd /d "%~dp0"
py -3w pet.py 2>nul && exit /b 0
pythonw pet.py 2>nul && exit /b 0
echo 未找到 py/pythonw，请安装 Python 或将 python 加入 PATH。
pause
