"""
TimeframeDataService - Manejo de datos por timeframes específicos
Soporte para diferentes intervalos de tiempo para stocks y crypto
"""

import logging
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import time

logger = logging.getLogger(__name__)

class TimeframeDataService:
    """Service for fetching and processing data across different timeframes"""
    
    def __init__(self):
        self.cache = {}  # Simple cache for recent data
        self.cache_duration = 300  # 5 minutes cache
        
        # Timeframe mappings for yfinance
        self.valid_timeframes = {
            "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1h", "4h": "1h", "1d": "1d", "1wk": "1wk"
        }
        
        # Default periods for each timeframe
        self.default_periods = {
            "1m": 60,      # 1 hour of 1m data
            "5m": 288,     # 1 day of 5m data  
            "15m": 192,    # 2 days of 15m data
            "30m": 168,    # 3.5 days of 30m data
            "1h": 168,     # 1 week of hourly data
            "4h": 168,     # 4 weeks of 4h data (need to process from 1h)
            "1d": 60,      # 2 months of daily data
            "1wk": 52      # 1 year of weekly data
        }
    
    def get_stock_data(self, symbol: str, timeframe: str = "1d", periods: int = None) -> Optional[pd.DataFrame]:
        """
        Get stock data for specific timeframe
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            timeframe: Time interval ("1m", "5m", "15m", "30m", "1h", "4h", "1d", "1wk")
            periods: Number of periods to fetch (default based on timeframe)
        
        Returns:
            DataFrame with OHLCV data and calculated indicators
        """
        try:
            # Cache key
            cache_key = f"{symbol}_{timeframe}_{periods}"
            
            # Check cache
            if self._is_cached_valid(cache_key):
                logger.debug(f"Using cached data for {symbol} {timeframe}")
                return self.cache[cache_key]['data']
            
            if periods is None:
                periods = self.default_periods.get(timeframe, 60)
            
            # Handle 4H timeframe (convert from 1H data)
            if timeframe == "4h":
                return self._get_4h_data_from_1h(symbol, periods)
            
            # Validate timeframe
            if timeframe not in self.valid_timeframes:
                logger.error(f"Invalid timeframe: {timeframe}")
                return None
            
            yf_timeframe = self.valid_timeframes[timeframe]
            
            # Calculate period for yfinance
            if timeframe in ["1m", "5m"]:
                # For intraday, use period in days
                period_days = max(1, periods // (390 // int(timeframe[:-1])))  # 390 mins in trading day
                period = f"{period_days}d"
            else:
                # For longer timeframes, calculate period more intelligently
                if timeframe == "1h":
                    period = f"{max(1, periods // 24)}d"
                elif timeframe == "1d":
                    period = f"{max(30, periods)}d" if periods < 365 else f"{periods // 365}y"
                else:
                    period = f"{periods}d"
            
            # Fetch data from yfinance
            ticker = yf.Ticker(symbol)
            
            try:
                data = ticker.history(
                    period=period,
                    interval=yf_timeframe,
                    auto_adjust=True,
                    prepost=False
                )
            except Exception as e:
                logger.warning(f"Failed to fetch with period {period}, trying max period for {symbol}")
                data = ticker.history(
                    period="max",
                    interval=yf_timeframe,
                    auto_adjust=True,
                    prepost=False
                )
            
            if data.empty:
                logger.warning(f"No data retrieved for {symbol} {timeframe}")
                return None
            
            # Take last N periods
            if len(data) > periods:
                data = data.tail(periods)
            
            # Calculate indicators
            data_with_indicators = self.calculate_indicators_by_timeframe(data, timeframe)
            
            # Cache the result
            self.cache[cache_key] = {
                'data': data_with_indicators,
                'timestamp': time.time()
            }
            
            logger.info(f"Fetched {len(data_with_indicators)} periods of {timeframe} data for {symbol}")
            return data_with_indicators
            
        except Exception as e:
            logger.error(f"Error fetching stock data for {symbol} {timeframe}: {e}")
            return None
    
    def get_crypto_data(self, symbol: str, timeframe: str = "4h", periods: int = 168) -> Optional[pd.DataFrame]:
        """
        Get crypto data for specific timeframe
        
        Args:
            symbol: Crypto symbol (e.g., "BTC-USD")
            timeframe: Time interval 
            periods: Number of periods (default 168 = 4 weeks of 4H data)
        
        Returns:
            DataFrame with OHLCV data and calculated indicators
        """
        try:
            # For crypto, we can use the same yfinance approach
            # Crypto trades 24/7 so we get more consistent data
            
            cache_key = f"{symbol}_crypto_{timeframe}_{periods}"
            
            if self._is_cached_valid(cache_key):
                logger.debug(f"Using cached crypto data for {symbol} {timeframe}")
                return self.cache[cache_key]['data']
            
            # Handle 4H data specially
            if timeframe == "4h":
                return self._get_4h_data_from_1h(symbol, periods, is_crypto=True)
            
            # Use stock data method for crypto (yfinance handles both)
            data = self.get_stock_data(symbol, timeframe, periods)
            
            if data is not None:
                # Cache crypto data separately
                self.cache[cache_key] = {
                    'data': data,
                    'timestamp': time.time()
                }
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching crypto data for {symbol} {timeframe}: {e}")
            return None
    
    def _get_4h_data_from_1h(self, symbol: str, periods: int = 168, is_crypto: bool = False) -> Optional[pd.DataFrame]:
        """
        Create 4H data by resampling 1H data
        
        Args:
            symbol: Symbol to fetch
            periods: Number of 4H periods needed
            is_crypto: Whether this is crypto data
        
        Returns:
            DataFrame with 4H OHLCV data
        """
        try:
            # Fetch enough 1H data to create the 4H periods
            # Need 4x more 1H data than 4H periods needed
            h1_periods_needed = periods * 4 + 24  # Extra buffer
            
            # Get 1H data
            h1_data = self.get_stock_data(symbol, "1h", h1_periods_needed)
            if h1_data is None or h1_data.empty:
                return None
            
            # Resample to 4H
            h4_data = h1_data.resample('4H', closed='right', label='right').agg({
                'Open': 'first',
                'High': 'max', 
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
            
            # Take only the requested number of periods
            if len(h4_data) > periods:
                h4_data = h4_data.tail(periods)
            
            # Recalculate indicators for 4H timeframe
            h4_with_indicators = self.calculate_indicators_by_timeframe(h4_data, "4h")
            
            logger.info(f"Created {len(h4_with_indicators)} periods of 4H data for {symbol}")
            return h4_with_indicators
            
        except Exception as e:
            logger.error(f"Error creating 4H data for {symbol}: {e}")
            return None
    
    def calculate_indicators_by_timeframe(self, data: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        Calculate technical indicators appropriate for each timeframe
        
        Args:
            data: OHLCV DataFrame
            timeframe: Timeframe string
        
        Returns:
            DataFrame with added indicator columns
        """
        try:
            df = data.copy()
            
            # Common periods for all timeframes
            rsi_period = 14
            macd_fast = 12
            macd_slow = 26
            macd_signal = 9
            ma_period = 20
            
            # Adjust periods based on timeframe for some indicators
            if timeframe in ["1m", "5m"]:
                # Faster settings for very short timeframes
                rsi_period = 10
                ma_period = 10
            elif timeframe in ["1d", "1wk"]:
                # Can use standard or slightly longer periods
                ma_period = 20
            
            # RSI
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # MACD
            exp1 = df['Close'].ewm(span=macd_fast).mean()
            exp2 = df['Close'].ewm(span=macd_slow).mean()
            df['MACD'] = exp1 - exp2
            df['MACD_Signal'] = df['MACD'].ewm(span=macd_signal).mean()
            df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
            
            # Moving Averages
            df['MA_20'] = df['Close'].rolling(window=ma_period).mean()
            df['MA_50'] = df['Close'].rolling(window=min(50, len(df)//2)).mean()
            df['MA_200'] = df['Close'].rolling(window=min(200, len(df)//4)).mean()
            
            # EMA for faster timeframes
            df['EMA_8'] = df['Close'].ewm(span=8).mean()
            df['EMA_21'] = df['Close'].ewm(span=21).mean()
            
            # Bollinger Bands
            bb_period = ma_period
            bb_std = 2
            df['BB_Middle'] = df['Close'].rolling(window=bb_period).mean()
            bb_std_dev = df['Close'].rolling(window=bb_period).std()
            df['BB_Upper'] = df['BB_Middle'] + (bb_std_dev * bb_std)
            df['BB_Lower'] = df['BB_Middle'] - (bb_std_dev * bb_std)
            
            # ATR (Average True Range) for volatility
            high_low = df['High'] - df['Low']
            high_close = np.abs(df['High'] - df['Close'].shift())
            low_close = np.abs(df['Low'] - df['Close'].shift())
            ranges = pd.DataFrame([high_low, high_close, low_close]).max()
            df['ATR'] = ranges.rolling(14).mean()
            
            # Volume indicators
            df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
            df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
            
            # Price position relative to BB
            df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
            
            # Volatility percentage
            df['Volatility_7d'] = df['Close'].pct_change().rolling(window=min(7, len(df)//2)).std() * np.sqrt(252)
            
            logger.debug(f"Calculated indicators for {timeframe} data: {len(df)} periods")
            return df
            
        except Exception as e:
            logger.error(f"Error calculating indicators for {timeframe}: {e}")
            return data  # Return original data if indicator calculation fails
    
    def _is_cached_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.cache:
            return False
        
        age = time.time() - self.cache[cache_key]['timestamp']
        return age < self.cache_duration
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear()
        logger.info("Data cache cleared")
    
    def get_multiple_timeframes(self, symbol: str, timeframes: List[str], is_crypto: bool = False) -> Dict[str, pd.DataFrame]:
        """
        Get data for multiple timeframes at once
        
        Args:
            symbol: Symbol to fetch
            timeframes: List of timeframes to fetch
            is_crypto: Whether this is crypto data
        
        Returns:
            Dictionary mapping timeframe to DataFrame
        """
        results = {}
        
        for tf in timeframes:
            try:
                if is_crypto:
                    data = self.get_crypto_data(symbol, tf)
                else:
                    data = self.get_stock_data(symbol, tf)
                
                if data is not None:
                    results[tf] = data
                else:
                    logger.warning(f"No data retrieved for {symbol} {tf}")
                    
            except Exception as e:
                logger.error(f"Error fetching {symbol} {tf}: {e}")
        
        return results