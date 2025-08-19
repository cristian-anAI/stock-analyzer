#!/usr/bin/env python3
"""
Script to fix database schema issues
"""

import sqlite3
import os
from pathlib import Path

def fix_database():
    """Fix database schema by adding missing columns and recreating tables if needed"""
    
    db_path = "trading.db"
    backup_path = "trading.db.backup"
    
    print("Fixing database schema...")
    
    # Create backup
    if os.path.exists(db_path):
        print(f"Creating backup: {backup_path}")
        import shutil
        shutil.copy2(db_path, backup_path)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if tables exist and their structure
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Found tables: {[t[0] for t in tables]}")
        
        # Drop and recreate all tables to ensure correct schema
        print("Recreating tables with correct schema...")
        
        # Drop existing tables
        cursor.execute("DROP TABLE IF EXISTS positions")
        cursor.execute("DROP TABLE IF EXISTS autotrader_transactions")
        cursor.execute("DROP TABLE IF EXISTS stocks")
        cursor.execute("DROP TABLE IF EXISTS cryptos")
        
        # Create stocks table
        cursor.execute("""
            CREATE TABLE stocks (
                id TEXT PRIMARY KEY,
                symbol TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                current_price REAL,
                score INTEGER,
                change_amount REAL,
                change_percent REAL,
                volume INTEGER,
                market_cap REAL,
                sector TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Created stocks table")
        
        # Create cryptos table
        cursor.execute("""
            CREATE TABLE cryptos (
                id TEXT PRIMARY KEY,
                symbol TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                current_price REAL,
                score INTEGER,
                change_amount REAL,
                change_percent REAL,
                volume REAL,
                market_cap REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Created cryptos table")
        
        # Create positions table with ALL required columns
        cursor.execute("""
            CREATE TABLE positions (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('stock', 'crypto')),
                quantity REAL NOT NULL,
                entry_price REAL NOT NULL,
                current_price REAL,
                value REAL,
                pnl REAL,
                pnl_percent REAL,
                source TEXT NOT NULL CHECK (source IN ('autotrader', 'manual')),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Created positions table")
        
        # Create autotrader transactions log
        cursor.execute("""
            CREATE TABLE autotrader_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL CHECK (action IN ('buy', 'sell')),
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason TEXT
            )
        """)
        print("Created autotrader_transactions table")
        
        conn.commit()
        conn.close()
        
        print("Database schema fixed successfully!")
        print("Tables created:")
        print("   - stocks (with all required columns)")
        print("   - cryptos (with all required columns)")
        print("   - positions (with type, source, name columns)")
        print("   - autotrader_transactions (for trading history)")
        
        return True
        
    except Exception as e:
        print(f"Error fixing database: {str(e)}")
        # Restore backup if something went wrong
        if os.path.exists(backup_path):
            print("Restoring backup...")
            import shutil
            shutil.copy2(backup_path, db_path)
        return False

if __name__ == "__main__":
    fix_database()