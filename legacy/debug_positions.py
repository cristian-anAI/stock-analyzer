#!/usr/bin/env python3
"""
Debug Positions - Investigar discrepancias de precios
"""

import importlib.util
from position_manager import PositionManager

spec = importlib.util.spec_from_file_location("data_collector", "data-collector.py")
data_collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data_collector)

def debug_all_positions():
    collector = data_collector.StockDataCollector()
    manager = PositionManager(collector)
    
    print(" DEBUGGING POSITION PRICES")
    print("=" * 60)
    
    for symbol, position in manager.positions.items():
        print(f"\n {symbol}:")
        print(f"   DB Entry Price: ${position.entry_price:.2f}")
        print(f"   DB Quantity: {position.quantity}")
        print(f"   DB Notes: {position.notes}")
        
        # Test different symbol variations
        test_symbols = [symbol]
        
        # Add variations for European stocks
        if symbol.endswith('.L'):
            test_symbols.append(symbol.replace('.L', ''))
        elif symbol.endswith('.MI'):
            test_symbols.append(symbol.replace('.MI', ''))
        elif symbol in ['PPFB.L']:
            test_symbols.extend(['PPFB', 'PHGP.L', 'SGLD.L'])
        elif symbol in ['VUSD.L']:
            test_symbols.extend(['VUSD', 'SPY', 'VOO'])
        elif symbol in ['SXLE.MI']:
            test_symbols.extend(['SXLE', 'XLU'])
        
        best_price = None
        best_symbol = None
        
        for test_symbol in test_symbols:
            try:
                print(f"   Testing {test_symbol}...", end=" ")
                stock_data = collector.get_stock_data(test_symbol)
                
                if 'error' not in stock_data:
                    current_price = stock_data['price_data']['current_price']
                    print(f"${current_price:.2f} ")
                    
                    if best_price is None:
                        best_price = current_price
                        best_symbol = test_symbol
                    
                    pnl_percent = ((current_price - position.entry_price) / position.entry_price) * 100
                    print(f"      P&L with this price: {pnl_percent:+.1f}%")
                else:
                    print(f"Error: {stock_data.get('error', 'Unknown')}")
            except Exception as e:
                print(f"Exception: {e}")
        if best_symbol != symbol:
            print(f"    RECOMMENDATION: Use {best_symbol} instead of {symbol}")
        print("-" * 40)

def fix_symbol_mappings():
    """Fix incorrect symbols in database"""
    corrections = {
        "PPFB.L": "PHGP.L",
        "VUSD.L": "VOO",
        "SXLE.MI": "XLU",
        "XAG-USD": "SLV",
    }
    print(" SUGGESTED SYMBOL CORRECTIONS:")
    print("=" * 60)
    for old_symbol, new_symbol in corrections.items():
        print(f"   {old_symbol:12} → {new_symbol}")

def check_real_vs_calculated():
    """Compare your real P&L vs calculated"""
    real_positions = {
        "BTC-USD": {"current_value_usd": 642.43, "pnl_percent": 53.81},
        "NDAQ": {"current_value_usd": 5103.69, "pnl_percent": 25.61},
        "BNTX": {"current_value_usd": 254.68, "pnl_percent": 0.95},
        "XAG-USD": {"current_value_eur": 3687.25, "pnl_percent": 9.44},
        "PPFB.L": {"current_value_eur": 508.65, "pnl_percent": 1.10},
        "SXLE.MI": {"current_value_eur": 24002.14, "pnl_percent": -11.32},
        "DFEN": {"current_value_usd": 794.88, "pnl_percent": 0.30},
        "VUSD.L": {"current_value_eur": 934.53, "pnl_percent": 0.91}
    }
    print(" REAL vs CALCULATED P&L:")
    print("=" * 60)
    collector = data_collector.StockDataCollector()
    manager = PositionManager(collector)
    for symbol in manager.positions.keys():
        real_data = real_positions.get(symbol, {})
        if real_data:
            print(f"\n{symbol}:")
            print(f"   Real P&L: {real_data['pnl_percent']:+.1f}%")
            position = manager.positions[symbol]
            print(f"   Calculated P&L: {position.unrealized_pnl_percent:+.1f}%")
            print(f"   Difference: {abs(real_data['pnl_percent'] - position.unrealized_pnl_percent):.1f} percentage points")

def main():
    print(" POSITION DEBUG TOOL")
    print("=" * 30)
    print("1. Debug all positions")
    print("2. Check symbol mappings")
    print("3. Compare real vs calculated P&L")
    print("4. All of the above")
    choice = input("\nChoice (1-4): ").strip()
    if choice == "1":
        debug_all_positions()
    elif choice == "2":
        fix_symbol_mappings()
    elif choice == "3":
        check_real_vs_calculated()
    elif choice == "4":
        debug_all_positions()
        print("\n" + "="*60 + "\n")
        fix_symbol_mappings()
        print("\n" + "="*60 + "\n")
        check_real_vs_calculated()
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()
