"""
Multi-Market Backtesting Engine

Runs backtests across multiple global markets in parallel.
Compares performance across different markets and regions.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from market_config import (
    get_market_config,
    get_all_market_codes,
    get_markets_by_region,
    convert_to_usd,
    MARKET_REGIONS
)
from data_loader import DataLoader
from global_strategy_adapter import GlobalBoxStrategy
from backtester import BacktestEngine, TradeRecord
from metrics import PerformanceMetrics


class MultiMarketBacktester:
    """Run and compare backtests across multiple markets"""

    def __init__(
        self,
        initial_capital: float = 100000,
        risk_per_trade: float = 0.02,
        use_volatility_filter: bool = False
    ):
        """
        Initialize Multi-Market Backtester

        Args:
            initial_capital: Starting capital (in USD equivalent)
            risk_per_trade: Risk percentage per trade
            use_volatility_filter: Apply volatility filters
        """
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.use_volatility_filter = use_volatility_filter

        self.data_loader = DataLoader()
        self.results = {}

    def run_single_market(
        self,
        market_code: str,
        days: int = 60,
        verbose: bool = True
    ) -> Dict:
        """
        Run backtest for a single market

        Args:
            market_code: Market code (e.g., 'SPX', 'DAX')
            days: Number of days to backtest
            verbose: Print progress

        Returns:
            Dictionary with backtest results
        """
        if verbose:
            print(f"\n{'='*60}")
            print(f"Backtesting: {market_code}")
            print(f"{'='*60}")

        try:
            # Get market configuration
            config = get_market_config(market_code)

            # Create global strategy
            strategy = GlobalBoxStrategy(
                market_code=market_code,
                risk_per_trade=self.risk_per_trade,
                use_volatility_filter=self.use_volatility_filter
            )

            # Initialize backtest engine
            engine = BacktestEngine(
                initial_capital=self.initial_capital,
                risk_per_trade=self.risk_per_trade,
                slippage_points=config.recommended_slippage,
                point_value=config.point_value,
                min_box_range=config.typical_box_range[0],
                max_box_range=config.typical_box_range[1],
                use_volatility_filter=self.use_volatility_filter
            )

            # Override strategy with global version
            engine.strategy = strategy

            # Set date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Run backtest
            results = engine.run_backtest(market_code, start_date, end_date)

            # Calculate metrics
            trades_df = engine.export_trades_to_df()
            equity_df = engine.export_equity_curve_to_df()

            if not trades_df.empty and not equity_df.empty:
                metrics_calc = PerformanceMetrics(trades_df, equity_df)
                metrics = metrics_calc.calculate_all_metrics()
                results['metrics'] = metrics

                # Convert P&L to USD for comparison
                if config.currency != 'USD':
                    pnl_local = results['total_pnl']
                    pnl_usd = convert_to_usd(pnl_local, config.currency)
                    results['total_pnl_usd'] = pnl_usd
                else:
                    results['total_pnl_usd'] = results['total_pnl']

                # Add market info
                results['market_info'] = strategy.get_market_info()

            if verbose:
                print(f"[OK] {market_code} completed: "
                      f"{len(trades_df)} trades, "
                      f"Return: {results.get('return_pct', 0):.2f}%")

            return results

        except Exception as e:
            print(f"[ERROR] {market_code} failed: {e}")
            return {
                'symbol': market_code,
                'error': str(e),
                'success': False
            }

    def run_parallel_backtests(
        self,
        market_codes: List[str],
        days: int = 60,
        max_workers: int = 4
    ) -> Dict[str, Dict]:
        """
        Run backtests for multiple markets in parallel

        Args:
            market_codes: List of market codes
            days: Number of days to backtest
            max_workers: Maximum parallel workers

        Returns:
            Dictionary of results by market code
        """
        print(f"\n{'='*80}")
        print(f"MULTI-MARKET BACKTEST")
        print(f"{'='*80}")
        print(f"Markets: {', '.join(market_codes)}")
        print(f"Period: Last {days} days")
        print(f"Parallel workers: {max_workers}")

        results = {}
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_market = {
                executor.submit(self.run_single_market, code, days, False): code
                for code in market_codes
            }

            # Collect results as they complete
            for future in as_completed(future_to_market):
                market_code = future_to_market[future]
                try:
                    result = future.result()
                    results[market_code] = result
                    print(f"[OK] {market_code} completed")
                except Exception as e:
                    print(f"[ERROR] {market_code} failed: {e}")
                    results[market_code] = {
                        'symbol': market_code,
                        'error': str(e),
                        'success': False
                    }

        elapsed_time = time.time() - start_time
        print(f"\n[OK] All backtests completed in {elapsed_time:.1f} seconds")

        self.results = results
        return results

    def run_regional_backtests(
        self,
        region: str = 'AMERICAS',
        days: int = 60
    ) -> Dict[str, Dict]:
        """
        Run backtests for all markets in a region

        Args:
            region: Region name (AMERICAS, EUROPE, ASIA_PACIFIC)
            days: Number of days to backtest

        Returns:
            Dictionary of results
        """
        market_codes = get_markets_by_region(region)
        return self.run_parallel_backtests(market_codes, days)

    def run_all_markets(self, days: int = 60) -> Dict[str, Dict]:
        """
        Run backtests for all available markets

        Args:
            days: Number of days to backtest

        Returns:
            Dictionary of results
        """
        market_codes = get_all_market_codes()
        return self.run_parallel_backtests(market_codes, days)

    def create_comparison_table(self) -> pd.DataFrame:
        """
        Create comparison table of all markets

        Returns:
            DataFrame with comparison metrics
        """
        if not self.results:
            raise ValueError("No results available. Run backtests first.")

        comparison_data = []

        for market_code, result in self.results.items():
            if result.get('error'):
                continue

            metrics = result.get('metrics', {})
            market_info = result.get('market_info', {})

            basic = metrics.get('basic_stats', {})
            wr = metrics.get('win_rate', {})
            pf = metrics.get('profit_factor', {})
            sharpe = metrics.get('sharpe_ratio', {})
            mdd = metrics.get('max_drawdown', {})
            r_dist = metrics.get('r_distribution', {})

            comparison_data.append({
                'Market': market_code,
                'Name': market_info.get('name', ''),
                'Currency': market_info.get('currency', ''),
                'Trades': basic.get('executed_trades', 0),
                'Win Rate (%)': round(wr.get('win_rate', 0), 2),
                'Profit Factor': round(pf.get('profit_factor', 0), 2),
                'Avg R': round(r_dist.get('avg_r_multiple', 0), 2),
                'Sharpe': round(sharpe.get('sharpe_ratio', 0), 2),
                'Max DD (%)': round(mdd.get('max_drawdown_pct', 0), 2),
                'Return (%)': round(result.get('return_pct', 0), 2),
                'P&L (USD)': round(result.get('total_pnl_usd', 0), 2),
                'Liquidity': market_info.get('liquidity_rating', 0)
            })

        if not comparison_data:
            # Return empty dataframe with expected columns if no valid results
            return pd.DataFrame(columns=[
                'Market', 'Name', 'Currency', 'Trades', 'Win Rate (%)',
                'Profit Factor', 'Avg R', 'Sharpe', 'Max DD (%)',
                'Return (%)', 'P&L (USD)', 'Liquidity'
            ])

        df = pd.DataFrame(comparison_data)

        # Sort by return percentage
        df = df.sort_values('Return (%)', ascending=False)

        return df

    def get_best_markets(self, metric: str = 'Return (%)', top_n: int = 5) -> pd.DataFrame:
        """
        Get top performing markets by metric

        Args:
            metric: Metric to rank by
            top_n: Number of top markets to return

        Returns:
            DataFrame with top markets
        """
        df = self.create_comparison_table()

        if metric not in df.columns:
            raise ValueError(f"Unknown metric: {metric}. Available: {df.columns.tolist()}")

        return df.nlargest(top_n, metric)

    def save_comparison(self, output_dir: str = "tools/backtest/box_strategy/results"):
        """
        Save comparison results

        Args:
            output_dir: Output directory
        """
        if not self.results:
            raise ValueError("No results available. Run backtests first.")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save comparison table
        df_comparison = self.create_comparison_table()
        csv_file = output_path / f"multi_market_comparison_{timestamp}.csv"
        df_comparison.to_csv(csv_file, index=False)

        print(f"\n[OK] Comparison saved: {csv_file}")

        # Save full results as JSON
        json_file = output_path / f"multi_market_results_{timestamp}.json"

        def json_serial(obj):
            if isinstance(obj, (datetime, pd.Timestamp)):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        with open(json_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=json_serial)

        print(f"[OK] Full results saved: {json_file}")

        return csv_file, json_file

    def print_summary(self):
        """Print summary of multi-market backtest"""
        if not self.results:
            print("No results available.")
            return

        df = self.create_comparison_table()

        print(f"\n{'='*120}")
        print("MULTI-MARKET BACKTEST SUMMARY")
        print(f"{'='*120}\n")

        print(df.to_string(index=False))

        print(f"\n{'='*120}")
        print("TOP PERFORMERS")
        print(f"{'='*120}\n")

        metrics = ['Return (%)', 'Win Rate (%)', 'Profit Factor', 'Sharpe']

        for metric in metrics:
            print(f"\nBest by {metric}:")
            top_3 = df.nlargest(3, metric)[['Market', 'Name', metric]]
            for idx, row in top_3.iterrows():
                print(f"  {row['Market']:6s} - {row['Name']:35s}: {row[metric]:8.2f}")

        print(f"\n{'='*120}\n")


def main():
    """Test multi-market backtester"""
    # Initialize backtester
    backtester = MultiMarketBacktester(
        initial_capital=100000,
        risk_per_trade=0.02,
        use_volatility_filter=False
    )

    # Test with a few markets
    markets = ['SPX', 'NDX', 'DAX']

    results = backtester.run_parallel_backtests(markets, days=30, max_workers=3)

    # Print summary
    backtester.print_summary()

    # Save results
    backtester.save_comparison()


if __name__ == "__main__":
    main()
