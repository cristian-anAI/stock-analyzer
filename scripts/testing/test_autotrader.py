#!/usr/bin/env python3
"""
Test script para probar el AutomatedTrader directamente
"""

from automated_trader import AutomatedTrader
import time

def test_autotrader():
    print("=== TESTING AUTOTRADER ===")
    
    # Create trader
    print("1. Initializing AutomatedTrader...")
    trader = AutomatedTrader(max_positions=3, max_investment_per_stock=2000)
    
    print("\n2. Reloading portfolio from database...")
    trader.position_manager.reload_from_database()
    reloaded = len(trader.position_manager.positions)
    print(f"   Reloaded {reloaded} positions")
    
    print("\n3. Testing crypto data collection...")
    crypto_symbols = ["BTC-USD", "SOL-USD", "BNB-USD"]
    for symbol in crypto_symbols:
        try:
            data = trader.collector.get_stock_data(symbol)
            if 'error' not in data:
                price = data['price_data']['current_price']
                change = data['price_data']['change_percent']
                rsi = data.get('technical_indicators', {}).get('rsi', 0)
                print(f"   {symbol}: ${price:.2f} ({change:+.2f}%) RSI:{rsi:.1f}")
            else:
                print(f"   {symbol}: ERROR - {data['error']}")
        except Exception as e:
            print(f"   {symbol}: EXCEPTION - {str(e)[:50]}")
    
    print("\n4. Testing market scanning (limited to 10 symbols)...")
    # Test scanning with a small subset
    original_watchlist = trader.watchlist
    trader.watchlist = ["AAPL", "MSFT", "BTC-USD", "SOL-USD", "ETH-USD"]
    
    opportunities = trader.scan_for_buy_signals()
    print(f"   Found {len(opportunities)} buy opportunities")
    
    for opp in opportunities[:3]:  # Show first 3
        print(f"   - {opp['symbol']}: Score {opp['buy_score']}, Reasons: {opp['reasons'][:2]}")
    
    print("\n5. Testing position updates...")
    if reloaded > 0:
        trader.update_positions()
    else:
        print("   No positions to update")
    
    print("\n=== TEST COMPLETE ===")
    return trader

if __name__ == "__main__":
    test_autotrader()