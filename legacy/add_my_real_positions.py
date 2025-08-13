#!/usr/bin/env python3
"""
Add My Real Positions - Script con datos reales precalculados
"""

import importlib.util
from datetime import datetime

spec = importlib.util.spec_from_file_location("data_collector", "data-collector.py")
data_collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data_collector)

from position_manager import PositionManager

def add_all_real_positions():
    """Add all real positions with calculated average prices"""
    
    collector = data_collector.StockDataCollector()
    manager = PositionManager(collector)
    
    print("🏦 ADDING ALL REAL PORTFOLIO POSITIONS")
    print("=" * 50)
    
    # My real positions with calculated average prices
    positions = [
        # REVOLUT
        {
            "symbol": "BTC-USD",
            "entry_price": 75949.53,
            "quantity": 0.0055,
            "broker": "REVOLUT",
            "type": "crypto",
            "stop_loss_pct": 15.0,
            "take_profit_pct": 30.0,
            "notes": "Real BTC position - avg price calculated from +53.81% gain"
        },
        {
            "symbol": "NDAQ",
            "entry_price": 560.19,
            "quantity": 7.2547,
            "broker": "REVOLUT", 
            "type": "stock",
            "stop_loss_pct": 8.0,
            "take_profit_pct": 15.0,
            "notes": "Real NDAQ position - avg price calculated from +25.61% gain"
        },
        {
            "symbol": "BNTX",
            "entry_price": 166.55,
            "quantity": 1.5146,
            "broker": "REVOLUT",
            "type": "stock", 
            "stop_loss_pct": 10.0,
            "take_profit_pct": 20.0,
            "notes": "Real BNTX position - avg price calculated from +0.95% gain"
        },
        {
            "symbol": "XAG-USD",
            "entry_price": 316.23,  # EUR converted
            "quantity": 10.6568,
            "broker": "REVOLUT",
            "type": "commodity",
            "stop_loss_pct": 12.0,
            "take_profit_pct": 25.0,
            "notes": "Real Silver position - avg price calculated from +9.44% gain"
        },
        
        # DEGIRO
        {
            "symbol": "PPFB.L",  # London exchange
            "entry_price": 167.71,  # EUR
            "quantity": 3,
            "broker": "DEGIRO",
            "type": "ETF",
            "stop_loss_pct": 8.0,
            "take_profit_pct": 15.0,
            "notes": "Real Gold ETC position - avg price calculated from +1.10% gain"
        },
        {
            "symbol": "SXLE.MI",  # Milan exchange
            "entry_price": 933.58,  # EUR
            "quantity": 29,
            "broker": "DEGIRO",
            "type": "ETF",
            "stop_loss_pct": 10.0,
            "take_profit_pct": 12.0,
            "notes": "Real STOXX Utilities position - avg price calculated from -11.32% loss"
        },
        {
            "symbol": "DFEN",
            "entry_price": 198.13,
            "quantity": 4,
            "broker": "DEGIRO",
            "type": "ETF",
            "stop_loss_pct": 8.0,
            "take_profit_pct": 15.0,
            "notes": "Real Defense ETF position - avg price calculated from +0.30% gain"
        },
        {
            "symbol": "VUSD.L",  # Vanguard S&P 500
            "entry_price": 308.72,  # EUR
            "quantity": 3,
            "broker": "DEGIRO", 
            "type": "ETF",
            "stop_loss_pct": 6.0,
            "take_profit_pct": 12.0,
            "notes": "Real S&P 500 ETF position - avg price calculated from +0.91% gain"
        }
    ]
    
    added_count = 0
    total_value = 0
    
    for pos_data in positions:
        try:
            print(f"\n📊 Adding {pos_data['symbol']} ({pos_data['broker']})...")
            
            # Calculate position value
            pos_value = pos_data['entry_price'] * pos_data['quantity']
            total_value += pos_value
            
            success = manager.open_position(
                symbol=pos_data['symbol'],
                entry_price=pos_data['entry_price'],
                quantity=pos_data['quantity'],
                stop_loss_percent=pos_data['stop_loss_pct'],
                take_profit_percent=pos_data['take_profit_pct']
            )
            
            if success:
                # Update notes
                if pos_data['symbol'] in manager.positions:
                    pos = manager.positions[pos_data['symbol']]
                    pos.notes = pos_data['notes']
                    
                    # Update in database
                    from dataclasses import asdict
                    if manager.db_manager:
                        manager.db_manager.update_position(asdict(pos))
                
                print(f"   ✅ Added: {pos_data['quantity']} @ ${pos_data['entry_price']:.2f}")
                print(f"   💰 Position value: ${pos_value:,.2f}")
                added_count += 1
            else:
                print(f"   ❌ Failed to add {pos_data['symbol']}")
                
        except Exception as e:
            print(f"   ❌ Error adding {pos_data['symbol']}: {e}")
    
    print(f"\n📈 PORTFOLIO SUMMARY:")
    print(f"   Positions added: {added_count}/{len(positions)}")
    print(f"   Total portfolio value: ${total_value:,.2f}")
    
    # Show detailed portfolio
    print(f"\n💼 DETAILED PORTFOLIO:")
    manager.print_portfolio_dashboard()
    
    return manager

def update_positions_with_current_prices():
    """Update all positions with current market prices"""
    print(f"\n🔄 UPDATING WITH CURRENT PRICES...")
    
    collector = data_collector.StockDataCollector()
    manager = PositionManager(collector)
    
    updated = 0
    for symbol in manager.positions.keys():
        try:
            print(f"   Updating {symbol}...", end=" ")
            stock_data = collector.get_stock_data(symbol)
            
            if 'error' not in stock_data:
                current_price = stock_data['price_data']['current_price']
                manager.update_position(symbol, current_price)
                print(f"${current_price:.2f} ✅")
                updated += 1
            else:
                print(f"Error ❌")
        except Exception as e:
            print(f"Error: {e} ❌")
    
    print(f"\n   Updated {updated} positions with current prices")
    return manager

def main():
    print("🏦 MY REAL PORTFOLIO SETUP")
    print("=" * 30)
    print("1. Add all positions")
    print("2. Add positions + update prices")
    print("3. Just update existing positions")
    
    choice = input("\nChoice (1-3): ").strip()
    
    if choice == "1":
        add_all_real_positions()
    elif choice == "2":
        manager = add_all_real_positions()
        update_positions_with_current_prices()
        print(f"\n💼 FINAL PORTFOLIO WITH CURRENT P&L:")
        manager.print_portfolio_dashboard()
    elif choice == "3":
        update_positions_with_current_prices()
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()
