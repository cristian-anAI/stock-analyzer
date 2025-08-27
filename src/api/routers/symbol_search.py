"""
Symbol Search and Registration API
Allows frontend to search for new symbols and add them to the trading system
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import yfinance as yf
import logging
from datetime import datetime

from ..models.schemas import SuccessResponse
from ..services.data_service import DataService

logger = logging.getLogger(__name__)

router = APIRouter()

class SymbolSearchRequest(BaseModel):
    symbol: str
    asset_type: str  # 'stock' or 'crypto'

class SymbolSearchResponse(BaseModel):
    symbol: str
    name: str
    asset_type: str
    current_price: float
    currency: str
    market_cap: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    exchange: Optional[str] = None
    is_valid: bool
    message: str

def get_data_service():
    return DataService()

@router.post("/search-symbol", response_model=SymbolSearchResponse)
async def search_and_validate_symbol(
    request: SymbolSearchRequest,
    data_service: DataService = Depends(get_data_service)
):
    """
    Search for a symbol and validate if it exists and can be traded
    If valid, adds it to the appropriate trading list for autotrader
    """
    try:
        symbol = request.symbol.upper().strip()
        asset_type = request.asset_type.lower()
        
        if asset_type not in ['stock', 'crypto']:
            raise HTTPException(status_code=400, detail="asset_type must be 'stock' or 'crypto'")
        
        logger.info(f"Searching for symbol: {symbol} (type: {asset_type})")
        
        # For crypto, ensure proper format
        if asset_type == 'crypto' and not symbol.endswith('-USD'):
            symbol = f"{symbol}-USD"
        
        # Try to fetch symbol data using yfinance
        ticker = yf.Ticker(symbol)
        
        try:
            # Get basic info
            info = ticker.info
            
            # Get recent price data to validate symbol exists
            hist = ticker.history(period="5d")
            
            if hist.empty or len(hist) == 0:
                return SymbolSearchResponse(
                    symbol=symbol,
                    name="Unknown",
                    asset_type=asset_type,
                    current_price=0.0,
                    currency="USD",
                    is_valid=False,
                    message=f"Symbol {symbol} not found or has no trading data"
                )
            
            # Get current price
            current_price = float(hist['Close'].iloc[-1])
            
            # Extract symbol information
            name = info.get('longName', info.get('shortName', symbol))
            currency = info.get('currency', 'USD')
            market_cap = info.get('marketCap')
            sector = info.get('sector')
            industry = info.get('industry')
            exchange = info.get('exchange')
            
            # Validate price is reasonable (not 0 or extremely small)
            if current_price <= 0 or (asset_type == 'crypto' and current_price < 0.00001):
                return SymbolSearchResponse(
                    symbol=symbol,
                    name=name,
                    asset_type=asset_type,
                    current_price=current_price,
                    currency=currency,
                    market_cap=market_cap,
                    sector=sector,
                    industry=industry,
                    exchange=exchange,
                    is_valid=False,
                    message=f"Symbol {symbol} has invalid price data: ${current_price}"
                )
            
            # Symbol is valid - add it to the appropriate trading list
            success = await _add_symbol_to_trading_lists(symbol, asset_type, name, data_service)
            
            if not success:
                logger.warning(f"Failed to add {symbol} to trading lists")
            
            return SymbolSearchResponse(
                symbol=symbol,
                name=name,
                asset_type=asset_type,
                current_price=current_price,
                currency=currency,
                market_cap=market_cap,
                sector=sector,
                industry=industry,
                exchange=exchange,
                is_valid=True,
                message=f"Symbol {symbol} found and added to trading system successfully"
            )
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return SymbolSearchResponse(
                symbol=symbol,
                name="Unknown",
                asset_type=asset_type,
                current_price=0.0,
                currency="USD",
                is_valid=False,
                message=f"Error validating symbol {symbol}: {str(e)}"
            )
            
    except Exception as e:
        logger.error(f"Error in search_and_validate_symbol: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching for symbol: {str(e)}")

async def _add_symbol_to_trading_lists(symbol: str, asset_type: str, name: str, data_service: DataService) -> bool:
    """
    Add the validated symbol to the appropriate trading lists
    """
    try:
        if asset_type == 'stock':
            # Add to stocks list
            await _add_to_stocks_list(symbol, name)
        elif asset_type == 'crypto':
            # Add to cryptos list
            await _add_to_cryptos_list(symbol, name)
        
        # Also update the data service cache
        await data_service.add_new_symbol(symbol, asset_type)
        
        logger.info(f"Successfully added {symbol} to {asset_type} trading lists")
        return True
        
    except Exception as e:
        logger.error(f"Error adding {symbol} to trading lists: {e}")
        return False

async def _add_to_stocks_list(symbol: str, name: str):
    """Add symbol to stocks database table"""
    from ..database.database import db_manager
    
    try:
        # Check if already exists
        existing = db_manager.execute_query(
            "SELECT symbol FROM stocks WHERE symbol = ?",
            (symbol,)
        )
        
        if existing:
            logger.info(f"Stock {symbol} already exists in database")
            return
        
        # Insert new stock
        db_manager.execute_insert(
            """INSERT INTO stocks (symbol, name, sector, market_cap, price, 
               change_percent, volume, last_updated, is_active, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (symbol, name, "Unknown", 0, 0, 0, 0, datetime.now().isoformat(), 
             True, f"Added via symbol search on {datetime.now().strftime('%Y-%m-%d')}")
        )
        
        logger.info(f"Added {symbol} to stocks table")
        
    except Exception as e:
        logger.error(f"Error adding {symbol} to stocks table: {e}")
        raise

