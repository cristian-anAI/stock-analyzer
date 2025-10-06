# Box Strategy Backtesting System

## Overview

Complete backtesting system for the Box/Opening Range intraday trading strategy.

## Strategy Description

The Box Strategy captures volatility around NYSE market open by trading breakouts from a defined price range (the "box").

### Key Parameters:
- **Timeframe**: 5-minute candles
- **Box Formation**: 8:30 AM - 10:00 AM ET (1.5 hours)
- **Entry Window**: 2 hours after box close (until 12:00 PM ET)
- **Stop Loss**: Opposite edge of box
- **Take Profit**: 3-tier system (50%, 25%, 25%)

## Usage

### Single Symbol Backtest

```bash
# S&P 500 (last 60 days)
python main.py --symbol SPX --days 60

# NASDAQ 100 (last 30 days, 1% risk)
python main.py --symbol NDX --days 30 --risk 0.01

# With custom parameters
python main.py --symbol SPX --days 60 --capital 50000 --risk 0.015 --point-value 50
```

### Compare Multiple Symbols

```bash
# Compare S&P 500 and NASDAQ 100
python main.py --compare SPX NDX --days 60

# Compare with custom settings
python main.py --compare SPX NDX --days 45 --risk 0.01 --capital 100000
```

### Command Line Arguments

- `--symbol`: Single symbol to backtest (SPX, NDX, DAX, etc.)
- `--compare`: Multiple symbols to compare (space-separated)
- `--days`: Number of days to backtest (max 60 for 5-min data, default: 60)
- `--capital`: Initial capital (default: 100000)
- `--risk`: Risk per trade as decimal (default: 0.02 = 2%)
- `--slippage`: Slippage in points (default: 1.0)
- `--point-value`: Dollar value per point (default: 50 for ES)
- `--min-box`: Minimum box range in points (default: 5)
- `--max-box`: Maximum box range in points (default: 100)
- `--volatility-filter`: Enable volatility filter (flag)

## Available Symbols

- **SPX**: S&P 500 E-mini Futures (ES=F)
- **NDX**: NASDAQ 100 E-mini Futures (NQ=F)
- **DAX**: DAX Futures (FDAX=F)
- **FTSE**: FTSE 100
- **CAC**: CAC 40
- **NKY**: Nikkei 225 Futures (NKD=F)
- **HSI**: Hang Seng Index

## Point Values

Common index point values:
- S&P 500 (ES): $50 per point
- NASDAQ 100 (NQ): $20 per point
- DAX: €25 per point
- FTSE: £10 per point

## Output

The system generates:

1. **JSON Results**: Complete backtest data saved to `results/`
2. **CSV Trades**: Individual trade records in CSV format
3. **Charts** (saved to `charts/`):
   - Equity curve with metrics
   - Drawdown analysis
   - R-multiple distribution
   - Monthly returns heatmap
   - Trade analysis dashboard
   - Box range analysis

4. **Console Report**: Comprehensive performance metrics

## Performance Metrics

The system calculates:
- Win rate and win/loss statistics
- Profit factor
- Sharpe ratio and Sortino ratio
- Maximum drawdown
- Monthly returns
- R-multiple distribution
- Trade duration analysis
- Directional performance (long vs short)
- Box range optimization

## Data Limitations

**IMPORTANT**: Yahoo Finance provides up to ~60 days of 5-minute historical data.

For longer backtests, consider:
- Interactive Brokers API
- Alpha Vantage
- Polygon.io
- FirstRate Data

## Examples

### Example 1: Quick Test
```bash
python main.py --symbol SPX --days 30
```

### Example 2: Conservative Settings
```bash
python main.py --symbol NDX --days 60 --risk 0.01 --max-box 50
```

### Example 3: Multi-Symbol Comparison
```bash
python main.py --compare SPX NDX DAX --days 60 --risk 0.02
```

### Example 4: Full Custom Configuration
```bash
python main.py --symbol SPX --days 60 \
    --capital 50000 \
    --risk 0.015 \
    --slippage 0.5 \
    --point-value 50 \
    --min-box 5 \
    --max-box 80 \
    --volatility-filter
```

## Module Structure

- `data_loader.py`: Historical data retrieval and caching
- `strategy.py`: Box strategy logic and trade management
- `backtester.py`: Backtesting engine
- `metrics.py`: Performance metrics calculation
- `visualization.py`: Chart and report generation
- `main.py`: CLI orchestrator

## Next Steps (Phase 2 & 3)

### Phase 2: Global Markets
Expand to additional indices:
- European markets (DAX, FTSE, CAC)
- Asian markets (Nikkei, Hang Seng)
- Comparative performance analysis

### Phase 3: Machine Learning
- Feature engineering from historical trades
- Predictive models for trade success probability
- Daily confidence scoring system
- Optimization of entry/exit rules

## Support

For issues or questions, consult the project documentation or create an issue in the repository.
