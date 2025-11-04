# Frontend Integration - PupupuV3 Scalping Strategy

## Nueva Pestaña: "Scalping 1-min" o "PupupuV3"

Crear una nueva pestaña/sección en el frontend junto a la estrategia Box existente.

## Endpoints Disponibles

Base URL: `http://localhost:8000/api/v1/pupupuv3`

### 1. Status del Sistema
```
GET /api/v1/pupupuv3/status
```

**Response:**
```json
{
  "strategy": "PupupuV3 Scalping",
  "timeframe": "1 minute",
  "ml_model_loaded": true,
  "status": "active",
  "timestamp": "2025-10-29T12:00:00"
}
```

### 2. Análisis Actual del Mercado (Principal)
```
GET /api/v1/pupupuv3/current-analysis?symbol=BTC/USDT
```

**Response:**
```json
{
  "symbol": "BTC/USDT",
  "timestamp": 1730203200000,
  "datetime": "2025-10-29T12:00:00",
  "current_price": 43250.50,
  "ema_15": 43180.25,
  "vwap": 43220.00,

  "active_resistances": [
    {
      "price": 43350.00,
      "strength": 85.5,
      "touches": 3,
      "bars_since": 25
    },
    {
      "price": 43500.00,
      "strength": 72.3,
      "touches": 2,
      "bars_since": 45
    }
  ],

  "active_supports": [
    {
      "price": 43100.00,
      "strength": 78.2,
      "touches": 4,
      "bars_since": 18
    }
  ],

  "volume_profile": {
    "poc": 43200.00,
    "vah": 43400.00,
    "val": 43000.00,
    "in_value_area": true,
    "near_hvn": false
  },

  "signal": {
    "signal_id": "BTCUSDT_1730203200000",
    "direction": "LONG",
    "entry_price": 43250.50,
    "stop_loss": 43230.00,
    "take_profit_1": 43270.50,
    "pivot_price": 43235.00,
    "pivot_type": "support",
    "pivot_strength": 78.2,
    "ema_value": 43180.25,
    "cross_type": "cross_above",
    "vwap_value": 43220.00,
    "vwap_bias": "bullish",
    "with_vwap_bias": true,
    "ml_confidence": 65.5,
    "risk_usd": 600.00,
    "position_size_usd": 10000.00,
    "risk_multiplier": 1.0,
    "is_valid": true,
    "reason": "LONG with VWAP bias"
  },

  "ml_prediction": {
    "tp2_ratio": 6.0,
    "tp2_price": 43373.50,
    "tp2_probability": 68.5,
    "tp2_timeframe": "4h",
    "tp3_ratio": 9.0,
    "tp3_price": 43434.00,
    "tp3_probability": 52.3,
    "tp3_timeframe": "8h",
    "confidence_score": 72.4
  },

  "ml_model_active": true
}
```

### 3. Señales Recientes
```
GET /api/v1/pupupuv3/signals/recent?limit=50&valid_only=true
```

**Response:**
```json
{
  "signals": [
    {
      "signal_id": "...",
      "timestamp": 1730203200000,
      "symbol": "BTC/USDT",
      "direction": "LONG",
      "entry_price": 43250.50,
      "is_valid": true,
      ...
    }
  ],
  "count": 50
}
```

### 4. Trades Activos
```
GET /api/v1/pupupuv3/trades/active
```

**Response:**
```json
{
  "active_trades": [
    {
      "trade_id": "BTCUSDT_1730203200000",
      "symbol": "BTC/USDT",
      "direction": "LONG",
      "entry_price": 43250.50,
      "current_stop_loss": 43250.50,
      "take_profit_1": 43270.50,
      "state": "TP1_HIT",
      "ema_tested": true
    }
  ],
  "count": 1
}
```

### 5. Trades Completados
```
GET /api/v1/pupupuv3/trades/completed?limit=100
```

### 6. Estadísticas
```
GET /api/v1/pupupuv3/statistics?days=30
```

**Response:**
```json
{
  "statistics": {
    "days": 30,
    "signals_total": 450,
    "signals_valid": 380,
    "trades_total": 380,
    "trades_wins": 228,
    "trades_losses": 152,
    "win_rate": 60.00,
    "total_pnl": 12500.00,
    "avg_win": 850.00,
    "avg_loss": -600.00,
    "no_test_count": 15
  },
  "days": 30
}
```

### 7. Resultados de Backtest
```
GET /api/v1/pupupuv3/backtest-results
```

**Response:**
```json
{
  "available": true,
  "file": "backtest_complete_BTCUSDT_20251029_120000.json",
  "results": {
    "phase1_metrics": {
      "total_trades": 469,
      "win_rate": 49.04,
      "total_pnl": -5400.00,
      ...
    },
    "phase3_metrics": {
      "total_trades": 469,
      "win_rate": 58.23,
      "total_pnl": 15200.00,
      ...
    }
  }
}
```

