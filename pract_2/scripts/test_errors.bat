@echo off
setlocal
cd /d "%~dp0.."
for %%C in (configs\errors\*.ini) do (
    call run.bat --config "%%C" --stage 3
    if not errorlevel 1 exit /b 1
)
echo Error checks passed.
exit /b 0
