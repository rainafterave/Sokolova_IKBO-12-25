@echo off
setlocal
cd /d "%~dp0.."
echo Inspect each VFS and enter exit to continue.
call run.bat --stage 3 --vfs vfs-samples\minimal.csv
call run.bat --stage 3 --vfs vfs-samples\several.csv
call run.bat --stage 3 --vfs vfs-samples\deep.csv
