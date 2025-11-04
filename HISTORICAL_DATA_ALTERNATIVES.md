# Alternativas para Datos Históricos - Box Strategy

## Situación Actual

**API Actual**: `yfinance` (Yahoo Finance)
**Limitación**: 60 días de datos de 5 minutos
**Datos que descargamos**: OHLCV (Open, High, Low, Close, Volume) en intervalos de 5 minutos

**Tickers usados:**
```python
'SPX': 'ES=F',      # S&P 500 Futures
'NDX': 'NQ=F',      # NASDAQ 100 Futures
'RUT': 'RTY=F',     # Russell 2000 Futures
'DAX': 'FDAX=F',    # DAX Futures
'FTSE': '^FTSE',    # FTSE 100 Index
'CAC': '^FCHI',     # CAC 40 Index
'STOXX': '^STOXX50E', # Euro Stoxx 50 Index
'NKY': 'NKD=F',     # Nikkei 225 Futures
'HSI': '^HSI',      # Hang Seng Index
'ASX': '^AXJO',     # ASX 200 Index
'IBEX': '^IBEX'     # IBEX 35 Index
```

---

## Problema Específico

Para backtest robusto necesitamos:
- **Mínimo**: 1 año de datos 5-min = ~63,000 velas por mercado
- **Óptimo**: 2 años de datos 5-min = ~126,000 velas por mercado
- **yfinance**: Solo 60 días = ~6,000 velas ❌

---

## Alternativas - Análisis Completo

### 🟢 OPCIÓN 1: Polygon.io (RECOMENDADA)

**Website**: https://polygon.io/
**Tipo**: Proveedor de datos profesional
**Cobertura**: US markets principalmente (SPX, NDX, RUT perfectos)

#### Pricing:
- **Starter**: $29/mes
  - 5 API calls/minuto
  - 2 años históricos
  - **Suficiente para box strategy**

- **Developer**: $99/mes
  - 100 API calls/minuto
  - 10 años históricos
  - WebSocket real-time

- **Advanced**: $249/mes
  - Unlimited calls
  - Completo

#### ✅ PROS:
- **API excelente** - Python client oficial
- **Histórico completo** - Hasta 10 años atrás
- **5-minute data** - Exactamente lo que necesitas
- **Futures incluidos** - ES, NQ, RTY (SPX, NDX, RUT)
- **Calidad institucional** - Data limpia, sin gaps
- **Muy rápido** - Descarga batch eficiente

#### ❌ CONTRAS:
- **Costo**: $29-99/mes (pero vale la pena)
- **Solo US markets**: Europa/Asia no están (FTSE, DAX, etc.)
- Requiere API key

#### Implementación:
```python
from polygon import RESTClient
import os

client = RESTClient(api_key=os.getenv("POLYGON_API_KEY"))

# Descargar 2 años de SPX (ES futures) en 5-min
aggs = client.get_aggs(
    ticker="ES",
    multiplier=5,
    timespan="minute",
    from_="2023-01-01",
    to="2025-01-01"
)

# Convierte a DataFrame
df = pd.DataFrame(aggs)
```

**ROI**: Con $29/mes + 2 años de datos = Mejora de win rate de +10% = Se paga solo en 1 trade.

---

### 🟢 OPCIÓN 2: Interactive Brokers API (GRATIS para clientes)

**Website**: https://www.interactivebrokers.com/
**Tipo**: Broker con API completa
**Cobertura**: GLOBAL - Todos los mercados

#### Pricing:
- **GRATIS** si tienes cuenta de Interactive Brokers
- Cuenta mínima: $0 (sí, cero)
- No hay cargos mensuales por datos históricos

#### ✅ PROS:
- **GRATIS** - Solo necesitas cuenta (incluso sin fondos)
- **Cobertura global completa** - SPX, NDX, DAX, FTSE, NKY, HSI, TODO
- **Histórico ilimitado** - Años de datos
- **Calidad institucional** - Es un broker real
- **Real-time data** - Para live trading futuro
- **Python library** - `ib_insync` muy buena

