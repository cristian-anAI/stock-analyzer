"""
Get summary of today's signals - SHORT VERSION
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import numpy as np
from datetime import datetime, timedelta
from src.data.binance_client_v3 import BinanceClientV3
from src.strategy.pupupuv3_signals import PupupuV3Strategy
from src.indicators.ema import calculate_ema

config = {
    'ema_period': 15,
    'pivot_lookback': 100,
    'capital_crypto': 30000,
    'risk_per_trade_pct': 0.02,
    'risk_reduced_pct': 0.01,
    'tp1_ratio': 1.0,
    'pivot_touch_threshold': 0.1
}

print("="*120)
print("RESUMEN DE SEÑALES HOY - BTC/USDT")
print("="*120)

client = BinanceClientV3(cache_dir="cache")
ohlcv_full = client.get_1min_data("BTC/USDT", days=7)
ema_values_full = calculate_ema(ohlcv_full[:, 4], period=config['ema_period'])

today_start_time = datetime.now() - timedelta(hours=24)
today_start_timestamp = int(today_start_time.timestamp() * 1000)

today_start_idx = None
for i, candle in enumerate(ohlcv_full):
    if candle[0] >= today_start_timestamp:
        today_start_idx = i
        break

if today_start_idx is None:
    today_start_idx = len(ohlcv_full) - 1440

strategy = PupupuV3Strategy(config)
results = []

print("\nAnalizando señales...")

for i in range(today_start_idx, len(ohlcv_full)):
    data_up_to_now = ohlcv_full[:i+1]
    signal = strategy.analyze_for_signals(data_up_to_now, symbol="BTC/USDT")

    if signal and signal.is_valid:
        timestamp = signal.timestamp
        dt = datetime.fromtimestamp(timestamp / 1000)
        ema_at_signal = ema_values_full[i]

        # Calculate risk/reward
        if signal.direction == "LONG":
            risk = ema_at_signal - signal.stop_loss
            reward = signal.take_profit_1 - ema_at_signal
        else:
            risk = signal.stop_loss - ema_at_signal
            reward = ema_at_signal - signal.take_profit_1

        # Check if limit filled
        filled = False
        fill_time = None
        minutes_to_fill = 0

        max_lookforward = min(60, len(ohlcv_full) - i - 1)
        for j in range(1, max_lookforward + 1):
            future_candle = ohlcv_full[i + j]
            future_high = future_candle[2]
            future_low = future_candle[3]

            if signal.direction == "LONG":
                if future_low <= ema_at_signal:
                    filled = True
                    fill_time = datetime.fromtimestamp(future_candle[0] / 1000)
                    minutes_to_fill = j
                    break
            else:
                if future_high >= ema_at_signal:
                    filled = True
                    fill_time = datetime.fromtimestamp(future_candle[0] / 1000)
                    minutes_to_fill = j
                    break

        # Check TP/SL if filled
        result = "NO_FILL"
        pnl = 0

        if filled:
            fill_candle_idx = i + minutes_to_fill
            for k in range(fill_candle_idx + 1, len(ohlcv_full)):
                candle = ohlcv_full[k]
                high = candle[2]
                low = candle[3]

                if signal.direction == "LONG":
                    if high >= signal.take_profit_1:
                        result = "WIN"
                        pnl = reward
                        break
                    elif low <= signal.stop_loss:
                        result = "LOSS"
                        pnl = -risk
                        break
                else:
                    if low <= signal.take_profit_1:
                        result = "WIN"
                        pnl = reward
                        break
                    elif high >= signal.stop_loss:
                        result = "LOSS"
                        pnl = -risk
                        break

        results.append({
            'time': dt,
            'direction': signal.direction,
            'limit_price': ema_at_signal,
            'entry_price': signal.entry_price,
            'sl': signal.stop_loss,
            'tp1': signal.take_profit_1,
            'filled': filled,
            'fill_time': fill_time,
            'minutes_to_fill': minutes_to_fill,
            'result': result,
            'pnl': pnl,
            'risk': risk,
            'reward': reward
        })

print(f"\nTotal señales válidas: {len(results)}")
print("\n" + "="*120)
print(f"{'#':<4} {'HORA':<20} {'DIR':<6} {'LIMIT PRICE':<15} {'SL':<15} {'TP1':<15} {'FILL?':<8} {'MINS':<6} {'RESULTADO':<12} {'PnL':<12}")
print("="*120)

for i, r in enumerate(results, 1):
    fill_str = "SI" if r['filled'] else "NO"
    fill_time_str = r['fill_time'].strftime('%H:%M') if r['filled'] else "-"

    print(f"{i:<4} {r['time'].strftime('%Y-%m-%d %H:%M'):<20} {r['direction']:<6} ${r['limit_price']:<14.2f} ${r['sl']:<14.2f} ${r['tp1']:<14.2f} {fill_str:<8} {r['minutes_to_fill']:<6} {r['result']:<12} ${r['pnl']:<11.2f}")

print("="*120)

# Calculate stats
total_trades = len(results)
filled_trades = [r for r in results if r['filled']]
wins = [r for r in results if r['result'] == 'WIN']
losses = [r for r in results if r['result'] == 'LOSS']
no_fills = [r for r in results if not r['filled']]

total_pnl = sum(r['pnl'] for r in results)
win_rate = (len(wins) / len(filled_trades) * 100) if filled_trades else 0

print(f"\nESTADISTICAS:")
print(f"  Total señales: {total_trades}")
print(f"  Limits que entraron: {len(filled_trades)} ({len(filled_trades)/total_trades*100:.1f}%)")
print(f"  Limits que NO entraron: {len(no_fills)} ({len(no_fills)/total_trades*100:.1f}%)")
print(f"  Wins: {len(wins)}")
print(f"  Losses: {len(losses)}")
print(f"  Win rate: {win_rate:.1f}%")
print(f"  PnL total (simulado): ${total_pnl:.2f}")

longs = [r for r in results if r['direction'] == 'LONG']
shorts = [r for r in results if r['direction'] == 'SHORT']
print(f"\n  LONG señales: {len(longs)}")
print(f"  SHORT señales: {len(shorts)}")

print("="*120)