async def _add_to_cryptos_list(symbol: str, name: str):
    """Add symbol to cryptos database table"""
    from ..database.database import db_manager
    
    try:
        # Check if already exists
        existing = db_manager.execute_query(
            "SELECT symbol FROM cryptos WHERE symbol = ?",
            (symbol,)
        )
        
        if existing:
            logger.info(f"Crypto {symbol} already exists in database")
            return
        
        # Insert new crypto
        db_manager.execute_insert(
            """INSERT INTO cryptos (symbol, name, price, change_percent, 
               market_cap, volume, last_updated, is_active, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (symbol, name, 0, 0, 0, 0, datetime.now().isoformat(), 
             True, f"Added via symbol search on {datetime.now().strftime('%Y-%m-%d')}")
        )
        
        logger.info(f"Added {symbol} to cryptos table")
        
    except Exception as e:
        logger.error(f"Error adding {symbol} to cryptos table: {e}")
        raise

@router.get("/validate-symbol/{symbol}")
async def validate_symbol_quick(symbol: str, asset_type: str = "auto"):
    """
    Quick validation of a symbol without adding it to the system
    """
    try:
        symbol = symbol.upper().strip()
        
        # Auto-detect asset type if not specified
        if asset_type == "auto":
            if symbol.endswith('-USD') or symbol in ['BTC', 'ETH', 'ADA', 'DOT', 'LINK']:
                asset_type = 'crypto'
                if not symbol.endswith('-USD'):
                    symbol = f"{symbol}-USD"
            else:
                asset_type = 'stock'
        
        # Quick check using yfinance
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        
        if hist.empty:
            return {
                "symbol": symbol,
                "is_valid": False,
                "message": f"Symbol {symbol} not found",
                "detected_type": asset_type
            }
        
        current_price = float(hist['Close'].iloc[-1])
        info = ticker.info
        name = info.get('longName', info.get('shortName', symbol))
        
        return {
            "symbol": symbol,
            "name": name,
            "current_price": current_price,
            "is_valid": True,
            "message": f"Symbol {symbol} is valid",
            "detected_type": asset_type
        }
        
    except Exception as e:
        return {
            "symbol": symbol,
            "is_valid": False,
            "message": f"Error validating {symbol}: {str(e)}",
            "detected_type": asset_type
        }