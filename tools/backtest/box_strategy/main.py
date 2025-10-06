"""
Main Entry Point for Box Strategy Backtesting System

Orchestrates the complete backtesting workflow:
1. Data loading
2. Strategy execution
3. Performance metrics calculation
4. Visualization generation
5. Report creation

Usage:
    python main.py --symbol SPX --days 60
    python main.py --symbol NDX --days 30 --risk 0.01
    python main.py --compare SPX NDX --days 60
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from data_loader import DataLoader
from backtester import BacktestEngine
from metrics import PerformanceMetrics
from visualization import StrategyVisualizer


def run_single_backtest(
    symbol: str,
    days: int = 60,
    initial_capital: float = 100000,
    risk_per_trade: float = 0.02,
    slippage_points: float = 1.0,
    point_value: float = 50.0,
    min_box_range: float = 5.0,
    max_box_range: float = 100.0,
    use_volatility_filter: bool = False
) -> dict:
    """
    Run backtest for a single symbol

    Args:
        symbol: Symbol key ('SPX', 'NDX', etc.)
        days: Number of days to backtest (max 60 for 5-min data)
        initial_capital: Starting capital
        risk_per_trade: Risk percentage per trade
        slippage_points: Slippage in points
        point_value: Dollar value per point
        min_box_range: Minimum box range to trade
        max_box_range: Maximum box range (volatility filter)
        use_volatility_filter: Enable volatility filter

    Returns:
        Dictionary with backtest results
    """
    print(f"\n{'='*80}")
    print(f"BOX STRATEGY BACKTEST - {symbol}")
    print(f"{'='*80}")
    print(f"Parameters:")
    print(f"  Period: Last {days} days")
    print(f"  Initial Capital: ${initial_capital:,.2f}")
    print(f"  Risk per Trade: {risk_per_trade*100:.1f}%")
    print(f"  Point Value: ${point_value}")
    print(f"  Box Range Filter: {min_box_range} - {max_box_range} points")
    print(f"  Volatility Filter: {'Enabled' if use_volatility_filter else 'Disabled'}")

    # Initialize engine
    engine = BacktestEngine(
        initial_capital=initial_capital,
        risk_per_trade=risk_per_trade,
        slippage_points=slippage_points,
        point_value=point_value,
        min_box_range=min_box_range,
        max_box_range=max_box_range,
        use_volatility_filter=use_volatility_filter
    )

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Run backtest
    results = engine.run_backtest(symbol, start_date, end_date)

    # Calculate metrics
    trades_df = engine.export_trades_to_df()
    equity_df = engine.export_equity_curve_to_df()

    if not trades_df.empty and not equity_df.empty:
        metrics_calc = PerformanceMetrics(trades_df, equity_df)
        metrics = metrics_calc.calculate_all_metrics()

        # Print summary
        metrics_calc.print_summary(metrics)

        # Add metrics to results
        results['metrics'] = metrics

        # Generate visualizations
        visualizer = StrategyVisualizer()
        chart_paths = visualizer.create_full_report(trades_df, equity_df, metrics, symbol)
        results['charts'] = [str(p) for p in chart_paths]

        # Save results
        output_path = engine.save_results(results)
        results['report_path'] = str(output_path)

    else:
        print("\n[WARNING] No trades executed. Cannot calculate metrics.")
        results['metrics'] = {}
        results['charts'] = []

    return results


def compare_symbols(
    symbols: list,
    days: int = 60,
    **backtest_kwargs
) -> dict:
    """
    Compare multiple symbols

    Args:
        symbols: List of symbol keys
        days: Number of days to backtest
        **backtest_kwargs: Additional backtest parameters

    Returns:
        Dictionary with comparison results
    """
    print(f"\n{'='*80}")
    print(f"COMPARATIVE BACKTEST - {', '.join(symbols)}")
    print(f"{'='*80}")

    results = {}
    comparison_data = []

    # Run backtest for each symbol
    for symbol in symbols:
        try:
            result = run_single_backtest(symbol, days, **backtest_kwargs)
            results[symbol] = result

            # Extract key metrics for comparison
            metrics = result.get('metrics', {})
            basic = metrics.get('basic_stats', {})
            wr = metrics.get('win_rate', {})
            pf = metrics.get('profit_factor', {})
            sharpe = metrics.get('sharpe_ratio', {})
            mdd = metrics.get('max_drawdown', {})
            r_dist = metrics.get('r_distribution', {})

            comparison_data.append({
                'Symbol': symbol,
                'Total Trades': basic.get('executed_trades', 0),
                'Win Rate (%)': round(wr.get('win_rate', 0), 2),
                'Profit Factor': round(pf.get('profit_factor', 0), 2),
                'Avg R': round(r_dist.get('avg_r_multiple', 0), 2),
                'Sharpe Ratio': round(sharpe.get('sharpe_ratio', 0), 2),
                'Max DD (%)': round(mdd.get('max_drawdown_pct', 0), 2),
                'Total P&L ($)': round(basic.get('total_pnl', 0), 2),
                'Return (%)': round(result.get('return_pct', 0), 2)
            })

        except Exception as e:
            print(f"\n[ERROR] Error backtesting {symbol}: {e}")
            continue

    # Create comparison table
    if comparison_data:
        df_comparison = pd.DataFrame(comparison_data)

        print(f"\n{'='*80}")
        print("COMPARISON SUMMARY")
        print(f"{'='*80}\n")
        print(df_comparison.to_string(index=False))

        # Save comparison
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("tools/backtest/box_strategy/results")
        output_dir.mkdir(parents=True, exist_ok=True)

        comparison_file = output_dir / f"comparison_{timestamp}.csv"
        df_comparison.to_csv(comparison_file, index=False)
        print(f"\n[OK] Comparison saved to: {comparison_file}")

        results['comparison'] = df_comparison.to_dict('records')
        results['comparison_file'] = str(comparison_file)

    return results


def create_readme():
    """Create README with usage instructions"""
    readme_content = """# Box Strategy Backtesting System

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
python main.py --symbol SPX --days 60 \\
    --capital 50000 \\
    --risk 0.015 \\
    --slippage 0.5 \\
    --point-value 50 \\
    --min-box 5 \\
    --max-box 80 \\
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
"""

    readme_path = Path("tools/backtest/box_strategy/README.md")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)

    print(f"\n[OK] README created: {readme_path}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Box Strategy Backtesting System',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Symbol selection
    parser.add_argument('--symbol', type=str, help='Single symbol to backtest (SPX, NDX, etc.)')
    parser.add_argument('--compare', nargs='+', help='Multiple symbols to compare')

    # Backtest parameters
    parser.add_argument('--days', type=int, default=60, help='Number of days to backtest (max 60)')
    parser.add_argument('--capital', type=float, default=100000, help='Initial capital')
    parser.add_argument('--risk', type=float, default=0.02, help='Risk per trade (decimal)')
    parser.add_argument('--slippage', type=float, default=1.0, help='Slippage in points')
    parser.add_argument('--point-value', type=float, default=50.0, help='Dollar value per point')
    parser.add_argument('--min-box', type=float, default=5.0, help='Minimum box range')
    parser.add_argument('--max-box', type=float, default=100.0, help='Maximum box range')
    parser.add_argument('--volatility-filter', action='store_true', help='Enable volatility filter')

    # Utility commands
    parser.add_argument('--create-readme', action='store_true', help='Create README file')

    args = parser.parse_args()

    # Create README if requested
    if args.create_readme:
        create_readme()
        return

    # Prepare backtest kwargs
    backtest_kwargs = {
        'initial_capital': args.capital,
        'risk_per_trade': args.risk,
        'slippage_points': args.slippage,
        'point_value': args.point_value,
        'min_box_range': args.min_box,
        'max_box_range': args.max_box,
        'use_volatility_filter': args.volatility_filter
    }

    # Run backtest
    if args.compare:
        # Multi-symbol comparison
        results = compare_symbols(args.compare, args.days, **backtest_kwargs)

    elif args.symbol:
        # Single symbol backtest
        results = run_single_backtest(args.symbol, args.days, **backtest_kwargs)

    else:
        # No symbol specified - run default SPX backtest
        print("No symbol specified. Running default SPX backtest...")
        results = run_single_backtest('SPX', args.days, **backtest_kwargs)

    print(f"\n{'='*80}")
    print("[OK] Backtest Complete!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
