@echo off
echo ===============================================
echo HABILITANDO ACCESO REMOTO AL DASHBOARD
echo ===============================================

echo.
echo 1. Creando regla de firewall para puerto 5000...
netsh advfirewall firewall add rule name="Trading Dashboard" dir=in action=allow protocol=TCP localport=5000

echo.
echo 2. Verificando que el servicio este corriendo...
netstat -an | findstr :5000

echo.
echo ===============================================
echo ACCESO REMOTO HABILITADO!
echo ===============================================
echo.
echo Desde tu movil/otro PC:
echo   URL: http://192.168.1.155:5000
echo.
echo Asegurate de que:
echo   - Ambos dispositivos esten en la misma WiFi
echo   - Tu portátil no se suspenda
echo   - El servidor de trading este funcionando
echo.
pause