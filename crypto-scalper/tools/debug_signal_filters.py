"""
Debug script to check why signals aren't being generated
Checks all filter conditions for PupupuV3 signals
"""
import numpy as np
from datetime import datetime, timedelta
from src.strategy.pupupuv3_signals import PupupuV3Strategy
from src.data.binance_client_v3 import BinanceClientV3
from src.indicators.session_indicators import calculate_ema, calculate_session_vwap, find_session_start
from src.indicators.vwap import get_vwap_position, should_allow_trade

def debug_current_signal(symbol: str = "BTCUSDT"):
    """Debug why signal isn't being generated"""

    print(f"\n{'='*80}")
    print(f"SIGNAL DEBUG FOR {symbol}")
    print(f"{'='*80}\n")

    # Fetch recent data
    data_client = BinanceClientV3(cache_dir="cache")

    # Get 1-minute data (100 candles = ~1.5 hours)
    # Convert symbol format: BTCUSDT -> BTC/USDT
    symbol_formatted = symbol.replace("USDT", "/USDT")
    print(f"Fetching recent 1-minute data for {symbol_formatted}...")
    ohlcv_data = data_client.get_1min_data(symbol_formatted, days=1, use_cache=True)

    # Use only last 200 candles
    if len(ohlcv_data) > 200:
        ohlcv_data = ohlcv_data[-200:]

    if len(ohlcv_data) == 0:
        print("[ERROR] No data retrieved!")
        return

    print(f"[OK] Retrieved {len(ohlcv_data)} candles\n")

    # Current candle info
    current_candle = ohlcv_data[-1]
    current_time = datetime.fromtimestamp(current_candle[0] / 1000)
    current_close = current_candle[4]

    print(f"Current Time: {current_time}")
    print(f"Current Close: ${current_close:,.2f}\n")

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
    print(f"Session Start Index: {session_start}")
    print(f"Bars in Session: {len(ohlcv_data) - session_start}\n")

    # === PIVOT DETECTION ===
    print(f"{'='*80}")
    print("1. PIVOT DETECTION")
    print(f"{'='*80}")

    pivot_result = strategy.pivot_detector.detect_pivots(
        ohlcv_data,
        session_start_idx=session_start,
        current_only=False  # Show all pivots for debugging
    )

    resistances = pivot_result['resistances']
    supports = pivot_result['supports']

    print(f"Active Resistances: {len(resistances)}")
    for i, r in enumerate(resistances):
        print(f"  R{i+1}: ${r.price:,.2f} (strength: {r.strength}, touches: {r.touches}, bars_since: {r.bars_since_formation})")

    print(f"\nActive Supports: {len(supports)}")
    for i, s in enumerate(supports):
        print(f"  S{i+1}: ${s.price:,.2f} (strength: {s.strength}, touches: {s.touches}, bars_since: {s.bars_since_formation})")

    # === EMA CROSS DETECTION ===
    print(f"\n{'='*80}")
    print("2. EMA 15 CROSS DETECTION")
    print(f"{'='*80}")

    closes = ohlcv_data[:, 4]
    ema15 = calculate_ema(closes, 15)

    current_ema = ema15[-1]
    current_open = ohlcv_data[-1, 1]
    prev_close = ohlcv_data[-2, 4]
    prev_ema = ema15[-2]

    print(f"Current Open:  ${current_open:,.2f}")
    print(f"Current Close: ${current_close:,.2f}")
    print(f"Current EMA15: ${current_ema:,.2f}")
    print(f"Previous Close: ${prev_close:,.2f}")
    print(f"Previous EMA15: ${prev_ema:,.2f}")
    print()

    # Check INTRA-CANDLE cross (preferred method)
    intra_cross_above = current_open < current_ema and current_close > current_ema
    intra_cross_below = current_open > current_ema and current_close < current_ema

    # Check INTER-CANDLE cross (fallback method)
    inter_cross_above = prev_close <= prev_ema and current_close > current_ema
    inter_cross_below = prev_close >= prev_ema and current_close < current_ema

    cross_above = intra_cross_above or inter_cross_above
    cross_below = intra_cross_below or inter_cross_below

    if intra_cross_above:
        print(f"[OK] INTRA-CANDLE CROSS ABOVE DETECTED (Bullish)")
        print(f"     Open ${current_open:,.2f} < EMA ${current_ema:,.2f} < Close ${current_close:,.2f}")
    elif inter_cross_above:
        print(f"[OK] INTER-CANDLE CROSS ABOVE DETECTED (Bullish)")
        print(f"     Previous close ${prev_close:,.2f} <= EMA, Current close ${current_close:,.2f} > EMA")
    elif intra_cross_below:
        print(f"[OK] INTRA-CANDLE CROSS BELOW DETECTED (Bearish)")
        print(f"     Open ${current_open:,.2f} > EMA ${current_ema:,.2f} > Close ${current_close:,.2f}")
    elif inter_cross_below:
        print(f"[OK] INTER-CANDLE CROSS BELOW DETECTED (Bearish)")
        print(f"     Previous close ${prev_close:,.2f} >= EMA, Current close ${current_close:,.2f} < EMA")
    else:
        print(f"[X] NO CROSS DETECTED")
        if current_close > current_ema:
            print(f"   Price is {((current_close/current_ema - 1) * 100):.2f}% above EMA")
        else:
            print(f"   Price is {((1 - current_close/current_ema) * 100):.2f}% below EMA")

    # === PIVOT TOUCH DETECTION ===
    print(f"\n{'='*80}")
    print("3. PIVOT TOUCH DETECTION")
    print(f"{'='*80}")

    lookback_for_touch = strategy.pivot_lookback  # 100 candles
    print(f"Checking last {lookback_for_touch} candles for pivot touches...\n")

    if cross_above:
        # Check support touch for LONG
        nearest_support = strategy.pivot_detector.get_nearest_pivot(current_close, "below")
        if nearest_support:
            print(f"Nearest Support Below: ${nearest_support.price:,.2f}")

            touched = False
            touch_bar = None
            for i in range(1, min(lookback_for_touch + 1, len(ohlcv_data))):
                candle = ohlcv_data[-i]
                if strategy.pivot_detector.candle_touched_pivot(candle, nearest_support):
                    touched = True
                    touch_bar = i
                    touch_time = datetime.fromtimestamp(candle[0] / 1000)
                    break

            if touched:
                print(f"[OK] SUPPORT TOUCHED {touch_bar} bars ago at {touch_time}")
            else:
                print(f"[X] SUPPORT NOT TOUCHED in last {lookback_for_touch} candles")
        else:
            print(f"[X] NO SUPPORT FOUND BELOW PRICE")

    elif cross_below:
        # Check resistance touch for SHORT
        nearest_resistance = strategy.pivot_detector.get_nearest_pivot(current_close, "above")
        if nearest_resistance:
            print(f"Nearest Resistance Above: ${nearest_resistance.price:,.2f}")

            touched = False
            touch_bar = None
            for i in range(1, min(lookback_for_touch + 1, len(ohlcv_data))):
                candle = ohlcv_data[-i]
                if strategy.pivot_detector.candle_touched_pivot(candle, nearest_resistance):
                    touched = True
                    touch_bar = i
                    touch_time = datetime.fromtimestamp(candle[0] / 1000)
                    break

            if touched:
                print(f"[OK] RESISTANCE TOUCHED {touch_bar} bars ago at {touch_time}")
            else:
                print(f"[X] RESISTANCE NOT TOUCHED in last {lookback_for_touch} candles")
        else:
            print(f"[X] NO RESISTANCE FOUND ABOVE PRICE")

    # === VWAP FILTER ===
    print(f"\n{'='*80}")
    print("4. VWAP FILTER")
    print(f"{'='*80}")

    session_vwap = calculate_session_vwap(ohlcv_data, session_start)
    print(f"Session VWAP: ${session_vwap:,.2f}")
    print(f"Current Price: ${current_close:,.2f}")

    vwap_position = get_vwap_position(current_close, session_vwap)
    print(f"VWAP Position: {vwap_position['position']} (bias: {vwap_position['directional_bias']})")
    print(f"Distance from VWAP: {vwap_position['distance_pct']:.2f}%")

    # === ML CONFIDENCE (Mock for now) ===
    print(f"\n{'='*80}")
    print("5. ML CONFIDENCE")
    print(f"{'='*80}")

    # In real system, this comes from ML predictor
    # For now, use a placeholder
    ml_confidence = 55.0  # Placeholder
    print(f"ML Confidence: {ml_confidence}%")
    print(f"(Note: This is a placeholder - real ML predictor not integrated yet)")

    # === FINAL FILTER CHECK ===
    print(f"\n{'='*80}")
    print("6. FINAL FILTER CHECK")
    print(f"{'='*80}")

    if cross_above:
        signal_direction = "LONG"
    elif cross_below:
        signal_direction = "SHORT"
    else:
        signal_direction = None

    if signal_direction:
        allow_trade, reason, risk_multiplier = should_allow_trade(
            signal_direction,
            vwap_position,
            ml_confidence
        )

        print(f"\nSignal Direction: {signal_direction}")
        print(f"Trade Allowed: {'[OK] YES' if allow_trade else '[X] NO'}")
        print(f"Reason: {reason}")
        print(f"Risk Multiplier: {risk_multiplier * 100}%")

        if not allow_trade:
            print(f"\n[WARNING] SIGNAL BLOCKED BY VWAP FILTER")
            print(f"   To allow this trade, either:")
            print(f"   1. Wait for price to align with VWAP bias")
            print(f"   2. ML confidence must be > 60% (currently {ml_confidence}%)")

    # === SUMMARY ===
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")

    checks = []
    checks.append(("EMA Cross", cross_above or cross_below))

    if cross_above and nearest_support:
        checks.append(("Support Touch", touched))
    elif cross_below and nearest_resistance:
        checks.append(("Resistance Touch", touched))

    if signal_direction:
        checks.append(("VWAP Filter", allow_trade))

    print(f"\nFilter Checklist:")
    for check_name, passed in checks:
        status = "[OK]" if passed else "[X]"
        print(f"  {status} {check_name}")

    all_passed = all(passed for _, passed in checks)

    if all_passed:
        print(f"\n[SUCCESS] ALL FILTERS PASSED - SIGNAL SHOULD BE GENERATED")
    else:
        print(f"\n[FAILED] SOME FILTERS FAILED - NO SIGNAL GENERATED")
        failed = [name for name, passed in checks if not passed]
        print(f"   Failed filters: {', '.join(failed)}")

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    debug_current_signal("BTCUSDT")
