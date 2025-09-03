#!/usr/bin/env python3
"""
Restablecer capital inicial del portfolio
"""
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.api.database.database import db_manager

def restore_portfolio_capital():
    try:
        # Verificar el estado actual de portfolio_state
        result = db_manager.execute_query('SELECT * FROM portfolio_state ORDER BY created_at DESC LIMIT 1')
        print('ESTADO ACTUAL PORTFOLIO_STATE:')
        if result:
            state = result[0]
            liquid_stocks = state.get('liquid_capital_stocks', 0)
            liquid_crypto = state.get('liquid_capital_crypto', 0)
            invested_stocks = state.get('invested_capital_stocks', 0)
            invested_crypto = state.get('invested_capital_crypto', 0)
            
            print(f'  Liquid stocks: ${liquid_stocks:,.2f}')
            print(f'  Liquid crypto: ${liquid_crypto:,.2f}')
            print(f'  Invested stocks: ${invested_stocks:,.2f}')
            print(f'  Invested crypto: ${invested_crypto:,.2f}')
            print(f'  Created: {state.get("created_at")}')
        else:
            print('  No hay registros en portfolio_state')
            liquid_stocks = 0

        # Insertar estado inicial si no existe o está en cero
        if not result or liquid_stocks == 0:
            print('\nRESTABLECIENDO CAPITAL INICIAL...')
            current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            
            db_manager.execute_query('''
                INSERT INTO portfolio_state (
                    liquid_capital_stocks,
                    liquid_capital_crypto,
                    invested_capital_stocks,
                    invested_capital_crypto,
                    total_pnl_stocks,
                    total_pnl_crypto,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (70000.0, 30000.0, 0.0, 0.0, 0.0, 0.0, current_time))
            print('Capital inicial restablecido: $70k stocks, $30k crypto')
            
            # Verificar que se insertó correctamente
            result = db_manager.execute_query('SELECT * FROM portfolio_state ORDER BY created_at DESC LIMIT 1')
            if result:
                state = result[0]
                print(f'VERIFICACIÓN - Nuevo estado:')
                print(f'  Liquid stocks: ${state.get("liquid_capital_stocks", 0):,.2f}')
                print(f'  Liquid crypto: ${state.get("liquid_capital_crypto", 0):,.2f}')
        else:
            print('Capital ya está configurado correctamente')

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    restore_portfolio_capital()