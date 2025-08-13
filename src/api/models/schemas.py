"""
Pydantic models for API data validation
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class StockBase(BaseModel):
    symbol: str = Field(..., description="Stock symbol (e.g., AAPL)")
    name: str = Field(..., description="Company name")
    sector: Optional[str] = Field(None, description="Stock sector")

class Stock(StockBase):
    id: str = Field(..., description="Unique identifier")
    current_price: Optional[float] = Field(None, description="Current stock price")
    score: Optional[int] = Field(None, ge=1, le=10, description="Score from 1-10")
    change: Optional[float] = Field(None, description="Price change amount")
    change_percent: Optional[float] = Field(None, description="Price change percentage")
    volume: Optional[int] = Field(None, description="Trading volume")
    market_cap: Optional[float] = Field(None, description="Market capitalization")

class CryptoBase(BaseModel):
    symbol: str = Field(..., description="Crypto symbol (e.g., BTC)")
    name: str = Field(..., description="Cryptocurrency name")

class Crypto(CryptoBase):
    id: str = Field(..., description="Unique identifier")
    current_price: Optional[float] = Field(None, description="Current price", alias="currentPrice")
    score: Optional[int] = Field(None, ge=1, le=10, description="Score from 1-10")
    change: Optional[float] = Field(None, description="Price change amount")
    change_percent: Optional[float] = Field(None, description="Price change percentage", alias="changePercent")
    volume: Optional[float] = Field(None, description="Trading volume")
    market_cap: Optional[float] = Field(None, description="Market capitalization", alias="marketCap")
    
    class Config:
        populate_by_name = True

class PositionBase(BaseModel):
    symbol: str = Field(..., description="Asset symbol")
    name: str = Field(..., description="Asset name")
    type: Literal["stock", "crypto"] = Field(..., description="Position type")
    quantity: float = Field(..., gt=0, description="Position quantity")
    entry_price: float = Field(..., gt=0, description="Entry price", alias="entryPrice")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    class Config:
        populate_by_name = True

class PositionCreate(PositionBase):
    pass

class PositionUpdate(BaseModel):
    symbol: Optional[str] = Field(None, description="Asset symbol")
    name: Optional[str] = Field(None, description="Asset name")
    type: Optional[Literal["stock", "crypto"]] = Field(None, description="Position type")
    quantity: Optional[float] = Field(None, gt=0, description="Position quantity")
    entry_price: Optional[float] = Field(None, gt=0, description="Entry price", alias="entryPrice")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    class Config:
        populate_by_name = True

class Position(PositionBase):
    id: str = Field(..., description="Unique identifier")
    current_price: Optional[float] = Field(None, description="Current asset price")
    value: Optional[float] = Field(None, description="Position value")
    pnl: Optional[float] = Field(None, description="Profit/Loss amount")
    pnl_percent: Optional[float] = Field(None, description="Profit/Loss percentage")
    source: Literal["autotrader", "manual"] = Field(..., description="Position source")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

class AutotraderTransaction(BaseModel):
    id: int = Field(..., description="Transaction ID")
    symbol: str = Field(..., description="Asset symbol")
    action: Literal["buy", "sell"] = Field(..., description="Transaction action")
    quantity: float = Field(..., description="Transaction quantity")
    price: float = Field(..., description="Transaction price")
    timestamp: datetime = Field(..., description="Transaction timestamp")
    reason: Optional[str] = Field(None, description="Transaction reason")

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")

class SuccessResponse(BaseModel):
    message: str = Field(..., description="Success message")
    data: Optional[dict] = Field(None, description="Response data")