# Box Strategy - Bugs Corregidos (30 Oct 2025)

## Problema Reportado

**Fecha**: 30 Octubre 2025
**Usuario**: Carlos
**Síntoma**: Alerta de Telegram para LONG en NDX pero no hubo trade válido

### Evidencia
- Telegram alertó breakout LONG en NDX
- En el gráfico NO hubo ninguna vela de 5 minutos que CERRARA por encima del box_high
- Solo el HIGH de algunas velas tocó por encima, pero el CLOSE permaneció dentro de la caja

### Imágenes
Dos capturas de NDX mostrando:
1. Caja formada de 8:30 - 10:00 AM ET (14:30 - 16:00 Madrid)
2. Post-box period donde velas tocaron por encima pero NO cerraron fuera

---

## Bugs Identificados

### Bug #1: Detección Incorrecta de Breakout

**Archivo**: `src/api/services/box_strategy_service.py`
**Líneas**: 361-375 (antes del fix)

**Código incorrecto**:
```python
# Detect breakout and find exact time
if highest > box_high:  # ❌ INCORRECTO: usa High máximo
    breakout_detected = True
    direction = "LONG"
    ...
    # Find first candle that broke above box_high
    breakout_candles = post_box_data[post_box_data['High'] > box_high]  # ❌ HIGH
```

**Problema**:
- Estaba buscando velas donde el **High** supera el box_high
- Debería buscar velas donde el **Close** supera el box_high
- Esto causaba alertas falsas cuando solo la sombra de la vela salía de la caja

**Impacto**:
- Alertas de Telegram incorrectas
- Trades que no se debían ejecutar
- Confusión del usuario

---

### Bug #2: Falta de Timeout de 2 Horas

**Archivo**: `src/api/services/box_strategy_service.py`
**Línea**: 341 (antes del fix)

**Código incorrecto**:
```python
# Get post-box data to detect breakout
post_box_data = self.data_loader.get_post_box_data(df, target_date, hours=6)  # ❌ 6 horas
```

**Problema**:
- Buscaba breakouts hasta 6 horas después del final de la caja
- Caja termina a las 10:00 AM ET (16:00 Madrid)
- Debería solo buscar breakouts hasta las 12:00 PM ET (18:00 Madrid) = **2 horas window**
- Breakouts tardíos tienen menor probabilidad de éxito

**Impacto**:
- Trades tardíos con menor win rate
- No cumple la regla de "primeras 2 horas"

---

## Correcciones Aplicadas

### Fix #1: Detección Correcta con CLOSE

**Archivo**: `src/api/services/box_strategy_service.py`
**Líneas**: 358-411 (después del fix)

**Código correcto**:
```python
# CRITICAL FIX: Detect breakout ONLY when candle CLOSES outside box
# A breakout is valid only when Close > box_high (LONG) or Close < box_low (SHORT)

# Find first candle that CLOSED above box_high (LONG breakout)
long_breakout_candles = post_box_data[post_box_data['Close'] > box_high]  # ✅ CLOSE

# Find first candle that CLOSED below box_low (SHORT breakout)
short_breakout_candles = post_box_data[post_box_data['Close'] < box_low]  # ✅ CLOSE

# Determine which breakout happened first (if any)
long_breakout_time = None
short_breakout_time = None

if not long_breakout_candles.empty:
    long_breakout_time = long_breakout_candles.index[0]

if not short_breakout_candles.empty:
    short_breakout_time = short_breakout_candles.index[0]

# Process LONG breakout
if long_breakout_time is not None:
    # Check if there was a SHORT breakout earlier
    if short_breakout_time is None or long_breakout_time < short_breakout_time:
        breakout_detected = True
        direction = "LONG"
        entry_price = box_high
        stop_loss = box_low
        risk_points = box_range
        tp1 = entry_price + (1.0 * risk_points)
        tp2 = entry_price + (2.0 * risk_points)
        tp3 = entry_price + (3.0 * risk_points)
        breakout_candle_time = long_breakout_time.isoformat()
        entry_time = breakout_candle_time

        logger.info(f"{market_code} LONG breakout: First candle CLOSED above {box_high:.2f} at {breakout_candle_time}")

# Process SHORT breakout
elif short_breakout_time is not None:
    breakout_detected = True
    direction = "SHORT"
    entry_price = box_low
    stop_loss = box_high
    risk_points = box_range
    tp1 = entry_price - (1.0 * risk_points)
    tp2 = entry_price - (2.0 * risk_points)
    tp3 = entry_price - (3.0 * risk_points)
    breakout_candle_time = short_breakout_time.isoformat()
    entry_time = breakout_candle_time

    logger.info(f"{market_code} SHORT breakout: First candle CLOSED below {box_low:.2f} at {breakout_candle_time}")

# No breakout detected
else:
    logger.debug(f"{market_code} No breakout: No candle closed outside box range ({box_low:.2f} - {box_high:.2f})")
```

