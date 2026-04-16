"""
PupupuV3 Signal Generator
Complete signal generation logic for the improved scalping strategy

Key Features:
- 1-minute timeframe
- EMA(15) for trend
- Pivot detection (100 lookback)
- VWAP filter for directional bias
- 7-day Volume Profile only
- ML prediction integration
- Dynamic risk management
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Import V3 components
# Imports

from src.indicators.ema import calculate_ema, ema_cross_detection
from src.indicators.pivot_detector_simple import SimplePivotDetector, SimplePivot
from src.indicators.vwap import (
    calculate_vwap_with_session_reset,
    get_vwap_position,
    should_allow_trade
)
from src.indicators.volume_profile import (
    get_7d_volume_profile,
    get_vp_context
)


@dataclass
class TradeSignal:
    """Complete trade signal with all parameters"""
    signal_id: str
    timestamp: int
    symbol: str
    direction: str  # 'LONG' or 'SHORT'

    # Entry and risk management
    entry_price: float
    stop_loss: float
    take_profit_1: float  # TP1 at 1:1 ratio

    # Signal details
    pivot_price: float
    pivot_type: str  # 'resistance' or 'support'
    pivot_strength: float
    ema_value: float
    cross_type: str  # 'cross_above' or 'cross_below'

    # VWAP filter
    vwap_value: float
    vwap_bias: str  # 'bullish' | 'bearish' | 'neutral'
    with_vwap_bias: bool  # True if trading with VWAP, False if against

    # Volume Profile context
    vp_poc: float
    vp_in_value_area: bool
    vp_near_hvn: bool

    # ML prediction
    ml_confidence: float

    # Risk parameters
    risk_usd: float
    position_size_usd: float
    risk_multiplier: float  # 1.0 for full risk, 0.5 for reduced

    # Additional info
    reason: str  # Why this signal was generated
    is_valid: bool  # Whether signal passed all filters


class PupupuV3Strategy:
    """
    Main strategy class for PupupuV3 signal generation
    """

    def __init__(self, config: Dict):
        """
        Args:
            config: Dictionary with strategy parameters
        """
        self.config = config

        # Strategy parameters
        self.ema_period = config.get('ema_period', 15)
        self.pivot_lookback = config.get('pivot_lookback', 100)
        self.capital = config.get('capital_crypto', 30000)
        self.risk_per_trade_pct = config.get('risk_per_trade_pct', 0.02)
        self.risk_reduced_pct = config.get('risk_reduced_pct', 0.01)
        self.tp1_ratio = config.get('tp1_ratio', 1.0)
        self.pivot_touch_threshold = config.get('pivot_touch_threshold', 0.1)

        # Initialize components - Using SimplePivotDetector (rolling high/low method)
        self.pivot_detector = SimplePivotDetector(
            lookback_periods=self.pivot_lookback,
            max_pivots_per_side=10,  # Show more levels
            merge_threshold_pct=0.3  # Merge similar levels within 0.3%
        )

        # ML predictor (placeholder - will be integrated later)
        self.ml_predictor = None

    def analyze_for_signals(
        self,
        ohlcv_data: np.ndarray,
        symbol: str = "BTC/USDT"
    ) -> Optional[TradeSignal]:
        """
        Analyze market data and generate signal if conditions are met

        Args:
            ohlcv_data: Array with [timestamp, open, high, low, close, volume]
            symbol: Trading pair symbol

        Returns:
            TradeSignal if all conditions met, None otherwise
        """
        if len(ohlcv_data) < max(self.ema_period, self.pivot_lookback):
            return None

        # Extract current and previous candle data
        current_candle = ohlcv_data[-1]
        previous_candle = ohlcv_data[-2]

        current_timestamp = int(current_candle[0])
        current_open = current_candle[1]
        current_close = current_candle[4]
        previous_close = previous_candle[4]

        # 1. Calculate EMA(15)
        closes = ohlcv_data[:, 4]
        ema_values = calculate_ema(closes, period=self.ema_period)
        current_ema = ema_values[-1]
        previous_ema = ema_values[-2]

        # 2. Detect EMA cross (intra-candle preferred: open < ema < close)
        cross_type = ema_cross_detection(
            current_close,
            previous_close,
            current_ema,
            current_open=current_open,
            previous_ema=previous_ema
        )

        if cross_type is None:
            return None  # No cross detected

        # 3. Detect pivots
        pivot_result = self.pivot_detector.detect_pivots(ohlcv_data)

        # 4. Check for pivot touch + EMA cross combination
        # Look for pivot touch in CURRENT PIVOT WINDOW (last 100 candles)
        signal_direction = None
        active_pivot = None
        lookback_for_touch = self.pivot_lookback  # Check entire pivot window (100 candles)

        if cross_type == "cross_above":
            # Bullish signal - look for support touch in current pivot window
            nearest_support = self.pivot_detector.get_nearest_pivot(current_close, "below")

            if nearest_support:
                # Check if any candle in current pivot window touched the support
                touched = False
                for i in range(1, min(lookback_for_touch + 1, len(ohlcv_data))):
                    candle = ohlcv_data[-i]
                    if self.pivot_detector.candle_touched_pivot(candle, nearest_support):
                        touched = True
                        break

                if touched:
                    signal_direction = "LONG"
                    active_pivot = nearest_support

        elif cross_type == "cross_below":
            # Bearish signal - look for resistance touch in current pivot window
            nearest_resistance = self.pivot_detector.get_nearest_pivot(current_close, "above")

            if nearest_resistance:
                # Check if any candle in current pivot window touched the resistance
                touched = False
                for i in range(1, min(lookback_for_touch + 1, len(ohlcv_data))):
                    candle = ohlcv_data[-i]
                    if self.pivot_detector.candle_touched_pivot(candle, nearest_resistance):
                        touched = True
                        break

                if touched:
                    signal_direction = "SHORT"
                    active_pivot = nearest_resistance

        if signal_direction is None or active_pivot is None:
            return None  # No valid pivot touch + cross combination

        # 5. Calculate VWAP and check bias
        vwap_values = calculate_vwap_with_session_reset(ohlcv_data, session_start_hour=0)
        current_vwap = vwap_values[-1]

        vwap_position = get_vwap_position(current_close, current_vwap)

        # 6. Get ML prediction (placeholder - returns 50% for now)
        ml_confidence = self._get_ml_prediction(ohlcv_data, signal_direction)

        # 7. Check if trade is allowed by VWAP filter
        allow_trade, reason, risk_multiplier = should_allow_trade(
            signal_direction,
            vwap_position,
            ml_confidence
        )

        if not allow_trade:
            # Generate signal but mark as invalid for logging
            return self._create_signal(
                symbol=symbol,
                direction=signal_direction,
                timestamp=current_timestamp,
                current_price=current_close,
                pivot=active_pivot,
                ema_value=current_ema,
                cross_type=cross_type,
                vwap_position=vwap_position,
                ml_confidence=ml_confidence,
                risk_multiplier=0.0,
                is_valid=False,
                reason=reason,
                ohlcv_data=ohlcv_data
            )

        # 8. Calculate Volume Profile context
        vp_7d = get_7d_volume_profile(ohlcv_data, num_bins=60)
        vp_context = get_vp_context(current_close, vp_7d) if vp_7d else {}

        # 9. Calculate entry, SL, and TP
        entry_price = current_close

        if signal_direction == "LONG":
            # SL at pivot - 2.5 points
            stop_loss = active_pivot.price - 2.5
            # TP1 at 1:1 ratio
            risk_per_trade = entry_price - stop_loss
            take_profit_1 = entry_price + (risk_per_trade * self.tp1_ratio)
        else:  # SHORT
            # SL at pivot + 2.5 points
            stop_loss = active_pivot.price + 2.5
            # TP1 at 1:1 ratio
            risk_per_trade = stop_loss - entry_price
            take_profit_1 = entry_price - (risk_per_trade * self.tp1_ratio)

        # 10. Calculate position size
        base_risk_usd = self.capital * self.risk_per_trade_pct  # $600
        actual_risk_usd = base_risk_usd * risk_multiplier  # $600 or $300

        price_diff = abs(entry_price - stop_loss)
        if price_diff > 0:
            position_size_usd = (actual_risk_usd / price_diff) * entry_price
        else:
            return None  # Invalid SL

        # 11. Generate final signal
        with_vwap_bias = (
            (signal_direction == "LONG" and vwap_position['directional_bias'] == 'bullish') or
            (signal_direction == "SHORT" and vwap_position['directional_bias'] == 'bearish')
        )

        return TradeSignal(
            signal_id=f"{symbol}_{current_timestamp}",
            timestamp=current_timestamp,
            symbol=symbol,
            direction=signal_direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            pivot_price=active_pivot.price,
            pivot_type=active_pivot.pivot_type,
            pivot_strength=active_pivot.strength,
            ema_value=current_ema,
            cross_type=cross_type,
            vwap_value=current_vwap,
            vwap_bias=vwap_position['directional_bias'],
            with_vwap_bias=with_vwap_bias,
            vp_poc=vp_context.get('poc', 0.0),
            vp_in_value_area=vp_context.get('in_value_area', False),
            vp_near_hvn=vp_context.get('near_hvn', False),
            ml_confidence=ml_confidence,
            risk_usd=actual_risk_usd,
            position_size_usd=position_size_usd,
            risk_multiplier=risk_multiplier,
            reason=reason,
            is_valid=True
        )

    def _create_signal(
        self,
        symbol: str,
        direction: str,
        timestamp: int,
        current_price: float,
        pivot: SimplePivot,
        ema_value: float,
        cross_type: str,
        vwap_position: Dict,
        ml_confidence: float,
        risk_multiplier: float,
        is_valid: bool,
        reason: str,
        ohlcv_data: np.ndarray
    ) -> TradeSignal:
        """Helper to create signal object (for invalid signals too)"""

        # Calculate basic SL and TP even for invalid signals
        if direction == "LONG":
            stop_loss = pivot.price - 2.5
            risk = current_price - stop_loss
            take_profit_1 = current_price + risk
        else:
            stop_loss = pivot.price + 2.5
            risk = stop_loss - current_price
            take_profit_1 = current_price - risk

        # VP context
        vp_7d = get_7d_volume_profile(ohlcv_data, num_bins=60)
        vp_context = get_vp_context(current_price, vp_7d) if vp_7d else {}

        return TradeSignal(
            signal_id=f"{symbol}_{timestamp}",
            timestamp=timestamp,
            symbol=symbol,
            direction=direction,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            pivot_price=pivot.price,
            pivot_type=pivot.pivot_type,
            pivot_strength=pivot.strength,
            ema_value=ema_value,
            cross_type=cross_type,
            vwap_value=vwap_position['vwap_value'],
            vwap_bias=vwap_position['directional_bias'],
            with_vwap_bias=False,
            vp_poc=vp_context.get('poc', 0.0),
            vp_in_value_area=vp_context.get('in_value_area', False),
            vp_near_hvn=vp_context.get('near_hvn', False),
            ml_confidence=ml_confidence,
            risk_usd=0.0,
            position_size_usd=0.0,
            risk_multiplier=risk_multiplier,
            reason=reason,
            is_valid=is_valid
        )

    def _get_ml_prediction(self, ohlcv_data: np.ndarray, direction: str) -> float:
        """
        Get ML prediction confidence

        TODO: Integrate actual ML model (Random Forest + XGBoost)
        For now, returns 50% as placeholder
        """
        if self.ml_predictor is None:
            return 50.0

        # Future: Extract features and run prediction
        # features = extract_features(ohlcv_data)
        # confidence = self.ml_predictor.predict(features)
        # return confidence

        return 50.0


def signal_to_dict(signal: TradeSignal) -> Dict:
    """Convert TradeSignal to dictionary for JSON serialization"""
    return {
        'signal_id': signal.signal_id,
        'timestamp': signal.timestamp,
        'datetime': datetime.fromtimestamp(signal.timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S'),
        'symbol': signal.symbol,
        'direction': signal.direction,
        'entry_price': round(signal.entry_price, 2),
        'stop_loss': round(signal.stop_loss, 2),
        'take_profit_1': round(signal.take_profit_1, 2),
        'pivot_price': round(signal.pivot_price, 2),
        'pivot_type': signal.pivot_type,
        'pivot_strength': round(signal.pivot_strength, 2),
        'ema_value': round(signal.ema_value, 2),
        'cross_type': signal.cross_type,
        'vwap_value': round(signal.vwap_value, 2),
        'vwap_bias': signal.vwap_bias,
        'with_vwap_bias': signal.with_vwap_bias,
        'vp_poc': round(signal.vp_poc, 2),
        'vp_in_value_area': signal.vp_in_value_area,
        'vp_near_hvn': signal.vp_near_hvn,
        'ml_confidence': round(signal.ml_confidence, 2),
        'risk_usd': round(signal.risk_usd, 2),
        'position_size_usd': round(signal.position_size_usd, 2),
        'risk_multiplier': signal.risk_multiplier,
        'reason': signal.reason,
        'is_valid': signal.is_valid
    }


# Test function
if __name__ == "__main__":
    print("Testing PupupuV3 Strategy Signal Generator...")

    # Configuration
    config = {
        'ema_period': 15,
        'pivot_lookback': 100,
        'capital_crypto': 30000,
        'risk_per_trade_pct': 0.02,
        'risk_reduced_pct': 0.01,
        'tp1_ratio': 1.0,
        'pivot_touch_threshold': 0.1
    }

    # Initialize strategy
    strategy = PupupuV3Strategy(config)

    # Generate test data (10,080 candles = 7 days of 1-min data)
    np.random.seed(42)
    num_candles = 10080

    timestamps = np.arange(1609459200000, 1609459200000 + num_candles * 60000, 60000)

    # Create price pattern with pivot touch
    base_price = 43000
    closes = []

    for i in range(num_candles):
        if i < 5000:
            # Downtrend to create support pivot
            closes.append(base_price - (i / 50))
        elif i < 5100:
            # Touch support
            closes.append(base_price - 100 + np.random.randn() * 5)
        else:
            # Uptrend after support touch
            closes.append(base_price - 100 + ((i - 5100) / 20))

    closes = np.array(closes)
    highs = closes + np.abs(np.random.randn(num_candles) * 10)
    lows = closes - np.abs(np.random.randn(num_candles) * 10)
    opens = closes + np.random.randn(num_candles) * 5
    volumes = np.abs(np.random.randn(num_candles) * 500000) + 1000000

    ohlcv_data = np.column_stack([timestamps, opens, highs, lows, closes, volumes])

    print(f"\nGenerated {len(ohlcv_data)} candles of test data")
    print(f"Price range: ${lows.min():.2f} - ${highs.max():.2f}")

    # Analyze for signals at various points
    test_points = [5050, 5100, 5150, 5200]

    for idx in test_points:
        print(f"\n=== Testing at candle {idx} ===")
        signal = strategy.analyze_for_signals(ohlcv_data[:idx], symbol="BTC/USDT")

        if signal:
            print(f"SIGNAL FOUND: {signal.direction}")
            print(f"  Valid: {signal.is_valid}")
            print(f"  Entry: ${signal.entry_price:.2f}")
            print(f"  SL: ${signal.stop_loss:.2f}")
            print(f"  TP1: ${signal.take_profit_1:.2f}")
            print(f"  Risk: ${signal.risk_usd:.2f}")
            print(f"  Position Size: ${signal.position_size_usd:.2f}")
            print(f"  VWAP Bias: {signal.vwap_bias}")
            print(f"  With VWAP: {signal.with_vwap_bias}")
            print(f"  ML Confidence: {signal.ml_confidence:.1f}%")
            print(f"  Reason: {signal.reason}")
        else:
            print("  No signal")

    print("\n[OK] PupupuV3 Strategy tests complete")