#### ❌ CONTRAS:
- **Complejidad setup** - Requiere instalar TWS (Trader Workstation)
- **Rate limits** - 60 requests/600 segundos (1 por 10 seg)
- **Curva de aprendizaje** - API más compleja que REST simple
- **Requiere conexión activa** - TWS debe estar corriendo

#### Implementación:
```python
from ib_insync import IB, util

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)  # TWS debe estar corriendo

# Definir contrato
contract = Future('ES', '202503', 'CME')  # SPX futures

# Descargar datos históricos
bars = ib.reqHistoricalData(
    contract,
    endDateTime='',
    durationStr='2 Y',  # 2 años
    barSizeSetting='5 mins',
    whatToShow='TRADES',
    useRTH=True
)

# Convertir a DataFrame
df = util.df(bars)
```

**ROI**: GRATIS pero requiere tiempo de setup (1-2 días). Vale la pena 100%.

---

### 🟡 OPCIÓN 3: Alpha Vantage (Gratis con límites)

**Website**: https://www.alphavantage.co/
**Tipo**: API gratuita de datos financieros
**Cobertura**: Global, pero limitada para intraday

#### Pricing:
- **Free**: 25 API calls/día, 5 calls/minuto
- **$50/mes**: 500 calls/día
- **$250/mes**: 3000 calls/día

#### ✅ PROS:
- **Gratis** - 25 calls/día suficiente para ir bajando poco a poco
- **Intraday data** - Tiene intervalos de 5 minutos
- **Global coverage** - Stocks, indices, forex

#### ❌ CONTRAS:
- **Limitación CRÍTICA**: Solo 1-3 meses de intraday data 😢
- **Rate limits severos** - 5 calls/min en plan gratis
- **No es para box strategy** - No tiene suficiente histórico

**Veredicto**: ❌ No sirve para tu caso (solo 1-3 meses)

---

### 🟡 OPCIÓN 4: FirstRate Data (Pago único)

**Website**: https://firstratedata.com/
**Tipo**: Descarga de datos históricos (archivos CSV)
**Cobertura**: Futures principalmente

#### Pricing:
- **Pago único** por dataset
- ES (SPX) 5-min data, 10 años: ~$200-500 (pago único)
- No hay subscripción mensual

#### ✅ PROS:
- **Pago único** - No subscripciones
- **Datos limpios** - Pre-procesados, calidad alta
- **CSV files** - Fácil de integrar
- **Histórico largo** - 10-20 años disponibles

#### ❌ CONTRAS:
- **Costo inicial alto** - $200-500 por mercado
- **No real-time** - Solo histórico
- **Actualización manual** - Tienes que comprar updates
- **Solo futures** - No índices directos

**Veredicto**: ⚠️ Bueno si solo quieres US markets (ES, NQ, RTY) y no necesitas updates frecuentes

---

### 🟡 OPCIÓN 5: Databento (Profesional)

**Website**: https://databento.com/
**Tipo**: Proveedor institucional de datos
**Cobertura**: Exchange-level data

#### Pricing:
- **On-demand**: Pagas por GB descargado
- Aprox $0.30-$1.00 por GB de datos históricos
- 2 años de ES 5-min ≈ 5-10 GB ≈ $5-10

#### ✅ PROS:
- **Muy barato** para históricos
- **Calidad institucional** - Tick-level data disponible
- **Flexible** - Solo pagas lo que usas
- **API moderna** - Python client excelente

#### ❌ CONTRAS:
- **Complejidad** - Más orientado a institucionales
- **Solo US markets** - No Europa/Asia
- **Curva de aprendizaje** - Documentación técnica

---

### 🔴 OPCIÓN 6: yfinance con "trucos" (NO RECOMENDADO)

**Idea**: Descargar día por día, ventanas de 60 días hacia atrás

#### Implementación:
```python
# Intentar engañar el límite de 60 días
all_data = []
for i in range(24):  # 24 meses
    end_date = datetime.now() - timedelta(days=60*i)
    start_date = end_date - timedelta(days=60)

    df = yf.download('ES=F', start=start_date, end=end_date, interval='5m')
    all_data.append(df)

combined = pd.concat(all_data)
```

