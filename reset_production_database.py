#!/usr/bin/env python3
"""
Production Database Reset Script
Resets all positions (manual and autotrader) and portfolio state for clean deployment
"""

import sqlite3
import os
import sys
from datetime import datetime

def reset_database(db_path: str = "src/trading.db"):
    """Reset all positions and trading data for fresh production start"""
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🗑️  RESETTING PRODUCTION DATABASE...")
        print("=" * 50)
        
        # 1. Clear all positions (manual + autotrader)
        cursor.execute("SELECT COUNT(*) FROM positions")
        position_count = cursor.fetchone()[0]
        cursor.execute("DELETE FROM positions")
        print(f"✅ Deleted {position_count} positions")
        
        # 2. Clear autotrader transactions
        cursor.execute("SELECT COUNT(*) FROM autotrader_transactions")
        transaction_count = cursor.fetchone()[0]
        cursor.execute("DELETE FROM autotrader_transactions")
        print(f"✅ Deleted {transaction_count} autotrader transactions")
        
        # 3. Reset portfolio state if exists
        try:
            cursor.execute("SELECT COUNT(*) FROM portfolio_state")
            portfolio_count = cursor.fetchone()[0]
            cursor.execute("DELETE FROM portfolio_state")
            print(f"✅ Deleted {portfolio_count} portfolio state records")
        except sqlite3.OperationalError:
            print("ℹ️  Portfolio state table not found (normal)")
        
        # 4. Clear stocks data (will be repopulated)
        cursor.execute("SELECT COUNT(*) FROM stocks")
        stocks_count = cursor.fetchone()[0]
        cursor.execute("DELETE FROM stocks")
        print(f"✅ Deleted {stocks_count} stock records")
        
        # 5. Clear cryptos data (will be repopulated)
        cursor.execute("SELECT COUNT(*) FROM cryptos")
        cryptos_count = cursor.fetchone()[0]
        cursor.execute("DELETE FROM cryptos")
        print(f"✅ Deleted {cryptos_count} crypto records")
        
        # 6. Reset auto-increment counters
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('positions', 'autotrader_transactions', 'portfolio_state')")
        print("✅ Reset auto-increment counters")
        
        # Commit all changes
        conn.commit()
        conn.close()
        
        print("=" * 50)
        print("🎯 DATABASE RESET COMPLETE!")
        print("🚀 Ready for fresh production deployment")
        print(f"📅 Reset timestamp: {datetime.now().isoformat()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error resetting database: {str(e)}")
        return False

def create_fresh_database():
    """Create a completely fresh database for production"""
    
    # Import the database setup
    sys.path.append('src/api')
    from database.database import db_manager
    
    print("🆕 Creating fresh production database...")
    
    # This will create all tables
    db_manager.initialize_database()
    print("✅ Fresh database created with all tables")
    
    return True

if __name__ == "__main__":
    print("🔄 PRODUCTION DATABASE RESET")
    print("This will delete ALL positions, transactions, and market data")
    
    # Check if running in production mode
    confirmation = input("⚠️  Type 'RESET_PRODUCTION' to confirm: ")
    
    if confirmation != "RESET_PRODUCTION":
        print("❌ Operation cancelled")
        sys.exit(1)
    
    # Reset existing database or create fresh one
    db_path = "src/trading.db"
    
    if os.path.exists(db_path):
        success = reset_database(db_path)
    else:
        print("📂 No existing database found, creating fresh one...")
        success = create_fresh_database()
    
    if success:
        print("\n🎉 Production database is ready!")
        print("💡 The autotrader will start with:")
        print("   - $10,000 stock capital")
        print("   - $50,000 crypto capital") 
        print("   - No existing positions")
        print("   - Clean transaction history")
    else:
        print("\n❌ Database reset failed!")
        sys.exit(1)