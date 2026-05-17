@echo off
chcp 65001 >nul
set "PONY_SOFTWARE=cmd"
pony git %*
