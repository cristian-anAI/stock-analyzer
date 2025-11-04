"""
Database configuration and initialization
Supports both SQLite (legacy) and PostgreSQL (production)
Automatically detects which database to use based on DATABASE_URL environment variable
"""

import sqlite3
import os
from typing import Dict, Any, List, Optional
import logging
from contextlib import contextmanager
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
env_file = '.env.local' if os.path.exists('.env.local') else '.env.prod'
if os.path.exists(env_file):
    load_dotenv(env_file)
    logger.info(f"Loaded environment from {env_file}")

# Check if PostgreSQL is configured
DATABASE_URL = os.getenv("DATABASE_URL")
USE_POSTGRES = DATABASE_URL is not None and DATABASE_URL.startswith('postgresql')

if USE_POSTGRES:
    logger.info("Using PostgreSQL database")
    # Import PostgreSQL implementation
    try:
        from .database_postgres import DatabaseManager as PostgresManager, init_db as init_postgres_db
        USE_POSTGRES = True
    except ImportError as e:
        logger.warning(f"PostgreSQL dependencies not available: {e}")
        logger.warning("Falling back to SQLite")
        USE_POSTGRES = False

# SQLite fallback
DATABASE_PATH = os.getenv("SQLITE_DB_PATH", "trading.db")

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

    if USE_POSTGRES:
        # Use PostgreSQL initialization
        logger.info("Initializing PostgreSQL database")
        init_postgres_db()
        return

    # SQLite initialization (legacy)
    logger.info("Initializing SQLite database")
    db = DatabaseManager()

    # Run migrations first
    from .migrations import run_portfolio_migrations
    run_portfolio_migrations()

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

        # Add new columns for advanced tracking if they don't exist
        cursor.execute("PRAGMA table_info(positions)")
        existing_columns = [column[1] for column in cursor.fetchall()]

        new_columns = [
            ("last_analysis_date", "TEXT"),
            ("last_recommendation", "TEXT"),
            ("stop_loss_updated", "REAL"),
            ("take_profit_updated", "REAL"),
            ("alerts_triggered", "TEXT"),
            ("analysis_history", "TEXT")
        ]

        for column_name, column_type in new_columns:
            if column_name not in existing_columns:
                cursor.execute(f"ALTER TABLE positions ADD COLUMN {column_name} {column_type}")
                logger.info(f"Added column {column_name} to positions table")

        # Autotrader transactions log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS autotrader_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL CHECK (action IN ('buy', 'sell', 'short')),
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason TEXT
            )
        """)

        conn.commit()
        logger.info("Database tables created successfully")

# Global database instance
if USE_POSTGRES:
    db_manager = PostgresManager()
    logger.info("Using PostgreSQL DatabaseManager")
else:
    db_manager = DatabaseManager()
    logger.info("Using SQLite DatabaseManager")