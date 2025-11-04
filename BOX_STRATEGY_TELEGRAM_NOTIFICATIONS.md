# Box Strategy - Telegram Notifications System

**Fecha**: 28 Octubre 2025
**Status**: ✅ SISTEMA IMPLEMENTADO

---

## 🎯 Objetivo

Sistema automático de monitoreo de la estrategia de caja (Box Strategy) para **NASDAQ (NDX)**, **S&P 500 (SPX)** y **Russell 2000 (RTY)** con notificaciones Telegram cuando se detectan breakouts.

---

## 📦 Componentes Implementados

### 1. **Servicio de Notificaciones Telegram**
**Archivo**: `src/api/services/telegram_service.py`

#### Nuevos métodos añadidos:

**`send_box_trade_notification()`** - Notificación de apertura de trade
- Market (NDX, SPX, RTY)
- Dirección (LONG/SHORT)
- Entry Price
- Stop Loss
- TP1, TP2, TP3 con ratios R:R
- Datos de la caja (box_high, box_low, box_range)
- Riesgo en puntos
- **ML Confidence** (HIGH/MEDIUM/LOW) con probabilidad

**`send_box_trade_exit_notification()`** - Notificación de cierre de trade
- Precio de entrada y salida
- Nivel de salida (TP1, TP2, TP3, STOP_LOSS, MANUAL)
- P&L en $ y puntos
- Ratio R:R alcanzado

---

### 2. **Monitor de Box Strategy**
**Archivo**: `src/api/services/box_strategy_monitor.py`

#### Funcionalidades:

**Monitoreo de Breakouts**:
- Revisa NDX, SPX, RTY cada minuto
- Detecta cuando se completa la caja (8:30-10:00 AM ET)
- Identifica breakouts (precio cierra arriba/abajo de la caja)
- Obtiene predicción ML de confianza
- Envía notificación Telegram automática

**Gestión de Trades Activos**:
- Trackea trades abiertos
- Monitorea si TP1 es alcanzado
- **Mueve Stop Loss a Break Even automáticamente** después de TP1
- Envía notificación cuando TP1 es alcanzado

**Prevención de Duplicados**:
- Mantiene registro de breakouts notificados
- Usa clave única: `{MARKET}_{DATE}_{DIRECTION}`
- Evita notificaciones duplicadas del mismo breakout

---

### 3. **Integración con Background Scheduler**
**Archivo**: `src/api/services/background_scheduler.py`

#### Configuración:
```python
self.box_strategy_interval = 60  # 1 minuto
```

#### Ciclo de Monitoreo:
1. Cada 60 segundos revisa los 3 mercados (NDX, SPX, RTY)
2. Detecta nuevos breakouts
3. Envía notificaciones Telegram
4. Monitorea trades activos para TP1
5. Mueve SL a break even automáticamente

---

## 📋 Reglas de Trading (Box Strategy)

### **Formación de la Caja**
- **Horario**: 8:30 AM - 10:00 AM ET (1.5 horas)
- **Box High**: Precio máximo en el período
- **Box Low**: Precio mínimo en el período
- **Box Range**: Diferencia entre high y low

### **Señales de Entrada**

#### **LONG** (Compra):
- Primera vela de 5 min que cierra **ARRIBA** de `box_high`
- **Entry**: Orden limit en `box_high`
- **Stop Loss**: `box_low`
- **Ventana de ejecución**: 2 horas después del cierre de la caja (hasta 12:00 PM ET)

#### **SHORT** (Venta):
- Primera vela de 5 min que cierra **DEBAJO** de `box_low`
- **Entry**: Orden limit en `box_low`
- **Stop Loss**: `box_high`
- **Ventana de ejecución**: 2 horas después del cierre de la caja (hasta 12:00 PM ET)

### **Take Profits**

#### **TP1 (50% de la posición)**: Ratio 1:1
- Si LONG: `entry_price + risk_points`
- Si SHORT: `entry_price - risk_points`
- **ACCIÓN**: Cuando se alcanza TP1 → **Mover SL a Break Even**

#### **TP2 (25% de la posición)**: RSI Divergence 15 min
- **LONG**: Esperar divergencia bajista en RSI 15 min
  - Precio hace higher high
  - RSI hace lower high
