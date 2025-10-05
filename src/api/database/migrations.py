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
        
        # Migration 6: Add P&L tracking columns to autotrader_transactions
        add_pnl_tracking_columns()
        
        # Migration 7: Create MTSS scores cache table
        create_mtss_scores_table()
        
        # Migration 8: Create volatility tracking table
        create_volatility_tracking_table()
        
        # Migration 9: Create trading cooldowns table
        create_trading_cooldowns_table()
        
        # Migration 10: Create symbol blacklist table
        create_symbol_blacklist_table()

        # Migration 11: Fix volatility_tracking constraint issue
        fix_volatility_tracking_constraint()

        # Migration 12: Create decision logs table for transparency
        create_decision_logs_table()

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
                liquid_capital_stocks REAL DEFAULT 70000.0,
                liquid_capital_crypto REAL DEFAULT 30000.0,
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
            70000.0,  # $70k stocks  
            30000.0,  # $30k crypto
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

def add_pnl_tracking_columns():
    """Add P&L tracking columns to autotrader_transactions table"""
    try:
        # Check if columns already exist
        columns = db_manager.execute_query("PRAGMA table_info(autotrader_transactions)")
        existing_columns = [row['name'] for row in columns]
        
        pnl_columns = [
            ("realized_pnl", "REAL"),
            ("entry_price", "REAL"), 
            ("exit_price", "REAL"),
            ("position_id", "TEXT"),
            ("hold_duration_hours", "REAL")
        ]
        
        for col_name, col_type in pnl_columns:
            if col_name not in existing_columns:
                try:
                    db_manager.execute_update(f"ALTER TABLE autotrader_transactions ADD COLUMN {col_name} {col_type}")
                    logger.info(f"Added P&L column: {col_name}")
                except Exception as col_error:
                    logger.warning(f"Failed to add column {col_name}: {col_error}")
            else:
                logger.info(f"P&L column {col_name} already exists")
        
        logger.info("P&L tracking columns migration completed")
        return True
        
    except Exception as e:
        logger.error(f"Error adding P&L tracking columns: {e}")
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
                VALUES ('stocks', 70000.0, 70000.0, 70000.0, 0.0)
            """)
            db_manager.execute_insert("""
                INSERT INTO portfolio_config (type, initial_capital, current_capital, available_cash, invested_amount)
                VALUES ('crypto', 30000.0, 30000.0, 30000.0, 0.0)
            """)
            logger.info("Initialized portfolio configuration with default values")
        
        logger.info("Created portfolio tracking tables")
        return True
        
    except Exception as e:
        logger.error(f"Error creating portfolio tracking tables: {e}")
        return False

def create_mtss_scores_table():
    """Create MTSS scores cache table for multi-timeframe scoring"""
    try:
        db_manager.execute_update("""
            CREATE TABLE IF NOT EXISTS mtss_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL, -- '1h', '1d', '1W', '1M'
                score REAL NOT NULL,
                timeframe_scores TEXT, -- JSON of all timeframe scores
                unified_score REAL,
                trading_signal TEXT,
                confidence REAL,
                monthly_filter_passed BOOLEAN,
                data_quality_score REAL,
                breakdown TEXT, -- JSON of full analysis breakdown
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, timeframe)
            )
        """)
        
        # Create indexes for efficient queries
        db_manager.execute_update("""
            CREATE INDEX IF NOT EXISTS idx_mtss_scores_symbol 
            ON mtss_scores(symbol)
        """)
        
        db_manager.execute_update("""
            CREATE INDEX IF NOT EXISTS idx_mtss_scores_timeframe 
            ON mtss_scores(timeframe)
        """)
        
        db_manager.execute_update("""
            CREATE INDEX IF NOT EXISTS idx_mtss_scores_updated 
            ON mtss_scores(updated_at)
        """)
        
        db_manager.execute_update("""
            CREATE INDEX IF NOT EXISTS idx_mtss_scores_score 
            ON mtss_scores(score)
        """)
        
        db_manager.execute_update("""
            CREATE INDEX IF NOT EXISTS idx_mtss_scores_symbol_timeframe 
            ON mtss_scores(symbol, timeframe, updated_at)
        """)
        
        logger.info("Created MTSS scores cache table with indexes")
        return True
        
    except Exception as e:
        logger.error(f"Error creating MTSS scores table: {e}")
        return False

def create_volatility_tracking_table():
    """Create volatility tracking table for market stress monitoring"""
    try:
        # First try to add missing columns to existing table
        try:
            db_manager.execute_update("ALTER TABLE volatility_tracking ADD COLUMN date TEXT")
        except:
            pass  # Column might already exist

        try:
            db_manager.execute_update("ALTER TABLE volatility_tracking ADD COLUMN daily_volatility REAL")
        except:
            pass

        try:
            db_manager.execute_update("ALTER TABLE volatility_tracking ADD COLUMN atr_14 REAL")
        except:
            pass

        try:
            db_manager.execute_update("ALTER TABLE volatility_tracking ADD COLUMN volatility_percentile REAL")
        except:
            pass

        try:
            db_manager.execute_update("ALTER TABLE volatility_tracking ADD COLUMN is_high_volatility INTEGER DEFAULT 0")
        except:
            pass

        try:
            db_manager.execute_update("ALTER TABLE volatility_tracking ADD COLUMN price_range_percent REAL")
        except:
            pass

        try:
            db_manager.execute_update("ALTER TABLE volatility_tracking ADD COLUMN volume_volatility REAL")
        except:
            pass

        # Create table with all required columns if it doesn't exist
        db_manager.execute_update("""
            CREATE TABLE IF NOT EXISTS volatility_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT,
                volatility REAL,
                daily_volatility REAL,
                atr_14 REAL,
                volatility_percentile REAL,
                is_high_volatility INTEGER DEFAULT 0,
                price_range_percent REAL,
                volume_volatility REAL,
                timeframe TEXT NOT NULL DEFAULT '1d',
                market_stress_level TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date)
            )
        """)
        
        # Create indexes for efficient queries
        db_manager.execute_update("""
            CREATE INDEX IF NOT EXISTS idx_volatility_symbol 
            ON volatility_tracking(symbol)
        """)
        
        db_manager.execute_update("""
            CREATE INDEX IF NOT EXISTS idx_volatility_timestamp 
            ON volatility_tracking(created_at)
        """)
        
        logger.info("Created volatility_tracking table")
        return True
        
    except Exception as e:
        logger.error(f"Error creating volatility_tracking table: {e}")
        return False

def create_trading_cooldowns_table():
    """Create trading cooldowns table for position management"""
    try:
        db_manager.execute_update("""
            CREATE TABLE IF NOT EXISTS trading_cooldowns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                cooldown_until TEXT NOT NULL,
                reason TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index for efficient symbol lookups
        db_manager.execute_update("""
            CREATE INDEX IF NOT EXISTS idx_cooldowns_symbol 
            ON trading_cooldowns(symbol)
        """)
        
        db_manager.execute_update("""
            CREATE INDEX IF NOT EXISTS idx_cooldowns_until 
            ON trading_cooldowns(cooldown_until)
        """)
        
        logger.info("Created trading_cooldowns table")
        return True
        
    except Exception as e:
        logger.error(f"Error creating trading_cooldowns table: {e}")
        return False

