"""
Stocks API endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Response
from typing import List, Optional
import logging
import uuid
import hashlib
import json

from ..models.schemas import Stock, ErrorResponse
from ..database.database import db_manager
from ..services.data_service import DataService
from ..services.scoring_service import ScoringService

logger = logging.getLogger(__name__)

router = APIRouter()

def get_data_service():
    return DataService()

def get_scoring_service():
    return ScoringService()

@router.get("/stocks", response_model=List[Stock])
async def get_stocks(
    response: Response,
    sort: Optional[str] = Query(None, description="Sort by 'score' or other fields"),
    limit: Optional[int] = Query(500, ge=1, le=1000, description="Number of stocks to return"),
    data_service: DataService = Depends(get_data_service),
    scoring_service: ScoringService = Depends(get_scoring_service)
):
    """
    Get all stocks with optional sorting by score
    """
    try:
        # First, ensure we have fresh data
        await data_service.update_stocks_data()
        
        # Build query
        base_query = """
            SELECT id, symbol, name, current_price, score, 
                   change_amount as change, change_percent, volume, 
                   market_cap, sector
            FROM stocks
        """
        
        # Add sorting
        if sort == "score":
            query = base_query + " ORDER BY score DESC, symbol ASC"
        else:
            query = base_query + " ORDER BY symbol ASC"
        
        # Add limit
        query += f" LIMIT {limit}"
        
        stocks_data = db_manager.execute_query(query)
        
        # Convert to Stock models
        stocks = []
        for stock_data in stocks_data:
            stock = Stock(
                id=stock_data["id"],
                symbol=stock_data["symbol"],
                name=stock_data["name"],
                current_price=stock_data["current_price"],
                score=stock_data["score"],
                change=stock_data["change"],
                change_percent=stock_data["change_percent"],
                volume=stock_data["volume"],
                market_cap=stock_data["market_cap"],
                sector=stock_data["sector"]
            )
            stocks.append(stock)
        
        # Add cache headers
        response.headers["Cache-Control"] = "public, max-age=300"  # 5 minutes
        
        # Generate ETag for caching
        etag = hashlib.md5(json.dumps([stock.dict() for stock in stocks], default=str).encode()).hexdigest()
        response.headers["ETag"] = f'"{etag}"'
        
        logger.info(f"Retrieved {len(stocks)} stocks (sort={sort})")
        return stocks
        
    except Exception as e:
        logger.error(f"Error retrieving stocks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving stocks: {str(e)}")

@router.get("/stocks/{symbol}", response_model=Stock)
async def get_stock_by_symbol(
    symbol: str,
    data_service: DataService = Depends(get_data_service)
):
    """
    Get specific stock by symbol
    """
    try:
        # Update data for this specific stock
        await data_service.update_single_stock(symbol.upper())
        
        query = """
            SELECT id, symbol, name, current_price, score, 
                   change_amount as change, change_percent, volume, 
                   market_cap, sector
            FROM stocks 
            WHERE UPPER(symbol) = UPPER(?)
        """
        
        stocks_data = db_manager.execute_query(query, (symbol.upper(),))
        
        if not stocks_data:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
        
        stock_data = stocks_data[0]
        stock = Stock(
            id=stock_data["id"],
            symbol=stock_data["symbol"],
            name=stock_data["name"],
            current_price=stock_data["current_price"],
            score=stock_data["score"],
            change=stock_data["change"],
            change_percent=stock_data["change_percent"],
            volume=stock_data["volume"],
            market_cap=stock_data["market_cap"],
            sector=stock_data["sector"]
        )
        
        logger.info(f"Retrieved stock: {symbol}")
        return stock
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving stock {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving stock: {str(e)}")

@router.post("/stocks/refresh")
async def refresh_stocks_data(
    data_service: DataService = Depends(get_data_service)
):
    """
    Manually refresh all stocks data
    """
    try:
        await data_service.update_stocks_data()
        return {"message": "Stocks data refreshed successfully"}
        
    except Exception as e:
        logger.error(f"Error refreshing stocks data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error refreshing data: {str(e)}")