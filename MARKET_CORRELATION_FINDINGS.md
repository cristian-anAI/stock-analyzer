# Market Correlation Analysis - SPX, NDX, Russell 2000

## Executive Summary

**Analysis Date**: October 9, 2025
**Data Period**: 250 trading days (1 year)
**Markets Analyzed**: S&P 500 (SPX), NASDAQ 100 (NDX), Russell 2000 (RUT)

---

## Key Findings

### 1. CORRELACIÓN EXTREMADAMENTE ALTA entre SPX y NDX

```
SPX ↔ NDX: 0.972 (97.2% correlation)
```

**Esto significa:**
- SPX y NDX se mueven casi idénticamente
- **87.1% de los días** se mueven en la misma dirección
- Cuando se mueven juntos, la correlación de magnitud es **0.976**

**Implicación para Box Strategy:**
- Si tomas **ambos trades (SPX SHORT + NDX SHORT)**, estás **duplicando exposición** al mismo movimiento
- NO son posiciones independientes - el riesgo es casi el mismo
- Si uno falla, es MUY PROBABLE que el otro también falle

### 2. Correlación Alta con Russell 2000

```
SPX ↔ RUT: 0.878 (87.8% correlation)
NDX ↔ RUT: 0.823 (82.3% correlation)
```

- RUT (small caps) tiene correlación alta pero **no tan extrema** como SPX-NDX
- **80.3%** de días SPX y RUT se mueven juntos
- **74.7%** de días NDX y RUT se mueven juntos

### 3. Divergencias Significativas = RARAS

En el último año, con movimientos > 1%:
- **0 días** donde SPX sube y NDX baja
- **0 días** donde SPX baja y NDX sube

**Conclusión:** Las divergencias significativas son extremadamente raras.

### 4. Correlación por Ventanas de Tiempo

| Ventana | SPX-NDX | SPX-RUT | NDX-RUT |
|---------|---------|---------|---------|
| 30 días | 0.963   | 0.804   | 0.774   |
| 60 días | 0.951   | 0.793   | 0.699   |
| 90 días | 0.947   | 0.798   | 0.692   |
| 180 días| 0.978   | 0.901   | 0.865   |

**Observación**: La correlación SPX-NDX se mantiene **consistentemente alta** en todos los periodos.

---

## Implicaciones Críticas para el Sistema ML

### Problema Actual

El modelo ML actual **NO considera** esta correlación. Cada mercado se evalúa independientemente, lo que resulta en:

1. **Sobre-confianza en trades correlacionados**: Si SPX y NDX dan señal SHORT simultáneamente, el modelo les asigna la misma confianza que si fueran mercados independientes.

2. **Riesgo no ajustado**: Tomar SPX SHORT + NDX SHORT = **casi el mismo trade dos veces**, pero el sistema no ajusta el tamaño de posición.

3. **Falta de señales de divergencia**: Cuando SPX y NDX divergen (raro, pero importante), el modelo no lo detecta como señal de alerta.

### Solución: Añadir Features de Correlación

## Features Propuestas para el Modelo ML

### 1. INTER-MARKET CORRELATION FEATURES

```python
# Correlación rolling entre mercados
- corr_spx_ndx_30d: float    # Correlación 30 días SPX-NDX
- corr_spx_rut_30d: float    # Correlación 30 días SPX-RUT
- corr_ndx_rut_30d: float    # Correlación 30 días NDX-RUT
- corr_spx_ndx_60d: float    # Correlación 60 días SPX-NDX
- corr_spx_ndx_90d: float    # Correlación 90 días SPX-NDX
```

**Uso en modelo:**
- Si `corr_spx_ndx_30d > 0.95` y ambos dan señal SHORT → Ajustar confianza (no son independientes)
- Si correlación baja repentinamente → Posible cambio de régimen, reducir confianza

### 2. RELATIVE STRENGTH FEATURES

```python
# ¿Qué mercado está más fuerte relativamente?
- rel_strength_ndx_vs_spx_5d: float   # (NDX return - SPX return) últimos 5d
- rel_strength_ndx_vs_spx_10d: float  # (NDX return - SPX return) últimos 10d
- rel_strength_rut_vs_spx_5d: float   # (RUT return - SPX return) últimos 5d
```

**Uso en modelo:**
- Si NDX está **más fuerte** que SPX (rel_strength > 0) → NDX SHORT puede tener más resistencia
- Si NDX está **más débil** → NDX SHORT más probable de éxito

### 3. DIRECTIONAL ALIGNMENT FEATURES

