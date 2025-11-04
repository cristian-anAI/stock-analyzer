# Autotrader Correlation Filter - Idea Estratégica

## 🎯 Concepto Principal

**IDEA CORE**: El autotrader NO debe ejecutar compras LONG en stocks si ese día la caja de SHORT está activa en el índice correlacionado.

### Razonamiento
Si el índice (SPX, NDX, RUT) rompe SHORT (a la baja), es muy probable que:
- Los stocks individuales del índice también bajen
- Comprar LONG en ese contexto es contra-tendencia
- Mejor esperar a que el índice se recupere

---

## 📊 Estado Actual

### Lo que ya tenemos:
1. ✅ **Box Strategy funcionando** - Detecta breakouts LONG/SHORT en índices
2. ✅ **Análisis de correlación** - SPX-NDX: 97.2%, SPX-RUT: 87.8%
3. ✅ **Confluence detection** - Sistema que detecta cuando múltiples mercados correlacionados rompen simultáneamente
4. ✅ **Market data en tiempo real** - Box strategy monitorea 10 mercados globales

### Lo que falta:
1. ❌ **Integración con Autotrader** - El autotrader no consulta el estado de las cajas
2. ❌ **Filtro de correlación** - No hay lógica que bloquee compras cuando índice está SHORT
3. ❌ **Sistema de scores ajustados** - No ajustamos scores según contexto del índice

---

## 🧠 Evolución de la Idea - ML y Herramientas Avanzadas

### 1. **Filtro Básico (Fase 1)** ⭐⭐⭐⭐⭐
**Implementación inmediata cuando se corrijan bugs de caja**

```python
def should_buy_stock(stock_symbol, stock_score):
    """
    Decide si comprar un stock basado en estado de cajas correlacionadas
    """
    # 1. Identificar índice correlacionado del stock
    stock_index = get_correlated_index(stock_symbol)  # NVDA -> NDX, AAPL -> SPX, etc.

    # 2. Consultar estado de la caja del índice
    box_status = get_box_status(stock_index)  # LONG, SHORT, NEUTRAL

    # 3. Filtro básico
    if box_status == 'SHORT':
        logger.info(f"❌ Bloqueando {stock_symbol}: Índice {stock_index} en caja SHORT")
        return False

    # 4. Si índice está LONG, permitir compra
    if box_status == 'LONG' and stock_score >= BUY_THRESHOLD:
        logger.info(f"✅ Permitiendo {stock_symbol}: Índice {stock_index} en caja LONG")
        return True

    # 5. Si índice está NEUTRAL, usar solo el score
    return stock_score >= BUY_THRESHOLD
```

**Ventajas**:
- Simple de implementar
- Efectivo inmediatamente
- Reduce drawdowns en días de mercado bajista

---

### 2. **Ajuste Dinámico de Scores (Fase 2)** ⭐⭐⭐⭐

En lugar de bloquear completamente, ajustar los scores según contexto:

```python
def adjust_score_by_market_context(stock_symbol, base_score):
    """
    Ajusta el score del stock según estado del mercado
    """
    stock_index = get_correlated_index(stock_symbol)
    box_status = get_box_status(stock_index)

    if box_status == 'SHORT':
        # Penalizar fuertemente
        adjusted_score = base_score * 0.5  # Reduce score a la mitad
        logger.info(f"Score {stock_symbol}: {base_score} -> {adjusted_score} (índice SHORT)")

    elif box_status == 'LONG':
        # Bonus por momentum del índice
        adjusted_score = base_score * 1.2  # Boost del 20%
        logger.info(f"Score {stock_symbol}: {base_score} -> {adjusted_score} (índice LONG)")

    else:
        adjusted_score = base_score

    return adjusted_score
```

**Ventajas**:
- Más flexible que bloqueo total
- Permite excepciones (stocks muy fuertes pueden superar penalización)
- Mejor gestión de riesgo gradual

---

### 3. **Sistema ML de Predicción de Divergencia (Fase 3)** ⭐⭐⭐⭐⭐

