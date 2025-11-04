"""
PostgreSQL Database configuration and initialization
Replaces SQLite with PostgreSQL for production-ready architecture
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from typing import Dict, Any, List, Optional
import logging
from contextlib import contextmanager
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
env_file = '.env.local' if os.path.exists('.env.local') else '.env.prod'
load_dotenv(env_file)

# PostgreSQL connection URL
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    logger.warning("DATABASE_URL not set, falling back to default local PostgreSQL")
    DATABASE_URL = "postgresql://stock_analyzer_user:local_dev_password_123@localhost:5432/stock_analyzer_local"


class DatabaseManager:
    """PostgreSQL Database manager for Stock Analyzer API"""

    def __init__(self, db_url: str = DATABASE_URL):
        self.db_url = db_url
        logger.info(f"DatabaseManager initialized with PostgreSQL")

    @contextmanager
    def get_connection(self):
        """Get database connection with context manager"""
        conn = psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
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

            # PostgreSQL uses RETURNING id instead of lastrowid
            # If the query doesn't have RETURNING, we can't get the id
            # Modify the query to add RETURNING if needed
            if 'RETURNING' not in query.upper():
                logger.warning("INSERT query should include RETURNING id for PostgreSQL")
                return None

            result = cursor.fetchone()
            return result['id'] if result else None

    def execute_insert_with_returning(self, query: str, params: tuple = (), returning_column: str = 'id') -> int:
        """Execute INSERT query with explicit RETURNING clause"""
        # Add RETURNING clause if not present
        if 'RETURNING' not in query.upper():
            query = f"{query} RETURNING {returning_column}"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            result = cursor.fetchone()
            return result[returning_column] if result else None


def init_db():
    """
    Initialize PostgreSQL database with required schema

    Note: The schema.sql file should be run first to create all tables.
    This function performs additional initialization and migrations if needed.
    """
    db = DatabaseManager()

    logger.info("Checking PostgreSQL database initialization...")

    # Verify connection
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            logger.info(f"Connected to PostgreSQL: {version['version']}")

            # Check if portfolio_state is initialized
            cursor.execute("SELECT COUNT(*) as count FROM portfolio_state")
            result = cursor.fetchone()

            if result['count'] == 0:
                logger.info("Initializing portfolio_state with default values...")
                cursor.execute("""
                    INSERT INTO portfolio_state (
                        id,
                        liquid_capital_stocks,
                        liquid_capital_crypto
                    ) VALUES (1, 10000.00, 50000.00)
                    ON CONFLICT (id) DO NOTHING
                """)
                conn.commit()
                logger.info("Portfolio state initialized")

            # Check if system_config has default values
            cursor.execute("SELECT COUNT(*) as count FROM system_config")
            result = cursor.fetchone()

            if result['count'] == 0:
                logger.info("Initializing system_config with default values...")
                cursor.execute("""
                    INSERT INTO system_config (key, value, description) VALUES
                    ('autotrader_enabled', 'false', 'Enable/disable automated trading'),
                    ('max_positions_stocks', '10', 'Maximum number of stock positions'),
                    ('max_positions_crypto', '5', 'Maximum number of crypto positions'),
                    ('buy_score_threshold', '6.0', 'Minimum score to buy LONG'),
                    ('sell_score_threshold', '4.5', 'Score threshold to sell LONG'),
                    ('short_score_threshold', '1.8', 'Maximum score to open SHORT'),
                    ('risk_per_trade', '0.02', 'Risk 2% per trade'),
                    ('max_portfolio_risk', '0.10', 'Maximum 10% portfolio risk')
                    ON CONFLICT (key) DO NOTHING
                """)
                conn.commit()
                logger.info("System config initialized")

            logger.info("PostgreSQL database initialization completed successfully")

    except psycopg2.Error as e:
        logger.error(f"Database initialization error: {e}")
        raise


def verify_schema():
    """Verify that all required tables exist in PostgreSQL"""
    required_tables = [
        'system_config',
        'market_status',
        'symbols',
        'positions',
        'transactions',
        'autotrader_transactions',
        'portfolio_transactions',
        'portfolio_snapshots',
        'portfolio_state',
        'price_alerts',
        'sentiment_analysis',
        'mtss_scores',
        'volatility_tracking',
        'decision_logs',
        'market_data_5m',
        'data_quality_log',
        'ml_training_features',
        'ml_model_results'
    ]

    db = DatabaseManager()

    with db.get_connection() as conn:
        cursor = conn.cursor()

        for table in required_tables:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = %s
                )
            """, (table,))

            exists = cursor.fetchone()['exists']

            if exists:
                logger.info(f"✓ Table '{table}' exists")
            else:
                logger.error(f"✗ Table '{table}' MISSING")
                raise Exception(f"Required table '{table}' not found in database")

    logger.info("Schema verification completed successfully")


# Global database instance
db_manager = DatabaseManager()


if __name__ == '__main__':
    """
    Run this script to verify PostgreSQL setup:
    python src/api/database/database_postgres.py
    """
    print("=== PostgreSQL Database Verification ===\n")

    try:
        print("1. Verifying schema...")
        verify_schema()

        print("\n2. Initializing database...")
        init_db()

        print("\n3. Testing queries...")
        db = DatabaseManager()

        # Test system_config
        configs = db.execute_query("SELECT * FROM system_config LIMIT 5")
        print(f"   Found {len(configs)} config entries")

        # Test portfolio_state
        portfolio = db.execute_query("SELECT * FROM portfolio_state WHERE id = 1")
        if portfolio:
            print(f"   Portfolio state: ${portfolio[0]['liquid_capital_stocks']} stocks, ${portfolio[0]['liquid_capital_crypto']} crypto")

        # Test positions count
        positions = db.execute_query("SELECT COUNT(*) as count FROM positions")
        print(f"   Total positions: {positions[0]['count']}")

        print("\n✓ PostgreSQL database is working correctly!")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
