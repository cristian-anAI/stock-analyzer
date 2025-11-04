# Prompt para el Frontend - Box Strategy Dashboard

Copia y pega este prompt a tu asistente de IA (Claude, Cursor, etc.) para integrar el nuevo endpoint de Box Strategy en el frontend.

---

## 📋 PROMPT COMPLETO

```
He creado un nuevo endpoint API para la estrategia de caja (Box Strategy) con predicciones ML para múltiples mercados globales.

ENDPOINT BASE: http://localhost:8000/api/v1/box-strategy

ENDPOINTS DISPONIBLES:

1. GET /dashboard - Dashboard completo con resumen y predicciones
   URL: http://localhost:8000/api/v1/box-strategy/dashboard?ml_version=1

2. GET /tradeable - Solo setups operables con breakouts
   URL: http://localhost:8000/api/v1/box-strategy/tradeable?min_confidence=HIGH

3. GET /market/{code} - Detalle de mercado específico
   URL: http://localhost:8000/api/v1/box-strategy/market/SPX

4. GET /markets - Todos los mercados
   URL: http://localhost:8000/api/v1/box-strategy/markets

5. GET /config - Configuración de mercados
   URL: http://localhost:8000/api/v1/box-strategy/config

MERCADOS SOPORTADOS: SPX, NDX, DAX, FTSE, STOXX, CAC, NKY, HSI, ASX, IBEX

NECESITO QUE CREES:

1. Una nueva página/ruta para "Box Strategy" en el menú de navegación

2. Un dashboard que muestre:
   - Estadísticas resumen (total markets, breakouts, high confidence setups)
   - Lista de setups de ALTA confianza destacados (HIGH confidence)
   - Tabla/cards con todos los breakouts detectados mostrando:
     * Market (SPX, NDX, etc.)
     * Direction (LONG/SHORT)
     * Win Probability (%)
     * Confidence Level (HIGH/MEDIUM/LOW badge con colores)
     * Recommendation (TRADE/REDUCE_SIZE/SKIP)
     * Entry Price
     * Stop Loss
     * TP1, TP2, TP3
   - Indicador de estado por mercado (BOX PERIOD / POST BOX / PENDING)

3. Auto-refresh cada 5 minutos del dashboard

4. Filtros opcionales:
   - Por mercado (SPX, NDX, etc.)
   - Por confidence level (HIGH/MEDIUM/LOW)
   - Solo breakouts activos

5. Estilos:
   - HIGH confidence: Verde/Green
   - MEDIUM confidence: Amarillo/Yellow
   - LOW confidence: Rojo/Red
   - LONG direction: Azul/Blue
   - SHORT direction: Naranja/Orange

EJEMPLO DE RESPONSE DEL /dashboard:

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
  "high_confidence_setups": [
    {
      "market": "NDX",
      "name": "NASDAQ 100",
      "status": { ... },
      "box_setup": {
        "direction": "LONG",
        "entry_price": 23670.50,
        "stop_loss": 23655.50,
        "tp1": 23685.50,
        "tp2": 23700.50,
        "tp3": 23715.50,
        "risk_points": 15.00,
        "current_price": 23672.30,
        "breakout_detected": true
      },
      "ml_prediction": {
        "win_probability": 0.78,
        "confidence_level": "HIGH",
        "recommendation": "TRADE",
        "position_size_multiplier": 1.0,
        "model_used": "random_forest"
      }
    }
  ],
  "all_breakouts": [ ... ],
  "all_markets": [ ... ]
}

INTEGRA ESTE NUEVO DASHBOARD EN EL FRONTEND EXISTENTE.

Si el proyecto usa React/Next.js, crea los componentes necesarios.
Si es Vue, adapta a Vue components.
Si es otro framework, adáptalo según corresponda.

Usa el mismo estilo y estructura que las otras páginas del proyecto para mantener consistencia.
```

---

## 🎨 PROMPT ALTERNATIVO (Más Específico para React/Next.js)

Si tu frontend es React o Next.js, usa este prompt más específico:

