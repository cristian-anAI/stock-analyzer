"""
Data Loader for Box Strategy Backtesting

Handles downloading and caching of intraday price data for major indices.
Supports 5-minute timeframe with proper timezone handling.

IMPORTANT LIMITATIONS:
- yfinance provides up to 60 days of 5-minute data
- For longer historical periods, consider alternative data providers:
  * Interactive Brokers API
  * Alpha Vantage
  * Polygon.io
  * FirstRate Data
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import pickle
from typing import Optional, Dict, Tuple
import pytz
from zoneinfo import ZoneInfo

# Try to import market configurations
try:
    from market_config import MARKETS, get_market_config as _get_market_config
    USE_MARKET_CONFIG = True
except ImportError:
    USE_MARKET_CONFIG = False
    _get_market_config = None


class DataLoader:
    """Loads and caches intraday market data for backtesting"""

    # Fallback symbol mappings
    SYMBOLS = {
        'SPX': 'ES=F',
        'NDX': 'NQ=F',
        'RUT': 'RTY=F',  # Russell 2000 futures
        'DAX': 'FDAX=F',
        'FTSE': '^FTSE',
        'CAC': '^FCHI',
        'STOXX': '^STOXX50E',
        'NKY': 'NKD=F',
        'HSI': '^HSI',
        'ASX': '^AXJO',
        'IBEX': '^IBEX'
    }

    def get_market_config(self, market_code: str):
        """Get market configuration if available"""
        if USE_MARKET_CONFIG and _get_market_config:
            return _get_market_config(market_code)
        else:
            raise ImportError("Market config not available")

    def __init__(self, cache_dir: str = "tools/backtest/box_strategy/cache"):
        """
        Initialize DataLoader

        Args:
            cache_dir: Directory to store cached data
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Timezone definitions
        self.et_tz = ZoneInfo("America/New_York")
        self.gmt2_tz = ZoneInfo("Europe/Madrid")  # GMT+2 (CET/CEST)

    def download_5min_data(
        self,
        symbol_key: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        force_refresh: bool = False
    ) -> pd.DataFrame:
        """
        Download 5-minute intraday data for a symbol

        Args:
            symbol_key: Key from SYMBOLS dict (e.g., 'SPX', 'NDX')
            start_date: Start date for data (default: 60 days ago)
            end_date: End date for data (default: today)
            force_refresh: If True, ignore cache and redownload

        Returns:
            DataFrame with OHLCV data and timezone-aware datetime index
        """
        # Get ticker symbol and timezone
        if USE_MARKET_CONFIG:
            try:
                config = self.get_market_config(symbol_key)
                ticker = config.symbol
                market_tz = config.timezone
            except:
                # Fallback to old method
                if symbol_key not in self.SYMBOLS:
                    raise ValueError(f"Unknown symbol: {symbol_key}. Available: {list(self.SYMBOLS.keys())}")
                ticker = self.SYMBOLS[symbol_key]
                market_tz = self.et_tz
        else:
            if symbol_key not in self.SYMBOLS:
                raise ValueError(f"Unknown symbol: {symbol_key}. Available: {list(self.SYMBOLS.keys())}")
            ticker = self.SYMBOLS[symbol_key]
            market_tz = self.et_tz

        # Set default date range (yfinance limitation: ~60 days for 5min data)
        if end_date is None:
            end_date = datetime.now(self.et_tz)
        if start_date is None:
            start_date = end_date - timedelta(days=60)

        # Generate cache filename
        cache_file = self.cache_dir / f"{symbol_key}_5m_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pkl"

        # Try to load from cache
        if not force_refresh and cache_file.exists():
            print(f"Loading {symbol_key} from cache: {cache_file}")
            with open(cache_file, 'rb') as f:
                return pickle.load(f)

        # Download fresh data
        print(f"Downloading 5-min data for {ticker} ({symbol_key}) from {start_date.date()} to {end_date.date()}")

        try:
            df = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                interval='5m',
                progress=False
            )

            if df.empty:
                raise ValueError(f"No data returned for {ticker}")

            # Ensure timezone awareness
            if df.index.tz is None:
                df.index = df.index.tz_localize(market_tz)
            else:
                df.index = df.index.tz_convert(market_tz)

            # Standardize column names (handle MultiIndex first!)
            if isinstance(df.columns, pd.MultiIndex):
                # yfinance returns MultiIndex columns like ('Close', 'ES=F')
                # Drop the ticker level to get standard column names
                df.columns = df.columns.droplevel(1)
            elif len(df.columns) == 6:
                df.columns = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
            elif len(df.columns) == 5:
                df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

            # Ensure we have the required columns
            if 'Close' not in df.columns:
                raise ValueError(f"Downloaded data doesn't have required 'Close' column. Columns: {df.columns.tolist()}")

            # Cache the data
            with open(cache_file, 'wb') as f:
                pickle.dump(df, f)

            print(f"Downloaded {len(df)} candles for {symbol_key}")
            return df

        except Exception as e:
            print(f"Error downloading data for {ticker}: {e}")
            raise

    def get_trading_days(self, df: pd.DataFrame) -> list:
        """
        Extract unique trading days from intraday data

        Args:
            df: DataFrame with timezone-aware datetime index

        Returns:
            List of unique trading dates
        """
        return sorted(pd.unique(df.index.date))

    def get_box_period_data(
        self,
        df: pd.DataFrame,
        date: datetime.date
    ) -> Tuple[pd.DataFrame, float, float]:
        """
        Extract data for box formation period (8:30 AM - 10:00 AM ET)

        Args:
            df: Full 5-minute OHLCV dataframe
            date: Trading day to analyze

        Returns:
            Tuple of (box_period_df, box_high, box_low)
        """
        # Define box period in ET timezone
        box_start = datetime.combine(date, datetime.min.time()).replace(
            hour=8, minute=30, tzinfo=self.et_tz
        )
        box_end = datetime.combine(date, datetime.min.time()).replace(
            hour=10, minute=0, tzinfo=self.et_tz
        )

        # Filter data for box period
        box_data = df[(df.index >= box_start) & (df.index < box_end)]

        if box_data.empty:
            return box_data, None, None

        # Calculate box range
        box_high = box_data['High'].max()
        box_low = box_data['Low'].min()

        return box_data, box_high, box_low

    def get_post_box_data(
        self,
        df: pd.DataFrame,
        date: datetime.date,
        hours: int = 2
    ) -> pd.DataFrame:
        """
        Extract data after box period for entry detection

        Args:
            df: Full 5-minute OHLCV dataframe
            date: Trading day to analyze
            hours: Hours after box close to consider for entry (default: 2)

        Returns:
            DataFrame with post-box period data
        """
        # Box closes at 10:00 AM ET
        box_end = datetime.combine(date, datetime.min.time()).replace(
            hour=10, minute=0, tzinfo=self.et_tz
        )
        entry_deadline = box_end + timedelta(hours=hours)

        # Filter data for entry window
        post_box_data = df[(df.index >= box_end) & (df.index <= entry_deadline)]

        return post_box_data

    def get_full_day_data(
        self,
        df: pd.DataFrame,
        date: datetime.date
    ) -> pd.DataFrame:
        """
        Extract all data for a specific trading day

        Args:
            df: Full 5-minute OHLCV dataframe
            date: Trading day to extract

        Returns:
            DataFrame with full day data
        """
        day_start = datetime.combine(date, datetime.min.time()).replace(tzinfo=self.et_tz)
        day_end = day_start + timedelta(days=1)

        day_data = df[(df.index >= day_start) & (df.index < day_end)]

        return day_data

    def clear_cache(self):
        """Remove all cached data files"""
        for cache_file in self.cache_dir.glob("*.pkl"):
            cache_file.unlink()
        print(f"Cleared all cache files from {self.cache_dir}")


def main():
    """Test data loader functionality"""
    loader = DataLoader()

    # Test downloading S&P 500 data
    print("\n=== Testing S&P 500 (ES) Data Download ===")
    spx_data = loader.download_5min_data('SPX')
    print(f"\nFirst few rows:\n{spx_data.head()}")
    print(f"\nLast few rows:\n{spx_data.tail()}")
    print(f"\nData shape: {spx_data.shape}")
    print(f"\nDate range: {spx_data.index[0]} to {spx_data.index[-1]}")

    # Test box period extraction
    print("\n=== Testing Box Period Extraction ===")
    trading_days = loader.get_trading_days(spx_data)
    print(f"Total trading days: {len(trading_days)}")

    if trading_days:
        test_date = trading_days[-1]  # Most recent day
        box_data, box_high, box_low = loader.get_box_period_data(spx_data, test_date)
        print(f"\nBox data for {test_date}:")
        print(f"Box High: {box_high}")
        print(f"Box Low: {box_low}")
        print(f"Box Range: {box_high - box_low if box_high and box_low else 'N/A'}")
        print(f"Candles in box: {len(box_data)}")


if __name__ == "__main__":
    main()