### 8. Configuración
```
GET /api/v1/pupupuv3/config
```

## Componentes del Frontend

### Dashboard Principal

```tsx
import React, { useState, useEffect } from 'react';

export const PupupuV3Dashboard = () => {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalysis = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/v1/pupupuv3/current-analysis?symbol=BTC/USDT');
        const data = await response.json();
        setAnalysis(data);
        setLoading(false);
      } catch (error) {
        console.error('Error fetching analysis:', error);
        setLoading(false);
      }
    };

    fetchAnalysis();
    const interval = setInterval(fetchAnalysis, 60000); // Update every minute

    return () => clearInterval(interval);
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="pupupuv3-dashboard">
      {/* Header */}
      <div className="header">
        <h1>PupupuV3 Scalping - 1 Minute</h1>
        <div className="status">
          <span>BTC/USDT</span>
          <span>${analysis.current_price.toFixed(2)}</span>
        </div>
      </div>

      {/* Current Signal (if any) */}
      {analysis.signal && (
        <div className="current-signal">
          <h2>🚨 Active Signal: {analysis.signal.direction}</h2>

          <div className="signal-details">
            <div className="price-levels">
              <div>Entry: ${analysis.signal.entry_price.toFixed(2)}</div>
              <div>SL: ${analysis.signal.stop_loss.toFixed(2)}</div>
              <div>TP1: ${analysis.signal.take_profit_1.toFixed(2)} (1:1)</div>
            </div>

            {analysis.ml_prediction && (
              <div className="ml-predictions">
                <h3>🤖 ML-Predicted TPs:</h3>
                <div>
                  TP2: ${analysis.ml_prediction.tp2_price.toFixed(2)}
                  ({analysis.ml_prediction.tp2_ratio}:1)
                  <span className="probability">
                    {analysis.ml_prediction.tp2_probability.toFixed(1)}%
                    in {analysis.ml_prediction.tp2_timeframe}
                  </span>
                </div>
                <div>
                  TP3: ${analysis.ml_prediction.tp3_price.toFixed(2)}
                  ({analysis.ml_prediction.tp3_ratio}:1)
                  <span className="probability">
                    {analysis.ml_prediction.tp3_probability.toFixed(1)}%
                    in {analysis.ml_prediction.tp3_timeframe}
                  </span>
                </div>
                <div>
                  Confidence: {analysis.ml_prediction.confidence_score.toFixed(1)}%
                </div>
              </div>
            )}

            <div className="signal-context">
              <div>VWAP Bias: {analysis.signal.vwap_bias}</div>
              <div>With VWAP: {analysis.signal.with_vwap_bias ? 'YES' : 'NO'}</div>
              <div>Risk: ${analysis.signal.risk_usd.toFixed(2)}</div>
              <div>Position Size: ${analysis.signal.position_size_usd.toFixed(2)}</div>
            </div>
          </div>
        </div>
      )}

      {/* Market Indicators */}
      <div className="indicators">
        <div className="indicator">
          <label>EMA(15)</label>
          <value>${analysis.ema_15.toFixed(2)}</value>
        </div>
        <div className="indicator">
          <label>VWAP</label>
          <value>${analysis.vwap.toFixed(2)}</value>
        </div>
        <div className="indicator">
          <label>VP POC</label>
          <value>${analysis.volume_profile.poc.toFixed(2)}</value>
        </div>
      </div>

      {/* Pivot Levels */}
      <div className="pivots">
        <div className="resistances">
          <h3>Resistances</h3>
          {analysis.active_resistances.map((r, i) => (
            <div key={i} className="pivot-level">
              <span>${r.price.toFixed(2)}</span>
              <span>Strength: {r.strength.toFixed(1)}</span>
              <span>Touches: {r.touches}</span>
            </div>
          ))}
        </div>

        <div className="supports">
          <h3>Supports</h3>
          {analysis.active_supports.map((s, i) => (
            <div key={i} className="pivot-level">
              <span>${s.price.toFixed(2)}</span>
              <span>Strength: {s.strength.toFixed(1)}</span>
              <span>Touches: {s.touches}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Volume Profile */}
      <div className="volume-profile">
        <h3>Volume Profile (7d)</h3>
        <div>POC: ${analysis.volume_profile.poc.toFixed(2)}</div>
        <div>VAH: ${analysis.volume_profile.vah.toFixed(2)}</div>
        <div>VAL: ${analysis.volume_profile.val.toFixed(2)}</div>
        <div>In Value Area: {analysis.volume_profile.in_value_area ? 'YES' : 'NO'}</div>
      </div>
    </div>
  );
};
```

### Statistics Component