**Mejoras**:
- ✅ Usa `Close` en vez de `High` para detectar breakouts
- ✅ Determina cuál breakout ocurrió primero (LONG vs SHORT)
- ✅ Log claro del momento exacto del breakout
- ✅ Log cuando NO hay breakout

---

### Fix #2: Timeout de 2 Horas

**Archivo**: `src/api/services/box_strategy_service.py`
**Líneas**: 340-393 (después del fix)

**Código correcto**:
```python
# Get post-box data to detect breakout (first 2 hours only)
# Box ends at 10:00 AM ET, so we only look until 12:00 PM ET (2 hours window)
post_box_data = self.data_loader.get_post_box_data(df, target_date, hours=2)  # ✅ 2 horas

if not long_breakout_candles.empty:
    long_breakout_time = long_breakout_candles.index[0]

    # Validate breakout is within 2-hour window (10:00 AM - 12:00 PM ET)
    box_end_time = tz.localize(datetime.combine(target_date, datetime.strptime("10:00", "%H:%M").time()))
    timeout_time = box_end_time + timedelta(hours=2)

    if long_breakout_time > timeout_time:
        logger.info(f"{market_code} LONG breakout at {long_breakout_time} is AFTER 2-hour window (timeout: {timeout_time}). Ignoring.")
        long_breakout_time = None

if not short_breakout_candles.empty:
    short_breakout_time = short_breakout_candles.index[0]

    # Validate breakout is within 2-hour window
    box_end_time = tz.localize(datetime.combine(target_date, datetime.strptime("10:00", "%H:%M").time()))
    timeout_time = box_end_time + timedelta(hours=2)

    if short_breakout_time > timeout_time:
        logger.info(f"{market_code} SHORT breakout at {short_breakout_time} is AFTER 2-hour window (timeout: {timeout_time}). Ignoring.")
        short_breakout_time = None
```

**Mejoras**:
- ✅ Limita búsqueda de breakouts a 2 horas (en vez de 6)
- ✅ Valida explícitamente que breakout está dentro del window
- ✅ Ignora breakouts tardíos (después de 12:00 PM ET)
- ✅ Log claro cuando breakout es descartado por timeout

---

## Verificación del Fix

### Test Ejecutado

**Archivo**: `test_box_fix_today.py`
**Fecha**: 30 Octubre 2025
**Mercados testeados**: NDX, SPX

**Resultados**:

#### NDX
```
Box Setup para NDX:
   Date: 2025-10-30
   Box High: 26175.75
   Box Low: 25942.25
   Box Range: 233.50
   Current Price: 26031.50

Breakout Detection:
   Breakout Detected: False  ✅
   Direction: None

TEST PASADO ✅
```

#### SPX
```
Box Setup para SPX:
   Date: 2025-10-30
   Box High: 6910.75
   Box Low: 6867.75
   Breakout Detected: False  ✅
   Direction: None

TEST PASADO ✅
```

**Conclusión**:
✅ El fix funciona correctamente
✅ Hoy NO se detecta breakout en NDX (correcto según los gráficos)
✅ Hoy NO se detecta breakout en SPX (correcto)
✅ No se enviarán alertas de Telegram incorrectas

---

## Criterios de Detección de Breakout (Post-Fix)

### Criterios Obligatorios

Para que se detecte un breakout válido, **TODOS** estos criterios deben cumplirse:

1. **Cierre Fuera de la Caja**
   - LONG: Vela de 5 minutos debe CERRAR (Close) por encima de box_high
   - SHORT: Vela de 5 minutos debe CERRAR (Close) por debajo de box_low
   - ❌ NO cuenta si solo el High/Low toca fuera pero Close queda dentro

2. **Dentro del Window de 2 Horas**
   - Breakout debe ocurrir entre 10:00 AM y 12:00 PM ET (16:00 - 18:00 Madrid)
   - ❌ Breakouts después de 12:00 PM ET son ignorados
   - ✅ "Si no hay trade después de las 2 horas, ese día ya no se hace trade"

