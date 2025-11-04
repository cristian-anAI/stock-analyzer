"""
Analyze all signals that would have been generated today
Shows limit order prices and timing
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import numpy as np
from datetime import datetime, timedelta
from src.data.binance_client_v3 import BinanceClientV3
from src.strategy.pupupuv3_signals import PupupuV3Strategy, signal_to_dict
from src.indicators.ema import calculate_ema

# Configuration
config = {
    'ema_period': 15,
    'pivot_lookback': 100,
    'capital_crypto': 30000,
    'risk_per_trade_pct': 0.02,
    'risk_reduced_pct': 0.01,
    'tp1_ratio': 1.0,
    'pivot_touch_threshold': 0.1
}

print("="*100)
print("ANALISIS DE SEÑALES DE HOY - BTC/USDT")
print("="*100)

# Fetch today's data
client = BinanceClientV3(cache_dir="cache")
ohlcv_data = client.get_1min_data("BTC/USDT", days=1)  # Last 24 hours

print(f"\nDatos obtenidos: {len(ohlcv_data)} velas (últimas 24 horas)")
print(f"Desde: {datetime.fromtimestamp(ohlcv_data[0, 0]/1000).strftime('%Y-%m-%d %H:%M:%S')} UTC")
print(f"Hasta: {datetime.fromtimestamp(ohlcv_data[-1, 0]/1000).strftime('%Y-%m-%d %H:%M:%S')} UTC")

# Initialize strategy
strategy = PupupuV3Strategy(config)

# Scan through all candles to find signals
signals = []
print("\nEscaneando todas las velas en busca de señales...")

# We need at least 100+ candles for pivots, so get 7 days of data
ohlcv_full = client.get_1min_data("BTC/USDT", days=7)
ema_values_full = calculate_ema(ohlcv_full[:, 4], period=config['ema_period'])

# Find index where "today" starts (last 24 hours)
today_start_time = datetime.now() - timedelta(hours=24)
today_start_timestamp = int(today_start_time.timestamp() * 1000)

# Find the index
today_start_idx = None
for i, candle in enumerate(ohlcv_full):
    if candle[0] >= today_start_timestamp:
        today_start_idx = i
        break

if today_start_idx is None:
    today_start_idx = len(ohlcv_full) - 1440  # Last 1440 candles = 24 hours

print(f"Analizando desde índice {today_start_idx} (últimas {len(ohlcv_full) - today_start_idx} velas)")

# Analyze each candle from today
for i in range(today_start_idx, len(ohlcv_full)):
    # Get data up to this point
    data_up_to_now = ohlcv_full[:i+1]

    # Analyze for signal
    signal = strategy.analyze_for_signals(data_up_to_now, symbol="BTC/USDT")

    if signal and signal.is_valid:
        signals.append(signal)

        # Print immediately when found
        timestamp = signal.timestamp
        dt = datetime.fromtimestamp(timestamp / 1000)
        print(f"\n{'='*100}")
        print(f"SEÑAL #{len(signals)} - {signal.direction}")
        print(f"{'='*100}")
        print(f"Hora del cruce EMA: {dt.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"Precio del cruce: ${signal.entry_price:.2f}")

        # Calculate limit order price (at EMA)
        ema_at_signal = ema_values_full[i]
        print(f"\nPRECIO DE LA LIMIT ORDER: ${ema_at_signal:.2f}")
        print(f"  (Se coloca limit en el EMA)")

        # Show trade details
        print(f"\nDetalles de la trade:")
        print(f"  Entry (limit): ${ema_at_signal:.2f}")
        print(f"  Stop Loss: ${signal.stop_loss:.2f}")
        print(f"  TP1 (1:1): ${signal.take_profit_1:.2f}")
        print(f"  Pivote: ${signal.pivot_price:.2f} ({signal.pivot_type})")

        # Calculate risk/reward
        if signal.direction == "LONG":
            risk = ema_at_signal - signal.stop_loss
            reward = signal.take_profit_1 - ema_at_signal
        else:
            risk = signal.stop_loss - ema_at_signal
            reward = ema_at_signal - signal.take_profit_1

        rr_ratio = reward / risk if risk > 0 else 0
        print(f"\n  Riesgo: ${risk:.2f}")
        print(f"  Reward: ${reward:.2f}")
        print(f"  R:R Ratio: 1:{rr_ratio:.2f}")

        # Now check if limit would have filled
        print(f"\nBUSCANDO ENTRADA DE LA LIMIT...")

        filled = False
        fill_time = None
        fill_candle_idx = None

        # Check next 60 candles (1 hour) to see if limit filled
        max_lookforward = min(60, len(ohlcv_full) - i - 1)

        for j in range(1, max_lookforward + 1):
            future_candle = ohlcv_full[i + j]
            future_high = future_candle[2]
            future_low = future_candle[3]

            # Check if price reached the limit
            if signal.direction == "LONG":
                # LONG: limit fills if price drops to EMA or below
                if future_low <= ema_at_signal:
                    filled = True
                    fill_time = datetime.fromtimestamp(future_candle[0] / 1000)
                    fill_candle_idx = i + j
                    minutes_to_fill = j
                    break
            else:  # SHORT
                # SHORT: limit fills if price rises to EMA or above
                if future_high >= ema_at_signal:
                    filled = True
                    fill_time = datetime.fromtimestamp(future_candle[0] / 1000)
                    fill_candle_idx = i + j
                    minutes_to_fill = j
                    break

        if filled:
            print(f"  [OK] LIMIT ENTRO!")
            print(f"  Hora de entrada: {fill_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print(f"  Tiempo hasta entrada: {minutes_to_fill} minutos")

            # Now check if TP1 or SL hit first
            tp_hit = False
            sl_hit = False
            exit_time = None
            exit_price = None

            for k in range(fill_candle_idx + 1, len(ohlcv_full)):
                candle = ohlcv_full[k]
                high = candle[2]
                low = candle[3]

                if signal.direction == "LONG":
                    if high >= signal.take_profit_1:
                        tp_hit = True
                        exit_time = datetime.fromtimestamp(candle[0] / 1000)
                        exit_price = signal.take_profit_1
                        break
                    elif low <= signal.stop_loss:
                        sl_hit = True
                        exit_time = datetime.fromtimestamp(candle[0] / 1000)
                        exit_price = signal.stop_loss
                        break
                else:  # SHORT
                    if low <= signal.take_profit_1:
                        tp_hit = True
                        exit_time = datetime.fromtimestamp(candle[0] / 1000)
                        exit_price = signal.take_profit_1
                        break
                    elif high >= signal.stop_loss:
                        sl_hit = True
                        exit_time = datetime.fromtimestamp(candle[0] / 1000)
                        exit_price = signal.stop_loss
                        break

            if tp_hit:
                print(f"\n  [WIN] TP1 ALCANZADO!")
                print(f"  Hora de salida: {exit_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                duration = (exit_time - fill_time).total_seconds() / 60
                print(f"  Duracion de la trade: {duration:.0f} minutos")
                print(f"  Resultado: WIN (+${reward:.2f})")
            elif sl_hit:
                print(f"\n  [LOSS] STOP LOSS ALCANZADO")
                print(f"  Hora de salida: {exit_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                duration = (exit_time - fill_time).total_seconds() / 60
                print(f"  Duracion de la trade: {duration:.0f} minutos")
                print(f"  Resultado: LOSS (-${risk:.2f})")
            else:
                print(f"\n  [PENDING] Trade aun activa (no alcanzo TP ni SL)")

        else:
            print(f"  [X] Limit NO entro")
            print(f"  (Precio no volvio al EMA en la siguiente hora)")

        print(f"\nVWAP bias: {signal.vwap_bias}")
        print(f"With VWAP bias: {signal.with_vwap_bias}")
        print(f"Razon: {signal.reason}")

print(f"\n{'='*100}")
print(f"RESUMEN")
print(f"{'='*100}")
print(f"Total señales válidas hoy: {len(signals)}")

if len(signals) > 0:
    print(f"\nDesglose:")
    longs = sum(1 for s in signals if s.direction == "LONG")
    shorts = sum(1 for s in signals if s.direction == "SHORT")
    print(f"  LONG: {longs}")
    print(f"  SHORT: {shorts}")
else:
    print("\nNo se generaron señales válidas en las últimas 24 horas.")

print(f"\n{'='*100}")
