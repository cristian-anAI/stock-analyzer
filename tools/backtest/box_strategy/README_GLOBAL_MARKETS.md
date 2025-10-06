# Global Multi-Market Backtesting System - FASE 2

## Overview

Sistema completo de backtesting multi-mercado para la Estrategia de Caja, expandido a 10 mercados globales con análisis comparativo avanzado.

---

## 🌍 Mercados Soportados

### AMERICAS (2 mercados)
- **SPX**: S&P 500 E-mini Futures (ES=F)
- **NDX**: NASDAQ 100 E-mini Futures (NQ=F)

### EUROPE (5 mercados)
- **DAX**: DAX 40 Futures (FDAX=F) - Alemania
- **FTSE**: FTSE 100 Index (^FTSE) - Reino Unido
- **CAC**: CAC 40 Index (^FCHI) - Francia
- **STOXX**: Euro Stoxx 50 (^STOXX50E) - Europa
- **IBEX**: IBEX 35 Index (^IBEX) - España

### ASIA_PACIFIC (3 mercados)
- **NKY**: Nikkei 225 Futures (NKD=F) - Japón
- **HSI**: Hang Seng Index (^HSI) - Hong Kong
- **ASX**: ASX 200 Index (^AXJO) - Australia

---

## 📁 Arquitectura del Sistema

### Nuevos Módulos Creados

#### 1. **market_config.py**
Configuración centralizada de todos los mercados globales:

```python
@dataclass
class MarketConfig:
    code: str                       # Código del mercado
    name: str                       # Nombre completo
    symbol: str                     # Símbolo Yahoo Finance
    timezone: ZoneInfo              # Zona horaria del mercado
    market_open: str                # Hora de apertura
    market_close: str               # Hora de cierre
    box_start_offset_minutes: int   # Minutos antes de apertura para caja
    box_duration_minutes: int       # Duración de formación de caja
    point_value: float              # Valor en $ por punto
    currency: str                   # Moneda del contrato
    tick_size: float                # Movimiento mínimo de precio
    typical_box_range: Tuple        # Rango típico de caja (min, max)
    recommended_slippage: float     # Slippage típico
    avg_daily_volume: str           # Descripción de volumen
    liquidity_rating: int           # Rating de liquidez (1-5)
```

**Características específicas por mercado:**

| Mercado | Timezone | Point Value | Typical Box Range | Liquidity |
|---------|----------|-------------|-------------------|-----------|
| SPX | America/New_York | $50 | 5-40 pts | 5/5 |
| NDX | America/New_York | $20 | 10-100 pts | 5/5 |
| DAX | Europe/Berlin | €25 | 10-80 pts | 5/5 |
| FTSE | Europe/London | £10 | 10-60 pts | 4/5 |
| CAC | Europe/Paris | €10 | 8-50 pts | 4/5 |
| NKY | Asia/Tokyo | ¥5 | 50-300 pts | 4/5 |
| HSI | Asia/Hong_Kong | HK$50 | 50-300 pts | 4/5 |

#### 2. **global_strategy_adapter.py**
Adaptador de estrategia consciente de zonas horarias:

```python
class GlobalBoxStrategy(BoxStrategy):
    """Adapta la estrategia a diferentes mercados y zonas horarias"""

    # Ajusta automáticamente:
    - Horarios de formación de caja según mercado
    - Parámetros de riesgo según volatilidad típica
    - Slippage según liquidez del mercado
    - Tamaños de tick según especificaciones
```

**Adaptaciones automáticas:**
- 🕐 Horarios de caja adaptados a cada mercado
- 💰 Point values correctos para cálculo de P&L
- 📊 Rangos de caja ajustados a volatilidad típica
- 🌍 Manejo completo de zonas horarias

#### 3. **multi_market_backtester.py**
Motor de backtesting paralelo:

```python
class MultiMarketBacktester:
    """Ejecuta backtests en múltiples mercados simultáneamente"""

    # Capacidades:
    run_parallel_backtests()      # Ejecuta N mercados en paralelo
    run_regional_backtests()      # Ejecuta una región completa
    run_all_markets()             # Ejecuta todos los mercados
    create_comparison_table()     # Genera tabla comparativa
    save_comparison()             # Guarda resultados
```

**Características:**
- ⚡ Ejecución paralela (hasta 4 workers simultáneos)
- 🔄 Conversión automática de P&L a USD
- 📊 Generación de tabla comparativa
- 💾 Exportación a CSV y JSON
- 🎯 Identificación de mejores mercados

