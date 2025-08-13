@echo off
echo ========================================
echo  INSTALANDO TRADING SERVER COMO SERVICIO
echo ========================================

echo.
echo 1. Creando tarea programada para inicio automático...

set TASK_NAME="TradingServer24x7"
set SCRIPT_PATH="%CD%\start_server.bat"

echo.
echo Eliminando tarea existente si existe...
schtasks /delete /tn %TASK_NAME% /f 2>nul

echo.
echo Creando nueva tarea programada...
schtasks /create /tn %TASK_NAME% /tr %SCRIPT_PATH% /sc onstart /ru "%USERNAME%" /rp

if errorlevel 1 (
    echo.
    echo ERROR: No se pudo crear la tarea programada.
    echo Ejecuta este script como Administrador.
    pause
    exit /b 1
)

echo.
echo 2. Creando acceso directo en Escritorio...
set DESKTOP=%USERPROFILE%\Desktop
set SHORTCUT=%DESKTOP%\Trading Server 24x7.lnk

powershell "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT%'); $Shortcut.TargetPath = '%SCRIPT_PATH%'; $Shortcut.WorkingDirectory = '%CD%'; $Shortcut.Description = 'Trading Server 24/7'; $Shortcut.Save()"

echo.
echo 3. Configurando carpeta de logs compartida...
net share TradingLogs="%CD%\logs" /grant:everyone,read 2>nul

echo.
echo ========================================
echo  INSTALACIÓN COMPLETADA!
echo ========================================
echo.
echo ✅ Servicio instalado: %TASK_NAME%
echo ✅ Se iniciará automáticamente al encender el PC
echo ✅ Acceso directo creado en Escritorio
echo ✅ Logs accesibles en red: \\%COMPUTERNAME%\TradingLogs
echo.
echo Para gestionar el servicio:
echo   - Iniciar: schtasks /run /tn %TASK_NAME%
echo   - Detener: taskkill /f /im python.exe
echo   - Eliminar: schtasks /delete /tn %TASK_NAME%
echo.
echo Web Dashboard: http://%COMPUTERNAME%:5000
echo               http://localhost:5000
echo.
pause