def create_symbol_blacklist_table():
    """Create symbol blacklist table for managing problematic symbols"""
    try:
        db_manager.execute_update("""
            CREATE TABLE IF NOT EXISTS symbol_blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                reason TEXT NOT NULL,
                blacklisted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                blacklisted_until TEXT, -- NULL for permanent blacklist
                auto_added INTEGER DEFAULT 0, -- 0=false, 1=true (SQLite doesn't have BOOLEAN)
                notes TEXT
            )
        """)
        
        # Create index for efficient symbol lookups
        db_manager.execute_update("""
            CREATE INDEX IF NOT EXISTS idx_blacklist_symbol 
            ON symbol_blacklist(symbol)
        """)
        
        # Note: Skip index on blacklisted_until since it can be NULL
        # db_manager.execute_update("""
        #     CREATE INDEX IF NOT EXISTS idx_blacklist_until 
        #     ON symbol_blacklist(blacklisted_until)
        # """)
        
        # Add problematic symbols that we've identified
        problematic_symbols = [
            ("CISCO", "Delisted symbol - no price data found", 1),
            ("MATIC-USD", "Possibly delisted crypto - no price data found", 1)
        ]
        
        for symbol, reason, auto_added in problematic_symbols:
            try:
                db_manager.execute_insert("""
                    INSERT OR IGNORE INTO symbol_blacklist (symbol, reason, auto_added)
                    VALUES (?, ?, ?)
                """, (symbol, reason, auto_added))
            except:
                pass  # Ignore if already exists
        
        logger.info("Created symbol_blacklist table")
        return True

    except Exception as e:
        logger.error(f"Error creating symbol_blacklist table: {e}")
        return False

