"""
New Strategy Migrations - Database schema updates for enhanced autotrader
Adds tables for cooldowns, blacklist, volatility tracking, and strategy config
"""

import logging
import sqlite3
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

def create_strategy_tables(db_path: str = "trading.db") -> bool:
    """
    Create new tables needed for enhanced autotrader strategies
    
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()
        
        logger.info("Creating strategy enhancement tables...")
        
        # 1. Trading Cooldowns Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS trading_cooldowns (
                symbol TEXT PRIMARY KEY,
                last_trade_timestamp TEXT NOT NULL,
                cooldown_until TEXT NOT NULL,
                reason TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Index for faster cooldown queries
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_cooldowns_until ON trading_cooldowns(cooldown_until)
        ''')
        
        logger.info("Created trading_cooldowns table")
        
        # 2. Symbol Blacklist Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS symbol_blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                blacklist_until TEXT NOT NULL,
                reason TEXT,
                consecutive_losses INTEGER DEFAULT 0,
                asset_type TEXT, -- 'stock' or 'crypto'
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Index for active blacklist queries
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_blacklist_active ON symbol_blacklist(symbol, blacklist_until)
        ''')
        
        logger.info("Created symbol_blacklist table")
        
        # 3. Volatility Tracking Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS volatility_tracking (
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                daily_volatility REAL,
                atr_14 REAL,
                volatility_percentile REAL, -- Where current volatility ranks vs historical
                is_high_volatility INTEGER DEFAULT 0, -- 1 if above threshold
                price_range_percent REAL, -- Daily high-low range %
                volume_volatility REAL, -- Volume standard deviation
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, date)
            )
        ''')
        
        # Index for volatility queries
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_volatility_date ON volatility_tracking(date)
        ''')
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_volatility_symbol ON volatility_tracking(symbol)
        ''')
        
        logger.info("Created volatility_tracking table")
        
        # 4. Strategy Configuration Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS strategy_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_type TEXT NOT NULL, -- 'stock' or 'crypto'
                strategy_name TEXT NOT NULL,
                config_key TEXT NOT NULL,
                config_value TEXT, -- JSON string for complex values
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(asset_type, strategy_name, config_key)
            )
        ''')
        
        # Index for strategy config lookups
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_strategy_config ON strategy_config(asset_type, strategy_name, is_active)
        ''')
        
        logger.info("Created strategy_config table")
        
        # 5. Trade Performance Tracking
        c.execute('''
            CREATE TABLE IF NOT EXISTS trade_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                strategy_used TEXT,
                entry_date TEXT NOT NULL,
                exit_date TEXT,
                entry_price REAL NOT NULL,
                exit_price REAL,
                quantity REAL NOT NULL,
                realized_pnl REAL,
                realized_pnl_percent REAL,
                days_held INTEGER,
                exit_reason TEXT,
                max_profit_percent REAL, -- Peak profit during hold
                max_loss_percent REAL,   -- Peak loss during hold
                volatility_at_entry REAL,
                score_at_entry REAL,
                score_at_exit REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Indexes for performance analysis
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_performance_symbol ON trade_performance(symbol)
        ''')
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_performance_strategy ON trade_performance(strategy_used)
        ''')
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_performance_dates ON trade_performance(entry_date, exit_date)
        ''')
        
        logger.info("Created trade_performance table")
        
        # 6. Update existing positions table with new columns
        logger.info("Adding new columns to positions table...")
        
        try:
            # Check if columns exist before adding
            c.execute("PRAGMA table_info(positions)")
            existing_columns = [column[1] for column in c.fetchall()]
            
            new_columns = {
                'strategy_used': 'TEXT',
                'timeframe_primary': 'TEXT', 
                'entry_volatility': 'REAL',
                'max_hold_days': 'INTEGER',
                'cooldown_until': 'TEXT',
                'entry_score': 'REAL',
                'stop_loss_updated': 'REAL',
                'take_profit_updated': 'REAL'
            }
            
            for column_name, column_type in new_columns.items():
                if column_name not in existing_columns:
                    c.execute(f'ALTER TABLE positions ADD COLUMN {column_name} {column_type}')
                    logger.info(f"Added {column_name} column to positions")
                else:
                    logger.debug(f"Column {column_name} already exists in positions")
            
        except Exception as e:
            logger.warning(f"Error updating positions table: {e}")
        
        # 7. Insert default strategy configurations
        logger.info("Inserting default strategy configurations...")
        
        default_configs = [
            # Swing Trading Strategy configs
            ('stock', 'SwingTrading', 'timeframe_primary', '1d'),
            ('stock', 'SwingTrading', 'timeframe_confirmation', '4h'),
            ('stock', 'SwingTrading', 'timeframe_entry', '1h'),
            ('stock', 'SwingTrading', 'buy_threshold', '7.5'),
            ('stock', 'SwingTrading', 'sell_threshold', '4.0'),
            ('stock', 'SwingTrading', 'risk_per_trade_percent', '2.0'),
            ('stock', 'SwingTrading', 'max_hold_days', '20'),
            ('stock', 'SwingTrading', 'min_hold_days', '3'),
            
            # Crypto Competition Strategy configs  
            ('crypto', 'CryptoCompetition', 'timeframe_primary', '4h'),
            ('crypto', 'CryptoCompetition', 'timeframe_entry', '1h'),
            ('crypto', 'CryptoCompetition', 'buy_threshold', '8.0'),
            ('crypto', 'CryptoCompetition', 'sell_threshold', '3.5'),
            ('crypto', 'CryptoCompetition', 'risk_per_trade_percent', '5.0'),
            ('crypto', 'CryptoCompetition', 'volatility_limit', '0.15'),
            ('crypto', 'CryptoCompetition', 'max_hold_days', '10'),
            
            # Risk Management configs
            ('stock', 'RiskManagement', 'max_portfolio_allocation', '70'),
            ('crypto', 'RiskManagement', 'max_portfolio_allocation', '30'),
            ('stock', 'RiskManagement', 'max_daily_trades', '5'),
            ('crypto', 'RiskManagement', 'max_daily_trades', '3'),
            ('stock', 'RiskManagement', 'cooldown_hours_same_symbol', '4'),
            ('crypto', 'RiskManagement', 'cooldown_hours_same_symbol', '2'),
        ]
        
        for asset_type, strategy_name, config_key, config_value in default_configs:
            c.execute('''
                INSERT OR IGNORE INTO strategy_config 
                (asset_type, strategy_name, config_key, config_value) 
                VALUES (?, ?, ?, ?)
            ''', (asset_type, strategy_name, config_key, config_value))
        
        logger.info("Inserted default strategy configurations")
        
        # 8. Create views for easier querying
        logger.info("Creating useful views...")
        
        # View for active positions with strategy info
        c.execute('''
            CREATE VIEW IF NOT EXISTS v_active_positions AS
            SELECT 
                p.*,
                tc.cooldown_until,
                sb.blacklist_until,
                vt.daily_volatility,
                vt.is_high_volatility
            FROM positions p
            LEFT JOIN trading_cooldowns tc ON p.symbol = tc.symbol
            LEFT JOIN symbol_blacklist sb ON p.symbol = sb.symbol AND datetime(sb.blacklist_until) > datetime('now')
            LEFT JOIN volatility_tracking vt ON p.symbol = vt.symbol AND vt.date = date('now')
            WHERE p.source = 'autotrader'
        ''')
        
        # View for strategy performance
        c.execute('''
            CREATE VIEW IF NOT EXISTS v_strategy_performance AS
            SELECT 
                strategy_used,
                asset_type,
                COUNT(*) as total_trades,
                COUNT(CASE WHEN exit_date IS NOT NULL THEN 1 END) as completed_trades,
                AVG(CASE WHEN realized_pnl IS NOT NULL THEN realized_pnl_percent END) as avg_return_percent,
                AVG(CASE WHEN realized_pnl IS NOT NULL THEN days_held END) as avg_hold_days,
                COUNT(CASE WHEN realized_pnl > 0 THEN 1 END) * 100.0 / COUNT(CASE WHEN realized_pnl IS NOT NULL THEN 1 END) as win_rate,
                SUM(CASE WHEN realized_pnl IS NOT NULL THEN realized_pnl END) as total_realized_pnl
            FROM trade_performance
            WHERE exit_date IS NOT NULL
            GROUP BY strategy_used, asset_type
        ''')
        
        logger.info("Created views")
        
        conn.commit()
        conn.close()
        
        logger.info("Successfully created all strategy enhancement tables")
        return True
        
    except Exception as e:
        logger.error(f"Error creating strategy tables: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def drop_strategy_tables(db_path: str = "trading.db") -> bool:
    """
    Drop strategy tables (for development/testing)
    
    Returns:
        True if successful
    """
    try:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()
        
        tables_to_drop = [
            'trading_cooldowns',
            'symbol_blacklist', 
            'volatility_tracking',
            'strategy_config',
            'trade_performance'
        ]
        
        views_to_drop = [
            'v_active_positions',
            'v_strategy_performance'
        ]
        
        logger.info("Dropping strategy tables and views...")
        
        for view in views_to_drop:
            c.execute(f'DROP VIEW IF EXISTS {view}')
            logger.info(f"Dropped view {view}")
        
        for table in tables_to_drop:
            c.execute(f'DROP TABLE IF EXISTS {table}')
            logger.info(f"Dropped table {table}")
        
        conn.commit()
        conn.close()
        
        logger.info("Successfully dropped strategy tables")
        return True
        
    except Exception as e:
        logger.error(f"Error dropping strategy tables: {e}")
        return False

def get_strategy_config(asset_type: str, strategy_name: str, db_path: str = "trading.db") -> dict:
    """
    Get configuration for a specific strategy
    
    Args:
        asset_type: 'stock' or 'crypto'
        strategy_name: Name of strategy
        db_path: Database path
    
    Returns:
        Dict with configuration
    """
    try:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()
        
        c.execute('''
            SELECT config_key, config_value 
            FROM strategy_config 
            WHERE asset_type = ? AND strategy_name = ? AND is_active = 1
        ''', (asset_type, strategy_name))
        
        config = {}
        for row in c.fetchall():
            key, value = row
            # Try to convert numeric values
            try:
                if '.' in value:
                    config[key] = float(value)
                else:
                    config[key] = int(value)
            except (ValueError, TypeError):
                config[key] = value
        
        conn.close()
        return config
        
    except Exception as e:
        logger.error(f"Error getting strategy config: {e}")
        return {}

if __name__ == "__main__":
    # Create tables when run directly
    print("Creating strategy enhancement tables...")
    success = create_strategy_tables()
    if success:
        print("✓ All tables created successfully")
    else:
        print("✗ Error creating tables")