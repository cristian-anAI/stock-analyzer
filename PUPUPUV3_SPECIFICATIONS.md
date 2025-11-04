# PupupuV3 - High Frequency Scalping Strategy

**Timeframe**: 1 minuto
**Instrumento**: BTC/USDT (Crypto)
**Tipo**: Scalping de alta frecuencia con ML
**Capital**: $30,000 (cartera crypto)
**Riesgo por trade**: 2% ($600)

---

## 🎯 DIFERENCIAS CLAVE CON PUPUPUV2

### Timeframe y Parámetros
| Parámetro | PupupuV2 (Viejo) | PupupuV3 (Nuevo) |
|-----------|------------------|------------------|
| **Timeframe** | 5 minutos | **1 minuto** |
| **EMA** | 12 períodos (~60 min) | **15 períodos (15 min)** |
| **Pivotes Lookback** | 400 períodos | **100 períodos** |
| **Volume Profile** | 3 timeframes (4h, 24h, 7d) | **Solo el más alto (7d)** |
| **Risk per trade** | 2% de $10k = $200 | **2% de $30k = $600** |

### Nuevo: VWAP Filter
- **VWAP** (Volume Weighted Average Price) añadido como filtro de dirección
- **Regla**:
  - Precio **< VWAP** → Preferir **LONG** (precio tiende a volver al VWAP)
  - Precio **> VWAP** → Preferir **SHORT** (precio tiende a bajar al VWAP)
  - **Excepción**: Si ML confidence > 60%, permitir trade contra VWAP con **50% del riesgo**

### Gestión de Trade Mejorada
- **TP1**: Ratio 1:1 (mismo tamaño que el riesgo)
- **Break Even**: Al alcanzar TP1, mover SL a entry price
- **TP2, TP3**: Dejar correr (ratios 5:1, 10:1, 20:1 posibles)
- **No Test**: Si precio va directo a TP1 sin testear la EMA → cerrar pending y guardar como "NO_TEST"

---

## 📊 LÓGICA DE SEÑALES

### Setup LONG
```
1. Precio forma pivot LOW (soporte)
2. Precio sube y cruza EMA(15)
3. Primera vela verde que cierra ARRIBA de EMA
4. FILTRO VWAP:
   - Si precio < VWAP: Riesgo completo ($600)
   - Si precio > VWAP y ML > 60%: Riesgo reducido ($300)
   - Si precio > VWAP y ML < 60%: NO operar

5. Colocar LIMIT en precio de EMA para siguiente vela
6. SL = Precio del pivot (última línea roja de Pupupu)
7. TP1 = Entry + (Entry - SL) × 1.0  [Ratio 1:1]
```

### Setup SHORT
```
1. Precio forma pivot HIGH (resistencia)
2. Precio baja y cruza EMA(15)
3. Primera vela roja que cierra DEBAJO de EMA
4. FILTRO VWAP:
   - Si precio > VWAP: Riesgo completo ($600)
   - Si precio < VWAP y ML > 60%: Riesgo reducido ($300)
   - Si precio < VWAP y ML < 60%: NO operar

5. Colocar LIMIT en precio de EMA para siguiente vela
6. SL = Precio del pivot (última línea verde de Pupupu)
7. TP1 = Entry - (SL - Entry) × 1.0  [Ratio 1:1]
```

---

## 🎯 GESTIÓN DE POSICIÓN

### Ciclo de Vida del Trade

```
PENDING → ACTIVE → TP1_HIT → RUNNER
          ↓
        SL_HIT
          ↓
       NO_TEST
```

**Estados**:
1. **PENDING**: Limit order colocada, esperando fill
2. **ACTIVE**: Trade abierto, buscando TP1
3. **TP1_HIT**: TP1 alcanzado, SL movido a BE, dejando correr
4. **RUNNER**: Trade extendido (TP2, TP3, trailing)
5. **SL_HIT**: Stop loss ejecutado
6. **NO_TEST**: Precio fue directo a TP1 sin testear EMA

### Take Profits Dinámicos

**TP1** (Ratio 1:1):
- Cierra **50%** de la posición
- Mueve SL a **breakeven**
- Deja correr el resto

**TP2** (Ratio 3:1):
- Cierra **25%** adicional
- Mueve SL a TP1

**TP3** (Ratio 5:1+):
- Trailing stop activado
- Dejar correr mientras no haya divergencia RSI fuerte

---

## 📈 INDICADORES TÉCNICOS

### 1. EMA(15)
```python
ema_period = 15  # 15 velas de 1 min = 15 minutos
```
- Filtro de tendencia de corto plazo
- Entry point para limit orders

### 2. SM Channel (Swing Market Pivots)
```python
lookback_periods = 100  # 100 velas de 1 min
swing_detection_bars = 5
```
- Identifica pivotes ÚNICOS más relevantes
- No múltiples pivotes cercanos (problema del V2)
- Solo las líneas rojas/verdes más fuertes

