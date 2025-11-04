# PupupuV3 - Cambios en los Endpoints para el Frontend

## Endpoint Actualizado: `/api/v1/pupupuv3/current-analysis`

### Nuevos Campos Añadidos

El endpoint ha sido mejorado para proporcionar más información de debugging sobre los indicadores y condiciones de trading.

### Response Schema Actualizado

```typescript
interface CurrentAnalysisResponse {
  symbol: string;
  timestamp: number;
  datetime: string;
  current_price: number;

  // ✅ NUEVO: Sección de indicadores con detalles adicionales
  indicators: {
    ema_15: number;              // EMA 15 actual
    ema_distance_pct: number;    // % distancia entre precio y EMA
    ema_above_price: boolean;    // ¿EMA está por encima del precio?
    vwap: number;                // VWAP actual
    vwap_distance_pct: number;   // % distancia entre precio y VWAP
    vwap_above_price: boolean;   // ¿VWAP está por encima del precio?
  };

  // EXISTENTE: Pivotes activos
  active_resistances: Array<{
    price: number;
    strength: number;
    touches: number;
    bars_since: number;
  }>;

  active_supports: Array<{
    price: number;
    strength: number;
    touches: number;
    bars_since: number;
  }>;

  // ✅ NUEVO: Todos los pivotes (activos e inactivos)
  all_pivots: {
    all_resistances: Array<{
      price: number;
      strength: number;
      touches: number;
      bars_since: number;
      is_active: boolean;        // Si el pivote está activo o no
    }>;

    all_supports: Array<{
      price: number;
      strength: number;
      touches: number;
      bars_since: number;
      is_active: boolean;        // Si el pivote está activo o no
    }>;
  };

  // EXISTENTE: Volume Profile
  volume_profile: {
    poc: number;
    vah: number;
    val: number;
    in_value_area: boolean;
    near_hvn: boolean;
  };

  // EXISTENTE: Señal actual (null si no hay señal)
  signal: null | {
    direction: "LONG" | "SHORT";
    entry_price: number;
    stop_loss: number;
    tp1: number;
    tp2: number;
    tp3: number;
    position_size: number;
    risk_amount: number;
    timestamp: number;
    datetime: string;
    pivot_touch: string;
    ema_test: string;
    vwap_aligned: string;
    volume_profile_support: string;
  };

  // ✅ NUEVO: Condiciones de señal (solo presente cuando signal es null)
  signal_conditions: null | {
    price_near_resistance: boolean;        // Precio cerca de resistencia
    closest_resistance_distance: number;   // Distancia a resistencia más cercana
    closest_resistance_price: number | null;
    price_near_support: boolean;           // Precio cerca de soporte
    closest_support_distance: number;      // Distancia a soporte más cercano
    closest_support_price: number | null;
    ema_above_price: boolean;
    ema_distance: number;
    ema_distance_pct: number;
    vwap_above_price: boolean;
    vwap_distance: number;
    vwap_distance_pct: number;
    in_value_area: boolean;
    near_hvn: boolean;
  };

  // EXISTENTE: Predicción del modelo ML
  ml_prediction: null | {
    tp2_ratio: number;
    tp2_price: number;
    tp2_probability: number;
    tp2_timeframe: string;
    tp3_ratio: number;
    tp3_price: number;
    tp3_probability: number;
    tp3_timeframe: string;
    confidence_score: number;
  };

  ml_model_active: boolean;
}
```

### Ejemplo de Response SIN Señal

```json
{
  "symbol": "BTC/USDT",
  "timestamp": 1730280000000,
  "datetime": "2025-10-30T10:00:00",
  "current_price": 110500.50,

  "indicators": {
    "ema_15": 110450.25,
    "ema_distance_pct": 0.045,
    "ema_above_price": false,
    "vwap": 110600.75,
    "vwap_distance_pct": 0.091,
    "vwap_above_price": true
  },

  "active_resistances": [
    {
      "price": 111000.00,
      "strength": 75.5,
      "touches": 15,
      "bars_since": 45
    }
  ],

  "active_supports": [
    {
      "price": 110000.00,
      "strength": 80.2,
      "touches": 20,
      "bars_since": 30
    }
  ],

  "all_pivots": {
    "all_resistances": [
      {
        "price": 111000.00,
        "strength": 75.5,
        "touches": 15,
        "bars_since": 45,
        "is_active": true
      },
      {
        "price": 112000.00,
        "strength": 60.0,
        "touches": 10,
        "bars_since": 150,
        "is_active": false
      }
    ],
    "all_supports": [
      {
        "price": 110000.00,
        "strength": 80.2,
        "touches": 20,
        "bars_since": 30,
        "is_active": true
      },
      {
        "price": 109000.00,
        "strength": 65.0,
        "touches": 12,
        "bars_since": 120,
        "is_active": false
      }
    ]
  },

  "volume_profile": {
    "poc": 110300.00,
    "vah": 111500.00,
    "val": 109000.00,
    "in_value_area": true,
    "near_hvn": true
  },

  "signal": null,

  "signal_conditions": {
    "price_near_resistance": false,
    "closest_resistance_distance": 499.50,
    "closest_resistance_price": 111000.00,
    "price_near_support": false,
    "closest_support_distance": 500.50,
    "closest_support_price": 110000.00,
    "ema_above_price": false,
    "ema_distance": 50.25,
    "ema_distance_pct": 0.045,
    "vwap_above_price": true,
    "vwap_distance": 100.25,
    "vwap_distance_pct": 0.091,
    "in_value_area": true,
    "near_hvn": true
  },

  "ml_prediction": null,
  "ml_model_active": true
}
```

