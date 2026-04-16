"""
Simple Pivot Detector - Rolling High/Low Method
Similar to TradingView's pivot detection

Instead of swing highs/lows with confirmation, this uses:
- Rolling maximum for resistances
- Rolling minimum for supports
- Over a fixed lookback period (default 100)
"""

import numpy as np
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class SimplePivot:
    """Simple pivot point"""
    price: float
    pivot_type: str  # 'resistance' or 'support'
    touches: int
    bars_since_formation: int
    is_active: bool
    strength: float = 50.0  # Strength score (0-100)


class SimplePivotDetector:
    """
    Detects pivots using rolling high/low method

    Algorithm:
    1. For each 100-candle window, find the highest high (resistance)
    2. For each 100-candle window, find the lowest low (support)
    3. Merge similar levels (within 0.5%)
    4. Keep strongest/most recent
    """

    def __init__(
        self,
        lookback_periods: int = 100,
        max_pivots_per_side: int = 5,
        merge_threshold_pct: float = 0.5
    ):
        """
        Args:
            lookback_periods: Rolling window size (default 100)
            max_pivots_per_side: Maximum pivots to keep (default 5)
            merge_threshold_pct: Merge pivots within this % (default 0.5%)
        """
        self.lookback = lookback_periods
        self.max_pivots = max_pivots_per_side
        self.merge_threshold = merge_threshold_pct

        # Store detected pivots
        self.resistances: List[SimplePivot] = []
        self.supports: List[SimplePivot] = []

    def detect_pivots(self, ohlcv_data: np.ndarray, session_start_idx: int = None, current_only: bool = False) -> Dict:
        """
        Detect pivots using rolling window method (matches TradingView Pine Script)

        Algorithm matches tradingview_pivot_rolling.pine:
        1. Divide session into windows of lookback bars (0-99, 100-199, etc.)
        2. For current window: calculate dynamic high/low from window start to now
        3. Store completed windows as historical pivots
        4. Return all active pivots (current + historical) or only current

        Args:
            ohlcv_data: Array with [timestamp, open, high, low, close, volume]
            session_start_idx: Index where current session started (for day reset)
            current_only: If True, return only current window pivots (for frontend display)

        Returns:
            Dictionary with 'resistances' and 'supports' lists
        """
        if len(ohlcv_data) == 0:
            return {'resistances': [], 'supports': []}

        highs = ohlcv_data[:, 2]
        lows = ohlcv_data[:, 3]
        current_price = ohlcv_data[-1, 4]

        # If no session start provided, use all data
        if session_start_idx is None:
            session_start_idx = 0

        # Calculate bars since session start
        bars_in_session = len(ohlcv_data) - session_start_idx

        # Current window number and position
        window_number = bars_in_session // self.lookback
        bars_in_window = bars_in_session % self.lookback

        all_resistances = []
        all_supports = []

        # Process completed windows (these are frozen pivots) - skip if current_only
        if not current_only:
            for win_num in range(window_number):
                win_start = session_start_idx + (win_num * self.lookback)
                win_end = win_start + self.lookback

                if win_end <= len(ohlcv_data):
                    window_highs = highs[win_start:win_end]
                    window_lows = lows[win_start:win_end]

                    max_high = np.max(window_highs)
                    min_low = np.min(window_lows)
                    max_idx = win_start + np.argmax(window_highs)
                    min_idx = win_start + np.argmin(window_lows)

                    # Resistance from completed window
                    all_resistances.append({
                        'price': max_high,
                        'index': max_idx,
                        'bars_ago': len(ohlcv_data) - max_idx - 1,
                        'window': win_num,
                        'completed': True
                    })

                    # Support from completed window
                    all_supports.append({
                        'price': min_low,
                        'index': min_idx,
                        'bars_ago': len(ohlcv_data) - min_idx - 1,
                        'window': win_num,
                        'completed': True
                    })

        # Process CURRENT window (dynamic, updates every bar)
        if bars_in_window > 0:
            window_start_idx = session_start_idx + (window_number * self.lookback)
            lookback_bars = min(bars_in_window, len(ohlcv_data) - window_start_idx)

            if lookback_bars > 0:
                window_highs = highs[window_start_idx:window_start_idx + lookback_bars]
                window_lows = lows[window_start_idx:window_start_idx + lookback_bars]

                max_high = np.max(window_highs)
                min_low = np.min(window_lows)
                max_idx = window_start_idx + np.argmax(window_highs)
                min_idx = window_start_idx + np.argmin(window_lows)

                # Current resistance (dynamic)
                all_resistances.append({
                    'price': max_high,
                    'index': max_idx,
                    'bars_ago': len(ohlcv_data) - max_idx - 1,
                    'window': window_number,
                    'completed': False
                })

                # Current support (dynamic)
                all_supports.append({
                    'price': min_low,
                    'index': min_idx,
                    'bars_ago': len(ohlcv_data) - min_idx - 1,
                    'window': window_number,
                    'completed': False
                })

        # Convert to SimplePivot objects
        self.resistances = []
        for level in all_resistances:
            # Always include pivots (don't filter by active/inactive like before)
            strength = self._calculate_strength_simple(level, current_price)
            pivot = SimplePivot(
                price=level['price'],
                pivot_type='resistance',
                touches=1,
                bars_since_formation=level['bars_ago'],
                is_active=level['price'] > current_price,
                strength=strength
            )
            self.resistances.append(pivot)

        self.supports = []
        for level in all_supports:
            strength = self._calculate_strength_simple(level, current_price)
            pivot = SimplePivot(
                price=level['price'],
                pivot_type='support',
                touches=1,
                bars_since_formation=level['bars_ago'],
                is_active=level['price'] < current_price,
                strength=strength
            )
            self.supports.append(pivot)

        return {
            'resistances': self.resistances,
            'supports': self.supports
        }

    def _merge_levels(self, levels: List[Dict], current_price: float) -> List[Dict]:
        """
        Merge similar price levels

        Args:
            levels: List of price levels
            current_price: Current market price

        Returns:
            Merged list with touch counts
        """
        if not levels:
            return []

        # Sort by price
        sorted_levels = sorted(levels, key=lambda x: x['price'])

        merged = []
        current_cluster = [sorted_levels[0]]

        for level in sorted_levels[1:]:
            # Check if this level is close to current cluster
            cluster_price = current_cluster[0]['price']
            threshold = cluster_price * (self.merge_threshold / 100.0)

            if abs(level['price'] - cluster_price) <= threshold:
                # Add to cluster
                current_cluster.append(level)
            else:
                # Save current cluster and start new one
                merged.append(self._consolidate_cluster(current_cluster))
                current_cluster = [level]

        # Don't forget last cluster
        if current_cluster:
            merged.append(self._consolidate_cluster(current_cluster))

        return merged

    def _consolidate_cluster(self, cluster: List[Dict]) -> Dict:
        """
        Consolidate a cluster of similar levels into one

        Takes the most recent price and counts touches
        """
        # Use the most recent price (smallest bars_ago)
        most_recent = min(cluster, key=lambda x: x['bars_ago'])

        return {
            'price': most_recent['price'],
            'touches': len(cluster),
            'bars_ago': most_recent['bars_ago'],
            'index': most_recent['index']
        }

    def _calculate_strength_simple(self, level: Dict, current_price: float) -> float:
        """
        Calculate pivot strength based on recency and distance

        Args:
            level: Level dict with bars_ago
            current_price: Current market price

        Returns:
            Strength score (0-100)
        """
        strength = 60.0  # Base strength for rolling window pivot

        # Recency factor (0-30 points): Recent pivots within window
        bars_ago = level['bars_ago']
        if bars_ago < self.lookback / 3:  # First third of window
            recency_score = 30
        elif bars_ago < 2 * self.lookback / 3:  # Middle third
            recency_score = 20
        else:  # Last third
            recency_score = 10
        strength += recency_score

        # Distance factor (0-10 points): Closer pivots are stronger
        distance_pct = abs(level['price'] - current_price) / current_price * 100
        if distance_pct < 1.0:
            distance_score = 10
        elif distance_pct < 2.0:
            distance_score = 5
        else:
            distance_score = 0
        strength += distance_score

        return min(100.0, max(0.0, strength))

    def get_nearest_pivot(self, current_price: float, direction: str) -> SimplePivot:
        """
        Get nearest pivot in specified direction

        Args:
            current_price: Current market price
            direction: 'above' for resistance, 'below' for support

        Returns:
            Nearest pivot or None
        """
        if direction == "above":
            # Find nearest resistance
            candidates = [p for p in self.resistances if p.price > current_price]
            return min(candidates, key=lambda p: p.price) if candidates else None
        else:
            # Find nearest support
            candidates = [p for p in self.supports if p.price < current_price]
            return max(candidates, key=lambda p: p.price) if candidates else None

    def candle_touched_pivot(self, candle: np.ndarray, pivot: SimplePivot) -> bool:
        """
        Check if candle physically touched the pivot level

        Args:
            candle: OHLCV array [timestamp, open, high, low, close, volume]
            pivot: Pivot object

        Returns:
            True if candle touched the pivot
        """
        candle_high = candle[2]
        candle_low = candle[3]
        pivot_price = pivot.price

        return candle_low <= pivot_price <= candle_high


