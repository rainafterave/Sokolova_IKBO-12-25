@echo off
setlocal
cd /d "%~dp0.."
for %%S in (1 2 3 4 5) do (
    echo Stage %%S
    call run.bat --config configs\test.ini --stage %%S
    if errorlevel 1 exit /b 1
)
