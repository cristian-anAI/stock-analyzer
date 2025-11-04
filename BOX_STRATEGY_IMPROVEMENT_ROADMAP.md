# Box Strategy - Roadmap de Mejoras

**Fecha**: 14 Octubre 2025
**Estado Actual**: 11 mercados, ML con 49 features, win rate ~60-68%

---

## Priorización (Impacto vs Esfuerzo)

### 🔴 PRIORIDAD ALTA (Quick Wins - Alto impacto, bajo esfuerzo)

#### 1. **Datos Históricos Más Antiguos para Backtesting** ⭐⭐⭐⭐⭐
**Impacto**: MUY ALTO | **Esfuerzo**: BAJO | **Tiempo**: 1-2 días

**Por qué es crítico:**
- Actualmente solo tenemos 55 días de datos
- Con 11 mercados × 55 días = ~605 días-mercado de datos
- **Mínimo recomendado**: 1 año (252 trading days) × 11 mercados = 2,772 días-mercado
- **Óptimo**: 2-3 años para capturar diferentes regímenes de mercado

**Problemas actuales:**
- Overfitting probable (modelo memoriza en vez de generalizar)
- No captura diferentes condiciones: bull market, bear market, alta volatilidad, baja volatilidad
- Sesgo reciente (últimos 2 meses pueden no ser representativos)

**Implementación:**
```python
# Cambiar en backtest
lookback_days = 365 * 2  # 2 años de datos
# Esto nos da ~5,000 días-mercado de entrenamiento
```

**Beneficios esperados:**
- ✅ Modelo más robusto
- ✅ Mejor detección de patrones reales vs ruido
- ✅ Validación cruzada más confiable
- ✅ Reducción de overfitting del 30-50%

---

#### 2. **Features de Correlación entre Mercados** ⭐⭐⭐⭐⭐
**Impacto**: MUY ALTO | **Esfuerzo**: MEDIO | **Tiempo**: 2-3 días

**Por qué es crítico:**
- SPX-NDX correlación 0.972 = casi el mismo trade
- Sistema actual trata trades correlacionados como independientes
- **Problema HOY**: 5 mercados LONG simultáneos sin ajuste de riesgo

**Implementación ya diseñada:**
- 17 nuevos features de correlación (ver MARKET_CORRELATION_FINDINGS.md)
- Sistema de detección de confluencia ya creado (`check_market_confluence.py`)

**Features prioritarias:**
```python
# Top 5 features de correlación (orden de implementación)
1. corr_spx_ndx_30d: float           # Correlación rolling 30d
2. other_markets_breaking_same_dir: int  # Cuenta mercados en misma dirección
3. rel_strength_vs_spx_5d: float     # Fuerza relativa vs SPX
4. direction_align_spx_ndx: bool     # Misma dirección hoy
5. market_strength_rank: int          # Ranking de fuerza 1-11
```

**Beneficios esperados:**
- ✅ Reducción de falsa confianza cuando mercados correlacionados rompen juntos
- ✅ Mejor position sizing (no multiplicar por 5 cuando SPX/NDX/RUT/FTSE/STOXX van igual)
- ✅ Detección de divergencias como señales de precaución
- ✅ Win rate esperado: +5-8% por mejor selección

---

#### 3. **Early Breakout Detection** ⭐⭐⭐⭐
**Impacto**: ALTO | **Esfuerzo**: BAJO | **Tiempo**: 1 día

**Por qué es importante:**
- HOY: Breakout real a las 9:05 AM (15:05 Madrid), sistema lo detectó a las 10:00 AM
- Perdimos 55 minutos de movimiento
- **Problema verificado**: Box se "rompe a sí mismo" durante formación

**Opciones de implementación:**

**Opción A - Conservadora (recomendada):**
```python
# Detectar pero etiquetar como "early_breakout"
if breakout_during_box_formation:
    entry_type = "EARLY"  # vs "STANDARD"
    confidence_adjustment = 0.85  # -15% confianza
    # Añadir feature: minutes_before_box_end
```

