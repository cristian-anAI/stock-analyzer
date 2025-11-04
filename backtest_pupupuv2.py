"""
Backtesting script for pupupuv2 strategy

Tests the strategy on historical BTC data to validate:
- Signal generation accuracy
- Win rate
- Average R:R achieved
- Drawdown
"""

import sys
import numpy as np
from datetime import datetime
from typing import List, Dict
import json

sys.path.append('c:/repos/stock-analyzer')

from src.data.binance_client import BinanceDataClient
from src.strategy.pupupuv2_signals import PupupuV2Strategy, TradeSignal
from src.indicators.volume_profile import get_multi_timeframe_vp


class BacktestResult:
    """Container for backtest results."""
    def __init__(self):
        self.signals: List[TradeSignal] = []
        self.trades: List[Dict] = []
        self.total_pnl = 0
        self.wins = 0
        self.losses = 0
        self.win_rate = 0
        self.avg_rr = 0
        self.max_drawdown = 0


class PupupuV2Backtester:
    """
    Backtest pupupuv2 strategy on historical data.

    Simulates walking forward through candles and detecting signals.
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
        self.risk_per_trade_usd = 200  # Fixed $200 risk per trade

    def run_backtest(
        self,
        ohlcv_data: np.ndarray,
        start_idx: int = 450,
        min_candles_between_signals: int = 10
    ) -> BacktestResult:
        """
        Run backtest on historical data.

        Args:
            ohlcv_data: Full OHLCV dataset
            start_idx: Index to start backtest (need history for indicators)
            min_candles_between_signals: Minimum candles between trade signals

        Returns:
            BacktestResult with all metrics
        """
        result = BacktestResult()
        last_signal_idx = -9999

        print(f"\n{'='*70}")
        print(f"RUNNING BACKTEST")
        print(f"{'='*70}")
        print(f"Total candles: {len(ohlcv_data)}")
        print(f"Start index: {start_idx}")
        print(f"Backtesting period: {len(ohlcv_data) - start_idx} candles")
        print(f"{'='*70}\n")

        # Walk forward through data
        for i in range(start_idx, len(ohlcv_data)):
            # Skip if too soon after last signal
            if i - last_signal_idx < min_candles_between_signals:
                continue

            # Get data up to current candle
            current_data = ohlcv_data[:i+1]

            # Calculate VP (use last 500 candles for speed)
            vp_data = None
            if len(current_data) >= 100:
                try:
                    vp_data = get_multi_timeframe_vp(current_data[-500:], num_bins=60)
                except:
                    pass

            # Analyze for signal
            signal = self.strategy.analyze_for_signals(current_data, vp_data)

            if signal:
                # Signal found!
                last_signal_idx = i

                # Simulate trade outcome
                trade = self._simulate_trade(signal, ohlcv_data[i+1:], i)

                result.signals.append(signal)
                result.trades.append(trade)

                # Log signal
                timestamp = datetime.fromtimestamp(ohlcv_data[i, 0] / 1000)
                print(f"\n[{i}/{len(ohlcv_data)}] SIGNAL @ {timestamp.strftime('%Y-%m-%d %H:%M')}")
                print(f"  Direction: {signal.direction}")
                print(f"  Entry: ${signal.entry_price:,.2f}")
                print(f"  SL: ${signal.stop_loss:,.2f}")
                print(f"  TP: ${signal.take_profit:,.2f}")
                print(f"  Confidence: {signal.confidence:.1%}")
                print(f"  Outcome: {trade['outcome']} (${trade['pnl']:,.2f})")

        # Calculate metrics
        result.total_pnl = sum(t['pnl'] for t in result.trades)
        result.wins = sum(1 for t in result.trades if t['outcome'] == 'WIN')
        result.losses = sum(1 for t in result.trades if t['outcome'] == 'LOSS')
        result.win_rate = result.wins / len(result.trades) if result.trades else 0

        # Calculate average R:R achieved
        if result.trades:
            rr_values = [t['rr_achieved'] for t in result.trades if t['rr_achieved'] is not None]
            result.avg_rr = np.mean(rr_values) if rr_values else 0

        # Calculate max drawdown
        result.max_drawdown = self._calculate_max_drawdown(result.trades)

        return result

    def _simulate_trade(
        self,
        signal: TradeSignal,
        future_candles: np.ndarray,
        signal_idx: int
    ) -> Dict:
        """
        Simulate trade outcome by checking future candles.

        Returns:
            {
                'outcome': 'WIN' | 'LOSS' | 'PENDING',
                'pnl': float,
                'bars_held': int,
                'exit_price': float,
                'rr_achieved': float
            }
        """
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

        # Walk through future candles until SL or TP hit
        for bar_num, candle in enumerate(future_candles):
            high = candle[2]
            low = candle[3]
            close = candle[4]

            if direction == "LONG":
                # Check SL first (conservative)
                if low <= sl:
                    # Stop loss hit
                    pnl = (sl - entry) * (self.risk_per_trade_usd / abs(entry - sl))
                    return {
                        'outcome': 'LOSS',
                        'pnl': pnl,
                        'bars_held': bar_num + 1,
                        'exit_price': sl,
                        'rr_achieved': -1.0
                    }

                # Check TP
                if high >= tp:
                    # Take profit hit
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
                # Check SL first
                if high >= sl:
                    # Stop loss hit
                    pnl = (entry - sl) * (self.risk_per_trade_usd / abs(entry - sl))
                    return {
                        'outcome': 'LOSS',
                        'pnl': pnl,
                        'bars_held': bar_num + 1,
                        'exit_price': sl,
                        'rr_achieved': -1.0
                    }

                # Check TP
                if low <= tp:
                    # Take profit hit
                    pnl = (entry - tp) * (self.risk_per_trade_usd / abs(entry - sl))
                    rr = abs((entry - tp) / (sl - entry))
                    return {
                        'outcome': 'WIN',
                        'pnl': pnl,
                        'bars_held': bar_num + 1,
                        'exit_price': tp,
                        'rr_achieved': rr
                    }

        # Neither hit in available data
        current_price = future_candles[-1, 4]
        if direction == "LONG":
            unrealized_pnl = (current_price - entry) * (self.risk_per_trade_usd / abs(entry - sl))
        else:
            unrealized_pnl = (entry - current_price) * (self.risk_per_trade_usd / abs(entry - sl))

        return {
            'outcome': 'PENDING',
            'pnl': unrealized_pnl,
            'bars_held': len(future_candles),
            'exit_price': current_price,
            'rr_achieved': None
        }

    def _calculate_max_drawdown(self, trades: List[Dict]) -> float:
        """Calculate maximum drawdown from equity curve."""
        if not trades:
            return 0

        equity = 0
        peak = 0
        max_dd = 0

        for trade in trades:
            equity += trade['pnl']
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd

        return max_dd


# ==================== MAIN SCRIPT ====================

if __name__ == "__main__":
    print("="*70)
    print("PUPUPUV2 BACKTEST")
    print("="*70)

    # Fetch historical data
    print("\nFetching BTC/USDT 5-min data from Binance...")
    client = BinanceDataClient()

    # Fetch maximum available (1000 candles = ~3.5 days)
    ohlcv = client.fetch_ohlcv('BTC/USDT', '5m', limit=1000)
    print(f"[OK] Fetched {len(ohlcv)} candles")
    print(f"Period: {datetime.fromtimestamp(ohlcv[0, 0]/1000)} to {datetime.fromtimestamp(ohlcv[-1, 0]/1000)}")

    # Run backtest
    backtester = PupupuV2Backtester()
    result = backtester.run_backtest(ohlcv, start_idx=450, min_candles_between_signals=10)

    # Print results
    print("\n" + "="*70)
    print("BACKTEST RESULTS")
    print("="*70)
    print(f"\nTotal signals generated: {len(result.signals)}")
    print(f"Total trades completed: {len([t for t in result.trades if t['outcome'] != 'PENDING'])}")

    completed_trades = [t for t in result.trades if t['outcome'] != 'PENDING']

    if completed_trades:
        print(f"\nWins: {result.wins}")
        print(f"Losses: {result.losses}")
        print(f"Win rate: {result.win_rate:.1%}")

        print(f"\nTotal P&L: ${result.total_pnl:,.2f}")
        print(f"Average R:R achieved: {result.avg_rr:.2f}")
        print(f"Max drawdown: ${result.max_drawdown:,.2f}")

        avg_win = np.mean([t['pnl'] for t in completed_trades if t['outcome'] == 'WIN']) if result.wins > 0 else 0
        avg_loss = np.mean([abs(t['pnl']) for t in completed_trades if t['outcome'] == 'LOSS']) if result.losses > 0 else 0

        print(f"\nAverage win: ${avg_win:,.2f}")
        print(f"Average loss: ${avg_loss:,.2f}")

        if avg_loss > 0:
            profit_factor = (avg_win * result.wins) / (avg_loss * result.losses)
            print(f"Profit factor: {profit_factor:.2f}")

        # Show distribution of holding periods
        hold_times = [t['bars_held'] for t in completed_trades]
        print(f"\nAverage bars held: {np.mean(hold_times):.1f} candles ({np.mean(hold_times) * 5:.0f} minutes)")
        print(f"Max bars held: {np.max(hold_times)} candles ({np.max(hold_times) * 5:.0f} minutes)")

    else:
        print("\n[NO COMPLETED TRADES] No signals were fully resolved in backtest period")

    # Save detailed results
    try:
        with open('backtest_results.json', 'w') as f:
            json.dump({
                'total_signals': len(result.signals),
                'total_trades': len(result.trades),
                'wins': result.wins,
                'losses': result.losses,
                'win_rate': result.win_rate,
                'total_pnl': result.total_pnl,
                'avg_rr': result.avg_rr,
                'max_drawdown': result.max_drawdown,
                'trades': result.trades
            }, f, indent=2)
        print(f"\n[OK] Detailed results saved to backtest_results.json")
    except Exception as e:
        print(f"\n[WARNING] Could not save results: {e}")

    print("\n" + "="*70)
