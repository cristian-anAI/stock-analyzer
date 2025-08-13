"""
Diagnostics endpoints for debugging data issues
"""

from fastapi import APIRouter, HTTPException, Path
from typing import Dict, Any
import logging
import yfinance as yf

from ..middleware.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/diagnostics/crypto/{symbol}")
async def diagnose_crypto(symbol: str = Path(..., description="Crypto symbol to diagnose")):
    """Diagnose crypto data issues"""
    try:
        await rate_limiter.acquire("yahoo_finance")
        
        try:
            # Ensure symbol format for Yahoo Finance
            yahoo_symbol = f"{symbol}-USD" if not symbol.endswith('-USD') else symbol
            
            # Fetch data from Yahoo Finance
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info
            history_hourly = ticker.history(period="5d", interval="1h")
            history_daily = ticker.history(period="30d", interval="1d")
            
        finally:
            rate_limiter.release("yahoo_finance")
        
        # Current price
        current_price = history_hourly['Close'].iloc[-1] if not history_hourly.empty else None
        
        # Calculate different change periods
        changes = {}
        
        if not history_hourly.empty and len(history_hourly) > 1:
            # 1 hour change
            if len(history_hourly) >= 2:
                price_1h_ago = history_hourly['Close'].iloc[-2]
                changes['1h'] = {
                    'amount': current_price - price_1h_ago,
                    'percent': ((current_price - price_1h_ago) / price_1h_ago) * 100
                }
            
            # 24 hour change
            if len(history_hourly) >= 24:
                price_24h_ago = history_hourly['Close'].iloc[-24]
                changes['24h'] = {
                    'amount': current_price - price_24h_ago,
                    'percent': ((current_price - price_24h_ago) / price_24h_ago) * 100
                }
        
        if not history_daily.empty and len(history_daily) > 1:
            # 7 day change
            if len(history_daily) >= 7:
                price_7d_ago = history_daily['Close'].iloc[-7]
                changes['7d'] = {
                    'amount': current_price - price_7d_ago,
                    'percent': ((current_price - price_7d_ago) / price_7d_ago) * 100
                }
        
        return {
            "symbol": symbol,
            "yahoo_symbol": yahoo_symbol,
            "current_price": float(current_price) if current_price else None,
            "info": {
                "name": info.get('longName', 'N/A'),
                "market_cap": info.get('marketCap', 'N/A'),
                "volume": info.get('volume', 'N/A')
            },
            "data_availability": {
                "hourly_data_points": len(history_hourly),
                "daily_data_points": len(history_daily),
                "hourly_period": f"{len(history_hourly)} hours" if not history_hourly.empty else "No data",
                "daily_period": f"{len(history_daily)} days" if not history_daily.empty else "No data"
            },
            "changes": changes,
            "raw_data_sample": {
                "latest_hourly": history_hourly.tail(3).to_dict() if not history_hourly.empty else {},
                "latest_daily": history_daily.tail(3).to_dict() if not history_daily.empty else {}
            }
        }
        
    except Exception as e:
        logger.error(f"Error diagnosing crypto {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error diagnosing crypto: {str(e)}")

@router.get("/diagnostics/stock/{symbol}")
async def diagnose_stock(symbol: str = Path(..., description="Stock symbol to diagnose")):
    """Diagnose stock data issues"""
    try:
        await rate_limiter.acquire("yahoo_finance")
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            history = ticker.history(period="5d", interval="1d")
            
        finally:
            rate_limiter.release("yahoo_finance")
        
        current_price = history['Close'].iloc[-1] if not history.empty else None
        
        changes = {}
        if not history.empty and len(history) > 1:
            # 1 day change
            price_1d_ago = history['Close'].iloc[-2]
            changes['1d'] = {
                'amount': current_price - price_1d_ago,
                'percent': ((current_price - price_1d_ago) / price_1d_ago) * 100
            }
        
        return {
            "symbol": symbol,
            "current_price": float(current_price) if current_price else None,
            "info": {
                "name": info.get('longName', 'N/A'),
                "sector": info.get('sector', 'N/A'),
                "market_cap": info.get('marketCap', 'N/A'),
                "volume": info.get('volume', 'N/A')
            },
            "data_availability": {
                "data_points": len(history),
                "period": f"{len(history)} days" if not history.empty else "No data"
            },
            "changes": changes,
            "raw_data_sample": history.tail(3).to_dict() if not history.empty else {}
        }
        
    except Exception as e:
        logger.error(f"Error diagnosing stock {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error diagnosing stock: {str(e)}")