"""
Market Status API endpoints
Provides information about market hours and trading status
"""

from fastapi import APIRouter
from typing import Dict, List
import logging
from datetime import datetime

from ..services.market_hours_service import market_hours_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/market-status")
async def get_all_market_status():
    """
    Get current status of all supported markets
    """
    try:
        current_time = datetime.now()
        market_statuses = {}
        
        # Get status for all supported markets
        for exchange in market_hours_service.markets.keys():
            market_statuses[exchange] = market_hours_service.get_market_status(
                exchange, current_time
            )
        
        # Get list of currently open markets
        open_markets = market_hours_service.get_all_open_markets(current_time)
        
        return {
            "timestamp": current_time.isoformat(),
            "open_markets": open_markets,
            "markets": market_statuses,
            "summary": {
                "total_markets": len(market_statuses),
                "open_count": len(open_markets),
                "closed_count": len(market_statuses) - len(open_markets)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting market status: {str(e)}")
        return {"error": f"Error getting market status: {str(e)}"}

@router.get("/market-status/{exchange}")
async def get_market_status(exchange: str):
    """
    Get status for a specific market/exchange
    """
    try:
        current_time = datetime.now()
        status = market_hours_service.get_market_status(exchange, current_time)
        
        return {
            "timestamp": current_time.isoformat(),
            "market": status
        }
        
    except Exception as e:
        logger.error(f"Error getting status for market {exchange}: {str(e)}")
        return {"error": f"Error getting market status: {str(e)}"}

@router.get("/symbol-market-status/{symbol}")
async def get_symbol_market_status(symbol: str):
    """
    Get market status for a specific stock symbol
    """
    try:
        current_time = datetime.now()
        exchange = market_hours_service.get_exchange_for_symbol(symbol)
        is_open = market_hours_service.is_stock_market_open(symbol, current_time)
        market_status = market_hours_service.get_market_status(exchange, current_time)
        
        return {
            "timestamp": current_time.isoformat(),
            "symbol": symbol,
            "exchange": exchange,
            "is_market_open": is_open,
            "market_details": market_status
        }
        
    except Exception as e:
        logger.error(f"Error getting market status for symbol {symbol}: {str(e)}")
        return {"error": f"Error getting market status: {str(e)}"}

@router.get("/trading-optimization-info")
async def get_trading_optimization_info():
    """
    Get information about current trading optimization based on market hours
    """
    try:
        current_time = datetime.now()
        
        # Sample some common symbols to show optimization
        sample_symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA", 
                         "VOD.L", "BMW.F", "7203.T", "BHP.AX"]
        
        symbols_to_update, symbols_skipped = market_hours_service.should_update_stocks(
            sample_symbols, current_time
        )
        
        # Get detailed breakdown by exchange
        exchange_breakdown = {}
        for symbol in sample_symbols:
            exchange = market_hours_service.get_exchange_for_symbol(symbol)
            is_open = market_hours_service.is_stock_market_open(symbol, current_time)
            
            if exchange not in exchange_breakdown:
                exchange_breakdown[exchange] = {
                    "symbols": [],
                    "is_open": is_open,
                    "symbols_count": 0,
                    "status": "open" if is_open else "closed"
                }
            
            exchange_breakdown[exchange]["symbols"].append(symbol)
            exchange_breakdown[exchange]["symbols_count"] += 1
        
        return {
            "timestamp": current_time.isoformat(),
            "optimization_summary": {
                "total_symbols_sample": len(sample_symbols),
                "symbols_to_update": len(symbols_to_update),
                "symbols_skipped": len(symbols_skipped),
                "api_calls_saved": len(symbols_skipped),
                "efficiency_percent": round((len(symbols_skipped) / len(sample_symbols)) * 100, 1)
            },
            "symbols_to_update": symbols_to_update,
            "symbols_skipped": symbols_skipped,
            "exchange_breakdown": exchange_breakdown
        }
        
    except Exception as e:
        logger.error(f"Error getting trading optimization info: {str(e)}")
        return {"error": f"Error getting optimization info: {str(e)}"}

@router.post("/add-symbol-mapping")
async def add_custom_symbol_mapping(symbol: str, exchange: str):
    """
    Add a custom symbol to exchange mapping for better market hours detection
    """
    try:
        market_hours_service.add_custom_symbol_mapping(symbol, exchange)
        
        return {
            "message": f"Successfully mapped {symbol} to {exchange}",
            "symbol": symbol,
            "exchange": exchange
        }
        
    except Exception as e:
        logger.error(f"Error adding symbol mapping {symbol} -> {exchange}: {str(e)}")
        return {"error": f"Error adding mapping: {str(e)}"}