```tsx
export const PupupuV3Stats = () => {
  const [stats, setStats] = useState(null);
  const [days, setDays] = useState(30);

  useEffect(() => {
    fetchStats();
  }, [days]);

  const fetchStats = async () => {
    const response = await fetch(`http://localhost:8000/api/v1/pupupuv3/statistics?days=${days}`);
    const data = await response.json();
    setStats(data.statistics);
  };

  if (!stats) return <div>Loading stats...</div>;

  return (
    <div className="pupupuv3-stats">
      <h2>Statistics (Last {days} days)</h2>

      <div className="stats-grid">
        <div className="stat-card">
          <label>Total Signals</label>
          <value>{stats.signals_total}</value>
          <sublabel>{stats.signals_valid} valid</sublabel>
        </div>

        <div className="stat-card">
          <label>Total Trades</label>
          <value>{stats.trades_total}</value>
        </div>

        <div className="stat-card">
          <label>Win Rate</label>
          <value className={stats.win_rate >= 55 ? 'positive' : 'negative'}>
            {stats.win_rate.toFixed(2)}%
          </value>
        </div>

        <div className="stat-card">
          <label>Total PnL</label>
          <value className={stats.total_pnl > 0 ? 'positive' : 'negative'}>
            ${stats.total_pnl.toFixed(2)}
          </value>
        </div>

        <div className="stat-card">
          <label>Avg Win</label>
          <value className="positive">${stats.avg_win.toFixed(2)}</value>
        </div>

        <div className="stat-card">
          <label>Avg Loss</label>
          <value className="negative">${stats.avg_loss.toFixed(2)}</value>
        </div>

        <div className="stat-card">
          <label>NO_TEST Count</label>
          <value>{stats.no_test_count}</value>
          <sublabel>TP1 without EMA test</sublabel>
        </div>
      </div>

      <div className="period-selector">
        <button onClick={() => setDays(7)}>7 days</button>
        <button onClick={() => setDays(14)}>14 days</button>
        <button onClick={() => setDays(30)}>30 days</button>
      </div>
    </div>
  );
};
```

## Layout Sugerido

```
┌─────────────────────────────────────────────────────────┐
│  [Box Strategy] [PupupuV3 Scalping] [Trades] [Settings] │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  📊 PupupuV3 Scalping - 1 Minute                        │
│  BTC/USDT: $43,250.50                                   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 🚨 ACTIVE SIGNAL: LONG                          │   │
│  │                                                 │   │
│  │ Entry: $43,250.50                              │   │
│  │ SL: $43,230.00                                 │   │
│  │ TP1: $43,270.50 (1:1 - auto to BE)            │   │
│  │                                                 │   │
│  │ 🤖 ML-Predicted TPs:                            │   │
│  │ TP2: $43,373.50 (6:1) - 68.5% in 4h           │   │
│  │ TP3: $43,434.00 (9:1) - 52.3% in 8h           │   │
│  │ Confidence: 72.4%                              │   │
│  │                                                 │   │
│  │ VWAP Bias: bullish | Risk: $600               │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────────┬──────────────┬──────────────┐       │
│  │ EMA(15)      │ VWAP         │ VP POC       │       │
│  │ $43,180.25   │ $43,220.00   │ $43,200.00   │       │
│  └──────────────┴──────────────┴──────────────┘       │
│                                                         │
│  ┌──────────────────────┬──────────────────────┐       │
│  │ Resistances          │ Supports             │       │
│  │ $43,350 (S: 85.5)   │ $43,100 (S: 78.2)   │       │
│  │ $43,500 (S: 72.3)   │ $43,050 (S: 65.1)   │       │
│  └──────────────────────┴──────────────────────┘       │
│                                                         │
│  ┌─────────────────────────────────────────────┐       │
│  │ Statistics (Last 30 days)                   │       │
│  │                                             │       │
│  │ Total Trades: 380 | Win Rate: 60.00%       │       │
│  │ Total PnL: +$12,500                         │       │
│  │ Avg Win: $850 | Avg Loss: -$600             │       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Diferencias vs Box Strategy

| Aspecto | Box Strategy | PupupuV3 Scalping |
|---------|--------------|-------------------|
| Timeframe | 5 minutos | 1 minuto |
| TPs | Fijos | Dinámicos con ML |
| Risk | Fijo 2% | Dinámico (2% o 1%) |
| Filtro | Volumen + Osciladores | VWAP + ML |
| Objetivo | Swing | Scalping |

## Testing

```bash
# Test endpoint
curl http://localhost:8000/api/v1/pupupuv3/status

# Test analysis
curl http://localhost:8000/api/v1/pupupuv3/current-analysis?symbol=BTC/USDT

# Test stats
curl http://localhost:8000/api/v1/pupupuv3/statistics?days=30
```

## Notas de Implementación

1. **Polling**: Actualizar cada 60 segundos (1 minuto)
2. **WebSocket** (futuro): Para updates en tiempo real
3. **Notificaciones**: Alertar cuando hay nueva señal válida
4. **ML Status**: Mostrar si el modelo ML está cargado
5. **Backtest Results**: Mostrar comparación Fase 1 vs Fase 3

---

**Status**: ✅ API lista para integración
**Próximo**: Implementar componentes React en el frontend
