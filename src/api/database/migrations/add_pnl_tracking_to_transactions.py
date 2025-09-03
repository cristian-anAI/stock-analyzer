"""
Database migration: Add P&L tracking fields to autotrader_transactions table
"""

import sqlite3
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.api.database.database import db_manager

def add_pnl_tracking_columns():
    """Add P&L tracking columns to autotrader_transactions table"""
    print("Adding P&L tracking columns to autotrader_transactions table...")
    
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(autotrader_transactions)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        new_columns = [
            ("realized_pnl", "REAL"),
            ("entry_price", "REAL"), 
            ("exit_price", "REAL"),
            ("position_id", "TEXT"),
            ("hold_duration_hours", "REAL")
        ]
        
        for column_name, column_type in new_columns:
            if column_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE autotrader_transactions ADD COLUMN {column_name} {column_type}")
                    print(f"✓ Added column: {column_name} ({column_type})")
                except sqlite3.Error as e:
                    print(f"✗ Error adding column {column_name}: {e}")
            else:
                print(f"- Column {column_name} already exists")
        
        conn.commit()
        print("✓ Migration completed successfully")

def verify_migration():
    """Verify the migration was successful"""
    print("\nVerifying migration...")
    
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(autotrader_transactions)")
        columns = cursor.fetchall()
        
        print("Updated autotrader_transactions schema:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")

if __name__ == "__main__":
    print("AUTOTRADER_TRANSACTIONS P&L TRACKING MIGRATION")
    print("=" * 60)
    
    add_pnl_tracking_columns()
    verify_migration()
    
    print("\n✓ Ready to implement P&L calculation logic")