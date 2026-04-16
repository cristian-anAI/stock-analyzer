"""
Market Context Filters

Filters to avoid trading during unfavorable conditions:
- Major fundamental events (NFP, FOMC, Trump speeches, etc.)
- Low liquidity conditions
- Extreme volatility
- Higher timeframe trend context
"""

import numpy as np
from datetime import datetime, time
from typing import Dict, Optional, Tuple
import warnings


def is_major_fundamental_event(current_time: Optional[datetime] = None) -> Tuple[bool, str]:
    """
    Check if there's a major fundamental event today.

    TODO: Integrate with economic calendar API (Forex Factory, Investing.com)

    Args:
        current_time: Current datetime (default: now)

    Returns:
        (is_event: bool, event_description: str)
    """
    if current_time is None:
        current_time = datetime.now()

    # Placeholder implementation
    # In production, query economic calendar API

    # Example: Avoid Fridays 8:30 AM ET (NFP release time)
    if current_time.weekday() == 4:  # Friday
        if time(8, 15) <= current_time.time() <= time(9, 0):
            return True, "NFP release window (8:30 AM ET Friday)"

    # Example: Avoid FOMC days (2:00 PM ET)
    # TODO: Get actual FOMC schedule from calendar
    if current_time.day in [1, 15]:  # Simplified check
        if time(13, 45) <= current_time.time() <= time(14, 30):
            return True, "Potential FOMC announcement window"

    return False, ""


def check_liquidity(
    candle: Dict,
    min_volume: float = 100.0,
    lookback_avg: Optional[np.ndarray] = None
) -> Tuple[bool, str]:
    """
    Verify minimum liquidity in the candle.

    Args:
        candle: Dict with OHLCV data
        min_volume: Minimum absolute volume
        lookback_avg: Optional array of recent volumes to compare against

    Returns:
        (passes: bool, reason: str)
    """
    volume = candle.get('volume', 0)

    # Check absolute minimum
    if volume < min_volume:
        return False, f"Volume {volume:.2f} below minimum {min_volume}"

    # Check relative to recent average (if provided)
    if lookback_avg is not None and len(lookback_avg) > 0:
        avg_volume = np.mean(lookback_avg)
        if volume < avg_volume * 0.5:  # Less than 50% of average
            return False, f"Volume {volume:.2f} is {(volume/avg_volume)*100:.0f}% of recent average"

    return True, ""


