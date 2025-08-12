#!/usr/bin/env python3
"""
Add Manual Crypto Positions - Script para añadir tus posiciones reales de SOL y BNB
"""

import importlib.util
from datetime import datetime

# Import data-collector.py
spec = importlib.util.spec_from_file_location("data_collector", "data-collector.py")
data_collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data_collector)

from position_manager import PositionManager

def add_crypto_positions():
    """Añadir posiciones reales de SOL y BNB al sistema"""
    
    print("[CRYPTO] ADDING CRYPTO POSITIONS TO PORTFOLIO")
    print("=" * 50)
    
    collector = data_collector.StockDataCollector()
    manager = PositionManager(collector)
    
    # 🔥 DATOS CALCULADOS BASADOS EN TU SCREENSHOT + PRECIOS DE MERCADO 🔥
    
    # 📊 SOL POSITION DATA
    sol_data = {
        "symbol": "SOL-USD",
        "quantity": 0.31373242,
        "current_value_eur": 49.05,  # Del screenshot actualizado
        "current_price_market": 181.83,  # Precio actual de mercado USD
        "pnl_display": "+0.61 €"
    }
    
    # 📊 BNB POSITION DATA  
    bnb_data = {
        "symbol": "BNB-USD",
        "quantity": 0.15871727,
        "current_value_eur": 109.21,  # Del screenshot
        "current_price_market": 808.33,  # Precio actual de mercado USD  
        "pnl_display": "+0.38 €"
    }
    
    # CALCULAR PRECIOS DE ENTRADA PRECISOS
    
    # SOL: Si tu valor actual es 49.05 EUR y tienes ganancia de +0.61 EUR
    sol_entry_value_eur = sol_data["current_value_eur"] - 0.61  # 48.44 EUR
    sol_entry_value_usd = sol_entry_value_eur * 1.05  # Convertir a USD
    sol_entry_price_usd = sol_entry_value_usd / sol_data["quantity"]
    sol_current_value_usd = sol_data["current_value_eur"] * 1.05
    sol_pnl_percent = (0.61 / sol_entry_value_eur) * 100  # % real de ganancia
    
    # BNB: Si tu valor actual es 109.21 EUR y tienes ganancia de +0.38 EUR
    bnb_entry_value_eur = bnb_data["current_value_eur"] - 0.38  # 108.83 EUR
    bnb_entry_value_usd = bnb_entry_value_eur * 1.05  # Convertir a USD
    bnb_entry_price_usd = bnb_entry_value_usd / bnb_data["quantity"]
    bnb_current_value_usd = bnb_data["current_value_eur"] * 1.05
    bnb_pnl_percent = (0.38 / bnb_entry_value_eur) * 100  # % real de ganancia
    
    print(f"[INFO] POSICIONES CALCULADAS:")
    print(f"\n[SOL] SOL (Solana):")
    print(f"   Cantidad: {sol_data['quantity']:.8f} SOL")
    print(f"   Valor actual: EUR{sol_data['current_value_eur']:.2f} (~${sol_current_value_usd:.2f})")
    print(f"   Precio mercado: ${sol_data['current_price_market']:.2f}")
    print(f"   Precio entrada calculado: ${sol_entry_price_usd:.2f}")
    print(f"   P&L real: {sol_pnl_percent:+.2f}% ({sol_data['pnl_display']})")
    
    print(f"\n[BNB] BNB (Binance Coin):")
    print(f"   Cantidad: {bnb_data['quantity']:.8f} BNB")
    print(f"   Valor actual: EUR{bnb_data['current_value_eur']:.2f} (~${bnb_current_value_usd:.2f})")
    print(f"   Precio mercado: ${bnb_data['current_price_market']:.2f}")
    print(f"   Precio entrada calculado: ${bnb_entry_price_usd:.2f}")
    print(f"   P&L real: {bnb_pnl_percent:+.2f}% ({bnb_data['pnl_display']})")
    
    crypto_positions = [
        {
            "symbol": sol_data["symbol"],
            "quantity": sol_data["quantity"], 
            "entry_price": sol_entry_price_usd,
            "current_value_eur": sol_data["current_value_eur"],
            "pnl_display": sol_data["pnl_display"],
            "name": "SOL"
        },
        {
            "symbol": bnb_data["symbol"],
            "quantity": bnb_data["quantity"],
            "entry_price": bnb_entry_price_usd, 
            "current_value_eur": bnb_data["current_value_eur"],
            "pnl_display": bnb_data["pnl_display"],
            "name": "BNB"
        }
    ]
    
    # Confirmar antes de añadir
    print(f"\n{'='*50}")
    confirm = input(f"¿Añadir estas posiciones al sistema? (y/n): ").lower()
    
    if confirm == 'y':
        added_count = 0
        
        for crypto in crypto_positions:
            symbol = crypto["symbol"]
            
            print(f"\n[ADD] Añadiendo {crypto['name']}...")
            
            # Verificar si ya existe
            if symbol in manager.positions:
                print(f"   ⚠️ {symbol} ya existe en el portfolio")
                continue
            
            # Añadir como posición MANUAL
            success = manager.open_position(
                symbol=symbol,
                entry_price=crypto["entry_price"],
                quantity=crypto["quantity"],
                stop_loss_percent=15.0,  # Stop loss más amplio para crypto
                take_profit_percent=50.0,  # Take profit más amplio para crypto
                position_type="MANUAL"
            )
            
            if success:
                # Actualizar notas para indicar que es posición real
                if symbol in manager.positions:
                    pos = manager.positions[symbol]
                    pos.notes = f"Real {crypto['name']} position - REVOLUT - Manual (Original: €{crypto['current_value_eur']:.2f}, P&L: {crypto['pnl_display']})"
                    
                    # Actualizar en database
                    from dataclasses import asdict
                    if manager.db_manager:
                        manager.db_manager.update_position(asdict(pos))
                
                print(f"   [OK] {crypto['name']} añadido exitosamente!")
                added_count += 1
                
                # Actualizar con precio actual real del mercado
                try:
                    stock_data = collector.get_stock_data(symbol)
                    if 'error' not in stock_data:
                        real_current_price = stock_data['price_data']['current_price']
                        manager.update_position(symbol, real_current_price)
                        
                        updated_pos = manager.positions[symbol]
                        print(f"   [PRICE] Precio mercado: ${real_current_price:.2f}")
                        print(f"   [P&L] P&L calculado: {updated_pos.unrealized_pnl_percent:+.1f}%")
                        print(f"   [USD] P&L en USD: ${updated_pos.unrealized_pnl:+.2f}")
                    else:
                        print(f"   ⚠️ No se pudo obtener precio de mercado: {stock_data.get('error')}")
                except Exception as e:
                    print(f"   ⚠️ Error actualizando precio: {e}")
            else:
                print(f"   ❌ Error añadiendo {crypto['name']}")
        
        if added_count > 0:
            print(f"\n[SUCCESS] RESUMEN:")
            print(f"   [OK] {added_count} posiciones crypto añadidas")
            print(f"   [SAFE] Tipo: MANUAL (solo monitoreo, NO venta automática)")
            print(f"   [INFO] El sistema mostrará P&L en tiempo real")
            
            # Mostrar dashboard actualizado
            print(f"\n[PORTFOLIO] CRYPTO ACTUALIZADO:")
            manager.print_portfolio_dashboard()
        else:
            print(f"\n⚠️ No se añadieron nuevas posiciones")
    else:
        print("Operación cancelada")

