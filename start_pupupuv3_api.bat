@echo off
echo ================================================================================
echo Starting PupupuV3 Standalone API Server
echo ================================================================================
echo.
echo This will start ONLY the PupupuV3 endpoints on port 8001
echo Main API (port 8000) will NOT be started
echo.
echo Press Ctrl+C to stop the server
echo.
echo ================================================================================

python run_pupupuv3_api.py

pause
