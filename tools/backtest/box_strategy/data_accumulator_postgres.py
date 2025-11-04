"""
PostgreSQL Data Accumulator for Box Strategy
Downloads 60 days of 5-minute data from yfinance and accumulates in PostgreSQL

This solves the historical data problem:
- yfinance gives us 60 days of 5-minute data for free
- We download daily and merge into PostgreSQL
- After 1 year, we have 1 year of data accumulated for free!

Usage:
    python tools/backtest/box_strategy/data_accumulator_postgres.py

Schedule with cron (daily at 4 PM ET after market close):
    0 16 * * 1-5 cd /path/to/stock-analyzer && python tools/backtest/box_strategy/data_accumulator_postgres.py
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os
import sys
import time
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

# Load environment variables
env_file = '.env.local' if os.path.exists('.env.local') else '.env.prod'
load_dotenv(env_file)

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in environment")
    sys.exit(1)

# Market configurations
MARKET_CONFIGS = {
    'SPX': {
        'ticker': 'ES=F',
        'name': 'S&P 500',
        'timezone': 'America/New_York'
    },
    'NDX': {
        'ticker': 'NQ=F',
        'name': 'Nasdaq 100',
        'timezone': 'America/New_York'
    },
    'RUT': {
        'ticker': 'RTY=F',
        'name': 'Russell 2000',
        'timezone': 'America/New_York'
    },
    'DAX': {
        'ticker': 'FDAX=F',
        'name': 'DAX',
        'timezone': 'Europe/Berlin'
    },
    'FTSE': {
        'ticker': 'FTSE',
        'name': 'FTSE 100',
        'timezone': 'Europe/London'
    },
    'CAC': {
        'ticker': 'CAC',
        'name': 'CAC 40',
        'timezone': 'Europe/Paris'
    },
    'STOXX': {
        'ticker': 'STOXX50E',
        'name': 'Euro Stoxx 50',
        'timezone': 'Europe/Berlin'
    },
    'NIKKEI': {
        'ticker': 'NI225',
        'name': 'Nikkei 225',
        'timezone': 'Asia/Tokyo'
    },
    'HSI': {
        'ticker': 'HSI',
        'name': 'Hang Seng',
        'timezone': 'Asia/Hong_Kong'
    },
    'ASX': {
        'ticker': 'AXJO',
        'name': 'ASX 200',
        'timezone': 'Australia/Sydney'
    }
}

# Rate limiting
MAX_CALLS_PER_MINUTE = 50
call_times = []


def rate_limit():
    """Implement leaky bucket rate limiting"""
    global call_times
    now = time.time()

    # Remove calls older than 1 minute
    call_times = [t for t in call_times if now - t < 60]

    if len(call_times) >= MAX_CALLS_PER_MINUTE:
        sleep_time = 60 - (now - call_times[0])
        if sleep_time > 0:
            print(f"  Rate limit reached, sleeping {sleep_time:.1f}s...")
            time.sleep(sleep_time)

    call_times.append(time.time())


def download_market_data(market: str, ticker: str, days: int = 60) -> pd.DataFrame:
    """
    Download 5-minute data from yfinance

    Args:
        market: Market symbol (SPX, NDX, etc.)
        ticker: yfinance ticker (ES=F, NQ=F, etc.)
        days: Number of days to download (max 60 for 5min data)

    Returns:
        DataFrame with OHLCV data, timezone-aware index
    """
    print(f"\nDownloading {market} ({ticker}) - last {days} days...")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    try:
        rate_limit()

        stock = yf.Ticker(ticker)
        data = stock.history(
            start=start_date,
            end=end_date,
            interval='5m',
            auto_adjust=False
        )

        if data.empty:
            print(f"  ⚠️  No data returned for {market}")
            return pd.DataFrame()

        # Reset index to get timestamp as column
        data = data.reset_index()

        # Ensure timezone-aware
        if 'Datetime' in data.columns:
            if data['Datetime'].dt.tz is None:
                # Assume UTC if no timezone
                data['Datetime'] = pd.to_datetime(data['Datetime'], utc=True)
        elif 'Date' in data.columns:
            if data['Date'].dt.tz is None:
                data['Date'] = pd.to_datetime(data['Date'], utc=True)
            data.rename(columns={'Date': 'Datetime'}, inplace=True)

        # Rename columns to match our schema
        data.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        }, inplace=True)

        # Select only needed columns
        data = data[['Datetime', 'open', 'high', 'low', 'close', 'volume']]

        print(f"  ✓ Downloaded {len(data)} candles")
        print(f"    Date range: {data['Datetime'].min()} to {data['Datetime'].max()}")

        return data

    except Exception as e:
        print(f"  ✗ Error downloading {market}: {e}")
        return pd.DataFrame()


def get_existing_date_range(conn, market: str) -> tuple:
    """
    Get the date range of existing data in PostgreSQL for a market

    Returns:
        (min_date, max_date) or (None, None) if no data
    """
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            MIN(timestamp) as min_date,
            MAX(timestamp) as max_date,
            COUNT(*) as count
        FROM market_data_5m
        WHERE market = %s
    """, (market,))

    result = cursor.fetchone()

    if result and result[2] > 0:
        return result[0], result[1]
    else:
        return None, None


