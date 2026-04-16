# CLAUDE.md

## Project Overview

Crypto Scalper ("Pupupu") is a high-frequency scalping system for BTC/USDT and altcoins on 1-minute and 5-minute timeframes. It detects EMA crossovers near pivot levels, filtered by VWAP bias and Volume Profile context.

**Origin**: Extracted from `stock-analyzer` repo, branch `feature/ca/caja`. This is a standalone project focused exclusively on short-timeframe crypto scalping.

## Architecture

```
crypto-scalper/
├── src/
│   ├── indicators/       # Technical indicators (EMA, Pivots, VP, VWAP)
│   ├── strategy/         # Signal generation (PupupuV2: 5m, PupupuV3: 1m)
│   ├── filters/          # Trade filters (market context)
│   ├── risk/             # Position sizing and risk management
│   ├── core/             # Trade lifecycle manager (PENDING→ACTIVE→TP1→RUNNER)
│   ├── data/             # Database and data access
│   └── api/              # Telegram alerts, decision logger
├── backtest/             # Backtesting engines and metrics
├── config/               # Strategy configuration (default.py)
├── tools/                # Analysis and debugging utilities
├── reference/            # TradingView Pine Script (reference implementation)
└── docs/                 # Documentation
```

## Strategy Logic

### PupupuV3 (Primary - 1 minute)
1. **Pivot Detection**: Rolling high/low over 100-bar windows
2. **EMA(15) Cross**: Intra-candle cross detection (Open < EMA < Close or vice versa)
3. **LONG Setup**: Price touches support pivot → EMA cross above → entry at close
4. **SHORT Setup**: Price touches resistance pivot → EMA cross below → entry at close
5. **VWAP Filter**: Price < VWAP = bullish bias (only LONG), Price > VWAP = bearish bias (only SHORT)
6. **Volume Profile**: 7-day VP for context (POC, VAH, VAL, HVN/LVN nodes)
7. **SL**: At pivot price ± 2.5 points
8. **TP1**: 1:1 risk/reward → then move SL to breakeven, let runner go

### PupupuV2 (Secondary - 5 minutes)
1. Same logic but EMA(12) and 400-bar pivot lookback (~33h)
2. TP at 1.7:1 risk/reward
3. Simpler (no VWAP filter, no VP)

## Trade Lifecycle

```
PENDING → ACTIVE → TP1_HIT → RUNNER
          ↓         ↓
        SL_HIT   NO_TEST (TP1 hit without EMA retest)
```

## Key Files

| File | Purpose |
|------|---------|
| `src/strategy/pupupuv3_signals.py` | Main signal generator (1m) |
| `src/strategy/pupupuv2_signals.py` | Legacy signal generator (5m) |
| `src/indicators/ema.py` | EMA calculation + cross detection |
| `src/indicators/pivot_detector_simple.py` | Rolling window pivot detection |
| `src/indicators/volume_profile.py` | 7-day Volume Profile (POC, HVN, LVN) |
| `src/indicators/vwap.py` | VWAP with session reset |
| `src/core/trade_lifecycle.py` | Trade state machine |
| `src/risk/position_sizer.py` | Dynamic position sizing |
| `config/default.py` | All strategy parameters |
| `reference/tradingview_pivot_rolling.pine` | Original TradingView indicator |

## Configuration

All parameters are in `config/default.py`. Key settings:
- **Capital**: $30,000
- **Risk per trade**: 2% ($600)
- **Max concurrent trades**: 3
- **Max daily loss**: 6% ($1,800) → stops trading
- **Exchange**: Binance (testnet by default)

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run backtests
python -m backtest.backtest_v3

# Debug signals
python tools/debug_signal_filters.py

# Compare pivots with TradingView
python tools/compare_pivots_tradingview.py
```

## Development Notes

### Data Format
All OHLCV data uses numpy arrays with shape (n, 6):
`[timestamp_ms, open, high, low, close, volume]`

### Exchange Connectivity
- Currently uses ccxt for historical data
- TODO: WebSocket integration for real-time feeds
- Testnet enabled by default (config/default.py → EXCHANGE.use_testnet)

### Known Limitations (from extraction)
- `sys.path.append('c:/repos/stock-analyzer')` removed - imports now use package structure
- ML predictor is a placeholder (returns 50% confidence)
- No live exchange execution yet
- Backtesting doesn't account for slippage properly
- Volume Profile recalculates from scratch every candle (should cache)