### 3. VWAP (Volume Weighted Average Price)
```python
# Calcula VWAP desde inicio de sesión
vwap = cumsum(price * volume) / cumsum(volume)
```
- **Magnético**: Precio tiende a revertir hacia VWAP
- **Filtro de dirección**:
  - Price < VWAP → bias LONG
  - Price > VWAP → bias SHORT

### 4. Volume Profile (Solo Largo Plazo)
```python
vp_periodo = "7d"  # Solo timeframe más alto
hvn_nodes_count = 5
lvn_nodes_count = 3
```
- Eliminar VP corto (4h) y medio (24h)
- Solo usar VP de 7 días para contexto mayor
- Usar HVN como zonas de resistencia/soporte macro

---

## 🤖 MACHINE LEARNING

### Features Principales

```python
FEATURES_V3 = {
    # Pivotes y estructura
    "pivot_strength": float,        # Fuerza del pivot tocado
    "pivot_touches": int,           # Veces que fue testeado
    "distance_from_pivot": float,   # % distancia del precio al pivot

    # EMA
    "ema_slope": float,             # Pendiente de EMA (alcista/bajista)
    "distance_from_ema_pct": float, # % distancia del precio a EMA
    "ema_cross_strength": float,    # Fuerza del cruce (tamaño de vela)

    # VWAP (NUEVO)
    "vwap_position": float,         # -1 (abajo), 0 (en), +1 (arriba)
    "distance_from_vwap_pct": float,# % distancia del precio a VWAP
    "vwap_slope": float,            # Tendencia del VWAP

    # Volume Profile (simplificado)
    "near_hvn_7d": bool,            # Cerca de HVN en VP 7d
    "near_poc_7d": bool,            # Cerca de POC en VP 7d

    # Volatilidad
    "atr_14": float,                # Average True Range
    "volatility_pct": float,        # Volatilidad reciente

    # RSI
    "rsi_14": float,                # RSI clásico
    "rsi_divergence": int,          # -1, 0, +1

    # Volumen
    "volume_ratio": float,          # Volumen actual vs promedio
    "volume_trend": float           # Tendencia del volumen
}
```

### Target Variable
```python
# Outcome del trade
target = {
    "tp1_hit": bool,           # ¿Alcanzó TP1?
    "sl_hit": bool,            # ¿Alcanzó SL?
    "no_test": bool,           # ¿No testeó EMA?
    "max_rr_achieved": float,  # Máximo R:R logrado
    "pnl_usd": float          # P&L en USD
}
```

### Modelo
- **Random Forest** + **XGBoost** (ensemble)
- **Threshold de confianza**: 60% para trade contra VWAP

---

## 💾 DATABASE SCHEMA

### Tabla: `pupupuv3_signals`

```sql
CREATE TABLE pupupuv3_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    direction TEXT NOT NULL,  -- 'LONG' | 'SHORT'

    -- Prices
    entry_price REAL NOT NULL,
    stop_loss REAL NOT NULL,
    tp1 REAL NOT NULL,
    tp2 REAL,
    tp3 REAL,

    -- Pivot info
    pivot_price REAL NOT NULL,
    pivot_strength REAL,
    pivot_touches INTEGER,

    -- EMA
    ema_value REAL NOT NULL,
    ema_cross_confirmed BOOLEAN,

    -- VWAP (NEW)
    vwap_value REAL NOT NULL,
    price_vs_vwap TEXT,  -- 'below' | 'above' | 'at'
    vwap_aligned BOOLEAN,

    -- Position sizing
    risk_usd REAL NOT NULL,
    position_size_usd REAL NOT NULL,
    risk_reduction_applied BOOLEAN DEFAULT FALSE,

    -- ML
    ml_confidence REAL,
    ml_features_json TEXT,

    -- Volume Profile
    near_hvn_7d BOOLEAN,
    near_poc_7d BOOLEAN,

    -- Trade status
    status TEXT DEFAULT 'PENDING',  -- PENDING | ACTIVE | TP1_HIT | RUNNER | SL_HIT | NO_TEST

    -- Outcomes
    filled_price REAL,
    fill_time DATETIME,
    exit_price REAL,
    exit_time DATETIME,
    exit_reason TEXT,  -- 'TP1' | 'TP2' | 'TP3' | 'SL' | 'BE' | 'NO_TEST'

    pnl_usd REAL,
    rr_achieved REAL,

    -- Metadata
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Tabla: `pupupuv3_trades`

```sql
CREATE TABLE pupupuv3_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER REFERENCES pupupuv3_signals(id),

    entry_price REAL NOT NULL,
    entry_time DATETIME NOT NULL,
    stop_loss REAL NOT NULL,
    current_stop_loss REAL NOT NULL,  -- Puede moverse a BE

    tp1_hit BOOLEAN DEFAULT FALSE,
    tp1_hit_time DATETIME,
    tp2_hit BOOLEAN DEFAULT FALSE,
    tp2_hit_time DATETIME,
    tp3_hit BOOLEAN DEFAULT FALSE,
    tp3_hit_time DATETIME,

    stop_at_breakeven BOOLEAN DEFAULT FALSE,
    stop_moved_time DATETIME,

    is_runner BOOLEAN DEFAULT FALSE,
    max_rr_achieved REAL,

    closed BOOLEAN DEFAULT FALSE,
    close_price REAL,
    close_time DATETIME,
    close_reason TEXT,

    final_pnl_usd REAL,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔧 CONFIGURACIÓN