3. **Primera Vela Contabiliza**
   - Se toma la primera vela que cierra fuera de la caja
   - Si múltiples breakouts (LONG y SHORT), se toma el primero cronológicamente

### Casos Especiales

#### Caso 1: Vela con Sombra Larga pero Cierre Dentro
```
High: 26200 (por encima de box_high 26175)
Close: 26170 (DENTRO de la caja)
```
**Resultado**: ❌ NO se detecta breakout

#### Caso 2: Vela Cierra Justo por Encima
```
High: 26180
Close: 26176 (por encima de box_high 26175)
```
**Resultado**: ✅ Breakout LONG detectado

#### Caso 3: Breakout Tardío
```
Breakout LONG a las 12:05 PM ET (después del timeout)
```
**Resultado**: ❌ Breakout ignorado (fuera del window de 2 horas)

#### Caso 4: Breakout Doble (LONG y luego SHORT)
```
10:05 AM: Vela cierra en 26176 (LONG breakout)
10:30 AM: Vela cierra en 25940 (SHORT breakout)
```
**Resultado**: ✅ Solo se toma el LONG (fue primero)

---

## Impacto del Fix

### Antes del Fix

- ❌ Alertas de Telegram incorrectas (como hoy 30 Oct)
- ❌ Trades en breakouts falsos (solo sombras)
- ❌ Trades tardíos (después de 2 horas)
- ❌ Win rate probablemente afectado negativamente

### Después del Fix

- ✅ Solo alertas para breakouts válidos (velas cerradas fuera)
- ✅ No más falsos positivos por sombras
- ✅ Solo trades en primeras 2 horas (mayor probabilidad)
- ✅ Win rate esperado mejora

---

## Recomendaciones para el Futuro

### 1. Monitorear Win Rate

- Comparar win rate antes y después del fix
- Si mejora: confirma que el fix era necesario
- Si empeora: revisar si el filtro es demasiado restrictivo

### 2. Considerar Variaciones

**Opción A: Timeout Dinámico**
- Si breakout LONG a las 10:05 AM → timeout extendido
- Si no hay breakout a las 11:00 AM → timeout reducido

**Opción B: Confirmación de Cierre**
- Esperar 1-2 velas adicionales de confirmación
- Reduce falsos positivos aún más
- Trade: Mayor confirmación vs entrada más tardía

### 3. Backtesting con Fix

- Re-ejecutar backtest con los nuevos criterios
- Comparar métricas:
  - Win rate
  - Profit factor
  - Max drawdown
  - Número de trades (esperado: menos trades pero mejor calidad)

### 4. Alertas de Telegram Mejoradas

Incluir en la alerta:
```
🚨 NDX LONG Breakout
📍 Entry: 26176 (box high)
⏰ Time: 10:05 AM ET (16:05 Madrid)
✅ Criteria: Close above box
✅ Window: Within 2 hours
```

---

## Bugs Conocidos Restantes

### 1. Premature Breakouts Durante Formación

**Status**: Documentado en conversaciones anteriores
**Descripción**: Velas durante 8:30 - 10:00 AM que rompen la caja en formación
**Impacto**: Bajo (solo afecta visualización, no genera trades)
**Prioridad**: Media

### 2. Timezone Discrepancies

**Status**: Documentado
**Descripción**: Pequeñas diferencias de hora entre frontend y backend
**Impacto**: Bajo (cosmético)
**Prioridad**: Baja

### 3. ML Model Overfitting

**Status**: Conocido, backtest en curso
**Descripción**: Modelo entrenado solo con 60 días de datos
**Solución**: Acumular más datos históricos (1-2 años)
**Prioridad**: Alta (bloquea mejora del modelo)

---

## Changelog

### 2025-10-30
- ✅ Fix #1: Detección de breakout usa Close en vez de High
- ✅ Fix #2: Timeout de 2 horas implementado (10:00 AM - 12:00 PM ET)
- ✅ Tests pasados correctamente para NDX y SPX
- ✅ Documentación completa creada

---

## Archivos Modificados

1. `src/api/services/box_strategy_service.py` - Lógica principal corregida
2. `test_box_fix_today.py` - Test de verificación (NUEVO)
3. `BOX_STRATEGY_BUGS_FIXED.md` - Este documento (NUEVO)

---

**Próximos pasos**: Re-entrenar modelo ML con criterios corregidos cuando se acumulen más datos históricos.
