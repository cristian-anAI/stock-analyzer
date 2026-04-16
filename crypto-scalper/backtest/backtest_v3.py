"""
PupupuV3 Complete Backtest - Fases 1, 2 y 3

Fase 1: Backtest con TP1 solo (baseline)
Fase 2: Entrenar ML para predecir TP2/TP3
Fase 3: Backtest con TP2/TP3 dinámicos basados en ML

Compara métricas: TP1 solo vs TP1+TP2+TP3 dinámicos
"""

import sys
import argparse
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import json

sys.path.append(str(Path(__file__).parent))

from src.data.binance_client_v3 import BinanceClientV3
from src.strategy.pupupuv3_signals import PupupuV3Strategy

sys.path.append(str(Path(__file__).parent / 'tools' / 'backtest' / 'box_strategy' / 'ml'))
from tp_ratio_predictor import TPRatioMLModel


class PupupuV3CompleteBacktest:
    """Complete backtesting with 3 phases"""

    def __init__(self, symbol: str = "BTC/USDT", capital: float = 30000):
        self.symbol = symbol
        self.capital = capital

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

    # PHASE 1: TP1 Only
    def phase1_backtest(self, ohlcv_data: np.ndarray, start_idx: int = 1000):
        """Backtest with TP1 only + collect ML training data"""
        print(f"\n{'='*70}")
        print(f"PHASE 1: TP1 ONLY + DATA COLLECTION")
        print(f"{'='*70}")

        signals_data = []
        trades_data = []

        for i in range(start_idx, len(ohlcv_data) - 500):
            if i % 1000 == 0:
                print(f"  Progress: {i}/{len(ohlcv_data)} ({i/len(ohlcv_data)*100:.1f}%)")

            signal = self.strategy.analyze_for_signals(ohlcv_data[:i+1], self.symbol)

            if signal and signal.is_valid:
                # Save signal data
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
                    'ml_confidence': signal.ml_confidence,
                    'outcomes': self._track_outcomes(ohlcv_data, i, signal)
                }
                signals_data.append(signal_data)

                # Simulate trade TP1 only
                trade = self._simulate_tp1_only(ohlcv_data, i, signal)
                trades_data.append(trade)

        print(f"\n[OK] Phase 1: {len(signals_data)} signals, {len(trades_data)} trades")
        return signals_data, trades_data

    def _track_outcomes(self, ohlcv_data, entry_idx, signal):
        """Track if each ratio was reached in each timeframe"""
        ratios = [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0,
                  11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0]

        outcomes = {}
        risk = abs(signal.entry_price - signal.stop_loss)

        for ratio in ratios:
            target = signal.entry_price + (risk * ratio) if signal.direction == 'LONG' else signal.entry_price - (risk * ratio)

            outcomes[str(ratio)] = {
                '1h': self._check_reached(ohlcv_data, entry_idx, target, 60, signal.direction),
                '2h': self._check_reached(ohlcv_data, entry_idx, target, 120, signal.direction),
                '4h': self._check_reached(ohlcv_data, entry_idx, target, 240, signal.direction),
                '8h': self._check_reached(ohlcv_data, entry_idx, target, 480, signal.direction)
            }

        return outcomes

    def _check_reached(self, ohlcv_data, entry_idx, target, candles, direction):
        """Check if target reached within timeframe"""
        end_idx = min(entry_idx + candles, len(ohlcv_data))
        future = ohlcv_data[entry_idx+1:end_idx+1]

        if len(future) == 0:
            return False

        if direction == 'LONG':
            return bool(np.any(future[:, 2] >= target))
        else:
            return bool(np.any(future[:, 3] <= target))

    def _simulate_tp1_only(self, ohlcv_data, entry_idx, signal):
        """Simulate trade with TP1 only"""
        for i in range(entry_idx + 1, min(entry_idx + 480, len(ohlcv_data))):
            high, low = ohlcv_data[i, 2], ohlcv_data[i, 3]

            if signal.direction == 'LONG':
                if low <= signal.stop_loss:
                    pnl = (signal.stop_loss - signal.entry_price) * (signal.position_size_usd / signal.entry_price)
                    return {'pnl': pnl, 'exit_type': 'SL', 'bars': i - entry_idx}

                if high >= signal.take_profit_1:
                    pnl = (signal.take_profit_1 - signal.entry_price) * (signal.position_size_usd / signal.entry_price)
                    return {'pnl': pnl, 'exit_type': 'TP1', 'bars': i - entry_idx}
            else:
                if high >= signal.stop_loss:
                    pnl = (signal.entry_price - signal.stop_loss) * (signal.position_size_usd / signal.entry_price)
                    return {'pnl': pnl, 'exit_type': 'SL', 'bars': i - entry_idx}

                if low <= signal.take_profit_1:
                    pnl = (signal.entry_price - signal.take_profit_1) * (signal.position_size_usd / signal.entry_price)
                    return {'pnl': pnl, 'exit_type': 'TP1', 'bars': i - entry_idx}

        return {'pnl': 0.0, 'exit_type': 'TIMEOUT', 'bars': 480}

    # PHASE 2: Train ML
    def phase2_train_ml(self, signals_data, ohlcv_data):
        """Train ML models"""
        print(f"\n{'='*70}")
        print(f"PHASE 2: ML MODEL TRAINING")
        print(f"{'='*70}")

        model = TPRatioMLModel()
        X, y_dict = model.prepare_training_data(ohlcv_data, signals_data)
        model.train(X, y_dict)
        model.save('models/tp_ratio_predictor_v1.pkl')

        return model

    # PHASE 3: Backtest with dynamic TPs
    def phase3_backtest(self, ohlcv_data, model, start_idx=1000):
        """Backtest with ML-predicted TP2/TP3"""
        print(f"\n{'='*70}")
        print(f"PHASE 3: BACKTEST WITH ML-PREDICTED TP2/TP3")
        print(f"{'='*70}")

        trades_data = []

        for i in range(start_idx, len(ohlcv_data) - 500):
            if i % 1000 == 0:
                print(f"  Progress: {i}/{len(ohlcv_data)} ({i/len(ohlcv_data)*100:.1f}%)")

            signal = self.strategy.analyze_for_signals(ohlcv_data[:i+1], self.symbol)

            if signal and signal.is_valid:
                try:
                    # ML prediction
                    features = model.extract_features(
                        ohlcv_data[:i+1], i, signal.entry_price, signal.stop_loss,
                        signal.direction, signal.pivot_strength,
                        signal.ema_value, signal.vwap_value
                    )

                    prediction = model.predict(features)

                    # Calculate TPs
                    risk = abs(signal.entry_price - signal.stop_loss)
                    tp1 = signal.take_profit_1

                    if signal.direction == 'LONG':
                        tp2 = signal.entry_price + (risk * prediction.tp2_ratio)
                        tp3 = signal.entry_price + (risk * prediction.tp3_ratio)
                    else:
                        tp2 = signal.entry_price - (risk * prediction.tp2_ratio)
                        tp3 = signal.entry_price - (risk * prediction.tp3_ratio)

                    # Simulate with dynamic TPs
                    trade = self._simulate_dynamic_tps(
                        ohlcv_data, i, signal, tp1, tp2, tp3,
                        prediction.tp2_ratio, prediction.tp3_ratio
                    )

                    trades_data.append(trade)

                except:
                    continue

        print(f"\n[OK] Phase 3: {len(trades_data)} trades")
        return trades_data

    def _simulate_dynamic_tps(self, ohlcv_data, entry_idx, signal, tp1, tp2, tp3, tp2_ratio, tp3_ratio):
        """
        Simulate trade with:
        - 50% at TP1, move SL to BE
        - 30% at TP2
        - 20% at TP3
        """
        remaining = 1.0
        total_pnl = 0.0
        exits = []
        sl = signal.stop_loss

        for i in range(entry_idx + 1, min(entry_idx + 480, len(ohlcv_data))):
            high, low = ohlcv_data[i, 2], ohlcv_data[i, 3]

            if signal.direction == 'LONG':
                # SL hit
                if low <= sl:
                    pnl = (sl - signal.entry_price) * (signal.position_size_usd / signal.entry_price) * remaining
                    total_pnl += pnl
                    exits.append({'type': 'SL', 'portion': remaining, 'pnl': pnl})
                    return {'total_pnl': total_pnl, 'exits': exits, 'bars': i - entry_idx,
                            'outcome': 'SL', 'tp2_ratio': tp2_ratio, 'tp3_ratio': tp3_ratio}

                # TP1 (50%)
                if remaining == 1.0 and high >= tp1:
                    pnl = (tp1 - signal.entry_price) * (signal.position_size_usd / signal.entry_price) * 0.5
                    total_pnl += pnl
                    exits.append({'type': 'TP1', 'portion': 0.5, 'pnl': pnl})
                    remaining = 0.5
                    sl = signal.entry_price  # Move to BE

                # TP2 (30%)
                elif remaining == 0.5 and high >= tp2:
                    pnl = (tp2 - signal.entry_price) * (signal.position_size_usd / signal.entry_price) * 0.3
                    total_pnl += pnl
                    exits.append({'type': 'TP2', 'portion': 0.3, 'pnl': pnl})
                    remaining = 0.2

                # TP3 (20%)
                elif remaining == 0.2 and high >= tp3:
                    pnl = (tp3 - signal.entry_price) * (signal.position_size_usd / signal.entry_price) * 0.2
                    total_pnl += pnl
                    exits.append({'type': 'TP3', 'portion': 0.2, 'pnl': pnl})
                    return {'total_pnl': total_pnl, 'exits': exits, 'bars': i - entry_idx,
                            'outcome': 'TP3', 'tp2_ratio': tp2_ratio, 'tp3_ratio': tp3_ratio}

            else:  # SHORT
                if high >= sl:
                    pnl = (signal.entry_price - sl) * (signal.position_size_usd / signal.entry_price) * remaining
                    total_pnl += pnl
                    exits.append({'type': 'SL', 'portion': remaining, 'pnl': pnl})
                    return {'total_pnl': total_pnl, 'exits': exits, 'bars': i - entry_idx,
                            'outcome': 'SL', 'tp2_ratio': tp2_ratio, 'tp3_ratio': tp3_ratio}

                if remaining == 1.0 and low <= tp1:
                    pnl = (signal.entry_price - tp1) * (signal.position_size_usd / signal.entry_price) * 0.5
                    total_pnl += pnl
                    exits.append({'type': 'TP1', 'portion': 0.5, 'pnl': pnl})
                    remaining = 0.5
                    sl = signal.entry_price

                elif remaining == 0.5 and low <= tp2:
                    pnl = (signal.entry_price - tp2) * (signal.position_size_usd / signal.entry_price) * 0.3
                    total_pnl += pnl
                    exits.append({'type': 'TP2', 'portion': 0.3, 'pnl': pnl})
                    remaining = 0.2

                elif remaining == 0.2 and low <= tp3:
                    pnl = (signal.entry_price - tp3) * (signal.position_size_usd / signal.entry_price) * 0.2
                    total_pnl += pnl
                    exits.append({'type': 'TP3', 'portion': 0.2, 'pnl': pnl})
                    return {'total_pnl': total_pnl, 'exits': exits, 'bars': i - entry_idx,
                            'outcome': 'TP3', 'tp2_ratio': tp2_ratio, 'tp3_ratio': tp3_ratio}

        # Timeout
        if remaining > 0:
            exits.append({'type': 'TIMEOUT', 'portion': remaining, 'pnl': 0.0})

        return {'total_pnl': total_pnl, 'exits': exits, 'bars': 480,
                'outcome': 'PARTIAL' if len(exits) > 1 else 'TIMEOUT',
                'tp2_ratio': tp2_ratio, 'tp3_ratio': tp3_ratio}

    # Metrics
    def calculate_metrics(self, trades, label=""):
        """Calculate performance metrics"""
        if not trades:
            return {}

        pnls = [t['pnl'] if 'pnl' in t else t['total_pnl'] for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        return {
            'label': label,
            'total_trades': len(trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': round(len(wins) / len(trades) * 100, 2),
            'total_pnl': round(sum(pnls), 2),
            'avg_win': round(sum(wins) / len(wins), 2) if wins else 0,
            'avg_loss': round(sum(losses) / len(losses), 2) if losses else 0,
            'expectancy': round(sum(pnls) / len(trades), 2),
            'profit_factor': round(abs(sum(wins) / sum(losses)), 2) if losses and sum(losses) != 0 else 0
        }

    def print_comparison(self, metrics1, metrics3):
        """Print comparison between Phase 1 and Phase 3"""
        print(f"\n{'='*70}")
        print(f"COMPARISON: TP1 ONLY vs TP1+TP2+TP3 DYNAMIC")
        print(f"{'='*70}\n")

        print(f"{'Metric':<25} {'Phase 1 (TP1 Only)':<25} {'Phase 3 (Dynamic TPs)':<25}")
        print(f"{'-'*75}")

        metrics = ['total_trades', 'wins', 'losses', 'win_rate', 'total_pnl',
                   'avg_win', 'avg_loss', 'expectancy', 'profit_factor']

        for metric in metrics:
            v1 = metrics1.get(metric, 0)
            v3 = metrics3.get(metric, 0)

            if metric in ['win_rate']:
                print(f"{metric:<25} {v1:>20.2f}% {v3:>25.2f}%")
            elif metric in ['total_pnl', 'avg_win', 'avg_loss', 'expectancy']:
                diff = v3 - v1
                arrow = "UP" if diff > 0 else "DOWN" if diff < 0 else "="
                print(f"{metric:<25} ${v1:>19.2f} ${v3:>20.2f} {arrow} ${abs(diff):.2f}")
            else:
                print(f"{metric:<25} {v1:>24} {v3:>25}")

        # Calculate improvement
        if metrics1.get('total_pnl', 0) != 0:
            improvement = ((metrics3.get('total_pnl', 0) - metrics1.get('total_pnl', 0)) /
                          abs(metrics1.get('total_pnl', 0))) * 100
            print(f"\n{'PnL Improvement:':<25} {improvement:>48.2f}%")


def main():
    parser = argparse.ArgumentParser(description='PupupuV3 Complete Backtest')
    parser.add_argument('--symbol', type=str, default='BTC/USDT')
    parser.add_argument('--days', type=int, default=14)
    parser.add_argument('--capital', type=float, default=30000)

    args = parser.parse_args()

    print(f"\n{'='*70}")
    print(f"PUPUPUV3 COMPLETE BACKTEST (3 PHASES)")
    print(f"{'='*70}")
    print(f"Symbol: {args.symbol}")
    print(f"Days: {args.days}")
    print(f"Capital: ${args.capital:,}\n")

    # Fetch data
    print(f"Fetching data...")
    client = BinanceClientV3(cache_dir="cache")
    ohlcv_data = client.get_1min_data(args.symbol, days=args.days, use_cache=False)
    print(f"[OK] {len(ohlcv_data)} candles")

    # Initialize backtest
    backtest = PupupuV3CompleteBacktest(args.symbol, args.capital)

    # Phase 1
    signals_data, trades_phase1 = backtest.phase1_backtest(ohlcv_data)

    if len(signals_data) < 10:
        print(f"\n[WARNING] Only {len(signals_data)} signals. Need more data.")
        return

    # Phase 2
    model = backtest.phase2_train_ml(signals_data, ohlcv_data)

    # Phase 3
    trades_phase3 = backtest.phase3_backtest(ohlcv_data, model)

    # Calculate metrics
    metrics1 = backtest.calculate_metrics(trades_phase1, "Phase 1")
    metrics3 = backtest.calculate_metrics(trades_phase3, "Phase 3")

    # Print comparison
    backtest.print_comparison(metrics1, metrics3)

    # Save results
    results_file = f"backtest_complete_{args.symbol.replace('/', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    results = {
        'config': backtest.config,
        'symbol': args.symbol,
        'days': args.days,
        'phase1_metrics': metrics1,
        'phase3_metrics': metrics3,
        'signals_count': len(signals_data),
        'timestamp': datetime.now().isoformat()
    }

    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n[OK] Results saved to {results_file}")


if __name__ == "__main__":
    main()
