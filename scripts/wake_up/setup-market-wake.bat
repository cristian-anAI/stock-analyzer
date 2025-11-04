@echo off
REM Setup Market Wake Scheduler - Run as Administrator

echo ================================================
echo  Stock Analyzer - Market Wake Setup
echo ================================================
echo.

REM Check for admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must be run as Administrator!
    echo Right-click and select "Run as Administrator"
    echo.
    pause
    exit /b 1
)

echo Installing scheduled task...
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0market-wake-scheduler.ps1" -Install

echo.
echo ================================================
echo  Setup Complete!
echo ================================================
echo.
echo Your PC will now wake at 2:30 PM CET (14:30) daily
echo to prepare for US market open at 3:30 PM CET (9:30 AM EST)
echo.
echo IMPORTANT NEXT STEPS:
echo 1. Verify wake timers are enabled:
echo    powercfg /query SCHEME_CURRENT SUB_SLEEP RTCWAKE
echo.
echo 2. Update backend path in backend-health-check.ps1 if needed
echo    Default: c:\repos\stock-analyzer-backend
echo.
echo 3. Check BIOS settings support wake timers
echo.
echo To check status: .\market-wake-scheduler.ps1 -Status
echo To uninstall: .\market-wake-scheduler.ps1 -Uninstall
echo.
pause
