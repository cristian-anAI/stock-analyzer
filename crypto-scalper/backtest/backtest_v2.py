"""
Extended Backtesting for PupupuV2 Strategy

Runs comprehensive backtests over multiple time periods with detailed metrics.
"""

import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import json
import os

sys.path.append('c:/repos/stock-analyzer')

from src.data.historical_data_fetcher import HistoricalDataFetcher
from src.strategy.pupupuv2_signals import PupupuV2Strategy, TradeSignal
from src.indicators.volume_profile import get_multi_timeframe_vp


class ExtendedBacktestResult:
    """Container for extended backtest results with advanced metrics."""

    def __init__(self):
        self.signals: List[TradeSignal] = []
        self.trades: List[Dict] = []
        self.equity_curve: List[float] = []
        self.timestamps: List[datetime] = []

        # Basic metrics
        self.total_trades = 0
        self.wins = 0
        self.losses = 0
        self.win_rate = 0.0
        self.total_pnl = 0.0
        self.profit_factor = 0.0

        # Advanced metrics
        self.max_drawdown = 0.0
        self.max_drawdown_pct = 0.0
        self.sharpe_ratio = 0.0
        self.avg_win = 0.0
        self.avg_loss = 0.0
        self.largest_win = 0.0
        self.largest_loss = 0.0
        self.avg_trade_duration = 0.0
        self.expectancy = 0.0

        # Consecutive stats
        self.max_consecutive_wins = 0
        self.max_consecutive_losses = 0

        # Monthly breakdown
        self.monthly_pnl: Dict[str, float] = {}
        self.monthly_trades: Dict[str, int] = {}

    def calculate_metrics(self):
        """Calculate all metrics from trades."""
        if not self.trades:
            return

        completed_trades = [t for t in self.trades if t['outcome'] != 'PENDING']

        if not completed_trades:
            return

        self.total_trades = len(completed_trades)
        self.wins = sum(1 for t in completed_trades if t['outcome'] == 'WIN')
        self.losses = self.total_trades - self.wins
        self.win_rate = self.wins / self.total_trades if self.total_trades > 0 else 0

        # P&L
        self.total_pnl = sum(t['pnl'] for t in completed_trades)

        # Win/Loss averages
        win_pnls = [t['pnl'] for t in completed_trades if t['outcome'] == 'WIN']
        loss_pnls = [abs(t['pnl']) for t in completed_trades if t['outcome'] == 'LOSS']

        self.avg_win = np.mean(win_pnls) if win_pnls else 0
        self.avg_loss = np.mean(loss_pnls) if loss_pnls else 0
        self.largest_win = max(win_pnls) if win_pnls else 0
        self.largest_loss = max(loss_pnls) if loss_pnls else 0

        # Profit factor
        total_wins = sum(win_pnls) if win_pnls else 0
        total_losses = sum(loss_pnls) if loss_pnls else 0
        self.profit_factor = total_wins / total_losses if total_losses > 0 else 0

        # Expectancy (average $ per trade)
        self.expectancy = self.total_pnl / self.total_trades

        # Average trade duration
        durations = [t['bars_held'] for t in completed_trades]
        self.avg_trade_duration = np.mean(durations) if durations else 0

        # Drawdown
        self._calculate_drawdown()

        # Consecutive wins/losses
        self._calculate_consecutive_stats(completed_trades)

        # Monthly breakdown
        self._calculate_monthly_breakdown(completed_trades)

    def _calculate_drawdown(self):
        """Calculate maximum drawdown from equity curve."""
        if not self.equity_curve:
            return

        peak = self.equity_curve[0]
        max_dd = 0
        max_dd_pct = 0

        for equity in self.equity_curve:
            if equity > peak:
                peak = equity

            dd = peak - equity
            dd_pct = (dd / peak * 100) if peak > 0 else 0

            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct

        self.max_drawdown = max_dd
        self.max_drawdown_pct = max_dd_pct

    def _calculate_consecutive_stats(self, trades: List[Dict]):
        """Calculate max consecutive wins and losses."""
        current_streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        last_outcome = None

        for trade in trades:
            outcome = trade['outcome']

            if outcome == last_outcome:
                current_streak += 1
            else:
                current_streak = 1
                last_outcome = outcome

            if outcome == 'WIN':
                max_win_streak = max(max_win_streak, current_streak)
            else:
                max_loss_streak = max(max_loss_streak, current_streak)

        self.max_consecutive_wins = max_win_streak
        self.max_consecutive_losses = max_loss_streak

    def _calculate_monthly_breakdown(self, trades: List[Dict]):
        """Break down results by month."""
        for i, trade in enumerate(trades):
            if i >= len(self.timestamps):
                continue

            month_key = self.timestamps[i].strftime('%Y-%m')

            if month_key not in self.monthly_pnl:
                self.monthly_pnl[month_key] = 0
                self.monthly_trades[month_key] = 0

            self.monthly_pnl[month_key] += trade['pnl']
            self.monthly_trades[month_key] += 1

    def to_dict(self) -> Dict:
        """Convert results to dictionary for JSON export."""
        return {
            'summary': {
                'total_trades': self.total_trades,
                'wins': self.wins,
                'losses': self.losses,
                'win_rate': f"{self.win_rate * 100:.2f}%",
                'total_pnl': round(self.total_pnl, 2),
                'profit_factor': round(self.profit_factor, 2),
                'expectancy': round(self.expectancy, 2)
            },
            'risk_metrics': {
                'max_drawdown': round(self.max_drawdown, 2),
                'max_drawdown_pct': f"{self.max_drawdown_pct:.2f}%",
                'largest_win': round(self.largest_win, 2),
                'largest_loss': round(self.largest_loss, 2)
            },
            'performance': {
                'avg_win': round(self.avg_win, 2),
                'avg_loss': round(self.avg_loss, 2),
                'avg_trade_duration_bars': round(self.avg_trade_duration, 1),
                'max_consecutive_wins': self.max_consecutive_wins,
                'max_consecutive_losses': self.max_consecutive_losses
            },
            'monthly_breakdown': {
                month: {
                    'pnl': round(pnl, 2),
                    'trades': self.monthly_trades[month]
                }
                for month, pnl in self.monthly_pnl.items()
            },
            'trades': self.trades
        }


