@echo off
setlocal
cd /d "%~dp0"
if defined PYTHON_EXE (
    "%PYTHON_EXE%" src\main.py %*
    exit /b
)
where py >nul 2>&1
if not errorlevel 1 (
    py -3 src\main.py %*
    exit /b
)
python src\main.py %*
