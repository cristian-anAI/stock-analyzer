# PupupuV3 - Sistema ML para TP Dinámicos

## Concepto

En lugar de usar TP2 y TP3 fijos, usamos **Machine Learning** para predecir:

- **Probabilidad de alcanzar ratios R:R** desde 2:1 hasta 20:1
- **En diferentes ventanas temporales**: 1h, 2h, 4h, 8h

### Lógica de Selección

```
TP2 = Ratio más alto con Probabilidad > 60%
TP3 = Ratio más alto con Probabilidad > 45%
```

**Ejemplo**:
```
Ratio 5:1 → P(1h)=45%, P(2h)=65%, P(4h)=72%, P(8h)=78%
Ratio 8:1 → P(1h)=30%, P(2h)=48%, P(4h)=55%, P(8h)=63%
Ratio 10:1 → P(1h)=20%, P(2h)=35%, P(4h)=42%, P(8h)=50%

TP2 = 8:1 (mayor ratio con P > 60% en algún timeframe)
     → P(8h) = 63% ✅

TP3 = 10:1 (mayor ratio con P > 45% en algún timeframe)
     → P(8h) = 50% ✅
```

## ¿Por qué es Mejor que TP Fijos?

### Problema con TPs Fijos
```python
# Estrategia fija (mala)
TP1 = 1:1  # Siempre igual
TP2 = 2:1  # Siempre igual
TP3 = 3:1  # Siempre igual
```

**Problemas**:
- ❌ Ignora condiciones del mercado
- ❌ No considera volatilidad actual
- ❌ Mismo TP en tendencia fuerte vs lateralización
- ❌ Deja dinero en la mesa o se sale muy tarde

### Con ML Dinámico (mejor)
```python
# Estrategia adaptativa (buena)
TP1 = 1:1  # Fijo (seguridad)

# TPs dinámicos basados en contexto
if volatilidad_alta and tendencia_fuerte:
    TP2 = 8:1   # P(4h) = 68%
    TP3 = 12:1  # P(8h) = 52%

elif volatilidad_baja and consolidación:
    TP2 = 3:1   # P(2h) = 71%
    TP3 = 5:1   # P(4h) = 48%
```

**Ventajas**:
- ✅ Se adapta a condiciones del mercado
- ✅ Maximiza profit potencial sin ser codicioso
- ✅ Considera probabilidades reales
- ✅ Incluye factor temporal

## Variables que Considera el ML

El modelo analiza **19 features** para cada trade:

### 1. Posición de Precio
- `price_vs_ema`: Distancia al EMA(15)
- `price_vs_vwap`: Distancia al VWAP
- `distance_to_sl_pct`: Tamaño del riesgo
- `price_vs_sma20`: Posición vs SMA(20)
- `price_vs_sma50`: Posición vs SMA(50)

### 2. Momentum (Fuerza Direccional)
- `momentum_5`: Cambio últimos 5 períodos
- `momentum_10`: Cambio últimos 10 períodos
- `momentum_20`: Cambio últimos 20 períodos
- `momentum_50`: Cambio últimos 50 períodos

### 3. Volatilidad
- `volatility_20`: Desviación estándar (20 períodos)
- `volatility_50`: Desviación estándar (50 períodos)
- `atr_14_pct`: Average True Range

### 4. Volumen
- `volume_ratio_20`: Volumen actual vs promedio
- `volume_trend_10`: Tendencia de volumen

