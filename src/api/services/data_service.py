"""
Data service for fetching and updating stock and crypto data
"""

import yfinance as yf
import requests
import logging
import asyncio
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from ..database.database import db_manager
from .scoring_service import ScoringService
from .cache_service import cache_service
from ..middleware.rate_limiter import rate_limiter

# Import expanded watchlists
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
# Import from archive directory
archive_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'archive', 'legacy-traders')
sys.path.append(archive_path)
from expanded_crypto_watchlist import get_diversified_portfolio, get_symbols_only
from optimized_trading_strategy import ExpandedTradingConfig

logger = logging.getLogger(__name__)

class DataService:
    """Service for fetching and updating stock and crypto data"""
    
    def __init__(self):
        self.scoring_service = ScoringService()
        
        # Initialize expanded trading configuration
        try:
            self.trading_config = ExpandedTradingConfig()
            self.default_stocks = self.trading_config.all_stock_symbols
            self.default_cryptos = self.trading_config.crypto_symbols
            logger.info(f"Loaded expanded watchlists: {len(self.default_stocks)} stocks, {len(self.default_cryptos)} cryptos")
        except Exception as e:
            logger.warning(f"Could not load expanded watchlists, using fallback: {e}")
            # Fallback to original small lists if expanded config fails
            self.default_stocks = [
                "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX",
                "AMD", "INTC", "CRM", "ORCL", "ADBE", "NOW", "SNOW", "PLTR",
                "BABA", "DIS", "V", "MA", "JPM", "BAC", "WMT", "HD", "UNH"
            ]
            self.default_cryptos = [
                "BTC-USD", "ETH-USD", "BNB-USD", "ADA-USD", "XRP-USD", "SOL-USD",
                "DOGE-USD", "DOT-USD", "AVAX-USD", "LINK-USD", "LTC-USD", "BCH-USD"
            ]
        
        # For performance, limit concurrent updates to avoid overwhelming APIs
        self.batch_size = 50  # Process 50 symbols at a time
        self.max_concurrent_stocks = 300  # Increased limit for full watchlist coverage
        self.max_concurrent_cryptos = 30   # Limit cryptos for API safety
    
    async def get_cached_stocks_data(self) -> Optional[List[Dict[str, Any]]]:
        """Get stocks data from cache"""
        return await cache_service.get("stocks:all")
    
    async def update_stocks_data(self, force_refresh: bool = False) -> None:
        """Update all stocks data from Yahoo Finance with caching"""
        # Check cache first unless forced refresh
        if not force_refresh:
            cached_data = await self.get_cached_stocks_data()
            if cached_data:
                logger.info("Using cached stocks data")
                return
        
        logger.info("Updating stocks data from external API...")
        
        try:
            stocks_data = []
            # Process in batches to avoid overwhelming the API
            stocks_to_process = self.default_stocks[:self.max_concurrent_stocks]
            
            for i in range(0, len(stocks_to_process), self.batch_size):
                batch = stocks_to_process[i:i + self.batch_size]
                logger.info(f"Processing stock batch {i//self.batch_size + 1}/{(len(stocks_to_process) + self.batch_size - 1)//self.batch_size}")
                
                for symbol in batch:
                    stock_data = await self.update_single_stock(symbol)
                    if stock_data:
                        stocks_data.append(stock_data)
                    await asyncio.sleep(0.15)  # Slightly longer rate limiting
                
                # Longer pause between batches
                if i + self.batch_size < len(stocks_to_process):
                    await asyncio.sleep(2.0)
            
            # Cache the results
            await cache_service.set("stocks:all", stocks_data, "stocks")
            logger.info(f"Cached {len(stocks_data)} stocks")
                
        except Exception as e:
            logger.error(f"Error updating stocks data: {str(e)}")
    
    async def update_single_stock(self, symbol: str) -> Dict[str, Any]:
        """Update data for a single stock with rate limiting"""
        try:
            # Rate limiting for Yahoo Finance API
            await rate_limiter.acquire("yahoo_finance")
            
            try:
                # Fetch data from Yahoo Finance with better data for 24h calculation
                ticker = yf.Ticker(symbol)
                info = ticker.info
                history = ticker.history(period="5d", interval="1d")  # 5 days of daily data
            finally:
                rate_limiter.release("yahoo_finance")
            
            if history.empty:
                logger.warning(f"No data found for stock {symbol}")
                return {}
            
            current_price = history['Close'].iloc[-1]
            prev_price = history['Close'].iloc[-2] if len(history) > 1 else current_price
            
            change_amount = current_price - prev_price
            change_percent = (change_amount / prev_price) * 100 if prev_price != 0 else 0
            
            # Calculate score
            score = self.scoring_service.calculate_stock_score({
                'symbol': symbol,
                'current_price': current_price,
                'change_percent': change_percent,
                'volume': history['Volume'].iloc[-1] if not history['Volume'].empty else 0,
                'market_cap': info.get('marketCap', 0),
                'sector': info.get('sector', 'Unknown')
            })
            
            # Prepare stock data
            stock_data = {
                'id': str(uuid.uuid4()),
                'symbol': symbol,
                'name': info.get('longName', symbol),
                'current_price': float(current_price),
                'score': score,
                'change_amount': float(change_amount),
                'change_percent': float(change_percent),
                'volume': int(history['Volume'].iloc[-1]) if not history['Volume'].empty else 0,
                'market_cap': info.get('marketCap', 0),
                'sector': info.get('sector', 'Unknown')
            }
            
            # Update database
            self._upsert_stock(stock_data)
            
            logger.debug(f"Updated stock data for {symbol}")
            return stock_data
            
        except Exception as e:
            logger.error(f"Error updating stock {symbol}: {str(e)}")
            return {}
    
    async def get_cached_cryptos_data(self) -> Optional[List[Dict[str, Any]]]:
        """Get cryptos data from cache"""
        return await cache_service.get("cryptos:all")
    
    async def update_cryptos_data(self, force_refresh: bool = False) -> None:
        """Update all cryptos data from Yahoo Finance with caching"""
        # Check cache first unless forced refresh
        if not force_refresh:
            cached_data = await self.get_cached_cryptos_data()
            if cached_data:
                logger.info("Using cached cryptos data")
                return
        
        logger.info("Updating cryptos data from external API...")
        
        try:
            cryptos_data = []
            # Process in batches to avoid overwhelming the API
            cryptos_to_process = self.default_cryptos[:self.max_concurrent_cryptos]
            
            for i in range(0, len(cryptos_to_process), min(self.batch_size, 20)):  # Smaller batches for crypto
                batch = cryptos_to_process[i:i + min(self.batch_size, 20)]
                logger.info(f"Processing crypto batch {i//20 + 1}/{(len(cryptos_to_process) + 19)//20}")
                
                for symbol in batch:
                    crypto_symbol = symbol.replace('-USD', '') if symbol.endswith('-USD') else symbol
                    crypto_data = await self.update_single_crypto(crypto_symbol)
                    if crypto_data:
                        cryptos_data.append(crypto_data)
                    await asyncio.sleep(0.2)  # Longer rate limiting for crypto
                
                # Longer pause between batches
                if i + 20 < len(cryptos_to_process):
                    await asyncio.sleep(3.0)
            
            # Cache the results  
            await cache_service.set("cryptos:all", cryptos_data, "cryptos")
            logger.info(f"Cached {len(cryptos_data)} cryptos")
                
        except Exception as e:
            logger.error(f"Error updating cryptos data: {str(e)}")
    
    async def update_single_crypto(self, symbol: str) -> Dict[str, Any]:
        """Update data for a single crypto with rate limiting"""
        try:
            # Rate limiting for Yahoo Finance API
            await rate_limiter.acquire("yahoo_finance")
            
            try:
                # Ensure symbol format for Yahoo Finance
                yahoo_symbol = f"{symbol}-USD" if not symbol.endswith('-USD') else symbol
                
                # Fetch data from Yahoo Finance with longer period for better 24h calculation
                ticker = yf.Ticker(yahoo_symbol)
                info = ticker.info
                history = ticker.history(period="5d", interval="1h")  # 5 days of hourly data
            finally:
                rate_limiter.release("yahoo_finance")
            
            if history.empty:
                logger.warning(f"No data found for crypto {symbol}")
                return {}
            
            current_price = history['Close'].iloc[-1]
            
            # Calculate proper 24h change
            change_amount, change_percent = self._calculate_24h_change(history)
            
            logger.debug(f"Crypto {symbol}: Current=${current_price:.4f}, Change={change_percent:.2f}%, Data points={len(history)}")
            
            # Calculate score
            score = self.scoring_service.calculate_crypto_score({
                'symbol': symbol,
                'current_price': current_price,
                'change_percent': change_percent,
                'volume': history['Volume'].iloc[-1] if not history['Volume'].empty else 0,
                'market_cap': info.get('marketCap', 0)
            })
            
            # Prepare crypto data
            crypto_data = {
                'id': str(uuid.uuid4()),
                'symbol': yahoo_symbol,  # Store full symbol with -USD for correct price fetching
                'name': info.get('longName', symbol.replace('-USD', '')),
                'current_price': float(current_price),
                'score': score,
                'change_amount': float(change_amount),
                'change_percent': float(change_percent),
                'volume': float(history['Volume'].iloc[-1]) if not history['Volume'].empty else 0,
                'market_cap': info.get('marketCap', 0)
            }
            
            # Update database
            self._upsert_crypto(crypto_data)
            
            logger.debug(f"Updated crypto data for {symbol}")
            return crypto_data
            
        except Exception as e:
            logger.error(f"Error updating crypto {symbol}: {str(e)}")
            return {}
    
    async def get_current_price(self, symbol: str, asset_type: str) -> Optional[float]:
        """Get current price for an asset"""
        try:
            if asset_type == 'stock':
                ticker = yf.Ticker(symbol)
            else:  # crypto
                yahoo_symbol = f"{symbol}-USD" if not symbol.endswith('-USD') else symbol
                ticker = yf.Ticker(yahoo_symbol)
            
            history = ticker.history(period="1d")
            if not history.empty:
                return float(history['Close'].iloc[-1])
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {str(e)}")
            return None
    
    async def update_positions_prices(self) -> None:
        """Update current prices for all positions"""
        try:
            # Get all positions including position_side
            positions = db_manager.execute_query(
                "SELECT id, symbol, type, quantity, entry_price, position_side FROM positions"
            )
            
            for position in positions:
                current_price = await self.get_current_price(position['symbol'], position['type'])
                
                if current_price:
                    # Calculate new values
                    quantity = position['quantity']
                    entry_price = position['entry_price']
                    position_side = position.get('position_side', 'LONG')
                    value = quantity * current_price
                    
                    # Calculate P&L based on position side
                    if position_side == 'SHORT':
                        # SHORT: profit when price goes down
                        pnl = (entry_price - current_price) * quantity
                    else:
                        # LONG: profit when price goes up
                        pnl = (current_price - entry_price) * quantity
                        
                    pnl_percent = (pnl / (entry_price * quantity)) * 100 if entry_price > 0 else 0
                    
                    # Update position
                    db_manager.execute_update(
                        """UPDATE positions 
                           SET current_price = ?, value = ?, pnl = ?, pnl_percent = ?, updated_at = CURRENT_TIMESTAMP
                           WHERE id = ?""",
                        (current_price, value, pnl, pnl_percent, position['id'])
                    )
            
            logger.info(f"Updated prices for {len(positions)} positions")
            
        except Exception as e:
            logger.error(f"Error updating positions prices: {str(e)}")
    
    def _upsert_stock(self, stock_data: Dict[str, Any]) -> None:
        """Insert or update stock data"""
        try:
            # Check if stock exists
            existing = db_manager.execute_query(
                "SELECT id FROM stocks WHERE symbol = ?",
                (stock_data['symbol'],)
            )
            
            if existing:
                # Update existing
                db_manager.execute_update(
                    """UPDATE stocks SET 
                       name = ?, current_price = ?, score = ?, change_amount = ?, 
                       change_percent = ?, volume = ?, market_cap = ?, sector = ?,
                       updated_at = CURRENT_TIMESTAMP
                       WHERE symbol = ?""",
                    (
                        stock_data['name'], stock_data['current_price'], stock_data['score'],
                        stock_data['change_amount'], stock_data['change_percent'],
                        stock_data['volume'], stock_data['market_cap'], stock_data['sector'],
                        stock_data['symbol']
                    )
                )
            else:
                # Insert new
                db_manager.execute_insert(
                    """INSERT INTO stocks 
                       (id, symbol, name, current_price, score, change_amount, 
                        change_percent, volume, market_cap, sector)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        stock_data['id'], stock_data['symbol'], stock_data['name'],
                        stock_data['current_price'], stock_data['score'],
                        stock_data['change_amount'], stock_data['change_percent'],
                        stock_data['volume'], stock_data['market_cap'], stock_data['sector']
                    )
                )
                
        except Exception as e:
            logger.error(f"Error upserting stock {stock_data['symbol']}: {str(e)}")
    
    def _calculate_24h_change(self, history) -> tuple:
        """Calculate 24-hour change from price history"""
        try:
            if len(history) < 2:
                return 0.0, 0.0
            
            current_price = history['Close'].iloc[-1]
            
            # Try to get price from 24 hours ago
            # Yahoo Finance usually gives us hourly data for recent periods
            if len(history) >= 24:
                # If we have hourly data, get price from 24 hours ago
                price_24h_ago = history['Close'].iloc[-24]
            else:
                # Fallback to previous available data point
                price_24h_ago = history['Close'].iloc[0]
            
            change_amount = current_price - price_24h_ago
            change_percent = (change_amount / price_24h_ago) * 100 if price_24h_ago != 0 else 0.0
            
            logger.debug(f"24h change: ${change_amount:.4f} ({change_percent:.2f}%)")
            return float(change_amount), float(change_percent)
            
        except Exception as e:
            logger.error(f"Error calculating 24h change: {str(e)}")
            return 0.0, 0.0
    
    def _upsert_crypto(self, crypto_data: Dict[str, Any]) -> None:
        """Insert or update crypto data"""
        try:
            # Check if crypto exists
            existing = db_manager.execute_query(
                "SELECT id FROM cryptos WHERE symbol = ?",
                (crypto_data['symbol'],)
            )
            
            if existing:
                # Update existing
                db_manager.execute_update(
                    """UPDATE cryptos SET 
                       name = ?, current_price = ?, score = ?, change_amount = ?, 
                       change_percent = ?, volume = ?, market_cap = ?,
                       updated_at = CURRENT_TIMESTAMP
                       WHERE symbol = ?""",
                    (
                        crypto_data['name'], crypto_data['current_price'], crypto_data['score'],
                        crypto_data['change_amount'], crypto_data['change_percent'],
                        crypto_data['volume'], crypto_data['market_cap'],
                        crypto_data['symbol']
                    )
                )
            else:
                # Insert new
                db_manager.execute_insert(
                    """INSERT INTO cryptos 
                       (id, symbol, name, current_price, score, change_amount, 
                        change_percent, volume, market_cap)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        crypto_data['id'], crypto_data['symbol'], crypto_data['name'],
                        crypto_data['current_price'], crypto_data['score'],
                        crypto_data['change_amount'], crypto_data['change_percent'],
                        crypto_data['volume'], crypto_data['market_cap']
                    )
                )
                
        except Exception as e:
            logger.error(f"Error upserting crypto {crypto_data['symbol']}: {str(e)}")
    
    async def add_new_symbol(self, symbol: str, asset_type: str) -> bool:
        """
        Add a new symbol to the trading watchlists for autotrader to consider
        
        Args:
            symbol: Symbol to add (e.g., 'AAPL', 'BTC-USD')
            asset_type: 'stock' or 'crypto'
        
        Returns:
            bool: Success status
        """
        try:
            symbol = symbol.upper().strip()
            
            if asset_type == 'stock':
                # Add to stock watchlist if not already present
                if symbol not in self.default_stocks:
                    self.default_stocks.append(symbol)
                    logger.info(f"Added {symbol} to stock watchlist (total: {len(self.default_stocks)})")
                
                # Also add to trading config if available
                if hasattr(self, 'trading_config') and self.trading_config:
                    if symbol not in self.trading_config.all_stock_symbols:
                        self.trading_config.all_stock_symbols.append(symbol)
                
            elif asset_type == 'crypto':
                # Ensure proper format for crypto
                if not symbol.endswith('-USD'):
                    symbol = f"{symbol}-USD"
                
                # Add to crypto watchlist if not already present
                if symbol not in self.default_cryptos:
                    self.default_cryptos.append(symbol)
                    logger.info(f"Added {symbol} to crypto watchlist (total: {len(self.default_cryptos)})")
                
                # Also add to trading config if available
                if hasattr(self, 'trading_config') and self.trading_config:
                    if symbol not in self.trading_config.crypto_symbols:
                        self.trading_config.crypto_symbols.append(symbol)
            
            else:
                logger.error(f"Invalid asset_type: {asset_type}")
                return False
            
            # Clear relevant cache to force refresh with new symbol
            await self._clear_symbol_cache(asset_type)
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding symbol {symbol} to watchlists: {e}")
            return False
    
    async def _clear_symbol_cache(self, asset_type: str):
        """Clear cache for the specified asset type to include new symbols"""
        try:
            if asset_type == 'stock':
                await cache_service.delete("stocks:all")
                logger.info("Cleared stocks cache")
            elif asset_type == 'crypto':
                await cache_service.delete("cryptos:all")
                logger.info("Cleared cryptos cache")
        except Exception as e:
            logger.error(f"Error clearing cache for {asset_type}: {e}")
    
    def get_current_watchlists(self) -> Dict[str, List[str]]:
        """
        Get current watchlists for debugging/info purposes
        
        Returns:
            Dict with current stock and crypto watchlists
        """
        return {
            'stocks': self.default_stocks.copy(),
            'cryptos': self.default_cryptos.copy(),
            'stock_count': len(self.default_stocks),
            'crypto_count': len(self.default_cryptos)
        }