# Box Strategy - Frontend Integration Guide

**Fecha**: 28 Octubre 2025
**API Version**: v1
**Mercados**: NDX (NASDAQ), SPX (S&P 500), RTY (Russell 2000)

---

## 🎯 Objetivo

Integrar notificaciones y monitoreo de trades de **Box Strategy** en el frontend, mostrando:
- Trades activos (NDX, SPX, RTY)
- Predicciones ML con niveles de confianza
- Estado de TP1 y Stop Loss en Breakeven
- Divergencias RSI para optimizar salidas

---

## 📊 ML Y RSI DIVERGENCIAS - Explicación

### ¿El ML aprende de las divergencias RSI?

**✅ SÍ**, el sistema ML incluye divergencias RSI como features clave:

#### **Entry ML (Predicción de Breakout)**
```python
Feature: rsi_divergence_5min
Valores: -1 (bearish), 0 (none), +1 (bullish)
Uso: Detecta divergencias ANTES del breakout
```

El modelo Random Forest + XGBoost aprende:
- Si una divergencia alcista aumenta probabilidad de éxito en trades LONG
- Si una divergencia bajista aumenta probabilidad de éxito en trades SHORT
- La importancia relativa de la divergencia vs otros 48+ indicadores

#### **Exit ML (Predicción de TP2/TP3)**
```python
Feature: rsi_divergence_15min
Valores: STRONG_BEARISH, MODERATE_BEARISH, NONE, MODERATE_BULLISH, STRONG_BULLISH
Uso: Detecta AGOTAMIENTO durante el trade en curso
```

El modelo recomienda:
- **CLOSE_NOW**: Si detecta divergencia fuerte contra la posición
- **HOLD**: Si no hay divergencia, aguantar hasta próximo TP
- **TRAIL_STOP**: Si hay divergencia moderada, proteger ganancias

**Archivo de implementación**: `tools/backtest/box_strategy/ml/feature_engineering.py:265-266`

---

## 📡 ENDPOINTS API ACTUALIZADOS

### Base URL
```
http://localhost:8000
```

---

### 1. **GET /api/v1/box-strategy/dashboard**

**Descripción**: Dashboard general con estadísticas y trades activos

#### Request
```http
GET /api/v1/box-strategy/dashboard?ml_version=1
```

#### Response
```typescript
{
  timestamp: string; // ISO 8601
  ml_version: string; // "1"

  summary: {
    total_markets: number;
    pending_box: number;
    active_box: number;
    box_complete: number;
    breakouts: number;
    high_confidence: number;
    avg_win_probability: number;

    // ✨ NUEVOS CAMPOS
    active_trades_count: number;           // Trades activos en curso
    tp1_achieved_count: number;            // Trades que alcanzaron TP1
    stop_moved_to_breakeven_count: number; // Trades con SL en breakeven
  };

  markets_by_status: {
    pending: string[];
    active: string[];
    complete: string[];
  };

  high_confidence_setups: MarketData[];
  all_breakouts: MarketData[];
  all_markets: MarketData[];

  // ✨ NUEVA SECCIÓN
  active_trades_summary: Array<{
    market: string;              // "NDX", "SPX", "RTY"
    direction: string;           // "LONG" o "SHORT"
    entry_price: number;         // Precio de entrada
    entry_time: string;          // ISO timestamp
    stop_loss: number;           // Nivel de stop loss actual
    tp1: number;                 // Take Profit 1
    tp2: number;                 // Take Profit 2
    tp3: number;                 // Take Profit 3
    risk_points: number;         // Riesgo en puntos
    ml_confidence: string;       // "HIGH", "MEDIUM", "LOW"
    ml_win_probability: number;  // 0-100
    tp1_hit: boolean;            // TP1 alcanzado?
    stop_moved_to_breakeven: boolean; // SL movido a BE?
  }>;
}
```

#### Ejemplo de respuesta
```json
{
  "timestamp": "2025-10-28T14:30:00Z",
  "ml_version": "1",
  "summary": {
    "total_markets": 10,
    "pending_box": 5,
    "active_box": 2,
    "box_complete": 3,
    "breakouts": 2,
    "high_confidence": 1,
    "avg_win_probability": 0.785,
    "active_trades_count": 2,
    "tp1_achieved_count": 1,
    "stop_moved_to_breakeven_count": 1
  },
  "active_trades_summary": [
    {
      "market": "NDX",
      "direction": "LONG",
      "entry_price": 15245.50,
      "entry_time": "2025-10-28T09:45:23Z",
      "stop_loss": 15245.50,
      "tp1": 15281.00,
      "tp2": 15316.50,
      "tp3": 15352.00,
      "risk_points": 35.50,
      "ml_confidence": "HIGH",
      "ml_win_probability": 82.5,
      "tp1_hit": true,
      "stop_moved_to_breakeven": true
    },
    {
      "market": "SPX",
      "direction": "SHORT",
      "entry_price": 5820.00,
      "entry_time": "2025-10-28T10:15:47Z",
      "stop_loss": 5850.00,
      "tp1": 5790.00,
      "tp2": 5760.00,
      "tp3": 5730.00,
      "risk_points": 30.00,
      "ml_confidence": "MEDIUM",
      "ml_win_probability": 68.3,
      "tp1_hit": false,
      "stop_moved_to_breakeven": false
    }
  ]
}
```

