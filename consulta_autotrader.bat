@echo off
echo ==========================================
echo CONSULTA ESPECIALIZADA SOBRE AUTOTRADER
echo ==========================================
echo.

ollama run libros-trading:8b "Analiza mi estrategia de autotrader actual según la metodología de Ernie Chan:

SISTEMA ACTUAL:
- buy_score_threshold = 6.0 (comprar cuando score >= 6.0)
- sell_score_threshold = 4.5 (vender cuando score <= 4.5)  
- max_position_value = $10,000 por posición
- max_total_positions = 10 posiciones máximo
- Capital stocks: $10,000 total
- Capital crypto: $50,000 total

RESULTADOS DE BACKTESTING PROBADOS:
- 95.8%% win rate en 30 días
- 91.7%% win rate en 60 días
- 72 trades exitosos generados

PROBLEMAS ACTUALES:
- SHORTs perdiendo dinero en HP, MOH, UNG, BRKR
- Mercado con 55.1%% symbols con alta volatilidad
- 148.6%% volatilidad máxima detectada

ARQUITECTURA:
- FastAPI backend
- advanced_scoring_service.py para SHORTs
- portfolio_manager.py para gestión de capital
- volatility_service.py para filtros
- Timeframe analysis: 1d, 4h, 1h

¿Qué opinas de esta estrategia según los principios del libro? ¿Qué mejoras específicas recomiendas para los SHORTs que están perdiendo? ¿Es correcta la gestión de riesgo con estos parámetros?"

pause