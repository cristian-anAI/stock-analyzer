# PupupuV3 - Standalone API Setup

## Overview

PupupuV3 puede ejecutarse de dos formas:

1. **Standalone** - Solo PupupuV3 en puerto 8001 (para debugging)
2. **Full API** - Todo el sistema en puerto 8000 (para producción)

## Opción 1: Standalone (Debugging) ✅ Recomendado para desarrollo

### Windows
```bash
start_pupupuv3_api.bat
```

### Linux/Mac
```bash
python run_pupupuv3_api.py
```

### Características
- **Puerto:** 8001
- **Endpoints:** Solo PupupuV3
- **Peso:** Ligero, rápido de arrancar
- **Uso:** Debugging, desarrollo, pruebas

### Endpoints Disponibles
```
http://localhost:8001/                           # Root
http://localhost:8001/health                     # Health check
http://localhost:8001/api/v1/pupupuv3/signals    # Get signals
http://localhost:8001/api/v1/pupupuv3/pivots     # Get pivots
http://localhost:8001/api/v1/pupupuv3/check      # Check strategy
http://localhost:8001/docs                       # Swagger UI
```

### Ejemplo de uso
```bash
# Arrancar servidor standalone
python run_pupupuv3_api.py

# En otra terminal - probar endpoint
curl http://localhost:8001/api/v1/pupupuv3/signals?symbol=BTC/USDT
```

## Opción 2: Full API (Producción)

### Windows
```bash
start_api.bat
```

### Linux/Mac
```bash
python run_api.py
```

### Características
- **Puerto:** 8000
- **Endpoints:** Todo el sistema (autotrader, portfolio, positions, pupupuv3, etc.)
- **Peso:** Completo, tarda más en arrancar
- **Uso:** Producción, testing completo

### Endpoints PupupuV3 en Full API
```
http://localhost:8000/api/v1/pupupuv3/signals
http://localhost:8000/api/v1/pupupuv3/pivots
http://localhost:8000/api/v1/pupupuv3/check
```

## Comparación

| Característica | Standalone (8001) | Full API (8000) |
|---|---|---|
| **Arranque** | Rápido (~2s) | Lento (~10s) |
| **Memoria** | Bajo (~200MB) | Alto (~500MB) |
| **Endpoints** | Solo PupupuV3 | Todo el sistema |
| **Database** | No inicia servicios BG | Inicia scheduler, autotrader, etc. |
| **Uso** | Debugging diario | Producción |
| **Puerto** | 8001 | 8000 |

## Cuándo usar cada uno

### Usa Standalone cuando:
- ✅ Es domingo y solo quieres debugear PupupuV3
- ✅ Estás desarrollando nuevas features
- ✅ Quieres probar cambios rápidamente
- ✅ No necesitas autotrader ni otros servicios
- ✅ Quieres arrancar rápido sin esperar

### Usa Full API cuando:
- ✅ Estás en producción
- ✅ Necesitas todos los servicios (autotrader, portfolio, etc.)
- ✅ Quieres probar integración completa
- ✅ Necesitas el scheduler de background

## Desarrollo Típico

```bash
# 1. Debugging domingo por la mañana
python run_pupupuv3_api.py

# 2. Probar cambios
curl http://localhost:8001/api/v1/pupupuv3/signals?symbol=BTC/USDT

# 3. Si todo bien, probar con full API
python run_api.py

# 4. Verificar en producción
curl http://localhost:8000/api/v1/pupupuv3/signals?symbol=BTC/USDT
```

## Estructura de Archivos

```
stock-analyzer/
├── run_api.py                      # Full API (puerto 8000)
├── run_pupupuv3_api.py            # Standalone PupupuV3 (puerto 8001) ⭐ NEW
├── start_api.bat                   # Windows launcher - Full API
├── start_pupupuv3_api.bat         # Windows launcher - Standalone ⭐ NEW
├── src/
│   ├── api/
│   │   ├── main.py                # Full API app
│   │   └── routers/
│   │       └── pupupuv3.py        # PupupuV3 router (compartido)
│   ├── strategy/
│   │   └── pupupuv3_signals.py    # PupupuV3 strategy
│   └── indicators/
│       ├── pivot_detector_simple.py
│       └── session_indicators.py
└── tradingview_pivot_rolling.pine  # TradingView indicator
```

## Ventajas de esta Arquitectura

### ✅ No duplicas código
- Un solo `pupupuv3.py` router
- Un solo `pupupuv3_signals.py` strategy
- Compartido entre ambas APIs

### ✅ Desarrollo rápido
- Arranca solo lo que necesitas
- Ciclo de desarrollo más rápido
- Menos recursos consumidos

### ✅ Fácil de mantener
- Un solo repositorio
- Cambios se reflejan en ambas versiones
- No hay sincronización manual

### ✅ Producción robusta
- Full API tiene todo
- Standalone no interfiere
- Puertos diferentes (8000 vs 8001)

## Testing

### Test Standalone
```bash
# Terminal 1: Arrancar servidor
python run_pupupuv3_api.py

# Terminal 2: Probar endpoints
curl http://localhost:8001/health
curl http://localhost:8001/api/v1/pupupuv3/signals?symbol=BTC/USDT
curl http://localhost:8001/api/v1/pupupuv3/pivots?symbol=BTC/USDT
```

### Test Full API
```bash
# Terminal 1: Arrancar servidor
python run_api.py

# Terminal 2: Probar endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/pupupuv3/signals?symbol=BTC/USDT
curl http://localhost:8000/api/v1/positions
curl http://localhost:8000/api/v1/portfolio
```

## Docker (Futuro)

Puedes crear dos servicios Docker:

```yaml
# docker-compose.yml
services:
  pupupuv3-api:
    build: .
    command: python run_pupupuv3_api.py
    ports:
      - "8001:8001"

  full-api:
    build: .
    command: python run_api.py
    ports:
      - "8000:8000"
```

## Notas

- **Puerto 8001** solo se usa para standalone
- **Puerto 8000** es el puerto principal de producción
- Ambos pueden correr simultáneamente (puertos diferentes)
- Comparten la misma base de código
- No hay conflictos entre ambos

## Próximos Pasos

1. ✅ Prueba standalone: `python run_pupupuv3_api.py`
2. ✅ Verifica endpoints en http://localhost:8001/docs
3. ✅ Compara con TradingView usando el indicador Pine Script
4. ✅ Si todo OK, prueba full API: `python run_api.py`
5. ✅ Deploy a producción con full API

---

**Recomendación Final:** Usa standalone para debugging diario, full API para producción. No necesitas crear un proyecto separado.
