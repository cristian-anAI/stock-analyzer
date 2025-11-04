# Box Strategy API - Guía Rápida

Sistema completo de monitorización de estrategia de caja con ML para 10 mercados globales.

## 🚀 Inicio Rápido (5 minutos)

### 1. Iniciar el API

```bash
# Desde la raíz del proyecto
python run_api.py
```

El servidor estará disponible en: `http://localhost:8000`

### 2. Probar los Endpoints

```bash
# En otra terminal, ejecutar tests
python test_box_strategy_api.py
```

Esto verificará que todos los endpoints funcionan correctamente.

### 3. Ver Documentación Interactiva

Abre tu navegador en: `http://localhost:8000/docs`

Busca la sección **"box-strategy"** y prueba los endpoints interactivamente.

---

## 📊 Endpoints Principales

### Dashboard Completo (Recomendado para empezar)

```bash
curl http://localhost:8000/api/v1/box-strategy/dashboard
```

**Devuelve**:
- Resumen de todos los mercados
- Setups de alta confianza
- Breakouts activos
- Estadísticas generales

### Setups Operables (Solo breakouts)

```bash
# Todos los breakouts
curl http://localhost:8000/api/v1/box-strategy/tradeable

# Solo HIGH confidence
curl http://localhost:8000/api/v1/box-strategy/tradeable?min_confidence=HIGH
```

### Mercado Específico

```bash
curl http://localhost:8000/api/v1/box-strategy/market/SPX
```

---

## 🌍 Mercados Disponibles

| Código | Mercado | Horas Caja (Local) |
|--------|---------|-------------------|
| SPX | S&P 500 | 08:30-10:00 ET |
| NDX | NASDAQ 100 | 08:30-10:00 ET |
| DAX | DAX | 08:00-09:30 CET |
| FTSE | FTSE 100 | 08:00-09:30 GMT |
| STOXX | Euro Stoxx 50 | 08:00-09:30 CET |
| CAC | CAC 40 | 08:00-09:30 CET |
| NKY | Nikkei 225 | 09:00-10:30 JST |
| HSI | Hang Seng | 09:30-11:00 HKT |
| ASX | ASX 200 | 10:00-11:30 AEST |
| IBEX | IBEX 35 | 09:00-10:30 CET |

---

## 🎯 Workflow Diario

### Mañana (antes de apertura)

```bash
# Ver configuración de mercados
curl http://localhost:8000/api/v1/box-strategy/config | jq '.markets | keys'
```

### Durante el día (monitoreo)

```bash
# Dashboard cada 5 minutos
while true; do
  curl -s http://localhost:8000/api/v1/box-strategy/dashboard | \
    jq '.summary'
  sleep 300
done
```

### Después de cierre de caja

```bash
# Ver setups operables
curl http://localhost:8000/api/v1/box-strategy/tradeable | \
  jq '.setups[] | {market, direction: .box_setup.direction, confidence: .ml_prediction.confidence_level}'
```

---

## 🤖 Predicciones ML

### Niveles de Confianza

| Nivel | Win Probability | Tamaño Posición | Acción |
|-------|----------------|-----------------|--------|
| **HIGH** | ≥ 75% | 100% | ✅ TRADE (posición completa) |
| **MEDIUM** | 50-75% | 60% | ⚠️ REDUCE_SIZE (reducir posición) |
| **LOW** | < 50% | 0% | ❌ SKIP (no operar) |

### Ejemplo de Respuesta ML

```json
{
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

**Interpretación**:
- 55.1% de probabilidad de ganar
- Confianza MEDIA
- Tomar posición reducida (60%)

---

## 📱 Integración Frontend

### React Component

Usar el componente proporcionado:

```tsx
import BoxStrategyDashboard from './components/BoxStrategyDashboard';

function App() {
  return (
    <BoxStrategyDashboard
      mlVersion="1"
      apiBaseUrl="http://localhost:8000"
      refreshInterval={300000}  // 5 min
    />
  );
}
```

Ver archivo completo: `frontend_example_BoxStrategyDashboard.tsx`

### JavaScript Simple

```javascript
async function getHighConfidenceSetups() {
  const response = await fetch(
    'http://localhost:8000/api/v1/box-strategy/tradeable?min_confidence=HIGH'
  );
  const data = await response.json();

  console.log(`Found ${data.count} high confidence setups`);

  data.setups.forEach(setup => {
    const pred = setup.ml_prediction;
    console.log(`${setup.market}: ${pred.win_probability * 100}% - ${pred.recommendation}`);
  });
}

// Auto-refresh cada 5 minutos
setInterval(getHighConfidenceSetups, 300000);
```

---

## 🔧 Configuración

### Cambiar Versión de Modelo ML

Todos los endpoints aceptan `?ml_version=X`:

```bash
# Usar modelo v1 (default)
curl http://localhost:8000/api/v1/box-strategy/dashboard?ml_version=1