**Idea avanzada**: No todos los stocks siguen al índice siempre. Algunos divergen.

**Objetivo ML**: Predecir si un stock va a diverger del índice en las próximas horas.

#### Features para el modelo:

```python
features = {
    # Contexto del índice
    'index_box_status': 'SHORT',  # LONG, SHORT, NEUTRAL
    'index_breakout_time': '10:00',  # Hora del breakout
    'index_strength': 0.85,  # Fuerza del breakout (0-1)
    'index_volume_ratio': 1.5,  # Volumen vs promedio

    # Correlación histórica stock-índice
    'stock_index_correlation_30d': 0.92,  # Correlación últimos 30 días
    'stock_index_correlation_7d': 0.88,   # Correlación últimos 7 días
    'stock_index_correlation_today': 0.95, # Correlación intraday

    # Divergencia histórica
    'divergence_count_30d': 3,  # Veces que divergió en 30 días
    'avg_divergence_profit': 0.02,  # P&L promedio cuando diverge
    'max_divergence_duration': 120,  # Minutos promedio de divergencia

    # Características del stock
    'stock_score': 7.5,
    'stock_relative_strength': 1.3,  # RSI del stock vs RSI del índice
    'stock_volume_spike': 2.0,  # Volumen anormal (2x promedio)
    'stock_sector': 'Technology',
    'stock_market_cap': 'Large',

    # Timing
    'time_since_index_breakout': 30,  # Minutos desde breakout del índice
    'time_of_day': '10:30',
    'is_opening_30min': False,

    # Contexto de mercado
    'vix_level': 18.5,
    'market_breadth': 0.45,  # % stocks avanzando
    'sector_rotation': True,  # Rotación sectorial activa
}

# Label: ¿El stock divergió y fue rentable?
label = 'PROFITABLE_DIVERGENCE'  # vs 'FOLLOWED_INDEX', 'LOSS'
```

#### Modelo propuesto:

```python
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from xgboost import XGBClassifier

# Ensemble de 3 modelos
models = {
    'random_forest': RandomForestClassifier(n_estimators=200, max_depth=10),
    'gradient_boosting': GradientBoostingClassifier(n_estimators=150),
    'xgboost': XGBClassifier(n_estimators=200, learning_rate=0.05)
}

# Predicción
predictions = []
for model in models.values():
    pred_proba = model.predict_proba(features)
    predictions.append(pred_proba)

# Voting ensemble
final_probability = np.mean(predictions, axis=0)

# Decisión
if index_box_status == 'SHORT':
    if final_probability['PROFITABLE_DIVERGENCE'] > 0.70:
        # Alta probabilidad de divergencia rentable
        decision = 'BUY_DESPITE_INDEX'
    elif final_probability['FOLLOWED_INDEX'] > 0.60:
        # Probablemente siga al índice a la baja
        decision = 'BLOCK_BUY'
    else:
        # Incierto
        decision = 'WAIT'
```

**Ventajas**:
- Captura excepciones (stocks que divergen rentablemente)
- Aprende patrones complejos de divergencia
- Mejora con el tiempo conforme acumula datos

---

### 4. **Análisis de Sectores y Rotación (Fase 4)** ⭐⭐⭐⭐

No todos los sectores reaccionan igual cuando el índice cae.

**Idea**: Identificar qué sectores tienden a ser defensivos o agresivos.