#### 4. **comparative_analysis.py**
Análisis comparativo avanzado:

```python
class ComparativeAnalyzer:
    """Analiza patrones y correlaciones entre mercados"""

    # Análisis disponibles:
    analyze_by_region()                       # Performance por región
    correlate_characteristics_with_performance()  # Correlaciones
    identify_best_market_profiles()           # Perfiles óptimos
    volatility_analysis()                     # Análisis de volatilidad
    generate_trading_recommendations()        # Recomendaciones
```

**Tipos de análisis:**
1. **Regional**: Compara AMERICAS vs EUROPE vs ASIA_PACIFIC
2. **Correlaciones**: Identifica qué características predicen éxito
3. **Perfiles**: Define características de mercados ganadores
4. **Volatilidad**: Relación entre rango de caja y performance
5. **Recomendaciones**: Genera estrategias basadas en datos

#### 5. **run_global_backtest.py**
CLI para ejecución de backtests globales:

```bash
# Ejecutar todos los mercados
python run_global_backtest.py --all --days 60

# Ejecutar por región
python run_global_backtest.py --region EUROPE --days 30

# Mercados específicos
python run_global_backtest.py --markets SPX NDX DAX --days 45 --workers 3
```

---

## 🚀 Uso del Sistema

### Comando Básico

```bash
python run_global_backtest.py --all --days 60
```

### Opciones Avanzadas

```bash
python run_global_backtest.py \
    --markets SPX NDX DAX FTSE NKY \
    --days 60 \
    --capital 200000 \
    --risk 0.015 \
    --workers 5 \
    --volatility-filter
```

### Parámetros Disponibles

| Parámetro | Descripción | Default |
|-----------|-------------|---------|
| `--all` | Ejecutar todos los mercados | - |
| `--region` | Ejecutar región específica | - |
| `--markets` | Lista de mercados específicos | - |
| `--days` | Días de histórico a testear | 60 |
| `--capital` | Capital inicial en USD | 100000 |
| `--risk` | Riesgo por trade (decimal) | 0.02 |
| `--workers` | Workers paralelos | 4 |
| `--volatility-filter` | Activar filtro de volatilidad | False |
| `--no-analysis` | Saltar análisis comparativo | False |

---

## 📊 Outputs Generados

### 1. Tabla Comparativa CSV
`multi_market_comparison_YYYYMMDD_HHMMSS.csv`

Columnas incluidas:
- Market, Name, Currency
- Trades, Win Rate (%), Profit Factor
- Avg R, Sharpe, Max DD (%)
- Return (%), P&L (USD)
- Liquidity

### 2. Resultados Completos JSON
`multi_market_results_YYYYMMDD_HHMMSS.json`

Incluye:
- Todos los trades de cada mercado
- Métricas completas
- Información de configuración
- Timestamps de ejecución

### 3. Análisis Comparativo
`market_comparison_YYYYMMDD_HHMMSS.csv`
- Métricas extendidas
- Características de mercado
- Tasas de ejecución

`regional_analysis_YYYYMMDD_HHMMSS.csv`
- Performance por región
- Mejores mercados por región
- Promedios regionales

`correlations_YYYYMMDD_HHMMSS.csv`
- Correlaciones entre características y performance
- Interpretación de fuerza de correlación

`recommendations_YYYYMMDD_HHMMSS.json`
- Recomendaciones de trading
- Mejores mercados identificados
- Justificación de cada recomendación

---

## 🔬 Análisis Realizados

### 1. Análisis Regional
Compara performance entre regiones geográficas:
- Promedio de win rate por región
- Profit factor regional
- Sharpe ratio promedio
- Mejor mercado de cada región

### 2. Correlación de Características
Identifica qué factores predicen éxito:
- Liquidez vs Performance
- Rango de caja vs Win Rate
- Tasa de ejecución vs Rentabilidad
- Duración promedio vs Sharpe

### 3. Perfiles de Mercados Exitosos
Características comunes de top performers:
- Liquidity rating óptimo
- Tasa de ejecución ideal
- Rango de caja preferido
- Regiones con mejor performance

### 4. Análisis de Volatilidad
Relación entre volatilidad (box range) y resultados:
- Performance en mercados de baja volatilidad
- Performance en mercados de alta volatilidad
- Punto óptimo de volatilidad

### 5. Recomendaciones Automatizadas
El sistema genera automáticamente:
- Top 3 mercados por Sharpe ratio
- Mejor región para operar
- Mercados con alta eficiencia de ejecución
- "All-around performers" (criterios múltiples)