- **SHORT**: Esperar divergencia alcista en RSI 15 min
  - Precio hace lower low
  - RSI hace higher low

#### **TP3 (25% de la posición)**: RSI Divergence 1 hora
- **LONG**: Esperar divergencia bajista en RSI 1 hora
- **SHORT**: Esperar divergencia alcista en RSI 1 hora
- O señales de exhaustión (agotamiento del movimiento)

---

## 🤖 ML Confidence Levels

El sistema usa Machine Learning (Random Forest + XGBoost) para evaluar cada breakout:

### **HIGH Confidence** (≥75% probabilidad)
- 🎯 **Posición completa** (100%)
- Trade con alta probabilidad de éxito
- Todos los indicadores alineados

### **MEDIUM Confidence** (50-75% probabilidad)
- ⚡ **Posición reducida** (60%)
- Trade con probabilidad moderada
- Algunos indicadores no alineados

### **LOW Confidence** (<50% probabilidad)
- ⚠️ **Skip trade** (0%)
- No operar - baja probabilidad de éxito
- Indicadores desfavorables

---

## 📱 Formato de Notificaciones Telegram

### **Apertura de Trade**
```
🟢 BOX STRATEGY - COMPRA (LONG)

Market: NDX
Dirección: LONG
Entrada: $15,245.50
Stop Loss: $15,210.00
Riesgo: 35.50 puntos

🎯 ML Confidence: HIGH (78.5%)

📊 CAJA (Box)
Alto: $15,245.50
Bajo: $15,210.00
Rango: 35.50 puntos

🎯 OBJETIVOS (Take Profits)
TP1 (50%): $15,281.00 | R:R 1.00x
TP2 (25%): $15,316.50 | R:R 2.00x
TP3 (25%): $15,352.00 | R:R 3.00x

2025-10-28 09:45:23
```

### **TP1 Alcanzado**
```
🎯 TP1 ALCANZADO - NDX

Dirección: LONG
Precio actual: $15,281.00
TP1: $15,281.00 ✅

🛡️ Stop Loss movido a Break Even
Nuevo SL: $15,245.50

2025-10-28 10:15:47
```

### **Cierre de Trade**
```
💰 BOX STRATEGY - GANANCIA

Market: NDX
Dirección: LONG
🎯 Salida: TP2

Precio entrada: $15,245.50
Precio salida: $15,316.50

P&L: $1,775.00
Puntos: +71.00
R:R: 2.00x

2025-10-28 11:30:12
```

---

## 🔧 Configuración

### **Variables de Entorno** (`.env.prod`)
```env
TELEGRAM_BOT_TOKEN=tu_bot_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id_numerico
```

### **Mercados Monitoreados**
```python
self.monitored_markets = ["NDX", "SPX", "RTY"]
```

### **Intervalo de Monitoreo**
```python
self.box_strategy_interval = 60  # 1 minuto
```

---

## 📊 Flujo de Operación

