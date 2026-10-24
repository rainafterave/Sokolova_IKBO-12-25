@echo off
setlocal
cd /d "%~dp0.."
call run.bat --help
if errorlevel 1 exit /b 1
call run.bat --stage 2 --headless --script scripts\stage2.txt
if errorlevel 1 exit /b 1
call run.bat --vfs vfs-samples\several.csv --headless --script scripts\list.txt
if errorlevel 1 exit /b 1
call run.bat --vfs vfs-samples\deep.csv --script scripts\stage4.txt --headless
if errorlevel 1 exit /b 1
call run.bat --vfs
if not errorlevel 1 exit /b 1
call run.bat --script
if not errorlevel 1 exit /b 1
call run.bat --unknown
if not errorlevel 1 exit /b 1
echo Configuration checks passed.
exit /b 0
