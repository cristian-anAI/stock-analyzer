#!/usr/bin/env python3
"""
Fix Positions with Real P&L - Usar precios actuales del sistema + tu P&L real
"""

import importlib.util
from position_manager import PositionManager

spec = importlib.util.spec_from_file_location("data_collector", "data-collector.py")
data_collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data_collector)

def fix_with_real_pnl():
    """Fix entry prices usando current system prices + real P&L"""
    collector = data_collector.StockDataCollector()
    manager = PositionManager(collector)
    print("🔧 FIXING POSITIONS WITH REAL P&L DATA")
    print("=" * 50)
    # Tu P&L real por posición
    real_pnl_data = {
        "NDAQ": 25.61,
        "BNTX": 0.95,
        "DFEN": 0.30,
        "GLD": 1.10,
        "XLU": -11.32,
        "VOO": 0.91,
        "SLV": 9.44,
    }
    print("Paso 1: Obtener precios actuales del sistema")
    current_prices = {}
    for symbol in real_pnl_data.keys():
        if symbol in manager.positions:
            try:
                print(f"   Getting current price for {symbol}...", end=" ")
                stock_data = collector.get_stock_data(symbol)
                if 'error' not in stock_data:
                    current_price = stock_data['price_data']['current_price']
                    current_prices[symbol] = current_price
                    print(f"${current_price:.2f} ✅")
                else:
                    print(f"Error ❌")
            except Exception as e:
                print(f"Exception: {e} ❌")
    print(f"\nPaso 2: Calcular entry prices correctos")
    for symbol, real_pnl_percent in real_pnl_data.items():
        if symbol in current_prices and symbol in manager.positions:
            current_price = current_prices[symbol]
            position = manager.positions[symbol]
            correct_entry_price = current_price / (1 + real_pnl_percent / 100)
            print(f"\n📊 {symbol}:")
            print(f"   Current Price (system): ${current_price:.2f}")
            print(f"   Real P&L: {real_pnl_percent:+.2f}%")
            print(f"   Old Entry Price: ${position.entry_price:.2f}")
            print(f"   Calculated Entry Price: ${correct_entry_price:.2f}")
            old_entry = position.entry_price
            position.entry_price = correct_entry_price
            position.current_price = current_price
            total_value = current_price * position.quantity
            entry_value = correct_entry_price * position.quantity
            position.unrealized_pnl = total_value - entry_value
            position.unrealized_pnl_percent = (position.unrealized_pnl / entry_value) * 100
            print(f"   New P&L: {position.unrealized_pnl_percent:+.2f}% ✅")
            print(f"   P&L Amount: ${position.unrealized_pnl:+.2f}")
            from dataclasses import asdict
            if manager.db_manager:
                try:
                    manager.db_manager.update_position(asdict(position))
                    print(f"   Database updated ✅")
                except Exception as e:
                    print(f"   Database error: {e} ❌")
    return manager

def verify_portfolio(manager):
    """Verify final portfolio looks correct"""
    print(f"\n✅ FINAL PORTFOLIO VERIFICATION")
    print("=" * 50)
    total_pnl = 0
    total_value = 0
    for symbol, position in manager.positions.items():
        current_value = position.current_price * position.quantity
        entry_value = position.entry_price * position.quantity
        total_value += current_value
        total_pnl += position.unrealized_pnl
        pnl_color = "📈" if position.unrealized_pnl >= 0 else "📉"
        print(f"{symbol:8} | {pnl_color} {position.unrealized_pnl_percent:+6.1f}% | ${position.unrealized_pnl:+8.2f} | Value: ${current_value:8.2f}")
    print("-" * 70)
    print(f"{'TOTAL':8} | Portfolio P&L: ${total_pnl:+.2f} | Total Value: ${total_value:.2f}")
    print(f"\n📊 EXPECTED vs ACTUAL:")
    print(f"   Expected positive positions: NDAQ, GLD, VOO, SLV, DFEN")
    print(f"   Expected negative positions: BNTX (small), XLU")
    print(f"   Total P&L should be positive (you have more winners than losers)")

def show_comparison():
    """Show before/after comparison"""
    real_values = {
        "BTC": {"value_usd": 642.43, "pnl": 53.81},
        "NDAQ": {"value_usd": 5103.69, "pnl": 25.61},
        "BNTX": {"value_usd": 254.68, "pnl": 0.95},
        "XAG/SLV": {"value_eur": 3687.25, "pnl": 9.44},
        "PPFB/GLD": {"value_eur": 508.65, "pnl": 1.10},
        "SXLE/XLU": {"value_eur": 24002.14, "pnl": -11.32},
        "DFEN": {"value_usd": 794.88, "pnl": 0.30},
        "VUSD/VOO": {"value_eur": 934.53, "pnl": 0.91}
    }
    print(f"\n📋 YOUR REAL PORTFOLIO FOR REFERENCE:")
    print("=" * 50)
    total_real_value_eur = 0
    total_real_value_usd = 0
    for asset, data in real_values.items():
        pnl_color = "📈" if data["pnl"] >= 0 else "📉"
        if "value_usd" in data:
            print(f"{asset:12} | {pnl_color} {data['pnl']:+6.1f}% | ${data['value_usd']:8.2f}")
            total_real_value_usd += data['value_usd']
        else:
            print(f"{asset:12} | {pnl_color} {data['pnl']:+6.1f}% | €{data['value_eur']:8.2f}")
            total_real_value_eur += data['value_eur']
    print(f"\nReal Total: ${total_real_value_usd:.2f} + €{total_real_value_eur:.2f}")
    print(f"            ≈ ${total_real_value_usd + total_real_value_eur * 1.05:.2f} (EUR→USD @1.05)")

def main():
    print("🔧 POSITION FIXER - REAL P&L METHOD")
    print("=" * 40)
    print("This will:")
    print("1. Use current system prices (no change)")
    print("2. Calculate correct entry prices from your real P&L")
    print("3. Update database with corrected positions")
    print("4. Verify final portfolio matches expectations")
    print("\n📊 Reference: Your Real P&L Data:")
    print("   NDAQ: +25.61% | BNTX: +0.95% | DFEN: +0.30%")
    print("   GLD: +1.10% | XLU: -11.32% | VOO: +0.91% | SLV: +9.44%")
    confirm = input(f"\nProceed with fix? (y/n): ").lower()
    if confirm == 'y':
        show_comparison()
        manager = fix_with_real_pnl()
        verify_portfolio(manager)
        print(f"\n✅ Portfolio fixed using real P&L data!")
        print(f"   Next automated_trader.py update should show correct values")
    else:
        print("Operation cancelled")

if __name__ == "__main__":
    main()