# Quick test
if __name__ == "__main__":
    print("Testing SimplePivotDetector...")

    # Generate test data
    np.random.seed(42)
    num_candles = 500

    timestamps = np.arange(1609459200000, 1609459200000 + num_candles * 60000, 60000)
    closes = 100 + np.cumsum(np.random.randn(num_candles) * 0.5)
    highs = closes + np.abs(np.random.randn(num_candles) * 2)
    lows = closes - np.abs(np.random.randn(num_candles) * 2)
    opens = closes + np.random.randn(num_candles)
    volumes = np.abs(np.random.randn(num_candles) * 10000)

    ohlcv = np.column_stack([timestamps, opens, highs, lows, closes, volumes])

    detector = SimplePivotDetector(lookback_periods=100, max_pivots_per_side=5)
    result = detector.detect_pivots(ohlcv)

    print(f"\nCurrent price: ${closes[-1]:.2f}")

    print(f"\nResistances found: {len(result['resistances'])}")
    for p in result['resistances']:
        print(f"  ${p.price:.2f} | Touches: {p.touches} | {p.bars_since_formation} bars ago")

    print(f"\nSupports found: {len(result['supports'])}")
    for p in result['supports']:
        print(f"  ${p.price:.2f} | Touches: {p.touches} | {p.bars_since_formation} bars ago")

    print("\n[OK] SimplePivotDetector test complete")