---

### 2. **GET /api/v1/box-strategy/active-trades** ✨ NUEVO

**Descripción**: Detalle completo de trades activos

#### Request
```http
GET /api/v1/box-strategy/active-trades
```

#### Response
```typescript
{
  timestamp: string;
  active_trades_count: number;

  trades: Array<{
    market: string;              // "NDX", "SPX", "RTY"
    direction: "LONG" | "SHORT";
    entry_price: number;
    entry_time: string;
    stop_loss: number;
    current_stop_loss: number;   // Puede diferir si movido a BE
    tp1: number;
    tp2: number;
    tp3: number;
    box_high: number;
    box_low: number;
    box_range: number;
    risk_points: number;
    ml_confidence: "HIGH" | "MEDIUM" | "LOW";
    ml_win_probability: number;  // 0-100
    tp1_hit: boolean;
    stop_moved_to_breakeven: boolean;
    breakout_key: string;        // ID único del trade
  }>;
}
```

#### Ejemplo de respuesta
```json
{
  "timestamp": "2025-10-28T14:30:00Z",
  "active_trades_count": 2,
  "trades": [
    {
      "market": "NDX",
      "direction": "LONG",
      "entry_price": 15245.50,
      "entry_time": "2025-10-28T09:45:23Z",
      "stop_loss": 15245.50,
      "current_stop_loss": 15245.50,
      "tp1": 15281.00,
      "tp2": 15316.50,
      "tp3": 15352.00,
      "box_high": 15245.50,
      "box_low": 15210.00,
      "box_range": 35.50,
      "risk_points": 35.50,
      "ml_confidence": "HIGH",
      "ml_win_probability": 82.5,
      "tp1_hit": true,
      "stop_moved_to_breakeven": true,
      "breakout_key": "NDX_2025-10-28_LONG"
    }
  ]
}
```

---

## 🎨 UI COMPONENTS A IMPLEMENTAR

### **1. Active Box Trades Card**

**Ubicación**: Dashboard principal (arriba)

**Layout sugerido**:
```
┌────────────────────────────────────────────────────────────┐
│ 📦 ACTIVE BOX TRADES (2)                  [REFRESH] [1m]  │
├────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌─────────────────────────────────────────────────────┐  │
│ │ 🟢 NDX - LONG                    🎯 HIGH 82.5%      │  │
│ │ Entry: $15,245.50  │  SL: $15,245.50 (BE)           │  │
│ │ TP1: ✅ $15,281.00 │ TP2: $15,316.50 │ TP3: $15,352│  │
│ │ Risk: 35.5 pts     │  Entered: 09:45 AM             │  │
│ └─────────────────────────────────────────────────────┘  │
│                                                             │
│ ┌─────────────────────────────────────────────────────┐  │
│ │ 🔴 SPX - SHORT                   ⚡ MEDIUM 68.3%    │  │
│ │ Entry: $5,820.00   │  SL: $5,850.00                 │  │
│ │ TP1: $5,790.00 │ TP2: $5,760.00 │ TP3: $5,730.00   │  │
│ │ Risk: 30.0 pts     │  Entered: 10:15 AM             │  │
│ └─────────────────────────────────────────────────────┘  │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

**Colores por dirección**:
- 🟢 LONG: Verde (`bg-green-500`)
- 🔴 SHORT: Rojo (`bg-red-500`)

**Colores por ML Confidence**:
- 🎯 HIGH: Verde oscuro (`bg-green-700`, `text-white`)
- ⚡ MEDIUM: Amarillo (`bg-yellow-500`, `text-black`)
- ⚠️ LOW: Rojo (`bg-red-600`, `text-white`)

**Estados especiales**:
- TP1 alcanzado: Mostrar ✅ junto a TP1
- SL en Breakeven: Mostrar "(BE)" junto al SL
- Highlight del trade completo si TP1 alcanzado: Border verde grueso

---

### **2. Statistics Summary**

**Ubicación**: Dashboard principal (sidebar o top bar)

```
┌──────────────────────────────────────┐
│ 📊 BOX STRATEGY STATS               │
├──────────────────────────────────────┤
│ Active Trades:     2                 │
│ TP1 Achieved:      1 (50%)           │
│ SL at Breakeven:   1 (50%)           │
│ Avg ML Confidence: 78.5%             │
└──────────────────────────────────────┘
```

---

### **3. TypeScript Interfaces**

```typescript
// Active Trade
interface ActiveBoxTrade {
  market: string;
  direction: 'LONG' | 'SHORT';
  entry_price: number;
  entry_time: string;
  stop_loss: number;
  current_stop_loss: number;
  tp1: number;
  tp2: number;
  tp3: number;
  box_high: number;
  box_low: number;
  box_range: number;
  risk_points: number;
  ml_confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  ml_win_probability: number;
  tp1_hit: boolean;
  stop_moved_to_breakeven: boolean;
  breakout_key: string;
}