#### ❌ Por qué NO funciona:
- yfinance tiene límite **hard-coded** de 60 días para 5-min
- Intentar bypassear rompe términos de servicio
- No es confiable
- Datos pueden tener gaps

**Veredicto**: ❌ No lo hagas

---

### 🟢 OPCIÓN 7: Almacenar incremental con yfinance (HACK SIMPLE)

**Idea**: Usar yfinance para ir acumulando datos día a día

#### Estrategia:
```python
# Script que corre DIARIAMENTE (cron job)
# Descarga los últimos 60 días y hace merge con histórico

def update_historical_data():
    # Cargar histórico existente
    historical = load_cached_data()

    # Descargar últimos 60 días con yfinance
    new_data = yf.download('ES=F', period='60d', interval='5m')

    # Merge sin duplicados
    combined = pd.concat([historical, new_data]).drop_duplicates()

    # Guardar
    save_cached_data(combined)

# Ejecutar esto DIARIAMENTE durante 2 años = tendrás 2 años de datos
```

#### ✅ PROS:
- **GRATIS** - Sigue usando yfinance
- **Simple** - No requiere nueva API
- **Funciona** - Si lo corres cada día, acumulas datos

#### ❌ CONTRAS:
- **Toma tiempo** - Necesitas 2 años reales para tener 2 años de datos
- **No retroactivo** - No puedes obtener datos pasados
- **Mantenimiento** - Script debe correr daily sin fallas

**Veredicto**: ⚠️ Buena solución FUTURA, pero no resuelve el problema AHORA

---

## 🎯 Mi Recomendación por Orden

### Para AHORA (necesitas datos YA):

**1. Interactive Brokers (GRATIS)** ⭐⭐⭐⭐⭐
- Cuenta gratis
- Datos de todos los mercados
- Calidad institucional
- Setup: 1-2 días

**2. Polygon.io ($29/mes)** ⭐⭐⭐⭐⭐
- Solo US markets (SPX, NDX, RUT)
- API súper fácil
- Datos en minutos
- Setup: 1 hora

**Si tienes presupuesto**: Polygon.io + IB
- Polygon para US (rápido y fácil)
- IB para Europa/Asia (gratis pero complejo)

---

### Para LARGO PLAZO:

**Sistema híbrido:**
```python
# Para datos históricos (2+ años atrás):
if market in ['SPX', 'NDX', 'RUT']:
    source = 'polygon'  # $29/mes
else:
    source = 'interactive_brokers'  # gratis

# Para datos recientes (<60 días):
source = 'yfinance'  # gratis, rápido

# Para acumulación futura:
daily_cron_job = store_yfinance_data()  # Ir acumulando
```

---

## 📊 Comparativa Rápida

| API | Costo/mes | Histórico | Setup | US Markets | Global | Calidad |
|-----|-----------|-----------|-------|------------|--------|---------|
| **yfinance** | $0 | 60 días | 0 min | ✅ | ✅ | 🟡 |
| **Polygon.io** | $29 | 2 años | 1 hora | ✅ | ❌ | ⭐⭐⭐⭐⭐ |
| **Interactive Brokers** | $0* | Ilimitado | 1-2 días | ✅ | ✅ | ⭐⭐⭐⭐⭐ |
| **Alpha Vantage** | $0 | 1-3 meses | 30 min | ✅ | ✅ | 🟡 |
| **FirstRate Data** | $200-500 único | 10+ años | 0 min | ✅ | ❌ | ⭐⭐⭐⭐ |
| **Databento** | ~$10 único | 2 años | 1 hora | ✅ | ❌ | ⭐⭐⭐⭐⭐ |

*Requiere cuenta, pero sin fondos mínimos

---

## 🚀 Plan de Acción Recomendado

### Opción A - GRATIS (2-3 días setup):
```
Día 1-2: Setup Interactive Brokers
  - Abrir cuenta (gratis, online)
  - Instalar TWS (Trader Workstation)
  - Configurar API
  - Implementar data_loader_ib.py

Día 3: Descargar 2 años de datos
  - 11 mercados × 2 años
  - ~5-6 horas de descarga (rate limits)
  - Cachear en archivos pickle

Día 4+: Re-entrenar modelo
```

