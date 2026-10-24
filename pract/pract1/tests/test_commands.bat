@echo off
setlocal
cd /d "%~dp0.."
call run.bat --vfs vfs-samples\deep.csv --script scripts\stage4.txt --headless
if errorlevel 1 exit /b 1
for %%S in (scripts\errors\*.txt) do (
    call run.bat --vfs vfs-samples\deep.csv --script "%%S" --headless
    if not errorlevel 1 exit /b 1
)
echo Command checks passed.
exit /b 0
