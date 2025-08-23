#!/usr/bin/env python3
"""
Diagnose Portfolio Discrepancies - Find inconsistencies between PortfolioManager and database
"""

import sys
import os
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from api.services.portfolio_manager import portfolio_manager
from api.database.database import db_manager

def diagnose_discrepancies():
    """Diagnose discrepancies between PortfolioManager and database"""
    
    print("=" * 80)
    print("    PORTFOLIO DISCREPANCY DIAGNOSIS")
    print("=" * 80)
    
    # 1. Get PortfolioManager state (in-memory)
    print("\n[1] PORTFOLIO MANAGER STATE (IN-MEMORY):")
    summary = portfolio_manager.get_portfolio_summary()
    
    pm_stocks_liquid = summary['stocks']['liquid_capital']
    pm_stocks_invested = summary['stocks']['invested_capital']
    pm_crypto_liquid = summary['crypto']['liquid_capital'] 
    pm_crypto_invested = summary['crypto']['invested_capital']
    pm_stocks_pnl = summary['stocks']['total_pnl']
    pm_crypto_pnl = summary['crypto']['total_pnl']
    
    print(f"   Stocks: Liquid=${pm_stocks_liquid:,.0f}, Invested=${pm_stocks_invested:,.0f}, P&L=${pm_stocks_pnl:,.2f}")
    print(f"   Crypto: Liquid=${pm_crypto_liquid:,.0f}, Invested=${pm_crypto_invested:,.0f}, P&L=${pm_crypto_pnl:,.2f}")
    
    # 2. Get actual positions from database
    print("\n[2] ACTUAL POSITIONS IN DATABASE:")
    positions = db_manager.execute_query("""
        SELECT type, COUNT(*) as count, SUM(value) as total_value, SUM(pnl) as total_pnl
        FROM positions 
        WHERE source = 'autotrader'
        GROUP BY type
    """)
    
    db_stocks_count = 0
    db_stocks_value = 0
    db_stocks_pnl = 0
    db_crypto_count = 0  
    db_crypto_value = 0
    db_crypto_pnl = 0
    
    for pos in positions:
        if pos['type'] == 'stock':
            db_stocks_count = pos['count']
            db_stocks_value = pos['total_value'] or 0
            db_stocks_pnl = pos['total_pnl'] or 0
        elif pos['type'] == 'crypto':
            db_crypto_count = pos['count']
            db_crypto_value = pos['total_value'] or 0
            db_crypto_pnl = pos['total_pnl'] or 0
    
    print(f"   Stocks: {db_stocks_count} positions, Value=${db_stocks_value:,.0f}, P&L=${db_stocks_pnl:,.2f}")
    print(f"   Crypto: {db_crypto_count} positions, Value=${db_crypto_value:,.0f}, P&L=${db_crypto_pnl:,.2f}")
    
    # 3. Get portfolio_config from database  
    print("\n[3] PORTFOLIO CONFIG IN DATABASE:")
    config = db_manager.execute_query("""
        SELECT type, initial_capital, current_capital, available_cash, invested_amount, total_pnl
        FROM portfolio_config
        ORDER BY type
    """)
    
    config_data = {}
    for c in config:
        config_data[c['type']] = c
        print(f"   {c['type'].upper()}: Initial=${c['initial_capital']:,.0f}, Current=${c['current_capital']:,.0f}, Cash=${c['available_cash']:,.0f}, Invested=${c['invested_amount']:,.0f}, P&L=${c['total_pnl']:,.2f}")
    
    # 4. Calculate discrepancies
    print("\n[4] DISCREPANCY ANALYSIS:")
    print("-" * 50)
    
    # Stocks discrepancies
    stocks_invested_diff = pm_stocks_invested - db_stocks_value
    stocks_liquid_diff = pm_stocks_liquid - config_data.get('stocks', {}).get('available_cash', 0)
    stocks_pnl_diff = pm_stocks_pnl - db_stocks_pnl
    
    print(f"STOCKS DISCREPANCIES:")
    print(f"   Invested Capital: PM=${pm_stocks_invested:,.0f} vs DB_Positions=${db_stocks_value:,.0f} (Diff: ${stocks_invested_diff:,.0f})")
    print(f"   Liquid Capital: PM=${pm_stocks_liquid:,.0f} vs DB_Config=${config_data.get('stocks', {}).get('available_cash', 0):,.0f} (Diff: ${stocks_liquid_diff:,.0f})")  
    print(f"   P&L: PM=${pm_stocks_pnl:,.2f} vs DB=${db_stocks_pnl:,.2f} (Diff: ${stocks_pnl_diff:,.2f})")
    
    # Crypto discrepancies
    crypto_invested_diff = pm_crypto_invested - db_crypto_value
    crypto_liquid_diff = pm_crypto_liquid - config_data.get('crypto', {}).get('available_cash', 0)
    crypto_pnl_diff = pm_crypto_pnl - db_crypto_pnl
    
    print(f"\nCRYPTO DISCREPANCIES:")
    print(f"   Invested Capital: PM=${pm_crypto_invested:,.0f} vs DB_Positions=${db_crypto_value:,.0f} (Diff: ${crypto_invested_diff:,.0f})")
    print(f"   Liquid Capital: PM=${pm_crypto_liquid:,.0f} vs DB_Config=${config_data.get('crypto', {}).get('available_cash', 0):,.0f} (Diff: ${crypto_liquid_diff:,.0f})")
    print(f"   P&L: PM=${pm_crypto_pnl:,.2f} vs DB=${db_crypto_pnl:,.2f} (Diff: ${crypto_pnl_diff:,.2f})")
    
    # 5. Check transactions count
    print("\n[5] TRANSACTION ANALYSIS:")
    recent_transactions = db_manager.execute_query("""
        SELECT portfolio_type, action, COUNT(*) as count, SUM(total_amount) as volume
        FROM portfolio_transactions 
        WHERE timestamp >= datetime('now', '-7 days')
        GROUP BY portfolio_type, action
        ORDER BY portfolio_type, action
    """)
    
    print("   Recent transactions (last 7 days):")
    for txn in recent_transactions:
        print(f"     {txn['portfolio_type'].upper()} {txn['action'].upper()}: {txn['count']} trades, ${txn['volume']:,.0f} volume")
    
    # 6. Summary of issues
    print("\n[6] SUMMARY OF ISSUES:")
    print("=" * 50)
    
    issues_found = []
    
    if abs(stocks_invested_diff) > 1:
        issues_found.append(f"STOCKS: Invested capital mismatch (${stocks_invested_diff:,.0f})")
    if abs(stocks_liquid_diff) > 1:
        issues_found.append(f"STOCKS: Liquid capital mismatch (${stocks_liquid_diff:,.0f})")
    if abs(crypto_invested_diff) > 1:
        issues_found.append(f"CRYPTO: Invested capital mismatch (${crypto_invested_diff:,.0f})")
    if abs(crypto_liquid_diff) > 1:
        issues_found.append(f"CRYPTO: Liquid capital mismatch (${crypto_liquid_diff:,.0f})")
    
    if issues_found:
        print("CRITICAL ISSUES FOUND:")
        for issue in issues_found:
            print(f"   - {issue}")
        print(f"\nRECOMMENDATION: Run auto_sync_portfolio() to fix these discrepancies")
    else:
        print("NO CRITICAL DISCREPANCIES FOUND")
        print("Portfolio Manager and database are in sync")

if __name__ == "__main__":
    try:
        diagnose_discrepancies()
    except Exception as e:
        print(f"Error during diagnosis: {e}")
        import traceback
        traceback.print_exc()