class ExtendedBacktester:
    """
    Extended backtester with multiple period testing and advanced analytics.
    """

    def __init__(self, strategy_config: Dict = None):
        if strategy_config is None:
            strategy_config = {
                'ema_period': 12,
                'lookback_periods': 400,
                'tp_rr': 1.7,
                'sl_padding': 2.5
            }

        self.strategy = PupupuV2Strategy(strategy_config)
        self.risk_per_trade_usd = 200  # Fixed risk

    def run_backtest(
        self,
        ohlcv_data: np.ndarray,
        start_idx: int = 450,
        min_candles_between_signals: int = 10,
        period_name: str = "Unknown"
    ) -> ExtendedBacktestResult:
        """
        Run backtest on historical data.

        Args:
            ohlcv_data: Full OHLCV dataset
            start_idx: Index to start backtest
            min_candles_between_signals: Minimum gap between signals
            period_name: Name of the period being tested

        Returns:
            ExtendedBacktestResult with all metrics
        """
        result = ExtendedBacktestResult()
        last_signal_idx = -9999
        equity = 0

        print(f"\n{'='*70}")
        print(f"BACKTESTING: {period_name}")
        print(f"{'='*70}")
        print(f"Total candles: {len(ohlcv_data)}")
        print(f"Start index: {start_idx}")
        print(f"Testing period: {len(ohlcv_data) - start_idx} candles")
        print(f"Date range: {datetime.fromtimestamp(ohlcv_data[start_idx, 0]/1000)} to {datetime.fromtimestamp(ohlcv_data[-1, 0]/1000)}")
        print(f"{'='*70}\n")

        signal_count = 0

        # Walk forward through data
        for i in range(start_idx, len(ohlcv_data)):
            # Skip if too soon after last signal
            if i - last_signal_idx < min_candles_between_signals:
                continue

            # Get data up to current candle
            current_data = ohlcv_data[:i+1]

            # Calculate VP (use last 500 for performance)
            vp_data = None
            if len(current_data) >= 100:
                try:
                    vp_data = get_multi_timeframe_vp(current_data[-500:], num_bins=60)
                except:
                    pass

            # Analyze for signal
            signal = self.strategy.analyze_for_signals(current_data, vp_data)

            if signal:
                signal_count += 1
                last_signal_idx = i

                # Simulate trade outcome
                trade = self._simulate_trade(signal, ohlcv_data[i+1:], i)

                result.signals.append(signal)
                result.trades.append(trade)

                # Update equity curve
                equity += trade['pnl']
                result.equity_curve.append(equity)
                result.timestamps.append(datetime.fromtimestamp(ohlcv_data[i, 0] / 1000))

                # Log progress every 5 signals
                if signal_count % 5 == 0:
                    timestamp = datetime.fromtimestamp(ohlcv_data[i, 0] / 1000)
                    print(f"[{signal_count}] {timestamp.strftime('%Y-%m-%d %H:%M')} | "
                          f"{signal.direction} @ ${signal.entry_price:,.2f} | "
                          f"Outcome: {trade['outcome']} (${trade['pnl']:+,.2f}) | "
                          f"Equity: ${equity:,.2f}")

        # Calculate all metrics
        result.calculate_metrics()

        return result

    def run_multi_period_backtest(
        self,
        periods_data: Dict[str, np.ndarray]
    ) -> Dict[str, ExtendedBacktestResult]:
        """
        Run backtests across multiple time periods.

        Args:
            periods_data: Dict mapping period name -> OHLCV data

        Returns:
            Dict mapping period name -> results
        """
        all_results = {}

        for period_name, data in periods_data.items():
            if data is None or len(data) < 500:
                print(f"\nSkipping {period_name} - insufficient data")
                continue

            result = self.run_backtest(
                data,
                start_idx=450,
                period_name=period_name
            )

            all_results[period_name] = result

        return all_results

    def _simulate_trade(
        self,
        signal: TradeSignal,
        future_candles: np.ndarray,
        signal_idx: int
    ) -> Dict:
        """Simulate trade outcome by checking future candles."""
        if len(future_candles) == 0:
            return {
                'outcome': 'PENDING',
                'pnl': 0,
                'bars_held': 0,
                'exit_price': signal.entry_price,
                'rr_achieved': None
            }

        entry = signal.entry_price
        sl = signal.stop_loss
        tp = signal.take_profit
        direction = signal.direction

        # Walk through future candles
        for bar_num, candle in enumerate(future_candles):
            high = candle[2]
            low = candle[3]

            if direction == "LONG":
                if low <= sl:
                    pnl = (sl - entry) * (self.risk_per_trade_usd / abs(entry - sl))
                    return {
                        'outcome': 'LOSS',
                        'pnl': pnl,
                        'bars_held': bar_num + 1,
                        'exit_price': sl,
                        'rr_achieved': -1.0
                    }

                if high >= tp:
                    pnl = (tp - entry) * (self.risk_per_trade_usd / abs(entry - sl))
                    rr = abs((tp - entry) / (entry - sl))
                    return {
                        'outcome': 'WIN',
                        'pnl': pnl,
                        'bars_held': bar_num + 1,
                        'exit_price': tp,
                        'rr_achieved': rr
                    }

            else:  # SHORT
                if high >= sl:
                    pnl = (entry - sl) * (self.risk_per_trade_usd / abs(entry - sl))
                    return {
                        'outcome': 'LOSS',
                        'pnl': pnl,
                        'bars_held': bar_num + 1,
                        'exit_price': sl,
                        'rr_achieved': -1.0
                    }

                if low <= tp:
                    pnl = (entry - tp) * (self.risk_per_trade_usd / abs(entry - sl))
                    rr = abs((entry - tp) / (sl - entry))
                    return {
                        'outcome': 'WIN',
                        'pnl': pnl,
                        'bars_held': bar_num + 1,
                        'exit_price': tp,
                        'rr_achieved': rr
                    }

        # Neither hit
        current_price = future_candles[-1, 4]
        if direction == "LONG":
            unrealized = (current_price - entry) * (self.risk_per_trade_usd / abs(entry - sl))
        else:
            unrealized = (entry - current_price) * (self.risk_per_trade_usd / abs(entry - sl))

        return {
            'outcome': 'PENDING',
            'pnl': unrealized,
            'bars_held': len(future_candles),
            'exit_price': current_price,
            'rr_achieved': None
        }