# Usar modelo v2 (re-entrenado)
curl http://localhost:8000/api/v1/box-strategy/dashboard?ml_version=2
```

### Modificar Mercados

Editar: `src/api/services/box_strategy_service.py`

```python
MARKET_CONFIGS = {
    "NEW_MARKET": MarketConfig(
        code="NEW_MARKET",
        name="Nuevo Mercado",
        ticker="TICKER=F",
        timezone="America/New_York",
        box_start=time(8, 30),
        box_end=time(10, 0),
        currency="USD",
        points_per_contract=50.0
    )
}
```

---

## 🧪 Testing

### Test Suite Completo

```bash
python test_box_strategy_api.py
```

**Tests incluidos**:
1. ✓ Config endpoint
2. ✓ All markets endpoint
3. ✓ Specific market endpoint
4. ✓ Tradeable endpoint
5. ✓ Dashboard endpoint

### Test Individual con cURL

```bash
# Test 1: Config
curl http://localhost:8000/api/v1/box-strategy/config

# Test 2: Dashboard
curl http://localhost:8000/api/v1/box-strategy/dashboard

# Test 3: SPX específico
curl http://localhost:8000/api/v1/box-strategy/market/SPX

# Test 4: High confidence setups
curl http://localhost:8000/api/v1/box-strategy/tradeable?min_confidence=HIGH
```

---

## 📖 Documentación Completa

Ver: `docs/BOX_STRATEGY_API.md`

**Incluye**:
- Descripción detallada de todos los endpoints
- Modelos de datos (TypeScript interfaces)
- Ejemplos de integración (React, Python, JavaScript)
- Troubleshooting
- Roadmap

---

## 🔍 Monitoreo en Tiempo Real

### Script Bash

```bash
#!/bin/bash
# monitor.sh - Monitoreo cada 5 minutos

while true; do
  clear
  echo "=== BOX STRATEGY MONITOR - $(date) ==="
  echo ""

  # Summary
  curl -s http://localhost:8000/api/v1/box-strategy/dashboard | \
    jq '.summary'

  echo ""
  echo "High Confidence Setups:"
  curl -s http://localhost:8000/api/v1/box-strategy/tradeable?min_confidence=HIGH | \
    jq -r '.setups[] | "\(.market): \(.ml_prediction.win_probability * 100 | round)% - \(.ml_prediction.recommendation)"'

  sleep 300
done
```

### Python Script

```python
import requests
import time
from datetime import datetime

while True:
    print(f"\n=== {datetime.now()} ===")

    # Get dashboard
    r = requests.get("http://localhost:8000/api/v1/box-strategy/dashboard")
    data = r.json()

    print(f"\nBreakouts: {data['summary']['breakouts']}")
    print(f"High Confidence: {data['summary']['high_confidence']}")
    print(f"Avg Win Prob: {data['summary']['avg_win_probability'] * 100:.1f}%")

    # High confidence setups
    for setup in data['high_confidence_setups']:
        pred = setup['ml_prediction']
        print(f"\n{setup['market']}: {pred['win_probability']*100:.1f}%")
        print(f"  Direction: {setup['box_setup']['direction']}")
        print(f"  Entry: {setup['box_setup']['entry_price']:.2f}")

    time.sleep(300)  # 5 minutes
```

---

## 🚨 Troubleshooting

### Error: "Connection refused"

**Solución**: Asegúrate de que el API está corriendo

```bash
python run_api.py
```

### Error: "ML system not available"

**Solución**: Entrenar modelos ML primero

```bash
cd tools/backtest/box_strategy
python ml/train_models.py --data results/multi_market_results_*.json --version 1
```

### No hay breakouts detectados

**Normal**: Espera a que cierre la caja (10:00 AM para SPX/NDX)

**Verificar**: Revisa el status del mercado

```bash
curl http://localhost:8000/api/v1/box-strategy/market/SPX | jq '.status'
```

---

## 📊 Ejemplo Completo del Día

```bash
# 8:00 AM - Revisar mercados que abrirán hoy
curl http://localhost:8000/api/v1/box-strategy/config | jq -r '.markets | to_entries[] | "\(.key): \(.value.box_hours.start)"'

# 10:30 AM - Ver si SPX/NDX tienen breakout
curl http://localhost:8000/api/v1/box-strategy/tradeable | jq '.setups[] | select(.market == "SPX" or .market == "NDX")'

# 11:00 AM - Verificar confianza de SPX
curl http://localhost:8000/api/v1/box-strategy/market/SPX | jq '.ml_prediction'

# Resultado ejemplo:
# {
#   "win_probability": 0.551,
#   "confidence_level": "MEDIUM",
#   "recommendation": "REDUCE_SIZE",
#   "position_size_multiplier": 0.6
# }

# DECISIÓN: Tomar posición reducida (60%) basado en MEDIUM confidence
```

---

## 🎯 Próximos Pasos

1. **Iniciar el API**: `python run_api.py`
2. **Probar endpoints**: `python test_box_strategy_api.py`
3. **Explorar Swagger**: http://localhost:8000/docs
4. **Integrar frontend**: Usar `BoxStrategyDashboard.tsx`
5. **Monitorear trades**: Configurar auto-refresh cada 5 min

---

## 📞 Archivos Clave

| Archivo | Descripción |
|---------|-------------|
| `src/api/routers/box_strategy.py` | Router FastAPI con endpoints |
| `src/api/services/box_strategy_service.py` | Lógica de negocio y ML |
| `test_box_strategy_api.py` | Test suite completo |
| `frontend_example_BoxStrategyDashboard.tsx` | Componente React |
| `docs/BOX_STRATEGY_API.md` | Documentación completa |
| `BOX_STRATEGY_QUICKSTART.md` | Este archivo |

---

**¡Todo listo para monitorizar la estrategia de caja con ML! 🎉**