```python
# Clasificación de sectores
sector_behavior = {
    'Technology': {
        'correlation_to_ndx': 0.95,
        'divergence_frequency': 'Low',
        'beta': 1.2,  # Más volátil que el mercado
        'safe_on_index_short': False  # NO comprar Tech si NDX SHORT
    },
    'Consumer Staples': {
        'correlation_to_spx': 0.65,
        'divergence_frequency': 'High',
        'beta': 0.6,  # Menos volátil
        'safe_on_index_short': True  # OK comprar si SPX SHORT
    },
    'Healthcare': {
        'correlation_to_spx': 0.70,
        'divergence_frequency': 'Medium',
        'beta': 0.8,
        'safe_on_index_short': True
    },
    'Energy': {
        'correlation_to_spx': 0.50,  # Baja correlación
        'divergence_frequency': 'Very High',
        'beta': 1.5,  # Alta volatilidad
        'safe_on_index_short': True,  # A veces diverge (commodities)
        'check_oil_prices': True  # Factor adicional
    }
}

def sector_adjusted_filter(stock_symbol, stock_sector, index_box_status):
    """
    Filtro ajustado por sector
    """
    if index_box_status == 'SHORT':
        sector_info = sector_behavior.get(stock_sector, {})

        if sector_info.get('safe_on_index_short'):
            # Sectores defensivos - permitir compra
            logger.info(f"✅ {stock_symbol} ({stock_sector}): Sector defensivo, permitido pese a índice SHORT")
            return True
        else:
            # Sectores agresivos - bloquear
            logger.info(f"❌ {stock_symbol} ({stock_sector}): Sector agresivo, bloqueado por índice SHORT")
            return False

    return True
```

**Ventajas**:
- Aprovecha divergencias sectoriales
- Reduce falsos negativos (no bloquea todo cuando índice cae)
- Más sofisticado que filtro simple

---

### 5. **Sistema de Confluencias Multi-Índice (Fase 5)** ⭐⭐⭐⭐⭐

Ya tienes la detección de confluencias. Evolución:

**Idea**: Usar confluencias para ajustar agresividad del autotrader.

```python
confluence_scenarios = {
    'ALL_INDICES_LONG': {
        'description': 'SPX, NDX, RUT todos LONG',
        'confidence': 'Very High',
        'action': 'AGGRESSIVE_BUYING',  # Aumentar tamaño de posiciones
        'position_size_multiplier': 1.5,
        'max_positions': 15  # Permitir más posiciones
    },
    'MIXED_SIGNALS': {
        'description': 'SPX LONG, NDX SHORT, RUT NEUTRAL',
        'confidence': 'Low',
        'action': 'CONSERVATIVE',
        'position_size_multiplier': 0.5,
        'max_positions': 5
    },
    'ALL_INDICES_SHORT': {
        'description': 'SPX, NDX, RUT todos SHORT',
        'confidence': 'Very High',
        'action': 'BLOCK_ALL_BUYS',  # No comprar nada
        'exit_existing_positions': True,  # Salir de posiciones actuales
        'consider_shorts': True  # Considerar abrir SHORTs
    }
}

def get_market_regime():
    """
    Determina el régimen de mercado actual
    """
    spx_box = get_box_status('SPX')
    ndx_box = get_box_status('NDX')
    rut_box = get_box_status('RUT')

    if spx_box == ndx_box == rut_box == 'LONG':
        return 'ALL_INDICES_LONG'
    elif spx_box == ndx_box == rut_box == 'SHORT':
        return 'ALL_INDICES_SHORT'
    else:
        return 'MIXED_SIGNALS'
```

**Ventajas**:
- Gestión de riesgo dinámico
- Aprovecha momentos de alta convicción (todos LONG)
- Protege capital en momentos de alta convicción bajista (todos SHORT)

---

### 6. **Análisis de Timing Intraday (Fase 6)** ⭐⭐⭐

**Observación**: Un breakout SHORT del índice a las 9:30 AM tiene diferente implicación que uno a las 3:00 PM.

```python
def timing_adjusted_decision(index_box_status, breakout_time, current_time):
    """
    Ajusta decisión según timing del breakout
    """
    time_since_breakout = (current_time - breakout_time).total_seconds() / 60  # minutos

    if index_box_status == 'SHORT':
        if breakout_time.hour == 9 and breakout_time.minute <= 35:
            # Breakout SHORT temprano (opening range)
            severity = 'HIGH'  # Todo el día probablemente bajista
            block_duration = 'ALL_DAY'

        elif breakout_time.hour >= 15:
            # Breakout SHORT tarde (power hour)
            severity = 'MEDIUM'  # Puede revertir mañana
            block_duration = 'REST_OF_DAY'

        elif time_since_breakout > 120:  # 2 horas desde breakout
            # Ya pasó tiempo, mercado puede estabilizarse
            severity = 'LOW'
            block_duration = 'EXPIRED'

            # Re-evaluar: ¿se recuperó el índice?
            current_index_price = get_current_price(index)
            if current_index_price > box_breakout_price * 1.005:  # Recuperó 0.5%
                return 'ALLOW_BUY'  # Mercado se recuperó

    return severity, block_duration
```

