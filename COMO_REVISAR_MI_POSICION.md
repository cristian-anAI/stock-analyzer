# ¿Cómo Revisar Mi Posición? - Guía Rápida

Guía ultra-simple para saber **CUÁNDO VENDER** tu posición actual del NASDAQ (o cualquier mercado).

---

## 🚀 Opción 1: Revisión INMEDIATA (1 minuto)

### Paso 1: Asegúrate de que el API está corriendo

```bash
python run_api.py
```

Deja esta ventana abierta en background.

### Paso 2: Revisa tu posición AHORA

```bash
python check_now.py
```

**El script te preguntará**:
```
Mercado (NDX/SPX/etc.) [NDX]: NDX
Precio de entrada: 21050
Stop loss: 21035
```

**Output**:
```
================================================================================
                        🚨 ¿QUÉ HACER CON MI POSICIÓN?
================================================================================

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                        ┃
┃      🔴🔴🔴 VENDER AHORA - CERRAR POSICIÓN INMEDIATAMENTE 🔴🔴🔴       ┃
┃                                                                        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

✅ ACCIÓN:
   • Cerrar al MERCADO inmediatamente
   • Asegurar profit de 1.2R (+18 puntos)
   • NO esperar más - Riesgo ALTO de reversión

⚠️  RAZÓN:
   CLOSE NOW: Strong signals suggest price exhaustion. Exhaustion level: STRONG,
   Momentum weakening: true, Next TP probability only 28%. Better to secure
   current profit of 1.2R.
```

---

## 🔄 Opción 2: Monitoreo Continuo (Auto-refresh cada 15 min)

### Para posiciones que quieres monitorear durante horas

```bash
python monitor_my_position.py --market NDX --entry 21050 --stop 21035
```

**Qué hace**:
- Actualiza cada 15 minutos automáticamente
- Muestra precio actual y P&L en tiempo real
- Te ALERTA cuando hay señal de VENDER
- Guarda log de todas las actualizaciones

**Output**:
```
==================================================================================
                    🎯 MONITOR DE POSICIÓN EN TIEMPO REAL
==================================================================================

Update #3 - 14:35:00
Próxima actualización en 15 minutos...

─────────────────────────────────────────────────────────────────────────────────
INFORMACIÓN DEL TRADE
─────────────────────────────────────────────────────────────────────────────────
Mercado:          NDX
Dirección:        LONG
Entry:            21050.00
Stop Loss:        21035.00
Precio Actual:    21068.50

─────────────────────────────────────────────────────────────────────────────────
PROFIT & LOSS
─────────────────────────────────────────────────────────────────────────────────
🟢 P&L:             +18.50 puntos (+0.09%)
🟢 P&L en R:         +1.23R

✅ TP1 (1R):         21065.00
⏳ TP2 (2R):         21080.00
⏳ TP3 (3R):         21095.00

==================================================================================
                        ANÁLISIS DE SEÑALES DE SALIDA
==================================================================================

🟡 Señal de Agotamiento:  MODERATE
🟡 RSI Divergencia:       MODERATE_BEARISH
🔴 Momentum:              DEBILITÁNDOSE

📊 Próximo Objetivo:     TP2 @ 21080.00
   Distancia:           0.77R
   Probabilidad:        45.0%
   Confianza ML:        72.0%

==================================================================================
                        🚨 RECOMENDACIÓN DE ACCIÓN
==================================================================================

╔════════════════════════════════════════════════════════════════════════════════╗
║                                                                                ║
║                🟡 ACTIVAR TRAILING STOP - PROTEGER PROFIT                     ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝

⚠️  RAZÓN:
   TRAIL STOP: Some exhaustion signals detected (MODERATE), but 45% chance of
   reaching TP2. Use trailing stop to protect 1.23R profit while allowing upside.

✅ ACCIÓN SUGERIDA:
   1. Mover Stop Loss a: 21062.50
   2. Proteger profit de 0.86R mínimo
   3. Dejar correr si continúa favorable
```

---

## 📊 ¿Qué Significan las Señales?

### 🔴 VENDER AHORA (CLOSE_NOW)

**Cuándo aparece**:
- Divergencia RSI FUERTE (precio sube, RSI baja)
- Momentum muy débil
- Alta probabilidad de reversión

**Qué hacer**:
1. Cerrar al mercado INMEDIATAMENTE
2. No esperar más
3. Asegurar el profit actual

**Ejemplo real**:
```
Exhaustion: STRONG
RSI Divergence: STRONG_BEARISH
Momentum: Weakening
→ Probabilidad de reversión: 70%+
→ ACCIÓN: Vender YA
```

---

### 🟡 TRAILING STOP (TRAIL_STOP)

**Cuándo aparece**:
- Divergencia RSI MODERADA
- Momentum débil pero no crítico
- Aún hay probabilidad de alcanzar próximo TP (40-60%)

**Qué hacer**:
1. Mover stop loss cerca del precio actual
2. Proteger la mayor parte del profit
3. Dejar espacio para que siga subiendo

**Ejemplo de trailing stop**:
```
Precio actual: 21070
Entry: 21050
Profit: 20 puntos (1.33R)

Trailing Stop sugerido: 21062 (protege 0.8R)
→ Si sube más: ganas más
→ Si revierte: sales con 0.8R asegurado
```

