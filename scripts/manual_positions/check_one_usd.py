#!/usr/bin/env python3
"""
Check ONE-USD Purchase - See what happened with the ONE-USD position
"""

from automated_trader import AutomatedTrader

def check_one_usd():
    print("=== CHECKING ONE-USD PURCHASE ===")
    
    # Create trader to check current positions
    trader = AutomatedTrader()
    
    # Check if ONE-USD is in positions
    if 'ONE-USD' in trader.position_manager.positions:
        pos = trader.position_manager.positions['ONE-USD']
        print(f"[OK] ONE-USD encontrado en portfolio:")
        print(f"   Cantidad: {pos.quantity:.8f} ONE")
        print(f"   Precio entrada: ${pos.entry_price:.4f}")
        print(f"   Valor total: ${pos.entry_price * pos.quantity:.2f}")
        print(f"   Tipo: {getattr(pos, 'position_type', 'AUTO')}")
        print(f"   Stop Loss: {getattr(pos, 'stop_loss_percent', 'N/A')}%")
        print(f"   Take Profit: {getattr(pos, 'take_profit_percent', 'N/A')}%")
        
        if hasattr(pos, 'notes') and pos.notes:
            print(f"   Notes: {pos.notes}")
        
        # Get current market data
        try:
            stock_data = trader.collector.get_stock_data('ONE-USD')
            if 'error' not in stock_data:
                current_price = stock_data['price_data']['current_price']
                change_pct = stock_data['price_data']['change_percent']
                rsi = stock_data.get('technical_indicators', {}).get('rsi', 'N/A')
                
                # Update P&L
                trader.position_manager.update_position('ONE-USD', current_price)
                updated_pos = trader.position_manager.positions['ONE-USD']
                
                print(f"\n[MARKET] DATOS ACTUALES:")
                print(f"   Precio actual: ${current_price:.4f}")
                print(f"   Cambio 24h: {change_pct:+.2f}%")
                print(f"   RSI: {rsi}")
                print(f"   P&L: {updated_pos.unrealized_pnl_percent:+.2f}% (${updated_pos.unrealized_pnl:+.2f})")
                
                # Show why it might have been bought
                print(f"\n[ANALYSIS] POR QUE SE COMPRO:")
                print(f"   - RSI: {rsi} (oversold si < 35)")
                print(f"   - Cambio reciente: {change_pct:+.2f}%")
                
            else:
                print(f"   Error obteniendo precio actual: {stock_data.get('error')}")
        except Exception as e:
            print(f"   Error: {str(e)[:50]}...")
    else:
        print("[INFO] ONE-USD no encontrado en portfolio actual")
        print("\nPosiciones actuales:")
        for symbol in trader.position_manager.positions.keys():
            pos = trader.position_manager.positions[symbol]
            pos_type = "[MANUAL]" if trader.is_manual_position(symbol) else "[AUTO]"
            print(f"  {pos_type} {symbol}: {pos.quantity:.6f} @ ${pos.entry_price:.4f}")

def explain_harmony():
    print("\n=== QUE ES HARMONY (ONE) ===")
    print("Harmony (ONE) es una blockchain de Layer 1 que se enfoca en:")
    print("- Escalabilidad y velocidad de transacciones")
    print("- Interoperabilidad entre diferentes blockchains") 
    print("- DeFi y aplicaciones descentralizadas")
    print("- Sharding para mejorar el rendimiento")
    print("\nCaracteristicas:")
    print("- Precio historico: $0.01 - $0.38 (muy volatil)")
    print("- Market cap relativamente pequeno (alta volatilidad)")
    print("- Proyecto con desarrollo activo")
    print("- Riesgo: ALTO (altcoin pequeña)")

if __name__ == "__main__":
    check_one_usd()
    explain_harmony()