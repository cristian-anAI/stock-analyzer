# Comparación de Pivotes: Python vs TradingView

Este documento explica cómo comparar la detección de pivotes entre el sistema Python y TradingView.

## Archivos Creados

1. **`tradingview_pivot_simple_v2.pine`** - Indicador Pine Script que replica la lógica de `SimplePivotDetector`
2. **`src/indicators/pivot_detector_simple.py`** - Detector Python actualizado

## Instrucciones para TradingView

### 1. Agregar el Indicador

1. Abre TradingView en BTC/USDT, timeframe 1 minuto
2. Click en "Pine Editor" (abajo)
3. Copia el contenido de `tradingview_pivot_simple_v2.pine`
4. Pega en el editor
5. Click en "Add to Chart"

### 2. Configuración del Indicador

El indicador tiene estos parámetros (deben coincidir con Python):

```
Lookback Periods: 100 (default)
Merge Threshold %: 0.3 (default)
Max Pivots to Show: 10 (default)
```

### 3. Qué Verás

El indicador dibujará:
- **Líneas rojas** = Resistencias (por encima del precio)
- **Líneas verdes** = Soportes (por debajo del precio)
- **Labels** con:
  - Nivel (R1, R2, S1, S2, etc.)
  - Precio exacto
  - Strength score

### 4. Verificación Visual

También verás:
- **Línea roja delgada** = Rolling High (transparente)
- **Línea verde delgada** = Rolling Low (transparente)

Estas líneas muestran el **highest high** y **lowest low** de los últimos 100 períodos.

## Algoritmo Implementado

### Python (`SimplePivotDetector`)

```python
# Paso 1: Para cada ventana de 100 velas
for i in range(lookback, len(data)):
    window = data[i-lookback:i]

    # Paso 2: Encontrar máximo y mínimo
    max_high = np.max(window[:, 2])  # Highest high
    min_low = np.min(window[:, 3])   # Lowest low

    # Paso 3: Agregar a lista de niveles
    resistance_levels.append(max_high)
    support_levels.append(min_low)

# Paso 4: Merge niveles similares (dentro de 0.3%)
merged_resistances = merge_levels(resistance_levels, 0.3%)
merged_supports = merge_levels(support_levels, 0.3%)

# Paso 5: Filtrar solo activos
active_resistances = [r for r in merged if r.price > current_price]
active_supports = [s for s in merged if s.price < current_price]

# Paso 6: Calcular strength
for level in levels:
    strength = 50.0
    strength += min(30, touches / 50 * 30)  # Touch factor
    strength += 20 if bars_ago < 50 else 10 if bars_ago < 100 else 5  # Recency
```

### Pine Script (`tradingview_pivot_simple_v2.pine`)

```pine
// Paso 1: Calcular rolling high/low
rolling_high = ta.highest(high, lookback)
rolling_low = ta.lowest(low, lookback)

// Paso 2: Escanear últimas 500 barras
for i = 1 to 500
    h = ta.highest(high, lookback)[i]
    l = ta.lowest(low, lookback)[i]

    // Paso 3: Merge (si diferencia < 0.3%)
    if abs(h - existing) / existing * 100 <= 0.3
        // Ya existe, no agregar

    // Paso 4: Filtrar activos
    if h > close
        resistance_prices.push(h)
    if l < close
        support_prices.push(l)

// Paso 5: Dibujar top N niveles
for i = 0 to max_pivots
    line.new(..., price, ...)
```

## Comparación Esperada

### Python Output (ejemplo)

```
RESISTENCIAS:
R1    $110,854.19     456 toques     +0.69%
R2    $111,190.00     720 toques     +1.00%

SOPORTES:
S1    $109,806.37     461 toques     -0.26%
S2    $109,590.46     445 toques     -0.45%
```

### TradingView Output (debería coincidir)

```
Chart mostrará:
- R1: $110,854 (línea roja)
- R2: $111,190 (línea roja)
- S1: $109,806 (línea verde)
- S2: $109,590 (línea verde)
```

## Diferencias Esperadas

