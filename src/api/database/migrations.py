"""
Database migration scripts for portfolio management updates
"""

import logging
from .database import db_manager

logger = logging.getLogger(__name__)

def run_portfolio_migrations():
    """Run all portfolio-related database migrations"""
    try:
        logger.info("Starting portfolio database migrations...")
        
        # Migration 1: Create portfolio_state table
        create_portfolio_state_table()
        
        # Migration 2: Add position_side column to positions table
        add_position_side_column()
        
        # Migration 3: Add asset_type column to positions table (if not exists)
        add_asset_type_column()
        
        # Migration 4: Update autotrader_transactions constraint to allow 'short'
        update_autotrader_transactions_constraint()
        
        # Migration 5: Create portfolio tracking tables
        create_portfolio_tracking_tables()
        
        logger.info("Portfolio migrations completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error running portfolio migrations: {e}")
        return False

def create_portfolio_state_table():
    """Create portfolio_state table for capital tracking"""
    try:
        db_manager.execute_update("""
            CREATE TABLE IF NOT EXISTS portfolio_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                liquid_capital_stocks REAL DEFAULT 10000.0,
                liquid_capital_crypto REAL DEFAULT 50000.0,
                invested_capital_stocks REAL DEFAULT 0.0,
                invested_capital_crypto REAL DEFAULT 0.0,
                total_pnl_stocks REAL DEFAULT 0.0,
                total_pnl_crypto REAL DEFAULT 0.0,
                total_positions_stocks INTEGER DEFAULT 0,
                total_positions_crypto INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("Created portfolio_state table")
        
    except Exception as e:
        logger.error(f"Error creating portfolio_state table: {e}")
        raise

def add_position_side_column():
    """Add position_side column to positions table"""
    try:
        # Check if column exists
        columns = db_manager.execute_query("PRAGMA table_info(positions)")
        column_names = [col['name'] for col in columns]
        
        if 'position_side' not in column_names:
            db_manager.execute_update("""
                ALTER TABLE positions 
                ADD COLUMN position_side TEXT DEFAULT 'LONG'
            """)
            logger.info("Added position_side column to positions table")
        else:
            logger.info("position_side column already exists")
            
    except Exception as e:
        logger.error(f"Error adding position_side column: {e}")
        raise

def add_asset_type_column():
    """Add asset_type column to positions table (legacy compatibility)"""
    try:
        # Check if column exists
        columns = db_manager.execute_query("PRAGMA table_info(positions)")
        column_names = [col['name'] for col in columns]
        
        if 'asset_type' not in column_names:
            db_manager.execute_update("""
                ALTER TABLE positions 
                ADD COLUMN asset_type TEXT DEFAULT 'stock'
            """)
            
            # Update asset_type based on existing type column
            db_manager.execute_update("""
                UPDATE positions 
                SET asset_type = type 
                WHERE asset_type IS NULL OR asset_type = 'stock'
            """)
            
            logger.info("Added asset_type column to positions table")
        else:
            logger.info("asset_type column already exists")
            
    except Exception as e:
        logger.error(f"Error adding asset_type column: {e}")
        raise

def reset_portfolio_state():
    """Reset portfolio to initial state - USE WITH CAUTION"""
    try:
        logger.warning("Resetting portfolio state - this will clear all positions and reset capital!")
        
        # Clear all autotrader positions
        db_manager.execute_update("DELETE FROM positions WHERE source = 'autotrader'")
        
        # Clear portfolio state history (optional)
        # db_manager.execute_update("DELETE FROM portfolio_state")
        
        # Insert fresh initial state
        from datetime import datetime
        db_manager.execute_insert("""
            INSERT INTO portfolio_state (
                date, liquid_capital_stocks, liquid_capital_crypto,
                invested_capital_stocks, invested_capital_crypto,
                total_pnl_stocks, total_pnl_crypto,
                total_positions_stocks, total_positions_crypto
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            10000.0,  # $10k stocks
            50000.0,  # $50k crypto
            0.0, 0.0, 0.0, 0.0, 0, 0
        ))
        
        logger.info("Portfolio state reset successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error resetting portfolio state: {e}")
        return False