---

## 🎯 Insights Clave a Obtener

Al ejecutar el análisis multi-mercado, podrás responder:

1. **¿Qué mercado es más rentable?**
   - Ranking por retorno absoluto
   - Ranking por retorno ajustado por riesgo (Sharpe)

2. **¿Qué región tiene mejor performance?**
   - Comparativa AMERICAS vs EUROPE vs ASIA
   - Consistencia regional

3. **¿La liquidez afecta el éxito?**
   - Correlación liquidez - win rate
   - Correlación liquidez - profit factor

4. **¿Qué rango de caja es óptimo?**
   - Performance en cajas pequeñas vs grandes
   - Sweet spot de volatilidad

5. **¿Hay sesgo direccional por mercado?**
   - Win rate LONG vs SHORT por mercado
   - Mercados con mejor performance en shorts

6. **¿Qué características debe tener un mercado ideal?**
   - Perfil del top performer
   - Características comunes de ganadores

---

## 📈 Ejemplo de Salida

```
=== COMPARATIVE MARKET ANALYSIS ===

TOP 5 MARKETS BY SHARPE RATIO:
Market  Name                              Sharpe  Win Rate  Return
------  ------------------------------  --------  --------  ------
NDX     NASDAQ 100 E-mini Futures          3.34     57.89   71.45%
DAX     DAX 40 Futures                     2.15     55.23   45.30%
STOXX   Euro Stoxx 50                      1.87     52.10   38.20%
FTSE    FTSE 100 Index                     1.45     51.00   28.15%
HSI     Hang Seng Index                    1.20     48.50   22.10%

PERFORMANCE BY REGION:
Region         Markets  Avg Win Rate  Avg PF  Avg Sharpe  Best Market
-------------  -------  ------------  ------  ----------  -----------
AMERICAS             2         54.45    2.17        2.76  NDX (71.45%)
EUROPE               5         51.20    1.85        1.65  DAX (45.30%)
ASIA_PACIFIC         3         48.10    1.45        1.05  HSI (22.10%)

KEY CORRELATIONS:
Characteristic    Performance Metric    Correlation  Strength
---------------   -------------------   -----------  --------
liquidity_rating  sharpe_ratio               0.68   Moderate
execution_rate    win_rate                   0.72   Strong
avg_box_range     profit_factor             -0.35   Weak
```

---

## ⚠️ Limitaciones Conocidas

### 1. Datos Históricos
- Yahoo Finance: ~60 días de datos 5-min
- Para períodos más largos, considerar:
  - Interactive Brokers API
  - Polygon.io
  - Alpha Vantage

### 2. Zonas Horarias
- Datos en timezone del mercado
- Crucial verificar alineación de horarios

### 3. Costos de Trading
- Slippage estimado
- No incluye comisiones
- Añadir manualmente según broker

### 4. Conversión de Divisas
- Tasas de cambio aproximadas
- Usar tasas reales para precisión

---

## 🔧 Solución de Problemas

### Error: "No data returned"
**Solución**: Reducir período de días o verificar símbolo

### Error: "Timezone issues"
**Solución**: Actualizar ZoneInfo database (`pip install tzdata`)

### Error: "Empty comparison table"
**Solución**: Verificar que al menos un mercado tenga datos válidos

### Backtesting muy lento
**Solución**: Reducir `--workers` o días de histórico

---

## 📚 Próximos Pasos (Fase 3)

Una vez validados los resultados multi-mercado:

### 1. Feature Engineering
Extraer características predictivas:
- Amplitud de caja
- Volatilidad ATR
- Gap de apertura
- Volumen relativo
- Indicadores de momentum

### 2. Machine Learning
- Modelo de clasificación (RandomForest/XGBoost)
- Predicción de éxito de trade
- Sistema de confidence scoring

### 3. Optimización
- Grid search de parámetros por mercado
- Walk-forward optimization
- Adaptive parameters

---

## 🤝 Contribuciones

Para extender el sistema:

1. **Añadir nuevo mercado**: Actualizar `market_config.py`
2. **Nueva métrica**: Modificar `comparative_analysis.py`
3. **Nuevo análisis**: Extender `ComparativeAnalyzer`

---

## 📞 Soporte

Consultar documentación principal: `README.md`

Para issues específicos de multi-mercado: revisar logs en `/results/`

---

**Sistema desarrollado para análisis profesional de estrategias de trading multi-mercado**
