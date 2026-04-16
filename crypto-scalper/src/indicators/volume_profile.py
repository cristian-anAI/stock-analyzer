"""
Volume Profile V3 for PupupuV3 Strategy
Simplified version that only calculates 7-day Volume Profile (macro context)

Changes from V2:
- Only calculates vp_largo (7 days)
- Removed vp_corto (4h) and vp_medio (24h)
- Optimized for 1-minute timeframe
- Focused on macro-level supply/demand zones
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import warnings


@dataclass
class VolumeProfileResult:
    """Container for Volume Profile calculation results"""
    price_levels: np.ndarray      # Array of price bins
    volume_distribution: np.ndarray  # Volume at each price level
    poc: float                     # Point of Control
    vah: float                     # Value Area High
    val: float                     # Value Area Low
    hvn: List[float]              # High Volume Nodes
    lvn: List[float]              # Low Volume Nodes
    total_volume: float           # Total volume in period
    price_range: Tuple[float, float]  # (min_price, max_price)


def calculate_volume_profile(
    ohlcv_data: np.ndarray,
    num_bins: int = 60
) -> VolumeProfileResult:
    """
    Calculate Volume Profile from OHLCV data.

    For 1-min data with 7-day lookback, 60 bins provides good balance.

    Args:
        ohlcv_data: Array shaped (n_candles, 6) with columns:
                   [timestamp, open, high, low, close, volume]
        num_bins: Number of price levels to divide range into (default: 60)

    Returns:
        VolumeProfileResult with complete VP data

    Raises:
        ValueError: If data is invalid or insufficient
    """
    if len(ohlcv_data) < 10:
        raise ValueError(f"Insufficient data: need at least 10 candles, got {len(ohlcv_data)}")

    # Extract OHLCV columns
    opens = ohlcv_data[:, 1]
    highs = ohlcv_data[:, 2]
    lows = ohlcv_data[:, 3]
    closes = ohlcv_data[:, 4]
    volumes = ohlcv_data[:, 5]

    # Validate data
    if np.any(volumes < 0):
        raise ValueError("Negative volumes detected in data")
    if np.any(highs < lows):
        raise ValueError("Invalid OHLC: high < low detected")

    # Define price range and bins
    min_price = np.min(lows)
    max_price = np.max(highs)
    price_range = max_price - min_price

    if price_range == 0:
        raise ValueError("No price movement in data (flat line)")

    # Create price bins (bin edges)
    bin_edges = np.linspace(min_price, max_price, num_bins + 1)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    volume_at_price = np.zeros(num_bins)

    # Distribute volume across price levels for each candle
    for i in range(len(ohlcv_data)):
        candle_low = lows[i]
        candle_high = highs[i]
        candle_volume = volumes[i]

        if candle_high == candle_low:
            # Single price - all volume goes to one bin
            bin_idx = np.searchsorted(bin_edges[1:], candle_low)
            bin_idx = min(bin_idx, num_bins - 1)
            volume_at_price[bin_idx] += candle_volume
        else:
            # Distribute volume proportionally across bins within candle range
            low_bin_idx = np.searchsorted(bin_edges[1:], candle_low)
            high_bin_idx = np.searchsorted(bin_edges, candle_high)
            high_bin_idx = min(high_bin_idx, num_bins)

            # Calculate overlap for each bin and distribute volume
            for bin_idx in range(low_bin_idx, high_bin_idx):
                bin_low = bin_edges[bin_idx]
                bin_high = bin_edges[bin_idx + 1]

                # Calculate overlap between candle and bin
                overlap_low = max(candle_low, bin_low)
                overlap_high = min(candle_high, bin_high)
                overlap_range = max(0, overlap_high - overlap_low)

                # Volume proportion based on price overlap
                candle_range = candle_high - candle_low
                volume_fraction = overlap_range / candle_range
                volume_at_price[bin_idx] += candle_volume * volume_fraction

    # Find key nodes
    poc = find_poc(bin_centers, volume_at_price)
    vah, val = find_value_area(bin_centers, volume_at_price, percentage=0.70)
    hvn = find_hvn_nodes(bin_centers, volume_at_price, num_nodes=5, min_distance_pct=0.5)
    lvn = find_lvn_nodes(bin_centers, volume_at_price, hvn_list=hvn, num_nodes=3)

    return VolumeProfileResult(
        price_levels=bin_centers,
        volume_distribution=volume_at_price,
        poc=poc,
        vah=vah,
        val=val,
        hvn=hvn,
        lvn=lvn,
        total_volume=np.sum(volumes),
        price_range=(min_price, max_price)
    )


def find_poc(price_levels: np.ndarray, volume_distribution: np.ndarray) -> float:
    """Find Point of Control (price level with highest volume)"""
    if len(volume_distribution) == 0:
        raise ValueError("Empty volume distribution")

    poc_idx = np.argmax(volume_distribution)
    return float(price_levels[poc_idx])


def find_value_area(
    price_levels: np.ndarray,
    volume_distribution: np.ndarray,
    percentage: float = 0.70
) -> Tuple[float, float]:
    """
    Find Value Area High (VAH) and Value Area Low (VAL).
    Value Area contains 70% of total volume, starting from POC.
    """
    total_volume = np.sum(volume_distribution)
    target_volume = total_volume * percentage

    # Start from POC
    poc_idx = np.argmax(volume_distribution)

    # Expand outward from POC to capture target volume
    accumulated_volume = volume_distribution[poc_idx]
    low_idx = poc_idx
    high_idx = poc_idx

    while accumulated_volume < target_volume:
        # Check volume above and below
        vol_above = volume_distribution[high_idx + 1] if high_idx + 1 < len(volume_distribution) else 0
        vol_below = volume_distribution[low_idx - 1] if low_idx > 0 else 0

        # Expand toward higher volume
        if vol_above >= vol_below and high_idx + 1 < len(volume_distribution):
            high_idx += 1
            accumulated_volume += volume_distribution[high_idx]
        elif low_idx > 0:
            low_idx -= 1
            accumulated_volume += volume_distribution[low_idx]
        else:
            break

    vah = float(price_levels[high_idx])
    val = float(price_levels[low_idx])

    if vah < val:
        vah, val = val, vah

    return vah, val


def find_hvn_nodes(
    price_levels: np.ndarray,
    volume_distribution: np.ndarray,
    num_nodes: int = 5,
    min_distance_pct: float = 0.5
) -> List[float]:
    """
    Find High Volume Nodes (significant volume peaks)
    These act as "magnets" where price tends to gravitate
    """
    if len(volume_distribution) < 3:
        return [find_poc(price_levels, volume_distribution)]

    price_range = price_levels[-1] - price_levels[0]
    min_distance = price_range * (min_distance_pct / 100.0)

    # Find local maxima (peaks)
    peaks = []
    for i in range(1, len(volume_distribution) - 1):
        if (volume_distribution[i] > volume_distribution[i-1] and
            volume_distribution[i] > volume_distribution[i+1]):
            peaks.append((i, volume_distribution[i]))

    if not peaks:
        return [find_poc(price_levels, volume_distribution)]

    # Sort peaks by volume (descending)
    peaks.sort(key=lambda x: x[1], reverse=True)

    # Filter by minimum distance
    selected_hvn = []
    for peak_idx, peak_vol in peaks:
        peak_price = price_levels[peak_idx]

        # Check distance from already selected HVNs
        too_close = False
        for selected_price in selected_hvn:
            if abs(peak_price - selected_price) < min_distance:
                too_close = True
                break

        if not too_close:
            selected_hvn.append(peak_price)

        if len(selected_hvn) >= num_nodes:
            break

    # Sort by volume for final output
    selected_hvn_with_vol = []
    for price in selected_hvn:
        idx = np.argmin(np.abs(price_levels - price))
        selected_hvn_with_vol.append((price, volume_distribution[idx]))

    selected_hvn_with_vol.sort(key=lambda x: x[1], reverse=True)

    return [price for price, vol in selected_hvn_with_vol]


def find_lvn_nodes(
    price_levels: np.ndarray,
    volume_distribution: np.ndarray,
    hvn_list: List[float],
    num_nodes: int = 3
) -> List[float]:
    """
    Find Low Volume Nodes (volume valleys between HVNs)
    These are "thin zones" where price can move quickly
    """
    if len(volume_distribution) < 3 or len(hvn_list) < 2:
        return []

    # Find local minima (valleys)
    valleys = []
    for i in range(1, len(volume_distribution) - 1):
        if (volume_distribution[i] < volume_distribution[i-1] and
            volume_distribution[i] < volume_distribution[i+1]):
            valleys.append((i, volume_distribution[i]))

    if not valleys:
        return []

    # Sort valleys by volume (ascending)
    valleys.sort(key=lambda x: x[1])

    # Filter: only keep valleys between HVNs
    hvn_sorted = sorted(hvn_list)
    selected_lvn = []

    for valley_idx, valley_vol in valleys:
        valley_price = price_levels[valley_idx]

        # Check if valley is between two HVNs
        is_between_hvns = False
        for i in range(len(hvn_sorted) - 1):
            if hvn_sorted[i] < valley_price < hvn_sorted[i+1]:
                is_between_hvns = True
                break

        if is_between_hvns:
            selected_lvn.append(valley_price)

        if len(selected_lvn) >= num_nodes:
            break

    return selected_lvn


def get_7d_volume_profile(
    ohlcv_data_1min: np.ndarray,
    num_bins: int = 60
) -> Optional[Dict]:
    """
    Calculate 7-day Volume Profile for PupupuV3 strategy

    Args:
        ohlcv_data_1min: Full array of 1-min OHLCV data (oldest to newest)
        num_bins: Number of price bins for VP calculation (default: 60)

    Returns:
        Dictionary with VP data or None if insufficient data

    Required data:
        - 7 days = 168 hours = 10,080 minutes = 10,080 candles
    """
    required_candles = 10080  # 7 days of 1-min candles
    total_candles = len(ohlcv_data_1min)

    if total_candles < required_candles:
        warnings.warn(
            f"Insufficient data for 7-day VP: need {required_candles} candles, "
            f"have {total_candles}. Using all available data."
        )
        vp_data = ohlcv_data_1min
    else:
        # Take most recent 7 days
        vp_data = ohlcv_data_1min[-required_candles:]

    try:
        vp = calculate_volume_profile(vp_data, num_bins=num_bins)

        return {
            'poc': vp.poc,
            'vah': vp.vah,
            'val': vp.val,
            'hvn': vp.hvn,
            'lvn': vp.lvn,
            'price_levels': vp.price_levels.tolist(),
            'volume_distribution': vp.volume_distribution.tolist(),
            'total_volume': vp.total_volume,
            'price_range': vp.price_range,
            'num_candles': len(vp_data),
            'days_covered': len(vp_data) / 1440  # 1440 = candles per day
        }
    except ValueError as e:
        warnings.warn(f"Error calculating 7-day VP: {str(e)}")
        return None


def is_near_hvn(current_price: float, hvn_list: List[float],
                threshold_pct: float = 0.5) -> Tuple[bool, Optional[float]]:
    """
    Check if current price is near any High Volume Node

    Args:
        current_price: Current market price
        hvn_list: List of HVN prices
        threshold_pct: Distance threshold as % of price (default: 0.5%)

    Returns:
        Tuple of (is_near: bool, nearest_hvn: float or None)
    """
    if not hvn_list:
        return False, None

    for hvn_price in hvn_list:
        distance_pct = abs(current_price - hvn_price) / hvn_price * 100
        if distance_pct <= threshold_pct:
            return True, hvn_price

    return False, None


def is_near_lvn(current_price: float, lvn_list: List[float],
                threshold_pct: float = 0.3) -> Tuple[bool, Optional[float]]:
    """
    Check if current price is near any Low Volume Node

    Args:
        current_price: Current market price
        lvn_list: List of LVN prices
        threshold_pct: Distance threshold as % of price (default: 0.3%)

    Returns:
        Tuple of (is_near: bool, nearest_lvn: float or None)
    """
    if not lvn_list:
        return False, None

    for lvn_price in lvn_list:
        distance_pct = abs(current_price - lvn_price) / lvn_price * 100
        if distance_pct <= threshold_pct:
            return True, lvn_price

    return False, None


def get_vp_context(current_price: float, vp_data: Dict) -> Dict:
    """
    Get Volume Profile context for current price

    Args:
        current_price: Current market price
        vp_data: Dictionary from get_7d_volume_profile()

    Returns:
        Dictionary with:
        - position_vs_poc: 'above' | 'below' | 'at'
        - in_value_area: bool
        - near_hvn: bool
        - near_lvn: bool
        - nearest_hvn: float or None
        - nearest_lvn: float or None
    """
    if vp_data is None:
        return {
            'position_vs_poc': 'unknown',
            'in_value_area': False,
            'near_hvn': False,
            'near_lvn': False,
            'nearest_hvn': None,
            'nearest_lvn': None
        }

    poc = vp_data['poc']
    vah = vp_data['vah']
    val = vp_data['val']

    # Position vs POC
    if abs(current_price - poc) / poc * 100 < 0.1:
        position_vs_poc = 'at'
    elif current_price > poc:
        position_vs_poc = 'above'
    else:
        position_vs_poc = 'below'

    # In value area?
    in_value_area = val <= current_price <= vah

    # Near HVN or LVN?
    near_hvn, nearest_hvn = is_near_hvn(current_price, vp_data['hvn'])
    near_lvn, nearest_lvn = is_near_lvn(current_price, vp_data['lvn'])

    return {
        'position_vs_poc': position_vs_poc,
        'in_value_area': in_value_area,
        'near_hvn': near_hvn,
        'near_lvn': near_lvn,
        'nearest_hvn': nearest_hvn,
        'nearest_lvn': nearest_lvn,
        'poc': poc,
        'vah': vah,
        'val': val
    }


# Test function
if __name__ == "__main__":
    print("Testing Volume Profile V3 (7-day only)...")

    # Generate test data (10,080 candles = 7 days of 1-min data)
    np.random.seed(42)
    num_candles = 10080

    timestamps = np.arange(1609459200000, 1609459200000 + num_candles * 60000, 60000)

    # Generate realistic price pattern
    base_price = 43000
    trend = np.linspace(0, 1000, num_candles)
    noise = np.cumsum(np.random.randn(num_candles) * 20)
    closes = base_price + trend + noise

    # Generate OHLC
    highs = closes + np.abs(np.random.randn(num_candles) * 30)
    lows = closes - np.abs(np.random.randn(num_candles) * 30)
    opens = closes + np.random.randn(num_candles) * 10
    volumes = np.abs(np.random.randn(num_candles) * 500000) + 1000000

    ohlcv_data = np.column_stack([timestamps, opens, highs, lows, closes, volumes])

    print(f"\nGenerated {len(ohlcv_data)} candles of 1-min data")
    print(f"Price range: ${lows.min():.2f} - ${highs.max():.2f}")

    # Calculate 7-day VP
    vp_7d = get_7d_volume_profile(ohlcv_data, num_bins=60)

    if vp_7d:
        print(f"\n=== 7-Day Volume Profile ===")
        print(f"Days covered: {vp_7d['days_covered']:.1f}")
        print(f"Candles used: {vp_7d['num_candles']}")
        print(f"POC: ${vp_7d['poc']:.2f}")
        print(f"VAH: ${vp_7d['vah']:.2f}")
        print(f"VAL: ${vp_7d['val']:.2f}")
        print(f"Value Area width: ${vp_7d['vah'] - vp_7d['val']:.2f}")
        print(f"HVN nodes: {len(vp_7d['hvn'])} - {[f'${x:.2f}' for x in vp_7d['hvn'][:3]]}")
        print(f"LVN nodes: {len(vp_7d['lvn'])} - {[f'${x:.2f}' for x in vp_7d['lvn']]}")

        # Test context functions
        current_price = closes[-1]
        context = get_vp_context(current_price, vp_7d)

        print(f"\n=== Current Price Context ===")
        print(f"Current Price: ${current_price:.2f}")
        print(f"Position vs POC: {context['position_vs_poc']}")
        print(f"In Value Area: {context['in_value_area']}")
        print(f"Near HVN: {context['near_hvn']}")
        print(f"Near LVN: {context['near_lvn']}")

        if context['nearest_hvn']:
            print(f"Nearest HVN: ${context['nearest_hvn']:.2f}")
        if context['nearest_lvn']:
            print(f"Nearest LVN: ${context['nearest_lvn']:.2f}")

    print("\n[OK] Volume Profile V3 tests complete")