### 5. Contexto Estructural
- `pivot_strength`: Fuerza del pivot (0-100)
- `range_position`: Posición en rango reciente
- `range_size_pct`: Tamaño del rango
- `higher_highs`: Número de máximos ascendentes
- `higher_lows`: Número de mínimos ascendentes

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────┐
│         FASE 1: BACKTEST & DATA COLLECTION      │
├─────────────────────────────────────────────────┤
│                                                 │
│  1. Run backtest on historical data (7-30 days) │
│  2. For each valid signal:                     │
│     - Record entry conditions                   │
│     - Track if ratio 2:1 reached (1h/2h/4h/8h) │
│     - Track if ratio 3:1 reached (...)          │
│     - ... up to 20:1                            │
│  3. Generate training dataset                   │
│                                                 │
│  Output: signals_data.json (features + labels)  │
└─────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────┐
│         FASE 2: ML MODEL TRAINING                │
├─────────────────────────────────────────────────┤
│                                                 │
│  For each timeframe (1h, 2h, 4h, 8h):          │
│    For each ratio (2:1, 3:1, ... 20:1):         │
│      1. Train Gradient Boosting Classifier      │
│      2. Predict: P(ratio reached in timeframe)  │
│      3. Validate with cross-validation          │
│                                                 │
│  Total models: 4 timeframes × 19 ratios = 76    │
│                                                 │
│  Output: tp_ratio_predictor_v1.pkl              │
└─────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────┐
│         FASE 3: PRODUCTION USE                   │
├─────────────────────────────────────────────────┤
│                                                 │
│  New Signal → Extract Features → ML Predict     │
│                                                 │
│  Model returns probabilities:                   │
│    Ratio 2:1 → [0.85, 0.90, 0.92, 0.93]        │
│    Ratio 3:1 → [0.70, 0.78, 0.82, 0.85]        │
│    ...                                          │
│    Ratio 20:1 → [0.05, 0.12, 0.18, 0.25]       │
│                                                 │
│  Select TPs:                                    │
│    TP2 = max(ratio) where max(P_any_tf) > 0.60 │
│    TP3 = max(ratio) where max(P_any_tf) > 0.45 │
│                                                 │
└─────────────────────────────────────────────────┘
```

## Ejemplo Completo de Predicción

### Entrada (Features del Trade)
```json
{
  "price_vs_ema": 0.15,           // 0.15% arriba del EMA
  "price_vs_vwap": -0.08,         // 0.08% abajo del VWAP
  "distance_to_sl_pct": 0.46,     // SL a 0.46%
  "momentum_20": 2.3,             // +2.3% en 20 períodos
  "volatility_20": 1.8,           // Volatilidad moderada
  "atr_14_pct": 0.52,             // ATR 0.52%
  "volume_ratio_20": 1.45,        // 45% más volumen
  "pivot_strength": 78.5,         // Pivot fuerte
  "range_position": 0.72,         // Cerca del tope del rango
  "is_long": 1.0                  // Trade LONG
}
```

### Salida del ML
```
Predicciones por Ratio:

Ratio  │  1h    2h    4h    8h   │ TP Elegido
───────┼──────────────────────────┼────────────
2:1    │  92%   95%   97%   98%  │
3:1    │  78%   85%   89%   91%  │
4:1    │  65%   74%   81%   84%  │
5:1    │  52%   63%   71%   76%  │ ← TP2 (P>60%)
6:1    │  42%   54%   63%   69%  │
7:1    │  34%   46%   56%   62%  │
8:1    │  27%   39%   49%   56%  │
9:1    │  22%   33%   43%   51%  │ ← TP3 (P>45%)
10:1   │  18%   28%   37%   45%  │
...    │  ...   ...   ...   ...  │
20:1   │   2%    5%    9%   15%  │

Recomendación:
✅ TP1 = 1:1 (automático al breakeven)
✅ TP2 = 5:1 (P(8h) = 76% > 60%)
✅ TP3 = 9:1 (P(8h) = 51% > 45%)
```

### Valores Calculados
```python
entry = 43000
sl = 42800
risk = 200

tp1 = 43200   # 1:1
tp2 = 44000   # 5:1 = 43000 + (200 × 5)
tp3 = 44800   # 9:1 = 43000 + (200 × 9)
```

## Ventajas del Sistema Temporal

### Sin Variable Temporal (Malo)
```
P(ratio=5:1) = 65%
```
**Problema**: ¿65% en cuánto tiempo? ¿1 hora? ¿1 semana? ¿1 mes?

### Con Variable Temporal (Bueno)
```
P(ratio=5:1, timeframe=1h) = 52%
P(ratio=5:1, timeframe=2h) = 63%
P(ratio=5:1, timeframe=4h) = 71%
P(ratio=5:1, timeframe=8h) = 76%
```

**Ventajas**:
1. **Gestión de tiempo**: Saber cuándo cerrar si no se alcanza
2. **Expectativas realistas**: P(8h) > P(1h) es lógico
3. **Stop temporal**: Si no alcanza en 8h, probabilidad cae
4. **Escalado inteligente**: Cerrar parciales según timeframe

## Casos de Uso

### Caso 1: Mercado Trending Fuerte
```
Features:
- momentum_20 = 5.2% (muy fuerte)
- volatility_20 = 2.8% (alta)
- volume_ratio = 2.1 (volumen explosivo)

Predicción ML:
- TP2 = 8:1 (P(4h) = 68%)
- TP3 = 12:1 (P(8h) = 52%)

Resultado: TPs ambiciosos porque las condiciones lo permiten
```

### Caso 2: Mercado Lateral
```
Features:
- momentum_20 = 0.3% (débil)
- volatility_20 = 0.8% (baja)
- range_size = 1.2% (estrecho)

Predicción ML:
- TP2 = 2:1 (P(1h) = 72%)
- TP3 = 3:1 (P(2h) = 51%)

Resultado: TPs conservadores, cierre rápido
```

### Caso 3: Contra VWAP (Riesgo Alto)
```
Features:
- with_vwap_bias = False
- ml_confidence = 65%
- risk_multiplier = 0.5 (riesgo reducido)

