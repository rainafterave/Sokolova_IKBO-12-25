@echo off
cd /d "%~dp0"
py -3 "src\main.py" %*
pause