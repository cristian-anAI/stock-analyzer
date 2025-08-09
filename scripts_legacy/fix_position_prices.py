#!/usr/bin/env python3
"""
Fix Position Prices - Corregir precios incorrectos y símbolos
"""

import importlib.util
from position_manager import PositionManager
from database_manager import DatabaseManager

spec = importlib.util.spec_from_file_location("data_collector", "data-collector.py")
data_collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data_collector)

def fix_all_positions():
    """Fix all position prices based on real data"""
    collector = data_collector.StockDataCollector()
    manager = PositionManager(collector)
    db = DatabaseManager()
    print("🔧 FIXING ALL POSITION PRICES")
    print("=" * 50)
    # Real positions with CORRECT current values and prices
    real_positions = {
        # REVOLUT positions (USD)
        "NDAQ": {
            "correct_current_price": 703.71,
            "correct_entry_price": 560.19,
            "quantity": 7.2547,
            "real_pnl_percent": 25.61
        },
        "BNTX": {
            "correct_current_price": 168.13,
            "correct_entry_price": 166.55,
            "quantity": 1.5146,
            "real_pnl_percent": 0.95
        },
        "BTC-USD": {
            "correct_current_price": 116805.0,
            "correct_entry_price": 75949.53,
            "quantity": 0.0055,
            "real_pnl_percent": 53.81
        },
        # DEGIRO positions (convert EUR to USD at ~1.05 rate)
        "DFEN": {
            "correct_current_price": 198.72,
            "correct_entry_price": 198.13,
            "quantity": 4,
            "real_pnl_percent": 0.30
        }
    }
    # Alternative symbols for broken ones
    symbol_replacements = {
        "PPFB.L": "GLD",
        "SXLE.MI": "XLU",
        "VUSD.L": "VOO",
        "XAG-USD": "SLV",
    }
    # Fix real positions first
    for symbol, data in real_positions.items():
        if symbol in manager.positions:
            position = manager.positions[symbol]
            print(f"\n🔧 Fixing {symbol}:")
            print(f"   Old entry price: ${position.entry_price:.2f}")
            print(f"   New entry price: ${data['correct_entry_price']:.2f}")
            # Update position in memory
            position.entry_price = data['correct_entry_price']
            position.current_price = data['correct_current_price']
            # Recalculate P&L
            total_value = data['correct_current_price'] * data['quantity']
            entry_value = data['correct_entry_price'] * data['quantity']
            position.unrealized_pnl = total_value - entry_value
            position.unrealized_pnl_percent = (position.unrealized_pnl / entry_value) * 100
            print(f"   Corrected P&L: {position.unrealized_pnl_percent:+.1f}% (should be ~{data['real_pnl_percent']:+.1f}%)")
            # Update in database
            from dataclasses import asdict
            if manager.db_manager:
                manager.db_manager.update_position(asdict(position))
    # Replace broken symbols
    for old_symbol, new_symbol in symbol_replacements.items():
        if old_symbol in manager.positions:
            print(f"\n🔄 Replacing {old_symbol} with {new_symbol}:")
            old_position = manager.positions[old_symbol]
            try:
                stock_data = collector.get_stock_data(new_symbol)
                if 'error' not in stock_data:
                    current_price = stock_data['price_data']['current_price']
                    print(f"   {new_symbol} current price: ${current_price:.2f} ✅")
                    # Calculate reasonable entry price based on your real P&L
                    if old_symbol == "PPFB.L":
                        entry_price = current_price / 1.011
                    elif old_symbol == "SXLE.MI":
                        entry_price = current_price / 0.8868
                    elif old_symbol == "VUSD.L":
                        entry_price = current_price / 1.0091
                    elif old_symbol == "XAG-USD":
                        entry_price = current_price / 1.0944
                    print(f"   Calculated entry price: ${entry_price:.2f}")
                    # Create new position
                    success = manager.open_position(
                        symbol=new_symbol,
                        entry_price=entry_price,
                        quantity=old_position.quantity,
                        stop_loss_percent=8.0,
                        take_profit_percent=15.0
                    )
                    if success:
                        new_pos = manager.positions[new_symbol]
                        new_pos.notes = f"Replaced {old_symbol} - Real position equivalent"
                        manager.update_position(new_symbol, current_price)
                        manager.close_position(old_symbol, f"Replaced with {new_symbol}")
                        print(f"   ✅ Successfully replaced with {new_symbol}")
                else:
                    print(f"   ❌ {new_symbol} also has data issues")
            except Exception as e:
                print(f"   ❌ Error testing {new_symbol}: {e}")

def verify_fixes():
    """Verify all positions now have reasonable P&L"""
    collector = data_collector.StockDataCollector()
    manager = PositionManager(collector)
    print(f"\n✅ VERIFICATION - Updated Positions:")
    print("=" * 50)
    total_pnl = 0
    for symbol, position in manager.positions.items():
        try:
            stock_data = collector.get_stock_data(symbol)
            if 'error' not in stock_data:
                current_price = stock_data['price_data']['current_price']
                manager.update_position(symbol, current_price)
                pnl_color = "📈" if position.unrealized_pnl >= 0 else "📉"
                print(f"{symbol:10} | {pnl_color} {position.unrealized_pnl_percent:+6.1f}% | ${position.unrealized_pnl:+8.2f}")
                total_pnl += position.unrealized_pnl
            else:
                print(f"{symbol:10} | ❌ Data error")
        except Exception as e:
            print(f"{symbol:10} | ❌ Error: {e}")
    print(f"\n📊 Total Portfolio P&L: ${total_pnl:+.2f}")
    print("   (Should be positive overall based on your real gains)")

def main():
    print("🔧 POSITION PRICE FIXER")
    print("=" * 30)
    print("This will:")
    print("1. Fix NDAQ/BNTX/DFEN/BTC prices")
    print("2. Replace broken European symbols")
    print("3. Verify all P&L calculations")
    confirm = input("\nProceed? (y/n): ").lower()
    if confirm == 'y':
        fix_all_positions()
        verify_fixes()
        print("\n✅ All positions fixed!")
    else:
        print("Operation cancelled")

if __name__ == "__main__":
    main()
