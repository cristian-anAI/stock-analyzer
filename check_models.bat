@echo off
echo Verificando modelos disponibles...
echo.

echo Modelos instalados localmente:
ollama list
echo.

echo Modelos Llama disponibles para descargar:
echo - llama3.1:8b
echo - llama3:8b  
echo - llama2:7b
echo - llama2:13b
echo.

echo Verificando si llama3.1:8b esta disponible...
ollama pull llama3.1:8b --help >nul 2>&1
if %ERRORLEVEL% eq 0 (
    echo llama3.1:8b esta disponible
) else (
    echo Verificando llama3:8b...
)

pause