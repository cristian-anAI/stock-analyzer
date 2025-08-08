#!/usr/bin/env python3
"""
Interactive Position Manager - Sistema interactivo de gestión
"""

import sys
import importlib.util
from datetime import datetime

# Import data-collector.py
spec = importlib.util.spec_from_file_location("data_collector", "data-collector.py")
data_collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data_collector)
StockDataCollector = data_collector.StockDataCollector

from position_manager import PositionManager, PositionDecision

def main_menu():
    """Menú principal interactivo"""
    collector = StockDataCollector()
    manager = PositionManager(collector)
    
    # Cargar posiciones demo
    load_demo_positions(manager)
    
    while True:
        print(f"\n{'='*60}")
        print(" AI TRADING SYSTEM - POSITION MANAGER")
        print(f"{'='*60}")
        print("1.  Ver Dashboard del Portfolio")
        print("2.  Abrir nueva posición") 
        print("3.  Actualizar todas las posiciones")
        print("4.  Análisis individual de posición")
        print("5.  Cerrar posición")
        print("6.  Guardar estado")
        print("7.  Salir")
        
        choice = input(f"\nSelecciona una opción (1-7): ").strip()
        
        if choice == '1':
            manager.print_portfolio_dashboard()
            
        elif choice == '2':
            open_new_position(manager, collector)
            
        elif choice == '3':
            print(f"\n Actualizando todas las posiciones...")
            update_all_positions_interactive(manager)
            
        elif choice == '4':
            analyze_single_position(manager)
            
        elif choice == '5':
            close_position_interactive(manager)
            
        elif choice == '6':
            filename = manager.save_to_file()
            print(f" Estado guardado en: {filename}")
            
        elif choice == '7':
            print(f"\n Cerrando sistema...")
            break
            
        else:
            print(f" Opción inválida. Intenta de nuevo.")
        
        input(f"\nPresiona Enter para continuar...")

def load_demo_positions(manager):
    """Carga posiciones demo para testing"""
    demo_positions = [
        {"symbol": "AAPL", "entry_price": 220.00, "quantity": 100},
        {"symbol": "TSLA", "entry_price": 250.00, "quantity": 50},
        {"symbol": "GOOGL", "entry_price": 160.00, "quantity": 75}
    ]
    
    print(f"\n Cargando posiciones demo...")
    for pos in demo_positions:
        manager.open_position(
            symbol=pos["symbol"],
            entry_price=pos["entry_price"],
            quantity=pos["quantity"],
            stop_loss_percent=5.0,
            take_profit_percent=12.0
        )

def open_new_position(manager, collector):
    """Interfaz para abrir nueva posición"""
    print(f"\n ABRIR NUEVA POSICIÓN")
    print("-" * 30)
    
    symbol = input("Ticker (ej: AAPL): ").upper().strip()
    if not symbol:
        print(" Ticker requerido")
        return
    
    # Obtener precio actual
    print(f" Obteniendo datos de {symbol}...")
    stock_data = collector.get_stock_data(symbol)
    
    if 'error' in stock_data:
        print(f" Error: {stock_data['error']}")
        return
    
    current_price = stock_data['price_data']['current_price']
    print(f" Precio actual de {symbol}: ${current_price:.2f}")
    
    try:
        entry_price = float(input(f"Precio entrada (actual: {current_price:.2f}): ") or current_price)
        quantity = int(input("Cantidad de acciones: "))
        
        stop_loss = float(input("Stop loss % (default 5%): ") or 5.0)
        take_profit = float(input("Take profit % (default 12%): ") or 12.0)
        
        success = manager.open_position(symbol, entry_price, quantity, stop_loss, take_profit)
        
        if success:
            print(f" Posición abierta exitosamente!")
            
            # Mostrar análisis inmediato
            manager.update_position(symbol, current_price)
            decision, reasons = manager.analyze_position_decision(symbol)
            print(f" Análisis inicial: {decision.value}")
            
    except ValueError:
        print(" Error en los valores ingresados")

