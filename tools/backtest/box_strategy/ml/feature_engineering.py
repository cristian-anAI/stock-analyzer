"""
Feature Engineering for Box Strategy ML

Extracts 50+ features from trading data including:
- Box characteristics (range, formation quality, breakout strength)
- Technical indicators (RSI, ATR, Bollinger Bands, MACD, EMA)
- Market conditions (volatility, volume, trend, time patterns)
- Price action patterns (candle patterns, support/resistance)
- Historical context (recent performance, correlations)
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')

# Try to import ta (Technical Analysis library)
try:
    import ta
    from ta.momentum import RSIIndicator, StochasticOscillator
    from ta.volatility import BollingerBands, AverageTrueRange
    from ta.trend import MACD, EMAIndicator, SMAIndicator
    from ta.volume import OnBalanceVolumeIndicator
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False
    print("WARNING: 'ta' library not installed. Install with: pip install ta")

from .ml_config import ML_CONFIG


@dataclass
class TradeFeatures:
    """Container for all extracted features"""
    # Target variable
    target: int  # 1 = win, 0 = loss

    # Box characteristics (8 features)
    box_range: float
    box_range_percentile: float
    box_high: float
    box_low: float
    box_midpoint: float
    box_formation_quality: float  # 0-1 score
    box_volatility_ratio: float
    candles_in_box: int

    # Entry characteristics (7 features)
    breakout_strength: float  # How far price closed beyond box
    entry_delay_minutes: float  # Time from breakout to entry
    entry_price_vs_box_pct: float  # Entry vs box edge
    stop_distance: float
    risk_points: float
    stop_to_atr_ratio: float
    initial_risk_reward: float

    # Technical indicators - 5min (11 features)
    rsi_5min_14: float
    rsi_5min_21: float
    rsi_divergence_5min: float  # -1 = bearish div, 0 = no div, 1 = bullish div
    macd_5min: float
    macd_signal_5min: float
    macd_hist_5min: float
    bb_position_5min: float  # Position within Bollinger Bands
    bb_width_5min: float
    atr_5min: float
    ema_9_5min: float
    volume_ratio_5min: float

    # Technical indicators - 1hour (5 features)
    rsi_1hour_14: float
    macd_1hour: float
    bb_position_1hour: float
    atr_1hour: float
    trend_1hour: float  # -1, 0, 1

    # Market conditions (8 features)
    hour_of_day: int
    day_of_week: int
    is_market_open: int
    volatility_environment: float  # Recent ATR percentile
    volume_environment: float  # Recent volume percentile
    market_trend_5d: float
    market_trend_10d: float
    market_trend_20d: float

    # Price action patterns (5 features)
    breakout_candle_size: float
    breakout_candle_body_pct: float  # Body vs total range
    previous_candle_direction: int  # 1 = up, -1 = down, 0 = doji
    price_momentum: float
    volume_spike: float  # Volume vs average

    # Trade metadata (5 features)
    direction: int  # 1 = LONG, -1 = SHORT
    market_code: str  # Categorical feature
    liquidity_rating: int
    point_value: float
    typical_box_range_min: float

    def to_dict(self) -> Dict:
        """Convert to dictionary for DataFrame"""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    def to_array(self, exclude_target: bool = False, exclude_categorical: bool = True) -> np.ndarray:
        """Convert to numpy array (numerical features only)"""
        features = []
        for key, value in self.__dict__.items():
            if exclude_target and key == 'target':
                continue
            if exclude_categorical and key == 'market_code':
                continue
            if isinstance(value, (int, float)):
                features.append(value)
        return np.array(features)


class FeatureEngineer:
    """Extract features from trading data for ML models"""

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize feature engineer

        Args:
            config: Optional configuration dict (uses ML_CONFIG if not provided)
        """
        self.config = config or ML_CONFIG['feature_engineering']

        # RSI periods
        self.rsi_periods = self.config.get('rsi_periods', [14, 21])

        # ATR period
        self.atr_period = self.config.get('atr_period', 14)

        # Bollinger Bands
        self.bb_period = self.config.get('bollinger_period', 20)
        self.bb_std = self.config.get('bollinger_std', 2)

        # MACD
        self.macd_fast = self.config.get('macd_fast', 12)
        self.macd_slow = self.config.get('macd_slow', 26)
        self.macd_signal = self.config.get('macd_signal', 9)

        # EMA periods
        self.ema_periods = self.config.get('ema_periods', [9, 21, 50])

        # Volume MA
        self.volume_ma_period = self.config.get('volume_ma_period', 20)

        # Lookback periods
        self.box_range_lookback = self.config.get('box_range_lookback', 20)
        self.market_trend_periods = self.config.get('market_trend_periods', [5, 10, 20])

        print(f"FeatureEngineer initialized (TA available: {TA_AVAILABLE})")

    def extract_features_from_trade(
        self,
        trade_data: Dict,
        df_5min: pd.DataFrame,
        df_1hour: Optional[pd.DataFrame] = None,
        market_config: Optional[Dict] = None
    ) -> TradeFeatures:
        """
        Extract all features from a single trade

        Args:
            trade_data: Dictionary with trade information
            df_5min: 5-minute OHLCV data
            df_1hour: 1-hour OHLCV data (optional)
            market_config: Market configuration (point_value, liquidity, etc.)

        Returns:
            TradeFeatures object with all extracted features
        """
        # Parse trade data
        entry_time = pd.to_datetime(trade_data['entry_time'])
        direction = 1 if trade_data['direction'] == 'LONG' else -1
        pnl_points = trade_data['pnl_points']
        target = 1 if pnl_points > 0 else 0  # Binary classification: win/loss

        # Get data before entry
        df_before_entry = df_5min[df_5min.index < entry_time].copy()

        if df_before_entry.empty or len(df_before_entry) < 50:
            # Not enough data for feature calculation
            return self._create_default_features(target)

        # ===================================================================
        # BOX CHARACTERISTICS
        # ===================================================================
        box_high = trade_data['box_high']
        box_low = trade_data['box_low']
        box_range = trade_data['box_range']
        box_midpoint = (box_high + box_low) / 2

        # Box range percentile (vs recent boxes)
        recent_ranges = df_before_entry['High'].rolling(window=5).max() - df_before_entry['Low'].rolling(window=5).min()
        recent_ranges = recent_ranges.dropna()
        box_range_percentile = (recent_ranges < box_range).sum() / len(recent_ranges) if len(recent_ranges) > 0 else 0.5

        # Box formation quality (higher = cleaner box)
        box_candles = df_before_entry.tail(18)  # Approx 1.5 hours of 5min candles
        candles_in_box = len(box_candles)
        touches_high = (box_candles['High'] >= box_high * 0.99).sum()
        touches_low = (box_candles['Low'] <= box_low * 1.01).sum()
        box_formation_quality = min((touches_high + touches_low) / (candles_in_box * 2), 1.0)

        # Box volatility ratio (box range vs recent ATR)
        if TA_AVAILABLE:
            atr_indicator = AverageTrueRange(
                high=df_before_entry['High'],
                low=df_before_entry['Low'],
                close=df_before_entry['Close'],
                window=self.atr_period
            )
            recent_atr = atr_indicator.average_true_range().iloc[-1]
            box_volatility_ratio = box_range / recent_atr if recent_atr > 0 else 1.0
        else:
            box_volatility_ratio = 1.0

        # ===================================================================
        # ENTRY CHARACTERISTICS
        # ===================================================================
        entry_price = trade_data['entry_price']
        stop_loss = trade_data['stop_loss']
        risk_points = trade_data['risk_points']

        # Breakout strength (how far close was beyond box)
        breakout_candle = df_5min[df_5min.index <= entry_time].iloc[-1]
        if direction == 1:  # LONG
            breakout_strength = (breakout_candle['Close'] - box_high) / box_range if box_range > 0 else 0
            entry_price_vs_box_pct = (entry_price - box_high) / box_high * 100
        else:  # SHORT
            breakout_strength = (box_low - breakout_candle['Close']) / box_range if box_range > 0 else 0
            entry_price_vs_box_pct = (box_low - entry_price) / box_low * 100

        # Entry delay (assumed box closed 1.5 hours before entry window)
        entry_delay_minutes = 0  # Simplified (would need box formation time)

        # Stop distance
        stop_distance = abs(entry_price - stop_loss)

        # Stop to ATR ratio
        if TA_AVAILABLE:
            stop_to_atr_ratio = stop_distance / recent_atr if recent_atr > 0 else 1.0
        else:
            stop_to_atr_ratio = 1.0

        # Initial risk:reward (assumes 1:1 TP1)
        initial_risk_reward = 1.0  # Strategy uses 1:1 for TP1

        # ===================================================================
        # TECHNICAL INDICATORS - 5MIN
        # ===================================================================
        if TA_AVAILABLE:
            # RSI
            rsi_14 = RSIIndicator(close=df_before_entry['Close'], window=14).rsi().iloc[-1]
            rsi_21 = RSIIndicator(close=df_before_entry['Close'], window=21).rsi().iloc[-1]

            # RSI Divergence Detection
            rsi_divergence = self._detect_rsi_divergence(df_before_entry, window=14, lookback=20)

            # MACD
            macd_indicator = MACD(
                close=df_before_entry['Close'],
                window_slow=self.macd_slow,
                window_fast=self.macd_fast,
                window_sign=self.macd_signal
            )
            macd = macd_indicator.macd().iloc[-1]
            macd_signal = macd_indicator.macd_signal().iloc[-1]
            macd_hist = macd_indicator.macd_diff().iloc[-1]

            # Bollinger Bands
            bb_indicator = BollingerBands(
                close=df_before_entry['Close'],
                window=self.bb_period,
                window_dev=self.bb_std
            )
            bb_high = bb_indicator.bollinger_hband().iloc[-1]
            bb_low = bb_indicator.bollinger_lband().iloc[-1]
            bb_mid = bb_indicator.bollinger_mavg().iloc[-1]
            current_price = df_before_entry['Close'].iloc[-1]
            bb_position = (current_price - bb_low) / (bb_high - bb_low) if (bb_high - bb_low) > 0 else 0.5
            bb_width = (bb_high - bb_low) / bb_mid if bb_mid > 0 else 0.1

            # ATR
            atr_5min = recent_atr

            # EMA
            ema_9 = EMAIndicator(close=df_before_entry['Close'], window=9).ema_indicator().iloc[-1]

            # Volume ratio
            volume_ma = df_before_entry['Volume'].rolling(window=self.volume_ma_period).mean().iloc[-1]
            volume_ratio = df_before_entry['Volume'].iloc[-1] / volume_ma if volume_ma > 0 else 1.0
        else:
            # Fallback values if ta library not available
            rsi_14 = rsi_21 = 50.0
            rsi_divergence = 0.0  # 0 = no divergence
            macd = macd_signal = macd_hist = 0.0
            bb_position = 0.5
            bb_width = 0.1
            atr_5min = box_range
            ema_9 = df_before_entry['Close'].iloc[-1]
            volume_ratio = 1.0

        # ===================================================================
        # TECHNICAL INDICATORS - 1HOUR
        # ===================================================================
        if df_1hour is not None and not df_1hour.empty and TA_AVAILABLE:
            df_1hour_before = df_1hour[df_1hour.index < entry_time]

            if len(df_1hour_before) > 50:
                # RSI
                rsi_1hour = RSIIndicator(close=df_1hour_before['Close'], window=14).rsi().iloc[-1]

                # MACD
                macd_1hour_indicator = MACD(close=df_1hour_before['Close'])
                macd_1hour = macd_1hour_indicator.macd_diff().iloc[-1]

                # Bollinger Bands
                bb_1hour_indicator = BollingerBands(close=df_1hour_before['Close'], window=20)
                bb_1hour_high = bb_1hour_indicator.bollinger_hband().iloc[-1]
                bb_1hour_low = bb_1hour_indicator.bollinger_lband().iloc[-1]
                price_1hour = df_1hour_before['Close'].iloc[-1]
                bb_position_1hour = (price_1hour - bb_1hour_low) / (bb_1hour_high - bb_1hour_low) if (bb_1hour_high - bb_1hour_low) > 0 else 0.5

                # ATR
                atr_1hour = AverageTrueRange(
                    high=df_1hour_before['High'],
                    low=df_1hour_before['Low'],
                    close=df_1hour_before['Close'],
                    window=14
                ).average_true_range().iloc[-1]

                # Trend
                ema_20 = EMAIndicator(close=df_1hour_before['Close'], window=20).ema_indicator().iloc[-1]
                ema_50 = EMAIndicator(close=df_1hour_before['Close'], window=50).ema_indicator().iloc[-1]
                if ema_20 > ema_50 * 1.01:
                    trend_1hour = 1.0  # Uptrend
                elif ema_20 < ema_50 * 0.99:
                    trend_1hour = -1.0  # Downtrend
                else:
                    trend_1hour = 0.0  # Neutral
            else:
                rsi_1hour = 50.0
                macd_1hour = 0.0
                bb_position_1hour = 0.5
                atr_1hour = atr_5min
                trend_1hour = 0.0
        else:
            rsi_1hour = 50.0
            macd_1hour = 0.0
            bb_position_1hour = 0.5
            atr_1hour = atr_5min
            trend_1hour = 0.0

        # ===================================================================
        # MARKET CONDITIONS
        # ===================================================================
        hour_of_day = entry_time.hour
        day_of_week = entry_time.weekday()  # 0 = Monday, 6 = Sunday

        # Market hours (simplified - assumes 9:30-16:00 ET)
        market_open_time = time(9, 30)
        market_close_time = time(16, 0)
        entry_time_only = entry_time.time()
        is_market_open = 1 if market_open_time <= entry_time_only <= market_close_time else 0

        # Volatility environment (recent ATR percentile)
        if TA_AVAILABLE and len(df_before_entry) > 100:
            atr_series = AverageTrueRange(
                high=df_before_entry['High'],
                low=df_before_entry['Low'],
                close=df_before_entry['Close'],
                window=14
            ).average_true_range()
            recent_atr_values = atr_series.tail(100)
            volatility_environment = (recent_atr_values < recent_atr).sum() / len(recent_atr_values)
        else:
            volatility_environment = 0.5

        # Volume environment
        if len(df_before_entry) > 100:
            recent_volumes = df_before_entry['Volume'].tail(100)
            current_volume = df_before_entry['Volume'].iloc[-1]
            volume_environment = (recent_volumes < current_volume).sum() / len(recent_volumes)
        else:
            volume_environment = 0.5

        # Market trends (price change over different periods)
        market_trend_5d = self._calculate_trend(df_before_entry, 5)
        market_trend_10d = self._calculate_trend(df_before_entry, 10)
        market_trend_20d = self._calculate_trend(df_before_entry, 20)

        # ===================================================================
        # PRICE ACTION PATTERNS
        # ===================================================================
        # Breakout candle characteristics
        breakout_candle_high = breakout_candle['High']
        breakout_candle_low = breakout_candle['Low']
        breakout_candle_open = breakout_candle['Open']
        breakout_candle_close = breakout_candle['Close']

        breakout_candle_size = breakout_candle_high - breakout_candle_low
        candle_body = abs(breakout_candle_close - breakout_candle_open)
        breakout_candle_body_pct = candle_body / breakout_candle_size if breakout_candle_size > 0 else 0.5

        # Previous candle direction
        if len(df_before_entry) >= 2:
            prev_candle = df_before_entry.iloc[-2]
            if prev_candle['Close'] > prev_candle['Open'] * 1.001:
                previous_candle_direction = 1
            elif prev_candle['Close'] < prev_candle['Open'] * 0.999:
                previous_candle_direction = -1
            else:
                previous_candle_direction = 0
        else:
            previous_candle_direction = 0

        # Price momentum (rate of change)
        if len(df_before_entry) >= 10:
            price_momentum = (df_before_entry['Close'].iloc[-1] / df_before_entry['Close'].iloc[-10] - 1) * 100
        else:
            price_momentum = 0.0

        # Volume spike
        volume_spike = volume_ratio  # Already calculated above

        # ===================================================================
        # TRADE METADATA
        # ===================================================================
        market_code = trade_data.get('market', 'UNKNOWN')
        liquidity_rating = market_config.get('liquidity_rating', 3) if market_config else 3
        point_value = market_config.get('point_value', 50.0) if market_config else 50.0
        typical_box_range_min = market_config.get('typical_box_range', (5.0, 40.0))[0] if market_config else 5.0

        # ===================================================================
        # CREATE FEATURES OBJECT
        # ===================================================================
        features = TradeFeatures(
            # Target
            target=target,

            # Box characteristics
            box_range=box_range,
            box_range_percentile=box_range_percentile,
            box_high=box_high,
            box_low=box_low,
            box_midpoint=box_midpoint,
            box_formation_quality=box_formation_quality,
            box_volatility_ratio=box_volatility_ratio,
            candles_in_box=candles_in_box,

            # Entry characteristics
            breakout_strength=breakout_strength,
            entry_delay_minutes=entry_delay_minutes,
            entry_price_vs_box_pct=entry_price_vs_box_pct,
            stop_distance=stop_distance,
            risk_points=risk_points,
            stop_to_atr_ratio=stop_to_atr_ratio,
            initial_risk_reward=initial_risk_reward,

            # Technical indicators - 5min
            rsi_5min_14=rsi_14,
            rsi_5min_21=rsi_21,
            rsi_divergence_5min=rsi_divergence,
            macd_5min=macd,
            macd_signal_5min=macd_signal,
            macd_hist_5min=macd_hist,
            bb_position_5min=bb_position,
            bb_width_5min=bb_width,
            atr_5min=atr_5min,
            ema_9_5min=ema_9,
            volume_ratio_5min=volume_ratio,

            # Technical indicators - 1hour
            rsi_1hour_14=rsi_1hour,
            macd_1hour=macd_1hour,
            bb_position_1hour=bb_position_1hour,
            atr_1hour=atr_1hour,
            trend_1hour=trend_1hour,

            # Market conditions
            hour_of_day=hour_of_day,
            day_of_week=day_of_week,
            is_market_open=is_market_open,
            volatility_environment=volatility_environment,
            volume_environment=volume_environment,
            market_trend_5d=market_trend_5d,
            market_trend_10d=market_trend_10d,
            market_trend_20d=market_trend_20d,

            # Price action patterns
            breakout_candle_size=breakout_candle_size,
            breakout_candle_body_pct=breakout_candle_body_pct,
            previous_candle_direction=previous_candle_direction,
            price_momentum=price_momentum,
            volume_spike=volume_spike,

            # Trade metadata
            direction=direction,
            market_code=market_code,
            liquidity_rating=liquidity_rating,
            point_value=point_value,
            typical_box_range_min=typical_box_range_min
        )

        return features

    def extract_features_from_backtest_results(
        self,
        backtest_results: Dict,
        market_configs: Optional[Dict] = None
    ) -> pd.DataFrame:
        """
        Extract features from complete backtest results

        Args:
            backtest_results: Dictionary with all market backtest results
            market_configs: Market configuration dictionary

        Returns:
            DataFrame with all features for all trades
        """
        all_features = []

        for market_code, market_result in backtest_results.items():
            # Skip if explicitly marked as failed
            if market_result.get('success') == False:
                continue

            # Skip if there's an error key
            if 'error' in market_result:
                continue

            trades = market_result.get('trades', [])
            if not trades:
                continue

            print(f"Extracting features from {market_code}: {len(trades)} trades")

            # Get market config
            market_config = market_configs.get(market_code) if market_configs else None

            # Load market data (would need to be passed or loaded)
            # For now, we'll create simplified features without full OHLCV data
            for trade in trades:
                try:
                    # Create simplified features without OHLCV data
                    features = self._create_features_from_trade_only(trade, market_code, market_config)
                    all_features.append(features.to_dict())
                except Exception as e:
                    print(f"Error extracting features from trade: {e}")
                    continue

        if not all_features:
            print("WARNING: No features extracted from backtest results")
            return pd.DataFrame()

        df_features = pd.DataFrame(all_features)
        print(f"\nFeature extraction complete: {len(df_features)} samples, {len(df_features.columns)} features")

        return df_features

    def _create_features_from_trade_only(
        self,
        trade: Dict,
        market_code: str,
        market_config: Optional[Dict]
    ) -> TradeFeatures:
        """Create features from trade data only (without full OHLCV)"""
        # Parse basic info
        pnl_points = trade['pnl_points']
        target = 1 if pnl_points > 0 else 0
        direction = 1 if trade['direction'] == 'LONG' else -1

        # Box characteristics
        box_range = trade['box_range']
        box_high = trade['box_high']
        box_low = trade['box_low']
        box_midpoint = (box_high + box_low) / 2

        # Entry characteristics
        entry_price = trade['entry_price']
        stop_loss = trade['stop_loss']
        risk_points = trade['risk_points']
        stop_distance = abs(entry_price - stop_loss)

        # Parse entry time
        entry_time = pd.to_datetime(trade['entry_time'])
        hour_of_day = entry_time.hour
        day_of_week = entry_time.weekday()

        # Market metadata
        liquidity_rating = market_config.get('liquidity_rating', 3) if market_config else 3
        point_value = market_config.get('point_value', 50.0) if market_config else 50.0
        typical_box_range_min = market_config.get('typical_box_range', (5.0, 40.0))[0] if market_config else 5.0

        # Partial exits info
        partial_exits = trade.get('partial_exits', [])
        num_partial_exits = len(partial_exits)

        # Create features with defaults for missing data
        features = TradeFeatures(
            target=target,
            box_range=box_range,
            box_range_percentile=0.5,  # Unknown
            box_high=box_high,
            box_low=box_low,
            box_midpoint=box_midpoint,
            box_formation_quality=0.5,  # Unknown
            box_volatility_ratio=1.0,  # Unknown
            candles_in_box=18,  # Assume standard 1.5 hours
            breakout_strength=0.1,  # Unknown
            entry_delay_minutes=0.0,  # Unknown
            entry_price_vs_box_pct=0.0,  # Unknown
            stop_distance=stop_distance,
            risk_points=risk_points,
            stop_to_atr_ratio=1.0,  # Unknown
            initial_risk_reward=1.0,  # Strategy default
            rsi_5min_14=50.0,  # Neutral
            rsi_5min_21=50.0,
            rsi_divergence_5min=0.0,  # No divergence
            macd_5min=0.0,
            macd_signal_5min=0.0,
            macd_hist_5min=0.0,
            bb_position_5min=0.5,  # Middle
            bb_width_5min=0.1,
            atr_5min=box_range,  # Approximate
            ema_9_5min=entry_price,
            volume_ratio_5min=1.0,
            rsi_1hour_14=50.0,
            macd_1hour=0.0,
            bb_position_1hour=0.5,
            atr_1hour=box_range * 2,
            trend_1hour=0.0,
            hour_of_day=hour_of_day,
            day_of_week=day_of_week,
            is_market_open=1,  # Assume yes
            volatility_environment=0.5,
            volume_environment=0.5,
            market_trend_5d=0.0,
            market_trend_10d=0.0,
            market_trend_20d=0.0,
            breakout_candle_size=box_range * 0.5,
            breakout_candle_body_pct=0.7,
            previous_candle_direction=0,
            price_momentum=0.0,
            volume_spike=1.0,
            direction=direction,
            market_code=market_code,
            liquidity_rating=liquidity_rating,
            point_value=point_value,
            typical_box_range_min=typical_box_range_min
        )

        return features

    def _detect_rsi_divergence(
        self,
        df: pd.DataFrame,
        window: int = 14,
        lookback: int = 20
    ) -> float:
        """
        Detect RSI divergence

        Args:
            df: Price dataframe with Close column
            window: RSI calculation window
            lookback: Number of periods to look back for divergence

        Returns:
            -1 = Bearish divergence (price higher, RSI lower)
             0 = No divergence
             1 = Bullish divergence (price lower, RSI higher)
        """
        if not TA_AVAILABLE or len(df) < lookback + window:
            return 0.0

        try:
            # Calculate RSI
            rsi = RSIIndicator(close=df['Close'], window=window).rsi()

            # Get recent data
            recent_df = df.tail(lookback).copy()
            recent_rsi = rsi.tail(lookback)

            if len(recent_df) < lookback or recent_rsi.isna().all():
                return 0.0

            # Find price peaks and troughs
            prices = recent_df['Close'].values
            rsi_values = recent_rsi.values

            # Simple peak/trough detection (last 10 vs last value)
            mid_point = lookback // 2

            # Check for bearish divergence: price makes higher high, RSI makes lower high
            price_recent = prices[-1]
            price_previous = max(prices[mid_point:-1]) if len(prices) > mid_point else prices[0]

            rsi_recent = rsi_values[-1]
            rsi_previous_idx = mid_point + np.argmax(rsi_values[mid_point:-1])
            rsi_previous = rsi_values[rsi_previous_idx] if len(rsi_values) > mid_point else rsi_values[0]

            # Bearish divergence: price up, RSI down
            if price_recent > price_previous * 1.002 and rsi_recent < rsi_previous - 3:
                return -1.0

            # Bullish divergence: price down, RSI up
            if price_recent < price_previous * 0.998 and rsi_recent > rsi_previous + 3:
                return 1.0

            return 0.0

        except Exception:
            return 0.0

    def _calculate_trend(self, df: pd.DataFrame, days: int) -> float:
        """Calculate trend as percentage change over N days"""
        window = days * 78  # Approximate 5-min candles per day (6.5 hours * 12)
        if len(df) < window:
            return 0.0

        start_price = df['Close'].iloc[-window]
        end_price = df['Close'].iloc[-1]
        trend = (end_price / start_price - 1) * 100 if start_price > 0 else 0.0

        return trend

    def _create_default_features(self, target: int) -> TradeFeatures:
        """Create default features when data is insufficient"""
        return TradeFeatures(
            target=target,
            box_range=10.0,
            box_range_percentile=0.5,
            box_high=100.0,
            box_low=90.0,
            box_midpoint=95.0,
            box_formation_quality=0.5,
            box_volatility_ratio=1.0,
            candles_in_box=18,
            breakout_strength=0.1,
            entry_delay_minutes=0.0,
            entry_price_vs_box_pct=0.0,
            stop_distance=10.0,
            risk_points=10.0,
            stop_to_atr_ratio=1.0,
            initial_risk_reward=1.0,
            rsi_5min_14=50.0,
            rsi_5min_21=50.0,
            rsi_divergence_5min=0.0,
            macd_5min=0.0,
            macd_signal_5min=0.0,
            macd_hist_5min=0.0,
            bb_position_5min=0.5,
            bb_width_5min=0.1,
            atr_5min=10.0,
            ema_9_5min=95.0,
            volume_ratio_5min=1.0,
            rsi_1hour_14=50.0,
            macd_1hour=0.0,
            bb_position_1hour=0.5,
            atr_1hour=20.0,
            trend_1hour=0.0,
            hour_of_day=12,
            day_of_week=2,
            is_market_open=1,
            volatility_environment=0.5,
            volume_environment=0.5,
            market_trend_5d=0.0,
            market_trend_10d=0.0,
            market_trend_20d=0.0,
            breakout_candle_size=5.0,
            breakout_candle_body_pct=0.7,
            previous_candle_direction=0,
            price_momentum=0.0,
            volume_spike=1.0,
            direction=1,
            market_code='UNKNOWN',
            liquidity_rating=3,
            point_value=50.0,
            typical_box_range_min=5.0
        )

    def get_feature_names(self, exclude_target: bool = False, exclude_categorical: bool = True) -> List[str]:
        """Get list of feature names"""
        features = TradeFeatures(
            target=0, box_range=0, box_range_percentile=0, box_high=0, box_low=0,
            box_midpoint=0, box_formation_quality=0, box_volatility_ratio=0, candles_in_box=0,
            breakout_strength=0, entry_delay_minutes=0, entry_price_vs_box_pct=0,
            stop_distance=0, risk_points=0, stop_to_atr_ratio=0, initial_risk_reward=0,
            rsi_5min_14=0, rsi_5min_21=0, rsi_divergence_5min=0, macd_5min=0, macd_signal_5min=0,
            macd_hist_5min=0, bb_position_5min=0, bb_width_5min=0, atr_5min=0,
            ema_9_5min=0, volume_ratio_5min=0, rsi_1hour_14=0, macd_1hour=0,
            bb_position_1hour=0, atr_1hour=0, trend_1hour=0, hour_of_day=0,
            day_of_week=0, is_market_open=0, volatility_environment=0,
            volume_environment=0, market_trend_5d=0, market_trend_10d=0,
            market_trend_20d=0, breakout_candle_size=0, breakout_candle_body_pct=0,
            previous_candle_direction=0, price_momentum=0, volume_spike=0,
            direction=0, market_code='', liquidity_rating=0, point_value=0,
            typical_box_range_min=0
        )

        names = []
        for key in features.__dict__.keys():
            if exclude_target and key == 'target':
                continue
            if exclude_categorical and key == 'market_code':
                continue
            names.append(key)

        return names
