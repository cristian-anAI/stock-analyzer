@echo off
echo ==========================================
echo PROBANDO MODELO LIBROS-TRADING:8B
echo ==========================================
echo.

echo Verificando que el modelo existe...
ollama list | findstr "libros-trading"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Modelo libros-trading:8b no encontrado
    pause
    exit /b 1
)

echo.
echo ✅ Modelo encontrado. Ejecutando pruebas...
echo.

echo ==========================================
echo PRUEBA 1: KELLY FORMULA
echo ==========================================
ollama run libros-trading:8b "¿Qué es la fórmula de Kelly y cómo se aplica al trading?"

echo.
echo ==========================================  
echo PRUEBA 2: ANALISIS DE SHORTS PERDEDORES
echo ==========================================
ollama run libros-trading:8b "¿Por qué mis SHORTs en HP, MOH, UNG están perdiendo? Mi threshold de compra es 6.0 y venta 4.5. ¿Qué dice Chan?"

echo.
echo ==========================================
echo PRUEBA 3: MEJORAS PRIORIZADAS
echo ==========================================
ollama run libros-trading:8b "Recomienda 3 mejoras específicas para mi autotrader basadas en la metodología de Chan"

echo.
echo ✅ PRUEBAS COMPLETADAS
pause