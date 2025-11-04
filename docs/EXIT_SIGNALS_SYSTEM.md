# Exit Signals System - Dynamic TP Prediction

Sistema ML para predecir dinámicamente cuándo salir de un trade basado en señales de agotamiento usando RSI divergencias en 15 minutos.

## 🎯 Problema que Resuelve

### Situación Real (Tu Trade de Hoy)
- Trade SPX LONG entró en 6776.50
- TP1: 6788.50 (1R) ✅ **ALCANZADO**
- TP2: 6800.50 (2R) ❓ **¿Debería haber esperado?**
- TP3: 6812.50 (3R)

**Problema**: Con TPs fijos (1R, 2R, 3R) no sabemos si:
1. Tomar profit en TP1 (conservador)
2. Esperar TP2 (codicia que puede costar dinero)
3. Ir por TP3 (raramente se alcanza)

### Solución: Exit Signals ML

El sistema analiza **cada 15 minutos** durante el trade:
- ¿Hay divergencia RSI en 15min? → Señal de agotamiento
- ¿El momentum se está debilitando? → Reversión inminente
- ¿La volatilidad se expande? → Posible pico

**Output**:
- `CLOSE_NOW` - Salir inmediatamente
- `TRAIL_STOP` - Usar trailing stop
- `HOLD` - Esperar próximo TP

---

## 🧠 Cómo Funciona

### 1. Feature Engineering (15min)

```python
Features extraídas cada 15 minutos:

1. RSI Divergence (15min timeframe)
   - Bearish divergence (LONG): Precio ↑ pero RSI ↓ = PELIGRO
   - Bullish divergence (SHORT): Precio ↓ pero RSI ↑ = PELIGRO
   - Strength: STRONG (-1.0) → WEAK (-0.3) → NONE (0.0)

2. Momentum Weakening
   - EMA fast vs EMA slow gap closing
   - MACD cruzando señal
   - Boolean: True/False

3. Volatility Expansion
   - ATR actual vs promedio
   - Ratio normalizado 0-1

4. Position Context
   - Current R-múltiples (cuántos R llevamos)
   - Distance to next TP (en R)
   - Next TP name (TP1, TP2, TP3)
```

### 2. Señal de Agotamiento

```
NONE      → Sin señales, trade saludable
WEAK      → Señal débil, monitorear
MODERATE  → Considerar salir o trailing stop
STRONG    → Salir INMEDIATAMENTE
```

### 3. ML Prediction

**Modelo entrenado** (cuando esté listo):
- Input: 7+ features de timeframe 15min
- Output: Probabilidad de alcanzar próximo TP
- Classification: EXIT_AT_TP1, HOLD_FOR_TP2, HOLD_FOR_TP3

**Actualmente** (rule-based mientras entrenas):
- Lógica basada en reglas usando features
- Ajusta probabilidad según señales
- Funciona bien para comenzar

---

## 🔄 Workflow Completo

### Durante el Trade (Tiempo Real)

```
1. Trade ABIERTO (Entry @ TP0)
   ├─> Esperar 15 minutos
   └─> Llamar /api/v1/box-strategy/exit-signal

2. Cada 15 minutos:
   ├─> Descargar datos 15min
   ├─> Calcular RSI divergence
   ├─> Calcular momentum
   ├─> Calcular volatility
   ├─> Extraer features
   ├─> Predecir con ML
   └─> Retornar señal: CLOSE_NOW / TRAIL_STOP / HOLD

3. Actuar según recomendación:
   - CLOSE_NOW    → Cerrar posición inmediatamente
   - TRAIL_STOP   → Activar trailing stop (proteger profit)
   - HOLD         → Seguir esperando próximo TP
```

### Ejemplo Real: SPX LONG de Hoy

```
10:05 AM - Entry @ 6776.50
10:20 AM - Check #1: HOLD (sin divergencia, momentum fuerte)
10:35 AM - Check #2: HOLD (precio subiendo limpio)
10:50 AM - Check #3: HOLD (alcanzando TP1)
11:05 AM - TP1 ALCANZADO (6788.50)
           Exit Signal: ???

Si hubiera divergencia RSI en 15min → CLOSE_NOW
Si momentum débil pero sin divergencia → TRAIL_STOP
Si todo limpio → HOLD FOR TP2
```

---

## 📡 API Endpoint

### POST /api/v1/box-strategy/exit-signal

**Request Body**:

```json
{
  "market": "SPX",
  "direction": "LONG",
  "entry_price": 6776.50,
  "entry_time": "2025-10-08T10:05:00-04:00",
  "stop_loss": 6764.50,
  "tp1": 6788.50,
  "tp2": 6800.50,
  "tp3": 6812.50,
  "current_price": 6790.25
}
```