def migrate_existing_positions():
    """Migrate existing positions to new schema"""
    try:
        # Set default position_side for existing positions
        db_manager.execute_update("""
            UPDATE positions 
            SET position_side = 'LONG' 
            WHERE position_side IS NULL
        """)
        
        # Set asset_type from type column if needed
        db_manager.execute_update("""
            UPDATE positions 
            SET asset_type = type 
            WHERE asset_type IS NULL OR asset_type = ''
        """)
        
        logger.info("Migrated existing positions to new schema")
        return True
        
    except Exception as e:
        logger.error(f"Error migrating existing positions: {e}")
        return False

def update_autotrader_transactions_constraint():
    """Update autotrader_transactions table to allow 'short' action"""
    try:
        # SQLite doesn't support ALTER TABLE DROP CONSTRAINT, so we need to recreate the table
        # First, check if we need to update
        columns = db_manager.execute_query("PRAGMA table_info(autotrader_transactions)")
        
        # Get current table data
        existing_data = db_manager.execute_query("SELECT * FROM autotrader_transactions")
        
        # Drop and recreate table with updated constraint
        db_manager.execute_update("DROP TABLE IF EXISTS autotrader_transactions_old")
        db_manager.execute_update("ALTER TABLE autotrader_transactions RENAME TO autotrader_transactions_old")
        
        # Create new table with updated constraint
        db_manager.execute_update("""
            CREATE TABLE autotrader_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL CHECK (action IN ('buy', 'sell', 'short')),
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason TEXT
            )
        """)
        
        # Migrate existing data
        for row in existing_data:
            db_manager.execute_insert(
                """INSERT INTO autotrader_transactions 
                   (symbol, action, quantity, price, timestamp, reason)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (row['symbol'], row['action'], row['quantity'], row['price'], 
                 row['timestamp'], row['reason'])
            )
        
        # Drop old table
        db_manager.execute_update("DROP TABLE autotrader_transactions_old")
        
        logger.info("Updated autotrader_transactions constraint to allow 'short' action")
        return True
        
    except Exception as e:
        logger.error(f"Error updating autotrader_transactions constraint: {e}")
        return False

def create_portfolio_tracking_tables():
    """Create portfolio tracking tables (config and transactions)"""
    try:
        # Create portfolio configuration table
        db_manager.execute_update("""
            CREATE TABLE IF NOT EXISTS portfolio_config (
                id INTEGER PRIMARY KEY,
                type TEXT NOT NULL, -- 'stocks' or 'crypto'
                initial_capital REAL NOT NULL,
                current_capital REAL NOT NULL,
                available_cash REAL NOT NULL,
                invested_amount REAL NOT NULL,
                total_pnl REAL NOT NULL DEFAULT 0,
                win_rate REAL NOT NULL DEFAULT 0,
                total_trades INTEGER NOT NULL DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create portfolio transactions table
        db_manager.execute_update("""
            CREATE TABLE IF NOT EXISTS portfolio_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_type TEXT NOT NULL, -- 'stocks' or 'crypto'
                symbol TEXT NOT NULL,
                action TEXT NOT NULL, -- 'buy' or 'sell'
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                total_amount REAL NOT NULL,
                fees REAL DEFAULT 0,
                buy_reason TEXT,
                sell_reason TEXT,
                score REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'autotrader' -- 'autotrader' or 'manual'
            )
        """)
        
        # Initialize portfolio config if empty
        existing_config = db_manager.execute_query("SELECT COUNT(*) as count FROM portfolio_config")
        if existing_config[0]['count'] == 0:
            # Insert initial portfolio configuration
            db_manager.execute_insert("""
                INSERT INTO portfolio_config (type, initial_capital, current_capital, available_cash, invested_amount)
                VALUES ('stocks', 10000.0, 10000.0, 10000.0, 0.0)
            """)
            db_manager.execute_insert("""
                INSERT INTO portfolio_config (type, initial_capital, current_capital, available_cash, invested_amount)
                VALUES ('crypto', 50000.0, 50000.0, 50000.0, 0.0)
            """)
            logger.info("Initialized portfolio configuration with default values")
        
        logger.info("Created portfolio tracking tables")
        return True
        
    except Exception as e:
        logger.error(f"Error creating portfolio tracking tables: {e}")
        return False