def check_volatility(
    ohlcv_data: np.ndarray,
    lookback_periods: int = 20,
    max_atr_multiplier: float = 2.5
) -> Tuple[bool, str]:
    """
    Check if current volatility is within acceptable range.

    Uses ATR (Average True Range) to measure volatility.

    Args:
        ohlcv_data: Recent OHLCV data
        lookback_periods: Periods for ATR calculation
        max_atr_multiplier: Max acceptable ATR as multiple of average

    Returns:
        (acceptable: bool, reason: str)
    """
    if len(ohlcv_data) < lookback_periods + 1:
        return True, "Insufficient data for volatility check"

    # Calculate True Range for each candle
    highs = ohlcv_data[:, 2]
    lows = ohlcv_data[:, 3]
    closes = ohlcv_data[:, 4]

    true_ranges = []
    for i in range(1, len(ohlcv_data)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        true_ranges.append(tr)

    true_ranges = np.array(true_ranges)

    # Calculate ATR (simple moving average of TR)
    atr = np.mean(true_ranges[-lookback_periods:])
    current_tr = true_ranges[-1]

    # Check if current volatility is excessive
    if current_tr > atr * max_atr_multiplier:
        return False, f"Excessive volatility: current TR {current_tr:.2f} vs ATR {atr:.2f}"

    return True, ""


def get_higher_timeframe_trend(
    ohlcv_1h: np.ndarray,
    ma_period: int = 50
) -> Tuple[str, Dict]:
    """
    Determine trend in higher timeframe (1h or 4h).

    Uses simple MA comparison:
    - Price > MA = bullish
    - Price < MA = bearish
    - Close to MA = neutral

    Args:
        ohlcv_1h: 1-hour OHLCV data
        ma_period: MA period for trend determination

    Returns:
        (trend: "bull"|"bear"|"neutral", details: dict)
    """
    if len(ohlcv_1h) < ma_period:
        return "neutral", {"reason": "Insufficient data"}

    closes = ohlcv_1h[:, 4]
    ma = np.mean(closes[-ma_period:])
    current_price = closes[-1]

    distance_pct = ((current_price - ma) / ma) * 100

    if distance_pct > 1.0:
        trend = "bull"
    elif distance_pct < -1.0:
        trend = "bear"
    else:
        trend = "neutral"

    return trend, {
        'ma_value': ma,
        'current_price': current_price,
        'distance_pct': distance_pct
    }


def apply_all_filters(
    current_candle: Dict,
    ohlcv_5m: np.ndarray,
    ohlcv_1h: Optional[np.ndarray] = None,
    config: Optional[Dict] = None
) -> Dict[str, any]:
    """
    Apply all market context filters.

    Args:
        current_candle: Current 5-min candle
        ohlcv_5m: Recent 5-min OHLCV data
        ohlcv_1h: Optional 1h data for trend context
        config: Optional filter configuration

    Returns:
        {
            'pass_all': bool,
            'fundamental_event': (bool, str),
            'liquidity': (bool, str),
            'volatility': (bool, str),
            'ht_trend': (str, dict)
        }
    """
    if config is None:
        config = {}

    # 1. Fundamental event check
    event_check = is_major_fundamental_event()

    # 2. Liquidity check
    recent_volumes = ohlcv_5m[-20:, 5] if len(ohlcv_5m) >= 20 else None
    liquidity_check = check_liquidity(
        current_candle,
        min_volume=config.get('min_volume', 100.0),
        lookback_avg=recent_volumes
    )

    # 3. Volatility check
    volatility_check = check_volatility(
        ohlcv_5m,
        lookback_periods=config.get('atr_periods', 20),
        max_atr_multiplier=config.get('max_atr_mult', 2.5)
    )

    # 4. Higher timeframe trend (if data available)
    ht_trend = ("neutral", {"reason": "No 1h data"})
    if ohlcv_1h is not None and len(ohlcv_1h) > 0:
        ht_trend = get_higher_timeframe_trend(
            ohlcv_1h,
            ma_period=config.get('ht_ma_period', 50)
        )

    # Determine if all filters pass
    pass_all = (
        not event_check[0] and  # No fundamental event
        liquidity_check[0] and  # Sufficient liquidity
        volatility_check[0]     # Acceptable volatility
    )

    return {
        'pass_all': pass_all,
        'fundamental_event': event_check,
        'liquidity': liquidity_check,
        'volatility': volatility_check,
        'ht_trend': ht_trend
    }


def should_trade_direction(
    signal_direction: str,
    ht_trend: str,
    require_trend_alignment: bool = False
) -> Tuple[bool, str]:
    """
    Check if signal direction aligns with higher timeframe trend.

    Args:
        signal_direction: "LONG" or "SHORT"
        ht_trend: "bull", "bear", or "neutral"
        require_trend_alignment: If True, only trade with the trend

    Returns:
        (should_trade: bool, reason: str)
    """
    if not require_trend_alignment:
        return True, "Trend alignment not required"

    if ht_trend == "neutral":
        return True, "Neutral trend - both directions acceptable"

    if signal_direction == "LONG" and ht_trend == "bull":
        return True, "LONG aligned with bullish trend"

    if signal_direction == "SHORT" and ht_trend == "bear":
        return True, "SHORT aligned with bearish trend"

    return False, f"{signal_direction} against {ht_trend} trend"


# Testing
if __name__ == "__main__":
    print("="*70)
    print("TESTING MARKET CONTEXT FILTERS")
    print("="*70)

    # Test with sample data
    from src.indicators.volume_profile import generate_dummy_ohlcv

    ohlcv_5m = generate_dummy_ohlcv(num_candles=100, base_price=112000)
    current_candle = {
        'timestamp': ohlcv_5m[-1, 0],
        'open': ohlcv_5m[-1, 1],
        'high': ohlcv_5m[-1, 2],
        'low': ohlcv_5m[-1, 3],
        'close': ohlcv_5m[-1, 4],
        'volume': ohlcv_5m[-1, 5]
    }

    print(f"\nCurrent candle:")
    print(f"  Price: ${current_candle['close']:,.2f}")
    print(f"  Volume: {current_candle['volume']:,.0f}")

    # Apply all filters
    results = apply_all_filters(current_candle, ohlcv_5m)

    print(f"\n[FILTER RESULTS]")
    print(f"Pass all filters: {results['pass_all']}")
    print(f"\nFundamental event: {results['fundamental_event'][0]}")
    if results['fundamental_event'][0]:
        print(f"  Event: {results['fundamental_event'][1]}")

    print(f"\nLiquidity check: {results['liquidity'][0]}")
    if not results['liquidity'][0]:
        print(f"  Reason: {results['liquidity'][1]}")

    print(f"\nVolatility check: {results['volatility'][0]}")
    if not results['volatility'][0]:
        print(f"  Reason: {results['volatility'][1]}")

    print(f"\nHigher TF trend: {results['ht_trend'][0]}")
    print(f"  Details: {results['ht_trend'][1]}")

    # Test trend alignment
    print(f"\n[TREND ALIGNMENT]")
    for direction in ["LONG", "SHORT"]:
        should_trade, reason = should_trade_direction(
            direction,
            results['ht_trend'][0],
            require_trend_alignment=True
        )
        print(f"{direction}: {should_trade} - {reason}")

    print("\n" + "="*70)
