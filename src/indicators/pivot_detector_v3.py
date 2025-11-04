"""
Pivot Detector V3 for PupupuV3 Strategy
Improvements over V2:
- Reduced lookback: 100 periods (vs 400)
- Stronger filtering: only most relevant pivots
- Better touch detection
- Pivot strength scoring
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Pivot:
    """Represents a single pivot point"""
    price: float
    index: int
    pivot_type: str  # 'resistance' or 'support'
    strength: float  # 0-100 score
    touches: int
    last_touch_idx: Optional[int]
    is_active: bool
    bars_since_formation: int


class PupupuV3PivotDetector:
    """
    Detects swing highs and lows for PupupuV3 strategy

    Key improvements:
    - Only keeps strongest/most relevant pivots
    - 100-period lookback (more responsive)
    - Better scoring system
    """

    def __init__(self, lookback_periods: int = 100, swing_bars: int = 5,
                 max_pivots_per_side: int = 3, touch_threshold_pct: float = 0.1):
        """
        Args:
            lookback_periods: How far back to look for pivots (default: 100)
            swing_bars: Bars on each side for swing detection (default: 5)
            max_pivots_per_side: Maximum pivots to keep per side (default: 3)
            touch_threshold_pct: Price distance to consider a "touch" (default: 0.1%)
        """
        self.lookback_periods = lookback_periods
        self.swing_bars = swing_bars
        self.max_pivots_per_side = max_pivots_per_side
        self.touch_threshold_pct = touch_threshold_pct

        # Storage
        self.resistances: List[Pivot] = []
        self.supports: List[Pivot] = []

    def detect_pivots(self, ohlcv_data: np.ndarray) -> Dict[str, List[Pivot]]:
        """
        Detect swing highs and lows in the data

        Args:
            ohlcv_data: numpy array [timestamp, open, high, low, close, volume]

        Returns:
            Dictionary with 'resistances' and 'supports' lists
        """
        if len(ohlcv_data) < self.swing_bars * 2 + 1:
            return {'resistances': [], 'supports': []}

        # Only analyze last lookback_periods candles
        start_idx = max(0, len(ohlcv_data) - self.lookback_periods)
        data_slice = ohlcv_data[start_idx:]

        highs = data_slice[:, 2]
        lows = data_slice[:, 3]
        closes = data_slice[:, 4]

        current_idx = len(ohlcv_data) - 1
        current_close = closes[-1]

        # Detect swing highs (resistances)
        new_resistances = []
        for i in range(self.swing_bars, len(highs) - self.swing_bars):
            is_swing_high = True

            # Check if this is highest point in the window
            for j in range(i - self.swing_bars, i + self.swing_bars + 1):
                if j != i and highs[j] >= highs[i]:
                    is_swing_high = False
                    break

            if is_swing_high:
                actual_idx = start_idx + i
                bars_since = current_idx - actual_idx

                # Calculate strength based on multiple factors
                strength = self._calculate_pivot_strength(
                    price=highs[i],
                    current_price=current_close,
                    bars_since=bars_since,
                    peak_value=highs[i],
                    surrounding_highs=highs[max(0, i-10):min(len(highs), i+10)]
                )

                # Count touches
                touches = self._count_touches(highs[i], highs, self.touch_threshold_pct)

                pivot = Pivot(
                    price=highs[i],
                    index=actual_idx,
                    pivot_type='resistance',
                    strength=strength,
                    touches=touches,
                    last_touch_idx=None,
                    is_active=highs[i] > current_close,  # Only active if above price
                    bars_since_formation=bars_since
                )

                new_resistances.append(pivot)

        # Detect swing lows (supports)
        new_supports = []
        for i in range(self.swing_bars, len(lows) - self.swing_bars):
            is_swing_low = True

            # Check if this is lowest point in the window
            for j in range(i - self.swing_bars, i + self.swing_bars + 1):
                if j != i and lows[j] <= lows[i]:
                    is_swing_low = False
                    break

            if is_swing_low:
                actual_idx = start_idx + i
                bars_since = current_idx - actual_idx

                # Calculate strength
                strength = self._calculate_pivot_strength(
                    price=lows[i],
                    current_price=current_close,
                    bars_since=bars_since,
                    peak_value=lows[i],
                    surrounding_highs=lows[max(0, i-10):min(len(lows), i+10)]
                )

                # Count touches
                touches = self._count_touches(lows[i], lows, self.touch_threshold_pct)

                pivot = Pivot(
                    price=lows[i],
                    index=actual_idx,
                    pivot_type='support',
                    strength=strength,
                    touches=touches,
                    last_touch_idx=None,
                    is_active=lows[i] < current_close,  # Only active if below price
                    bars_since_formation=bars_since
                )

                new_supports.append(pivot)

        # Filter and keep only strongest pivots
        self.resistances = self._filter_best_pivots(new_resistances, current_close, 'resistance')
        self.supports = self._filter_best_pivots(new_supports, current_close, 'support')

        return {
            'resistances': self.resistances,
            'supports': self.supports
        }

    def _calculate_pivot_strength(self, price: float, current_price: float,
                                  bars_since: int, peak_value: float,
                                  surrounding_highs: np.ndarray) -> float:
        """
        Calculate pivot strength score (0-100)

        Factors:
        - Recency (newer = stronger)
        - Distance from current price (closer = stronger)
        - Peak prominence (how much it stands out)
        """
        strength = 50.0  # Base strength

        # Recency factor (0-30 points)
        # Recent pivots (< 20 bars) get more points
        recency_score = max(0, 30 - (bars_since / 20.0) * 30)
        strength += recency_score

        # Distance factor (0-20 points)
        # Pivots within 2% get full points, further get less
        distance_pct = abs(price - current_price) / current_price * 100
        if distance_pct < 2.0:
            distance_score = 20
        elif distance_pct < 5.0:
            distance_score = 10
        else:
            distance_score = 5
        strength += distance_score

        # Prominence factor (0-20 points)
        # How much the pivot stands out from surrounding prices
        if len(surrounding_highs) > 0:
            avg_surrounding = np.mean(surrounding_highs)
            prominence = abs(peak_value - avg_surrounding) / avg_surrounding * 100
            prominence_score = min(20, prominence * 4)
            strength += prominence_score

        return min(100.0, max(0.0, strength))

    def _count_touches(self, pivot_price: float, price_array: np.ndarray,
                      threshold_pct: float) -> int:
        """Count how many times price touched this level"""
        threshold = pivot_price * (threshold_pct / 100.0)
        touches = 0

        for price in price_array:
            if abs(price - pivot_price) <= threshold:
                touches += 1

        return max(1, touches)  # At least 1 (the pivot itself)

    def _filter_best_pivots(self, pivots: List[Pivot], current_price: float,
                           pivot_type: str) -> List[Pivot]:
        """
        Keep only the strongest/most relevant pivots

        Criteria:
        - Must be active (above price for resistance, below for support)
        - Sort by strength score
        - Keep only max_pivots_per_side
        - Merge similar levels (within 0.5%)
        """
        # Filter only active pivots
        active_pivots = [p for p in pivots if p.is_active]

        if len(active_pivots) == 0:
            return []

        # Merge similar levels
        merged_pivots = self._merge_similar_pivots(active_pivots, merge_threshold_pct=0.5)

        # Sort by strength (descending)
        merged_pivots.sort(key=lambda p: p.strength, reverse=True)

        # Keep only top N
        return merged_pivots[:self.max_pivots_per_side]

    def _merge_similar_pivots(self, pivots: List[Pivot],
                              merge_threshold_pct: float = 0.5) -> List[Pivot]:
        """
        Merge pivots that are very close to each other
        Keep the strongest one from each cluster
        """
        if len(pivots) <= 1:
            return pivots

        # Sort by price
        sorted_pivots = sorted(pivots, key=lambda p: p.price)

        merged = []
        current_cluster = [sorted_pivots[0]]

        for i in range(1, len(sorted_pivots)):
            prev_price = current_cluster[-1].price
            curr_price = sorted_pivots[i].price

            # Check if within merge threshold
            distance_pct = abs(curr_price - prev_price) / prev_price * 100

            if distance_pct <= merge_threshold_pct:
                # Add to current cluster
                current_cluster.append(sorted_pivots[i])
            else:
                # Save strongest from cluster and start new cluster
                strongest = max(current_cluster, key=lambda p: p.strength)
                merged.append(strongest)
                current_cluster = [sorted_pivots[i]]

        # Don't forget last cluster
        if current_cluster:
            strongest = max(current_cluster, key=lambda p: p.strength)
            merged.append(strongest)

        return merged

    def get_nearest_pivot(self, current_price: float, direction: str = "above") -> Optional[Pivot]:
        """
        Get nearest pivot above or below current price

        Args:
            current_price: Current market price
            direction: "above" for resistance, "below" for support

        Returns:
            Nearest Pivot or None
        """
        if direction == "above":
            candidates = [p for p in self.resistances if p.price > current_price]
            if candidates:
                return min(candidates, key=lambda p: p.price)
        else:  # below
            candidates = [p for p in self.supports if p.price < current_price]
            if candidates:
                return max(candidates, key=lambda p: p.price)

        return None

    def is_touching_pivot(self, current_price: float, pivot: Pivot) -> bool:
        """Check if current price is touching a pivot"""
        threshold = pivot.price * (self.touch_threshold_pct / 100.0)
        return abs(current_price - pivot.price) <= threshold

    def candle_touched_pivot(self, candle: np.ndarray, pivot: Pivot) -> bool:
        """
        Check if candle (wick) physically touched the pivot level

        Args:
            candle: OHLCV array [timestamp, open, high, low, close, volume]
            pivot: Pivot object to check

        Returns:
            True if candle high/low touched the pivot price
        """
        candle_high = candle[2]
        candle_low = candle[3]
        pivot_price = pivot.price

        # Check if pivot price is within candle range (high to low)
        return candle_low <= pivot_price <= candle_high

    def get_active_pivots_summary(self) -> Dict:
        """Get summary of all active pivots"""
        return {
            'resistances': [
                {
                    'price': p.price,
                    'strength': round(p.strength, 2),
                    'touches': p.touches,
                    'bars_since': p.bars_since_formation
                }
                for p in self.resistances
            ],
            'supports': [
                {
                    'price': p.price,
                    'strength': round(p.strength, 2),
                    'touches': p.touches,
                    'bars_since': p.bars_since_formation
                }
                for p in self.supports
            ]
        }


# Test function
if __name__ == "__main__":
    print("Testing Pivot Detector V3...")

    # Create sample data with clear swing highs and lows
    np.random.seed(42)
    timestamps = np.arange(1609459200000, 1609459200000 + 150 * 60000, 60000)  # 150 candles

    # Create price pattern with clear pivots
    base_price = 29000
    prices = []
    for i in range(150):
        # Create swing pattern
        if i % 20 < 10:
            prices.append(base_price + (i % 20) * 50)  # Upswing
        else:
            prices.append(base_price + (20 - (i % 20)) * 50)  # Downswing

    closes = np.array(prices)
    highs = closes + np.random.uniform(10, 50, len(closes))
    lows = closes - np.random.uniform(10, 50, len(closes))
    opens = closes - np.random.uniform(-30, 30, len(closes))
    volumes = np.random.uniform(100, 200, len(closes))

    ohlcv_data = np.column_stack([timestamps, opens, highs, lows, closes, volumes])

    # Test detector
    detector = PupupuV3PivotDetector(lookback_periods=100, max_pivots_per_side=3)
    result = detector.detect_pivots(ohlcv_data)

    print(f"\nCurrent Price: ${closes[-1]:.2f}")
    print(f"\n=== Active Resistances (Top {len(result['resistances'])}) ===")
    for i, pivot in enumerate(result['resistances'], 1):
        print(f"{i}. ${pivot.price:.2f} | Strength: {pivot.strength:.1f} | "
              f"Touches: {pivot.touches} | Bars ago: {pivot.bars_since_formation}")

    print(f"\n=== Active Supports (Top {len(result['supports'])}) ===")
    for i, pivot in enumerate(result['supports'], 1):
        print(f"{i}. ${pivot.price:.2f} | Strength: {pivot.strength:.1f} | "
              f"Touches: {pivot.touches} | Bars ago: {pivot.bars_since_formation}")

    # Test nearest pivot functions
    nearest_resistance = detector.get_nearest_pivot(closes[-1], "above")
    nearest_support = detector.get_nearest_pivot(closes[-1], "below")

    print(f"\n=== Nearest Levels ===")
    if nearest_resistance:
        print(f"Nearest Resistance: ${nearest_resistance.price:.2f} "
              f"(+{((nearest_resistance.price - closes[-1]) / closes[-1] * 100):.2f}%)")
    if nearest_support:
        print(f"Nearest Support: ${nearest_support.price:.2f} "
              f"({((nearest_support.price - closes[-1]) / closes[-1] * 100):.2f}%)")

    print("\n[OK] Pivot Detector V3 tests complete")