```python
PUPUPUV3_CONFIG = {
    # Timeframe
    "timeframe": "1m",
    "ema_period": 15,
    "pivot_lookback": 100,
    "swing_bars": 5,

    # VWAP
    "vwap_enabled": True,
    "vwap_filter_strict": True,  # Requiere alineación
    "vwap_tolerance_pct": 0.1,   # % de tolerancia para "at VWAP"

    # Volume Profile
    "vp_use_only_long": True,    # Solo VP 7d
    "vp_period_days": 7,
    "vp_num_bins": 60,

    # Risk Management
    "capital_crypto": 30000,
    "risk_per_trade_pct": 0.02,  # 2%
    "risk_reduced_pct": 0.01,    # 1% si contra VWAP

    # Take Profits
    "tp1_ratio": 1.0,   # 1:1
    "tp2_ratio": 3.0,   # 3:1
    "tp3_ratio": 5.0,   # 5:1
    "trailing_stop_activation": 5.0,  # Activar trailing en 5:1

    # Position Management
    "tp1_close_pct": 0.5,   # Cerrar 50% en TP1
    "tp2_close_pct": 0.25,  # Cerrar 25% en TP2
    "move_sl_to_be_on_tp1": True,

    # ML
    "ml_enabled": True,
    "ml_min_confidence": 0.6,  # 60% para trade contra VWAP
    "ml_version": "v3",

    # Filters
    "min_volume": 100.0,
    "max_volatility_mult": 2.5,
    "cooldown_minutes": 5  # Min tiempo entre señales
}
```

---

## 📁 ESTRUCTURA DE ARCHIVOS

```
src/
├── indicators/
│   ├── vwap.py                    # NUEVO: VWAP calculation
│   ├── pivot_detector_v3.py       # MEJORADO: Solo pivotes relevantes
│   └── volume_profile.py          # EXISTENTE: Modificar para solo 7d
│
├── strategy/
│   ├── pupupuv3_signals.py        # NUEVA: Lógica de señales V3
│   └── pupupuv3_trade_manager.py  # NUEVO: Gestión de trades activos
│
├── risk/
│   ├── position_sizer_v3.py       # NUEVO: Con riesgo reducido
│   └── trade_lifecycle.py         # NUEVO: Estados de trade
│
├── data/
│   └── binance_client_1m.py       # NUEVO: Cliente para 1-min data
│
└── ml/
    ├── features_v3.py              # NUEVO: Features con VWAP
    └── model_v3.py                 # NUEVO: Modelo V3

pupupuv3_bot.py                     # Bot principal
backtest_pupupuv3.py                # Backtesting V3
```

---

## 🚀 ROADMAP DE IMPLEMENTACIÓN

### Fase 1: Core Indicators (1-2 días)
- [ ] VWAP calculator
- [ ] Pivot detector V3 (solo relevantes)
- [ ] Volume Profile (solo 7d)
- [ ] EMA(15) con 1-min data

### Fase 2: Signal Generation (2-3 días)
- [ ] PupupuV3 signal logic
- [ ] VWAP filter integration
- [ ] ML feature engineering V3
- [ ] Position sizing con riesgo reducido

### Fase 3: Trade Management (2-3 días)
- [ ] Trade lifecycle manager
- [ ] TP1/TP2/TP3 tracking
- [ ] Break even automation
- [ ] NO_TEST detection

### Fase 4: Testing (3-5 días)
- [ ] Backtesting con 1-min data
- [ ] Validación de VWAP filter
- [ ] Performance metrics
- [ ] Optimización de parámetros

### Fase 5: Production (2-3 días)
- [ ] Database setup
- [ ] API endpoints
- [ ] Frontend integration
- [ ] Monitoring & alerts

---

## ✅ RESUMEN DE MEJORAS

**Problemas del V2 → Soluciones en V3**:

1. ❌ Pivotes múltiples poco relevantes
   ✅ **Solo los pivotes MÁS fuertes (100 períodos)**

2. ❌ Volume Profile 3 timeframes = ruido
   ✅ **Solo VP 7d (contexto macro)**

3. ❌ Sin filtro direccional
   ✅ **VWAP filter (magnético)**

4. ❌ Timeframe 5-min = pocas oportunidades
   ✅ **1-min = alta frecuencia**

5. ❌ TP fijo en 1.7:1
   ✅ **TP dinámico (1:1 BE, luego runner)**

6. ❌ No tracking de estados
   ✅ **Lifecycle completo (PENDING → RUNNER)**

---

**¿Empezamos con la implementación?**