// Dashboard Summary (extendido)
interface BoxStrategyDashboardSummary {
  total_markets: number;
  pending_box: number;
  active_box: number;
  box_complete: number;
  breakouts: number;
  high_confidence: number;
  avg_win_probability: number;
  // NEW
  active_trades_count: number;
  tp1_achieved_count: number;
  stop_moved_to_breakeven_count: number;
}

// Active Trades Summary
interface ActiveTradesSummary {
  market: string;
  direction: string;
  entry_price: number;
  entry_time: string;
  stop_loss: number;
  tp1: number;
  tp2: number;
  tp3: number;
  risk_points: number;
  ml_confidence: string;
  ml_win_probability: number;
  tp1_hit: boolean;
  stop_moved_to_breakeven: boolean;
}
```

---

### **4. React Component Example**

```tsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface ActiveBoxTradesProps {
  apiBaseUrl?: string;
  refreshInterval?: number;
}

const ActiveBoxTrades: React.FC<ActiveBoxTradesProps> = ({
  apiBaseUrl = 'http://localhost:8000',
  refreshInterval = 60000 // 1 minute
}) => {
  const [trades, setTrades] = useState<ActiveBoxTrade[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const fetchActiveTrades = async () => {
    try {
      const response = await axios.get(
        `${apiBaseUrl}/api/v1/box-strategy/active-trades`
      );
      setTrades(response.data.trades);
      setLastUpdate(new Date());
      setLoading(false);
    } catch (error) {
      console.error('Error fetching active trades:', error);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActiveTrades();
    const interval = setInterval(fetchActiveTrades, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval]);

  const getConfidenceColor = (confidence: string) => {
    switch (confidence) {
      case 'HIGH': return 'bg-green-700 text-white';
      case 'MEDIUM': return 'bg-yellow-500 text-black';
      case 'LOW': return 'bg-red-600 text-white';
      default: return 'bg-gray-500 text-white';
    }
  };

  const getDirectionEmoji = (direction: string) => {
    return direction === 'LONG' ? '🟢' : '🔴';
  };

  const getConfidenceEmoji = (confidence: string) => {
    switch (confidence) {
      case 'HIGH': return '🎯';
      case 'MEDIUM': return '⚡';
      case 'LOW': return '⚠️';
      default: return '';
    }
  };

  if (loading) {
    return <div>Loading active trades...</div>;
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold">
          📦 Active Box Trades ({trades.length})
        </h2>
        <div className="text-sm text-gray-500">
          Last updated: {lastUpdate ? lastUpdate.toLocaleTimeString() : 'Never'}
        </div>
      </div>

      {trades.length === 0 ? (
        <p className="text-gray-500">No active trades</p>
      ) : (
        <div className="space-y-4">
          {trades.map((trade) => (
            <div
              key={trade.breakout_key}
              className={`border-2 rounded-lg p-4 ${
                trade.tp1_hit ? 'border-green-500' : 'border-gray-200'
              }`}
            >
              {/* Header */}
              <div className="flex justify-between items-start mb-3">
                <div className="text-xl font-bold">
                  {getDirectionEmoji(trade.direction)} {trade.market} - {trade.direction}
                </div>
                <div className={`px-3 py-1 rounded-full text-sm font-semibold ${getConfidenceColor(trade.ml_confidence)}`}>
                  {getConfidenceEmoji(trade.ml_confidence)} {trade.ml_confidence} {trade.ml_win_probability.toFixed(1)}%
                </div>
              </div>

              {/* Entry & Stop Loss */}
              <div className="grid grid-cols-2 gap-4 mb-3">
                <div>
                  <span className="text-gray-600">Entry:</span>{' '}
                  <span className="font-semibold">${trade.entry_price.toFixed(2)}</span>
                </div>
                <div>
                  <span className="text-gray-600">SL:</span>{' '}
                  <span className="font-semibold">${trade.stop_loss.toFixed(2)}</span>
                  {trade.stop_moved_to_breakeven && (
                    <span className="ml-2 text-green-600 font-bold">(BE)</span>
                  )}
                </div>
              </div>

              {/* Take Profits */}
              <div className="grid grid-cols-3 gap-2 mb-3">
                <div className="text-sm">
                  <div className="text-gray-600">TP1 (50%)</div>
                  <div className="font-semibold">
                    {trade.tp1_hit && '✅ '}${trade.tp1.toFixed(2)}
                  </div>
                </div>
                <div className="text-sm">
                  <div className="text-gray-600">TP2 (25%)</div>
                  <div className="font-semibold">${trade.tp2.toFixed(2)}</div>
                </div>
                <div className="text-sm">
                  <div className="text-gray-600">TP3 (25%)</div>
                  <div className="font-semibold">${trade.tp3.toFixed(2)}</div>
                </div>
              </div>

              {/* Additional Info */}
              <div className="grid grid-cols-2 gap-4 text-sm text-gray-600">
                <div>
                  Risk: {trade.risk_points.toFixed(1)} pts
                </div>
                <div>
                  Entered: {new Date(trade.entry_time).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ActiveBoxTrades;
```

---

## 📊 POLLING STRATEGY

**Intervalo recomendado**: 60 segundos (1 minuto)

```typescript
const POLLING_CONFIG = {
  dashboard: 60000,      // 60 segundos
  activeTrades: 60000,   // 60 segundos
  showLastUpdate: true   // Mostrar "Last updated: XX seconds ago"
};
```

**Implementación**:
```typescript
useEffect(() => {
  fetchData();
  const interval = setInterval(fetchData, POLLING_CONFIG.dashboard);
  return () => clearInterval(interval);
}, []);
```

---

## 🔔 NOTIFICACIONES (Opcional)

Si el frontend tiene sistema de notificaciones, mostrar alerta cuando:

1. **Nuevo breakout detectado**
   ```
   🟢 NDX - LONG Breakout Detected
   ML Confidence: HIGH (82.5%)
   Entry: $15,245.50
   ```

2. **TP1 alcanzado**
   ```
   🎯 TP1 HIT - NDX
   Stop Loss moved to Breakeven
   ```

3. **Divergencia RSI fuerte** (futuro)
   ```
   ⚠️ Strong RSI Divergence - NDX
   Consider taking profits
   ```

---

## 🎯 PRIORIDADES DE IMPLEMENTACIÓN

### **Fase 1: Básico (1-2 días)**
1. ✅ Crear componente `ActiveBoxTrades`
2. ✅ Integrar endpoint `/active-trades`
3. ✅ Mostrar trades con ML confidence
4. ✅ Polling cada 60 segundos

### **Fase 2: Mejorado (2-3 días)**
1. Actualizar dashboard con `active_trades_summary`
2. Estadísticas de TP1 achieved
3. Highlight de trades con TP1
4. Mostrar "Last updated" timestamp

### **Fase 3: Avanzado (futuro)**
1. RSI Divergence indicator en tiempo real
2. Historial de notificaciones
3. Gráficos de P&L por trade
4. Alertas browser

---

## 🧪 TESTING

### **Test con cURL**

**Dashboard actualizado**:
```bash
curl http://localhost:8000/api/v1/box-strategy/dashboard | jq .
```

**Active trades**:
```bash
curl http://localhost:8000/api/v1/box-strategy/active-trades | jq .
```

### **Casos de prueba**

1. **Sin trades activos**:
   - `active_trades_count: 0`
   - `active_trades_summary: []`

2. **1 trade sin TP1**:
   - `tp1_hit: false`
   - `stop_moved_to_breakeven: false`

3. **1 trade con TP1 alcanzado**:
   - `tp1_hit: true`
   - `stop_moved_to_breakeven: true`
   - `stop_loss == entry_price`

---

## 📞 CONTACTO Y SOPORTE

**Dudas sobre la API**: Consultar [docs/BOX_STRATEGY_API.md](docs/BOX_STRATEGY_API.md)

**Telegram Notifications**: Ver [BOX_STRATEGY_TELEGRAM_NOTIFICATIONS.md](BOX_STRATEGY_TELEGRAM_NOTIFICATIONS.md)

---

**¡Listo para integrar! 🚀**
