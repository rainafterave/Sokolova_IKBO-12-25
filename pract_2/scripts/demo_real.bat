@echo off
setlocal
cd /d "%~dp0.."
for %%C in (csv regex serde_json) do (
    call run.bat --config configs\%%C.ini --output output\%%C.puml --svg output\%%C.svg
    if errorlevel 1 exit /b 1
)
echo Diagrams saved in output.