### Ejemplo de Response CON Señal

```json
{
  "symbol": "BTC/USDT",
  "timestamp": 1730280000000,
  "datetime": "2025-10-30T10:00:00",
  "current_price": 110000.50,

  "indicators": {
    "ema_15": 110010.00,
    "ema_distance_pct": 0.009,
    "ema_above_price": true,
    "vwap": 109950.00,
    "vwap_distance_pct": 0.046,
    "vwap_above_price": false
  },

  "active_resistances": [],
  "active_supports": [
    {
      "price": 110000.00,
      "strength": 85.5,
      "touches": 25,
      "bars_since": 5
    }
  ],

  "all_pivots": {
    "all_resistances": [...],
    "all_supports": [...]
  },

  "volume_profile": {
    "poc": 110100.00,
    "vah": 111000.00,
    "val": 109200.00,
    "in_value_area": true,
    "near_hvn": true
  },

  "signal": {
    "direction": "LONG",
    "entry_price": 110000.50,
    "stop_loss": 109800.00,
    "tp1": 110100.00,
    "tp2": 110300.00,
    "tp3": 110600.00,
    "position_size": 0.27,
    "risk_amount": 30.00,
    "timestamp": 1730280000000,
    "datetime": "2025-10-30T10:00:00",
    "pivot_touch": "✅ Support at 110000.00",
    "ema_test": "✅ Price near EMA (0.009%)",
    "vwap_aligned": "✅ LONG above VWAP",
    "volume_profile_support": "✅ Near HVN"
  },

  "signal_conditions": null,

  "ml_prediction": {
    "tp2_ratio": 1.5,
    "tp2_price": 110300.00,
    "tp2_probability": 75.5,
    "tp2_timeframe": "15-30min",
    "tp3_ratio": 3.0,
    "tp3_price": 110600.00,
    "tp3_probability": 45.2,
    "tp3_timeframe": "30-60min",
    "confidence_score": 82.3
  },

  "ml_model_active": true
}
```

## Cómo Usar los Nuevos Campos en el Frontend

### 1. Mostrar Indicadores con Distancias

```typescript
function IndicatorCard({ analysis }: { analysis: CurrentAnalysisResponse }) {
  const { indicators } = analysis;

  return (
    <div>
      <h3>Indicadores</h3>

      <div>
        <p>EMA 15: {indicators.ema_15.toFixed(2)}</p>
        <p>Distancia: {indicators.ema_distance_pct.toFixed(2)}%</p>
        <p>Posición: {indicators.ema_above_price ? "EMA arriba" : "EMA abajo"}</p>
      </div>

      <div>
        <p>VWAP: {indicators.vwap.toFixed(2)}</p>
        <p>Distancia: {indicators.vwap_distance_pct.toFixed(2)}%</p>
        <p>Posición: {indicators.vwap_above_price ? "VWAP arriba" : "VWAP abajo"}</p>
      </div>
    </div>
  );
}
```

### 2. Mostrar Todos los Pivotes (Activos e Inactivos)

```typescript
function PivotsCard({ analysis }: { analysis: CurrentAnalysisResponse }) {
  const { all_pivots } = analysis;

  return (
    <div>
      <h3>Resistencias</h3>
      {all_pivots.all_resistances.map((r, i) => (
        <div key={i} className={r.is_active ? "active" : "inactive"}>
          <p>{r.price} - Fuerza: {r.strength.toFixed(1)}</p>
          <p>Toques: {r.touches} | Barras: {r.bars_since}</p>
          <p>Estado: {r.is_active ? "✅ Activo" : "⏸️ Inactivo"}</p>
        </div>
      ))}

      <h3>Soportes</h3>
      {all_pivots.all_supports.map((s, i) => (
        <div key={i} className={s.is_active ? "active" : "inactive"}>
          <p>{s.price} - Fuerza: {s.strength.toFixed(1)}</p>
          <p>Toques: {s.touches} | Barras: {s.bars_since}</p>
          <p>Estado: {s.is_active ? "✅ Activo" : "⏸️ Inactivo"}</p>
        </div>
      ))}
    </div>
  );
}
```

