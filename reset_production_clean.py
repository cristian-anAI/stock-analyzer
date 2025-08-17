#!/usr/bin/env python3
"""
PRODUCTION DATABASE CLEAN RESET
Complete reset of portfolio data for fresh start

This script:
1. Removes ALL positions (autotrader + manual)
2. Resets portfolio_config to initial values
3. Clears transaction history 
4. Resets portfolio_state
5. Preserves stocks/cryptos data tables
"""

import sqlite3
import os
from datetime import datetime

def reset_production_database(db_path='trading.db'):
    """Complete reset of production database"""
    
    if not os.path.exists(db_path):
        print(f"❌ Database {db_path} not found!")
        return False
    
    print("🧹 PRODUCTION DATABASE RESET")
    print("=" * 50)
    print(f"Database: {db_path}")
    print(f"Timestamp: {datetime.now()}")
    print()
    
    # Safety confirmation
    confirm = input("⚠️  This will DELETE ALL portfolio data! Type 'RESET_PRODUCTION' to confirm: ")
    if confirm != "RESET_PRODUCTION":
        print("❌ Reset cancelled. No changes made.")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Count current data before deletion
        cursor.execute("SELECT COUNT(*) FROM positions")
        positions_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM autotrader_transactions")
        transactions_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM portfolio_transactions")
        portfolio_transactions_count = cursor.fetchone()[0]
        
        print(f"📊 Current Data:")
        print(f"   Positions: {positions_count}")
        print(f"   Autotrader Transactions: {transactions_count}")
        print(f"   Portfolio Transactions: {portfolio_transactions_count}")
        print()
        
        # 2. Clear all positions
        print("🗑️  Clearing positions...")
        cursor.execute("DELETE FROM positions")
        print(f"   ✅ Deleted {positions_count} positions")
        
        # 3. Clear transaction history
        print("🗑️  Clearing transaction history...")
        cursor.execute("DELETE FROM autotrader_transactions")
        print(f"   ✅ Deleted {transactions_count} autotrader transactions")
        
        cursor.execute("DELETE FROM portfolio_transactions")
        print(f"   ✅ Deleted {portfolio_transactions_count} portfolio transactions")
        
        # 4. Reset portfolio_config to correct initial values
        print("🔄 Resetting portfolio configuration...")
        cursor.execute("DELETE FROM portfolio_config")
        
        # Insert correct initial configuration
        cursor.execute("""
            INSERT INTO portfolio_config (type, initial_capital, current_capital, available_cash, invested_amount, total_pnl, win_rate, total_trades)
            VALUES ('stocks', 10000.0, 10000.0, 10000.0, 0.0, 0.0, 0.0, 0)
        """)
        
        cursor.execute("""
            INSERT INTO portfolio_config (type, initial_capital, current_capital, available_cash, invested_amount, total_pnl, win_rate, total_trades)
            VALUES ('crypto', 50000.0, 50000.0, 50000.0, 0.0, 0.0, 0.0, 0)
        """)
        print("   ✅ Reset portfolio config: $10k stocks, $50k crypto")
        
        # 5. Reset portfolio_state
        print("🔄 Resetting portfolio state...")
        cursor.execute("DELETE FROM portfolio_state")
        
        cursor.execute("""
            INSERT INTO portfolio_state (
                date, liquid_capital_stocks, liquid_capital_crypto,
                invested_capital_stocks, invested_capital_crypto,
                total_pnl_stocks, total_pnl_crypto,
                total_positions_stocks, total_positions_crypto
            ) VALUES (?, 10000.0, 50000.0, 0.0, 0.0, 0.0, 0.0, 0, 0)
        """, (datetime.now().isoformat(),))
        print("   ✅ Reset portfolio state")
        
        # 6. Clear portfolio_positions if exists
        try:
            cursor.execute("DELETE FROM portfolio_positions")
            print("   ✅ Cleared portfolio positions")
        except:
            pass  # Table might not exist
        
        # 7. Clear portfolio_snapshots if exists
        try:
            cursor.execute("DELETE FROM portfolio_snapshots")
            print("   ✅ Cleared portfolio snapshots")
        except:
            pass  # Table might not exist
        
        # Commit all changes
        conn.commit()
        
        # 8. Verify reset
        print("\n📋 Verification:")
        cursor.execute("SELECT COUNT(*) FROM positions")
        print(f"   Positions: {cursor.fetchone()[0]} (should be 0)")
        
        cursor.execute("SELECT type, initial_capital, current_capital FROM portfolio_config")
        configs = cursor.fetchall()
        for config in configs:
            print(f"   {config[0]}: Initial=${config[1]:.2f}, Current=${config[2]:.2f}")
        
        conn.close()
        
        print("\n✅ DATABASE RESET COMPLETE!")
        print("💡 You should now restart the application to reload the portfolio manager")
        print()
        print("Next steps:")
        print("1. Restart Docker container")
        print("2. Verify /api/v1/portfolio/summary shows clean state")
        print("3. Check autotrader is working with fresh data")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during reset: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def main():
    """Main function with database path handling"""
    import sys
    
    # Default to trading.db, allow override via command line
    db_path = 'trading.db'
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    success = reset_production_database(db_path)
    
    if success:
        print("🎉 Production database reset successfully!")
        exit(0)
    else:
        print("💥 Production database reset failed!")
        exit(1)

if __name__ == "__main__":
    main()