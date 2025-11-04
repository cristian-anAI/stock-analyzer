@echo off
REM Run this script as ADMINISTRATOR to install the wake-up task

echo ============================================
echo Stock Analyzer - Wake Timer Installation
echo ============================================
echo.
echo This will configure your PC to wake at 2:30 PM CET (1 hour before US market open)
echo and ensure the backend API is running.
echo.

REM Check for administrator privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running as Administrator...
    echo.
) else (
    echo ERROR: This script requires administrator privileges!
    echo Please right-click this file and select "Run as Administrator"
    pause
    exit /b 1
)

REM Install the scheduled task
powershell -ExecutionPolicy Bypass -File "%~dp0market-wake-scheduler.ps1" -Install

echo.
echo ============================================
echo Next Steps:
echo ============================================
echo 1. Enable wake timers if disabled:
echo    powercfg /change standby-timeout-ac 0
echo.
echo 2. Verify your BIOS supports wake timers
echo    (Most modern PCs support this)
echo.
echo 3. Test by checking task status:
echo    powershell -File "%~dp0market-wake-scheduler.ps1" -Status
echo.
pause
