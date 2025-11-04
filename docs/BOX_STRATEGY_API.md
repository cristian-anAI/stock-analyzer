# Box Strategy API Documentation

API endpoints para monitorizar la estrategia de caja con predicciones ML en múltiples mercados globales.

## Índice

1. [Descripción General](#descripción-general)
2. [Endpoints Disponibles](#endpoints-disponibles)
3. [Modelos de Datos](#modelos-de-datos)
4. [Mercados Soportados](#mercados-soportados)
5. [Ejemplos de Uso](#ejemplos-de-uso)
6. [Integración Frontend](#integración-frontend)

---

## Descripción General

El sistema Box Strategy API proporciona:

- **Monitorización multi-mercado**: 10 mercados globales (SPX, NDX, DAX, FTSE, etc.)
- **Awareness de zonas horarias**: Cada mercado tiene sus horas de caja específicas
- **Predicciones ML**: Confianza de trades basada en modelos entrenados
- **Detección de breakouts**: Identifica automáticamente LONG/SHORT
- **Trade setup completo**: Entry, stop loss, y 3 take profits

### Flujo de Datos

```
1. Box Formation (8:30-10:00 AM local)
   └─> Box High, Low, Range detectados

2. Post-Box Period (después 10:00 AM)
   └─> Monitorización de breakouts

3. Breakout Detected
   └─> ML Prediction calculada
       ├─> Win Probability (0-100%)
       ├─> Confidence Level (HIGH/MEDIUM/LOW)
       └─> Recommendation (TRADE/REDUCE_SIZE/SKIP)

4. Trade Setup Generado
   └─> Entry, Stop, TP1, TP2, TP3
```

---

## Endpoints Disponibles

### Base URL

```
http://localhost:8000/api/v1/box-strategy
```

### 1. GET `/markets`

Obtener estado y predicciones para **todos los mercados**.

**Query Parameters:**
- `ml_version` (opcional): Versión del modelo ML (default: "1")

**Response:**

```json
{
  "timestamp": "2025-10-08T15:30:00",
  "ml_version": "1",
  "summary": {
    "total_markets": 10,
    "box_complete": 4,
    "breakouts_detected": 2,
    "high_confidence_setups": 1
  },
  "markets": [
    {
      "market": "SPX",
      "name": "S&P 500",
      "timezone": "America/New_York",
      "status": {
        "market": "SPX",
        "local_time": "2025-10-08T15:30:00-04:00",
        "is_box_period": false,
        "is_post_box": true,
        "box_complete": true,
        "next_box_time": "2025-10-09T08:30:00-04:00"
      },
      "box_setup": {
        "market": "SPX",
        "date": "2025-10-08",
        "box_high": 6776.50,
        "box_low": 6764.50,
        "box_range": 12.00,
        "box_midpoint": 6770.50,
        "candles_in_box": 18,
        "current_price": 6799.25,
        "breakout_detected": true,
        "direction": "LONG",
        "entry_price": 6776.50,
        "stop_loss": 6764.50,
        "tp1": 6788.50,
        "tp2": 6800.50,
        "tp3": 6812.50,
        "risk_points": 12.00
      },
      "ml_prediction": {
        "win_probability": 0.551,
        "confidence_level": "MEDIUM",
        "recommendation": "REDUCE_SIZE",
        "position_size_multiplier": 0.6,
        "model_used": "random_forest",
        "model_version": "1"
      }
    }
    // ... más mercados
  ]
}
```

**Ejemplo cURL:**

```bash
curl -X GET "http://localhost:8000/api/v1/box-strategy/markets?ml_version=1"
```

---

### 2. GET `/market/{market_code}`

Obtener detalles completos de un **mercado específico**.

**Path Parameters:**
- `market_code`: Código del mercado (SPX, NDX, DAX, etc.)

**Query Parameters:**
- `ml_version` (opcional): Versión del modelo ML (default: "1")

**Response:**

```json
{
  "timestamp": "2025-10-08T15:30:00",
  "market": "SPX",
  "name": "S&P 500",
  "timezone": "America/New_York",
  "box_hours": {
    "start": "08:30",
    "end": "10:00"
  },
  "status": {
    "market": "SPX",
    "local_time": "2025-10-08T15:30:00-04:00",
    "is_box_period": false,
    "is_post_box": true,
    "box_complete": true,
    "next_box_time": "2025-10-09T08:30:00-04:00"
  },
  "box_setup": {
    "market": "SPX",
    "date": "2025-10-08",
    "box_high": 6776.50,
    "box_low": 6764.50,
    "box_range": 12.00,
    "current_price": 6799.25,
    "breakout_detected": true,
    "direction": "LONG",
    "entry_price": 6776.50,
    "stop_loss": 6764.50,
    "tp1": 6788.50,
    "tp2": 6800.50,
    "tp3": 6812.50,
    "risk_points": 12.00
  },
  "ml_prediction": {
    "win_probability": 0.551,
    "confidence_level": "MEDIUM",
    "recommendation": "REDUCE_SIZE",
    "position_size_multiplier": 0.6,
    "model_used": "random_forest",
    "model_version": "1"
  }
}
```

**Ejemplo cURL:**

```bash
curl -X GET "http://localhost:8000/api/v1/box-strategy/market/SPX?ml_version=1"
```

---

### 3. GET `/tradeable`

Obtener solo mercados con **setups operables** (box completo + breakout detectado).

**Query Parameters:**
- `ml_version` (opcional): Versión del modelo ML (default: "1")
- `min_confidence` (opcional): Filtrar por confianza mínima (HIGH, MEDIUM, LOW)

**Response:**

```json
{
  "timestamp": "2025-10-08T15:30:00",
  "ml_version": "1",
  "filter": {
    "min_confidence": "MEDIUM"
  },
  "count": 2,
  "setups": [
    {
      "market": "SPX",
      "name": "S&P 500",
      "box_setup": { /* ... */ },
      "ml_prediction": { /* ... */ }
    },
    {
      "market": "NDX",
      "name": "NASDAQ 100",
      "box_setup": { /* ... */ },
      "ml_prediction": { /* ... */ }
    }
  ]
}
```

**Ejemplo cURL:**

```bash
# Todos los setups operables
curl -X GET "http://localhost:8000/api/v1/box-strategy/tradeable"

# Solo HIGH confidence
curl -X GET "http://localhost:8000/api/v1/box-strategy/tradeable?min_confidence=HIGH"
```

---

### 4. GET `/dashboard`

Obtener datos completos del **dashboard** con estadísticas y categorización.

**Query Parameters:**
- `ml_version` (opcional): Versión del modelo ML (default: "1")

**Response:**

```json
{
  "timestamp": "2025-10-08T15:30:00",
  "ml_version": "1",
  "summary": {
    "total_markets": 10,
    "pending_box": 3,
    "active_box": 2,
    "box_complete": 5,
    "breakouts": 2,
    "high_confidence": 1,
    "avg_win_probability": 0.573
  },
  "markets_by_status": {
    "pending": ["NKY", "HSI", "ASX"],
    "active": ["DAX", "FTSE"],
    "complete": ["SPX", "NDX", "STOXX", "CAC", "IBEX"]
  },
  "high_confidence_setups": [
    {
      "market": "NDX",
      "box_setup": { /* ... */ },
      "ml_prediction": {
        "win_probability": 0.78,
        "confidence_level": "HIGH",
        "recommendation": "TRADE"
      }
    }
  ],
  "all_breakouts": [
    { /* SPX */ },
    { /* NDX */ }
  ],
  "all_markets": [
    { /* ... todos los mercados ... */ }
  ]
}
```

**Ejemplo cURL:**

```bash
curl -X GET "http://localhost:8000/api/v1/box-strategy/dashboard?ml_version=1"
```

---

### 5. GET `/config`

Obtener **configuración** de todos los mercados soportados.

**Response:**

```json
{
  "markets": {
    "SPX": {
      "code": "SPX",
      "name": "S&P 500",
      "ticker": "ES=F",
      "timezone": "America/New_York",
      "box_hours": {
        "start": "08:30",
        "end": "10:00"
      },
      "currency": "USD",
      "points_per_contract": 50.0
    },
    "NDX": {
      "code": "NDX",
      "name": "NASDAQ 100",
      "ticker": "NQ=F",
      "timezone": "America/New_York",
      "box_hours": {
        "start": "08:30",
        "end": "10:00"
      },
      "currency": "USD",
      "points_per_contract": 20.0
    }
    // ... más mercados
  },
  "total": 10
}
```

**Ejemplo cURL:**

```bash
curl -X GET "http://localhost:8000/api/v1/box-strategy/config"
```

---

## Modelos de Datos

### MarketStatus

```typescript
interface MarketStatus {
  market: string;              // "SPX", "NDX", etc.
  local_time: string;          // ISO timestamp en timezone local
  is_box_period: boolean;      // Está en período de formación de caja
  is_post_box: boolean;        // Después del período de caja
  box_complete: boolean;       // Caja completada
  next_box_time: string | null; // Próximo inicio de caja
  market_open: boolean;        // Mercado abierto
}
```

### BoxSetup

```typescript
interface BoxSetup {
  market: string;
  date: string;
  box_high: number;
  box_low: number;
  box_range: number;
  box_midpoint: number;
  candles_in_box: number;
  current_price: number | null;
  breakout_detected: boolean;
  direction: "LONG" | "SHORT" | null;
  entry_price: number | null;
  stop_loss: number | null;
  tp1: number | null;          // Take Profit 1 (1R)
  tp2: number | null;          // Take Profit 2 (2R)
  tp3: number | null;          // Take Profit 3 (3R)
  risk_points: number | null;
}
```

### MLPrediction

```typescript
interface MLPrediction {
  win_probability: number;     // 0.0 - 1.0
  confidence_level: "HIGH" | "MEDIUM" | "LOW";
  recommendation: "TRADE" | "REDUCE_SIZE" | "SKIP";
  position_size_multiplier: number; // 0.0 - 1.0
  model_used: string;          // "random_forest", "xgboost", etc.
  model_version: string;       // "1", "2", etc.
}
```

### Confidence Levels

| Nivel | Win Probability | Position Size | Acción |
|-------|----------------|---------------|---------|
| HIGH  | ≥ 75%          | 100%          | TRADE (posición completa) |
| MEDIUM| 50-75%         | 60%           | REDUCE_SIZE (posición reducida) |
| LOW   | < 50%          | 0%            | SKIP (no operar) |

---

## Mercados Soportados

| Código | Nombre | Ticker | Timezone | Box Hours | Moneda |
|--------|--------|--------|----------|-----------|--------|
| SPX | S&P 500 | ES=F | America/New_York | 08:30-10:00 | USD |
| NDX | NASDAQ 100 | NQ=F | America/New_York | 08:30-10:00 | USD |
| DAX | DAX | FDAX=F | Europe/Berlin | 08:00-09:30 | EUR |
| FTSE | FTSE 100 | ^FTSE | Europe/London | 08:00-09:30 | GBP |
| STOXX | Euro Stoxx 50 | ^STOXX50E | Europe/Paris | 08:00-09:30 | EUR |
| CAC | CAC 40 | ^FCHI | Europe/Paris | 08:00-09:30 | EUR |
| NKY | Nikkei 225 | ^N225 | Asia/Tokyo | 09:00-10:30 | JPY |
| HSI | Hang Seng | ^HSI | Asia/Hong_Kong | 09:30-11:00 | HKD |
| ASX | ASX 200 | ^AXJO | Australia/Sydney | 10:00-11:30 | AUD |
| IBEX | IBEX 35 | ^IBEX | Europe/Madrid | 09:00-10:30 | EUR |

---

## Ejemplos de Uso

### Workflow Típico del Día

```bash
# 1. Por la mañana (antes de abrir mercados): Revisar configuración
curl -X GET "http://localhost:8000/api/v1/box-strategy/config"

# 2. Durante el día: Monitorizar dashboard
curl -X GET "http://localhost:8000/api/v1/box-strategy/dashboard"

# 3. Después de cierre de caja: Ver setups operables
curl -X GET "http://localhost:8000/api/v1/box-strategy/tradeable?min_confidence=MEDIUM"

# 4. Detalle de mercado específico
curl -X GET "http://localhost:8000/api/v1/box-strategy/market/SPX"
```

### Filtrado por Confianza

```bash
# Solo HIGH confidence (≥75% win probability)
curl -X GET "http://localhost:8000/api/v1/box-strategy/tradeable?min_confidence=HIGH"

# MEDIUM o superior (≥50% win probability)
curl -X GET "http://localhost:8000/api/v1/box-strategy/tradeable?min_confidence=MEDIUM"

# Todos los breakouts (sin filtro)
curl -X GET "http://localhost:8000/api/v1/box-strategy/tradeable"
```

### Usando Diferentes Versiones de Modelo

```bash
# Modelo v1 (entrenado con backtest inicial)
curl -X GET "http://localhost:8000/api/v1/box-strategy/dashboard?ml_version=1"

# Modelo v2 (re-entrenado con nuevos trades)
curl -X GET "http://localhost:8000/api/v1/box-strategy/dashboard?ml_version=2"
```

### Monitoreo en Tiempo Real (cada 5 minutos)

```bash
#!/bin/bash
# monitor_box_strategy.sh

while true; do
  echo "=== $(date) ==="

  # Dashboard summary
  curl -s "http://localhost:8000/api/v1/box-strategy/dashboard" | \
    jq '.summary'

  # High confidence setups
  curl -s "http://localhost:8000/api/v1/box-strategy/tradeable?min_confidence=HIGH" | \
    jq '.count, .setups[].market'

  echo ""
  sleep 300  # 5 minutes
done
```

---

## Integración Frontend

### React/TypeScript

Ver archivo completo: `frontend_example_BoxStrategyDashboard.tsx`

```tsx
import BoxStrategyDashboard from './components/BoxStrategyDashboard';

function App() {
  return (
    <BoxStrategyDashboard
      mlVersion="1"
      apiBaseUrl="http://localhost:8000"
      refreshInterval={300000}  // 5 minutes
    />
  );
}
```

### JavaScript Vanilla

```javascript
// Fetch dashboard data
async function fetchBoxStrategyDashboard() {
  const response = await fetch(
    'http://localhost:8000/api/v1/box-strategy/dashboard?ml_version=1'
  );
  const data = await response.json();

  // Display high confidence setups
  data.high_confidence_setups.forEach(setup => {
    console.log(`${setup.market}: ${setup.ml_prediction.win_probability * 100}% win probability`);
  });
}

// Auto-refresh every 5 minutes
setInterval(fetchBoxStrategyDashboard, 300000);
```

### Python Client

```python
import requests
from datetime import datetime

class BoxStrategyClient:
    def __init__(self, base_url="http://localhost:8000", ml_version="1"):
        self.base_url = base_url
        self.ml_version = ml_version

    def get_dashboard(self):
        """Get complete dashboard data"""
        response = requests.get(
            f"{self.base_url}/api/v1/box-strategy/dashboard",
            params={"ml_version": self.ml_version}
        )
        return response.json()

    def get_tradeable(self, min_confidence=None):
        """Get tradeable setups"""
        params = {"ml_version": self.ml_version}
        if min_confidence:
            params["min_confidence"] = min_confidence

        response = requests.get(
            f"{self.base_url}/api/v1/box-strategy/tradeable",
            params=params
        )
        return response.json()

    def get_market(self, market_code):
        """Get specific market details"""
        response = requests.get(
            f"{self.base_url}/api/v1/box-strategy/market/{market_code}",
            params={"ml_version": self.ml_version}
        )
        return response.json()

# Usage
client = BoxStrategyClient()

# Get high confidence setups
setups = client.get_tradeable(min_confidence="HIGH")
print(f"Found {setups['count']} high confidence setups")

for setup in setups['setups']:
    pred = setup['ml_prediction']
    print(f"{setup['market']}: {pred['win_probability']*100:.1f}% - {pred['recommendation']}")
```

---

## Testing

### Swagger UI

Visita la documentación interactiva:

```
http://localhost:8000/docs
```

Busca la sección **"box-strategy"** para probar todos los endpoints.

### Pytest

```python
# test_box_strategy_api.py
import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_get_all_markets():
    response = client.get("/api/v1/box-strategy/markets")
    assert response.status_code == 200
    data = response.json()
    assert "markets" in data
    assert "summary" in data

def test_get_specific_market():
    response = client.get("/api/v1/box-strategy/market/SPX")
    assert response.status_code == 200
    data = response.json()
    assert data["market"] == "SPX"

def test_get_tradeable():
    response = client.get("/api/v1/box-strategy/tradeable?min_confidence=HIGH")
    assert response.status_code == 200
    data = response.json()
    assert "setups" in data

def test_get_dashboard():
    response = client.get("/api/v1/box-strategy/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "high_confidence_setups" in data
```

---

## Troubleshooting

### Error: "ML system not available"

**Causa**: Sistema ML no instalado o path incorrecto

**Solución**:
```bash
# Verificar que existe el sistema ML
ls tools/backtest/box_strategy/ml/

# Re-entrenar modelos si es necesario
cd tools/backtest/box_strategy
python ml/train_models.py --data results/multi_market_results_*.json --version 1
```

### Error: "No data available for market"

**Causa**: yfinance no puede descargar datos (mercado cerrado, ticker incorrecto)

**Solución**:
- Verificar que el mercado está abierto
- Revisar ticker en MARKET_CONFIGS
- Intentar con `force_refresh=True`

### Predicciones siempre LOW confidence

**Causa**: Modelo necesita re-entrenamiento con más datos

**Solución**:
```bash
# Ejecutar backtest más largo
python run_corrected_backtest.py  # 55 días

# Re-entrenar con más datos
python ml/train_models.py --data results/latest.json --version 2
```

---

## Roadmap

- [ ] WebSocket support para updates en tiempo real
- [ ] Alertas configurables (HIGH confidence detected)
- [ ] Backtesting histórico via API
- [ ] Trade execution integration
- [ ] Performance tracking de predicciones ML
- [ ] Multi-timeframe analysis (1h, 4h, daily)

---

## Soporte

Para issues o preguntas:
1. Revisar logs: `logs/api.log`
2. Verificar Swagger docs: `http://localhost:8000/docs`
3. Testear endpoint con curl antes de integrar frontend
