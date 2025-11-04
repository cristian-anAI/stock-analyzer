"""
SQLite to PostgreSQL Migration Script
Migrates all data from trading.db (SQLite) to PostgreSQL

Usage:
    python database/migrate_sqlite_to_postgres.py

Requirements:
    - PostgreSQL must be running and accessible
    - Update DATABASE_URL in .env.local or .env.prod
    - Install: pip install psycopg2-binary python-dotenv
"""

import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import os
from datetime import datetime
from dotenv import load_dotenv
import sys

# Load environment variables
env_file = '.env.local' if os.path.exists('.env.local') else '.env.prod'
load_dotenv(env_file)

# Database paths
SQLITE_DB = 'trading.db'
POSTGRES_URL = os.getenv('DATABASE_URL')

if not POSTGRES_URL:
    print("ERROR: DATABASE_URL not found in environment variables")
    print(f"Checked file: {env_file}")
    sys.exit(1)

print(f"=== SQLite to PostgreSQL Migration ===")
print(f"Source: {SQLITE_DB}")
print(f"Target: {POSTGRES_URL.replace(POSTGRES_URL.split('@')[0].split('://')[1], '***')}")
print(f"Environment: {env_file}")
print()

# Table mapping: SQLite table -> (PostgreSQL table, columns to migrate)
# Note: Some columns may need transformation or may be auto-generated in PostgreSQL
TABLES_TO_MIGRATE = {
    'system_config': {
        'columns': ['key', 'value', 'description'],
        'skip_id': True  # PostgreSQL uses SERIAL
    },
    'market_status': {
        'columns': ['date', 'is_open', 'notes'],
        'skip_id': True
    },
    'symbols': {
        'columns': [
            'symbol', 'name', 'sector', 'market_cap',
            'base_score', 'momentum_score', 'technical_score', 'total_score',
            'is_active', 'last_updated', 'added_date',
            'data_source', 'notes'
        ],
        'skip_id': True
    },
    'positions': {
        'columns': [
            'symbol', 'position_type',
            'entry_price', 'entry_date', 'quantity',
            'current_price', 'current_value', 'cost_basis',
            'unrealized_pnl', 'unrealized_pnl_pct',
            'stop_loss', 'take_profit', 'trailing_stop',
            'strategy', 'entry_score', 'is_open',
            'exit_price', 'exit_date', 'realized_pnl', 'realized_pnl_pct', 'exit_reason',
            'notes', 'last_updated'
        ],
        'skip_id': True
    },
    'transactions': {
        'columns': [
            'position_id', 'symbol', 'action',
            'quantity', 'price', 'total_value',
            'transaction_date',
            'commission', 'fees',
            'strategy', 'reason', 'notes'
        ],
        'skip_id': True
    },
    'autotrader_transactions': {
        'columns': [
            'symbol', 'action',
            'quantity', 'price', 'total_value',
            'transaction_date',
            'strategy', 'entry_score',
            'stop_loss', 'take_profit',
            'exit_price', 'exit_date', 'pnl', 'pnl_pct',
            'reason', 'notes'
        ],
        'skip_id': True
    },
    'portfolio_transactions': {
        'columns': [
            'transaction_type', 'amount', 'currency', 'account_type',
            'transaction_date', 'description', 'notes'
        ],
        'skip_id': True
    },
    'portfolio_snapshots': {
        'columns': [
            'snapshot_date',
            'liquid_capital_stocks', 'invested_capital_stocks', 'total_pnl_stocks', 'total_value_stocks',
            'liquid_capital_crypto', 'invested_capital_crypto', 'total_pnl_crypto', 'total_value_crypto',
            'total_portfolio_value',
            'open_positions_stocks', 'open_positions_crypto'
        ],
        'skip_id': True
    },
    'portfolio_state': {
        'columns': [
            'liquid_capital_stocks', 'invested_capital_stocks', 'total_pnl_stocks',
            'liquid_capital_crypto', 'invested_capital_crypto', 'total_pnl_crypto',
            'last_updated'
        ],
        'skip_id': False,  # Keep id = 1
        'force_id': 1
    },
    'price_alerts': {
        'columns': [
            'symbol', 'alert_type',
            'target_price', 'current_price',
            'is_active', 'is_triggered', 'triggered_at',
            'notification_method', 'notification_sent',
            'notes', 'updated_at'
        ],
        'skip_id': True
    },
    'sentiment_analysis': {
        'columns': [
            'symbol', 'analysis_date', 'source',
            'sentiment_score', 'confidence',
            'text_sample',
            'positive_mentions', 'negative_mentions', 'neutral_mentions'
        ],
        'skip_id': True
    },
    'mtss_scores': {
        'columns': [
            'symbol', 'score_date',
            'score_1d', 'score_4h', 'score_1h', 'total_score',
            'rsi_14', 'macd', 'signal',
            'momentum_7d', 'momentum_30d'
        ],
        'skip_id': True
    },
    'volatility_tracking': {
        'columns': [
            'symbol', 'tracking_date',
            'volatility_1d', 'volatility_7d', 'volatility_30d',
            'atr_14',
            'close_price', 'high_price', 'low_price'
        ],
        'skip_id': True
    },
    'decision_logs': {
        'columns': [
            'decision_date', 'symbol', 'decision_type',
            'strategy', 'score', 'confidence',
            'factors', 'action_taken', 'outcome', 'notes'
        ],
        'skip_id': True
    }
}


