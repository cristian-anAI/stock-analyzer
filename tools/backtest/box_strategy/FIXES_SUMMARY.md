# Resumen de Fixes - Octubre 5, 2025

## 🔴 PROBLEMA CRÍTICO IDENTIFICADO

**Bug**: SPX y NDX mostraban trades 100% idénticos
**Impacto**: Invalidaba TODOS los resultados de ML (68.3% win rate era falso)
**Tu memoria era CORRECTA**: Oct 3 - NDX SHORT→TP1, SPX LONG→SL

## ✅ SOLUCIONES IMPLEMENTADAS

### 1. Fix MultiIndex en data_loader.py

**Archivo**: `data_loader.py:145-153`

**Antes (INCORRECTO)**:
```python
# Verificaba len() antes de MultiIndex
if len(df.columns) == 6:
    df.columns = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
elif len(df.columns) == 5:
    df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
else:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
```

**Después (CORRECTO)**:
```python
# Verifica MultiIndex PRIMERO
if isinstance(df.columns, pd.MultiIndex):
    # yfinance devuelve ('Close', 'ES=F') - eliminar ticker
    df.columns = df.columns.droplevel(1)
elif len(df.columns) == 6:
    df.columns = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
elif len(df.columns) == 5:
    df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
```

**Por qué fallaba**:
- yfinance devuelve MultiIndex: `[('Close', 'ES=F'), ('High', 'ES=F'), ...]`
- `len(MultiIndex) == 5` entraba en la condición incorrecta
- Nunca llegaba al código que eliminaba el ticker
- Resultado: Todas las descargas usaban el MISMO ticker

**Verificación del fix**:
```
ANTES (bug):
SPX: 23673.50  ← Datos de NDX!
NDX: 23673.50  ← Datos de NDX!

DESPUÉS (fixed):
SPX: 6405.00   ← Correcto ~6,400 ✓
NDX: 23658.50  ← Correcto ~23,600 ✓
```

---

### 2. Ajuste Límite de Días yfinance

**Problema**: yfinance solo acepta ~55 días de datos 5min, no 60
**Error**: `"5m data not available ... must be within the last 60 days"`

**Fix**: Cambiar de 60 días a 55 días en todos los backtests

**Archivos actualizados**:
- `run_corrected_backtest.py`: `days=55` (antes 60)
- `fix_and_retrain_ml.py`: `days=55`
- Cualquier script futuro debe usar max 55 días

---

### 3. Nueva Feature: RSI Divergence

**Archivo**: `ml/feature_engineering.py`

**Nueva feature añadida**: `rsi_divergence_5min`

**Valores**:
- `-1.0` = Divergencia bajista (precio ↑, RSI ↓) - señal venta
- `0.0` = Sin divergencia
- `+1.0` = Divergencia alcista (precio ↓, RSI ↑) - señal compra

**Implementación**:
```python
def _detect_rsi_divergence(self, df, window=14, lookback=20):
    # Calcula RSI
    rsi = RSIIndicator(close=df['Close'], window=window).rsi()

    # Compara picos/valles de precio vs RSI
    # Bearish: precio hace higher high, RSI hace lower high
    # Bullish: precio hace lower low, RSI hace higher low
    ...
```

**Total features**: 48 (antes 47)

---

## 📊 ESTADO ACTUAL

### Backtest en Progreso

**Configuración**:
- Mercados: 10 (SPX, NDX, FTSE, DAX, STOXX, CAC, NKY, HSI, ASX, IBEX)
- Período: 55 días (Aug 11 - Oct 5, 2025)
- Capital inicial: $100,000 por mercado
- Risk per trade: 2%

**Script**: `run_corrected_backtest.py`
**Status**: Ejecutándose en background (bash ID: 36bbb5)

### Datos Verificados

**SPX** (S&P 500 E-mini):
- Símbolo: ES=F
- Rango precio: ~6,000 - 7,000
- Primera descarga: 6405.00 ✓

**NDX** (NASDAQ-100 E-mini):
- Símbolo: NQ=F
- Rango precio: ~20,000 - 25,000
- Primera descarga: 23658.50 ✓

**Diferencia verificada**: ~17,000 puntos (completamente diferentes) ✓

---

## 🔄 PRÓXIMOS PASOS

### Paso 1: Completar Backtest (En Progreso)
- ⏳ Esperar resultados de 10 mercados
- ✅ Verificar SPX ≠ NDX en los resultados finales
- 📁 Guardar JSON con datos correctos

