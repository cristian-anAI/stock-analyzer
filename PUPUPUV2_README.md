# PupupuV2 Scalping Bot

Sistema semi-automático de trading para BTC/USDT en timeframe de 5 minutos, basado en la estrategia Pupupu de TradingView.

## 🎯 Resumen de Resultados (Backtest)

**Período:** 3.5 días (1000 velas de 5 min)
**Señales generadas:** 16
**Win Rate:** 56.2% (9W / 7L)
**P&L Total:** +$2,060 (con riesgo de $200/trade)
**Profit Factor:** 2.19
**Max Drawdown:** $600
**Tiempo promedio en trade:** 13 minutos

### Métricas Clave
- **Average Win:** $340 (R:R de 1.7)
- **Average Loss:** $200 (riesgo fijo)
- **R:R promedio conseguido:** 0.52 (nota: muchos trades cerrados antes del TP completo)

---

## 📋 Arquitectura del Sistema

### Módulos Implementados

```
src/
├── indicators/
│   ├── volume_profile.py    # Volume Profile (4h, 24h, 7d)
│   ├── pivot_detector.py    # Detección de pivotes (Pupupu logic)
│   └── ema.py               # EMA(12) calculation
│
├── strategy/
│   └── pupupuv2_signals.py  # Lógica de generación de señales
│
├── risk/
│   └── position_sizer.py    # Position sizing + risk management
│
├── filters/
│   └── market_context.py    # Filtros (liquidez, volatilidad, eventos)
│
└── data/
    └── binance_client.py    # Cliente para datos de Binance

pupupuv2_bot.py              # Orquestador principal
backtest_pupupuv2.py         # Sistema de backtesting
test_pupupuv2_bot.py         # Test de una ejecución
```

---

## 🚀 Instalación

### Requisitos

```bash
pip install ccxt numpy matplotlib
```

### Estructura de Archivos

Todos los archivos están en:
- `c:\repos\stock-analyzer\src\*`
- `c:\repos\stock-analyzer\pupupuv2_bot.py`

---

## 💡 Uso

### 1. Test Rápido (Single Check)

Ejecuta un análisis único del mercado actual:

```bash
python test_pupupuv2_bot.py
```

**Output esperado:**
- Fetch de datos en tiempo real de Binance
- Cálculo de Volume Profile
- Detección de pivotes activos
- Generación de señal (si hay setup válido)

### 2. Modo Continuo (Recomendado)

Ejecuta el bot en modo monitoreo continuo:

```bash
python pupupuv2_bot.py
```

Cuando se pida modo, elige `2` para continuous monitoring.

**Comportamiento:**
- Revisa el mercado cada 60 segundos
- Genera alerta cuando detecta setup válido
- Guarda señales en carpeta `signals/`
- Cooldown de 15 minutos entre señales

### 3. Backtesting

Valida la estrategia con datos históricos:

```bash
python backtest_pupupuv2.py
```

**Output:**
- Simula trades en últimas 1000 velas (3.5 días)
- Calcula win rate, profit factor, drawdown
- Guarda resultados en `backtest_results.json`

---

## 📊 Lógica de la Estrategia

### Setup de Entrada

**Requisitos para generar señal:**

1. **Pivot Touch:** Precio toca un pivot (resistencia o soporte)
   - Pivotes detectados con lookback de 400 períodos
   - Swing detection de 5 barras a cada lado

2. **EMA Cross:** Primera vela que cierra cruzando EMA(12)
   - Cruce bajista (SHORT): cierre por debajo de EMA después de tocar resistencia
   - Cruce alcista (LONG): cierre por encima de EMA después de tocar soporte

3. **Filtros de Mercado:**
   - ✅ Liquidez mínima (volumen > 100 BTC)
   - ✅ Volatilidad aceptable (ATR < 2.5x promedio)
   - ✅ No eventos fundamentales (NFP, FOMC, etc.)

### Gestión de Riesgo

- **Entry:** Precio donde se cruza la EMA
- **Stop Loss:** Pivot ± 2.5 puntos
- **Take Profit:** Entry ± (1.7 × riesgo)
- **Position Size:** 2% de capital en riesgo por trade

**Ejemplo:**
```
Señal SHORT:
- Resistencia tocada: $112,000
- Entry (EMA cross): $111,900
- SL: $112,002.5 (resistencia + 2.5)
- Riesgo: $102.5
- TP: $111,725.75 (entry - 1.7 × riesgo)
```

---

## 🎨 Volume Profile Integration

El sistema calcula VP en 3 timeframes:

- **VP_corto (4h):** Contexto inmediato para entries/exits
- **VP_medio (24h):** S/R intradía
- **VP_largo (7d):** Zonas de supply/demand mayores

**Boost de Confianza:**
- Señal gana +15% confidence si pivot coincide con HVN del VP
- Ayuda a filtrar setups de mayor probabilidad

