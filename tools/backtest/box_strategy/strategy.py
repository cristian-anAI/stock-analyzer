"""
Box Strategy (Opening Range Strategy) Implementation

Captures volatility around NYSE market open using a defined price range.

Strategy Rules:
1. Box Formation: 8:30 AM - 10:00 AM ET (1.5 hours)
2. Entry: First 5-min candle close breaking above/below box
3. Order: Limit order at box edge level
4. Entry Window: 2 hours after box close (until 12:00 PM ET)
5. Stop Loss: Opposite edge of the box
6. Take Profit Levels:
   - TP1 (50%): 1:1 ratio, move SL to breakeven
   - TP2 (25%): First RSI divergence on 5-min chart
   - TP3 (25%): First RSI divergence on 1-hour chart or exhaustion
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
from zoneinfo import ZoneInfo


class Direction(Enum):
    """Trade direction"""
    LONG = "LONG"
    SHORT = "SHORT"
    NONE = "NONE"


class TradeStatus(Enum):
    """Trade execution status"""
    INVALID = "INVALID"  # Not executed within time window
    STOPPED_OUT = "STOPPED_OUT"  # Hit stop loss
    TP1_HIT = "TP1_HIT"  # Hit first take profit
    TP2_HIT = "TP2_HIT"  # Hit second take profit
    TP3_HIT = "TP3_HIT"  # Hit third take profit
    OPEN = "OPEN"  # Still in trade


@dataclass
class BoxSetup:
    """Box formation data"""
    date: datetime.date
    box_high: float
    box_low: float
    box_range: float
    formation_start: datetime
    formation_end: datetime
    candles_count: int


@dataclass
class TradeEntry:
    """Trade entry information"""
    date: datetime.date
    direction: Direction
    entry_time: datetime
    entry_price: float
    stop_loss: float
    box_setup: BoxSetup
    risk_points: float  # Distance to stop in points


@dataclass
class TradeExit:
    """Trade exit information"""
    exit_time: datetime
    exit_price: float
    status: TradeStatus
    pnl_points: float
    pnl_r: float  # P&L in R multiples
    partial_exits: List[Dict]  # Track partial exits


class BoxStrategy:
    """Implementation of the Box/Opening Range Strategy"""

    def __init__(
        self,
        risk_per_trade: float = 0.02,  # 2% risk per trade
        slippage_points: float = 1.0,   # Estimated slippage in points
        min_box_range: float = 5.0,     # Minimum box range in points
        max_box_range: float = 100.0,   # Maximum box range (volatility filter)
        use_volatility_filter: bool = False
    ):
        """
        Initialize Box Strategy

        Args:
            risk_per_trade: Percentage of account to risk per trade
            slippage_points: Estimated slippage in index points
            min_box_range: Minimum box range to consider trading
            max_box_range: Maximum box range (skip if exceeded)
            use_volatility_filter: Whether to apply volatility filter
        """
        self.risk_per_trade = risk_per_trade
        self.slippage_points = slippage_points
        self.min_box_range = min_box_range
        self.max_box_range = max_box_range
        self.use_volatility_filter = use_volatility_filter

        # Timezone
        self.et_tz = ZoneInfo("America/New_York")

    def identify_box(self, df: pd.DataFrame, date: datetime.date) -> Optional[BoxSetup]:
        """
        Identify the box formation for a given day

        Args:
            df: 5-minute OHLCV data
            date: Trading day

        Returns:
            BoxSetup object or None if invalid
        """
        # Define box period: 8:30 AM - 10:00 AM ET
        box_start = datetime.combine(date, time(8, 30), tzinfo=self.et_tz)
        box_end = datetime.combine(date, time(10, 0), tzinfo=self.et_tz)

        # Filter data for box period
        box_data = df[(df.index >= box_start) & (df.index < box_end)].copy()

        if box_data.empty:
            return None

        # Calculate box boundaries
        box_high_val = box_data['High'].max()
        box_low_val = box_data['Low'].min()

        # Ensure scalar values (handle numpy/pandas types)
        if hasattr(box_high_val, 'item'):
            box_high = float(box_high_val.item())
            box_low = float(box_low_val.item())
        else:
            box_high = float(box_high_val)
            box_low = float(box_low_val)

        box_range = box_high - box_low

        # Apply filters
        if box_range < self.min_box_range:
            return None

        if self.use_volatility_filter and box_range > self.max_box_range:
            return None

        return BoxSetup(
            date=date,
            box_high=box_high,
            box_low=box_low,
            box_range=box_range,
            formation_start=box_start,
            formation_end=box_end,
            candles_count=len(box_data)
        )

    def detect_breakout(
        self,
        df: pd.DataFrame,
        box_setup: BoxSetup
    ) -> Optional[Tuple[Direction, datetime, float]]:
        """
        Detect the first 5-min candle close breaking the box

        Args:
            df: 5-minute OHLCV data
            box_setup: Box formation data

        Returns:
            Tuple of (direction, breakout_time, close_price) or None
        """
        # Get data after box formation
        post_box = df[df.index >= box_setup.formation_end].copy()

        if post_box.empty:
            return None

        # Find first candle closing above box
        breakout_up = post_box[post_box['Close'] > box_setup.box_high]
        if not breakout_up.empty:
            first_break = breakout_up.iloc[0]
            return Direction.LONG, first_break.name, first_break['Close']

        # Find first candle closing below box
        breakout_down = post_box[post_box['Close'] < box_setup.box_low]
        if not breakout_down.empty:
            first_break = breakout_down.iloc[0]
            return Direction.SHORT, first_break.name, first_break['Close']

        return None

    def check_entry_execution(
        self,
        df: pd.DataFrame,
        direction: Direction,
        breakout_time: datetime,
        box_setup: BoxSetup
    ) -> Optional[TradeEntry]:
        """
        Check if limit order at box edge would be filled within 2 hours

        Args:
            df: 5-minute OHLCV data
            direction: Trade direction
            breakout_time: Time of box breakout
            box_setup: Box formation data

        Returns:
            TradeEntry object or None if not executed
        """
        # Entry window: 2 hours after box close
        entry_deadline = box_setup.formation_end + timedelta(hours=2)

        # Get candles from breakout to deadline
        entry_window = df[
            (df.index >= breakout_time) &
            (df.index <= entry_deadline)
        ].copy()

        if entry_window.empty:
            return None

        if direction == Direction.LONG:
            # Limit buy at box_high (box top)
            limit_price = box_setup.box_high
            stop_loss = box_setup.box_low

            # Check if price touched limit level
            for idx, candle in entry_window.iterrows():
                if candle['Low'] <= limit_price <= candle['High']:
                    # Order filled
                    entry_price = limit_price + self.slippage_points  # Account for slippage

                    return TradeEntry(
                        date=box_setup.date,
                        direction=direction,
                        entry_time=idx,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        box_setup=box_setup,
                        risk_points=entry_price - stop_loss
                    )

        elif direction == Direction.SHORT:
            # Limit sell at box_low (box bottom)
            limit_price = box_setup.box_low
            stop_loss = box_setup.box_high

            # Check if price touched limit level
            for idx, candle in entry_window.iterrows():
                if candle['Low'] <= limit_price <= candle['High']:
                    # Order filled
                    entry_price = limit_price - self.slippage_points  # Account for slippage

                    return TradeEntry(
                        date=box_setup.date,
                        direction=direction,
                        entry_time=idx,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        box_setup=box_setup,
                        risk_points=stop_loss - entry_price
                    )

        return None

    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate RSI indicator

        Args:
            df: DataFrame with Close prices
            period: RSI period (default 14)

        Returns:
            Series with RSI values
        """
        close = df['Close']
        delta = close.diff()

        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def detect_rsi_divergence(
        self,
        df: pd.DataFrame,
        direction: Direction,
        entry_time: datetime,
        rsi_period: int = 14
    ) -> Optional[datetime]:
        """
        Detect first RSI divergence after entry

        Args:
            df: DataFrame with price data
            direction: Trade direction
            entry_time: Entry timestamp
            rsi_period: RSI calculation period

        Returns:
            Timestamp of divergence or None
        """
        # Get data after entry
        post_entry = df[df.index > entry_time].copy()

        if len(post_entry) < rsi_period + 2:
            return None

        # Calculate RSI
        post_entry['RSI'] = self.calculate_rsi(post_entry, rsi_period)

        # Need at least 2 swing points to detect divergence
        if len(post_entry) < 20:  # Minimum candles to find divergence
            return None

        if direction == Direction.LONG:
            # Look for bearish divergence (higher high in price, lower high in RSI)
            return self._find_bearish_divergence(post_entry)

        elif direction == Direction.SHORT:
            # Look for bullish divergence (lower low in price, higher low in RSI)
            return self._find_bullish_divergence(post_entry)

        return None

    def _find_bearish_divergence(self, df: pd.DataFrame) -> Optional[datetime]:
        """Find bearish divergence (price higher high, RSI lower high)"""
        # Simple implementation: find local highs in price and RSI
        window = 5
        for i in range(window, len(df) - window):
            # Check if it's a local high in price
            if df['High'].iloc[i] == df['High'].iloc[i-window:i+window].max():
                # Check previous local high
                for j in range(window, i - window):
                    if df['High'].iloc[j] == df['High'].iloc[j-window:j+window].max():
                        # Compare highs
                        if (df['High'].iloc[i] > df['High'].iloc[j] and
                            df['RSI'].iloc[i] < df['RSI'].iloc[j]):
                            return df.index[i]
        return None

    def _find_bullish_divergence(self, df: pd.DataFrame) -> Optional[datetime]:
        """Find bullish divergence (price lower low, RSI higher low)"""
        # Simple implementation: find local lows in price and RSI
        window = 5
        for i in range(window, len(df) - window):
            # Check if it's a local low in price
            if df['Low'].iloc[i] == df['Low'].iloc[i-window:i+window].min():
                # Check previous local low
                for j in range(window, i - window):
                    if df['Low'].iloc[j] == df['Low'].iloc[j-window:j+window].min():
                        # Compare lows
                        if (df['Low'].iloc[i] < df['Low'].iloc[j] and
                            df['RSI'].iloc[i] > df['RSI'].iloc[j]):
                            return df.index[i]
        return None

    def manage_trade(
        self,
        df_5min: pd.DataFrame,
        df_1hour: pd.DataFrame,
        entry: TradeEntry
    ) -> TradeExit:
        """
        Manage trade with 3-tier take profit system

        Args:
            df_5min: 5-minute OHLCV data
            df_1hour: 1-hour OHLCV data (for TP3)
            entry: Trade entry information

        Returns:
            TradeExit object with final exit information
        """
        partial_exits = []
        remaining_position = 1.0  # 100%

        # TP1: 1:1 ratio (50% position)
        tp1_price = self._calculate_tp1(entry)

        # Get post-entry data
        post_entry_5min = df_5min[df_5min.index > entry.entry_time].copy()
        post_entry_1hour = df_1hour[df_1hour.index > entry.entry_time].copy()

        if post_entry_5min.empty:
            return self._create_invalid_exit(entry)

        # Track current stop loss (will move to breakeven after TP1)
        current_stop = entry.stop_loss
        sl_moved_to_be = False

        for idx, candle in post_entry_5min.iterrows():
            # Check stop loss first
            if entry.direction == Direction.LONG:
                if candle['Low'] <= current_stop:
                    # Stopped out
                    exit_price = current_stop - self.slippage_points
                    return self._create_exit(
                        entry, idx, exit_price, remaining_position,
                        TradeStatus.STOPPED_OUT, partial_exits
                    )

                # Check TP1
                if not sl_moved_to_be and candle['High'] >= tp1_price:
                    # Take 50% profit
                    partial_exits.append({
                        'time': idx,
                        'price': tp1_price,
                        'size': 0.5,
                        'reason': 'TP1 (1:1)'
                    })
                    remaining_position = 0.5
                    current_stop = entry.entry_price  # Move SL to breakeven
                    sl_moved_to_be = True
                    continue

                # Check TP2 (RSI divergence on 5min) - only if TP1 hit
                if sl_moved_to_be and remaining_position > 0.25:
                    div_time = self.detect_rsi_divergence(
                        post_entry_5min.loc[:idx],
                        entry.direction,
                        entry.entry_time,
                        rsi_period=14
                    )
                    if div_time and div_time == idx:
                        # Take 25% profit
                        tp2_price = candle['Close']
                        partial_exits.append({
                            'time': idx,
                            'price': tp2_price,
                            'size': 0.25,
                            'reason': 'TP2 (RSI Div 5min)'
                        })
                        remaining_position = 0.25
                        continue

            elif entry.direction == Direction.SHORT:
                if candle['High'] >= current_stop:
                    # Stopped out
                    exit_price = current_stop + self.slippage_points
                    return self._create_exit(
                        entry, idx, exit_price, remaining_position,
                        TradeStatus.STOPPED_OUT, partial_exits
                    )

                # Check TP1
                if not sl_moved_to_be and candle['Low'] <= tp1_price:
                    # Take 50% profit
                    partial_exits.append({
                        'time': idx,
                        'price': tp1_price,
                        'size': 0.5,
                        'reason': 'TP1 (1:1)'
                    })
                    remaining_position = 0.5
                    current_stop = entry.entry_price  # Move SL to breakeven
                    sl_moved_to_be = True
                    continue

                # Check TP2 (RSI divergence on 5min) - only if TP1 hit
                if sl_moved_to_be and remaining_position > 0.25:
                    div_time = self.detect_rsi_divergence(
                        post_entry_5min.loc[:idx],
                        entry.direction,
                        entry.entry_time,
                        rsi_period=14
                    )
                    if div_time and div_time == idx:
                        # Take 25% profit
                        tp2_price = candle['Close']
                        partial_exits.append({
                            'time': idx,
                            'price': tp2_price,
                            'size': 0.25,
                            'reason': 'TP2 (RSI Div 5min)'
                        })
                        remaining_position = 0.25
                        continue

        # If we reached here with remaining position, check TP3 on hourly chart
        # (Simplified: exit at end of day or first hourly RSI divergence)
        if remaining_position > 0:
            # Find last price
            last_candle = post_entry_5min.iloc[-1]
            final_status = TradeStatus.TP3_HIT if sl_moved_to_be else TradeStatus.OPEN

            return self._create_exit(
                entry, last_candle.name, last_candle['Close'],
                remaining_position, final_status, partial_exits
            )

        # All position closed via partials
        final_status = TradeStatus.TP3_HIT if len(partial_exits) == 3 else TradeStatus.TP2_HIT
        last_exit = partial_exits[-1]
        return self._create_exit(
            entry, last_exit['time'], last_exit['price'],
            0, final_status, partial_exits
        )

    def _calculate_tp1(self, entry: TradeEntry) -> float:
        """Calculate TP1 price (1:1 risk/reward)"""
        if entry.direction == Direction.LONG:
            return entry.entry_price + entry.risk_points
        else:
            return entry.entry_price - entry.risk_points

    def _create_exit(
        self,
        entry: TradeEntry,
        exit_time: datetime,
        exit_price: float,
        remaining_size: float,
        status: TradeStatus,
        partial_exits: List[Dict]
    ) -> TradeExit:
        """Create TradeExit object with P&L calculation"""
        # Calculate total P&L from all exits
        total_pnl = 0.0

        # P&L from partial exits
        for partial in partial_exits:
            if entry.direction == Direction.LONG:
                pnl = (partial['price'] - entry.entry_price) * partial['size']
            else:
                pnl = (entry.entry_price - partial['price']) * partial['size']
            total_pnl += pnl

        # P&L from remaining position
        if remaining_size > 0:
            if entry.direction == Direction.LONG:
                pnl = (exit_price - entry.entry_price) * remaining_size
            else:
                pnl = (entry.entry_price - exit_price) * remaining_size
            total_pnl += pnl

        # Calculate R multiple
        pnl_r = total_pnl / entry.risk_points if entry.risk_points > 0 else 0

        return TradeExit(
            exit_time=exit_time,
            exit_price=exit_price,
            status=status,
            pnl_points=total_pnl,
            pnl_r=pnl_r,
            partial_exits=partial_exits
        )

    def _create_invalid_exit(self, entry: TradeEntry) -> TradeExit:
        """Create exit for invalid/non-executed trade"""
        return TradeExit(
            exit_time=entry.entry_time,
            exit_price=entry.entry_price,
            status=TradeStatus.INVALID,
            pnl_points=0,
            pnl_r=0,
            partial_exits=[]
        )