def fix_volatility_tracking_constraint():
    """Fix volatility_tracking table constraint issue - remove NOT NULL from legacy volatility column"""
    try:
        # First, check current table schema
        columns = db_manager.execute_query("PRAGMA table_info(volatility_tracking)")
        if not columns:
            logger.info("volatility_tracking table does not exist - creating from scratch")
            return create_volatility_tracking_table()

        logger.info("Fixing volatility_tracking constraint issue...")

        # Get existing data
        existing_data = db_manager.execute_query("SELECT * FROM volatility_tracking")
        logger.info(f"Found {len(existing_data)} existing volatility tracking records")

        # Drop existing table and recreate with fixed schema
        db_manager.execute_update("DROP TABLE IF EXISTS volatility_tracking_backup")
        db_manager.execute_update("ALTER TABLE volatility_tracking RENAME TO volatility_tracking_backup")

        # Create new table with correct schema (no NOT NULL constraint on volatility column)
        db_manager.execute_update("""
            CREATE TABLE volatility_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT,
                volatility REAL,  -- Removed NOT NULL constraint here
                daily_volatility REAL,
                atr_14 REAL,
                volatility_percentile REAL,
                is_high_volatility INTEGER DEFAULT 0,
                price_range_percent REAL,
                volume_volatility REAL,
                timeframe TEXT NOT NULL DEFAULT '1d',
                market_stress_level TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date)
            )
        """)

        # Migrate existing data - handle NULL volatility values
        for row in existing_data:
            try:
                db_manager.execute_insert("""
                    INSERT OR REPLACE INTO volatility_tracking
                    (symbol, date, volatility, daily_volatility, atr_14, volatility_percentile,
                     is_high_volatility, price_range_percent, volume_volatility, timeframe,
                     market_stress_level, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row.get('symbol'),
                    row.get('date'),
                    row.get('volatility'),  # Allow NULL values now
                    row.get('daily_volatility'),
                    row.get('atr_14'),
                    row.get('volatility_percentile'),
                    row.get('is_high_volatility', 0),
                    row.get('price_range_percent'),
                    row.get('volume_volatility'),
                    row.get('timeframe', '1d'),
                    row.get('market_stress_level'),
                    row.get('created_at')
                ))
            except Exception as e:
                logger.warning(f"Failed to migrate volatility record for {row.get('symbol', 'unknown')}: {e}")

        # Recreate indexes
        db_manager.execute_update("""
            CREATE INDEX IF NOT EXISTS idx_volatility_symbol
            ON volatility_tracking(symbol)
        """)

        db_manager.execute_update("""
            CREATE INDEX IF NOT EXISTS idx_volatility_timestamp
            ON volatility_tracking(created_at)
        """)

        # Clean up backup table
        db_manager.execute_update("DROP TABLE volatility_tracking_backup")

        logger.info("Successfully fixed volatility_tracking constraint issue")
        return True

    except Exception as e:
        logger.error(f"Error fixing volatility_tracking constraint: {e}")
        # Try to rollback if possible
        try:
            db_manager.execute_update("DROP TABLE IF EXISTS volatility_tracking")
            db_manager.execute_update("ALTER TABLE volatility_tracking_backup RENAME TO volatility_tracking")
            logger.info("Rolled back changes due to error")
        except:
            pass
        return False

def create_decision_logs_table():
    """Create decision logs table for tracking all autotrader buy/sell decisions"""
    try:
        db_manager.execute_update("""
            CREATE TABLE IF NOT EXISTS decision_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                decision_type TEXT NOT NULL CHECK (decision_type IN ('buy_signal', 'sell_signal', 'no_buy', 'no_sell')),
                action_taken TEXT CHECK (action_taken IN ('buy', 'sell', 'none')),
                score REAL,
                current_price REAL,

                -- Decision factors (JSON strings for complex data)
                filters_passed TEXT,  -- JSON: {"volatility": true, "overtrading": true, ...}
                filters_failed TEXT,  -- JSON: {"monthly_filter": false, ...}
                scoring_breakdown TEXT,  -- JSON: complete scoring breakdown

                -- Buy decision factors
                buy_threshold REAL,
                confidence REAL,
                position_size REAL,

                -- Sell decision factors
                sell_threshold REAL,
                entry_price REAL,
                pnl_percent REAL,
                days_held INTEGER,
                trailing_stop_price REAL,
                stop_loss_price REAL,
                take_profit_price REAL,

                -- Exit reason details
                exit_reason TEXT,
                exit_details TEXT,  -- JSON with full exit analysis

                -- Market context
                market_status TEXT,
                risk_within_limits INTEGER DEFAULT 1,
                portfolio_status TEXT,  -- JSON with portfolio snapshot

                -- Metadata
                cycle_id TEXT,  -- Links decisions from same cycle
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
        """)

        # Create indexes for efficient queries
        db_manager.execute_update("""
            CREATE INDEX IF NOT EXISTS idx_decision_logs_symbol
            ON decision_logs(symbol)
        """)

        db_manager.execute_update("""
            CREATE INDEX IF NOT EXISTS idx_decision_logs_timestamp
            ON decision_logs(timestamp)
        """)

        db_manager.execute_update("""
            CREATE INDEX IF NOT EXISTS idx_decision_logs_cycle
            ON decision_logs(cycle_id)
        """)

        db_manager.execute_update("""
            CREATE INDEX IF NOT EXISTS idx_decision_logs_decision_type
            ON decision_logs(decision_type)
        """)

        logger.info("Created decision_logs table")
        return True

    except Exception as e:
        logger.error(f"Error creating decision_logs table: {e}")
        return False