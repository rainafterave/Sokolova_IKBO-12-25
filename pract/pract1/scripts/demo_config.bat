@echo off
setlocal
cd /d "%~dp0.."
echo Close each emulator window to continue to the next configuration.
call run.bat
call run.bat --vfs vfs-samples\several.csv
call run.bat --script scripts\interactive.txt
call run.bat --vfs vfs-samples\deep.csv --script scripts\interactive.txt
