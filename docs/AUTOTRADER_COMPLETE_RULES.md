# REGLAS COMPLETAS DEL AUTOTRADER PARA BACKTESTING

Esta documentación especifica **EXACTAMENTE** todas las reglas que el autotrader sigue. Para que el backtesting sea preciso, debe implementar **todas** estas reglas.

## 🔧 CONFIGURACIÓN PRINCIPAL

```python
# De trading_config.py - BACKTEST PROVEN CONFIG
buy_score_threshold = 6.0        # Umbral mínimo para comprar
sell_score_threshold = 4.5       # Umbral para vender por score  
max_position_value = 10000.0     # $10K por posición exacto
max_positions_stocks = 10        # Máximo 10 posiciones
stop_loss_percent = 8.0          # Stop loss -8%
take_profit_percent = 15.0       # Take profit +15%
use_database_scores = True       # Usar scores de DB, NO calcular
```

## ⏰ MARKET TIMING (CRÍTICO - FALTA EN BACKTESTING)

```python
# De market_timing_service.py
market_open = 09:30 ET           # NYSE/NASDAQ horarios
market_close = 16:00 ET          # 
buy_restriction_minutes = 15     # NO COMPRAR primeros 15min (9:30-9:45)
sell_restriction_minutes = 60    # NO VENDER primeros 60min (9:30-10:30)

# RULE: No trading on weekends
# RULE: All times in ET timezone with EST/EDT handling
```

## 📊 SWING TRADING STRATEGY EXIT LOGIC (FIXED)

```python
# De swing_trading_strategy.py - should_exit_position()
min_hold_days = 3                # MÍNIMO 3 días hold period
max_hold_days = 20               # Máximo 20 días

# EXIT CRITERIA PRIORITY:
# 1. EMERGENCY: Stop loss (-8%) or Take profit (+15%) - ALWAYS
# 2. HOLD ENFORCEMENT: If days_held < 3 -> NO SELL (ignore score drops)
# 3. TECHNICAL EXITS: After day 3, RSI > 80 or MACD bearish crossover
# 4. SCORE EXITS: After day 7, only if score drops below 3.0 (not 4.5)
```

## 🔄 CICLO DE TRADING (5 MINUTOS)

El autotrader ejecuta **cada 5 minutos** durante horas de mercado:

### 1. VALIDACIONES INICIALES
```python
# market_timing.is_market_open()
if not market_open:
    skip_cycle()

# portfolio risk limits
if risk_limits_exceeded:
    reduce_position_sizes()

# volatility_service check  
if extreme_volatility:
    apply_volatility_adjustments()
```

### 2. ANÁLISIS POSICIONES EXISTENTES
```python
for each position:
    # Call SwingTradingStrategy.should_exit_position()
    should_exit, reason = strategy.should_exit_position(
        symbol=position.symbol,
        entry_price=position.entry_price, 
        current_price=current_price,
        days_held=calculate_days_held(position.entry_date),
        position_side="LONG",
        data=timeframe_data
    )
    
    if should_exit:
        # SELL validation
        sell_allowed, sell_reason = market_timing.is_trading_allowed("SELL")
        if sell_allowed:
            execute_sell(position, reason)
```

### 3. BÚSQUEDA NUEVAS OPORTUNIDADES  
```python
# Filter by score
candidates = [stock for stock in all_stocks if stock.score >= 6.0]

for candidate in candidates:
    # Market timing validation
    buy_allowed, buy_reason = market_timing.is_trading_allowed("BUY")
    if not buy_allowed:
        continue
        
    # Overtrading prevention
    if already_traded_today(candidate.symbol):
        continue
        
    # Position limits
    if len(positions) >= 10:
        continue
        
    # Generate signal
    signal = swing_strategy.generate_signal(
        symbol=candidate.symbol,
        current_price=candidate.current_price,
        data=timeframe_data
    )
    
    if signal.action == "BUY":
        execute_buy(candidate, signal.reason)
```

## 🚫 OVERTRADING PREVENTION

```python
# De overtrading_prevention_service.py
daily_trade_limits = {
    "total_trades": 8,           # Max 8 trades per day total
    "same_symbol": 1             # Max 1 trade per symbol per day
}

# RULE: Block trading if limits exceeded
# RULE: Reset counters at market open each day
```

