@echo off
REM Build script wrapper for Windows
REM Calls the PowerShell build script

echo Running PowerShell build script...
powershell -ExecutionPolicy Bypass -File "%~dp0build.ps1"

if errorlevel 1 (
    echo.
    echo Build failed!
    pause
    exit /b 1
)

echo.
pause