---

### 7. **Integración con RSI Divergences (Fase 7)** ⭐⭐⭐⭐

Ya mencionaste divergencias RSI. Combinar con box strategy:

```python
def detect_bullish_divergence_on_index_short(stock_symbol, index):
    """
    Si índice está SHORT pero stock muestra divergencia alcista RSI
    """
    index_rsi = calculate_rsi(index, period=14)
    stock_rsi = calculate_rsi(stock_symbol, period=14)

    # Índice en caja SHORT (bajista)
    if get_box_status(index) == 'SHORT':

        # Pero stock muestra divergencia alcista
        if detect_bullish_rsi_divergence(stock_symbol):
            logger.info(f"🔍 {stock_symbol}: Divergencia alcista RSI pese a índice SHORT")

            # Stock muestra fortaleza relativa
            if stock_rsi > index_rsi + 10:  # RSI del stock 10 puntos mayor
                logger.info(f"✅ Fortaleza relativa: RSI {stock_symbol} = {stock_rsi}, RSI {index} = {index_rsi}")
                return 'ALLOW_BUY_DIVERGENCE'

    return 'NO_DIVERGENCE'
```

---

### 8. **Backtesting del Sistema Completo (Fase 8)** ⭐⭐⭐⭐⭐

**CRÍTICO**: Antes de activar en producción, backtest completo.

```python
class CorrelationFilterBacktest:
    """
    Backtesting del sistema de filtro de correlación
    """

    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date
        self.trades = []

    def simulate(self):
        """
        Simula trading con y sin filtro de correlación
        """
        results = {
            'with_filter': {
                'total_trades': 0,
                'winning_trades': 0,
                'total_pnl': 0,
                'max_drawdown': 0,
                'trades_blocked_by_filter': 0
            },
            'without_filter': {
                'total_trades': 0,
                'winning_trades': 0,
                'total_pnl': 0,
                'max_drawdown': 0
            }
        }

        for date in daterange(self.start_date, self.end_date):
            # Obtener estado de cajas ese día
            box_statuses = get_historical_box_status(date)

            # Obtener stocks con score alto ese día
            candidate_stocks = get_high_score_stocks(date)

            for stock in candidate_stocks:
                # Scenario 1: CON filtro
                if self.should_trade_with_filter(stock, box_statuses):
                    trade_result = execute_virtual_trade(stock, date)
                    results['with_filter']['total_trades'] += 1
                    results['with_filter']['total_pnl'] += trade_result['pnl']
                    if trade_result['pnl'] > 0:
                        results['with_filter']['winning_trades'] += 1
                else:
                    results['with_filter']['trades_blocked_by_filter'] += 1

                # Scenario 2: SIN filtro (sistema actual)
                trade_result = execute_virtual_trade(stock, date)
                results['without_filter']['total_trades'] += 1
                results['without_filter']['total_pnl'] += trade_result['pnl']
                if trade_result['pnl'] > 0:
                    results['without_filter']['winning_trades'] += 1

        # Comparar resultados
        self.compare_results(results)

        return results
```

**Métricas a comparar**:
- Win rate: ¿Mejora con el filtro?
- P&L total: ¿Mayor profit?
- Max drawdown: ¿Menor drawdown?
- Sharpe ratio: ¿Mejor risk-adjusted return?
- Trades evitados: ¿Cuántos trades malos se bloquearon?

---

## 🛠️ Herramientas y Tecnologías Adicionales

### 1. **Real-time Websockets**
Para recibir estado de cajas en tiempo real sin polling:

