# PupupuV2 API Documentation

API endpoints para monitorear señales de trading del bot pupupuv2 desde el frontend.

Base URL: `http://localhost:8000/api/v1/pupupuv2`

---

## 🔍 Endpoints Disponibles

### 1. Health Check

**GET** `/api/v1/pupupuv2/health`

Verifica que el servicio esté funcionando.

**Response:**
```json
{
  "status": "healthy",
  "service": "pupupuv2",
  "timestamp": "2025-10-21T20:45:00",
  "is_monitoring": false
}
```

---

### 2. Current Analysis (⭐ PRINCIPAL)

**GET** `/api/v1/pupupuv2/current-analysis`

Ejecuta un análisis completo del mercado en tiempo real.

**Query Params:**
- `account_balance` (optional): Capital total en USD (default: 10000)
- `risk_per_trade` (optional): % de riesgo por trade (default: 0.02)

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/pupupuv2/current-analysis?account_balance=10000&risk_per_trade=0.02"
```

**Response:**
```json
{
  "timestamp": "2025-10-21T20:45:00",
  "current_price": 112065.78,
  "current_ema": 112150.45,
  "price_vs_ema": "below",
  "distance_from_ema_pct": -0.075,

  "signal": {
    "direction": "SHORT",
    "entry_price": 112150.45,
    "stop_loss": 112280.50,
    "take_profit": 111929.36,
    "position_size_usd": 1500.00,
    "confidence": 0.875,
    "reason": "Resistance touch @ $112,280.50 + bearish EMA cross",
    "pivot_info": {
      "price": 112280.50,
      "touches": 2,
      "strength": 0.85
    },
    "timestamp": "2025-10-21T20:45:00",
    "risk_reward_ratio": 1.7,
    "risk_usd": 200.00
  },

  "active_resistances": [
    {
      "price": 112280.50,
      "strength": 0.95,
      "touches": 2,
      "age_candles": 45,
      "distance_pct": 0.19
    },
    ...
  ],

  "active_supports": [
    {
      "price": 111800.00,
      "strength": 0.88,
      "touches": 1,
      "age_candles": 30,
      "distance_pct": 0.24
    },
    ...
  ],

  "volume_profile": {
    "vp_corto": {
      "poc": 112269.78,
      "vah": 112500.00,
      "val": 111900.00,
      "hvn_count": 5,
      "lvn_count": 3
    },
    "vp_medio": {
      "poc": 112100.00,
      "vah": 113500.00,
      "val": 110500.00,
      "hvn_count": 5,
      "lvn_count": 3
    }
  },

  "market_filters": {
    "pass_all": true,
    "fundamental_event": false,
    "fundamental_event_description": null,
    "liquidity_ok": true,
    "volatility_ok": true,
    "ht_trend": "neutral"
  },

  "metadata": {
    "total_resistances": 6,
    "total_supports": 23,
    "data_candles": 500,
    "analysis_time": "2025-10-21T20:45:00"
  }
}
```

**Uso en Frontend:**
- Llamar cada 60 segundos para actualizar estado
- Si `signal` no es null → mostrar alerta de trading
- Mostrar resistances/supports en tabla ordenadas por strength
- Visualizar VP nodes en gráfico

---

### 3. Latest Signals

**GET** `/api/v1/pupupuv2/signals/latest`

Obtiene las últimas señales generadas (guardadas en disco).

**Query Params:**
- `limit` (optional): Número máximo de señales (default: 10)

**Response:**
```json
{
  "signals": [
    {
      "direction": "SHORT",
      "entry_price": 109093.44,
      "stop_loss": 108986.95,
      "take_profit": 108912.41,
      "position_size_usd": 1880.00,
      "confidence": 0.911,
      "reason": "Resistance touch @ $109,200.00 + bearish EMA cross",
      "pivot_info": {
        "price": 109200.00,
        "touches": 2,
        "strength": 0.85
      },
      "timestamp": "2025-10-20T01:00:00",
      "risk_reward_ratio": 1.7,
      "risk_usd": 200.00
    },
    ...
  ],
  "count": 10,
  "total_stored": 16
}
```

**Uso en Frontend:**
- Mostrar historial de señales en tabla
- Permitir filtrar por LONG/SHORT
- Mostrar confidence con color (verde > 80%, amarillo 60-80%, rojo < 60%)

---

### 4. Active Levels

**GET** `/api/v1/pupupuv2/active-levels`

Obtiene todos los pivotes activos (soportes y resistencias).

**Response:**
```json
{
  "current_price": 112065.78,
  "timestamp": "2025-10-21T20:45:00",

  "resistances": [
    {
      "price": 112280.50,
      "strength": 0.95,
      "touches": 2,
      "age_candles": 45,
      "distance_usd": 214.72,
      "distance_pct": 0.19,
      "timestamp": "2025-10-21T18:30:00"
    },
    ...
  ],

  "supports": [
    {
      "price": 111800.00,
      "strength": 0.88,
      "touches": 1,
      "age_candles": 30,
      "distance_usd": 265.78,
      "distance_pct": 0.24,
      "timestamp": "2025-10-21T19:15:00"
    },
    ...
  ],

  "summary": {
    "total_resistances": 6,
    "total_supports": 23,
    "strongest_resistance": {
      "price": 112280.50,
      "strength": 0.95
    },
    "strongest_support": {
      "price": 111800.00,
      "strength": 0.88
    }
  }
}
```

**Uso en Frontend:**
- Dibujar líneas horizontales en gráfico de TradingView
- Color por strength: verde (> 0.8), amarillo (0.6-0.8), gris (< 0.6)
- Grosor de línea basado en touches

---

### 5. Volume Profile

**GET** `/api/v1/pupupuv2/volume-profile`

Obtiene datos completos del Volume Profile.

**Response:**
```json
{
  "timestamp": "2025-10-21T20:45:00",
  "current_price": 112065.78,

  "vp_corto": {
    "poc": 112269.78,
    "vah": 112500.00,
    "val": 111900.00,
    "hvn": [112269.78, 112150.00, 112400.00, ...],
    "lvn": [112050.00, 112300.00, ...],
    "price_levels": [112000, 112010, ...],
    "volume_distribution": [1500000, 1200000, ...],
    "total_volume": 15541,
    "price_range": [109659.52, 114000.00],
    "num_candles": 48
  },

  "vp_medio": { ... },
  "vp_largo": { ... }
}
```

**Uso en Frontend:**
- Visualizar histogram de volumen lateral en gráfico
- Marcar POC con línea roja prominente
- Sombrear área entre VAH-VAL (zona de valor)
- Marcar HVN con líneas naranjas punteadas

---

### 6. Market Context

**GET** `/api/v1/pupupuv2/market-context`

Estado de filtros de mercado.

**Response:**
```json
{
  "timestamp": "2025-10-21T20:45:00",
  "pass_all_filters": true,

  "fundamental_event": {
    "detected": false,
    "description": null
  },

  "liquidity": {
    "ok": true,
    "reason": null
  },

  "volatility": {
    "ok": true,
    "reason": null
  },

  "higher_timeframe_trend": {
    "trend": "neutral",
    "details": {
      "ma_value": 112000.00,
      "current_price": 112065.78,
      "distance_pct": 0.06
    }
  },

  "recommendation": "SAFE TO TRADE"
}
```

**Uso en Frontend:**
- Mostrar semáforo de filtros (verde = ok, rojo = no ok)
- Si `pass_all_filters` = false → mostrar warning grande
- Mostrar trend de HT con icono (🐂 bull, 🐻 bear, ➡️ neutral)

---

### 7. Backtest Summary

**GET** `/api/v1/pupupuv2/backtest-summary`

Resultados del último backtest ejecutado.

**Response:**
```json
{
  "available": true,
  "timestamp": "2025-10-21T20:45:00",
  "summary": {
    "total_signals": 16,
    "total_trades": 16,
    "wins": 9,
    "losses": 7,
    "win_rate": "56.2%",
    "total_pnl": 2060.00,
    "avg_rr": 0.52,
    "max_drawdown": 600.00
  },
  "recent_trades": [
    {
      "outcome": "WIN",
      "pnl": 340.00,
      "bars_held": 3,
      "exit_price": 111929.36,
      "rr_achieved": 1.7
    },
    ...
  ]
}
```

**Uso en Frontend:**
- Mostrar métricas en cards
- Gráfico de equity curve
- Tabla de últimos trades

---

### 8. Statistics

**GET** `/api/v1/pupupuv2/statistics`

Estadísticas generales del bot.

**Response:**
```json
{
  "timestamp": "2025-10-21T20:45:00",
  "total_signals_generated": 16,
  "signals_by_direction": {
    "long": 0,
    "short": 16
  },
  "average_confidence": 0.867,
  "last_analysis": "2025-10-21T20:45:00",
  "monitoring_active": false
}
```

---

### 9. Start/Stop Monitoring

**POST** `/api/v1/pupupuv2/start-monitoring`

Inicia monitoreo continuo en background.

**Response:**
```json
{
  "status": "started",
  "message": "Background monitoring started",
  "check_interval": "60 seconds"
}
```

**POST** `/api/v1/pupupuv2/stop-monitoring`

Detiene monitoreo.

**Response:**
```json
{
  "status": "stopped",
  "message": "Background monitoring stopped"
}
```

---

## 📱 Estructura de Frontend Sugerida

### Dashboard Principal

```
┌─────────────────────────────────────────────────────┐
│  PupupuV2 Scalping Bot Dashboard                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  📊 Current Market Status                          │
│  ├─ BTC/USDT: $112,065.78  (↓ 0.24%)              │
│  ├─ EMA(12): $112,150.45                           │
│  └─ HT Trend: Neutral ➡️                           │
│                                                     │
│  🚨 ACTIVE SIGNAL                                  │
│  ┌───────────────────────────────────────────────┐ │
│  │ SHORT @ $112,150.45  |  Confidence: 87.5% 🟢 │ │
│  │ SL: $112,280.50  |  TP: $111,929.36          │ │
│  │ Risk: $200  |  Potential: $340  (R:R 1.7)    │ │
│  │                                                │ │
│  │ Reason: Resistance touch + EMA bearish cross  │ │
│  │ [EXECUTE MANUALLY] [DISMISS]                  │ │
│  └───────────────────────────────────────────────┘ │
│                                                     │
│  📈 Active Levels                                  │
│  Resistances (6):                                  │
│  • $112,280 (str: 0.95, touches: 2) 🟢            │
│  • $112,500 (str: 0.82, touches: 1) 🟡            │
│                                                     │
│  Supports (23):                                    │
│  • $111,800 (str: 0.88, touches: 1) 🟢            │
│  • $111,500 (str: 0.75, touches: 2) 🟡            │
│                                                     │
│  🎯 Market Filters                                 │
│  ├─ Liquidity: ✅                                  │
│  ├─ Volatility: ✅                                 │
│  ├─ Fundamental Events: ✅                         │
│  └─ SAFE TO TRADE                                  │
│                                                     │
│  📊 Performance (Last Backtest)                    │
│  ├─ Win Rate: 56.2% (9W / 7L)                     │
│  ├─ Total P&L: +$2,060                            │
│  ├─ Profit Factor: 2.19                           │
│  └─ Max DD: $600                                   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Código React Ejemplo