---

### 🟢 MANTENER (HOLD)

**Cuándo aparece**:
- Sin divergencias RSI significativas
- Momentum fuerte
- Alta probabilidad de alcanzar próximo TP (>60%)

**Qué hacer**:
1. NO vender todavía
2. Esperar próximo TP
3. Seguir monitoreando cada 15 min

**Ejemplo**:
```
Exhaustion: NONE
RSI Divergence: NONE
Momentum: Strong
TP2 Probability: 72%
→ ACCIÓN: Mantener hasta TP2
```

---

## 🎯 Casos de Uso Típicos

### Caso 1: "Alcancé TP1, ¿vendo o espero TP2?"

```bash
python check_now.py
```

**Si dice CLOSE_NOW** → Vende en TP1
**Si dice TRAIL_STOP** → Mueve stop a breakeven, deja correr
**Si dice HOLD** → Espera TP2

---

### Caso 2: "Estoy en profit, ¿sigo esperando?"

```bash
python monitor_my_position.py --market NDX --entry TU_ENTRY --stop TU_STOP
```

Deja corriendo y te avisará automáticamente cada 15 min.

---

### Caso 3: "Quiero saber AHORA si vender (estoy nervioso)"

```bash
python check_now.py
```

Te da la respuesta en 10 segundos.

---

## 🔔 Interpretación de Análisis Detallado

### RSI Divergence

```
STRONG_BEARISH (-1.0 a -0.7)
→ 🔴 Precio hace nuevo máximo pero RSI baja fuerte
→ Reversión INMINENTE
→ VENDER AHORA

MODERATE_BEARISH (-0.7 a -0.3)
→ 🟡 Señal de agotamiento moderada
→ Considerar trailing stop

WEAK_BEARISH (-0.3 a -0.1)
→ 🟠 Señal débil, monitorear

NONE (cerca de 0)
→ 🟢 Sin divergencia, seguro continuar
```

### Momentum

```
DEBILITÁNDOSE
→ EMA rápida se acerca a EMA lenta
→ MACD cruza señal hacia abajo
→ Pérdida de fuerza

FUERTE
→ EMAs separándose
→ MACD por encima de señal
→ Impulso continúa
```

---

## ⚡ Comandos Rápidos

```bash
# Revisar AHORA (manual)
python check_now.py

# Monitorear continuo (auto cada 15 min)
python monitor_my_position.py --market NDX --entry 21050 --stop 21035

# Monitorear con intervalos personalizados (cada 5 min)
python monitor_my_position.py --market NDX --entry 21050 --stop 21035 --interval 5

# Ver ejemplo (sin necesidad de especificar entry/stop)
python check_now.py
# → Te preguntará los datos
```

---

## 🚨 IMPORTANTE: Cuándo Confiar en las Señales

### Alta Confianza (>75%)

```
Exhaustion: STRONG o NONE
Momentum: Muy claro (muy débil o muy fuerte)
RSI Divergence: STRONG o NONE

→ Seguir recomendación al pie de la letra
```

### Media Confianza (50-75%)

```
Exhaustion: MODERATE
Señales mixtas

→ Usar trailing stop como compromiso
```

### Baja Confianza (<50%)

```
Señales contradictorias
Datos insuficientes

→ Usar criterio personal + trailing stop conservador
```

---

## 📝 Ejemplo Completo: Tu Trade de HOY

### Setup
```
Mercado: NDX
Entry: 21050 (10:05 AM)
Stop: 21035
TP1: 21065 (1R)
TP2: 21080 (2R)
TP3: 21095 (3R)
```

### 11:05 AM - Alcanzas TP1 (21065)

```bash
python check_now.py --market NDX --entry 21050 --stop 21035
```

**Posible resultado**:
```
🟡 TRAILING STOP

Exhaustion: MODERATE
RSI Divergence: MODERATE_BEARISH
TP2 Probability: 48%

ACCIÓN: Mover stop a 21058
→ Protege 0.53R
→ Si llega TP2: ganas 2R
→ Si revierte: sales con 0.53R
```

**Tu decisión**: Mover stop a 21058, esperar TP2

### 11:20 AM - Precio en 21072

```bash
python check_now.py --market NDX --entry 21050 --stop 21035
```

**Posible resultado**:
```
🔴 VENDER AHORA

Exhaustion: STRONG
RSI Divergence: STRONG_BEARISH
TP2 Probability: 22%

ACCIÓN: Cerrar al mercado
→ Asegurar 1.47R (22 puntos)
→ No esperar más
```

**Tu decisión**: Vender en 21072, asegurar 1.47R

---

## ✅ Checklist Pre-Trade

Antes de abrir un trade, prepara:

```
[ ] Entry price
[ ] Stop loss
[ ] Calcular TP1, TP2, TP3
[ ] Tener API corriendo (python run_api.py)
[ ] Tener check_now.py listo para usar
```

Después de alcanzar TP1:

```
[ ] Ejecutar: python check_now.py
[ ] Leer recomendación
[ ] Actuar según señal (CLOSE/TRAIL/HOLD)
[ ] Si TRAIL: Mover stop loss
[ ] Si HOLD: Revisar cada 15 min
```

---

**¡Listo! Ahora sabes exactamente cuándo vender tu posición del NASDAQ!** 🎯
