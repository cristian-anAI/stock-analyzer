"""
VWAP (Volume Weighted Average Price) Calculator
Used in PupupuV3 strategy for directional bias filtering
"""

import numpy as np
from typing import Dict, Tuple, Optional
from datetime import datetime, time


def calculate_vwap(ohlcv_data: np.ndarray, session_start_idx: int = 0) -> np.ndarray:
    """
    Calculate VWAP from session start

    VWAP = cumulative(typical_price * volume) / cumulative(volume)
    typical_price = (high + low + close) / 3

    Args:
        ohlcv_data: numpy array with columns [timestamp, open, high, low, close, volume]
        session_start_idx: Index where calculation should start (default: 0)

    Returns:
        numpy array with VWAP values for each candle
    """
    if len(ohlcv_data) == 0:
        return np.array([])

    # Extract OHLCV components
    highs = ohlcv_data[:, 2]
    lows = ohlcv_data[:, 3]
    closes = ohlcv_data[:, 4]
    volumes = ohlcv_data[:, 5]

    # Calculate typical price
    typical_price = (highs + lows + closes) / 3.0

    # Initialize VWAP array
    vwap = np.zeros(len(ohlcv_data))

    # Calculate VWAP from session start
    cumulative_tpv = 0.0  # cumulative typical_price * volume
    cumulative_volume = 0.0

    for i in range(len(ohlcv_data)):
        if i < session_start_idx:
            vwap[i] = typical_price[i]  # Before session, use typical price
            continue

        cumulative_tpv += typical_price[i] * volumes[i]
        cumulative_volume += volumes[i]

        if cumulative_volume > 0:
            vwap[i] = cumulative_tpv / cumulative_volume
        else:
            vwap[i] = typical_price[i]

    return vwap


def get_vwap_position(current_price: float, vwap_value: float,
                      threshold_pct: float = 0.05) -> Dict[str, any]:
    """
    Determine price position relative to VWAP

    Args:
        current_price: Current market price
        vwap_value: Current VWAP value
        threshold_pct: Percentage threshold to consider "at" VWAP (default: 0.05%)

    Returns:
        Dictionary with:
        - position: 'above' | 'below' | 'at'
        - distance_pct: Percentage distance from VWAP
        - distance_abs: Absolute distance from VWAP
        - directional_bias: 'bullish' | 'bearish' | 'neutral'
    """
    distance_abs = current_price - vwap_value
    distance_pct = (distance_abs / vwap_value) * 100.0

    # Determine position
    if abs(distance_pct) < threshold_pct:
        position = 'at'
        directional_bias = 'neutral'
    elif distance_abs > 0:
        position = 'above'
        directional_bias = 'bearish'  # Price > VWAP = prefer SHORT
    else:
        position = 'below'
        directional_bias = 'bullish'  # Price < VWAP = prefer LONG

    return {
        'position': position,
        'distance_pct': round(distance_pct, 4),
        'distance_abs': round(distance_abs, 2),
        'directional_bias': directional_bias,
        'vwap_value': round(vwap_value, 2),
        'current_price': round(current_price, 2)
    }


def should_allow_trade(signal_direction: str, vwap_position: Dict[str, any],
                       ml_confidence: float) -> Tuple[bool, str, float]:
    """
    Determine if trade should be allowed based on VWAP filter

    PupupuV3 VWAP Filter Rules (SIMPLIFIED):
    - LONG signals when price < VWAP: ALLOW with full risk (100%)
    - SHORT signals when price > VWAP: ALLOW with full risk (100%)
    - LONG signals when price > VWAP: BLOCK (against bias)
    - SHORT signals when price < VWAP: BLOCK (against bias)

    Logic: Only trade WITH the VWAP bias, never against it.
    - Price below VWAP = bullish bias → only LONG
    - Price above VWAP = bearish bias → only SHORT

    Args:
        signal_direction: 'LONG' or 'SHORT'
        vwap_position: Dictionary from get_vwap_position()
        ml_confidence: ML prediction confidence (0-100) - NOT USED in this version

    Returns:
        Tuple of (allow_trade: bool, reason: str, risk_multiplier: float)
    """
    bias = vwap_position['directional_bias']
    position = vwap_position['position']

    # Neutral position (at VWAP) - allow with full risk
    if bias == 'neutral':
        return True, "Price at VWAP - neutral zone", 1.0

    # LONG signal
    if signal_direction == 'LONG':
        if bias == 'bullish':  # Price < VWAP
            return True, "LONG with VWAP bias (price < VWAP)", 1.0
        else:  # Price > VWAP (against bias) - BLOCK
            return False, "LONG blocked - price above VWAP (bearish bias)", 0.0

    # SHORT signal
    elif signal_direction == 'SHORT':
        if bias == 'bearish':  # Price > VWAP
            return True, "SHORT with VWAP bias (price > VWAP)", 1.0
        else:  # Price < VWAP (against bias) - BLOCK
            return False, "SHORT blocked - price below VWAP (bullish bias)", 0.0

    return False, f"Unknown signal direction: {signal_direction}", 0.0


