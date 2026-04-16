"""
Analyze specific historical candle that shows EMA cross in TradingView
"""
import numpy as np
from datetime import datetime, timezone
from src.data.binance_client_v3 import BinanceClientV3
from src.indicators.session_indicators import calculate_ema, calculate_session_vwap, find_session_start
from src.indicators.vwap import get_vwap_position, should_allow_trade
from src.strategy.pupupuv3_signals import PupupuV3Strategy

def analyze_recent_candles(symbol: str = "BTC/USDT", num_candles: int = 30):
    """Analyze last N candles to find EMA crosses"""

    print(f"Analyzing last {num_candles} candles for {symbol}")
    print("="*80)

    # Fetch data
    data_client = BinanceClientV3(cache_dir="cache")
    ohlcv_data = data_client.get_1min_data(symbol, days=1, use_cache=True)

    # Use only last 200 candles for context
    if len(ohlcv_data) > 200:
        ohlcv_data = ohlcv_data[-200:]

    # Calculate EMA
    closes = ohlcv_data[:, 4]
    ema_values = calculate_ema(closes, period=15)

    # Initialize strategy
    config = {
        'ema_period': 15,
        'pivot_lookback': 100,
        'capital_crypto': 30000,
        'risk_per_trade_pct': 0.02,
        'risk_reduced_pct': 0.01,
        'tp1_ratio': 1.0,
        'pivot_touch_threshold': 0.1
    }
    strategy = PupupuV3Strategy(config)

    # Find session start
    session_start = find_session_start(ohlcv_data)

    # Get pivots
    pivot_result = strategy.pivot_detector.detect_pivots(ohlcv_data, session_start_idx=session_start, current_only=False)

    print(f"\nActive Pivots:")
    print(f"  Resistances: {len(pivot_result['resistances'])}")
    for r in pivot_result['resistances'][:3]:
        print(f"    ${r.price:,.2f}")
    print(f"  Supports: {len(pivot_result['supports'])}")
    for s in pivot_result['supports'][:3]:
        print(f"    ${s.price:,.2f}")

    print(f"\n{'='*80}")
    print("CANDLES WITH EMA CROSSES (Last {num_candles} candles):")
    print(f"{'='*80}\n")

    # Analyze last N candles
    start_idx = len(ohlcv_data) - num_candles

    crosses_found = 0

    for i in range(start_idx, len(ohlcv_data)):
        candle = ohlcv_data[i]
        timestamp = int(candle[0])
        open_price = candle[1]
        high_price = candle[2]
        low_price = candle[3]
        close_price = candle[4]

        current_ema = ema_values[i]
        prev_ema = ema_values[i-1] if i > 0 else current_ema
        prev_close = ohlcv_data[i-1, 4] if i > 0 else close_price

        # Check for intra-candle cross
        intra_cross_up = open_price < current_ema and close_price > current_ema
        intra_cross_down = open_price > current_ema and close_price < current_ema

        # Check for inter-candle cross
        inter_cross_up = prev_close <= prev_ema and close_price > current_ema
        inter_cross_down = prev_close >= prev_ema and close_price < current_ema

        if intra_cross_up or intra_cross_down or inter_cross_up or inter_cross_down:
            crosses_found += 1
            dt = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)

            print(f"[{crosses_found}] Time: {dt.strftime('%H:%M:%S')} UTC")
            print(f"    Open:  ${open_price:,.2f}")
            print(f"    Close: ${close_price:,.2f}")
            print(f"    EMA:   ${current_ema:,.2f}")

            if intra_cross_up:
                print(f"    >>> INTRA-CANDLE CROSS UP (LONG)")
                signal_type = "LONG"
            elif intra_cross_down:
                print(f"    >>> INTRA-CANDLE CROSS DOWN (SHORT)")
                signal_type = "SHORT"
            elif inter_cross_up:
                print(f"    >>> INTER-CANDLE CROSS UP (LONG)")
                signal_type = "LONG"
            elif inter_cross_down:
                print(f"    >>> INTER-CANDLE CROSS DOWN (SHORT)")
                signal_type = "SHORT"

            # Check pivot touch
            if signal_type == "LONG":
                nearest_support = strategy.pivot_detector.get_nearest_pivot(close_price, "below")
                if nearest_support:
                    # Check if touched in last 100 candles
                    touched = False
                    for j in range(max(0, i - 100), i):
                        check_candle = ohlcv_data[j]
                        if strategy.pivot_detector.candle_touched_pivot(check_candle, nearest_support):
                            touched = True
                            bars_ago = i - j
                            break

                    print(f"    Nearest Support: ${nearest_support.price:,.2f}")
                    if touched:
                        print(f"    Support Touched: YES ({bars_ago} bars ago)")
                    else:
                        print(f"    Support Touched: NO [SIGNAL BLOCKED]")
                else:
                    print(f"    Nearest Support: NONE [SIGNAL BLOCKED]")

            elif signal_type == "SHORT":
                nearest_resistance = strategy.pivot_detector.get_nearest_pivot(close_price, "above")
                if nearest_resistance:
                    touched = False
                    for j in range(max(0, i - 100), i):
                        check_candle = ohlcv_data[j]
                        if strategy.pivot_detector.candle_touched_pivot(check_candle, nearest_resistance):
                            touched = True
                            bars_ago = i - j
                            break

                    print(f"    Nearest Resistance: ${nearest_resistance.price:,.2f}")
                    if touched:
                        print(f"    Resistance Touched: YES ({bars_ago} bars ago)")
                    else:
                        print(f"    Resistance Touched: NO [SIGNAL BLOCKED]")
                else:
                    print(f"    Nearest Resistance: NONE [SIGNAL BLOCKED]")

            # Check VWAP filter
            current_vwap = calculate_session_vwap(ohlcv_data[:i+1], session_start_idx=min(session_start, i))
            vwap_position = get_vwap_position(close_price, current_vwap)

            ml_confidence = 55.0  # Placeholder
            allow_trade, reason, risk_multiplier = should_allow_trade(
                signal_type,
                vwap_position,
                ml_confidence
            )

            print(f"    VWAP: ${current_vwap:,.2f} (position: {vwap_position['position']}, bias: {vwap_position['directional_bias']})")
            if allow_trade:
                print(f"    VWAP Filter: PASSED (risk: {risk_multiplier*100}%)")
            else:
                print(f"    VWAP Filter: BLOCKED - {reason}")

            print()

    print(f"{'='*80}")
    print(f"Total crosses found: {crosses_found}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    analyze_recent_candles("BTC/USDT", num_candles=30)
