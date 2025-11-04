"""
PupupuV2 Trading Strategy - Signal Generation Logic

Setup:
1. Price touches a pivot (resistance or support)
2. First candle that closes crossing EMA(12) confirms direction
3. Entry = price where candle crossed EMA
4. SL = pivot ± padding
5. TP = entry ± (1.7 * risk)

This is a SEMI-AUTOMATIC system - generates alerts for manual execution.
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime

from src.indicators.pivot_detector import PupupuPivotDetector, Pivot
from src.indicators.ema import calculate_ema, ema_cross_detection, get_ema_position


@dataclass
class TradeSignal:
    """Represents a generated trading signal."""
    direction: str  # "LONG" or "SHORT"
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size_usd: float
    confidence: float  # 0-1
    reason: str  # Setup description
    pivot_info: Dict
    timestamp: datetime
    risk_reward_ratio: float = 1.7
    risk_usd: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dict for JSON serialization."""
        return {
            'direction': self.direction,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'position_size_usd': self.position_size_usd,
            'confidence': self.confidence,
            'reason': self.reason,
            'pivot_info': self.pivot_info,
            'timestamp': self.timestamp.isoformat(),
            'risk_reward_ratio': self.risk_reward_ratio,
            'risk_usd': self.risk_usd
        }

    def __str__(self):
        """Pretty print for console/logs."""
        return f"""
{'='*60}
{self.direction} SIGNAL - Confidence: {self.confidence:.1%}
{'='*60}
Entry:  ${self.entry_price:,.2f}
SL:     ${self.stop_loss:,.2f}
TP:     ${self.take_profit:,.2f}
R:R:    1:{self.risk_reward_ratio}
Risk:   ${self.risk_usd:,.2f}
Size:   ${self.position_size_usd:,.2f}

Reason: {self.reason}
Pivot:  ${self.pivot_info['price']:.2f} (touches={self.pivot_info['touches']}, strength={self.pivot_info['strength']:.2f})
Time:   {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}
"""


