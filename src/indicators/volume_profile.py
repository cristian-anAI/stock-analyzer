"""
Volume Profile Calculation for Crypto Scalping (5-min timeframe)

This module provides functions to calculate Volume Profile and extract key nodes
(POC, VAH, VAL, HVN, LVN) across multiple timeframes for trading decisions.

Author: Stock Analyzer Bot
Timeframe: Optimized for 5-minute scalping on Binance
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

    For 5-min scalping, 60 bins provides optimal balance between precision
    and noise reduction. Each bin represents ~0.5-1% price movement in typical crypto.

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
    # Assumption: Volume distributed uniformly between high-low
    for i in range(len(ohlcv_data)):
        candle_low = lows[i]
        candle_high = highs[i]
        candle_volume = volumes[i]

        if candle_high == candle_low:
            # Single price - all volume goes to one bin
            bin_idx = np.searchsorted(bin_edges[1:], candle_low)
            bin_idx = min(bin_idx, num_bins - 1)  # Clip to valid range
            volume_at_price[bin_idx] += candle_volume
        else:
            # Distribute volume proportionally across bins within candle range
            # Find bins that overlap with this candle
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
    """
    Find Point of Control (price level with highest volume).

    Args:
        price_levels: Array of price bin centers
        volume_distribution: Volume at each price level

    Returns:
        Price of the POC
    """
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

    Value Area contains the specified percentage of total volume (default 70%),
    starting from POC and expanding symmetrically.

    Args:
        price_levels: Array of price bin centers
        volume_distribution: Volume at each price level
        percentage: Percentage of volume to include (default: 0.70)

    Returns:
        Tuple of (VAH, VAL)
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
            # Reached boundaries
            break

    vah = float(price_levels[high_idx])
    val = float(price_levels[low_idx])

    # Ensure VAH > VAL (should always be true, but safety check)
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
    Find High Volume Nodes (significant volume peaks).

    Uses peak detection to find local maxima in volume distribution,
    filtered by minimum separation distance.

    Args:
        price_levels: Array of price bin centers
        volume_distribution: Volume at each price level
        num_nodes: Maximum number of HVN nodes to return
        min_distance_pct: Minimum distance between nodes as % of price range

    Returns:
        List of HVN prices, sorted by volume (highest first)
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
        # No peaks found, return POC
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

    # Sort by volume for final output (highest volume first)
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
    Find Low Volume Nodes (volume valleys between HVNs).

    LVNs act as "thin zones" or "air pockets" where price can move quickly.
    These are local minima in volume between high-volume areas.

    Args:
        price_levels: Array of price bin centers
        volume_distribution: Volume at each price level
        hvn_list: List of HVN prices to find valleys between
        num_nodes: Maximum number of LVN nodes to return

    Returns:
        List of LVN prices, sorted by volume (lowest first)
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

    # Sort valleys by volume (ascending - we want lowest volume)
    valleys.sort(key=lambda x: x[1])

    # Filter: only keep valleys that are between HVNs
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


def get_multi_timeframe_vp(
    ohlcv_data_5min: np.ndarray,
    num_bins: int = 60
) -> Dict[str, Dict]:
    """
    Calculate Volume Profile across multiple timeframes for scalping.

    Timeframes:
    - vp_corto: 48 candles (4 hours) - immediate context
    - vp_medio: 288 candles (24 hours) - daily context
    - vp_largo: 2016 candles (7 days) - weekly context

    Args:
        ohlcv_data_5min: Full array of 5-min OHLCV data (oldest to newest)
        num_bins: Number of price bins for VP calculation

    Returns:
        Dictionary with 'vp_corto', 'vp_medio', 'vp_largo' keys containing VP data
    """
    total_candles = len(ohlcv_data_5min)

    # Define timeframe windows (in number of 5-min candles)
    windows = {
        'vp_corto': 48,      # 4 hours
        'vp_medio': 288,     # 24 hours (1 day)
        'vp_largo': 2016     # 168 hours (7 days)
    }

    result = {}

    for tf_name, window_size in windows.items():
        if total_candles < window_size:
            warnings.warn(
                f"Insufficient data for {tf_name}: need {window_size} candles, "
                f"have {total_candles}. Using all available data."
            )
            tf_data = ohlcv_data_5min
        else:
            # Take most recent 'window_size' candles
            tf_data = ohlcv_data_5min[-window_size:]

        try:
            vp = calculate_volume_profile(tf_data, num_bins=num_bins)

            result[tf_name] = {
                'poc': vp.poc,
                'vah': vp.vah,
                'val': vp.val,
                'hvn': vp.hvn,
                'lvn': vp.lvn,
                'price_levels': vp.price_levels.tolist(),
                'volume_distribution': vp.volume_distribution.tolist(),
                'total_volume': vp.total_volume,
                'price_range': vp.price_range,
                'num_candles': len(tf_data)
            }
        except ValueError as e:
            warnings.warn(f"Error calculating {tf_name}: {str(e)}")
            result[tf_name] = None

    return result


def visualize_volume_profile(
    vp_result: VolumeProfileResult,
    title: str = "Volume Profile",
    save_path: Optional[str] = None
):
    """
    Visualize Volume Profile with matplotlib (for debugging only).

    Args:
        vp_result: VolumeProfileResult object
        title: Plot title
        save_path: Optional path to save figure (if None, displays interactively)
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available - skipping visualization")
        return

    fig, ax = plt.subplots(figsize=(12, 8))

    # Plot volume profile as horizontal bar chart
    ax.barh(vp_result.price_levels, vp_result.volume_distribution,
            height=(vp_result.price_levels[1] - vp_result.price_levels[0]),
            color='steelblue', alpha=0.6, label='Volume')

    # Mark POC
    ax.axhline(vp_result.poc, color='red', linestyle='--', linewidth=2, label=f'POC: {vp_result.poc:.2f}')

    # Mark Value Area
    ax.axhline(vp_result.vah, color='green', linestyle='--', linewidth=1.5, label=f'VAH: {vp_result.vah:.2f}')
    ax.axhline(vp_result.val, color='green', linestyle='--', linewidth=1.5, label=f'VAL: {vp_result.val:.2f}')
    ax.axhspan(vp_result.val, vp_result.vah, alpha=0.1, color='green', label='Value Area (70%)')

    # Mark HVNs
    for i, hvn in enumerate(vp_result.hvn):
        ax.axhline(hvn, color='orange', linestyle=':', linewidth=1, alpha=0.7)
        if i == 0:
            ax.text(ax.get_xlim()[1] * 0.95, hvn, 'HVN', fontsize=8, va='center')

    # Mark LVNs
    for i, lvn in enumerate(vp_result.lvn):
        ax.axhline(lvn, color='purple', linestyle=':', linewidth=1, alpha=0.7)
        if i == 0:
            ax.text(ax.get_xlim()[1] * 0.95, lvn, 'LVN', fontsize=8, va='center')

    ax.set_xlabel('Volume', fontsize=12)
    ax.set_ylabel('Price', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Volume Profile chart saved to: {save_path}")
    else:
        plt.show()

    plt.close()


# ==================== TESTING & EXAMPLE USAGE ====================

def generate_dummy_ohlcv(num_candles: int = 500, base_price: float = 43000) -> np.ndarray:
    """
    Generate synthetic OHLCV data for testing.

    Simulates realistic crypto price action with trends, volatility, and volume.
    """
    np.random.seed(42)

    data = np.zeros((num_candles, 6))

    # Generate timestamps (5-min intervals)
    start_time = 1700000000000  # Arbitrary timestamp
    data[:, 0] = start_time + np.arange(num_candles) * 300000  # 5 min = 300,000 ms

    # Generate price action with trend
    trend = np.linspace(0, 1000, num_candles)  # Upward trend of $1000
    noise = np.cumsum(np.random.randn(num_candles) * 50)  # Random walk
    close_prices = base_price + trend + noise

    # Generate OHLC from close prices
    for i in range(num_candles):
        close = close_prices[i]
        volatility = abs(np.random.randn()) * 30  # Random volatility

        open_price = close + np.random.randn() * 10
        high = max(open_price, close) + abs(np.random.randn()) * volatility
        low = min(open_price, close) - abs(np.random.randn()) * volatility

        data[i, 1] = open_price  # Open
        data[i, 2] = high        # High
        data[i, 3] = low         # Low
        data[i, 4] = close       # Close

        # Volume: higher near price extremes (simulates institutional accumulation)
        base_volume = 1000000 + abs(np.random.randn()) * 500000
        if i > 0 and abs(close - close_prices[i-1]) > 100:
            base_volume *= 1.5  # Higher volume on big moves
        data[i, 5] = base_volume

    return data


def test_volume_profile_system():
    """
    Test the complete Volume Profile system with dummy data.
    """
    print("=" * 70)
    print("TESTING VOLUME PROFILE SYSTEM")
    print("=" * 70)

    # Generate test data
    print("\n1. Generating 2500 candles of synthetic OHLCV data (5-min)...")
    ohlcv_data = generate_dummy_ohlcv(num_candles=2500, base_price=43000)
    print(f"   [OK] Generated {len(ohlcv_data)} candles")
    print(f"   Price range: ${ohlcv_data[:, 3].min():.2f} - ${ohlcv_data[:, 2].max():.2f}")
    print(f"   Total volume: {ohlcv_data[:, 5].sum():,.0f}")

    # Test single timeframe VP
    print("\n2. Testing single timeframe VP calculation (288 candles = 24h)...")
    recent_data = ohlcv_data[-288:]
    vp = calculate_volume_profile(recent_data, num_bins=60)

    print(f"   [OK] POC: ${vp.poc:.2f}")
    print(f"   [OK] VAH: ${vp.vah:.2f}")
    print(f"   [OK] VAL: ${vp.val:.2f}")
    print(f"   [OK] Value Area spread: ${vp.vah - vp.val:.2f} ({((vp.vah-vp.val)/vp.poc*100):.2f}%)")
    print(f"   [OK] HVN nodes: {len(vp.hvn)} identified - {[f'${x:.2f}' for x in vp.hvn[:3]]}")
    print(f"   [OK] LVN nodes: {len(vp.lvn)} identified - {[f'${x:.2f}' for x in vp.lvn]}")

    # Validate invariants
    assert vp.vah > vp.poc > vp.val, "ERROR: VAH > POC > VAL invariant violated!"
    assert len(vp.hvn) > 0, "ERROR: No HVN nodes found!"
    print("   [OK] All invariants validated (VAH > POC > VAL)")

    # Test multi-timeframe VP
    print("\n3. Testing multi-timeframe VP calculation...")
    mtf_vp = get_multi_timeframe_vp(ohlcv_data, num_bins=60)

    for tf_name in ['vp_corto', 'vp_medio', 'vp_largo']:
        if mtf_vp[tf_name] is not None:
            tf_data = mtf_vp[tf_name]
            print(f"\n   {tf_name.upper()} ({tf_data['num_candles']} candles):")
            print(f"      POC: ${tf_data['poc']:.2f}")
            print(f"      VAH: ${tf_data['vah']:.2f}")
            print(f"      VAL: ${tf_data['val']:.2f}")
            print(f"      HVN: {len(tf_data['hvn'])} nodes")
            print(f"      LVN: {len(tf_data['lvn'])} nodes")

    # Test visualization (optional - requires matplotlib)
    print("\n4. Testing visualization (if matplotlib available)...")
    try:
        visualize_volume_profile(vp, title="Volume Profile Test - 24H", save_path="vp_test.png")
        print("   [OK] Visualization saved to vp_test.png")
    except Exception as e:
        print(f"   ! Visualization skipped: {str(e)}")

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED [OK]")
    print("=" * 70)
    print("\nRECOMMENDATIONS:")
    print("- For 5-min scalping, 60 bins provides good precision without noise")
    print("- Use VP_corto (4h) for immediate entry/exit levels")
    print("- Use VP_medio (24h) for intraday support/resistance")
    print("- Use VP_largo (7d) for major supply/demand zones")
    print("- LVN zones act as 'thin air' - expect fast moves through them")
    print("- HVN zones act as magnets - price tends to revert to them")
    print("=" * 70)

    return mtf_vp


if __name__ == "__main__":
    # Run tests
    test_volume_profile_system()