```python
# Box Strategy WebSocket feed
ws_feed = BoxStrategyWebSocket()
ws_feed.on_box_breakout = handle_box_breakout

def handle_box_breakout(market, direction, timestamp):
    if direction == 'SHORT':
        autotrader.block_buys_for_correlated_stocks(market)
```

### 2. **Redis Cache**
Para compartir estado de cajas entre autotrader y box strategy:

```python
import redis
r = redis.Redis()

# Box strategy escribe
r.set('SPX_box_status', 'SHORT')
r.set('SPX_box_breakout_time', '2025-10-30T09:30:00')

# Autotrader lee
spx_status = r.get('SPX_box_status')
```

### 3. **Grafana Dashboard**
Visualizar en tiempo real:
- Estado de cajas de todos los índices
- Trades bloqueados vs permitidos
- Correlación actual stock-índice
- P&L con vs sin filtro

### 4. **Alertas Telegram/Email**
```python
if index_box_status == 'SHORT' and trades_blocked > 0:
    send_telegram_alert(
        f"⚠️ Autotrader: {trades_blocked} compras bloqueadas por {index} en caja SHORT"
    )
```

---

## 📋 Plan de Implementación (CUANDO CAJA ESTÉ LISTA)

### Fase 1: MVP (1-2 días)
- [ ] Crear función `get_box_status(market)` en box_strategy_service
- [ ] Crear función `get_correlated_index(stock_symbol)`
- [ ] Implementar filtro básico en autotrader
- [ ] Test manual con datos históricos

### Fase 2: Ajustes Dinámicos (2-3 días)
- [ ] Implementar ajuste de scores por contexto
- [ ] Agregar lógica de timing (cuánto tiempo desde breakout)
- [ ] Test en paper trading

### Fase 3: ML Divergencia (1-2 semanas)
- [ ] Recolectar datos históricos de divergencias
- [ ] Entrenar modelo de divergencia
- [ ] Integrar predicciones en autotrader
- [ ] Backtest extensivo

### Fase 4: Sectores (3-5 días)
- [ ] Clasificar stocks por sector
- [ ] Implementar lógica sector-aware
- [ ] Ajustar filters por sector

### Fase 5: Confluencias (2-3 días)
- [ ] Implementar detección de régimen de mercado
- [ ] Ajustar tamaño de posiciones según régimen
- [ ] Sistema de alertas

### Fase 6: Producción (1 semana)
- [ ] Backtesting completo (6-12 meses)
- [ ] Paper trading (2 semanas)
- [ ] Deploy gradual (10% capital, luego 50%, luego 100%)

---

## 🔴 BUGS PENDIENTES EN BOX STRATEGY

**ANTES DE IMPLEMENTAR ESTO, ARREGLAR**:

1. [ ] Premature breakouts (cajas rompiendo durante formación)
2. [ ] Timezone issues (discrepancias de hora)
3. [ ] Data quality (verificar gaps en datos de 5 min)
4. [ ] ML model overfitting (solo 60 días de datos)

---

## 💡 Resumen de la Idea Original

**Core Concept**:
> Si el índice (SPX/NDX/RUT) está en caja SHORT → NO comprar stocks LONG del mismo índice

**Evolución**:
1. Filtro básico de bloqueo
2. Ajuste dinámico de scores
3. ML para predecir divergencias
4. Análisis sectorial
5. Confluencias multi-índice
6. Timing intraday
7. RSI divergencias
8. Backtesting completo

**Implementar cuando box strategy esté estable y sin bugs.**

---

## 📌 RECORDATORIO PARA CONVERSACIONES FUTURAS

**TAREA PENDIENTE**: Implementar sistema de filtro de correlación índice-stock en autotrader

**STATUS**: ⏸️ EN PAUSA - Esperando corrección de bugs en box strategy

**PRÓXIMO PASO**: Una vez box strategy esté estable, empezar por Fase 1 (MVP)

**PRIORIDAD**: ⭐⭐⭐⭐⭐ (Crítico para mejorar win rate del autotrader)

---

**Última actualización**: 2025-10-30
**Documento creado por**: Conversación sobre evolución del autotrader
**Próxima revisión**: Cuando box strategy esté corregida