class PupupuV2Strategy:
    """
    Implementation of pupupuv2 scalping strategy.

    Config params match TradingView Pupupu indicator:
    - EMA period: 12
    - Lookback: 400 periods (~33h on 5min)
    - SL padding: 2.5 points
    - TP R:R: 1.7
    """

    def __init__(self, config: Optional[Dict] = None):
        if config is None:
            config = {}

        self.ema_period = config.get('ema_period', 12)
        self.lookback_periods = config.get('lookback_periods', 400)
        self.swing_bars = config.get('swing_bars', 5)
        self.tp_rr = config.get('tp_rr', 1.7)
        self.sl_padding_pts = config.get('sl_padding', 2.5)

        # Pivot detector
        self.pivot_detector = PupupuPivotDetector(
            lookback_periods=self.lookback_periods,
            swing_detection_bars=self.swing_bars,
            break_tolerance_pct=config.get('break_tolerance', 0.2),
            touch_tolerance_pct=config.get('touch_tolerance', 0.15)
        )

        # Track state
        self.last_pivot_touch = {}  # Prevent multiple signals from same touch
        self.last_signal_time = None
        self.cooldown_candles = config.get('cooldown_candles', 5)  # Min candles between signals

    def analyze_for_signals(
        self,
        ohlcv_data: np.ndarray,
        vp_data: Optional[Dict] = None
    ) -> Optional[TradeSignal]:
        """
        Analyze OHLCV data and generate signal if valid setup found.

        Args:
            ohlcv_data: Full OHLCV array (timestamp, o, h, l, c, v)
            vp_data: Optional Volume Profile data for confluence boost

        Returns:
            TradeSignal if valid setup, None otherwise
        """
        if len(ohlcv_data) < self.ema_period + 10:
            return None

        # 1. Calculate EMA
        closes = ohlcv_data[:, 4]
        ema_values = calculate_ema(closes, self.ema_period)

        if np.isnan(ema_values[-1]):
            return None

        # 2. Detect all pivots
        pivots = self.pivot_detector.detect_pivots(ohlcv_data)

        # 3. Update active pivots with latest candle
        last_candle = self._candle_dict(ohlcv_data[-1])

        self.pivot_detector.active_resistances = \
            self.pivot_detector.update_pivot_status(last_candle, pivots['resistances'])
        self.pivot_detector.active_supports = \
            self.pivot_detector.update_pivot_status(last_candle, pivots['supports'])

        # 4. Get current state
        current_price = last_candle['close']
        current_ema = ema_values[-1]
        previous_close = closes[-2]

        # 5. Check for SHORT setup (resistance touch + bearish EMA cross)
        signal = self._check_short_setup(
            last_candle, current_price, current_ema, previous_close, vp_data
        )

        if signal:
            return signal

        # 6. Check for LONG setup (support touch + bullish EMA cross)
        signal = self._check_long_setup(
            last_candle, current_price, current_ema, previous_close, vp_data
        )

        return signal

    def _check_short_setup(
        self,
        candle: Dict,
        current_price: float,
        current_ema: float,
        previous_close: float,
        vp_data: Optional[Dict]
    ) -> Optional[TradeSignal]:
        """Check for SHORT signal setup."""

        # Find nearest resistance above current price
        nearest_resistance = self.pivot_detector.get_nearest_pivot(current_price, "above")

        if not nearest_resistance:
            return None

        # Check if candle touched the resistance
        if not self.pivot_detector.price_touched_pivot(candle, nearest_resistance):
            return None

        # Check for bearish EMA cross
        cross_type = ema_cross_detection(candle['close'], previous_close, current_ema)

        if cross_type == "cross_below":
            # VALID SHORT SETUP!
            return self._generate_short_signal(
                entry=current_ema,  # Entry at EMA cross point
                pivot=nearest_resistance,
                current_candle=candle,
                vp_data=vp_data
            )

        return None

    def _check_long_setup(
        self,
        candle: Dict,
        current_price: float,
        current_ema: float,
        previous_close: float,
        vp_data: Optional[Dict]
    ) -> Optional[TradeSignal]:
        """Check for LONG signal setup."""

        # Find nearest support below current price
        nearest_support = self.pivot_detector.get_nearest_pivot(current_price, "below")

        if not nearest_support:
            return None

        # Check if candle touched the support
        if not self.pivot_detector.price_touched_pivot(candle, nearest_support):
            return None

        # Check for bullish EMA cross
        cross_type = ema_cross_detection(candle['close'], previous_close, current_ema)

        if cross_type == "cross_above":
            # VALID LONG SETUP!
            return self._generate_long_signal(
                entry=current_ema,
                pivot=nearest_support,
                current_candle=candle,
                vp_data=vp_data
            )

        return None

    def _generate_short_signal(
        self,
        entry: float,
        pivot: Pivot,
        current_candle: Dict,
        vp_data: Optional[Dict]
    ) -> TradeSignal:
        """Generate complete SHORT signal with SL, TP, and confidence."""

        # SL above resistance + padding
        stop_loss = pivot.price + self.sl_padding_pts

        # Risk = distance from entry to SL
        risk = abs(entry - stop_loss)

        # TP below entry at R:R ratio
        take_profit = entry - (risk * self.tp_rr)

        # Calculate base confidence from pivot strength
        confidence = self._calculate_confidence(pivot, vp_data)

        return TradeSignal(
            direction="SHORT",
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size_usd=0,  # Set by risk manager
            confidence=confidence,
            reason=f"Resistance touch @ ${pivot.price:.2f} + bearish EMA cross",
            pivot_info={
                'price': pivot.price,
                'touches': pivot.touches,
                'strength': pivot.strength,
                'age_candles': pivot.candles_age
            },
            timestamp=datetime.now(),
            risk_reward_ratio=self.tp_rr,
            risk_usd=0  # Set by risk manager
        )

    def _generate_long_signal(
        self,
        entry: float,
        pivot: Pivot,
        current_candle: Dict,
        vp_data: Optional[Dict]
    ) -> TradeSignal:
        """Generate complete LONG signal with SL, TP, and confidence."""

        # SL below support - padding
        stop_loss = pivot.price - self.sl_padding_pts

        # Risk = distance from entry to SL
        risk = abs(entry - stop_loss)

        # TP above entry at R:R ratio
        take_profit = entry + (risk * self.tp_rr)

        # Calculate confidence
        confidence = self._calculate_confidence(pivot, vp_data)

        return TradeSignal(
            direction="LONG",
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size_usd=0,
            confidence=confidence,
            reason=f"Support touch @ ${pivot.price:.2f} + bullish EMA cross",
            pivot_info={
                'price': pivot.price,
                'touches': pivot.touches,
                'strength': pivot.strength,
                'age_candles': pivot.candles_age
            },
            timestamp=datetime.now(),
            risk_reward_ratio=self.tp_rr,
            risk_usd=0
        )

    def _calculate_confidence(
        self,
        pivot: Pivot,
        vp_data: Optional[Dict]
    ) -> float:
        """
        Calculate signal confidence (0-1).

        Factors:
        - Pivot strength (base)
        - Number of touches (more = stronger)
        - Volume Profile confluence (if available)
        """
        # Base confidence from pivot strength (0.4-0.9 range)
        base = pivot.strength * 0.5 + 0.4

        # Boost from multiple touches
        touch_boost = min(0.1, (pivot.touches - 1) * 0.03)

        # Boost if aligns with Volume Profile HVN
        vp_boost = 0.0
        if vp_data:
            vp_boost = self._check_vp_confluence(pivot.price, vp_data)

        confidence = base + touch_boost + vp_boost

        return min(0.95, max(0.3, confidence))

    def _check_vp_confluence(self, pivot_price: float, vp_data: Dict) -> float:
        """
        Check if pivot aligns with Volume Profile HVN nodes.

        Returns:
            Boost value (0-0.15) based on proximity to HVN
        """
        # Check VP_medio (24h context) for confluence
        vp_medio = vp_data.get('vp_medio')
        if not vp_medio:
            return 0.0

        hvn_nodes = vp_medio.get('hvn', [])

        for hvn_price in hvn_nodes[:3]:  # Check top 3 HVNs
            price_diff_pct = abs(hvn_price - pivot_price) / pivot_price * 100

            if price_diff_pct < 0.2:  # Within 0.2%
                return 0.15  # Strong confluence
            elif price_diff_pct < 0.5:  # Within 0.5%
                return 0.08  # Moderate confluence

        return 0.0

    def _candle_dict(self, candle_array: np.ndarray) -> Dict:
        """Convert OHLCV array to dict."""
        return {
            'timestamp': candle_array[0],
            'open': candle_array[1],
            'high': candle_array[2],
            'low': candle_array[3],
            'close': candle_array[4],
            'volume': candle_array[5]
        }

    def get_active_levels(self) -> Dict[str, List[Pivot]]:
        """Get all currently active support/resistance levels."""
        return {
            'resistances': sorted(
                self.pivot_detector.active_resistances,
                key=lambda p: p.strength,
                reverse=True
            ),
            'supports': sorted(
                self.pivot_detector.active_supports,
                key=lambda p: p.strength,
                reverse=True
            )
        }