```
┌─────────────────────────────────────────────────────────────────┐
│                   BOX STRATEGY MONITORING                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. DETECCIÓN DE CAJA (8:30-10:00 AM ET)                        │
│     └─> Calcula box_high, box_low, box_range                    │
│                                                                   │
│  2. DETECCIÓN DE BREAKOUT (10:00-12:00 PM ET)                   │
│     └─> Primera vela 5min que cierra fuera de la caja           │
│         ├─> Breakout LONG (cierra arriba de box_high)           │
│         └─> Breakout SHORT (cierra abajo de box_low)            │
│                                                                   │
│  3. EVALUACIÓN ML                                                │
│     └─> Random Forest + XGBoost predicción                      │
│         ├─> HIGH: 100% position size                            │
│         ├─> MEDIUM: 60% position size                           │
│         └─> LOW: Skip trade                                     │
│                                                                   │
│  4. NOTIFICACIÓN TELEGRAM                                        │
│     └─> Entry, SL, TP1/TP2/TP3, ML Confidence                  │
│                                                                   │
│  5. MONITOREO DE TRADE ACTIVO                                    │
│     └─> Detecta cuando TP1 es alcanzado                         │
│         └─> Mueve SL a Break Even                                │
│             └─> Envía notificación de TP1                       │
│                                                                   │
│  6. GESTIÓN DE SALIDA                                            │
│     ├─> TP1: Ratio 1:1 (cierra 50%)                            │
│     ├─> TP2: RSI divergence 15m (cierra 25%)                   │
│     ├─> TP3: RSI divergence 1h (cierra 25%)                    │
│     └─> STOP LOSS: Break even después de TP1                   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Archivos Modificados/Creados

### **Nuevos Archivos**:
1. `src/api/services/box_strategy_monitor.py` - Monitor principal
2. `BOX_STRATEGY_TELEGRAM_NOTIFICATIONS.md` - Esta documentación

### **Archivos Modificados**:
1. `src/api/services/telegram_service.py`
   - Línea 282-358: `send_box_trade_notification()`
   - Línea 360-417: `send_box_trade_exit_notification()`

2. `src/api/services/background_scheduler.py`
   - Línea 17: Import `box_strategy_monitor`
   - Línea 50: `box_strategy_interval = 60`
   - Línea 126: `last_box_strategy_run = 0`
   - Línea 176-179: Ciclo de monitoreo cada 60 segundos
   - Línea 512-529: Método `_run_box_strategy_monitor()`

---

## 🚀 Testing

### **Test Manual**
Puedes probar el sistema manualmente con:
```bash
python test_box_strategy_telegram.py
```

### **Verificar Estado del Scheduler**
```bash
curl http://localhost:8000/api/v1/autotrader/status
```

### **Ver Breakouts Actuales**
```bash
curl http://localhost:8000/api/v1/box-strategy/tradeable
```

---

## 📈 Próximos Pasos (Backtesting)

### **Análisis de TP2/TP3 Óptimos**
Para optimizar los niveles de TP2 y TP3:

1. **Recopilar Datos Históricos**:
   - Todos los breakouts de los últimos 6-12 meses
   - Para cada breakout, calcular:
     - Tiempo hasta primera divergencia RSI 15m
     - Tiempo hasta primera divergencia RSI 1h
     - Precio en cada divergencia
     - P&L si hubiera salido en cada nivel

2. **Análisis de Confianza ML**:
   - Correlación entre confianza ML y éxito de TP2/TP3
   - ¿Los trades HIGH confidence alcanzan TP2/TP3 más frecuentemente?
   - ¿Los trades MEDIUM confidence deberían usar TP2/TP3 más conservadores?

3. **Reglas Discrecionales**:
   - **HIGH Confidence**: Esperar TP2 y TP3 completos
   - **MEDIUM Confidence**: Salir antes si RSI 15m diverge, no esperar TP3
   - **LOW Confidence**: No operar (ya implementado)

4. **Métricas a Analizar**:
   - Win rate por nivel de TP (TP1/TP2/TP3)
   - Tiempo promedio en trade para cada TP
   - R:R promedio alcanzado
   - Máxima excursión favorable (MAE) vs adversa (MFE)

---

## ✅ Estado Actual

- ✅ Notificaciones Telegram para apertura de trade
- ✅ ML Confidence integrado en notificaciones
- ✅ Monitoreo automático de NDX, SPX, RTY
- ✅ Detección de TP1 y movimiento de SL a break even
- ✅ Prevención de notificaciones duplicadas
- ⏳ **PENDIENTE**: Backtesting para optimizar TP2/TP3
- ⏳ **PENDIENTE**: Implementar detección automática de divergencias RSI en tiempo real

---

## 🎓 Notas Importantes

1. **Horarios**: Todos los horarios son ET (Eastern Time - New York)
2. **Frecuencia**: El monitor revisa cada 60 segundos (configurable)
3. **Rate Limiting**: El sistema respeta los límites de la API de yfinance
4. **ML Models**: Usa modelos entrenados en `tools/backtest/box_strategy/models/`
5. **Persistencia**: Los breakouts notificados se guardan en memoria (se limpian cada 100 entradas)

---

**Documentación Relacionada**:
- [BOX_STRATEGY_COMPLETE_SUMMARY.md](BOX_STRATEGY_COMPLETE_SUMMARY.md)
- [BOX_STRATEGY_QUICKSTART.md](BOX_STRATEGY_QUICKSTART.md)
- [docs/BOX_STRATEGY_API.md](docs/BOX_STRATEGY_API.md)