### 3. Mostrar Por Qué NO Hay Señal (signal_conditions)

```typescript
function SignalStatusCard({ analysis }: { analysis: CurrentAnalysisResponse }) {
  if (analysis.signal) {
    return <div>✅ Señal activa: {analysis.signal.direction}</div>;
  }

  const { signal_conditions } = analysis;

  if (!signal_conditions) {
    return <div>Analizando...</div>;
  }

  return (
    <div>
      <h3>¿Por qué no hay señal?</h3>

      <div>
        <h4>Pivotes</h4>
        <p>Cerca de resistencia: {signal_conditions.price_near_resistance ? "✅" : "❌"}</p>
        {signal_conditions.closest_resistance_price && (
          <p>Resistencia más cercana: {signal_conditions.closest_resistance_price}
             (Distancia: {signal_conditions.closest_resistance_distance})</p>
        )}

        <p>Cerca de soporte: {signal_conditions.price_near_support ? "✅" : "❌"}</p>
        {signal_conditions.closest_support_price && (
          <p>Soporte más cercano: {signal_conditions.closest_support_price}
             (Distancia: {signal_conditions.closest_support_distance})</p>
        )}
      </div>

      <div>
        <h4>EMA & VWAP</h4>
        <p>EMA distancia: {signal_conditions.ema_distance_pct.toFixed(2)}%</p>
        <p>VWAP distancia: {signal_conditions.vwap_distance_pct.toFixed(2)}%</p>
      </div>

      <div>
        <h4>Volume Profile</h4>
        <p>En value area: {signal_conditions.in_value_area ? "✅" : "❌"}</p>
        <p>Cerca HVN: {signal_conditions.near_hvn ? "✅" : "❌"}</p>
      </div>
    </div>
  );
}
```

### 4. Dashboard Completo de Debugging

```typescript
function PupupuV3Dashboard() {
  const [analysis, setAnalysis] = useState<CurrentAnalysisResponse | null>(null);

  useEffect(() => {
    const fetchAnalysis = async () => {
      const res = await fetch('/api/v1/pupupuv3/current-analysis?symbol=BTC/USDT');
      const data = await res.json();
      setAnalysis(data);
    };

    fetchAnalysis();
    const interval = setInterval(fetchAnalysis, 60000); // Cada 1 min

    return () => clearInterval(interval);
  }, []);

  if (!analysis) return <div>Cargando...</div>;

  return (
    <div className="dashboard">
      <h1>PupupuV3 - {analysis.symbol}</h1>
      <p>Precio: {analysis.current_price}</p>
      <p>Hora: {new Date(analysis.timestamp).toLocaleString()}</p>

      <IndicatorCard analysis={analysis} />
      <PivotsCard analysis={analysis} />
      <SignalStatusCard analysis={analysis} />

      {analysis.ml_model_active && (
        <div>
          <h3>ML Model: ✅ Activo</h3>
          {analysis.ml_prediction && (
            <div>
              <p>TP2: {analysis.ml_prediction.tp2_price} ({analysis.ml_prediction.tp2_probability}%)</p>
              <p>TP3: {analysis.ml_prediction.tp3_price} ({analysis.ml_prediction.tp3_probability}%)</p>
              <p>Confianza: {analysis.ml_prediction.confidence_score}%</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

## Resumen de Cambios

### ✅ Campos Nuevos

1. **`indicators`**: Objeto con EMA y VWAP, incluyendo distancias y posiciones relativas
2. **`all_pivots`**: Objeto con TODOS los pivotes (activos e inactivos) para debugging
3. **`signal_conditions`**: Cuando NO hay señal, muestra exactamente por qué no se generó

### ✅ Campos Existentes (Sin Cambios)

- `active_resistances`, `active_supports`
- `volume_profile`
- `signal`
- `ml_prediction`
- `ml_model_active`

### 🎯 Beneficios

1. **Debugging completo**: Ahora puedes ver EXACTAMENTE por qué no se generan señales
2. **Transparencia**: Ves todos los pivotes, no solo los activos
3. **Información rica**: Distancias y porcentajes para todos los indicadores
4. **Mismo endpoint**: No hay cambios breaking, solo campos adicionales

## URL del Endpoint

```
GET http://localhost:8000/api/v1/pupupuv3/current-analysis?symbol=BTC/USDT
```

Params:
- `symbol`: Par de trading (ej: "BTC/USDT", "ETH/USDT")