# Testing
if __name__ == "__main__":
    print("="*70)
    print("TESTING PUPUPUV2 STRATEGY")
    print("="*70)

    # Use real BTC data
    import sys
    sys.path.append('c:/repos/stock-analyzer')
    from test_vp_real_btc import fetch_binance_ohlcv

    print("\nFetching real BTC data from Binance...")
    ohlcv = fetch_binance_ohlcv(symbol='BTC/USDT', timeframe='5m', limit=500)

    # Initialize strategy
    strategy = PupupuV2Strategy({
        'ema_period': 12,
        'lookback_periods': 400,
        'tp_rr': 1.7,
        'sl_padding': 2.5
    })

    print("\nAnalyzing for signals...")
    signal = strategy.analyze_for_signals(ohlcv)

    if signal:
        print("\n[SIGNAL GENERATED]")
        print(signal)
    else:
        print("\n[NO SIGNAL] - No valid setup found")

        # Show active levels for context
        levels = strategy.get_active_levels()
        print(f"\nActive resistances: {len(levels['resistances'])}")
        print(f"Active supports: {len(levels['supports'])}")

        if levels['resistances']:
            print("\nTop 3 resistances:")
            for p in levels['resistances'][:3]:
                print(f"  ${p.price:,.2f} - strength={p.strength:.2f}, touches={p.touches}")

        if levels['supports']:
            print("\nTop 3 supports:")
            for p in levels['supports'][:3]:
                print(f"  ${p.price:,.2f} - strength={p.strength:.2f}, touches={p.touches}")

    print("\n" + "="*70)