**Opción B - Agresiva:**
```python
# Permitir entrada inmediata si:
- Box lleva >60% formado (9:12 AM o más)
- Breakout >0.5 ATR de penetración
- Volumen >150% promedio
```

**Beneficios:**
- ✅ Captura movimientos tempranos fuertes
- ✅ Mejora R-multiple promedio (+0.3-0.5R)
- ⚠️ Puede aumentar falsos breakouts (requiere filtros)

---

### 🟡 PRIORIDAD MEDIA (Alto impacto, esfuerzo moderado)

#### 4. **Análisis de Sentimiento con Noticias** ⭐⭐⭐⭐
**Impacto**: ALTO | **Esfuerzo**: ALTO | **Tiempo**: 5-7 días

**Tu idea es EXCELENTE, pero con matices:**

**✅ A FAVOR:**
- Datos fundamentales pueden explicar "por qué" el mercado se mueve
- Noticias macro afectan todos los índices simultáneamente
- Puede detectar "risk-on" vs "risk-off" days

**⚠️ DESAFÍOS:**
- **Timing**: Noticias salen a diferentes horas (pre-mercado, durante box, post-box)
- **Lag**: Feed de noticias puede tener delay de 5-15 minutos
- **Ruido**: 90% de noticias son irrelevantes para el trade de 10:00-11:00 AM
- **Costo**: APIs de noticias de calidad son caras (NewsAPI, Bloomberg Terminal)

**Implementación recomendada - FASE 1 (GRATIS):**

```python
# Usar FinancialModelingPrep API (gratis hasta 250 calls/día)
# https://financialmodelingprep.com/

features_sentiment = {
    # Sentimiento PRE-MERCADO (antes de 8:30 AM)
    'premarket_news_sentiment': float,  # -1.0 a +1.0
    'premarket_news_count': int,        # Cantidad de noticias importantes

    # Eventos macro del día
    'has_fomc_meeting': bool,           # Fed habla hoy
    'has_cpi_release': bool,            # Inflación sale hoy
    'has_earnings_spx_heavy': bool,     # Muchas earnings importantes

    # Fear & Greed Index (ya disponible gratis)
    'fear_greed_index': int,            # 0-100

    # VIX level (volatilidad implícita)
    'vix_level': float,                 # >20 = alta volatilidad
    'vix_change_pct': float             # Cambio día anterior
}
```

**Fuentes de datos gratuitas:**
1. **Fear & Greed Index**: CNN Money (scraping o API no oficial)
2. **VIX**: Ya lo tienes en yfinance (`^VIX`)
3. **Economic Calendar**: https://www.investing.com/economic-calendar/
4. **News Sentiment (básico)**: NewsAPI (100 requests/day gratis)

**Implementación recomendada - FASE 2 (Si funciona Fase 1):**

```python
# Análisis NLP de headlines con transformers
from transformers import pipeline

sentiment_analyzer = pipeline("sentiment-analysis",
                             model="ProsusAI/finbert")

# Analizar headlines de pre-mercado (6:00-8:30 AM)
headlines = get_premarket_news(market='SPX')
sentiments = [sentiment_analyzer(h)[0] for h in headlines]

# Agregado
avg_sentiment = mean([s['score'] * (1 if s['label']=='positive' else -1)
                      for s in sentiments])
```

**ROI esperado:**
- Win rate: +3-5% (detección de días "raros" con noticias extremas)
- Evitar trades en días de alta incertidumbre
- **Costo-beneficio**: MEDIO (requiere infraestructura, pero datos gratuitos)

**Mi recomendación**: Implementar DESPUÉS de las features de correlación

---

#### 5. **Exit Signal System con RSI Divergencias (TP2 dinámico)** ⭐⭐⭐⭐
**Impacto**: ALTO | **Esfuerzo**: MEDIO | **Tiempo**: 3-4 días

**Estado actual:**
- ✅ Sistema ya diseñado (`exit_signal_predictor.py`, `train_exit_model.py`)
- ⚠️ Modelo NO entrenado aún
- ⚠️ No integrado en API en tiempo real

