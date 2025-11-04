"""
Trade Lifecycle Manager V3 for PupupuV3 Strategy

Manages complete trade lifecycle:
PENDING → ACTIVE → TP1_HIT → RUNNER
         ↓
       SL_HIT / NO_TEST

Features:
- Track NO_TEST scenarios (price hits TP1 without testing EMA)
- Automatic SL to breakeven after TP1
- TP2 and TP3 are manual (not automated)
- Full trade history and state transitions
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class TradeState(Enum):
    """Trade lifecycle states"""
    PENDING = "PENDING"           # Signal generated, waiting for entry
    ACTIVE = "ACTIVE"             # Trade entered, monitoring
    TP1_HIT = "TP1_HIT"          # TP1 reached, SL moved to BE
    RUNNER = "RUNNER"             # Running with TP2/TP3 manual
    SL_HIT = "SL_HIT"            # Stop loss hit
    NO_TEST = "NO_TEST"           # TP1 hit without testing EMA
    CANCELLED = "CANCELLED"       # Trade cancelled before entry


@dataclass
class TradeEvent:
    """Single event in trade lifecycle"""
    timestamp: int
    event_type: str  # 'entry', 'tp1', 'sl_move', 'exit', 'no_test'
    price: float
    note: str
    pnl: Optional[float] = None


@dataclass
class Trade:
    """Complete trade with lifecycle tracking"""
    trade_id: str
    signal_id: str
    symbol: str
    direction: str  # 'LONG' or 'SHORT'

    # Entry details
    entry_price: float
    entry_time: Optional[int] = None
    position_size_usd: float = 0.0
    position_size_units: float = 0.0

    # Risk management
    initial_stop_loss: float = 0.0
    current_stop_loss: float = 0.0
    take_profit_1: float = 0.0

    # Tracking
    ema_value_at_entry: float = 0.0
    ema_tested: bool = False
    ema_test_price: Optional[float] = None

    # State
    state: TradeState = TradeState.PENDING
    state_history: List[Tuple[int, TradeState]] = field(default_factory=list)
    events: List[TradeEvent] = field(default_factory=list)

    # Results
    exit_price: Optional[float] = None
    exit_time: Optional[int] = None
    pnl_usd: Optional[float] = None
    pnl_pct: Optional[float] = None

    # Metadata
    created_at: int = 0
    updated_at: int = 0


class TradeLifecycleManager:
    """
    Manages all active trades and their lifecycle transitions
    """

    def __init__(self):
        """Initialize trade manager"""
        self.active_trades: Dict[str, Trade] = {}
        self.completed_trades: List[Trade] = []

    def create_trade_from_signal(
        self,
        signal_id: str,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit_1: float,
        position_size_usd: float,
        position_size_units: float,
        ema_value: float
    ) -> Trade:
        """
        Create a new trade from a signal

        Args:
            signal_id: Unique signal identifier
            symbol: Trading pair
            direction: 'LONG' or 'SHORT'
            entry_price: Entry price
            stop_loss: Initial stop loss
            take_profit_1: TP1 target
            position_size_usd: Position size in USD
            position_size_units: Position size in units
            ema_value: EMA value at signal time

        Returns:
            New Trade object in PENDING state
        """
        now = int(datetime.now().timestamp() * 1000)
        trade_id = f"{symbol}_{now}"

        trade = Trade(
            trade_id=trade_id,
            signal_id=signal_id,
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            position_size_usd=position_size_usd,
            position_size_units=position_size_units,
            initial_stop_loss=stop_loss,
            current_stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            ema_value_at_entry=ema_value,
            state=TradeState.PENDING,
            created_at=now,
            updated_at=now
        )

        # Record initial state
        trade.state_history.append((now, TradeState.PENDING))

        # Add creation event
        trade.events.append(TradeEvent(
            timestamp=now,
            event_type='created',
            price=entry_price,
            note=f"Trade created from signal {signal_id}"
        ))

        self.active_trades[trade_id] = trade

        return trade

    def activate_trade(self, trade_id: str, entry_time: int, actual_entry_price: Optional[float] = None) -> bool:
        """
        Activate a pending trade (entry executed)

        Args:
            trade_id: Trade identifier
            entry_time: Timestamp of entry
            actual_entry_price: Actual fill price (if different from signal)

        Returns:
            True if activated successfully
        """
        trade = self.active_trades.get(trade_id)
        if not trade or trade.state != TradeState.PENDING:
            return False

        # Update entry details
        trade.entry_time = entry_time
        if actual_entry_price:
            trade.entry_price = actual_entry_price

        # Transition to ACTIVE
        self._transition_state(trade, TradeState.ACTIVE, entry_time)

        # Add entry event
        trade.events.append(TradeEvent(
            timestamp=entry_time,
            event_type='entry',
            price=trade.entry_price,
            note=f"Trade entered at ${trade.entry_price:.2f}"
        ))

        trade.updated_at = entry_time

        return True

    def update_trade(
        self,
        trade_id: str,
        current_price: float,
        current_ema: float,
        timestamp: int
    ) -> Optional[str]:
        """
        Update trade with current market data and check for state transitions

        Args:
            trade_id: Trade identifier
            current_price: Current market price
            current_ema: Current EMA value
            timestamp: Current timestamp

        Returns:
            String describing any state transition, or None
        """
        trade = self.active_trades.get(trade_id)
        if not trade or trade.state == TradeState.PENDING:
            return None

        # Check for EMA test (if not already tested)
        if not trade.ema_tested:
            if self._check_ema_test(trade, current_price, current_ema):
                trade.ema_tested = True
                trade.ema_test_price = current_price
                trade.events.append(TradeEvent(
                    timestamp=timestamp,
                    event_type='ema_test',
                    price=current_price,
                    note=f"Price tested EMA at ${current_price:.2f}"
                ))

        # Check for stop loss hit
        if self._check_stop_loss_hit(trade, current_price):
            pnl = self._calculate_pnl(trade, current_price)
            self._close_trade(trade, current_price, timestamp, TradeState.SL_HIT, pnl)
            return f"SL_HIT: Trade closed at ${current_price:.2f} | PnL: ${pnl:.2f}"

        # Check for TP1 hit
        if trade.state == TradeState.ACTIVE and self._check_tp1_hit(trade, current_price):
            # Check for NO_TEST scenario
            if not trade.ema_tested:
                pnl = self._calculate_pnl(trade, current_price)
                self._close_trade(trade, current_price, timestamp, TradeState.NO_TEST, pnl)
                return f"NO_TEST: TP1 hit without EMA test | PnL: ${pnl:.2f}"

            # Normal TP1 hit - move SL to breakeven
            self._transition_state(trade, TradeState.TP1_HIT, timestamp)
            trade.current_stop_loss = trade.entry_price

            trade.events.append(TradeEvent(
                timestamp=timestamp,
                event_type='tp1',
                price=current_price,
                note=f"TP1 hit at ${current_price:.2f}, SL moved to BE"
            ))

            # Transition to RUNNER
            self._transition_state(trade, TradeState.RUNNER, timestamp)

            return f"TP1_HIT: SL moved to breakeven, now running with manual TP2/TP3"

        trade.updated_at = timestamp
        return None

    def close_trade_manually(
        self,
        trade_id: str,
        exit_price: float,
        exit_time: int,
        reason: str = "Manual close"
    ) -> Optional[float]:
        """
        Manually close a trade (for TP2/TP3 or discretionary exits)

        Args:
            trade_id: Trade identifier
            exit_price: Exit price
            exit_time: Exit timestamp
            reason: Reason for closing

        Returns:
            PnL in USD, or None if trade not found
        """
        trade = self.active_trades.get(trade_id)
        if not trade:
            return None

        pnl = self._calculate_pnl(trade, exit_price)
        self._close_trade(trade, exit_price, exit_time, TradeState.RUNNER, pnl, reason)

        return pnl

    def cancel_trade(self, trade_id: str, timestamp: int, reason: str = "Cancelled") -> bool:
        """
        Cancel a pending trade before entry

        Args:
            trade_id: Trade identifier
            timestamp: Cancellation timestamp
            reason: Reason for cancellation

        Returns:
            True if cancelled successfully
        """
        trade = self.active_trades.get(trade_id)
        if not trade or trade.state != TradeState.PENDING:
            return False

        self._transition_state(trade, TradeState.CANCELLED, timestamp)

        trade.events.append(TradeEvent(
            timestamp=timestamp,
            event_type='cancelled',
            price=trade.entry_price,
            note=reason
        ))

        # Move to completed
        self.completed_trades.append(trade)
        del self.active_trades[trade_id]

        return True

    def get_active_trades(self) -> List[Trade]:
        """Get all active trades"""
        return list(self.active_trades.values())

    def get_completed_trades(self) -> List[Trade]:
        """Get all completed trades"""
        return self.completed_trades

    def get_trade(self, trade_id: str) -> Optional[Trade]:
        """Get specific trade by ID"""
        return self.active_trades.get(trade_id)

    def get_summary_stats(self) -> Dict:
        """Get summary statistics for all completed trades"""
        if not self.completed_trades:
            return {
                'total_trades': 0,
                'total_pnl': 0.0,
                'win_rate': 0.0,
                'wins': 0,
                'losses': 0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'no_test_count': 0
            }

        total_trades = len(self.completed_trades)
        wins = [t for t in self.completed_trades if t.pnl_usd and t.pnl_usd > 0]
        losses = [t for t in self.completed_trades if t.pnl_usd and t.pnl_usd <= 0]

        total_pnl = sum(t.pnl_usd for t in self.completed_trades if t.pnl_usd)
        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0.0
        avg_win = (sum(t.pnl_usd for t in wins) / len(wins)) if wins else 0.0
        avg_loss = (sum(t.pnl_usd for t in losses) / len(losses)) if losses else 0.0

        no_test_count = len([t for t in self.completed_trades if t.state == TradeState.NO_TEST])

        return {
            'total_trades': total_trades,
            'total_pnl': round(total_pnl, 2),
            'win_rate': round(win_rate, 2),
            'wins': len(wins),
            'losses': len(losses),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'no_test_count': no_test_count
        }

    # Private helper methods

    def _transition_state(self, trade: Trade, new_state: TradeState, timestamp: int):
        """Record state transition"""
        trade.state = new_state
        trade.state_history.append((timestamp, new_state))
        trade.updated_at = timestamp

    def _check_ema_test(self, trade: Trade, current_price: float, current_ema: float) -> bool:
        """Check if price has tested EMA after entry"""
        threshold = 0.0005  # 0.05% threshold

        if trade.direction == "LONG":
            # For LONG, price should dip to or below EMA
            return current_price <= current_ema * (1 + threshold)
        else:  # SHORT
            # For SHORT, price should rise to or above EMA
            return current_price >= current_ema * (1 - threshold)

    def _check_stop_loss_hit(self, trade: Trade, current_price: float) -> bool:
        """Check if stop loss has been hit"""
        if trade.direction == "LONG":
            return current_price <= trade.current_stop_loss
        else:  # SHORT
            return current_price >= trade.current_stop_loss

    def _check_tp1_hit(self, trade: Trade, current_price: float) -> bool:
        """Check if TP1 has been hit"""
        if trade.direction == "LONG":
            return current_price >= trade.take_profit_1
        else:  # SHORT
            return current_price <= trade.take_profit_1

    def _calculate_pnl(self, trade: Trade, exit_price: float) -> float:
        """Calculate PnL in USD"""
        if trade.direction == "LONG":
            pnl_per_unit = exit_price - trade.entry_price
        else:  # SHORT
            pnl_per_unit = trade.entry_price - exit_price

        pnl_usd = pnl_per_unit * trade.position_size_units
        return pnl_usd

    def _close_trade(
        self,
        trade: Trade,
        exit_price: float,
        exit_time: int,
        final_state: TradeState,
        pnl: float,
        reason: str = ""
    ):
        """Close a trade and move to completed"""
        trade.exit_price = exit_price
        trade.exit_time = exit_time
        trade.pnl_usd = pnl
        trade.pnl_pct = (pnl / trade.position_size_usd) * 100 if trade.position_size_usd > 0 else 0.0

        self._transition_state(trade, final_state, exit_time)

        # Add exit event
        trade.events.append(TradeEvent(
            timestamp=exit_time,
            event_type='exit',
            price=exit_price,
            note=reason or f"Trade closed: {final_state.value}",
            pnl=pnl
        ))

        # Move to completed
        self.completed_trades.append(trade)
        del self.active_trades[trade.trade_id]


# Test function
if __name__ == "__main__":
    print("Testing Trade Lifecycle Manager V3...")

    manager = TradeLifecycleManager()

    # Create a test trade
    print("\n1. Creating trade from signal...")
    trade = manager.create_trade_from_signal(
        signal_id="BTCUSDT_1609459200",
        symbol="BTC/USDT",
        direction="LONG",
        entry_price=43000,
        stop_loss=42980,
        take_profit_1=43020,
        position_size_usd=10000,
        position_size_units=0.2326,
        ema_value=42990
    )
    print(f"   Trade created: {trade.trade_id} | State: {trade.state.value}")

    # Activate trade
    print("\n2. Activating trade...")
    manager.activate_trade(trade.trade_id, int(datetime.now().timestamp() * 1000), 43000)
    print(f"   Trade activated | State: {trade.state.value}")

    # Update with price movements
    print("\n3. Simulating price movements...")

    test_updates = [
        (42995, 42990, "Price dips to EMA (test)"),
        (43005, 42992, "Price bounces up"),
        (43020, 42995, "Price hits TP1"),
    ]

    for price, ema, desc in test_updates:
        print(f"\n   {desc}: Price=${price}, EMA=${ema}")
        result = manager.update_trade(
            trade.trade_id,
            current_price=price,
            current_ema=ema,
            timestamp=int(datetime.now().timestamp() * 1000)
        )
        if result:
            print(f"   >>> {result}")

    # Check stats
    print("\n4. Trade Summary:")
    print(f"   Events: {len(trade.events)}")
    for event in trade.events:
        print(f"      - {event.event_type}: ${event.price:.2f} | {event.note}")

    print(f"\n   State History:")
    for ts, state in trade.state_history:
        dt = datetime.fromtimestamp(ts / 1000).strftime('%H:%M:%S')
        print(f"      - {dt}: {state.value}")

    # Get summary stats
    stats = manager.get_summary_stats()
    print(f"\n5. Overall Stats:")
    print(f"   Total Trades: {stats['total_trades']}")
    print(f"   Total PnL: ${stats['total_pnl']:.2f}")
    print(f"   Win Rate: {stats['win_rate']:.2f}%")
    print(f"   NO_TEST Count: {stats['no_test_count']}")

    print("\n[OK] Trade Lifecycle Manager V3 tests complete")
