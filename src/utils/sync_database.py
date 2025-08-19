#!/usr/bin/env python3
"""
Sync Database - Sincronizar database con posiciones corregidas del sistema
"""

import importlib.util
from position_manager import PositionManager
from database_manager import DatabaseManager

spec = importlib.util.spec_from_file_location("data_collector", "data-collector.py")
data_collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data_collector)

def clean_and_sync_database():
    """Clean database and sync with corrected positions"""
    
    collector = data_collector.StockDataCollector()
    manager = PositionManager(collector)
    db = DatabaseManager()
    
    print(" CLEANING AND SYNCING DATABASE")
    print("=" * 50)
    
    # Step 1: Show current database content
    print(" Current Database Content:")
    db_positions = db.load_positions()
    for pos in db_positions:
        print(f"   {pos['symbol']:12} | Entry: ${pos['entry_price']:8.2f} | Qty: {pos['quantity']:6.2f}")
    
    # Step 2: Clear ALL positions from database
    print(f"\n️ Clearing all positions from database...")
    cursor = db.conn.cursor()
    cursor.execute("DELETE FROM positions")
    db.conn.commit()
    deleted_count = cursor.rowcount
    print(f"   Deleted {deleted_count} old positions")
    
    # Step 3: Define correct positions based on your real data
    correct_positions = [
        # REVOLUT positions (USD)
        {
            "symbol": "BTC-USD",
            "entry_price": 75949.53,    # Calculated from your +53.81% real gain
            "quantity": 0.0055,
            "stop_loss_percent": 15.0,
            "take_profit_percent": 30.0,
            "notes": "Real BTC position - REVOLUT - Manual"
        },
        {
            "symbol": "NDAQ", 
            "entry_price": 77.12,       # Calculated: $96.85 / 1.2561 = +25.61%
            "quantity": 7.2547,
            "stop_loss_percent": 8.0,
            "take_profit_percent": 15.0,
            "notes": "Real NDAQ position - REVOLUT - Manual"
        },
        {
            "symbol": "BNTX",
            "entry_price": 110.66,      # Calculated: $111.66 / 1.0095 = +0.95%
            "quantity": 1.5146,
            "stop_loss_percent": 10.0,
            "take_profit_percent": 20.0,
            "notes": "Real BNTX position - REVOLUT - Manual"
        },
        
        # DEGIRO positions (using US equivalents)
        {
            "symbol": "GLD",            # Replacement for PPFB.L
            "entry_price": 309.64,      # Current system shows this works
            "quantity": 3,
            "stop_loss_percent": 8.0,
            "take_profit_percent": 15.0,
            "notes": "Real Gold position (was PPFB.L) - DEGIRO equivalent - Manual"
        },
        {
            "symbol": "XLU",            # Replacement for SXLE.MI
            "entry_price": 97.18,       # Current system shows this works  
            "quantity": 29,
            "stop_loss_percent": 10.0,
            "take_profit_percent": 12.0,
            "notes": "Real Utilities position (was SXLE.MI) - DEGIRO equivalent - Manual"
        },
        {
            "symbol": "DFEN",
            "entry_price": 57.45,       # Calculated: $57.62 / 1.003 = +0.30%
            "quantity": 4,
            "stop_loss_percent": 8.0,
            "take_profit_percent": 15.0,
            "notes": "Real Defense ETF position - DEGIRO - Manual"
        },
        {
            "symbol": "VOO",            # Replacement for VUSD.L
            "entry_price": 580.46,      # Current system shows this works
            "quantity": 3,
            "stop_loss_percent": 6.0,
            "take_profit_percent": 12.0,
            "notes": "Real S&P 500 position (was VUSD.L) - DEGIRO equivalent - Manual"
        },
        {
            "symbol": "SLV",            # Replacement for XAG-USD
            "entry_price": 31.87,       # Current system shows this works
            "quantity": 10.6568,
            "stop_loss_percent": 12.0,
            "take_profit_percent": 25.0,
            "notes": "Real Silver position (was XAG-USD) - REVOLUT equivalent - Manual"
        }
    ]
    
    # Step 4: Add corrected positions to database
    print(f"\n Adding corrected positions to database:")
    
    total_expected_pnl = 0
    
    for pos_data in correct_positions:
        # Get current price
        stock_data = collector.get_stock_data(pos_data["symbol"])
        
        if 'error' not in stock_data:
            current_price = stock_data['price_data']['current_price']
            
            # Calculate expected P&L
            entry_value = pos_data["entry_price"] * pos_data["quantity"]
            current_value = current_price * pos_data["quantity"]
            expected_pnl = current_value - entry_value
            expected_pnl_pct = (expected_pnl / entry_value) * 100
            
            total_expected_pnl += expected_pnl
            
            print(f"   {pos_data['symbol']:8} | Entry: ${pos_data['entry_price']:8.2f} | Current: ${current_price:8.2f} | P&L: {expected_pnl_pct:+6.1f}%")
            
            # Create position object for database
            position_dict = {
                'symbol': pos_data['symbol'],
                'entry_date': '2025-08-09',
                'entry_price': pos_data['entry_price'],
                'quantity': pos_data['quantity'],
                'stop_loss': pos_data['entry_price'] * (1 - pos_data['stop_loss_percent'] / 100),
                'take_profit': pos_data['entry_price'] * (1 + pos_data['take_profit_percent'] / 100),
                'current_price': current_price,
                'unrealized_pnl': expected_pnl,
                'unrealized_pnl_percent': expected_pnl_pct,
                'days_held': 0,
                'trailing_stop': pos_data['entry_price'] * (1 - pos_data['stop_loss_percent'] / 100),
                'partial_sold': False,
                'notes': pos_data['notes']
            }
            
            # Save to database
            try:
                db.save_position(position_dict)
                print(f"       Saved to database")
            except Exception as e:
                print(f"       Database error: {e}")
        else:
            print(f"   {pos_data['symbol']:8} |  Cannot get current price")
    
    print(f"\n Expected Portfolio P&L: ${total_expected_pnl:+.2f}")
    
    # Step 5: Verify sync
    print(f"\n Verification - Reloading from database:")
    new_manager = PositionManager(collector)
    
    if new_manager.positions:
        print(f"    Loaded {len(new_manager.positions)} positions")
        
        for symbol, position in new_manager.positions.items():
            # Update with current price
            stock_data = collector.get_stock_data(symbol)
            if 'error' not in stock_data:
                current_price = stock_data['price_data']['current_price']
                new_manager.update_position(symbol, current_price)
                
                pnl_color = "" if position.unrealized_pnl >= 0 else ""
                print(f"      {symbol:8} | {pnl_color} {position.unrealized_pnl_percent:+6.1f}% | ${position.unrealized_pnl:+8.2f}")
    
    return new_manager

def main():
    print(" DATABASE SYNC TOOL")
    print("=" * 30)
    print("This will:")
    print("1. Clear ALL positions from database")
    print("2. Add corrected positions with proper entry prices")
    print("3. Sync database with current system state")
    print("4. Verify all P&L calculations")
    
    print(f"\n WARNING: This will DELETE all current database positions!")
    confirm = input("Are you sure? Type 'YES' to proceed: ")
    
    if confirm == "YES":
        manager = clean_and_sync_database()
        print(f"\n Database synchronized!")
        print(f"   Next automated_trader.py run should show correct P&L")
    else:
        print("Operation cancelled")

if __name__ == "__main__":
    main()
