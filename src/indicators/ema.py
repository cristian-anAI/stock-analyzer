"""
Exponential Moving Average (EMA) calculation

Used in pupupuv2 strategy with period=12 on 5-min BTC/USDT
"""

import numpy as np
from typing import Optional, Dict


def calculate_ema(prices: np.ndarray, period: int = 12) -> np.ndarray:
    """
    Calculate Exponential Moving Average.

    Formula: EMA = Price(t) * k + EMA(y) * (1-k)
    where k = 2 / (period + 1)

    Args:
        prices: Array of prices (typically close prices)
        period: EMA period (default: 12)

    Returns:
        Array with EMA values (same length as prices)
        First 'period-1' values are NaN
    """
    if len(prices) < period:
        return np.full_like(prices, np.nan)

    ema = np.full_like(prices, np.nan, dtype=float)
    multiplier = 2.0 / (period + 1)

    # First EMA value = SMA of first 'period' values
    ema[period - 1] = np.mean(prices[:period])

    # Calculate rest iteratively
    for i in range(period, len(prices)):
        ema[i] = (prices[i] - ema[i-1]) * multiplier + ema[i-1]

    return ema


def ema_cross_detection(
    current_close: float,
    previous_close: float,
    ema_value: float,
    current_open: float = None,
    previous_ema: float = None
) -> Optional[str]:
    """
    Detect if price crossed EMA.

    TWO METHODS:
    1. Intra-candle cross (preferred): Check if current candle crosses EMA within the bar
       - LONG: Open < EMA AND Close > EMA (bullish cross within the candle)
       - SHORT: Open > EMA AND Close < EMA (bearish cross within the candle)

    2. Inter-candle cross (fallback): Check if price crossed from previous candle to current
       - LONG: Previous close <= Previous EMA AND Current close > Current EMA
       - SHORT: Previous close >= Previous EMA AND Current close < Current EMA

    Args:
        current_close: Current candle close price
        previous_close: Previous candle close price
        ema_value: Current EMA value
        current_open: Current candle open price (optional, for intra-candle detection)
        previous_ema: Previous EMA value (optional, for more accurate inter-candle detection)

    Returns:
        "cross_below" if crossed below EMA (bearish/SHORT)
        "cross_above" if crossed above EMA (bullish/LONG)
        None if no cross
    """
    # METHOD 1: Intra-candle cross (preferred - catches cross within the minute)
    if current_open is not None:
        # LONG signal: Open below EMA, Close above EMA (crossed up within candle)
        if current_open < ema_value and current_close > ema_value:
            return "cross_above"

        # SHORT signal: Open above EMA, Close below EMA (crossed down within candle)
        if current_open > ema_value and current_close < ema_value:
            return "cross_below"

    # METHOD 2: Inter-candle cross (fallback - uses previous candle close)
    # Use previous EMA if provided, otherwise use current EMA as approximation
    prev_ema = previous_ema if previous_ema is not None else ema_value

    # Bearish cross: previous above/at EMA, current below
    if previous_close >= prev_ema and current_close < ema_value:
        return "cross_below"

    # Bullish cross: previous below/at EMA, current above
    if previous_close <= prev_ema and current_close > ema_value:
        return "cross_above"

    return None


def get_ema_position(price: float, ema_value: float) -> Dict[str, any]:
    """
    Get price position relative to EMA.

    Returns:
        {
            'position': 'above' | 'below',
            'distance_pct': percentage distance from EMA,
            'distance_abs': absolute distance in price units
        }
    """
    distance_abs = price - ema_value
    distance_pct = (distance_abs / ema_value) * 100

    return {
        'position': 'above' if price > ema_value else 'below',
        'distance_pct': abs(distance_pct),
        'distance_abs': abs(distance_abs)
    }


# Testing
if __name__ == "__main__":
    # Test with sample data
    test_prices = np.array([
        100, 102, 101, 103, 105, 104, 106, 107, 105, 108,
        110, 109, 111, 112, 110, 113, 115, 114, 116, 117
    ], dtype=float)

    ema = calculate_ema(test_prices, period=12)

    print("EMA Test:")
    print(f"Prices: {test_prices}")
    print(f"EMA(12): {ema}")
    print(f"\nLast EMA value: {ema[-1]:.2f}")

    # Test cross detection
    cross = ema_cross_detection(test_prices[-1], test_prices[-2], ema[-1])
    print(f"Cross detected: {cross}")
