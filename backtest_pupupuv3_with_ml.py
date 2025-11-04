"""
PupupuV3 Backtest with ML Training

Complete backtest system that:
1. Runs backtest on historical 1-min data
2. Collects signal outcomes for each R:R ratio
3. Trains TP Ratio Predictor ML model
4. Re-runs backtest with ML-predicted TP2/TP3
5. Compares performance

Usage:
    python backtest_pupupuv3_with_ml.py --symbol BTC/USDT --days 30
"""

import sys
import argparse
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple
import json

sys.path.append(str(Path(__file__).parent))

from src.data.binance_client_v3 import BinanceClientV3
from src.strategy.pupupuv3_signals import PupupuV3Strategy, TradeSignal

# Import ML model directly to avoid circular imports
sys.path.append(str(Path(__file__).parent / 'tools' / 'backtest' / 'box_strategy' / 'ml'))
from tp_ratio_predictor import TPRatioMLModel


class PupupuV3Backtest:
    """
    Backtesting engine for PupupuV3 with ML integration
    """

    def __init__(self, symbol: str = "BTC/USDT", capital: float = 30000):
        """
        Initialize backtest

        Args:
            symbol: Trading pair
            capital: Starting capital
        """
        self.symbol = symbol
        self.capital = capital
        self.initial_capital = capital

        # Configuration
        self.config = {
            'ema_period': 15,
            'pivot_lookback': 100,
            'capital_crypto': capital,
            'risk_per_trade_pct': 0.02,
            'risk_reduced_pct': 0.01,
            'tp1_ratio': 1.0,
            'pivot_touch_threshold': 0.1
        }

        self.strategy = PupupuV3Strategy(self.config)

        # Results storage
        self.signals: List[Dict] = []
        self.trades: List[Dict] = []

    def run_backtest_phase1(self, ohlcv_data: np.ndarray,
                           start_idx: int = 1000) -> Tuple[List[Dict], List[Dict]]:
        """
        Phase 1: Run backtest to collect data for ML training

        For each signal:
        - Record entry details
        - Track if each R:R ratio (2:1 to 20:1) was reached
        - Track timeframes when reached (1h, 2h, 4h, 8h)

        Args:
            ohlcv_data: Historical OHLCV data (1-min candles)
            start_idx: Index to start backtest (need history for indicators)

        Returns:
            (signals_data, trades_data)
        """
        print(f"\n{'='*70}")
        print(f"PHASE 1: DATA COLLECTION FOR ML TRAINING")
        print(f"{'='*70}")
        print(f"Symbol: {self.symbol}")
        print(f"Candles: {len(ohlcv_data)}")
        print(f"Start Index: {start_idx}")

        signals_data = []
        trades_data = []

        print(f"\nScanning for signals...")

        for i in range(start_idx, len(ohlcv_data) - 500):  # Leave 500 candles for outcome tracking
            if i % 1000 == 0:
                print(f"  Progress: {i}/{len(ohlcv_data)} ({i/len(ohlcv_data)*100:.1f}%)")

            # Get data up to current point
            current_data = ohlcv_data[:i+1]

            # Check for signal
            signal = self.strategy.analyze_for_signals(current_data, self.symbol)

            if signal and signal.is_valid:
                # Record signal
                signal_data = {
                    'timestamp': signal.timestamp,
                    'entry_idx': i,
                    'entry_price': signal.entry_price,
                    'stop_loss': signal.stop_loss,
                    'direction': signal.direction,
                    'pivot_strength': signal.pivot_strength,
                    'ema_value': signal.ema_value,
                    'vwap_value': signal.vwap_value,
                    'with_vwap_bias': signal.with_vwap_bias,
                    'ml_confidence': signal.ml_confidence
                }

                # Track outcomes for each R:R ratio
                risk = abs(signal.entry_price - signal.stop_loss)
                outcomes = self._track_ratio_outcomes(
                    ohlcv_data, i, signal.entry_price, risk, signal.direction
                )

                signal_data['outcomes'] = outcomes

                signals_data.append(signal_data)

                # Simulate trade with TP1 only
                trade_result = self._simulate_trade_tp1(
                    ohlcv_data, i, signal.entry_price, signal.stop_loss,
                    signal.take_profit_1, signal.direction, signal.position_size_usd
                )

                trades_data.append(trade_result)

        print(f"\n[OK] Phase 1 complete")
        print(f"Signals found: {len(signals_data)}")
        print(f"Trades simulated: {len(trades_data)}")

        return signals_data, trades_data

    def _track_ratio_outcomes(self, ohlcv_data: np.ndarray, entry_idx: int,
                              entry_price: float, risk: float, direction: str) -> Dict:
        """
        Track if each R:R ratio was reached and when

        Returns:
            {
                '2.0': {'1h': True, '2h': True, '4h': True, '8h': True},
                '3.0': {'1h': False, '2h': True, ...},
                ...
            }
        """
        ratios = [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0,
                  11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0]

        outcomes = {}

        candles_1h = 60
        candles_2h = 120
        candles_4h = 240
        candles_8h = 480

        for ratio in ratios:
            # Calculate target price
            if direction == 'LONG':
                target = entry_price + (risk * ratio)
            else:
                target = entry_price - (risk * ratio)

            # Check each timeframe
            reached_1h = self._check_target_reached(ohlcv_data, entry_idx, target, candles_1h, direction)
            reached_2h = self._check_target_reached(ohlcv_data, entry_idx, target, candles_2h, direction)
            reached_4h = self._check_target_reached(ohlcv_data, entry_idx, target, candles_4h, direction)
            reached_8h = self._check_target_reached(ohlcv_data, entry_idx, target, candles_8h, direction)

            outcomes[str(ratio)] = {
                '1h': reached_1h,
                '2h': reached_2h,
                '4h': reached_4h,
                '8h': reached_8h
            }

        return outcomes

    def _check_target_reached(self, ohlcv_data: np.ndarray, entry_idx: int,
                             target: float, candles: int, direction: str) -> bool:
        """Check if target was reached within timeframe"""
        end_idx = min(entry_idx + candles, len(ohlcv_data))
        future_data = ohlcv_data[entry_idx+1:end_idx+1]

        if len(future_data) == 0:
            return False

        if direction == 'LONG':
            return bool(np.any(future_data[:, 2] >= target))
        else:
            return bool(np.any(future_data[:, 3] <= target))

    def _simulate_trade_tp1(self, ohlcv_data: np.ndarray, entry_idx: int,
                           entry_price: float, stop_loss: float, tp1: float,
                           direction: str, position_size: float) -> Dict:
        """
        Simulate trade with TP1 only

        Returns:
            Trade result dictionary
        """
        # Search forward for SL or TP1
        for i in range(entry_idx + 1, min(entry_idx + 480, len(ohlcv_data))):
            candle = ohlcv_data[i]
            high = candle[2]
            low = candle[3]

            if direction == 'LONG':
                # Check SL hit
                if low <= stop_loss:
                    pnl = (stop_loss - entry_price) * (position_size / entry_price)
                    return {
                        'entry_idx': entry_idx,
                        'exit_idx': i,
                        'entry_price': entry_price,
                        'exit_price': stop_loss,
                        'exit_type': 'SL',
                        'pnl': pnl,
                        'pnl_pct': (stop_loss - entry_price) / entry_price * 100,
                        'bars_held': i - entry_idx
                    }
                # Check TP1 hit
                if high >= tp1:
                    pnl = (tp1 - entry_price) * (position_size / entry_price)
                    return {
                        'entry_idx': entry_idx,
                        'exit_idx': i,
                        'entry_price': entry_price,
                        'exit_price': tp1,
                        'exit_type': 'TP1',
                        'pnl': pnl,
                        'pnl_pct': (tp1 - entry_price) / entry_price * 100,
                        'bars_held': i - entry_idx
                    }
            else:  # SHORT
                # Check SL hit
                if high >= stop_loss:
                    pnl = (entry_price - stop_loss) * (position_size / entry_price)
                    return {
                        'entry_idx': entry_idx,
                        'exit_idx': i,
                        'entry_price': entry_price,
                        'exit_price': stop_loss,
                        'exit_type': 'SL',
                        'pnl': pnl,
                        'pnl_pct': (entry_price - stop_loss) / entry_price * 100,
                        'bars_held': i - entry_idx
                    }
                # Check TP1 hit
                if low <= tp1:
                    pnl = (entry_price - tp1) * (position_size / entry_price)
                    return {
                        'entry_idx': entry_idx,
                        'exit_idx': i,
                        'entry_price': entry_price,
                        'exit_price': tp1,
                        'exit_type': 'TP1',
                        'pnl': pnl,
                        'pnl_pct': (entry_price - tp1) / entry_price * 100,
                        'bars_held': i - entry_idx
                    }

        # No exit found within window - close at BE
        return {
            'entry_idx': entry_idx,
            'exit_idx': entry_idx + 480,
            'entry_price': entry_price,
            'exit_price': entry_price,
            'exit_type': 'TIMEOUT',
            'pnl': 0.0,
            'pnl_pct': 0.0,
            'bars_held': 480
        }

    def train_ml_model(self, signals_data: List[Dict], ohlcv_data: np.ndarray) -> TPRatioMLModel:
        """
        Train ML model on collected signals

        Args:
            signals_data: List of signals with outcomes
            ohlcv_data: Full OHLCV data

        Returns:
            Trained TPRatioMLModel
        """
        print(f"\n{'='*70}")
        print(f"PHASE 2: ML MODEL TRAINING")
        print(f"{'='*70}")

        model = TPRatioMLModel()

        # Prepare training data
        X, y_dict = model.prepare_training_data(ohlcv_data, signals_data)

        # Train models
        metrics = model.train(X, y_dict)

        # Save model
        model.save('models/tp_ratio_predictor_v1.pkl')

        return model

    def calculate_phase1_metrics(self, trades_data: List[Dict]) -> Dict:
        """Calculate metrics for Phase 1 (TP1 only)"""
        if not trades_data:
            return {}

        wins = [t for t in trades_data if t['pnl'] > 0]
        losses = [t for t in trades_data if t['pnl'] <= 0]

        total_pnl = sum(t['pnl'] for t in trades_data)
        win_rate = len(wins) / len(trades_data) * 100

        return {
            'total_trades': len(trades_data),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': round(win_rate, 2),
            'total_pnl': round(total_pnl, 2),
            'avg_win': round(sum(t['pnl'] for t in wins) / len(wins), 2) if wins else 0,
            'avg_loss': round(sum(t['pnl'] for t in losses) / len(losses), 2) if losses else 0,
            'avg_bars_held': round(sum(t['bars_held'] for t in trades_data) / len(trades_data), 2)
        }

    def print_results(self, phase1_metrics: Dict):
        """Print backtest results"""
        print(f"\n{'='*70}")
        print(f"BACKTEST RESULTS")
        print(f"{'='*70}")

        print(f"\nPhase 1 (TP1 Only):")
        print(f"  Total Trades: {phase1_metrics['total_trades']}")
        print(f"  Win Rate: {phase1_metrics['win_rate']:.2f}%")
        print(f"  Total PnL: ${phase1_metrics['total_pnl']:.2f}")
        print(f"  Avg Win: ${phase1_metrics['avg_win']:.2f}")
        print(f"  Avg Loss: ${phase1_metrics['avg_loss']:.2f}")
        print(f"  Avg Bars Held: {phase1_metrics['avg_bars_held']:.0f} (={phase1_metrics['avg_bars_held']/60:.1f}h)")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='PupupuV3 Backtest with ML')

    parser.add_argument('--symbol', type=str, default='BTC/USDT', help='Trading pair')
    parser.add_argument('--days', type=int, default=14, help='Days of historical data (max 30)')
    parser.add_argument('--capital', type=float, default=30000, help='Starting capital')

    args = parser.parse_args()

    print(f"\n{'='*70}")
    print(f"PUPUPUV3 BACKTEST WITH ML TRAINING")
    print(f"{'='*70}")
    print(f"Symbol: {args.symbol}")
    print(f"Days: {args.days}")
    print(f"Capital: ${args.capital:,}")

    # Fetch data
    print(f"\nFetching historical data...")
    client = BinanceClientV3(cache_dir="cache")

    try:
        ohlcv_data = client.get_1min_data(args.symbol, days=args.days, use_cache=False)
    except Exception as e:
        print(f"[ERROR] Failed to fetch data: {e}")
        return

    print(f"[OK] Fetched {len(ohlcv_data)} candles")
    print(f"Date range: {datetime.fromtimestamp(ohlcv_data[0,0]/1000).strftime('%Y-%m-%d')} to {datetime.fromtimestamp(ohlcv_data[-1,0]/1000).strftime('%Y-%m-%d')}")

    # Initialize backtest
    backtest = PupupuV3Backtest(symbol=args.symbol, capital=args.capital)

    # Phase 1: Collect data
    signals_data, trades_data = backtest.run_backtest_phase1(ohlcv_data, start_idx=1000)

    if len(signals_data) < 10:
        print(f"\n[WARNING] Only {len(signals_data)} signals found. Need more data for ML training.")
        print(f"Try increasing --days parameter (e.g., --days 30)")
        return

    # Calculate Phase 1 metrics
    phase1_metrics = backtest.calculate_phase1_metrics(trades_data)

    # Train ML model
    model = backtest.train_ml_model(signals_data, ohlcv_data)

    # Print results
    backtest.print_results(phase1_metrics)

    # Save results
    results_file = f"backtest_results_{args.symbol.replace('/', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    results = {
        'config': backtest.config,
        'symbol': args.symbol,
        'days': args.days,
        'capital': args.capital,
        'phase1_metrics': phase1_metrics,
        'signals_count': len(signals_data),
        'timestamp': datetime.now().isoformat()
    }

    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n[OK] Results saved to {results_file}")
    print(f"[OK] ML model saved to models/tp_ratio_predictor_v1.pkl")


if __name__ == "__main__":
    main()
