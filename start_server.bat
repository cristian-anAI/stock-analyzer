@echo off
title Trading Server 24/7
color 0A

echo ========================================
echo  TRADING SERVER 24/7 - INICIANDO
echo ========================================
echo.

cd /d "C:\Users\Cristian\Downloads\stock-analyzer-main\stock-analyzer-main"

echo Verificando Python...
python --version
if errorlevel 1 (
    echo ERROR: Python no encontrado
    pause
    exit /b 1
)

echo.
echo Instalando Flask para web monitor...
pip install flask

echo.
echo ========================================
echo  INICIANDO SERVICIOS
echo ========================================

echo.
echo 1. Iniciando Web Monitor en puerto 5000...
start "Web Monitor" cmd /k python web_monitor.py

echo.
echo 2. Esperando 3 segundos...
timeout /t 3 /nobreak

echo.
echo 3. Iniciando Trading Server...
echo    - Para detener: Ctrl+C
echo    - Web Dashboard: http://localhost:5000
echo    - Logs en: ./logs/
echo ========================================

python server_trader.py

echo.
echo Trading server detenido.
pause