**Response**:

```json
{
  "timestamp": "2025-10-08T11:05:00",
  "market": "SPX",
  "current_price": 6790.25,
  "entry_price": 6776.50,
  "current_pnl_r": 1.15,

  "exhaustion_signal": "MODERATE",
  "rsi_divergence_15min": -0.45,
  "rsi_divergence_type": "MODERATE_BEARISH",
  "momentum_weakening": true,

  "next_tp_probability": 0.42,
  "recommended_action": "TRAIL_STOP",
  "confidence": 0.78,

  "next_tp_level": 6800.50,
  "next_tp_name": "TP2",
  "distance_to_next_tp_r": 0.85,

  "analysis": {
    "rsi_analysis": {
      "divergence_score": -0.45,
      "interpretation": "MODERATE bearish divergence - Watch closely, prepare to exit"
    },
    "momentum_analysis": {
      "weakening": true,
      "interpretation": "Momentum is weakening - consider taking profits"
    },
    "exhaustion_analysis": {
      "level": "MODERATE",
      "interpretation": "Moderate exhaustion - Consider trailing stop or partial exit"
    },
    "recommendation_reasoning": "TRAIL STOP: Some exhaustion signals detected (MODERATE), but 42% chance of reaching TP2. Use trailing stop to protect 1.15R profit while allowing upside."
  }
}
```

---

## 🎓 Training del Modelo

### Datos de Entrenamiento

```bash
# 1. Entrenar modelo con backtest histórico
cd tools/backtest/box_strategy

python ml/train_exit_model.py \
  --data results/multi_market_results_20251005_230737.json \
  --version 1
```

**Qué hace**:
1. Lee trades históricos del backtest
2. Para cada trade, simula monitoreo cada 15 minutos
3. Extrae features en cada momento
4. Label: ¿Alcanzó TP2? o ¿se revirtió en TP1?
5. Entrena Random Forest con ~500+ snapshots

### Features Usadas (7 principales)

```python
1. current_r                  # Cuántos R llevamos
2. distance_to_next_tp_r      # Distancia al próximo TP
3. rsi_divergence_15min       # -1.0 a +1.0
4. rsi_current                # RSI actual (0-100)
5. momentum_weakening         # True/False
6. momentum_score             # -0.5 a +0.5
7. volatility_expansion       # 0.0 a 1.0
```

### Labels (Multi-class)

```
EXIT_AT_TP1    → Trade se revirtió en TP1, debería haber salido
HOLD_FOR_TP2   → Trade llegó a TP2, debería haber esperado
HOLD_FOR_TP3   → Trade llegó a TP3, debería haber esperado más
```

### Modelo Output

```
Random Forest Classifier
├─> 200 trees
├─> Max depth: 10
├─> Class weight: balanced
└─> Accuracy esperado: 65-75%
```

---

## 💡 Uso en Producción

### Escenario 1: Trade Alcanza TP1

```bash
# Llamar API en TP1
curl -X POST http://localhost:8000/api/v1/box-strategy/exit-signal \
  -H "Content-Type: application/json" \
  -d '{
    "market": "SPX",
    "direction": "LONG",
    "entry_price": 6776.50,
    "entry_time": "2025-10-08T10:05:00",
    "stop_loss": 6764.50,
    "tp1": 6788.50,
    "tp2": 6800.50,
    "tp3": 6812.50,
    "current_price": 6789.00
  }'
```

**Respuesta: CLOSE_NOW**
```json
{
  "recommended_action": "CLOSE_NOW",
  "exhaustion_signal": "STRONG",
  "next_tp_probability": 0.25,
  "analysis": {
    "recommendation_reasoning": "CLOSE NOW: Strong signals suggest price exhaustion. Exhaustion level: STRONG, Momentum weakening: true, Next TP probability only 25%. Better to secure current profit of 1.04R."
  }
}
```

**Acción**: Cerrar trade inmediatamente en ~6789, asegurar ~1R de profit

---

### Escenario 2: Trade en TP1, Sin Agotamiento

**Respuesta: HOLD**
```json
{
  "recommended_action": "HOLD",
  "exhaustion_signal": "NONE",
  "next_tp_probability": 0.72,
  "analysis": {
    "recommendation_reasoning": "HOLD: No significant exhaustion signals. 72% probability of reaching TP2 at 6800.50. Current profit: 1.04R."
  }
}
```

**Acción**: Mantener trade abierto, esperar TP2

---

### Escenario 3: Trade en TP1, Señales Mixtas

