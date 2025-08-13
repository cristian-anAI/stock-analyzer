"""
Database configuration and initialization
"""

import sqlite3
import os
from typing import Dict, Any, List, Optional
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DATABASE_PATH = "trading.db"

class DatabaseManager:
    """Database manager for Stock Analyzer API"""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        
    @contextmanager
    def get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute SELECT query and return results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE query and return affected rows"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
    
    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT query and return last row id"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid

def init_db():
    """Initialize database with required tables"""
    db = DatabaseManager()
    
    # Create tables
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Stocks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
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
        
        # Cryptos table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cryptos (
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
        
        # Positions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
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
        
        # Autotrader transactions log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS autotrader_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL CHECK (action IN ('buy', 'sell')),
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason TEXT
            )
        """)
        
        conn.commit()
        logger.info("Database tables created successfully")

# Global database instance
db_manager = DatabaseManager()