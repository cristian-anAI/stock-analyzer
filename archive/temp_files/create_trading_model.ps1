# SCRIPT PARA CREAR MODELO ESPECIALIZADO DE TRADING
# Basado en "Quantitative Trading" de Ernie Chan

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "CREANDO MODELO ESPECIALIZADO DE TRADING" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar que Ollama está instalado
Write-Host "Verificando instalación de Ollama..." -ForegroundColor Yellow
try {
    $ollamaVersion = & ollama --version
    Write-Host "✅ Ollama encontrado: $ollamaVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ ERROR: Ollama no encontrado" -ForegroundColor Red
    Write-Host "Por favor instala Ollama desde https://ollama.ai/" -ForegroundColor Red
    Read-Host "Presiona Enter para salir"
    exit 1
}

# Verificar que el Modelfile existe
$modelfilePath = "books/Modelfile-libros-trading"
if (-not (Test-Path $modelfilePath)) {
    Write-Host "❌ ERROR: No se encontró $modelfilePath" -ForegroundColor Red
    Read-Host "Presiona Enter para salir"
    exit 1
}

Write-Host "✅ Modelfile encontrado: $modelfilePath" -ForegroundColor Green
Write-Host ""

# Crear el modelo
Write-Host "🔧 Creando modelo libros-trading:8b..." -ForegroundColor Yellow
Write-Host "⏳ Esto puede tomar varios minutos (descargando llama3.2:8b si es necesario)..." -ForegroundColor Yellow
Write-Host ""

try {
    & ollama create libros-trading:8b -f $modelfilePath
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "✅ MODELO CREADO EXITOSAMENTE!" -ForegroundColor Green  
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        
        Write-Host "🧠 El modelo libros-trading:8b está listo para usar." -ForegroundColor Cyan
        Write-Host ""
        
        Write-Host "📋 PRUEBAS RECOMENDADAS:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "1. 🔍 Prueba básica:" -ForegroundColor White
        Write-Host '   ollama run libros-trading:8b "¿Qué es la fórmula de Kelly y cómo aplicarla?"' -ForegroundColor Gray
        Write-Host ""
        
        Write-Host "2. 🎯 Análisis de tu autotrader:" -ForegroundColor White  
        Write-Host '   ollama run libros-trading:8b "¿Por qué mis SHORTs en HP, MOH, UNG están perdiendo según Chan?"' -ForegroundColor Gray
        Write-Host ""
        
        Write-Host "3. ⚡ Mejoras específicas:" -ForegroundColor White
        Write-Host '   ollama run libros-trading:8b "Recomienda 3 mejoras priorizadas para mi autotrader"' -ForegroundColor Gray
        Write-Host ""
        
        Write-Host "4. 📊 Gestión de riesgo:" -ForegroundColor White
        Write-Host '   ollama run libros-trading:8b "Mi mercado tiene 55% volatilidad alta. ¿Cómo ajustar risk management?"' -ForegroundColor Gray
        Write-Host ""
        
        # Verificar que el modelo se creó
        Write-Host "📋 Verificando modelos disponibles:" -ForegroundColor Yellow
        & ollama list
        
    } else {
        Write-Host "❌ ERROR: Falló la creación del modelo" -ForegroundColor Red
    }
    
} catch {
    Write-Host "❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Read-Host "Presiona Enter para continuar"