"""
Session-based Technical Indicators
Matches TradingView calculations for EMA and VWAP
"""

import numpy as np
from datetime import datetime, timezone


def calculate_ema(prices: np.ndarray, period: int) -> np.ndarray:
    """
    Calculate Exponential Moving Average

    Matches TradingView's ta.ema() function

    Args:
        prices: Array of prices (typically close prices)
        period: EMA period (e.g., 15)

    Returns:
        Array of EMA values (same length as input)
    """
    if len(prices) == 0:
        return np.array([])

    ema = np.zeros(len(prices))
    multiplier = 2.0 / (period + 1)

    # First EMA is simple average of first 'period' values
    if len(prices) >= period:
        ema[period - 1] = np.mean(prices[:period])

        # Calculate EMA for remaining values
        for i in range(period, len(prices)):
            ema[i] = (prices[i] - ema[i - 1]) * multiplier + ema[i - 1]

        # Fill initial values with NaN or first calculated EMA
        for i in range(period - 1):
            ema[i] = ema[period - 1]
    else:
        # Not enough data, use simple average
        ema[:] = np.mean(prices)

    return ema


def calculate_session_vwap(ohlcv_data: np.ndarray, session_start_idx: int = None) -> float:
    """
    Calculate Volume Weighted Average Price for current session

    Matches TradingView's VWAP that resets each session (day)

    Args:
        ohlcv_data: Array with [timestamp, open, high, low, close, volume]
        session_start_idx: Index where current session started (for day reset)

    Returns:
        Current VWAP value
    """
    if len(ohlcv_data) == 0:
        return 0.0

    # If no session start provided, use all data
    if session_start_idx is None:
        session_start_idx = 0

    # Get session data
    session_data = ohlcv_data[session_start_idx:]

    closes = session_data[:, 4]
    volumes = session_data[:, 5]

    # VWAP = sum(close * volume) / sum(volume)
    vwap_sum = np.sum(closes * volumes)
    volume_sum = np.sum(volumes)

    if volume_sum == 0:
        return closes[-1] if len(closes) > 0 else 0.0

    return vwap_sum / volume_sum


def calculate_all_session_vwap(ohlcv_data: np.ndarray, session_start_idx: int = None) -> np.ndarray:
    """
    Calculate cumulative VWAP for each bar in the session

    Args:
        ohlcv_data: Array with [timestamp, open, high, low, close, volume]
        session_start_idx: Index where current session started

    Returns:
        Array of VWAP values for each bar
    """
    if len(ohlcv_data) == 0:
        return np.array([])

    if session_start_idx is None:
        session_start_idx = 0

    session_data = ohlcv_data[session_start_idx:]
    closes = session_data[:, 4]
    volumes = session_data[:, 5]

    vwap_values = np.zeros(len(session_data))
    cumsum_pv = 0.0
    cumsum_vol = 0.0

    for i in range(len(session_data)):
        cumsum_pv += closes[i] * volumes[i]
        cumsum_vol += volumes[i]

        if cumsum_vol > 0:
            vwap_values[i] = cumsum_pv / cumsum_vol
        else:
            vwap_values[i] = closes[i]

    # Create full array with pre-session values
    full_vwap = np.zeros(len(ohlcv_data))
    if session_start_idx > 0:
        full_vwap[:session_start_idx] = ohlcv_data[session_start_idx - 1, 4]
    full_vwap[session_start_idx:] = vwap_values

    return full_vwap


def find_session_start(ohlcv_data: np.ndarray, current_idx: int = None) -> int:
    """
    Find the start of the current session (day change)

    Args:
        ohlcv_data: Array with [timestamp, open, high, low, close, volume]
        current_idx: Current bar index (default: last bar)

    Returns:
        Index where current session started
    """
    if len(ohlcv_data) == 0:
        return 0

    if current_idx is None:
        current_idx = len(ohlcv_data) - 1

    timestamps = ohlcv_data[:current_idx + 1, 0]

    # Convert to datetime
    current_dt = datetime.fromtimestamp(timestamps[current_idx] / 1000, tz=timezone.utc)
    current_day = current_dt.date()

    # Search backwards for day change
    for i in range(current_idx, -1, -1):
        dt = datetime.fromtimestamp(timestamps[i] / 1000, tz=timezone.utc)
        if dt.date() != current_day:
            return i + 1

    return 0


# Test functions
if __name__ == "__main__":
    print("Testing Session Indicators...")

    # Generate test data
    np.random.seed(42)
    num_candles = 200

    timestamps = np.arange(1609459200000, 1609459200000 + num_candles * 60000, 60000)
    closes = 100 + np.cumsum(np.random.randn(num_candles) * 0.5)
    highs = closes + np.abs(np.random.randn(num_candles) * 2)
    lows = closes - np.abs(np.random.randn(num_candles) * 2)
    opens = closes + np.random.randn(num_candles)
    volumes = np.abs(np.random.randn(num_candles) * 10000)

    ohlcv = np.column_stack([timestamps, opens, highs, lows, closes, volumes])

    # Test EMA
    ema_values = calculate_ema(closes, 15)
    print(f"\nEMA 15:")
    print(f"  Last value: {ema_values[-1]:.2f}")
    print(f"  Current price: {closes[-1]:.2f}")

    # Test VWAP
    vwap = calculate_session_vwap(ohlcv, session_start_idx=0)
    print(f"\nVWAP:")
    print(f"  Current value: {vwap:.2f}")
    print(f"  Current price: {closes[-1]:.2f}")

    # Test session start detection
    session_start = find_session_start(ohlcv)
    print(f"\nSession start: Index {session_start}")

    print("\n[OK] Session indicators test complete")
