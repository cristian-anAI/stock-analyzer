@echo off
echo ========================================
echo    STOCK ANALYZER - 24/7 AUTOTRADER
echo ========================================
echo Starting autotrader in background...
echo The autotrader will keep running even if you close this window.
echo.

cd /d "%~dp0"

:: Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

:: Start the autotrader
python start_autotrader.py

echo.
echo Autotrader stopped.
pause