```
NUEVO FEATURE: Box Strategy Dashboard con ML Predictions

He creado un endpoint API completo para monitorizar la estrategia de caja.

API ENDPOINT: http://localhost:8000/api/v1/box-strategy/dashboard

CREAR NUEVA PÁGINA:
Ruta: /box-strategy o /strategies/box

ESTRUCTURA DE LA PÁGINA:

1. HEADER SECTION
   - Título: "Box Strategy Monitor"
   - Subtítulo: "ML-Powered Multi-Market Analysis"
   - Last Update timestamp
   - Refresh button (manual)
   - Auto-refresh cada 5 minutos

2. SUMMARY CARDS (Grid 6 columnas)
   - Total Markets
   - Pending Box
   - Active Box
   - Box Complete
   - Breakouts Detected
   - High Confidence Setups

3. HIGH CONFIDENCE SECTION (Destacado con border verde)
   - Título: "High Confidence Setups" con badge count
   - Cards grandes mostrando:
     * Market name
     * Direction (LONG/SHORT badge)
     * Win Probability (grande, bold)
     * Confidence badge (GREEN para HIGH)
     * Trade setup (Entry, Stop, TP1, TP2, TP3)
     * Current price
     * Recommendation: "TRADE - Full Position (100%)"

4. ALL BREAKOUTS TABLE
   - Tabla o grid de cards con todos los breakouts
   - Columnas:
     * Market
     * Direction
     * Entry Price
     * Current Price
     * Win Probability
     * Confidence Level
     * Position Size
     * Recommendation
   - Sortable por Win Probability
   - Filtrable por Confidence

5. ALL MARKETS OVERVIEW (Grid compacto)
   - Mini cards mostrando:
     * Market name
     * Status (PENDING/ACTIVE/COMPLETE badge)
     * Box range (si disponible)
     * Next box time (para pending)

TYPESCRIPT INTERFACES:

interface MLPrediction {
  win_probability: number;
  confidence_level: 'HIGH' | 'MEDIUM' | 'LOW';
  recommendation: 'TRADE' | 'REDUCE_SIZE' | 'SKIP';
  position_size_multiplier: number;
  model_used: string;
  model_version: string;
}

interface BoxSetup {
  market: string;
  date: string;
  box_high: number;
  box_low: number;
  box_range: number;
  current_price: number | null;
  breakout_detected: boolean;
  direction: 'LONG' | 'SHORT' | null;
  entry_price: number | null;
  stop_loss: number | null;
  tp1: number | null;
  tp2: number | null;
  tp3: number | null;
  risk_points: number | null;
}

interface MarketData {
  market: string;
  name: string;
  timezone: string;
  status: {
    is_box_period: boolean;
    is_post_box: boolean;
    box_complete: boolean;
  };
  box_setup: BoxSetup | null;
  ml_prediction: MLPrediction | null;
}

COLORES/BADGES:
- HIGH confidence: bg-green-500 text-white
- MEDIUM confidence: bg-yellow-500 text-white
- LOW confidence: bg-red-500 text-white
- LONG direction: bg-blue-500 text-white
- SHORT direction: bg-orange-500 text-white
- TRADE recommendation: text-green-600 font-bold
- REDUCE_SIZE: text-yellow-600
- SKIP: text-red-600

FETCHING:
- Usa axios o fetch
- Auto-refresh cada 5 minutos con useEffect
- Loading state mientras carga
- Error handling con mensaje amigable

AÑADE AL MENÚ DE NAVEGACIÓN:
Icono sugerido: Chart/TrendingUp/Activity
Label: "Box Strategy"

Mantén el mismo estilo visual que el resto de la app (usa los mismos componentes de UI si hay).
```

---

## 🎯 PROMPT MINIMALISTA (Si solo quieres lo básico)

```
Crear nueva página "Box Strategy" en el frontend.

Endpoint: GET http://localhost:8000/api/v1/box-strategy/dashboard

Mostrar:
1. Resumen: breakouts detectados, high confidence setups
2. Tabla de setups con: Market, Direction, Win%, Confidence, Entry, Stop, TPs
3. Badges de color: HIGH=verde, MEDIUM=amarillo, LOW=rojo
4. Auto-refresh cada 5 min

Usa el mismo estilo que el resto de la app.
```

---

## 📝 INFORMACIÓN ADICIONAL ÚTIL

Si te piden más detalles, puedes añadir:

### Ejemplo de fetch en React:

```typescript
const [dashboard, setDashboard] = useState(null);

useEffect(() => {
  const fetchDashboard = async () => {
    const response = await fetch(
      'http://localhost:8000/api/v1/box-strategy/dashboard?ml_version=1'
    );
    const data = await response.json();
    setDashboard(data);
  };

  fetchDashboard();
  const interval = setInterval(fetchDashboard, 300000); // 5 min
  return () => clearInterval(interval);
}, []);
```

### Endpoints adicionales para filtros:

```javascript
// Solo HIGH confidence
fetch('http://localhost:8000/api/v1/box-strategy/tradeable?min_confidence=HIGH')

// Mercado específico
fetch('http://localhost:8000/api/v1/box-strategy/market/SPX')

// Todos los mercados
fetch('http://localhost:8000/api/v1/box-strategy/markets')
```

---

## ✅ CHECKLIST POST-IMPLEMENTACIÓN

Después de que el frontend implemente los cambios, verifica:

- [ ] Se ve la nueva página/ruta "Box Strategy" en el menú
- [ ] El dashboard carga correctamente
- [ ] Se muestran los high confidence setups destacados
- [ ] Los badges de colores (HIGH/MEDIUM/LOW) son correctos
- [ ] La tabla de breakouts muestra todos los datos
- [ ] El auto-refresh funciona (espera 5 min o ajusta el tiempo)
- [ ] Los filtros (si los implementaron) funcionan
- [ ] El diseño es responsive (mobile/tablet/desktop)

---

## 🐛 TROUBLESHOOTING

Si el frontend tiene problemas:

**CORS Error:**
```
El API ya tiene CORS habilitado en desarrollo (allow_origins=["*"])
Si persiste, verifica que el API esté corriendo en http://localhost:8000
```

**No hay datos / Empty response:**
```
Normal si los mercados no han completado su box period aún.
Espera hasta después de las 10:00 AM ET para SPX/NDX.
Puedes probar con: curl http://localhost:8000/api/v1/box-strategy/config
```

**TypeScript errors:**
```
Copia las interfaces TypeScript del prompt en un archivo types.ts
```

---

**Listo! Copia el PROMPT COMPLETO o el específico para React según tu frontend** 🚀