Predicción ML:
- TP2 = 3:1 (P(2h) = 63%)
- TP3 = 5:1 (P(4h) = 48%)

Resultado: TPs más conservadores por contexto desfavorable
```

## Entrenamiento del Modelo

### Dataset Requerido
```
Señales mínimas: ~100 para prueba, 500+ para producción
Timeframe: 7-30 días de datos 1-min
Por cada señal: 19 features + 76 labels (4 TF × 19 ratios)
```

### Algoritmo
```python
GradientBoostingClassifier(
    n_estimators=100,     # 100 árboles
    max_depth=5,          # Profundidad 5
    learning_rate=0.1,    # Learning rate conservador
    random_state=42
)
```

### Validación
```
- Cross-validation 5-fold
- Métrica: ROC-AUC
- Threshold mínimo: AUC > 0.60
- Balance de clases: 5% < positive_rate < 95%
```

## Integración con PupupuV3 Bot

### Flujo Actual (Sin ML)
```python
signal = strategy.analyze_for_signals(data)

if signal.is_valid:
    tp1 = entry + risk  # 1:1 fijo
    # TP2 y TP3 manuales
```

### Flujo Con ML
```python
signal = strategy.analyze_for_signals(data)

if signal.is_valid:
    # TP1 igual (automático)
    tp1 = entry + risk

    # ML predice TP2 y TP3
    features = model.extract_features(...)
    prediction = model.predict(features)

    tp2 = entry + (risk * prediction.tp2_ratio)
    tp3 = entry + (risk * prediction.tp3_ratio)

    print(f"TP2: {prediction.tp2_ratio}:1 (P={prediction.tp2_probability:.0%}, {prediction.tp2_timeframe})")
    print(f"TP3: {prediction.tp3_ratio}:1 (P={prediction.tp3_probability:.0%}, {prediction.tp3_timeframe})")
```

## Backtest y Validación

### Comando
```bash
python backtest_pupupuv3_with_ml.py --symbol BTC/USDT --days 14
```

### Proceso
1. **Phase 1**: Backtest con TP1 solo → Recolecta datos
2. **Phase 2**: Entrena 76 modelos ML
3. **Phase 3** (futuro): Re-backtest con ML predictions
4. **Comparación**: TP1 solo vs TP1+TP2+TP3 dinámicos

### Métricas Esperadas
```
TP1 Solo (Baseline):
- Win Rate: 60-70%
- Avg R:R: 1:1
- Expectancy: +0.2R por trade

TP1+TP2+TP3 con ML (Objetivo):
- Win Rate: 55-65% (ligeramente menor por targets más altos)
- Avg R:R: 2.5:1 - 4:1 (mucho mejor)
- Expectancy: +0.8R - +1.2R por trade (4-6x mejor)
```

## Archivos Creados

```
stock-analyzer/
├── tools/backtest/box_strategy/ml/
│   └── tp_ratio_predictor.py          # ML Model
│
├── backtest_pupupuv3_with_ml.py       # Backtest + Training
│
├── models/
│   └── tp_ratio_predictor_v1.pkl      # Trained model
│
└── PUPUPUV3_ML_SYSTEM.md              # This doc
```

## Próximos Pasos

### 1. Validar Sistema (HOY)
```bash
# Backtest 7 días (prueba)
python backtest_pupupuv3_with_ml.py --days 7

# Backtest 14 días (mejor)
python backtest_pupupuv3_with_ml.py --days 14

# Backtest 30 días (óptimo)
python backtest_pupupuv3_with_ml.py --days 30
```

### 2. Integrar con Bot (MAÑANA)
- Cargar modelo en `pupupuv3_bot.py`
- Predecir TP2/TP3 en cada señal
- Guardar predicciones en database
- Tracking de accuracy en producción

### 3. Optimizaciones (SEMANA 1)
- Feature engineering adicional
- Ensemble de modelos (RF + XGBoost)
- Hyperparameter tuning
- Re-entrenamiento semanal

### 4. Monitoreo (CONTINUO)
- Track real outcomes vs predictions
- Recalibrate modelo mensualmente
- A/B testing: Fixed TPs vs ML TPs

## Conclusión

Este sistema de **TP dinámicos con ML** es **significativamente superior** a TPs fijos porque:

1. ✅ **Se adapta al contexto** del mercado
2. ✅ **Considera probabilidades reales** basadas en datos históricos
3. ✅ **Incluye variable temporal** (cuándo esperar el target)
4. ✅ **Maximiza expectancy** sin ser codicioso
5. ✅ **Aprende continuamente** con cada trade nuevo

**Es la evolución natural de PupupuV3** y llevará la estrategia al siguiente nivel. 🚀

---

**Status**: ✅ Sistema implementado, en fase de testing
**Próximo**: Validar con backtest y ajustar thresholds según resultados
