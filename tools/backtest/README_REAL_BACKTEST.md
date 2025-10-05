# Real Backtest System - Professional Backtesting Engine

## ✅ QUÉ SE IMPLEMENTÓ

Un sistema de backtesting profesional que **replica EXACTAMENTE** el comportamiento del autotrader, sin look-ahead bias, con costos reales y métricas institucionales.

### Archivos Creados

1. **`real_backtest_engine.py`** - Motor de backtesting principal
2. **`backtest_metrics.py`** - Sistema de métricas profesionales
3. **`run_real_backtest.py`** - Script ejecutable

---

## 🎯 DIFERENCIAS VS BACKTEST ANTERIOR

### ❌ **Backtest Anterior (INÚTIL)**

```python
# backtest_simplified.py - PROBLEMAS CRÍTICOS:

1. ❌ Look-ahead bias masivo
   - Descargaba 365 días de datos históricos
   - Usaba scores calculados CON DATOS DEL FUTURO
   - Resultado: 95.8% win rate FALSO

2. ❌ Scoring desconectado
   - Calculaba scores con un algoritmo diferente al autotrader
   - El autotrader real usa scores de la BD

3. ❌ Sin filtros
   - No aplicaba volatility filters
   - No aplicaba risk management
   - No aplicaba overtrading prevention

4. ❌ Costos irreales
   - Solo 0.1% commission
   - Sin slippage, spread, impact de mercado
```

### ✅ **Backtest Real (CORRECTO)**

```python
# real_backtest_engine.py - CARACTERÍSTICAS:

1. ✅ Sin look-ahead bias
   - Simula día a día
   - Usa SOLO datos disponibles antes de cada fecha
   - Calcula scores dinámicamente con ScoringService REAL

2. ✅ Mismos servicios que el autotrader
   - Usa ScoringService (el mismo)
   - Usa TRADING_CONFIG (la misma)
   - Aplica TODOS los filtros

3. ✅ Costos reales
   - Commission: 0.1%
   - Slippage: 0.1%
   - Spread: 0.05%
   - Total: ~0.25% por trade

4. ✅ Métricas profesionales
   - Sharpe Ratio
   - Sortino Ratio
   - Max Drawdown
   - Calmar Ratio
   - Win Rate, Profit Factor, etc.
```

---

## 📊 RESULTADOS DE PRUEBA

**Test ejecutado:** 2 meses (Agosto-Octubre 2024), 20 símbolos

```
======================================================================
BACKTEST SUMMARY
======================================================================
Total Return:           0.04%
CAGR:                   0.21%
Sharpe Ratio:          -0.69
Max Drawdown:          -1.83%
Win Rate:              56.25%
Total Trades:             16
Profit Factor:          1.02
======================================================================
```

### Interpretación

- **Win Rate: 56.25%** - Realista (vs 95.8% falso)
- **Sharpe: -0.69** - Bajo, indica que la estrategia necesita optimización
- **Profit Factor: 1.02** - Apenas rentable
- **Max Drawdown: -1.83%** - Muy bajo (puede indicar poco riesgo o pocos trades)

**CONCLUSIÓN:** La estrategia actual NO es rentable en este período. Necesitas optimizarla.

---

## 🚀 CÓMO USAR

### Instalación

```bash
# Ya está todo en tools/backtest/
cd tools/backtest
```

### Ejecución Básica

```bash
# Backtest de 1 año con 50 símbolos
python run_real_backtest.py

# Backtest personalizado
python run_real_backtest.py \
  --start-date 2023-01-01 \
  --end-date 2024-01-01 \
  --capital-stocks 70000 \
  --capital-crypto 30000 \
  --symbols-limit 100 \
  --output-dir ../../reports
```

### Parámetros

```bash
--start-date         # Fecha inicio (YYYY-MM-DD)
--end-date           # Fecha fin (YYYY-MM-DD)
--capital-stocks     # Capital inicial stocks (default: $70,000)
--capital-crypto     # Capital inicial crypto (default: $30,000)
--symbols-limit      # Máximo de símbolos (default: 50)
--min-market-cap     # Market cap mínimo (default: 50B)
--output-dir         # Directorio salida (default: reports/)
```

---

## 📁 ARCHIVOS GENERADOS

Cada ejecución genera 5 archivos:

1. **`real_backtest_full_TIMESTAMP.json`**
   - Resultados completos
   - Trades individuales
   - Estados diarios del portfolio

2. **`real_backtest_trades_TIMESTAMP.csv`**
   - CSV con todos los trades
   - Fácil de importar a Excel/pandas

3. **`real_backtest_daily_TIMESTAMP.csv`**
   - Valores diarios del portfolio
   - Para graficar evolución

4. **`real_backtest_report_TIMESTAMP.txt`**
   - Reporte completo con todas las métricas
   - Formato legible

5. **`real_backtest_summary_TIMESTAMP.json`**
   - Resumen ejecutivo
   - Métricas clave

---

## 📈 MÉTRICAS INCLUIDAS

### Returns
- Total Return
- CAGR (Compound Annual Growth Rate)
- Avg Monthly Return
- Best/Worst Month

### Risk
- Annual Volatility
- Downside Volatility
- VaR (Value at Risk 95%)
- Max Daily Loss/Gain

### Drawdown
- Max Drawdown
- Avg Drawdown
- Max Drawdown Days
- Recovery Days

### Trade Statistics
- Total Trades
- Win Rate
- Profit Factor
- Avg Win/Loss
- Win/Loss Ratio
- Largest Win/Loss
- Avg Hold Days
- Total Costs Paid
- Max Consecutive Losses

