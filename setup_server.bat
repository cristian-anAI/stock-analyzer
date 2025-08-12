@echo off
echo ===============================================
echo CONFIGURANDO PORTÁTIL COMO SERVIDOR 24/7
echo ===============================================

echo.
echo 1. Deshabilitando hibernación y suspensión...
powercfg -change -standby-timeout-ac 0
powercfg -change -standby-timeout-dc 0
powercfg -change -hibernate-timeout-ac 0
powercfg -change -hibernate-timeout-dc 0
powercfg -change -disk-timeout-ac 0
powercfg -change -disk-timeout-dc 0
powercfg -change -monitor-timeout-ac 0
powercfg -change -monitor-timeout-dc 0

echo.
echo 2. Configurando plan de energía de alto rendimiento...
powercfg -duplicatescheme 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
powercfg -setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c

echo.
echo 3. Deshabilitando Fast Startup (puede causar problemas)...
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Power" /v HiberbootEnabled /t REG_DWORD /d 0 /f

echo.
echo 4. Configurando Windows Update para no reiniciar automáticamente...
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU" /v NoAutoRebootWithLoggedOnUsers /t REG_DWORD /d 1 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU" /v AUOptions /t REG_DWORD /d 2 /f

echo.
echo 5. Deshabilitando protector de pantalla...
reg add "HKCU\Control Panel\Desktop" /v ScreenSaveActive /t REG_SZ /d 0 /f

echo.
echo ===============================================
echo CONFIGURACIÓN COMPLETADA!
echo Tu portátil ahora está optimizado para funcionar 24/7
echo ===============================================
pause