### Opción B - RÁPIDO ($29/mes):
```
Hoy:
  - Registrarse en Polygon.io ($29/mes)
  - API key en 5 minutos
  - Implementar data_loader_polygon.py (1 hora)
  - Descargar SPX, NDX, RUT (30 minutos)

Mañana:
  - Usar IB para mercados europeos/asiáticos (gratis)
  - O simplemente enfocarte solo en US markets por ahora
```

### Opción C - HÍBRIDO (LO MEJOR):
```
Semana 1:
  - Polygon.io para US markets ($29/mes) - setup rápido
  - Re-entrenar modelo con SPX/NDX/RUT
  - Ver mejora inmediata

Semana 2:
  - Setup Interactive Brokers (gratis)
  - Descargar mercados europeos/asiáticos
  - Cancelar Polygon si quieres (ya tienes datos)
```

---

## 💻 Código de Ejemplo - Polygon.io

```python
# data_loader_polygon.py

import os
from polygon import RESTClient
import pandas as pd
from datetime import datetime, timedelta

class PolygonDataLoader:
    def __init__(self):
        self.client = RESTClient(api_key=os.getenv("POLYGON_API_KEY"))

        # Mapping de nuestros códigos a Polygon tickers
        self.ticker_map = {
            'SPX': 'I:SPX',    # S&P 500 Index
            'NDX': 'I:NDX',    # NASDAQ 100 Index
            'RUT': 'I:RUT'     # Russell 2000 Index
        }

    def download_historical(self, market, years=2):
        """
        Descarga datos históricos de 5 minutos

        Args:
            market: 'SPX', 'NDX', 'RUT'
            years: Años hacia atrás

        Returns:
            DataFrame con OHLCV
        """
        ticker = self.ticker_map.get(market)
        if not ticker:
            raise ValueError(f"Market {market} not supported in Polygon")

        # Fechas
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * years)

        # Descargar
        print(f"Downloading {market} from {start_date.date()} to {end_date.date()}")

        aggs = []
        for agg in self.client.list_aggs(
            ticker=ticker,
            multiplier=5,
            timespan="minute",
            from_=start_date.strftime("%Y-%m-%d"),
            to=end_date.strftime("%Y-%m-%d"),
            limit=50000  # Max por request
        ):
            aggs.append(agg)

        # Convertir a DataFrame
        df = pd.DataFrame([{
            'Open': a.open,
            'High': a.high,
            'Low': a.low,
            'Close': a.close,
            'Volume': a.volume,
            'Timestamp': pd.Timestamp(a.timestamp, unit='ms', tz='America/New_York')
        } for a in aggs])

        df.set_index('Timestamp', inplace=True)
        df.sort_index(inplace=True)

        print(f"Downloaded {len(df)} candles for {market}")

        return df

# Uso:
loader = PolygonDataLoader()
spx_2years = loader.download_historical('SPX', years=2)
```

---

## ❓ ¿Qué te recomiendo hacer?

**Mi sugerencia personal:**

1. **Esta semana**: Polygon.io ($29/mes)
   - Setup en 1 hora
   - Datos de SPX, NDX, RUT en 30 minutos
   - Re-entrenar modelo este fin de semana
   - Ver resultados inmediatos

2. **Próxima semana**: Interactive Brokers (gratis)
   - Mientras tanto, crear cuenta IB
   - Setup TWS
   - Descargar mercados europeos/asiáticos
   - Después cancelar Polygon si quieres (ya tienes datos descargados)

3. **Going forward**: yfinance diario + cache
   - Script que corre daily
   - Acumula datos nuevos
   - En 6 meses tendrás 6 meses adicionales, etc.

**Costo total**: $29/mes por 1-2 meses = $58 total para resolver el problema para siempre.

¿Quieres que implemente el data loader de Polygon o prefieres ir directo a Interactive Brokers (gratis pero más complejo)?