## 📈 SIGNAL GENERATION (SwingTradingStrategy)

```python
# De swing_trading_strategy.py - generate_signal()
def generate_signal(symbol, current_price, data):
    # 1. Get database score (NOT calculate)
    score = get_database_score(symbol)  # From stocks/cryptos table
    
    # 2. Score-based decision
    if score >= 6.0:
        action = "BUY"
        confidence = score
    elif score <= 4.5:
        action = "SELL"  # Only for existing positions
        confidence = 10 - score
    else:
        action = "HOLD"
        confidence = 5.0
    
    # 3. Technical confirmation (optional enhancement)
    # RSI, MACD, volume analysis
    
    return TradingSignal(
        action=action,
        score=score,
        confidence=confidence,
        suggested_position_size=10000.0,  # Fixed $10K
        stop_loss=current_price * 0.92,   # -8%
        take_profit=current_price * 1.15, # +15%
        risk_level="MEDIUM"
    )
```

## 💰 POSITION SIZING

```python
# EXACT position sizing rules
position_value = 10000.0  # Exactly $10K per position
quantity = position_value / current_price

# RULE: Always $10K, adjust quantity
# RULE: No fractional shares handling needed (autotrader uses fractional)
```

## ❌ GAPS CRÍTICOS EN BACKTESTING ACTUAL

### 1. Market Timing NO IMPLEMENTADO
- Backtesting compra/vende cualquier hora
- **DEBE**: Respetar 15min BUY restriction después apertura
- **DEBE**: Respetar 60min SELL restriction después apertura

### 2. Exit Logic INCORRECTO
- Backtesting usa thresholds simples (score <= 4.5)
- **DEBE**: Usar SwingTradingStrategy.should_exit_position()
- **DEBE**: Enforce 3-day minimum hold period

### 3. Ciclo INCORRECTO
- Backtesting evalúa una vez por día
- **DEBE**: Evaluar cada 5 minutos durante market hours
- **DEBE**: Check exit criteria every cycle

### 4. Scores INCORRECTOS
- Backtesting calcula scores propios
- **DEBE**: Usar database scores (get_database_score)

### 5. Overtrading NO IMPLEMENTADO
- Backtesting no previene múltiples trades
- **DEBE**: Implementar daily trade limits

## 📋 CHECKLIST PARA BACKTESTING CORRECTO

### ✅ Implementado
- [x] Buy/sell thresholds (6.0/4.5)
- [x] Position sizing ($10K)
- [x] Stop loss/take profit (8%/15%)

### ❌ FALTA IMPLEMENTAR
- [ ] Market timing restrictions (15min/60min)
- [ ] 3-day minimum hold period
- [ ] Score-based exits every 5 minutos
- [ ] Database score usage
- [ ] Overtrading prevention
- [ ] SwingTradingStrategy exit logic
- [ ] Weekend/holiday restrictions

## 🔧 IMPLEMENTACIÓN SUGERIDA

### 1. INMEDIATO
1. Verificar que el backend actualizado esté ejecutando
2. Confirmar que nuevas posiciones respetan 3-day hold
3. Monitor logs para "SWING HOLD" messages

### 2. PARA BACKTESTING PRECISO
1. Implementar market_timing en backtesting
2. Usar SwingTradingStrategy.should_exit_position()
3. Simular ciclos de 5 minutos
4. Usar database scores en lugar de cálculos
5. Implementar overtrading prevention
6. Add timezone handling (EST/EDT)

## 📊 EJEMPLO DE CORRECCIÓN

### ANTES (Backtesting incorrecto)
```python
# Daily check
if stock.score <= 4.5:  # Score drop -> sell immediately
    sell(stock)
```

### DESPUÉS (Como autotrader real)
```python
# Every 5 minutes during market hours
if market_timing.is_trading_allowed("SELL"):
    should_exit, reason = swing_strategy.should_exit_position(
        stock.symbol, entry_price, current_price, days_held, "LONG", data
    )
    if should_exit:
        sell(stock, reason)
    # else: HOLD even if score dropped (minimum hold period)
```

Esta documentación garantiza que el backtesting sea **idéntico** al comportamiento real del autotrader.