def insert_market_data(conn, market: str, ticker: str, data: pd.DataFrame) -> int:
    """
    Insert market data into PostgreSQL, skipping duplicates

    Returns:
        Number of rows inserted
    """
    if data.empty:
        return 0

    cursor = conn.cursor()

    # Prepare data for insertion
    records = []
    for _, row in data.iterrows():
        records.append((
            market,
            ticker,
            row['Datetime'],
            float(row['open']),
            float(row['high']),
            float(row['low']),
            float(row['close']),
            int(row['volume']) if pd.notna(row['volume']) else 0,
            'yfinance',
            1.0  # quality_score
        ))

    # Insert with ON CONFLICT DO NOTHING to skip duplicates
    insert_query = """
        INSERT INTO market_data_5m
        (market, ticker, timestamp, open, high, low, close, volume, source, quality_score)
        VALUES %s
        ON CONFLICT (market, timestamp) DO NOTHING
    """

    try:
        execute_values(cursor, insert_query, records, page_size=1000)
        conn.commit()
        inserted = cursor.rowcount
        print(f"  ✓ Inserted {inserted} new candles (skipped {len(records) - inserted} duplicates)")
        return inserted

    except Exception as e:
        conn.rollback()
        print(f"  ✗ Error inserting data: {e}")
        return 0


def log_data_quality(conn, market: str, start_date, end_date, total_candles: int, missing_candles: int):
    """Log data quality metrics"""
    cursor = conn.cursor()

    quality_score = (total_candles - missing_candles) / total_candles if total_candles > 0 else 0

    cursor.execute("""
        INSERT INTO data_quality_log
        (market, check_date, start_date, end_date, total_candles, missing_candles, quality_score)
        VALUES (%s, NOW(), %s, %s, %s, %s, %s)
    """, (market, start_date, end_date, total_candles, missing_candles, quality_score))

    conn.commit()


def accumulate_market(conn, market: str, config: dict) -> dict:
    """
    Accumulate data for a single market

    Returns:
        Stats dict with inserted, duplicates, etc.
    """
    ticker = config['ticker']

    print(f"\n{'='*60}")
    print(f"Market: {market} ({config['name']})")
    print(f"Ticker: {ticker}")
    print(f"{'='*60}")

    # Check existing data
    min_date, max_date = get_existing_date_range(conn, market)

    if min_date:
        print(f"Existing data: {min_date} to {max_date}")
    else:
        print(f"No existing data - first run")

    # Download new data (60 days max from yfinance)
    data = download_market_data(market, ticker, days=60)

    if data.empty:
        return {
            'market': market,
            'inserted': 0,
            'duplicates': 0,
            'error': True
        }

    # Insert into PostgreSQL
    inserted = insert_market_data(conn, market, ticker, data)

    # Log quality
    log_data_quality(conn, market, data['Datetime'].min(), data['Datetime'].max(), len(data), 0)

    # Get updated range
    new_min_date, new_max_date = get_existing_date_range(conn, market)

    print(f"\nUpdated data range: {new_min_date} to {new_max_date}")

    return {
        'market': market,
        'inserted': inserted,
        'duplicates': len(data) - inserted,
        'total_candles': len(data),
        'date_range': (new_min_date, new_max_date),
        'error': False
    }


def main():
    """Main accumulator function"""

    print("\n" + "="*60)
    print("PostgreSQL Data Accumulator - Box Strategy")
    print("="*60)
    print(f"Time: {datetime.now()}")
    print(f"Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")
    print(f"Markets: {len(MARKET_CONFIGS)}")
    print("="*60)

    # Connect to PostgreSQL
    try:
        conn = psycopg2.connect(DATABASE_URL)
        print("\n✓ Connected to PostgreSQL")
    except Exception as e:
        print(f"\n✗ Could not connect to PostgreSQL: {e}")
        sys.exit(1)

    # Accumulate data for each market
    results = []

    for market, config in MARKET_CONFIGS.items():
        try:
            result = accumulate_market(conn, market, config)
            results.append(result)
        except Exception as e:
            print(f"\n✗ Error processing {market}: {e}")
            results.append({
                'market': market,
                'inserted': 0,
                'duplicates': 0,
                'error': True,
                'error_msg': str(e)
            })

    # Summary
    print("\n" + "="*60)
    print("ACCUMULATION SUMMARY")
    print("="*60)

    total_inserted = sum(r['inserted'] for r in results if not r['error'])
    total_duplicates = sum(r['duplicates'] for r in results if not r['error'])
    errors = sum(1 for r in results if r['error'])

    print(f"\nTotal markets processed: {len(results)}")
    print(f"New candles inserted: {total_inserted}")
    print(f"Duplicates skipped: {total_duplicates}")
    print(f"Errors: {errors}")

    print("\nPer-market breakdown:")
    for r in results:
        if r['error']:
            print(f"  ✗ {r['market']:10s} - ERROR")
        else:
            print(f"  ✓ {r['market']:10s} - {r['inserted']:5d} new, {r['duplicates']:5d} duplicates")

    # Close connection
    conn.close()

    print("\n" + "="*60)
    print("Data accumulation completed!")
    print(f"Next run: Tomorrow at 4 PM ET (after market close)")
    print("="*60)

    return 0 if errors == 0 else 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nAccumulation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