### Pequeñas diferencias aceptables:

1. **Touch count**: TradingView simplifica el conteo (muestra "1" en lugar del real)
   - **Razón**: Pine Script tiene limitaciones para contar touches históricos
   - **Solución**: Python tiene el conteo correcto

2. **Número exacto de niveles**: Pueden variar ±1 nivel
   - **Razón**: Método de merge puede tener ligeras diferencias en orden de procesamiento
   - **OK si**: Los niveles principales (top 3-5) coinciden

3. **Precisión decimal**: TradingView muestra 2 decimales, Python puede mostrar más
   - **OK**: Solo diferencia visual

### Diferencias NO aceptables (indicarían un bug):

1. **Niveles completamente diferentes** (ej: Python muestra $111,190 pero TradingView $115,000)
   - ❌ Bug en uno de los dos sistemas

2. **Dirección incorrecta** (ej: Python muestra resistencia pero TradingView soporte)
   - ❌ Bug en lógica de filtrado

3. **Todos los niveles desplazados** por un % constante
   - ❌ Posible problema con datos (diferente exchange o delay)

## Cómo Usar Esta Comparación

### Paso 1: Ejecuta Python

```bash
python show_pivots_last_2hours.py
```

Obtendrás:
```
RESISTENCIAS:
R1    $110,854.19     456 toques     +0.69%
R2    $111,190.00     720 toques     +1.00%

SOPORTES:
S1    $109,806.37     461 toques     -0.26%
S2    $109,590.46     445 toques     -0.45%
```

### Paso 2: Compara con TradingView

1. Abre TradingView con el indicador
2. Verifica que las **líneas rojas** estén aproximadamente en:
   - $110,854
   - $111,190

3. Verifica que las **líneas verdes** estén aproximadamente en:
   - $109,806
   - $109,590

### Paso 3: Si NO coinciden

Si los niveles son completamente diferentes:

1. **Verifica el timeframe**: Debe ser 1 minuto en ambos
2. **Verifica el símbolo**: BTC/USDT en ambos
3. **Verifica el lookback**: 100 períodos en ambos
4. **Verifica la hora**: Asegúrate de que ambos estén viendo los mismos datos (no hay delay)

Si aún no coinciden, hay un bug en la lógica que necesita corrección.

## Próximos Pasos

Una vez que los niveles coincidan:

1. ✅ **Confirma que el detector funciona correctamente**
2. ✅ **Usa estos niveles en la estrategia PupupuV3**
3. ✅ **Genera señales basadas en estos pivotes**

## Preguntas Frecuentes

### P: ¿Por qué TradingView muestra "1 touch" pero Python muestra "456 touches"?

**R**: Pine Script tiene limitaciones para contar touches históricos. Python cuenta correctamente todas las veces que el precio rolling high/low se repitió.

### P: ¿Puedo confiar en los niveles si el touch count no coincide?

**R**: Sí. Lo importante es que los **precios** de los pivotes coincidan, no el touch count. El touch count es solo un indicador de strength.

### P: ¿Qué hago si Python muestra 10 resistencias pero TradingView solo 5?

**R**: Normal. Verifica que los parámetros `max_pivots` coincidan en ambos. Si coinciden y siguen siendo diferentes, es porque Pine Script tiene limitaciones de rendimiento.

### P: ¿Los niveles cambiarán cada vez que refresque?

**R**: Sí, ligeramente. Los niveles son dinámicos basados en las últimas 100 velas. Cuando entra una nueva vela, los niveles se recalculan.

## Código de Referencia

### Python
- **Archivo**: `src/indicators/pivot_detector_simple.py`
- **Clase**: `SimplePivotDetector`
- **Método principal**: `detect_pivots(ohlcv_data)`

### Pine Script
- **Archivo**: `tradingview_pivot_simple_v2.pine`
- **Versión**: @version=5
- **Método**: Rolling `ta.highest()` y `ta.lowest()`

---

**Última actualización**: 2025-10-31
**Autor**: Claude Code
**Estado**: ✅ Listo para probar
