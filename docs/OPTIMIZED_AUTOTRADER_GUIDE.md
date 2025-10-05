# Optimized Autotrader & Decision Transparency System

## 🚀 What's New

### 1. **Optimized Trading Strategy** (Backtest Proven: 18.79% CAGR)
Based on 1-year backtest results (Oct 2023 - Oct 2024):
- **Total Return**: 18.79% vs 0.48% original
- **Sharpe Ratio**: 2.43 (professional-grade) vs -1.19 original
- **Alpha vs S&P 500**: +8.36%
- **Monthly Win Rate**: 83.33% (10/12 months positive)

### 2. **Complete Decision Transparency**
Every buy/sell decision is now logged with full context:
- Why did we buy or NOT buy?
- Which filters passed and which failed?
- Complete scoring breakdown
- Trailing stop updates
- Exit reasons

---

## 📊 Key Improvements

### Improved Scoring System
**File**: `src/api/services/improved_scoring_service.py`

New scoring includes:
- **Momentum confirmation** across 5d, 10d, 20d periods
- **EMA crossover** trend strength (20/50 day)
- **Volume confirmation**
- **Volatility penalty**
- **Position in price range**

### Optimized Trading Config
**File**: `src/api/strategies/optimized_trading_config.py`

New parameters:
- `buy_threshold`: 6.0 → **6.5** (more selective)
- `sell_threshold`: 4.5 → **5.5** (less premature exits)
- `min_hold_days`: 3 → **7 days** (capture trends)
- `max_hold_days`: 20 → **30 days**
- `trailing_stop`: **5%** (NEW - protect profits)
- `cooldown_days`: **7 days** (NEW - prevent overtrading)

### Trailing Stops
**How it works**:
1. Track highest price since entry
2. Set trailing stop 5% below highest price
3. Automatically sell if price drops below trailing stop
4. Locks in profits while letting winners run

**Example**:
- Buy at $100
- Price rises to $120 → trailing stop moves to $114 (5% below)
- Price rises to $130 → trailing stop moves to $123.50
- If price drops to $123 → SELL (trailing stop hit)

---

## 🔍 Decision Transparency API

### Get Recent Decisions
```bash
GET /api/v1/positions/autotrader/decisions?limit=50&decision_type=no_buy
```

**Response**:
```json
{
  "count": 50,
  "decisions": [
    {
      "symbol": "AAPL",
      "asset_type": "stock",
      "decision_type": "no_buy",
      "action_taken": "none",
      "score": 6.2,
      "current_price": 150.00,
      "filters_passed": {
        "overtrading": true,
        "volatility": true,
        "score_threshold": false
      },
      "filters_failed": {
        "score_threshold": "Score 6.2 < 6.5"
      },
      "scoring_breakdown": {
        "improved_score": 6.2,
        "method": "ImprovedScoringService",
        "momentum_5d": "+2.3%",
        "momentum_10d": "+4.5%",
        "ema_crossover": "bullish"
      },
      "buy_threshold": 6.5,
      "confidence": 70.0,
      "timestamp": "2025-10-03T10:30:00"
    }
  ]
}
```

### Get Decisions by Symbol
```bash
GET /api/v1/positions/autotrader/decisions/symbol/AAPL?limit=20
```

Shows complete history of why AAPL was bought, sold, or not traded.

### Get Decisions by Trading Cycle
```bash
GET /api/v1/positions/autotrader/decisions/cycle/{cycle_id}
```

Shows all decisions from a specific trading cycle.

### Get Decision Statistics
```bash
GET /api/v1/positions/autotrader/decisions/stats?hours=24
```

Aggregated stats:
- Buy signals vs no-buy decisions
- Sell signals vs hold decisions
- Average scores

---

## 🎯 Using the Optimized Autotrader

### Enable Optimized Strategy

By default, the autotrader now uses the optimized config:

```python
# src/api/services/autotrader_service.py
autotrader = AutotraderService(use_optimized_config=True)  # Default
```

To use legacy config:
```python
autotrader = AutotraderService(use_optimized_config=False)
```

### Configuration Options

```python
from src.api.strategies.optimized_trading_config import OptimizedTradingConfig

# Optimized (default)
config = OptimizedTradingConfig.get_optimized_config()

# Conservative (lower risk)
config = OptimizedTradingConfig.get_conservative_config()
# - buy_threshold: 7.0 (very selective)
# - trailing_stop: 4.0% (tighter stop)
# - cooldown: 10 days

# Aggressive (testing only)
config = OptimizedTradingConfig.get_aggressive_config()
# - buy_threshold: 6.0
# - trailing_stop: 6.0% (wider stop)
# - cooldown: 3 days
```

---

## 📈 Understanding Decision Logs

### Buy Decision Fields

| Field | Description |
|-------|-------------|
| `symbol` | Stock/crypto symbol |
| `score` | Current improved score |
| `current_price` | Current asset price |
| `filters_passed` | Dict of filters that passed |
| `filters_failed` | Dict of filters that failed (with reasons) |
| `scoring_breakdown` | Complete scoring details |
| `buy_threshold` | Buy threshold used (6.5) |
| `confidence` | Confidence level (0-100) |
| `position_size` | Position size if buy executed |

### Sell Decision Fields