def find_session_start_index(ohlcv_data: np.ndarray, session_start_hour: int = 0) -> int:
    """
    Find the index where the trading session starts (for session-based VWAP reset)

    For crypto (24/7 markets), typically resets at midnight UTC

    Args:
        ohlcv_data: numpy array with columns [timestamp, open, high, low, close, volume]
        session_start_hour: Hour of day when session starts (0-23, default: 0 for midnight)

    Returns:
        Index of first candle in current session
    """
    if len(ohlcv_data) == 0:
        return 0

    # Get timestamps (in milliseconds)
    timestamps = ohlcv_data[:, 0]

    # Convert to datetime and find last session boundary
    for i in range(len(timestamps) - 1, -1, -1):
        dt = datetime.fromtimestamp(timestamps[i] / 1000)
        if dt.hour == session_start_hour and dt.minute == 0:
            return i

    # If no session boundary found, use beginning
    return 0


def calculate_vwap_with_session_reset(ohlcv_data: np.ndarray,
                                      session_start_hour: int = 0) -> np.ndarray:
    """
    Calculate VWAP with automatic session reset

    Args:
        ohlcv_data: numpy array with columns [timestamp, open, high, low, close, volume]
        session_start_hour: Hour of day when session starts (0-23, default: 0 for midnight)

    Returns:
        numpy array with VWAP values for each candle
    """
    session_start_idx = find_session_start_index(ohlcv_data, session_start_hour)
    return calculate_vwap(ohlcv_data, session_start_idx)


# Test function
if __name__ == "__main__":
    # Test with sample data
    print("Testing VWAP Calculator...")

    # Create sample OHLCV data (timestamp, open, high, low, close, volume)
    sample_data = np.array([
        [1609459200000, 29000, 29100, 28900, 29050, 100],
        [1609459260000, 29050, 29150, 29000, 29100, 150],
        [1609459320000, 29100, 29200, 29050, 29150, 200],
        [1609459380000, 29150, 29180, 29100, 29120, 120],
        [1609459440000, 29120, 29160, 29080, 29140, 180],
    ])

    vwap = calculate_vwap(sample_data)
    print(f"\nVWAP values: {vwap}")

    # Test position detection
    current_price = 29140
    vwap_value = vwap[-1]
    position_info = get_vwap_position(current_price, vwap_value)

    print(f"\nCurrent Price: ${current_price}")
    print(f"Current VWAP: ${vwap_value:.2f}")
    print(f"Position: {position_info['position']}")
    print(f"Distance: {position_info['distance_pct']:.4f}%")
    print(f"Directional Bias: {position_info['directional_bias']}")

    # Test trade allowance
    print("\n=== Trade Allowance Tests ===")

    test_cases = [
        ("LONG", "below", 50.0),  # Should allow with full risk
        ("LONG", "above", 70.0),  # Should allow with reduced risk
        ("LONG", "above", 50.0),  # Should block
        ("SHORT", "above", 50.0), # Should allow with full risk
        ("SHORT", "below", 70.0), # Should allow with reduced risk
        ("SHORT", "below", 50.0), # Should block
    ]

    for direction, pos, ml_conf in test_cases:
        # Create mock vwap_position
        mock_position = {
            'position': pos,
            'directional_bias': 'bullish' if pos == 'below' else 'bearish'
        }

        allow, reason, risk = should_allow_trade(direction, mock_position, ml_conf)

        print(f"\n{direction} signal, price {pos} VWAP, ML: {ml_conf}%")
        print(f"  Allow: {allow}")
        print(f"  Risk Multiplier: {risk}")
        print(f"  Reason: {reason}")

    print("\n[OK] VWAP Calculator tests complete")