### Risk-Adjusted Returns
- **Sharpe Ratio** (>1.0 = good, >2.0 = excellent)
- **Sortino Ratio** (similar to Sharpe, but only penalizes downside)
- **Calmar Ratio** (return / max drawdown)

### Consistency
- Monthly Win Rate
- Monthly Volatility
- Longest Win/Loss Streak

### Benchmark
- Comparison vs S&P 500
- Alpha
- Outperformance

---

## 🚨 REALITY CHECK

El sistema incluye alertas automáticas:

```
⚠️  Win rate > 70% is suspicious - check for look-ahead bias
⚠️  Sharpe ratio > 2.0 is rare - verify results
⚠️  Max drawdown < 5% is unusual - check risk parameters
⚠️  >100% return - exceptional performance, verify thoroughly
```

---

## 🔧 CÓMO INTERPRETAR LOS RESULTADOS

### Win Rate Realista

| Win Rate | Interpretación |
|----------|---------------|
| 50-55%   | Aceptable - sistema balanceado |
| 55-60%   | Bueno - edge positivo |
| 60-65%   | Excelente - estrategia sólida |
| 65-70%   | Excepcional - nivel institucional |
| >70%     | **SOSPECHOSO** - verificar look-ahead bias |

### Sharpe Ratio

| Sharpe | Interpretación |
|--------|---------------|
| <0     | Perdiendo dinero vs risk-free rate |
| 0-1    | Bajo - no vale la pena el riesgo |
| 1-2    | Bueno - estrategia viable |
| 2-3    | Excelente - nivel profesional |
| >3     | **SOSPECHOSO** - verificar datos |

### Profit Factor

| PF    | Interpretación |
|-------|---------------|
| <1.0  | Perdiendo dinero |
| 1.0-1.5 | Apenas rentable |
| 1.5-2.0 | Bueno |
| 2.0-3.0 | Excelente |
| >3.0  | Excepcional |

---

## 🎯 PRÓXIMOS PASOS

### 1. Ejecuta Backtest Largo (1-2 años)

```bash
python run_real_backtest.py \
  --start-date 2023-01-01 \
  --end-date 2024-12-31 \
  --symbols-limit 100
```

### 2. Analiza Resultados

- ¿Win rate > 55%?
- ¿Sharpe > 1.0?
- ¿Superó al S&P 500?

### 3. Si la Estrategia NO Funciona

**Opciones:**

A. **Optimizar thresholds**
   - Probar diferentes buy_threshold (5.5, 6.5, 7.0)
   - Ajustar sell_threshold

B. **Mejorar scoring**
   - Revisar `ScoringService`
   - Agregar más indicadores técnicos

C. **Modificar filtros**
   - Ajustar volatility limits
   - Cambiar risk parameters

D. **Cambiar timeframe**
   - Modificar `swing_max_hold_days`
   - Probar diferentes períodos de holding

### 4. Si la Estrategia SÍ Funciona

**Validación adicional:**

1. **Walk-forward analysis**
   - Dividir en períodos
   - Testear en cada uno independientemente

2. **Out-of-sample testing**
   - Guardar últimos 3 meses sin tocar
   - Probar estrategia optimizada en esos datos

3. **Monte Carlo simulation**
   - Simular múltiples escenarios
   - Verificar robustez

4. **Paper trading**
   - Ejecutar en vivo SIN dinero real
   - Verificar que resultados sean consistentes

---

## ⚠️ ADVERTENCIAS IMPORTANTES

### NO Confíes Ciegamente en el Backtest

1. **Overfitting** - Optimizar demasiado para datos históricos
2. **Régimen changes** - El mercado cambia, pasado ≠ futuro
3. **Black swans** - Eventos extremos no capturados
4. **Execution issues** - Slippage real puede ser peor

### Benchmark Mínimo

Tu estrategia DEBE:
- Superar al S&P 500 por al menos 3-5% anual
- Tener Sharpe > 1.0
- Tener Max Drawdown < 20%

Si no cumple, **mejor invertir en un index fund**.

---

## 📚 RECURSOS ADICIONALES

### Libros Recomendados
- "Evidence-Based Technical Analysis" - David Aronson
- "Quantitative Trading" - Ernie Chan
- "Advances in Financial Machine Learning" - Marcos López de Prado

### Conceptos Clave
- **Walk-Forward Optimization**
- **Monte Carlo Simulation**
- **Kelly Criterion**
- **Position Sizing**

---

## 🐛 TROUBLESHOOTING

### Error: "no such table: stocks"
```bash
# Asegúrate de ejecutar desde tools/backtest/
cd tools/backtest
python run_real_backtest.py
```

### Error: Timezone issues
Ya está arreglado en el código actual.

### Backtesting muy lento
```bash
# Reduce el número de símbolos
python run_real_backtest.py --symbols-limit 20
```

---

## ✅ CHECKLIST DE CALIDAD

Antes de confiar en los resultados, verifica:

- [ ] Win rate < 70%
- [ ] Sharpe ratio < 3.0
- [ ] Mínimo 50 trades
- [ ] Período > 6 meses
- [ ] Max drawdown > 5%
- [ ] Resultados vs benchmark (S&P 500)
- [ ] Out-of-sample validation
- [ ] Walk-forward analysis

---

## 🏆 CONCLUSIÓN

Este sistema de backtesting es **profesional** y te dará resultados **realistas**.

**Si tu estrategia tiene:**
- Win rate 55-65%
- Sharpe 1.0-2.0
- Supera al S&P 500 por 3-5%

**Entonces tienes algo bueno** y vale la pena ejecutarlo en paper trading.

**Si NO cumple esos criterios**, necesitas optimizar o cambiar de estrategia.

¡Buena suerte! 🚀
