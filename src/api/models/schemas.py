"""
Pydantic models for API data validation
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import datetime

class StockBase(BaseModel):
    symbol: str = Field(..., description="Stock symbol (e.g., AAPL)")
    name: str = Field(..., description="Company name")
    sector: Optional[str] = Field(None, description="Stock sector")

class Stock(StockBase):
    id: str = Field(..., description="Unique identifier")
    current_price: Optional[float] = Field(None, description="Current stock price")
    score: Optional[float] = Field(None, ge=1, le=10, description="Score from 1-10")
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
    score: Optional[float] = Field(None, ge=1, le=10, description="Score from 1-10")
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
    position_side: Literal["LONG", "SHORT"] = Field("LONG", description="Position side")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    def calculate_pnl(self, current_price: float) -> tuple[float, float]:
        """Calculate P&L according to position side"""
        if self.position_side == 'LONG':
            pnl = (current_price - self.entry_price) * self.quantity
        else:  # SHORT
            pnl = (self.entry_price - current_price) * self.quantity
            
        pnl_percent = (pnl / (self.entry_price * self.quantity)) * 100
        return pnl, pnl_percent
    
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
    position_side: Optional[Literal["LONG", "SHORT"]] = Field(None, description="Position side")
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

# Manual Position Analysis Models
class TechnicalIndicators(BaseModel):
    rsi: Optional[float] = Field(None, description="RSI (0-100)")
    macd: Optional[float] = Field(None, description="MACD signal")
    macd_signal: Optional[float] = Field(None, description="MACD signal line")
    macd_histogram: Optional[float] = Field(None, description="MACD histogram")
    ma_20: Optional[float] = Field(None, description="20-day moving average")
    ma_50: Optional[float] = Field(None, description="50-day moving average")
    ma_200: Optional[float] = Field(None, description="200-day moving average")
    bollinger_upper: Optional[float] = Field(None, description="Bollinger Band upper")
    bollinger_lower: Optional[float] = Field(None, description="Bollinger Band lower")

class ExitStrategy(BaseModel):
    stop_loss: float = Field(..., description="Stop loss price")
    take_profit: float = Field(..., description="Take profit price")
    partial_profit: float = Field(..., description="Partial profit price (50% sell)")
    trailing_stop: float = Field(..., description="Trailing stop price")

class RiskMetrics(BaseModel):
    risk_reward_ratio: float = Field(..., description="Risk/reward ratio")
    position_size_percent: float = Field(..., description="Position size as % of portfolio")
    days_held: int = Field(..., description="Days position has been held")
    volatility: Optional[float] = Field(None, description="Price volatility")

class PositionRecommendation(BaseModel):
    action: str = Field(..., description="Recommended action (HOLD, SELL, PARTIAL_SELL)")
    confidence: float = Field(..., ge=0, le=100, description="Confidence level (0-100)")
    reasons: List[str] = Field(..., description="Reasons for recommendation")

class AlertItem(BaseModel):
    type: str = Field(..., description="Alert type (technical, fundamental, news, volume)")
    message: str = Field(..., description="Alert message")
    timestamp: datetime = Field(..., description="Alert timestamp")
    severity: str = Field(..., description="Alert severity (low, medium, high)")

class FundamentalData(BaseModel):
    newsSentiment: float = Field(..., ge=-1.0, le=1.0, description="News sentiment score (-1.0 to +1.0)")
    earningsDate: Optional[str] = Field(None, description="Next earnings date (YYYY-MM-DD)")
    earningsProximity: Optional[int] = Field(None, description="Days until earnings")
    sectorPerformance: Optional[float] = Field(None, description="% performance vs sector benchmark")
    analystRating: Optional[str] = Field(None, description="Analyst rating (buy/hold/sell)")
    priceTarget: Optional[float] = Field(None, description="Average analyst price target")
    recentAlerts: List[AlertItem] = Field(default=[], description="Last 5 alerts for this position")

class PositionAnalysisResponse(BaseModel):
    symbol: str = Field(..., description="Position symbol")
    fundamental: FundamentalData = Field(..., description="Fundamental analysis data")
    timestamp: datetime = Field(..., description="Analysis timestamp")

class ManualPositionAnalysis(BaseModel):
    symbol: str = Field(..., description="Position symbol")
    current_price: float = Field(..., description="Current market price")
    entry_price: float = Field(..., description="Position entry price")
    quantity: float = Field(..., description="Position quantity")
    unrealized_pnl: float = Field(..., description="Unrealized P&L")
    unrealized_pnl_percent: float = Field(..., description="Unrealized P&L percentage")
    technical_indicators: TechnicalIndicators = Field(..., description="Technical analysis indicators")
    exit_strategies: ExitStrategy = Field(..., description="Exit strategy calculations")
    risk_metrics: RiskMetrics = Field(..., description="Risk assessment metrics")
    recommendation: PositionRecommendation = Field(..., description="Position recommendation")
    analysis_timestamp: datetime = Field(..., description="Analysis timestamp")