# ==================== MAIN SCRIPT ====================

if __name__ == "__main__":
    print("="*70)
    print("PUPUPUV2 EXTENDED BACKTESTING")
    print("="*70)

    # 1. Fetch historical data
    fetcher = HistoricalDataFetcher()

    print("\nFetching historical data for multiple periods...")
    periods_data = fetcher.fetch_multiple_periods(
        'BTC/USDT',
        '5m',
        periods=[7, 14, 30]  # 7, 14, and 30 days
    )

    # 2. Run backtests
    backtester = ExtendedBacktester()
    results = backtester.run_multi_period_backtest(periods_data)

    # 3. Print results for each period
    print("\n" + "="*70)
    print("BACKTEST RESULTS SUMMARY")
    print("="*70)

    for period_name, result in results.items():
        print(f"\n{'─'*70}")
        print(f"PERIOD: {period_name}")
        print(f"{'─'*70}")

        print(f"\n📊 PERFORMANCE METRICS")
        print(f"  Total Trades:     {result.total_trades}")
        print(f"  Wins:             {result.wins}")
        print(f"  Losses:           {result.losses}")
        print(f"  Win Rate:         {result.win_rate*100:.2f}%")

        print(f"\n💰 P&L METRICS")
        print(f"  Total P&L:        ${result.total_pnl:,.2f}")
        print(f"  Profit Factor:    {result.profit_factor:.2f}")
        print(f"  Expectancy:       ${result.expectancy:,.2f}/trade")
        print(f"  Avg Win:          ${result.avg_win:,.2f}")
        print(f"  Avg Loss:         ${result.avg_loss:,.2f}")

        print(f"\n⚠️  RISK METRICS")
        print(f"  Max Drawdown:     ${result.max_drawdown:,.2f} ({result.max_drawdown_pct:.2f}%)")
        print(f"  Largest Win:      ${result.largest_win:,.2f}")
        print(f"  Largest Loss:     ${result.largest_loss:,.2f}")

        print(f"\n📈 TRADING STATS")
        print(f"  Avg Duration:     {result.avg_trade_duration:.1f} bars ({result.avg_trade_duration * 5:.0f} min)")
        print(f"  Max Win Streak:   {result.max_consecutive_wins}")
        print(f"  Max Loss Streak:  {result.max_consecutive_losses}")

        # Monthly breakdown
        if result.monthly_pnl:
            print(f"\n📅 MONTHLY BREAKDOWN")
            for month in sorted(result.monthly_pnl.keys()):
                pnl = result.monthly_pnl[month]
                trades = result.monthly_trades[month]
                print(f"  {month}:  ${pnl:+,.2f}  ({trades} trades)")

    # 4. Save detailed results
    print("\n" + "="*70)
    print("SAVING RESULTS")
    print("="*70)

    for period_name, result in results.items():
        filename = f"backtest_results_{period_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(filename, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)

        print(f"✓ Saved {period_name} results to: {filename}")

    print("\n" + "="*70)
    print("BACKTESTING COMPLETED")
    print("="*70)
