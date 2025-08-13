#!/usr/bin/env python3
"""
Verify Manual Positions - Check that SOL and BNB are correctly added and protected
"""

from automated_trader import AutomatedTrader

def verify_manual_positions():
    print("=== VERIFICATION OF MANUAL POSITIONS ===")
    
    # Create trader
    trader = AutomatedTrader(max_positions=5, max_investment_per_stock=3000)
    
    print(f"Total positions: {len(trader.position_manager.positions)}")
    
    for symbol, pos in trader.position_manager.positions.items():
        is_manual = trader.is_manual_position(symbol)
        pos_type = "[MANUAL]" if is_manual else "[AUTO]"
        print(f"{pos_type} {symbol}: {pos.quantity:.8f} @ ${pos.entry_price:.2f}")
        
        if hasattr(pos, 'notes') and pos.notes:
            print(f"    Notes: {pos.notes[:60]}...")
    
    print("\n=== MANUAL POSITION PROTECTION TEST ===")
    # Test protection for manual positions
    manual_symbols = ["SOL-USD", "BNB-USD"]
    for symbol in manual_symbols:
        if symbol in trader.position_manager.positions:
            is_manual = trader.is_manual_position(symbol)
            print(f"{symbol}: Manual detection = {is_manual}")
        else:
            print(f"{symbol}: NOT FOUND in positions")
    
    print("\n=== CURRENT PRICES AND P&L ===")
    for symbol in manual_symbols:
        if symbol in trader.position_manager.positions:
            try:
                # Get current market data
                stock_data = trader.collector.get_stock_data(symbol)
                if 'error' not in stock_data:
                    current_price = stock_data['price_data']['current_price']
                    
                    # Update position with current price
                    trader.position_manager.update_position(symbol, current_price)
                    pos = trader.position_manager.positions[symbol]
                    
                    crypto_name = "SOL" if "SOL" in symbol else "BNB"
                    print(f"{crypto_name}: Current ${current_price:.2f} | P&L: {pos.unrealized_pnl_percent:+.2f}% (${pos.unrealized_pnl:+.2f})")
                else:
                    print(f"{symbol}: Error getting price - {stock_data.get('error')}")
            except Exception as e:
                print(f"{symbol}: Exception - {str(e)[:50]}")

if __name__ == "__main__":
    verify_manual_positions()