"""
Database Manager for PupupuV3 Strategy

Tables:
- pupupuv3_signals: All generated signals (valid and invalid)
- pupupuv3_trades: Complete trade lifecycle tracking
- pupupuv3_events: Trade events log
"""

import sqlite3
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path


class PupupuV3Database:
    """Database manager for PupupuV3 strategy"""

    def __init__(self, db_path: str = "pupupuv3.db"):
        """
        Initialize database connection and create tables if needed

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """Establish database connection"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Access columns by name

    def _create_tables(self):
        """Create all required tables"""
        cursor = self.conn.cursor()

        # Signals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pupupuv3_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id TEXT UNIQUE NOT NULL,
                timestamp INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,

                -- Entry and risk
                entry_price REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit_1 REAL NOT NULL,

                -- Signal details
                pivot_price REAL NOT NULL,
                pivot_type TEXT NOT NULL,
                pivot_strength REAL NOT NULL,
                ema_value REAL NOT NULL,
                cross_type TEXT NOT NULL,

                -- VWAP filter
                vwap_value REAL NOT NULL,
                vwap_bias TEXT NOT NULL,
                with_vwap_bias INTEGER NOT NULL,

                -- Volume Profile
                vp_poc REAL NOT NULL,
                vp_in_value_area INTEGER NOT NULL,
                vp_near_hvn INTEGER NOT NULL,

                -- ML
                ml_confidence REAL NOT NULL,

                -- Risk
                risk_usd REAL NOT NULL,
                position_size_usd REAL NOT NULL,
                risk_multiplier REAL NOT NULL,

                -- Status
                is_valid INTEGER NOT NULL,
                reason TEXT NOT NULL,

                created_at INTEGER NOT NULL
            )
        """)

        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pupupuv3_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT UNIQUE NOT NULL,
                signal_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,

                -- Entry
                entry_price REAL NOT NULL,
                entry_time INTEGER,
                position_size_usd REAL NOT NULL,
                position_size_units REAL NOT NULL,

                -- Risk management
                initial_stop_loss REAL NOT NULL,
                current_stop_loss REAL NOT NULL,
                take_profit_1 REAL NOT NULL,

                -- Tracking
                ema_value_at_entry REAL NOT NULL,
                ema_tested INTEGER NOT NULL DEFAULT 0,
                ema_test_price REAL,

                -- State
                state TEXT NOT NULL,

                -- Results
                exit_price REAL,
                exit_time INTEGER,
                pnl_usd REAL,
                pnl_pct REAL,

                -- Metadata
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,

                FOREIGN KEY (signal_id) REFERENCES pupupuv3_signals(signal_id)
            )
        """)

        # Events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pupupuv3_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                price REAL NOT NULL,
                note TEXT NOT NULL,
                pnl REAL,

                FOREIGN KEY (trade_id) REFERENCES pupupuv3_trades(trade_id)
            )
        """)

        # State history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pupupuv3_state_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                state TEXT NOT NULL,

                FOREIGN KEY (trade_id) REFERENCES pupupuv3_trades(trade_id)
            )
        """)

        # Create indexes for better query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_signals_timestamp
            ON pupupuv3_signals(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_signals_symbol
            ON pupupuv3_signals(symbol)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_state
            ON pupupuv3_trades(state)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_timestamp
            ON pupupuv3_trades(created_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_trade_id
            ON pupupuv3_events(trade_id)
        """)

        self.conn.commit()

    # Signal operations

    def save_signal(self, signal: Dict) -> bool:
        """
        Save a signal to the database

        Args:
            signal: Signal dictionary from signal_to_dict()

        Returns:
            True if saved successfully
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO pupupuv3_signals (
                    signal_id, timestamp, symbol, direction,
                    entry_price, stop_loss, take_profit_1,
                    pivot_price, pivot_type, pivot_strength,
                    ema_value, cross_type,
                    vwap_value, vwap_bias, with_vwap_bias,
                    vp_poc, vp_in_value_area, vp_near_hvn,
                    ml_confidence,
                    risk_usd, position_size_usd, risk_multiplier,
                    is_valid, reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal['signal_id'], signal['timestamp'], signal['symbol'], signal['direction'],
                signal['entry_price'], signal['stop_loss'], signal['take_profit_1'],
                signal['pivot_price'], signal['pivot_type'], signal['pivot_strength'],
                signal['ema_value'], signal['cross_type'],
                signal['vwap_value'], signal['vwap_bias'], int(signal['with_vwap_bias']),
                signal['vp_poc'], int(signal['vp_in_value_area']), int(signal['vp_near_hvn']),
                signal['ml_confidence'],
                signal['risk_usd'], signal['position_size_usd'], signal['risk_multiplier'],
                int(signal['is_valid']), signal['reason'], signal['timestamp']
            ))

            self.conn.commit()
            return True

        except sqlite3.IntegrityError:
            # Signal already exists
            return False

    def get_recent_signals(self, limit: int = 50, valid_only: bool = False) -> List[Dict]:
        """Get recent signals"""
        cursor = self.conn.cursor()

        query = "SELECT * FROM pupupuv3_signals"
        if valid_only:
            query += " WHERE is_valid = 1"
        query += " ORDER BY timestamp DESC LIMIT ?"

        cursor.execute(query, (limit,))

        return [dict(row) for row in cursor.fetchall()]

    # Trade operations

    def save_trade(self, trade: Any) -> bool:
        """
        Save a trade to the database

        Args:
            trade: Trade object from TradeLifecycleManager

        Returns:
            True if saved successfully
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO pupupuv3_trades (
                    trade_id, signal_id, symbol, direction,
                    entry_price, entry_time, position_size_usd, position_size_units,
                    initial_stop_loss, current_stop_loss, take_profit_1,
                    ema_value_at_entry, ema_tested, ema_test_price,
                    state, exit_price, exit_time, pnl_usd, pnl_pct,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.trade_id, trade.signal_id, trade.symbol, trade.direction,
                trade.entry_price, trade.entry_time, trade.position_size_usd, trade.position_size_units,
                trade.initial_stop_loss, trade.current_stop_loss, trade.take_profit_1,
                trade.ema_value_at_entry, int(trade.ema_tested), trade.ema_test_price,
                trade.state.value, trade.exit_price, trade.exit_time, trade.pnl_usd, trade.pnl_pct,
                trade.created_at, trade.updated_at
            ))

            # Save state history
            for timestamp, state in trade.state_history:
                cursor.execute("""
                    INSERT INTO pupupuv3_state_history (trade_id, timestamp, state)
                    VALUES (?, ?, ?)
                """, (trade.trade_id, timestamp, state.value))

            # Save events
            for event in trade.events:
                cursor.execute("""
                    INSERT INTO pupupuv3_events (
                        trade_id, timestamp, event_type, price, note, pnl
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    trade.trade_id, event.timestamp, event.event_type,
                    event.price, event.note, event.pnl
                ))

            self.conn.commit()
            return True

        except sqlite3.IntegrityError:
            return False

    def update_trade(self, trade: Any) -> bool:
        """Update an existing trade"""
        cursor = self.conn.cursor()

        cursor.execute("""
            UPDATE pupupuv3_trades
            SET state = ?, current_stop_loss = ?, ema_tested = ?, ema_test_price = ?,
                exit_price = ?, exit_time = ?, pnl_usd = ?, pnl_pct = ?, updated_at = ?
            WHERE trade_id = ?
        """, (
            trade.state.value, trade.current_stop_loss, int(trade.ema_tested), trade.ema_test_price,
            trade.exit_price, trade.exit_time, trade.pnl_usd, trade.pnl_pct,
            trade.updated_at, trade.trade_id
        ))

        self.conn.commit()
        return cursor.rowcount > 0

    def get_trades_by_state(self, state: str) -> List[Dict]:
        """Get all trades by state"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM pupupuv3_trades
            WHERE state = ?
            ORDER BY created_at DESC
        """, (state,))

        return [dict(row) for row in cursor.fetchall()]

    def get_active_trades(self) -> List[Dict]:
        """Get all active trades"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM pupupuv3_trades
            WHERE state IN ('ACTIVE', 'TP1_HIT', 'RUNNER')
            ORDER BY created_at DESC
        """)

        return [dict(row) for row in cursor.fetchall()]

    def get_completed_trades(self, limit: int = 100) -> List[Dict]:
        """Get completed trades"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM pupupuv3_trades
            WHERE state IN ('SL_HIT', 'NO_TEST', 'CANCELLED')
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def get_trade_events(self, trade_id: str) -> List[Dict]:
        """Get all events for a trade"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM pupupuv3_events
            WHERE trade_id = ?
            ORDER BY timestamp ASC
        """, (trade_id,))

        return [dict(row) for row in cursor.fetchall()]

    # Statistics

    def get_statistics(self, days: int = 30) -> Dict:
        """Get trading statistics for the last N days"""
        cursor = self.conn.cursor()

        # Calculate timestamp for N days ago
        cutoff_time = int((datetime.now().timestamp() - (days * 24 * 60 * 60)) * 1000)

        # Total signals
        cursor.execute("""
            SELECT COUNT(*) as total, SUM(is_valid) as valid
            FROM pupupuv3_signals
            WHERE timestamp > ?
        """, (cutoff_time,))

        signal_stats = dict(cursor.fetchone())

        # Trade statistics
        cursor.execute("""
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN pnl_usd <= 0 THEN 1 ELSE 0 END) as losses,
                SUM(pnl_usd) as total_pnl,
                AVG(CASE WHEN pnl_usd > 0 THEN pnl_usd END) as avg_win,
                AVG(CASE WHEN pnl_usd <= 0 THEN pnl_usd END) as avg_loss,
                SUM(CASE WHEN state = 'NO_TEST' THEN 1 ELSE 0 END) as no_test_count
            FROM pupupuv3_trades
            WHERE created_at > ? AND pnl_usd IS NOT NULL
        """, (cutoff_time,))

        trade_stats = dict(cursor.fetchone())

        # Calculate win rate
        total_trades = trade_stats['total_trades'] or 0
        wins = trade_stats['wins'] or 0
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0

        return {
            'days': days,
            'signals_total': signal_stats['total'] or 0,
            'signals_valid': signal_stats['valid'] or 0,
            'trades_total': total_trades,
            'trades_wins': wins,
            'trades_losses': trade_stats['losses'] or 0,
            'win_rate': round(win_rate, 2),
            'total_pnl': round(trade_stats['total_pnl'] or 0.0, 2),
            'avg_win': round(trade_stats['avg_win'] or 0.0, 2),
            'avg_loss': round(trade_stats['avg_loss'] or 0.0, 2),
            'no_test_count': trade_stats['no_test_count'] or 0
        }

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


# Test function
if __name__ == "__main__":
    print("Testing PupupuV3 Database...")

    # Create test database
    db = PupupuV3Database("test_pupupuv3.db")

    # Test signal save
    print("\n1. Testing signal save...")
    test_signal = {
        'signal_id': 'BTCUSDT_1609459200',
        'timestamp': 1609459200000,
        'symbol': 'BTC/USDT',
        'direction': 'LONG',
        'entry_price': 43000.0,
        'stop_loss': 42980.0,
        'take_profit_1': 43020.0,
        'pivot_price': 42985.0,
        'pivot_type': 'support',
        'pivot_strength': 75.5,
        'ema_value': 42990.0,
        'cross_type': 'cross_above',
        'vwap_value': 43100.0,
        'vwap_bias': 'bullish',
        'with_vwap_bias': True,
        'vp_poc': 43050.0,
        'vp_in_value_area': True,
        'vp_near_hvn': False,
        'ml_confidence': 65.0,
        'risk_usd': 600.0,
        'position_size_usd': 10000.0,
        'risk_multiplier': 1.0,
        'is_valid': True,
        'reason': 'All filters passed'
    }

    success = db.save_signal(test_signal)
    print(f"   Signal saved: {success}")

    # Test signal retrieval
    print("\n2. Testing signal retrieval...")
    signals = db.get_recent_signals(limit=10)
    print(f"   Retrieved {len(signals)} signals")
    if signals:
        print(f"   Latest: {signals[0]['symbol']} {signals[0]['direction']} @ ${signals[0]['entry_price']:.2f}")

    # Test statistics
    print("\n3. Testing statistics...")
    stats = db.get_statistics(days=30)
    print(f"   Signals: {stats['signals_total']} total, {stats['signals_valid']} valid")
    print(f"   Trades: {stats['trades_total']} total")
    print(f"   Win Rate: {stats['win_rate']:.2f}%")

    # Cleanup
    db.close()

    import os
    if os.path.exists("test_pupupuv3.db"):
        os.remove("test_pupupuv3.db")
        print("\n[OK] Test database cleaned up")

    print("\n[OK] PupupuV3 Database tests complete")
