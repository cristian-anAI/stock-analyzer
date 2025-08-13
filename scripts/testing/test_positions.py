#!/usr/bin/env python3
"""
Test Positions - Sistema de pruebas para PositionManager
"""

import sys
import os
import importlib.util
from datetime import datetime, timedelta
import time

# Import desde data-collector.py (con guión)
spec = importlib.util.spec_from_file_location("data_collector", "data-collector.py")
data_collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data_collector)
StockDataCollector = data_collector.StockDataCollector

from position_manager import PositionManager, PositionDecision

def test_position_management():
    """Test básico del sistema"""
    
    print(" INICIANDO SISTEMA DE GESTIÓN DE POSICIONES")
    print("=" * 60)
    
    # Inicializar
    collector = StockDataCollector()
    manager = PositionManager(collector)
    
    # Abrir posiciones de prueba
    test_positions = [
        {"symbol": "AAPL", "entry_price": 218.50, "quantity": 100},
        {"symbol": "MSFT", "entry_price": 415.20, "quantity": 50},
        {"symbol": "GOOGL", "entry_price": 158.30, "quantity": 75}
    ]
    
    print("\n Abriendo posiciones de prueba...")
    for pos in test_positions:
        manager.open_position(
            symbol=pos["symbol"],
            entry_price=pos["entry_price"], 
            quantity=pos["quantity"]
        )
    
    print(f"\n {len(manager.positions)} posiciones abiertas")
    
    # Análizar posiciones
    print(f"\n Analizando posiciones...")
    for symbol in manager.positions.keys():
        # Obtener datos actuales
        stock_data = collector.get_stock_data(symbol)
        if 'error' not in stock_data:
            current_price = stock_data['price_data']['current_price']
            manager.update_position(symbol, current_price)
            
            decision, reasons = manager.analyze_position_decision(symbol)
            position = manager.positions[symbol]
            
            print(f"\n {symbol}:")
            print(f"    P&L: ${position.unrealized_pnl:.2f} ({position.unrealized_pnl_percent:+.1f}%)")
            print(f"    Decisión: {decision.value}")
    
    # Dashboard
    manager.print_portfolio_dashboard()
    
    print(f"\n Testing completado!")
    return manager

if __name__ == "__main__":
    print(" TESTING - POSITION MANAGER")
    print("=" * 50)
    
    try:
        manager = test_position_management()
        print("\n Sistema funcionando correctamente!")
    except Exception as e:
        print(f" Error: {e}")
        import traceback
        traceback.print_exc()