### Paso 2: Re-entrenar ML
Una vez completado el backtest:

```bash
cd tools/backtest/box_strategy
python ml/train_models.py --data results/multi_market_results_*.json --version 1
```

**Modelos a entrenar**:
- Random Forest (200 trees, max_depth=15)
- XGBoost (150 estimators, GPU-optimized si disponible)

**Features**: 48 incluyendo `rsi_divergence_5min`

### Paso 3: Validar Resultados ML

Ejecutar análisis en trades reales:
```bash
python analyze_ml_on_real_trades.py
```

**Verificar**:
- Win rate mejora vs baseline
- Predicciones en Oct 3 SPX (debería ser LONG→SL predicho como LOSS)
- Predicciones en Oct 3 NDX (debería ser SHORT→TP1 predicho como WIN)

---

## 🐛 PROBLEMAS CONOCIDOS

### Mercados con Errores

**DAX (FDAX=F)**:
- Error: `YFTzMissingError('possibly delisted; no timezone found')`
- Estado: Delisted o símbolo incorrecto
- Solución: Excluir DAX del análisis O usar símbolo alternativo
- Impacto: No crítico, tenemos 9 mercados más

**Otros mercados**:
- FTSE (^FTSE): OK ✓
- CAC (^FCHI): OK ✓
- STOXX (^STOXX50E): OK ✓
- NKY (NKD=F): OK ✓
- HSI (^HSI): OK ✓
- ASX (^AXJO): OK ✓
- IBEX (^IBEX): OK ✓

---

## 📈 LIMITACIONES yfinance

### Datos Históricos 5min

**Límite actual**: ~55 días (yfinance actualizado)
**Límite anterior**: ~60 días
**Motivo**: Yahoo Finance API limita descargas intraday

### Soluciones para Más Histórico

1. **Polygon.io** ($200/mes)
   - Profesional, completo
   - API fácil integración
   - **Recomendado**

2. **Alpha Vantage** (Gratis 500 calls/día)
   - Suficiente para empezar
   - Necesita batching

3. **Interactive Brokers API** (Gratis con cuenta)
   - Excelente calidad
   - Requiere cuenta activa IB

4. **FirstRate Data** ($100-500 one-time)
   - Comprar períodos específicos
   - Alta calidad

---

## 📝 ARCHIVOS MODIFICADOS

### Core Fixes
- ✅ `data_loader.py`: MultiIndex handling (líneas 145-153)
- ✅ `ml/feature_engineering.py`: RSI divergence (+65 líneas, método `_detect_rsi_divergence`)

### Nuevos Scripts
- ✅ `run_corrected_backtest.py`: Backtest con 55 días
- ✅ `test_spx_ndx_fix.py`: Test rápido verificación
- ✅ `debug_yfinance.py`: Debug descargas
- ✅ `compare_spx_ndx.py`: Comparación trade por trade
- ✅ `BACKTEST_DATA_ISSUES.md`: Documentación problemas
- ✅ `FIXES_SUMMARY.md`: Este documento

### Cache Limpiado
- 🗑️ Eliminados 10+ archivos cache corruptos
- ✅ Forzada descarga fresca de todos los mercados

---

## ✅ VERIFICACIÓN FINAL

### Pre-Fix (INCORRECTO)
```
Oct 3, 2025:
SPX: LONG Entry:6789.25 Stop:6766.50 P&L:-23.75 [IDÉNTICO - BUG]
NDX: LONG Entry:6789.25 Stop:6766.50 P&L:-23.75 [IDÉNTICO - BUG]
```

### Post-Fix (ESPERADO)
```
Oct 3, 2025:
SPX: LONG  Entry:~6,800  Stop:~6,750  P&L:NEGATIVO  [LOSS ✓]
NDX: SHORT Entry:~25,000 Stop:~25,100 P&L:POSITIVO  [WIN ✓]
```

**Nota**: Valores exactos dependen de backtest en ejecución

---

## 🎯 OBJETIVO FINAL

**Re-entrenar ML con datos REALES**:
- 9-10 mercados independientes
- 55 días de histórico
- 48 features (incluyendo RSI divergence)
- Validar mejora real en win rate
- Analizar predicciones en trades conocidos (Oct 3)

---

**Creado**: 2025-10-05 21:22 UTC
**Status**: ✅ Fixes aplicados, backtest en progreso
**Autor**: Claude Code (con asistencia de cristian-anAI)
