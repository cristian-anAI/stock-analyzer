#!/usr/bin/env python3
"""
Sync Capital to $100k Total: $70k stocks + $30k crypto
Migrates and synchronizes all portfolio tracking systems
"""

import sys
import os
import sqlite3
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from api.database.database import db_manager
from api.services.portfolio_manager import portfolio_manager

def sync_capital_distribution():
    """Synchronize capital to new $100k distribution"""
    
    print("=" * 60)
    print("    SYNCING CAPITAL TO $100K TOTAL")
    print("    Stocks: $70,000 (70%) | Crypto: $30,000 (30%)")
    print("=" * 60)
    
    # Step 1: Update portfolio_state table
    print("\n[1/5] Updating portfolio_state table...")
    try:
        # Clear old portfolio state
        db_manager.execute_update("DELETE FROM portfolio_state")
        
        # Insert new initial state
        db_manager.execute_insert("""
            INSERT INTO portfolio_state (
                date, liquid_capital_stocks, liquid_capital_crypto,
                invested_capital_stocks, invested_capital_crypto,
                total_pnl_stocks, total_pnl_crypto,
                total_positions_stocks, total_positions_crypto
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            70000.0,  # $70k stocks
            30000.0,  # $30k crypto  
            0.0, 0.0, 0.0, 0.0, 0, 0
        ))
        print("    [OK] portfolio_state updated")
        
    except Exception as e:
        print(f"     Error updating portfolio_state: {e}")
        return False
    
    # Step 2: Update/create portfolio_config table  
    print("\n[2/5] Updating portfolio_config table...")
    try:
        # Clear existing config
        db_manager.execute_update("DELETE FROM portfolio_config")
        
        # Insert new configuration
        db_manager.execute_insert("""
            INSERT INTO portfolio_config (type, initial_capital, current_capital, available_cash, invested_amount)
            VALUES ('stocks', 70000.0, 70000.0, 70000.0, 0.0)
        """)
        db_manager.execute_insert("""
            INSERT INTO portfolio_config (type, initial_capital, current_capital, available_cash, invested_amount)  
            VALUES ('crypto', 30000.0, 30000.0, 30000.0, 0.0)
        """)
        print("     portfolio_config updated")
        
    except Exception as e:
        print(f"     Error updating portfolio_config: {e}")
        return False
    
    # Step 3: Reset PortfolioManager instance
    print("\n[3/5] Resetting PortfolioManager instance...")
    try:
        portfolio_manager.reset_portfolio()
        print("     PortfolioManager reset with new values")
        
    except Exception as e:
        print(f"     Error resetting PortfolioManager: {e}")
        return False
    
    # Step 4: Archive existing autotrader positions (they're from old capital)
    print("\n[4/5] Archiving existing autotrader positions...")
    try:
        # Get count of existing autotrader positions
        result = db_manager.execute_query("""
            SELECT COUNT(*) as count FROM positions WHERE source = 'autotrader'
        """)
        existing_count = result[0]['count'] if result else 0
        
        if existing_count > 0:
            print(f"    Found {existing_count} existing autotrader positions")
            
            # Update notes to indicate they're from old capital system
            db_manager.execute_update("""
                UPDATE positions 
                SET notes = COALESCE(notes, '') || ' [ARCHIVED: Pre-$100k capital sync]'
                WHERE source = 'autotrader' 
                AND (notes IS NULL OR notes NOT LIKE '%ARCHIVED%')
            """)
            
            print(f"     Archived {existing_count} positions (marked with ARCHIVED tag)")
        else:
            print("     No existing autotrader positions to archive")
            
    except Exception as e:
        print(f"     Error archiving positions: {e}")
        return False
    
    # Step 5: Verification
    print("\n[5/5] Verification...")
    try:
        # Check portfolio_state
        state_result = db_manager.execute_query("""
            SELECT liquid_capital_stocks, liquid_capital_crypto 
            FROM portfolio_state ORDER BY created_at DESC LIMIT 1
        """)
        
        # Check portfolio_config  
        config_result = db_manager.execute_query("""
            SELECT type, initial_capital FROM portfolio_config ORDER BY type
        """)
        
        print("     Current State:")
        if state_result:
            state = state_result[0]
            print(f"       portfolio_state: Stocks=${state['liquid_capital_stocks']:,.0f}, Crypto=${state['liquid_capital_crypto']:,.0f}")
        
        if config_result:
            for config in config_result:
                print(f"       portfolio_config {config['type']}: ${config['initial_capital']:,.0f}")
        
        # Check PortfolioManager values
        summary = portfolio_manager.get_portfolio_summary()
        print(f"       PortfolioManager: Stocks=${summary['stocks']['liquid_capital']:,.0f}, Crypto=${summary['crypto']['liquid_capital']:,.0f}")
        
        total_liquid = summary['stocks']['liquid_capital'] + summary['crypto']['liquid_capital']
        print(f"        Total Capital: ${total_liquid:,.0f}")
        
        if total_liquid == 100000.0:
            print("\n SUCCESS: All systems synchronized to $100k total capital!")
            return True
        else:
            print(f"\n ERROR: Total capital is ${total_liquid:,.0f}, expected $100,000")
            return False
            
    except Exception as e:
        print(f"     Error in verification: {e}")
        return False

def show_portfolio_summary():
    """Show current portfolio summary after sync"""
    try:
        summary = portfolio_manager.get_portfolio_summary()
        
        print("\n" + "=" * 60)
        print("         PORTFOLIO SUMMARY (POST-SYNC)")
        print("=" * 60)
        
        print(f" STOCKS PORTFOLIO:")
        print(f"   Liquid Capital: ${summary['stocks']['liquid_capital']:,.2f}")
        print(f"   Invested: ${summary['stocks']['invested_capital']:,.2f}")
        print(f"   Total P&L: ${summary['stocks']['total_pnl']:,.2f}")
        print(f"   Positions: {summary['stocks']['current_positions']}/{summary['stocks']['max_positions']}")
        
        print(f"\n CRYPTO PORTFOLIO:")
        print(f"   Liquid Capital: ${summary['crypto']['liquid_capital']:,.2f}")
        print(f"   Invested: ${summary['crypto']['invested_capital']:,.2f}")
        print(f"   Total P&L: ${summary['crypto']['total_pnl']:,.2f}")
        print(f"   Positions: {summary['crypto']['current_positions']}/{summary['crypto']['max_positions']}")
        
        print(f"\n TOTALS:")
        print(f"   Total Portfolio Value: ${summary['totals']['total_portfolio_value']:,.2f}")
        print(f"   Total Liquid: ${summary['totals']['total_liquid']:,.2f}")
        print(f"   Total Invested: ${summary['totals']['total_invested']:,.2f}")
        print(f"   Total P&L: ${summary['totals']['total_pnl']:,.2f}")
        print(f"   ROI: {summary['totals']['roi_percent']:.2f}%")
        
    except Exception as e:
        print(f"Error showing portfolio summary: {e}")

def main():
    print(" CAPITAL SYNCHRONIZATION TO $100K TOTAL")
    print("This will reset capital distribution to:")
    print("  • Stocks: $70,000 (70%)")  
    print("  • Crypto: $30,000 (30%)")
    print("  • Total: $100,000")
    print("\nExisting autotrader positions will be archived (not deleted)")
    
    confirm = input("\nProceed with capital sync? (y/N): ").lower()
    
    if confirm != 'y':
        print(" Operation cancelled")
        return
    
    # Run synchronization
    success = sync_capital_distribution()
    
    if success:
        show_portfolio_summary()
        print("\n Capital synchronization completed successfully!")
        print(" The autotrader will now use the new $100k capital distribution")
    else:
        print("\n Capital synchronization failed!")
        print("Please check the errors above and try again")

if __name__ == "__main__":
    main()