```python
# ¿Se están moviendo en la misma dirección HOY?
- direction_align_spx_ndx: int     # 1 si misma dirección, 0 si opuesta
- direction_align_spx_rut: int     # 1 si misma dirección, 0 si opuesta
- direction_align_ndx_rut: int     # 1 si misma dirección, 0 si opuesta
```

**Uso en modelo:**
- Si `direction_align_spx_ndx = 0` (movimientos opuestos) → **ALERTA**: Situación anómala
- Si todos alineados = 1 → Movimiento general del mercado, no específico del índice

### 4. MAGNITUDE DIFFERENCE FEATURES

```python
# ¿Qué tan diferentes son los movimientos?
- magnitude_diff_spx_ndx: float  # abs(SPX_return - NDX_return)
- magnitude_diff_spx_rut: float  # abs(SPX_return - RUT_return)
```

**Uso en modelo:**
- Si `magnitude_diff_spx_ndx > 0.02` (2%) → Divergencia significativa, considerar cautelosamente

### 5. BREAKOUT CONFLUENCE FEATURES

```python
# ¿Cuántos mercados correlacionados están rompiendo en la misma dirección?
- other_markets_breaking_same_dir: int  # Count (0-2)
- market_strength_rank: int             # 1=strongest, 3=weakest hoy
```

**Uso en modelo:**
- Si `other_markets_breaking_same_dir = 2` → Fuerte movimiento de mercado general
- Si `market_strength_rank = 1` (más fuerte) → Mayor probabilidad de éxito en LONG

---

## Recomendaciones de Implementación

### PRIORIDAD ALTA

1. **Añadir feature `corr_spx_ndx_30d`**
   - Más importante dado la correlación 0.972
   - Implementar PRIMERO esta

2. **Añadir feature `other_markets_breaking_same_dir`**
   - Cuenta cuántos mercados correlacionados tienen breakout simultáneo
   - Si SPX SHORT + NDX SHORT + RUT SHORT todos juntos → Ajustar confianza/tamaño

3. **Añadir feature `rel_strength_ndx_vs_spx_5d`**
   - Identifica si NDX está liderando o siguiendo a SPX

### PRIORIDAD MEDIA

4. **Features de direction alignment**
5. **Features de magnitude difference**

### Ajuste de Posición Sizing

Cuando múltiples mercados correlacionados dan señal:

```python
# Pseudo-código para ajuste de tamaño
if spx_signal == "SHORT" and ndx_signal == "SHORT":
    correlation = get_correlation_spx_ndx_30d()

    if correlation > 0.95:
        # Mercados casi idénticos - reduce exposición
        position_size_multiplier *= 0.7

    elif correlation > 0.90:
        # Alta correlación - reduce menos
        position_size_multiplier *= 0.85
```

### Ajuste de Confianza

```python
if spx_signal == "SHORT" and ndx_signal == "SHORT":
    # Ambos dando misma señal
    if corr_spx_ndx_30d > 0.95:
        # No son señales independientes, ajustar confianza hacia abajo
        confidence *= 0.9
        reasoning.append("High correlation SPX-NDX - signals not independent")
```

---

## Próximos Pasos

1. ✅ **COMPLETADO**: Análisis de correlación histórica
2. 🔄 **EN PROGRESO**: Diseño de features de correlación
3. ⏳ **PENDIENTE**: Implementar extracción de features multi-market
4. ⏳ **PENDIENTE**: Re-entrenar modelo con nuevas features
5. ⏳ **PENDIENTE**: Backtesting con features de correlación
6. ⏳ **PENDIENTE**: Validar mejora en win rate y reducción de riesgo

---

## Archivos Generados

- `ml/correlation_analysis/market_correlation_heatmap.png` - Mapa de calor de correlaciones
- `ml/correlation_analysis/market_correlation_features.csv` - Features diarias para entrenamiento
- `ml/correlation_analysis/correlation_summary.txt` - Resumen estadístico

---

## Conclusión

La correlación SPX-NDX de **0.972** es **extremadamente alta** y debe ser considerada en el modelo ML.

**Riesgo actual**: El sistema puede estar sobrestimando la confianza cuando múltiples mercados correlacionados dan la misma señal, porque los trata como eventos independientes cuando no lo son.

**Beneficio esperado**: Añadir features de correlación debería:
- ✅ Reducir false confidence en trades correlacionados
- ✅ Mejorar sizing cuando múltiples mercados rompen juntos
- ✅ Detectar divergencias anómalas como señales de precaución
- ✅ Mejor gestión de riesgo overall
