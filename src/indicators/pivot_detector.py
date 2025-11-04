"""
Pupupu Pivot Detector - Replicates TradingView Pupupu indicator logic

Detects swing highs (resistances) and swing lows (supports) in price action.
These pivots persist as horizontal levels for trade setups.
"""

import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Pivot:
    """Represents a pivot point (support or resistance)."""
    price: float
    timestamp: datetime
    type: str  # "resistance" or "support"
    index: int  # index in candle array
    strength: float  # 0-1, based on touches and context
    active: bool = True  # if still valid (not clearly broken)
    touches: int = 1  # number of times price touched this level
    candles_age: int = 0  # how many candles since formation

    def __repr__(self):
        return f"Pivot({self.type}, ${self.price:.2f}, strength={self.strength:.2f}, touches={self.touches})"


class PupupuPivotDetector:
    """
    Replicates Pupupu indicator logic from TradingView.

    Detects swing highs/lows in the last N periods and maintains
    a list of active pivots (resistances and supports).

    Configuration matches Pupupu indicator:
    - Lookback: 400 periods (5-min → ~33 hours)
    - Swing detection: 5 bars on each side
    - Persistence: Pivots remain until clearly broken
    """

    def __init__(
        self,
        lookback_periods: int = 400,
        swing_detection_bars: int = 5,
        break_tolerance_pct: float = 0.2,
        touch_tolerance_pct: float = 0.15
    ):
        self.lookback = lookback_periods
        self.swing_bars = swing_detection_bars
        self.break_tolerance = break_tolerance_pct
        self.touch_tolerance = touch_tolerance_pct

        self.active_resistances: List[Pivot] = []
        self.active_supports: List[Pivot] = []
        self.historical_pivots: List[Pivot] = []

    def detect_pivots(self, ohlcv_data: np.ndarray) -> Dict[str, List[Pivot]]:
        """
        Detect all pivots in the dataset.

        Args:
            ohlcv_data: Array numpy shape (n, 6) with [timestamp, o, h, l, c, v]

        Returns:
            {
                'resistances': [Pivot, ...],
                'supports': [Pivot, ...]
            }
        """
        if len(ohlcv_data) < self.swing_bars * 2 + 1:
            return {'resistances': [], 'supports': []}

        # Only analyze last lookback_periods
        data_to_analyze = ohlcv_data[-self.lookback:]

        highs = data_to_analyze[:, 2]  # high prices
        lows = data_to_analyze[:, 3]   # low prices
        timestamps = data_to_analyze[:, 0]

        resistances = []
        supports = []

        # Detect swing highs (resistances)
        for i in range(self.swing_bars, len(highs) - self.swing_bars):
            if self._is_swing_high(highs, i):
                resistances.append(Pivot(
                    price=highs[i],
                    timestamp=datetime.fromtimestamp(timestamps[i] / 1000),
                    type="resistance",
                    index=i,
                    strength=self._calculate_pivot_strength(highs, i, 'high'),
                    candles_age=len(highs) - i - 1
                ))

        # Detect swing lows (supports)
        for i in range(self.swing_bars, len(lows) - self.swing_bars):
            if self._is_swing_low(lows, i):
                supports.append(Pivot(
                    price=lows[i],
                    timestamp=datetime.fromtimestamp(timestamps[i] / 1000),
                    type="support",
                    index=i,
                    strength=self._calculate_pivot_strength(lows, i, 'low'),
                    candles_age=len(lows) - i - 1
                ))

        return {
            'resistances': resistances,
            'supports': supports
        }

    def _is_swing_high(self, highs: np.ndarray, index: int) -> bool:
        """Check if index is a swing high (local maximum)."""
        current_high = highs[index]

        for j in range(1, self.swing_bars + 1):
            if highs[index - j] >= current_high or highs[index + j] >= current_high:
                return False

        return True

    def _is_swing_low(self, lows: np.ndarray, index: int) -> bool:
        """Check if index is a swing low (local minimum)."""
        current_low = lows[index]

        for j in range(1, self.swing_bars + 1):
            if lows[index - j] <= current_low or lows[index + j] <= current_low:
                return False

        return True

    def _calculate_pivot_strength(
        self,
        price_array: np.ndarray,
        pivot_index: int,
        pivot_type: str
    ) -> float:
        """
        Calculate "strength" of a pivot based on:
        - How extreme it is compared to neighbors
        - Temporal distance from formation
        - Local context

        Returns:
            float between 0-1, where 1 = very strong pivot
        """
        window = 20
        start = max(0, pivot_index - window)
        end = min(len(price_array), pivot_index + window)
        local_prices = price_array[start:end]

        price_range = np.max(local_prices) - np.min(local_prices)
        if price_range < 0.0001:
            return 0.5

        if pivot_type == 'high':
            # How close to local maximum
            extremeness = (price_array[pivot_index] - np.min(local_prices)) / price_range
        else:  # low
            # How close to local minimum
            extremeness = (np.max(local_prices) - price_array[pivot_index]) / price_range

        # Recency factor: newer pivots have less proven strength initially
        recency = min(1.0, (len(price_array) - pivot_index) / 50)

        # Combine factors
        strength = extremeness * 0.7 + recency * 0.3

        return min(1.0, max(0.0, strength))

    def update_pivot_status(
        self,
        new_candle: Dict,
        existing_pivots: List[Pivot]
    ) -> List[Pivot]:
        """
        Update status of existing pivots with new candle.
        Marks as inactive those that have been clearly broken.

        Args:
            new_candle: Dict with {'high', 'low', 'close', ...}
            existing_pivots: List of pivots to update

        Returns:
            List of still-active pivots
        """
        active_pivots = []

        for pivot in existing_pivots:
            pivot.candles_age += 1

            if pivot.type == "resistance":
                # Broken if price closes clearly above
                break_price = pivot.price * (1 + self.break_tolerance / 100)

                if new_candle['close'] > break_price:
                    pivot.active = False
                    self.historical_pivots.append(pivot)
                else:
                    # Increment touches if near
                    if self._is_near_pivot(new_candle['high'], pivot.price):
                        pivot.touches += 1
                        # Increase strength with more touches
                        pivot.strength = min(0.95, pivot.strength + 0.1)
                    active_pivots.append(pivot)

            else:  # support
                # Broken if price closes clearly below
                break_price = pivot.price * (1 - self.break_tolerance / 100)

                if new_candle['close'] < break_price:
                    pivot.active = False
                    self.historical_pivots.append(pivot)
                else:
                    # Increment touches if near
                    if self._is_near_pivot(new_candle['low'], pivot.price):
                        pivot.touches += 1
                        pivot.strength = min(0.95, pivot.strength + 0.1)
                    active_pivots.append(pivot)

        return active_pivots

    def _is_near_pivot(self, price: float, pivot_price: float) -> bool:
        """Check if price is near pivot level."""
        return abs(price - pivot_price) / pivot_price < (self.touch_tolerance / 100)

    def get_nearest_pivot(
        self,
        current_price: float,
        direction: str = "above"
    ) -> Optional[Pivot]:
        """
        Get nearest active pivot above/below current price.

        Args:
            current_price: Current market price
            direction: "above" for resistances, "below" for supports

        Returns:
            Nearest Pivot or None if none exists
        """
        if direction == "above":
            candidates = [p for p in self.active_resistances if p.price > current_price]
            if not candidates:
                return None
            return min(candidates, key=lambda p: p.price - current_price)

        else:  # below
            candidates = [p for p in self.active_supports if p.price < current_price]
            if not candidates:
                return None
            return max(candidates, key=lambda p: current_price - p.price)

    def price_touched_pivot(
        self,
        candle: Dict,
        pivot: Pivot,
        tolerance_pct: Optional[float] = None
    ) -> bool:
        """
        Verify if a candle "touched" a pivot.

        Args:
            candle: Dict with OHLC
            pivot: Pivot to check
            tolerance_pct: % tolerance to consider "touch" (default: use instance value)

        Returns:
            True if candle touched the pivot
        """
        if tolerance_pct is None:
            tolerance_pct = self.touch_tolerance

        upper_bound = pivot.price * (1 + tolerance_pct / 100)
        lower_bound = pivot.price * (1 - tolerance_pct / 100)

        if pivot.type == "resistance":
            # Check if high of candle reached pivot
            return lower_bound <= candle['high'] <= upper_bound

        else:  # support
            # Check if low of candle reached pivot
            return lower_bound <= candle['low'] <= upper_bound

    def get_all_active_pivots(self) -> List[Pivot]:
        """Get all active pivots sorted by strength."""
        all_pivots = self.active_resistances + self.active_supports
        return sorted(all_pivots, key=lambda p: p.strength, reverse=True)

    def merge_close_pivots(
        self,
        pivots: List[Pivot],
        merge_threshold_pct: float = 0.1
    ) -> List[Pivot]:
        """
        Merge pivots that are very close to each other.
        Useful to avoid clutter from multiple similar levels.

        Args:
            pivots: List of pivots to merge
            merge_threshold_pct: % distance to consider "same level"

        Returns:
            List of merged pivots
        """
        if not pivots:
            return []

        sorted_pivots = sorted(pivots, key=lambda p: p.price)
        merged = [sorted_pivots[0]]

        for pivot in sorted_pivots[1:]:
            last_merged = merged[-1]
            price_diff_pct = abs(pivot.price - last_merged.price) / last_merged.price * 100

            if price_diff_pct < merge_threshold_pct:
                # Merge into existing pivot (keep stronger one, combine touches)
                if pivot.strength > last_merged.strength:
                    merged[-1] = pivot
                merged[-1].touches += pivot.touches
            else:
                merged.append(pivot)

        return merged