---

## 🔧 Configuración

### Bot Config (`pupupuv2_bot.py`)

```python
bot_config = {
    'symbol': 'BTC/USDT',
    'timeframe': '5m',
    'account_balance': 10000,     # Capital total
    'risk_per_trade': 0.02,       # 2% riesgo
    'max_position_size': 5000,    # Max $5k por trade
    'signal_cooldown': 15         # Minutos entre señales
}
```

### Strategy Config

```python
strategy_config = {
    'ema_period': 12,              # EMA(12)
    'lookback_periods': 400,       # 400 velas = ~33h
    'tp_rr': 1.7,                  # R:R de 1.7
    'sl_padding': 2.5,             # 2.5 pts de padding en SL
    'swing_bars': 5,               # Detección de swings
    'touch_tolerance': 0.15,       # 0.15% tolerancia para "toque"
    'break_tolerance': 0.2         # 0.2% para considerar pivot roto
}
```

---

## 📈 Interpretación de Señales

### Ejemplo de Alerta

```
======================================================================
🚨 TRADE ALERT 🚨
======================================================================

SHORT SIGNAL - Confidence: 91.1%
======================================================================
Entry:  $109,093.44
SL:     $108,986.95
TP:     $108,912.41
R:R:    1:1.7
Risk:   $200.00
Size:   $1,880.00

Reason: Resistance touch @ $109,200.00 + bearish EMA cross
Pivot:  $109,200.00 (touches=2, strength=0.85)
Time:   2025-10-20 01:00:00
======================================================================

⚠️  MANUAL EXECUTION REQUIRED - Check for fundamental events!
======================================================================
```

### Qué Revisar Antes de Ejecutar

1. **Eventos Fundamentales:**
   - ¿Hay NFP, FOMC, discurso de Powell/Trump hoy?
   - ¿Hay noticias mayores de crypto?

2. **Contexto de Mercado:**
   - ¿Precio está en zona lógica del VP?
   - ¿HT trend alineado o neutral?

3. **Pivot Strength:**
   - Confidence > 80% = muy buena
   - Touches > 1 = pivot confirmado múltiples veces

---

## 🎯 Roadmap / Mejoras Futuras

### Corto Plazo
- [ ] Integración con Telegram para alertas
- [ ] Visualización de pivotes sobre gráfico (debugging)
- [ ] Sistema de tracking de trades ejecutados
- [ ] Integración con calendario económico (Forex Factory API)

### Medio Plazo
- [ ] Machine Learning para filtrar mejores setups
- [ ] Análisis de confluencias múltiples (VP + Fibonacci + ...)
- [ ] Optimización de parámetros con genetic algorithms
- [ ] Backtesting extendido (30+ días de datos)

### Largo Plazo
- [ ] Auto-ejecución con API de Binance Futures
- [ ] Portfolio multi-par (BTC, ETH, SOL, etc.)
- [ ] Dashboard web en tiempo real
- [ ] Sistema de journaling automático

---

## ⚠️ Disclaimer

**IMPORTANTE:** Este es un sistema **SEMI-AUTOMÁTICO**.

- ✅ Genera señales automáticamente
- ❌ NO ejecuta trades automáticamente
- ⚠️ Usuario debe validar cada señal manualmente

**Riesgos:**
- Trading crypto es altamente volátil
- Ninguna estrategia garantiza ganancias
- Win rate de 56% significa que 44% de trades pierden
- Gestión de riesgo es CRÍTICA

**Recomendaciones:**
- Empezar con cuenta demo o capital mínimo
- Nunca arriesgar más del 2% por trade
- Evitar operar durante eventos fundamentales
- Mantener un journal de trades ejecutados

---

## 📞 Soporte

Si encuentras bugs o tienes sugerencias:

1. Revisa los logs en consola
2. Verifica conexión a Binance API
3. Comprueba que tienes la última versión de dependencies

**Archivos de Logs:**
- Señales guardadas en: `signals/signal_*.json`
- Backtest results en: `backtest_results.json`

---

## 📚 Referencias

- **Pupupu Indicator:** TradingView community indicator
- **Volume Profile:** Market Profile methodology
- **Risk Management:** Fixed fractional position sizing (2% rule)

---

## ✅ Checklist Pre-Operación

Antes de empezar a usar el bot:

- [ ] Instaladas todas las dependencias (`pip install ccxt numpy matplotlib`)
- [ ] Testeado el bot con `test_pupupuv2_bot.py`
- [ ] Revisado el backtest (`backtest_pupupuv2.py`)
- [ ] Configurado `bot_config` con tu capital real
- [ ] Entendido que es SEMI-AUTOMÁTICO (requiere validación manual)
- [ ] Establecido plan de gestión de riesgo
- [ ] Preparado para NO operar durante eventos fundamentales

---

**Happy Trading! 🚀**

*Generado el 21/10/2025*