| Field | Description |
|-------|-------------|
| `entry_price` | Original buy price |
| `days_held` | Days position was held |
| `pnl_percent` | Current P&L percentage |
| `exit_reason` | Why we sold or are holding |
| `exit_details` | Complete exit analysis |
| `trailing_stop_price` | Current trailing stop price |
| `stop_loss_price` | Stop loss price |
| `take_profit_price` | Take profit target |

### Exit Reasons

1. **"Trailing stop hit"** - Price dropped 5% from peak
2. **"Score dropped to X.X"** - Score fell below 5.5 threshold
3. **"Take profit target hit"** - Gained 15%+
4. **"Stop loss hit"** - Lost 8%+
5. **"Max hold time reached"** - Held for 30 days
6. **"Min hold time not reached"** - Only sells on stop loss before 7 days

---

## 🔧 Troubleshooting

### No Trades Executing?

Check decision logs to see why:
```bash
curl http://localhost:8000/api/v1/positions/autotrader/decisions?decision_type=no_buy
```

Common reasons:
- **Score too low**: Score 6.2 < 6.5 threshold
- **Overtrading prevention**: Recently traded this symbol (7-day cooldown)
- **Portfolio capacity**: Max positions reached or insufficient capital
- **Volatility filter**: Symbol too volatile

### Understanding Why We Didn't Buy High-Score Stocks

Example decision log:
```json
{
  "symbol": "NVDA",
  "score": 7.2,
  "filters_passed": {
    "score_threshold": true,
    "volatility": true
  },
  "filters_failed": {
    "overtrading": "Symbol in 7-day cooldown (sold 3 days ago)"
  }
}
```

**Explanation**: Even though NVDA scored 7.2 (above 6.5 threshold), we recently sold it 3 days ago, so the 7-day cooldown prevents re-entry. This prevents revenge trading.

### Understanding Trailing Stops

Check current trailing stops:
```bash
curl http://localhost:8000/api/v1/positions/autotrader/decisions?decision_type=no_sell
```

Look for `trailing_stop_price` and `highest_price`:
```json
{
  "symbol": "AAPL",
  "entry_price": 100.00,
  "current_price": 125.00,
  "highest_price": 130.00,
  "trailing_stop_price": 123.50,
  "pnl_percent": 25.0,
  "exit_reason": null,
  "exit_details": {
    "trailing_stop_price": 123.50,
    "distance_to_stop": "1.2%"
  }
}
```

**Explanation**:
- Bought at $100
- Peak was $130
- Trailing stop set at $123.50 (5% below $130)
- Current price $125 is still above trailing stop
- If price drops to $123, position will automatically sell

---

## 📊 Dashboard Integration (Coming Soon)

Future frontend dashboard will show:
- Real-time decision stream
- Why each symbol passed/failed filters
- Visual trailing stop indicators
- Score breakdowns with charts
- Historical decision patterns

For now, use the API endpoints directly or check logs.

---

## 🎓 Best Practices

### 1. Monitor Decision Logs Regularly
```bash
# Check recent no-buys to understand missed opportunities
curl http://localhost:8000/api/v1/positions/autotrader/decisions?decision_type=no_buy&limit=20

# Check recent sells to understand exit patterns
curl http://localhost:8000/api/v1/positions/autotrader/decisions?decision_type=sell_signal&limit=20
```

### 2. Review Symbol-Specific Patterns
```bash
# See why AAPL keeps getting rejected
curl http://localhost:8000/api/v1/positions/autotrader/decisions/symbol/AAPL
```

### 3. Track Daily Statistics
```bash
# Get 24-hour decision summary
curl http://localhost:8000/api/v1/positions/autotrader/decisions/stats?hours=24
```

### 4. Analyze Trading Cycles
```bash
# Get all decisions from a specific cycle
curl http://localhost:8000/api/v1/positions/autotrader/decisions/cycle/{cycle_id}
```

---

## 🚨 Important Notes

### Database Migration Required

Before using the new system, run migrations to create the decision_logs table:

```python
from src.api.database.migrations import run_portfolio_migrations
run_portfolio_migrations()
```

Or use the migration script (coming soon).

### Backwards Compatibility

The autotrader is fully backwards compatible:
- Set `use_optimized_config=False` to use legacy strategy
- Decision logging always runs (doesn't affect trading)
- Trailing stops can be disabled in config

### Performance Impact

- Decision logging adds ~10ms per evaluation
- Improved scoring adds ~50-100ms per symbol (fetches historical data)
- Total cycle time increase: ~2-5 seconds for 20 symbols

---

## 📚 Related Files

### Core Implementation
- `src/api/services/improved_scoring_service.py` - New scoring algorithm
- `src/api/services/decision_logger.py` - Decision logging service
- `src/api/services/autotrader_service.py` - Updated autotrader
- `src/api/strategies/optimized_trading_config.py` - Optimized config

### Database
- `src/api/database/migrations.py` - Migration to create decision_logs table

### API
- `src/api/routers/positions.py` - Decision endpoints

### Backtesting
- `tools/backtest/optimized_backtest_engine.py` - Backtest with optimized strategy
- `reports/COMPARACION_ESTRATEGIAS.md` - Backtest comparison results

---

## 🎯 Next Steps

1. ✅ Run database migrations
2. ✅ Start autotrader with optimized config (default)
3. ✅ Monitor decision logs via API
4. ⏳ Build frontend dashboard (optional)
5. ⏳ Run paper trading for validation

---

*Generated: 2025-10-03*
*Version: 1.0 - Optimized Strategy Release*