**Qué hace:**
- Monitorea trades activos cada 15 minutos
- Detecta agotamiento con RSI divergencias en 15min
- Recomienda: CLOSE_NOW, TRAIL_STOP, o HOLD

**Implementación pendiente:**
1. Entrenar modelo con trades históricos
2. Añadir endpoint `/api/v1/box-strategy/exit-signal`
3. Integrar en frontend para posiciones abiertas

**Beneficios esperados:**
- ✅ Mejor timing de salidas
- ✅ Captura TP2/TP3 en trades fuertes
- ✅ Sale antes en reversiones tempranas
- ✅ R-multiple promedio: 1.5R → 2.1R (+40%)

---

#### 6. **Multi-Timeframe Confluence** ⭐⭐⭐
**Impacto**: MEDIO-ALTO | **Esfuerzo**: MEDIO | **Tiempo**: 3-4 días

**Concepto:**
Añadir análisis de timeframes mayores (1H, 4H, Daily) para confirmar dirección

```python
# Nuevas features de contexto mayor
features_mtf = {
    # Tendencia en 1H
    'trend_1h': str,  # 'BULLISH', 'BEARISH', 'NEUTRAL'
    'ema_alignment_1h': bool,  # Precio sobre EMA 20/50/200

    # Tendencia en 4H
    'trend_4h': str,
    'support_resistance_proximity_4h': float,  # Distancia a S/R importante

    # Tendencia Daily
    'trend_daily': str,
    'daily_candle_type': str  # 'BULLISH_ENGULFING', 'DOJI', etc
}
```

**Ejemplo de filtro:**
```python
# Solo tomar LONG breakouts si:
if breakout_direction == 'LONG':
    if trend_1h == 'BEARISH':
        confidence *= 0.7  # -30% confianza
    if trend_4h == 'BULLISH' and trend_daily == 'BULLISH':
        confidence *= 1.2  # +20% confianza
```

**Beneficios:**
- ✅ Evitar trades contra-tendencia mayor
- ✅ Win rate: +4-6%

---

### 🟢 PRIORIDAD BAJA (Buenos de tener, no urgente)

#### 7. **Optimización de Take Profits Dinámicos** ⭐⭐⭐
**Impacto**: MEDIO | **Esfuerzo**: MEDIO | **Tiempo**: 2-3 días

Actualmente: TP1 = 1R, TP2 = 2R, TP3 = 3R (fijos)

**Mejora:**
```python
# Ajustar TPs según volatilidad del día
atr_ratio = current_atr / avg_atr_20d

if atr_ratio > 1.5:  # Alta volatilidad
    tp1 = entry + (1.5 * risk)  # TPs más lejanos
    tp2 = entry + (3.0 * risk)
else:  # Baja volatilidad
    tp1 = entry + (0.8 * risk)  # TPs más cercanos
    tp2 = entry + (1.6 * risk)
```

#### 8. **Backtesting Multi-Market Simultáneo** ⭐⭐⭐
**Impacto**: MEDIO | **Esfuerzo**: ALTO | **Tiempo**: 5-6 días

Simular gestión de capital con múltiples mercados abiertos simultáneamente

#### 9. **Portfolio Heat Map** ⭐⭐
**Impacto**: BAJO | **Esfuerzo**: BAJO | **Tiempo**: 1 día

Visualización de exposición por región/sector

---

## 📋 ROADMAP RECOMENDADO (Secuencia Óptima)

### **Sprint 1 (Semana 1-2): Fundamentos Sólidos**
```
1. ✅ Datos históricos 2 años (2 días)
2. ✅ Re-entrenar modelo con más datos (1 día)
3. ✅ Validar mejora en backtesting (1 día)
4. ✅ Features de correlación - Top 5 (3 días)
5. ✅ Re-entrenar con correlación (1 día)
6. ✅ Validar mejora (1 día)

Total: ~9 días
ROI esperado: +8-12% win rate, -40% overfitting
```