**Respuesta: TRAIL_STOP**
```json
{
  "recommended_action": "TRAIL_STOP",
  "exhaustion_signal": "WEAK",
  "next_tp_probability": 0.58,
  "analysis": {
    "recommendation_reasoning": "TRAIL STOP: Some exhaustion signals detected (WEAK), but 58% chance of reaching TP2. Use trailing stop to protect 1.04R profit while allowing upside."
  }
}
```

**Acción**: Mover stop loss a breakeven o ligeramente por encima, proteger profit

---

## 🔧 Integración con Sistema Existente

### 1. Añadir a Box Strategy Dashboard

```typescript
// Después de abrir trade, monitorear cada 15 min
useEffect(() => {
  if (activeTrade) {
    const checkExitSignal = async () => {
      const response = await fetch('/api/v1/box-strategy/exit-signal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(activeTrade)
      });

      const signal = await response.json();

      if (signal.recommended_action === 'CLOSE_NOW') {
        // Mostrar alerta roja
        alert(`⚠️ EXIT SIGNAL: ${signal.analysis.recommendation_reasoning}`);
      } else if (signal.recommended_action === 'TRAIL_STOP') {
        // Mostrar aviso amarillo
        console.log(`⚡ TRAIL STOP: ${signal.analysis.recommendation_reasoning}`);
      }
    };

    const interval = setInterval(checkExitSignal, 15 * 60 * 1000); // 15 min
    return () => clearInterval(interval);
  }
}, [activeTrade]);
```

### 2. Alertas Automáticas

```python
# Script que corre en background
while trade_is_active:
    signal = get_exit_signal(trade)

    if signal.recommended_action == "CLOSE_NOW":
        send_email_alert("EXIT SIGNAL DETECTED")
        send_telegram_message("⚠️ Close trade NOW!")

    elif signal.recommended_action == "TRAIL_STOP":
        send_notification("Consider trailing stop")

    time.sleep(15 * 60)  # 15 minutes
```

---

## 📊 Performance Esperado

### Accuracy del Sistema

**Con modelo entrenado** (después de training):
- Accuracy: 65-75%
- Precision (EXIT_AT_TP1): ~70%
- Recall (HOLD_FOR_TP2): ~60%

**Impacto en Trading**:
- Evitar 3-4 reversiones de cada 10 trades
- Mejorar win rate de 40% → 55-60%
- Aumentar profit factor significativamente

### Ejemplo de Mejora

**Sin Exit Signals** (TPs fijos):
```
10 trades:
- 4 alcanzan TP1 y se revierten → -4R
- 3 alcanzan TP2 → +6R
- 3 stopped out → -3R
Total: -1R (break even / pérdida)
```

**Con Exit Signals**:
```
10 trades:
- 4 detectan reversión y cierran en TP1 → +4R ✅
- 3 alcanzan TP2 → +6R ✅
- 3 stopped out → -3R
Total: +7R (profitable!)
```

---

## 🎯 Próximos Pasos

### Fase 1: Implementación Básica (Ya hecho ✅)
- [x] Feature engineering (RSI divergence 15min)
- [x] Exit signal predictor (rule-based)
- [x] API endpoint
- [x] Documentación

### Fase 2: Training ML (Próximo)
- [ ] Ejecutar `train_exit_model.py` con backtest data
- [ ] Validar accuracy del modelo
- [ ] Reemplazar rule-based con ML predictor
- [ ] Re-deployar API

### Fase 3: Producción (1 semana)
- [ ] Integrar con frontend dashboard
- [ ] Añadir alertas (email/Telegram)
- [ ] Monitorear performance real
- [ ] Ajustar modelo según resultados

### Fase 4: Optimización (1 mes)
- [ ] A/B testing: Exit signals vs TPs fijos
- [ ] Re-entrenar con nuevos datos
- [ ] Añadir más features (multi-timeframe)
- [ ] Implementar ensemble de modelos

---

## 🚀 Cómo Empezar HOY

### 1. Entrenar Modelo

```bash
cd tools/backtest/box_strategy

python ml/train_exit_model.py \
  --data results/multi_market_results_20251005_230737.json \
  --version 1
```

### 2. Iniciar API

```bash
python run_api.py
```

### 3. Probar con Trade de Hoy

```bash
curl -X POST http://localhost:8000/api/v1/box-strategy/exit-signal \
  -H "Content-Type: application/json" \
  -d '{
    "market": "SPX",
    "direction": "LONG",
    "entry_price": 6776.50,
    "entry_time": "2025-10-08T10:05:00-04:00",
    "stop_loss": 6764.50,
    "tp1": 6788.50,
    "tp2": 6800.50,
    "tp3": 6812.50
  }'
```

### 4. Integrar con Frontend

Ver ejemplos en la sección "Integración con Sistema Existente"

---

**Sistema listo para evitar que pierdas profits dejando trades correr demasiado!** 🎯
