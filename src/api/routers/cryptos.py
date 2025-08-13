"""
Cryptos API endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
import logging

from ..models.schemas import Crypto, ErrorResponse
from ..database.database import db_manager
from ..services.data_service import DataService
from ..services.scoring_service import ScoringService

logger = logging.getLogger(__name__)

router = APIRouter()

def get_data_service():
    return DataService()

def get_scoring_service():
    return ScoringService()

@router.get("/cryptos", response_model=List[Crypto])
async def get_cryptos(
    sort: Optional[str] = Query(None, description="Sort by 'score' or other fields"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Number of cryptos to return"),
    data_service: DataService = Depends(get_data_service),
    scoring_service: ScoringService = Depends(get_scoring_service)
):
    """
    Get all cryptocurrencies with optional sorting by score
    """
    try:
        # First, ensure we have fresh data
        await data_service.update_cryptos_data()
        
        # Build query
        base_query = """
            SELECT id, symbol, name, current_price, score, 
                   change_amount as change, change_percent, volume, 
                   market_cap
            FROM cryptos
        """
        
        # Add sorting
        if sort == "score":
            query = base_query + " ORDER BY score DESC, symbol ASC"
        else:
            query = base_query + " ORDER BY symbol ASC"
        
        # Add limit
        query += f" LIMIT {limit}"
        
        cryptos_data = db_manager.execute_query(query)
        
        # Convert to Crypto models
        cryptos = []
        for crypto_data in cryptos_data:
            crypto = Crypto(
                id=crypto_data["id"],
                symbol=crypto_data["symbol"],
                name=crypto_data["name"],
                current_price=crypto_data["current_price"],
                score=crypto_data["score"],
                change=crypto_data["change"],
                change_percent=crypto_data["change_percent"],
                volume=crypto_data["volume"],
                market_cap=crypto_data["market_cap"]
            )
            cryptos.append(crypto)
        
        logger.info(f"Retrieved {len(cryptos)} cryptos (sort={sort})")
        return cryptos
        
    except Exception as e:
        logger.error(f"Error retrieving cryptos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving cryptos: {str(e)}")

@router.get("/cryptos/{symbol}", response_model=Crypto)
async def get_crypto_by_symbol(
    symbol: str,
    data_service: DataService = Depends(get_data_service)
):
    """
    Get specific cryptocurrency by symbol
    """
    try:
        # Update data for this specific crypto
        await data_service.update_single_crypto(symbol.upper())
        
        query = """
            SELECT id, symbol, name, current_price, score, 
                   change_amount as change, change_percent, volume, 
                   market_cap
            FROM cryptos 
            WHERE UPPER(symbol) = UPPER(?)
        """
        
        cryptos_data = db_manager.execute_query(query, (symbol.upper(),))
        
        if not cryptos_data:
            raise HTTPException(status_code=404, detail=f"Crypto {symbol} not found")
        
        crypto_data = cryptos_data[0]
        crypto = Crypto(
            id=crypto_data["id"],
            symbol=crypto_data["symbol"],
            name=crypto_data["name"],
            current_price=crypto_data["current_price"],
            score=crypto_data["score"],
            change=crypto_data["change"],
            change_percent=crypto_data["change_percent"],
            volume=crypto_data["volume"],
            market_cap=crypto_data["market_cap"]
        )
        
        logger.info(f"Retrieved crypto: {symbol}")
        return crypto
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving crypto {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving crypto: {str(e)}")

@router.post("/cryptos/refresh")
async def refresh_cryptos_data(
    data_service: DataService = Depends(get_data_service)
):
    """
    Manually refresh all cryptos data
    """
    try:
        await data_service.update_cryptos_data()
        return {"message": "Cryptos data refreshed successfully"}
        
    except Exception as e:
        logger.error(f"Error refreshing cryptos data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error refreshing data: {str(e)}")