def update_all_positions_interactive(manager):
    """Actualiza posiciones con feedback detallado"""
    if not manager.positions:
        print(" No hay posiciones activas")
        return
    
    decisions_count = {decision.value: 0 for decision in PositionDecision}
    
    for symbol in manager.positions.keys():
        print(f"\n Analizando {symbol}...")
        
        # Obtener datos actuales
        stock_data = manager.stock_collector.get_stock_data(symbol)
        if 'error' in stock_data:
            print(f"    Error obteniendo datos")
            continue
        
        current_price = stock_data['price_data']['current_price']
        manager.update_position(symbol, current_price)
        
        decision, reasons = manager.analyze_position_decision(symbol)
        decisions_count[decision.value] += 1
        
        position = manager.positions[symbol]
        pnl_color = "" if position.unrealized_pnl >= 0 else ""
        
        print(f"    Precio: ${current_price:.2f}")
        print(f"   {pnl_color} P&L: ${position.unrealized_pnl:.2f} ({position.unrealized_pnl_percent:+.1f}%)")
        print(f"    Decisión: {decision.value}")
        
        if reasons:
            print(f"    Razones: {reasons[0]}")
        
        # Ejecutar acciones automáticas
        if decision == PositionDecision.TAKE_PARTIAL_PROFIT:
            print(f"    Ejecutando venta parcial automática...")
            manager.execute_partial_profit(symbol)
    
    # Resumen de decisiones
    print(f"\n RESUMEN DE DECISIONES:")
    for decision, count in decisions_count.items():
        if count > 0:
            icon = "" if "HOLD" in decision else "" if "CONSIDER" in decision else ""
            print(f"   {icon} {decision}: {count} posiciones")

def analyze_single_position(manager):
    """Análisis detallado de una posición específica"""
    if not manager.positions:
        print(" No hay posiciones activas")
        return
    
    print(f"\nPosiciones disponibles:")
    for i, symbol in enumerate(manager.positions.keys(), 1):
        pos = manager.positions[symbol]
        print(f"{i}. {symbol} - P&L: ${pos.unrealized_pnl:.2f}")
    
    try:
        choice = int(input(f"\nSelecciona posición (1-{len(manager.positions)}): "))
        symbol = list(manager.positions.keys())[choice - 1]
        
        print(f"\n ANÁLISIS DETALLADO: {symbol}")
        print("-" * 40)
        
        # Actualizar con datos actuales
        stock_data = manager.stock_collector.get_stock_data(symbol)
        if 'error' in stock_data:
            print(f" Error: {stock_data['error']}")
            return
        
        current_price = stock_data['price_data']['current_price']
        manager.update_position(symbol, current_price)
        
        position = manager.positions[symbol]
        decision, reasons = manager.analyze_position_decision(symbol)
        
        # Mostrar detalles completos
        print(f" Posición: {position.quantity} acciones")
        print(f" Entrada: {position.entry_date} @ ${position.entry_price:.2f}")
        print(f" Actual: ${current_price:.2f}")
        print(f" P&L: ${position.unrealized_pnl:.2f} ({position.unrealized_pnl_percent:+.1f}%)")
        print(f" Stop Loss: ${position.trailing_stop:.2f}")
        print(f" Take Profit: ${position.take_profit:.2f}")
        print(f" Decisión: {decision.value}")
        
        if reasons:
            print(f"\n Análisis técnico:")
            for reason in reasons:
                print(f"    {reason}")
        
        # Mostrar indicadores técnicos
        tech = stock_data.get('technical_indicators', {})
        if tech.get('rsi'):
            print(f"\n Indicadores técnicos:")
            print(f"   RSI: {tech.get('rsi', 'N/A'):.1f}")
            print(f"   MACD: {tech.get('macd', 'N/A'):.2f}")
            print(f"   BB Position: {tech.get('bb_position', 'N/A'):.1f}%")
        
    except (ValueError, IndexError):
        print(" Selección inválida")

def close_position_interactive(manager):
    """Interfaz para cerrar posición"""
    if not manager.positions:
        print(" No hay posiciones activas")
        return
    
    print(f"\nPosiciones disponibles para cerrar:")
    for i, (symbol, pos) in enumerate(manager.positions.items(), 1):
        pnl_color = "" if pos.unrealized_pnl >= 0 else ""
        print(f"{i}. {symbol} - {pnl_color} P&L: ${pos.unrealized_pnl:.2f}")
    
    try:
        choice = int(input(f"\nSelecciona posición a cerrar (1-{len(manager.positions)}): "))
        symbol = list(manager.positions.keys())[choice - 1]
        
        reason = input(f"Razón para cerrar (opcional): ").strip() or "Manual close"
        
        result = manager.close_position(symbol, reason)
        if result:
            pnl_color = "" if result['pnl'] >= 0 else ""
            print(f"{pnl_color} Posición cerrada: P&L final ${result['pnl']:.2f}")
        
    except (ValueError, IndexError):
        print(" Selección inválida")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n\n Sistema cerrado por el usuario")
    except Exception as e:
        print(f"\n Error inesperado: {e}")
        import traceback
        traceback.print_exc()