### **Sprint 2 (Semana 3-4): Optimizaciones**
```
7. ✅ Early breakout detection (1 día)
8. ✅ Exit signal system - entrenar modelo (2 días)
9. ✅ Exit signal - API integration (2 días)
10. ✅ Multi-timeframe confluence (3 días)

Total: ~8 días
ROI esperado: +0.5R en R-multiple promedio
```

### **Sprint 3 (Semana 5-6): Sentimiento & Avanzado**
```
11. ✅ VIX y Fear/Greed features (1 día)
12. ✅ Economic calendar integration (2 días)
13. ✅ News sentiment - fase 1 básica (3 días)
14. ✅ Re-entrenar con todo (1 día)
15. ✅ Validación completa (1 día)

Total: ~8 días
ROI esperado: +3-5% win rate en días de eventos
```

---

## 🎯 Mi Recomendación Personal

**Orden exacto:**

1. **Datos antiguos (2 años)** - AHORA
   - Sin esto, todo lo demás está construido sobre arena
   - Quick win enorme

2. **Features de correlación** - AHORA
   - Ya tienes el análisis hecho
   - Ya tienes el código escrito
   - Solo falta integrar y re-entrenar
   - Problema real detectado HOY (5 mercados LONG)

3. **Early breakout detection** - Esta semana
   - Problema verificado HOY (9:05 vs 10:00)
   - Fácil de implementar
   - Mejora inmediata en R-multiple

4. **Exit signals** - Próxima semana
   - Sistema ya diseñado
   - Solo falta entrenar
   - Mayor impacto en profitabilidad

5. **Sentimiento de noticias** - Después
   - Es cool, pero no es el cuello de botella actual
   - Primero optimiza lo que ya tienes
   - Luego añade complejidad

---

## 💡 Sobre tu idea de Sentimiento de Noticias

**Mi opinión honesta:**

✅ **PROS:**
- Es una dimensión completamente nueva (fundamental vs técnico)
- Puede explicar movimientos "anómalos"
- Funciona bien en timeframes más largos (swing trading, position trading)

⚠️ **CONTRAS para Box Strategy específicamente:**
- Box strategy es **ultra-short term** (entrada 10:00 AM, salida mismo día o siguiente)
- Noticias de pre-mercado ya están "priced in" para cuando abre el box a las 8:30 AM
- El breakout de 10:00 AM refleja **acción de precio real**, no sentiment
- Riesgo de "data snooping" - encontrar correlaciones espurias

**Mi recomendación:**
- Implementa **DESPUÉS** de tener datos históricos sólidos y features de correlación
- Empieza simple: VIX, Fear & Greed, Economic Calendar (binario: hay evento o no)
- Si mejora win rate >3%, entonces invierte en NLP de noticias

**Alternativa más simple y efectiva:**
En vez de sentiment de noticias, añade:
- **Opening gap analysis**: ¿Abrió con gap arriba/abajo del cierre anterior?
- **Pre-market volume**: ¿Volumen pre-mercado >150% del normal?
- **VIX spike**: ¿VIX subió >10% ayer?

Estos 3 features capturan "algo raro pasó" sin necesidad de NLP.

---

## 📊 ROI Estimado por Mejora

| Mejora | Win Rate Δ | R-Multiple Δ | Esfuerzo | Prioridad |
|--------|------------|--------------|----------|-----------|
| Datos 2 años | +5-8% | - | Bajo | 🔴 1 |
| Features correlación | +5-8% | - | Medio | 🔴 2 |
| Early breakout | - | +0.3R | Bajo | 🔴 3 |
| Exit signals | - | +0.6R | Medio | 🟡 4 |
| Multi-timeframe | +4-6% | +0.2R | Medio | 🟡 5 |
| VIX/Fear-Greed | +2-3% | - | Bajo | 🟡 6 |
| News sentiment | +3-5% | - | Alto | 🟢 7 |

**TOTAL OPTIMISTA**: +20-25% win rate, +1.1R en R-multiple

---

## ¿Por dónde empezamos?

Dame luz verde y arranco con:
1. Extender datos a 2 años
2. Re-entrenar modelo
3. Implementar top 5 features de correlación

¿Te parece bien este plan?