def verify_crypto_positions():
    """Verificar si SOL y BNB ya están en el portfolio"""
    collector = data_collector.StockDataCollector()
    manager = PositionManager(collector)
    
    crypto_symbols = ["SOL-USD", "BNB-USD"]
    existing_positions = []
    
    for symbol in crypto_symbols:
        if symbol in manager.positions:
            pos = manager.positions[symbol]
            existing_positions.append({
                "symbol": symbol,
                "quantity": pos.quantity,
                "entry_price": pos.entry_price,
                "pnl_percent": pos.unrealized_pnl_percent,
                "position_type": getattr(pos, 'position_type', 'AUTO')
            })
    
    if existing_positions:
        print(f"\n[INFO] Posiciones crypto existentes en tu portfolio:")
        for pos in existing_positions:
            crypto_name = "SOL" if "SOL" in pos["symbol"] else "BNB"
            print(f"   {crypto_name}: {pos['quantity']:.8f} @ ${pos['entry_price']:.2f} | P&L: {pos['pnl_percent']:+.1f}% | Type: {pos['position_type']}")
        return True
    else:
        print(f"\n[INFO] No hay posiciones crypto en tu portfolio actual")
        return False

def main():
    print("[CRYPTO] POSITION MANAGER")
    print("=" * 30)
    
    # Verificar si ya existe
    exists = verify_crypto_positions()
    
    if exists:
        print("\n¿Qué quieres hacer?")
        print("1. Añadir posiciones adicionales")
        print("2. Ver detalles actuales")
        print("3. Salir")
        choice = input("Opción (1-3): ").strip()
        
        if choice == "1":
            add_crypto_positions()
        elif choice == "2":
            collector = data_collector.StockDataCollector()
            manager = PositionManager(collector)
            manager.print_portfolio_dashboard()
        
    else:
        print("\n¿Quieres añadir tus posiciones SOL y BNB al sistema?")
        print("Esto permitirá:")
        print("- Monitorear el precio en tiempo real")
        print("- Ver P&L actualizado")
        print("- Recibir alertas si hay movimientos importantes")
        print("- Las posiciones serán MANUAL (no se venderán automáticamente)")
        
        confirm = input("\nProceder? (y/n): ").lower()
        if confirm == 'y':
            add_crypto_positions()
        else:
            print("Operación cancelada")

if __name__ == "__main__":
    main()