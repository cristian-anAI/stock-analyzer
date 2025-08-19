#!/usr/bin/env python3
"""
Stock Analyzer - Punto de entrada principal
"""

import sys
import os
from pathlib import Path

# Añadir el directorio raíz al path para imports
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

def show_menu():
    """Mostrar menú principal"""
    print("\n" + "="*60)
    print("         STOCK ANALYZER - SISTEMA DE TRADING")  
    print("="*60)
    print("1. 🤖 Automated Trader")
    print("2.  Hybrid Trading System") 
    print("3.  Interactive Trading")
    print("4.   Server Trader (24/7)")
    print("5.  Web Dashboard")
    print("6.  Web Monitor")
    print("7.  Database Manager")
    print("8.  Position Manager")
    print("0.  Exit")
    print("="*60)

def main():
    """Función principal"""
    while True:
        show_menu()
        choice = input("\n Choose an option: ").strip()
        
        if choice == "0":
            print("\n Goodbye!")
            break
        elif choice == "1":
            from src.traders.automated_trader import AutomatedTrader
            trader = AutomatedTrader()
            trader.run()
        elif choice == "2":
            from src.traders.hybrid_trading_system import main as hybrid_main
            hybrid_main()
        elif choice == "3":
            from src.traders.interactive_trading import main as interactive_main
            interactive_main()
        elif choice == "4":
            from src.traders.server_trader import ServerTrader
            server = ServerTrader()
            server.run()
        elif choice == "5":
            from src.web.dashboard import main as dashboard_main
            dashboard_main()
        elif choice == "6":
            from src.web.monitor import main as monitor_main
            monitor_main()
        elif choice == "7":
            from src.core.database_manager import DatabaseManager
            db = DatabaseManager()
            print("Database manager initialized")
        elif choice == "8":
            from src.core.position_manager import PositionManager
            pm = PositionManager()
            print("Position manager initialized")
        else:
            print(" Invalid option. Please try again.")

if __name__ == "__main__":
    main()