"""
Service for adding symbols to watchlist on-demand when creating manual positions
"""

import logging
import yfinance as yf
from datetime import datetime
from typing import Optional, Dict, Any

from ..database.database import db_manager
from .scoring_service import ScoringService

logger = logging.getLogger(__name__)

class SymbolOnDemandService:
    """Service to add new symbols to watchlist automatically"""
    
    def __init__(self):
        self.scoring_service = ScoringService()
    
    async def ensure_symbol_in_watchlist(self, symbol: str, asset_type: str = "stock") -> bool:
        """
        Ensures a symbol exists in the appropriate watchlist table
        If not found, fetches data and adds it with a calculated score
        """
        try:
            symbol = symbol.upper()
            
            # Check if symbol already exists
            if asset_type == "stock":
                existing = db_manager.execute_query(
                    "SELECT symbol FROM stocks WHERE symbol = ?", (symbol,)
                )
            else:  # crypto
                existing = db_manager.execute_query(
                    "SELECT symbol FROM cryptos WHERE symbol = ?", (symbol,)
                )
            
            if existing:
                logger.debug(f"Symbol {symbol} already exists in {asset_type} watchlist")
                return True
            
            # Symbol doesn't exist, fetch data and add it
            logger.info(f"Adding new symbol {symbol} to {asset_type} watchlist on-demand")
            
            if asset_type == "stock":
                return await self._add_stock_symbol(symbol)
            else:
                return await self._add_crypto_symbol(symbol)
                
        except Exception as e:
            logger.error(f"Error ensuring symbol {symbol} in watchlist: {e}")
            return False
    
    async def _add_stock_symbol(self, symbol: str) -> bool:
        """Add a new stock symbol to the watchlist"""
        try:
            # Fetch data from Yahoo Finance
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="5d")
            
            if hist.empty:
                logger.warning(f"No price data found for stock {symbol}")
                return False
            
            # Get current price and calculate change
            current_price = hist['Close'].iloc[-1]
            previous_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            change = current_price - previous_price
            change_percent = (change / previous_price) * 100 if previous_price > 0 else 0
            
            # Get company info
            name = info.get('longName', symbol)
            sector = info.get('sector', 'Unknown')
            market_cap = info.get('marketCap', 0)
            volume = hist['Volume'].iloc[-1] if 'Volume' in hist.columns else 0
            
            # Calculate initial score using scoring service
            stock_data = {
                'symbol': symbol,
                'current_price': float(current_price),
                'change_percent': float(change_percent),
                'volume': int(volume),
                'market_cap': market_cap,
                'sector': sector
            }
            
            # Calculate score
            score = self.scoring_service.calculate_stock_score(stock_data)
            
            # Insert into stocks table (using correct column names)
            insert_query = """
                INSERT INTO stocks 
                (id, symbol, name, current_price, change_amount, change_percent, volume, 
                 market_cap, sector, score, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            db_manager.execute_insert(insert_query, (
                symbol,  # Use symbol as id
                symbol,
                name,
                float(current_price),
                float(change),
                float(change_percent),
                int(volume),
                market_cap,
                sector,
                float(score),
                datetime.now().isoformat()
            ))
            
            logger.info(f"Successfully added stock {symbol} with score {score:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding stock symbol {symbol}: {e}")
            return False
    
    async def _add_crypto_symbol(self, symbol: str) -> bool:
        """Add a new crypto symbol to the watchlist"""
        try:
            # Ensure symbol has -USD suffix for crypto
            if not symbol.endswith('-USD'):
                symbol = f"{symbol}-USD"
            
            # Fetch data from Yahoo Finance
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            
            if hist.empty:
                logger.warning(f"No price data found for crypto {symbol}")
                return False
            
            # Get current price and calculate change
            current_price = hist['Close'].iloc[-1]
            previous_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            change = current_price - previous_price
            change_percent = (change / previous_price) * 100 if previous_price > 0 else 0
            
            # Get crypto info
            info = ticker.info
            name = info.get('longName', symbol.replace('-USD', ''))
            volume = hist['Volume'].iloc[-1] if 'Volume' in hist.columns else 0
            market_cap = info.get('marketCap', 0)
            
            # Calculate score for crypto
            crypto_data = {
                'symbol': symbol,
                'current_price': float(current_price),
                'change_percent': float(change_percent),
                'volume': int(volume),
                'market_cap': market_cap
            }
            
            # Use a simplified scoring for crypto (can be enhanced later)
            score = self._calculate_crypto_score(crypto_data)
            
            # Insert into cryptos table
            insert_query = """
                INSERT INTO cryptos 
                (symbol, name, current_price, change, change_percent, volume, 
                 market_cap, score, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            db_manager.execute_insert(insert_query, (
                symbol,
                name,
                float(current_price),
                float(change),
                float(change_percent),
                int(volume),
                market_cap,
                float(score),
                datetime.now().isoformat()
            ))
            
            logger.info(f"Successfully added crypto {symbol} with score {score:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding crypto symbol {symbol}: {e}")
            return False
    
    def _calculate_crypto_score(self, crypto_data: Dict[str, Any]) -> float:
        """Calculate a basic score for crypto (simplified version)"""
        try:
            change_percent = crypto_data.get('change_percent', 0)
            volume = crypto_data.get('volume', 0)
            
            # Basic scoring logic for crypto
            score = 5.0  # Neutral baseline
            
            # Adjust based on recent performance
            if change_percent > 10:
                score += 2.0  # Strong positive momentum
            elif change_percent > 5:
                score += 1.0  # Moderate positive momentum
            elif change_percent < -10:
                score -= 2.0  # Strong negative momentum
            elif change_percent < -5:
                score -= 1.0  # Moderate negative momentum
            
            # Adjust based on volume (higher volume = more reliable)
            if volume > 100000000:  # High volume
                score += 0.5
            elif volume < 10000000:  # Low volume
                score -= 0.5
            
            # Ensure score is within reasonable bounds
            score = max(0.0, min(10.0, score))
            
            return score
            
        except Exception as e:
            logger.error(f"Error calculating crypto score: {e}")
            return 5.0  # Default neutral score

# Singleton instance
symbol_on_demand_service = SymbolOnDemandService()