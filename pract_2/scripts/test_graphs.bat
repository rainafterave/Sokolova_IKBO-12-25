@echo off
setlocal
cd /d "%~dp0.."
for %%C in (test depth filter cycle) do (
    call run.bat --config configs\%%C.ini --stage 3
    if errorlevel 1 exit /b 1
)
call run.bat --config configs\test.ini --stage 4
if errorlevel 1 exit /b 1
call run.bat --config configs\cycle.ini --stage 4
if not errorlevel 1 exit /b 1
echo Graph checks passed.
exit /b 0
