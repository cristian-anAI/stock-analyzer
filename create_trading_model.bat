@echo off
echo ===========================================
echo CREANDO MODELO ESPECIALIZADO DE TRADING
echo ===========================================
echo.

REM Verificar que Ollama está instalado
ollama --version
if %ERRORLEVEL% neq 0 (
    echo ERROR: Ollama no encontrado. Por favor instala Ollama desde https://ollama.ai/
    pause
    exit /b 1
)

echo Ollama detectado correctamente.
echo.

REM Crear el modelo especializado
echo Creando modelo libros-trading:8b...
echo Esto puede tomar varios minutos...
echo.

ollama create libros-trading:8b -f books/Modelfile-libros-trading

if %ERRORLEVEL% eq 0 (
    echo.
    echo ========================================
    echo ✅ MODELO CREADO EXITOSAMENTE!
    echo ========================================
    echo.
    echo El modelo libros-trading:8b está listo para usar.
    echo.
    echo PRUEBAS RÁPIDAS:
    echo.
    echo 1. Prueba básica:
    echo    ollama run libros-trading:8b "¿Qué es la fórmula de Kelly?"
    echo.
    echo 2. Análisis de tu autotrader:
    echo    ollama run libros-trading:8b "¿Por qué mis SHORTs en HP, MOH, UNG están perdiendo?"
    echo.
    echo 3. Mejoras específicas:
    echo    ollama run libros-trading:8b "Recomienda 3 mejoras para mi autotrader basadas en Chan"
    echo.
) else (
    echo.
    echo ❌ ERROR: Falló la creación del modelo
    echo Verifica que el archivo books/Modelfile-libros-trading existe
    echo y que Ollama está funcionando correctamente.
)

echo.
pause