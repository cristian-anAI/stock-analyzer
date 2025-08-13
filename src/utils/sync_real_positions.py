#!/usr/bin/env python3
"""
Sync Real Positions - Sincroniza el dashboard con las posiciones reales del servidor
"""

from automated_trader import AutomatedTrader
import json
import os
from datetime import datetime

def sync_real_positions():
    print("=== OBTENIENDO POSICIONES REALES DEL SERVIDOR ===")
    
    # Obtener posiciones reales
    trader = AutomatedTrader()
    real_positions = {}
    
    print(f"Posiciones encontradas: {len(trader.position_manager.positions)}")
    
    for symbol, pos in trader.position_manager.positions.items():
        is_manual = trader.is_manual_position(symbol)
        
        # Actualizar con precio actual
        try:
            print(f"Actualizando {symbol}...", end=" ")
            stock_data = trader.collector.get_stock_data(symbol)
            if 'error' not in stock_data:
                current_price = stock_data['price_data']['current_price']
                trader.position_manager.update_position(symbol, current_price)
                updated_pos = trader.position_manager.positions[symbol]
                
                real_positions[symbol] = {
                    'type': 'MANUAL' if is_manual else 'AUTO',
                    'quantity': updated_pos.quantity,
                    'entry_price': updated_pos.entry_price,
                    'current_price': current_price,
                    'pnl_percent': updated_pos.unrealized_pnl_percent,
                    'pnl_usd': updated_pos.unrealized_pnl
                }
                
                print(f"[OK] {updated_pos.unrealized_pnl_percent:+.2f}% (${updated_pos.unrealized_pnl:+.2f})")
            else:
                print(f"[ERROR] {stock_data.get('error')}")
        except Exception as e:
            print(f"[EXCEPTION] {str(e)[:50]}")
    
    # Calcular P&L total
    total_pnl = sum(pos['pnl_usd'] for pos in real_positions.values())
    
    # Crear status real
    real_status = {
        'timestamp': datetime.now().isoformat(),
        'uptime_hours': 1.0,
        'running': True,
        'positions': real_positions,
        'total_pnl': total_pnl
    }
    
    # Guardar status real
    os.makedirs('web', exist_ok=True)
    with open('web/status.json', 'w') as f:
        json.dump(real_status, f, indent=2)
    
    print(f"\n=== STATUS ACTUALIZADO ===")
    print(f"Total posiciones: {len(real_positions)}")
    print(f"P&L Total: ${total_pnl:.2f}")
    print("Dashboard sincronizado con posiciones reales")
    
    # Mostrar resumen
    print(f"\n=== RESUMEN DE POSICIONES REALES ===")
    manual_positions = [s for s, p in real_positions.items() if p['type'] == 'MANUAL']
    auto_positions = [s for s, p in real_positions.items() if p['type'] == 'AUTO']
    
    print(f"[MANUAL] Protegidas: {manual_positions}")
    print(f"[AUTO] Automaticas: {auto_positions}")
    
    return real_status

if __name__ == "__main__":
    sync_real_positions()