# Testing
if __name__ == "__main__":
    from src.indicators.volume_profile import generate_dummy_ohlcv

    print("="*70)
    print("TESTING PUPUPU PIVOT DETECTOR")
    print("="*70)

    # Generate test data
    print("\nGenerating 500 candles of test data...")
    ohlcv = generate_dummy_ohlcv(num_candles=500, base_price=43000)

    # Initialize detector
    detector = PupupuPivotDetector(
        lookback_periods=400,
        swing_detection_bars=5
    )

    # Detect pivots
    print("\nDetecting pivots...")
    pivots = detector.detect_pivots(ohlcv)

    print(f"\n[OK] Found {len(pivots['resistances'])} resistances")
    print(f"[OK] Found {len(pivots['supports'])} supports")

    # Show top 5 strongest resistances
    print("\nTOP 5 RESISTANCES:")
    top_resistances = sorted(pivots['resistances'], key=lambda p: p.strength, reverse=True)[:5]
    for i, p in enumerate(top_resistances, 1):
        print(f"  #{i}: ${p.price:.2f} - strength={p.strength:.2f}, age={p.candles_age} candles")

    # Show top 5 strongest supports
    print("\nTOP 5 SUPPORTS:")
    top_supports = sorted(pivots['supports'], key=lambda p: p.strength, reverse=True)[:5]
    for i, p in enumerate(top_supports, 1):
        print(f"  #{i}: ${p.price:.2f} - strength={p.strength:.2f}, age={p.candles_age} candles")

    # Test nearest pivot
    current_price = ohlcv[-1, 4]
    print(f"\nCurrent price: ${current_price:.2f}")

    detector.active_resistances = pivots['resistances']
    detector.active_supports = pivots['supports']

    nearest_resistance = detector.get_nearest_pivot(current_price, "above")
    nearest_support = detector.get_nearest_pivot(current_price, "below")

    if nearest_resistance:
        print(f"Nearest resistance: ${nearest_resistance.price:.2f} (+{((nearest_resistance.price - current_price)/current_price*100):.2f}%)")
    if nearest_support:
        print(f"Nearest support: ${nearest_support.price:.2f} ({((nearest_support.price - current_price)/current_price*100):.2f}%)")

    print("\n" + "="*70)
    print("TEST COMPLETED")
    print("="*70)