def connect_sqlite():
    """Connect to SQLite database"""
    if not os.path.exists(SQLITE_DB):
        print(f"ERROR: SQLite database not found: {SQLITE_DB}")
        sys.exit(1)

    return sqlite3.connect(SQLITE_DB)


def connect_postgres():
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        return conn
    except Exception as e:
        print(f"ERROR: Could not connect to PostgreSQL: {e}")
        sys.exit(1)


def get_sqlite_table_info(sqlite_conn, table_name):
    """Get table info from SQLite"""
    cursor = sqlite_conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return cursor.fetchall()


def check_table_exists_sqlite(sqlite_conn, table_name):
    """Check if table exists in SQLite"""
    cursor = sqlite_conn.cursor()
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    return cursor.fetchone() is not None


def migrate_table(sqlite_conn, pg_conn, table_name, config):
    """Migrate a single table from SQLite to PostgreSQL"""

    # Check if table exists in SQLite
    if not check_table_exists_sqlite(sqlite_conn, table_name):
        print(f"  ⚠️  Table '{table_name}' not found in SQLite - skipping")
        return 0

    # Get data from SQLite
    columns = config['columns']
    columns_str = ', '.join(columns)

    sqlite_cursor = sqlite_conn.cursor()

    # Add id column if not skipping
    if not config.get('skip_id', True):
        columns_str = 'id, ' + columns_str

    query = f"SELECT {columns_str} FROM {table_name}"
    sqlite_cursor.execute(query)
    rows = sqlite_cursor.fetchall()

    if not rows:
        print(f"  ℹ️  Table '{table_name}' is empty - skipping")
        return 0

    # Insert into PostgreSQL
    pg_cursor = pg_conn.cursor()

    # Clear existing data (optional - comment out if you want to preserve data)
    pg_cursor.execute(f"DELETE FROM {table_name}")

    # Prepare insert statement
    placeholders = ', '.join(['%s'] * len(columns))
    columns_insert = ', '.join(columns)

    if config.get('force_id'):
        # For portfolio_state - force id = 1
        placeholders = '%s, ' + placeholders
        columns_insert = 'id, ' + columns_insert
        rows = [(config['force_id'],) + row for row in rows]

    insert_query = f"INSERT INTO {table_name} ({columns_insert}) VALUES ({placeholders})"

    # Batch insert
    try:
        execute_values(pg_cursor, insert_query, rows, page_size=100)
        pg_conn.commit()
        print(f"  ✓ Migrated {len(rows)} rows from '{table_name}'")
        return len(rows)
    except Exception as e:
        pg_conn.rollback()
        print(f"  ✗ ERROR migrating '{table_name}': {e}")
        print(f"    First row sample: {rows[0] if rows else 'N/A'}")
        return 0


def verify_migration(sqlite_conn, pg_conn):
    """Verify data was migrated correctly"""
    print("\n=== Migration Verification ===")

    pg_cursor = pg_conn.cursor()

    total_sqlite = 0
    total_postgres = 0

    for table_name in TABLES_TO_MIGRATE.keys():
        # SQLite count
        if check_table_exists_sqlite(sqlite_conn, table_name):
            sqlite_cursor = sqlite_conn.cursor()
            sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            sqlite_count = sqlite_cursor.fetchone()[0]
        else:
            sqlite_count = 0

        # PostgreSQL count
        try:
            pg_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            pg_count = pg_cursor.fetchone()[0]
        except Exception as e:
            pg_count = 0
            print(f"  ⚠️  Could not count '{table_name}' in PostgreSQL: {e}")

        status = "✓" if sqlite_count == pg_count else "✗"
        print(f"  {status} {table_name:30s} SQLite: {sqlite_count:5d} | PostgreSQL: {pg_count:5d}")

        total_sqlite += sqlite_count
        total_postgres += pg_count

    print(f"\n  Total rows - SQLite: {total_sqlite} | PostgreSQL: {total_postgres}")

    if total_sqlite == total_postgres:
        print("  ✓ Migration verification PASSED")
        return True
    else:
        print("  ✗ Migration verification FAILED - row counts don't match")
        return False


def main():
    """Main migration function"""

    print("Connecting to databases...")
    sqlite_conn = connect_sqlite()
    pg_conn = connect_postgres()

    print("✓ Connected to both databases\n")

    # Create backup of PostgreSQL (optional)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    print(f"Starting migration at {timestamp}...\n")

    total_migrated = 0

    # Migrate each table
    for table_name, config in TABLES_TO_MIGRATE.items():
        print(f"Migrating '{table_name}'...")
        count = migrate_table(sqlite_conn, pg_conn, table_name, config)
        total_migrated += count

    print(f"\n=== Migration Summary ===")
    print(f"Total rows migrated: {total_migrated}")

    # Verify migration
    verification_passed = verify_migration(sqlite_conn, pg_conn)

    # Close connections
    sqlite_conn.close()
    pg_conn.close()

    if verification_passed:
        print("\n✓ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Update src/api/database/database.py to use PostgreSQL")
        print("2. Test the API with PostgreSQL")
        print("3. Keep trading.db as backup for now")
        return 0
    else:
        print("\n✗ Migration completed with errors")
        print("Please review the errors above and retry if needed")
        return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nMigration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
