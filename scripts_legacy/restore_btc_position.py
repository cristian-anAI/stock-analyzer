#!/usr/bin/env python3
"""
Restore BTC-USD position to open positions (MANUAL)
"""

import importlib.util
from datetime import datetime

spec = importlib.util.spec_from_file_location("data_collector", "data-collector.py")
data_collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data_collector)

from position_manager import PositionManager
from database_manager import DatabaseManager
from dataclasses import asdict

# --- CONFIGURE YOUR BTC-USD POSITION DATA ---
RESTORE_DATA = {
    "symbol": "BTC-USD",
    "entry_price": 75949.53,
    "quantity": 0.0055,
    "entry_date": "2025-08-01",  # Ajusta si es necesario
    "stop_loss": 64557.10,  # 15% stop
    "take_profit": 98734.39,  # 30% profit
    "notes": "Restored BTC position - MANUAL after auto-sell",
    "position_type": "MANUAL"
}

def restore_btc_position():
    collector = data_collector.StockDataCollector()
    manager = PositionManager(collector)
    db = DatabaseManager()

    # Remove from trades_history if exists (optional, not implemented here)

    # Add back to open positions
    pos_dict = {
        "symbol": RESTORE_DATA["symbol"],
        "entry_date": RESTORE_DATA["entry_date"],
        "entry_price": RESTORE_DATA["entry_price"],
        "quantity": RESTORE_DATA["quantity"],
        "stop_loss": RESTORE_DATA["stop_loss"],
        "take_profit": RESTORE_DATA["take_profit"],
        "current_price": RESTORE_DATA["entry_price"],
        "unrealized_pnl": 0.0,
        "unrealized_pnl_percent": 0.0,
        "days_held": 0,
        "trailing_stop": RESTORE_DATA["stop_loss"],
        "partial_sold": False,
        "notes": RESTORE_DATA["notes"],
        "position_type": RESTORE_DATA["position_type"]
    }
    db.save_position(pos_dict)
    print(f"✅ BTC-USD restored to open positions as MANUAL.")

if __name__ == "__main__":
    restore_btc_position()