```tsx
import { useQuery } from 'react-query';
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api/v1/pupupuv2';

function PupupuV2Dashboard() {
  // Fetch current analysis every 60 seconds
  const { data: analysis, isLoading } = useQuery(
    'pupupuv2-analysis',
    () => axios.get(`${API_BASE}/current-analysis`).then(res => res.data),
    { refetchInterval: 60000 }
  );

  if (isLoading) return <div>Loading...</div>;

  const hasSignal = analysis?.signal !== null;

  return (
    <div className="dashboard">
      {/* Market Status */}
      <div className="market-status">
        <h2>BTC/USDT: ${analysis.current_price.toLocaleString()}</h2>
        <p>EMA(12): ${analysis.current_ema.toLocaleString()}</p>
        <p>Price is {analysis.price_vs_ema} EMA</p>
      </div>

      {/* Active Signal Alert */}
      {hasSignal && (
        <div className="signal-alert">
          <h2>🚨 {analysis.signal.direction} SIGNAL</h2>
          <p>Confidence: {(analysis.signal.confidence * 100).toFixed(1)}%</p>
          <p>Entry: ${analysis.signal.entry_price.toLocaleString()}</p>
          <p>SL: ${analysis.signal.stop_loss.toLocaleString()}</p>
          <p>TP: ${analysis.signal.take_profit.toLocaleString()}</p>
          <p>Risk: ${analysis.signal.risk_usd}</p>
          <button onClick={() => handleExecuteTrade(analysis.signal)}>
            EXECUTE MANUALLY
          </button>
        </div>
      )}

      {/* Active Levels */}
      <div className="active-levels">
        <h3>Resistances ({analysis.metadata.total_resistances})</h3>
        {analysis.active_resistances.map((r, i) => (
          <div key={i}>
            ${r.price.toLocaleString()} - Strength: {r.strength.toFixed(2)}
          </div>
        ))}

        <h3>Supports ({analysis.metadata.total_supports})</h3>
        {analysis.active_supports.map((s, i) => (
          <div key={i}>
            ${s.price.toLocaleString()} - Strength: {s.strength.toFixed(2)}
          </div>
        ))}
      </div>

      {/* Market Filters */}
      <div className="market-filters">
        <h3>Market Filters</h3>
        <p>Liquidity: {analysis.market_filters.liquidity_ok ? '✅' : '❌'}</p>
        <p>Volatility: {analysis.market_filters.volatility_ok ? '✅' : '❌'}</p>
        <p>Events: {!analysis.market_filters.fundamental_event ? '✅' : '❌'}</p>
        <p className={analysis.market_filters.pass_all ? 'safe' : 'danger'}>
          {analysis.market_filters.pass_all ? 'SAFE TO TRADE' : 'DO NOT TRADE'}
        </p>
      </div>
    </div>
  );
}
```

---

## 🔄 Flujo Recomendado

1. **Load Dashboard** → GET `/current-analysis`
2. **Poll every 60s** → GET `/current-analysis` (auto-refresh)
3. **Show Signal** → Display alert box cuando `signal !== null`
4. **User validates** → Chequear calendarios, noticias
5. **Manual execution** → Usuario ejecuta en Binance/exchange
6. **Check history** → GET `/signals/latest` para ver histórico

---

## 🛠️ Testing

Archivo `test_pupupuv2_api.py` incluido para probar todos los endpoints.

```bash
python test_pupupuv2_api.py
```

---

## ⚠️ Notas Importantes

1. **Rate Limiting**: Binance API tiene límites. No hacer polling < 30 segundos.

2. **Background Monitoring**: Actualmente `/start-monitoring` solo cambia un flag. Para producción, implementar con Celery o background tasks apropiados.

3. **Signal Storage**: Señales se guardan en `signals/*.json`. En producción, usar base de datos.

4. **CORS**: Verificar configuración de CORS en `main.py` para permitir tu frontend.

5. **Security**: Endpoints son públicos. En producción, añadir autenticación.

---

**Ready to integrate! 🚀**
