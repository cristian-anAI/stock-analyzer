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
  - Capital stocks: $70,000 total (no $10,000)
  - Capital crypto: $30,000 total (no $50,000)

  SWING TRADING STRATEGY IMPLEMENTADA:
  - Minimum hold period: 3 días (previene exits tempranos)
  - Market timing: 15min BUY restriction, 60min SELL restriction después apertura
  - Exit logic: Solo emergency exits (±8%/±15%) o technical signals después día 3
  - Score-based exits: Solo después día 7 y score < 3.0 (no 4.5)

  RESULTADOS DE BACKTESTING VALIDADOS:
  - 95.8% win rate en 30 días
  - 91.7% win rate en 60 días
  - 72 trades exitosos generados
  - P&L realizado histórico: $210.08 en 5 trades (80% win rate)

  ARQUITECTURA ACTUAL:
  - FastAPI backend con market timing service
  - SwingTradingStrategy con minimum hold enforcement
  - Volatility service para filtros de alta volatilidad
  - P&L tracking automático para todas las transacciones
  - Database scores (no calculated scores)

  ESTADO ACTUAL DEL MERCADO:
  - 54.8% symbols con alta volatilidad (market stress)
  - 148.4% volatilidad extrema detectada
  - Overtrading prevention: max 8 trades/día

  ¿Qué opinas de esta estrategia según los principios del libro? ¿Es correcta la gestión de riesgo con estos parámetros de swing trading? ¿Cómo evalúas el
  minimum hold period de 3 días vs volatilidad alta?"
pause

