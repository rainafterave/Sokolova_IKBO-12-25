@echo off
setlocal
cd /d "%~dp0.."
for %%V in (minimal several deep) do (
    call run.bat --vfs vfs-samples\%%V.csv --script scripts\list.txt --headless
    if errorlevel 1 exit /b 1
)
call run.bat --stage 3 --vfs vfs-samples\deep.csv --script scripts\stage3.txt --headless
if errorlevel 1 exit /b 1
call run.bat --vfs vfs-samples\missing.csv --script scripts\list.txt --headless
if not errorlevel 1 exit /b 1
echo VFS checks passed.
exit /b 0
