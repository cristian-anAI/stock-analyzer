#!/usr/bin/env python3
"""
Production Database Cleaner
WARNING: This will clean the production database removing all trading data
Only run this when preparing for production deployment
"""

import os
import shutil
import sys
from pathlib import Path

class ProductionDBCleaner:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        
    def clean_production_database(self):
        """Create clean production database"""
        print("Creating clean production database...")
        
        import sys
        sys.path.append(str(self.project_root))
        
        from src.api.database.database import db_manager
        
        # Backup existing database
        db_path = self.project_root / "trading.db"
        if db_path.exists():
            backup_path = self.project_root / f"trading.db.backup_production_clean"
            shutil.copy(db_path, backup_path)
            print(f"   OK Database backed up to {backup_path}")
        
        # Create clean database with schema only
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Clear all transaction data
            print("   Clearing transaction data...")
            try:
                cursor.execute("DELETE FROM autotrader_transactions")
            except:
                print("   autotrader_transactions table not found, skipping...")
            try:
                cursor.execute("DELETE FROM portfolio_transactions")
            except:
                print("   portfolio_transactions table not found, skipping...")
            try:
                cursor.execute("DELETE FROM positions WHERE source = 'autotrader'")
            except:
                print("   positions table not found, skipping...")
            
            # Reset portfolio to initial state
            print("   Resetting portfolio to initial state...")
            try:
                cursor.execute("DELETE FROM portfolio_snapshots")
            except:
                print("   portfolio_snapshots table not found, skipping...")
            
            # Keep stocks and cryptos with scores for trading
            print("   Preserving stock/crypto scores...")
            
            # Reset any test symbols scores
            cursor.execute("""
                UPDATE stocks SET score = 5.0 
                WHERE symbol IN ('TEST', 'SAMPLE', 'MOCK')
            """)
            
            conn.commit()
            print("   OK Production database ready")

if __name__ == "__main__":
    print("WARNING: This will clean your trading database!")
    print("This will remove all autotrader positions and transactions.")
    print("Only run this when preparing for production deployment.")
    response = input("Are you sure you want to continue? (yes/no): ")
    
    if response.lower() == 'yes':
        cleaner = ProductionDBCleaner()
        cleaner.clean_production_database()
        print("\nProduction database cleaned successfully!")
    else:
        print("Operation cancelled.")