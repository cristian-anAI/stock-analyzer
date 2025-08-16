"""
Positions API endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Path
from typing import List, Optional
import logging
import uuid
from datetime import datetime

from ..models.schemas import (
    Position, PositionCreate, PositionUpdate, SuccessResponse,
    ManualPositionAnalysis, TechnicalIndicators, ExitStrategy, 
    RiskMetrics, PositionRecommendation, PositionAnalysisResponse,
    FundamentalData, AlertItem
)
from ..database.database import db_manager
from ..services.data_service import DataService
from ..services.autotrader_service import AutotraderService

logger = logging.getLogger(__name__)

router = APIRouter()

def get_data_service():
    return DataService()

def get_autotrader_service():
    return AutotraderService()

@router.get("/positions/autotrader", response_model=List[Position])
async def get_autotrader_positions(
    type_filter: Optional[str] = Query(None, description="Filter by 'stock' or 'crypto'"),
    data_service: DataService = Depends(get_data_service)
):
    """
    Get all autotrader positions separated by type
    """
    try:
        # Update current prices for positions
        await data_service.update_positions_prices()
        
        # Build query
        base_query = """
            SELECT id, symbol, name, type, quantity, entry_price, 
                   current_price, value, pnl, pnl_percent, source,
                   position_side, created_at, updated_at
            FROM positions 
            WHERE source = 'autotrader'
        """
        
        # Add type filter if specified
        params = []
        if type_filter in ['stock', 'crypto']:
            base_query += " AND type = ?"
            params.append(type_filter)
        
        # Add ordering
        base_query += " ORDER BY type ASC, symbol ASC"
        
        positions_data = db_manager.execute_query(base_query, tuple(params))
        
        # Convert to Position models
        positions = []
        for pos_data in positions_data:
            # Debug log to check position_side value
            if pos_data["symbol"] in ["NEAR", "VET", "ADA"]:
                logger.info(f"DEBUG: {pos_data['symbol']} position_side from DB: '{pos_data['position_side']}'")
            
            position = Position(
                id=pos_data["id"],
                symbol=pos_data["symbol"],
                name=pos_data["name"],
                type=pos_data["type"],
                quantity=pos_data["quantity"],
                entry_price=pos_data["entry_price"],
                position_side=pos_data["position_side"],
                current_price=pos_data["current_price"],
                value=pos_data["value"],
                pnl=pos_data["pnl"],
                pnl_percent=pos_data["pnl_percent"],
                source=pos_data["source"],
                created_at=datetime.fromisoformat(pos_data["created_at"]) if pos_data["created_at"] else None,
                updated_at=datetime.fromisoformat(pos_data["updated_at"]) if pos_data["updated_at"] else None
            )
            
            # Debug log to check Position object
            if pos_data["symbol"] in ["NEAR", "VET", "ADA"]:
                logger.info(f"DEBUG: {pos_data['symbol']} Position object position_side: '{position.position_side}'")
            
            positions.append(position)
        
        logger.info(f"Retrieved {len(positions)} autotrader positions (filter={type_filter})")
        return positions
        
    except Exception as e:
        logger.error(f"Error retrieving autotrader positions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving positions: {str(e)}")

@router.get("/positions/manual", response_model=List[Position])
async def get_manual_positions(
    type_filter: Optional[str] = Query(None, description="Filter by 'stock' or 'crypto'"),
    data_service: DataService = Depends(get_data_service)
):
    """
    Get all manual positions
    """
    try:
        # Update current prices for positions
        await data_service.update_positions_prices()
        
        # Build query
        base_query = """
            SELECT id, symbol, name, type, quantity, entry_price, 
                   current_price, value, pnl, pnl_percent, source, notes,
                   created_at, updated_at
            FROM positions 
            WHERE source = 'manual'
        """
        
        # Add type filter if specified
        params = []
        if type_filter in ['stock', 'crypto']:
            base_query += " AND type = ?"
            params.append(type_filter)
        
        # Add ordering
        base_query += " ORDER BY type ASC, symbol ASC"
        
        positions_data = db_manager.execute_query(base_query, tuple(params))
        
        # Convert to Position models
        positions = []
        for pos_data in positions_data:
            position = Position(
                id=pos_data["id"],
                symbol=pos_data["symbol"],
                name=pos_data["name"],
                type=pos_data["type"],
                quantity=pos_data["quantity"],
                entry_price=pos_data["entry_price"],
                current_price=pos_data["current_price"],
                value=pos_data["value"],
                pnl=pos_data["pnl"],
                pnl_percent=pos_data["pnl_percent"],
                source=pos_data["source"],
                notes=pos_data.get("notes"),
                created_at=datetime.fromisoformat(pos_data["created_at"]) if pos_data["created_at"] else None,
                updated_at=datetime.fromisoformat(pos_data["updated_at"]) if pos_data["updated_at"] else None
            )
            positions.append(position)
        
        logger.info(f"Retrieved {len(positions)} manual positions (filter={type_filter})")
        return positions
        
    except Exception as e:
        logger.error(f"Error retrieving manual positions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving positions: {str(e)}")

@router.post("/positions/manual", response_model=Position)
async def create_manual_position(
    position_data: PositionCreate,
    data_service: DataService = Depends(get_data_service)
):
    """
    Create a new manual position
    """
    try:
        # Generate unique ID
        position_id = str(uuid.uuid4())
        
        # Get current price for the asset
        current_price = await data_service.get_current_price(position_data.symbol, position_data.type)
        
        # Calculate values
        value = position_data.quantity * current_price if current_price else 0
        
        # Calculate P&L based on position side
        if current_price:
            if position_data.position_side == 'SHORT':
                # SHORT: profit when price goes down
                pnl = (position_data.entry_price - current_price) * position_data.quantity
            else:
                # LONG: profit when price goes up
                pnl = (current_price - position_data.entry_price) * position_data.quantity
        else:
            pnl = 0
            
        pnl_percent = (pnl / (position_data.entry_price * position_data.quantity)) * 100 if position_data.entry_price > 0 else 0
        
        # Insert into database
        query = """
            INSERT INTO positions 
            (id, symbol, name, type, quantity, entry_price, current_price, 
             value, pnl, pnl_percent, source, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'manual', ?)
        """
        
        db_manager.execute_insert(query, (
            position_id,
            position_data.symbol.upper(),
            position_data.name,
            position_data.type,
            position_data.quantity,
            position_data.entry_price,
            current_price,
            value,
            pnl,
            pnl_percent,
            position_data.notes
        ))
        
        # Retrieve the created position
        created_position_data = db_manager.execute_query(
            "SELECT * FROM positions WHERE id = ?", 
            (position_id,)
        )[0]
        
        position = Position(
            id=created_position_data["id"],
            symbol=created_position_data["symbol"],
            name=created_position_data["name"],
            type=created_position_data["type"],
            quantity=created_position_data["quantity"],
            entry_price=created_position_data["entry_price"],
            current_price=created_position_data["current_price"],
            value=created_position_data["value"],
            pnl=created_position_data["pnl"],
            pnl_percent=created_position_data["pnl_percent"],
            source=created_position_data["source"],
            notes=created_position_data.get("notes"),
            created_at=datetime.fromisoformat(created_position_data["created_at"]) if created_position_data["created_at"] else None,
            updated_at=datetime.fromisoformat(created_position_data["updated_at"]) if created_position_data["updated_at"] else None
        )
        
        logger.info(f"Created manual position: {position_data.symbol}")
        return position
        
    except Exception as e:
        logger.error(f"Error creating manual position: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating position: {str(e)}")

@router.put("/positions/manual/{position_id}", response_model=Position)
async def update_manual_position(
    position_id: str = Path(..., description="Position ID"),
    position_update: PositionUpdate = ...,
    data_service: DataService = Depends(get_data_service)
):
    """
    Update a manual position
    """
    try:
        # Check if position exists and is manual
        existing = db_manager.execute_query(
            "SELECT * FROM positions WHERE id = ? AND source = 'manual'",
            (position_id,)
        )
        
        if not existing:
            raise HTTPException(status_code=404, detail="Manual position not found")
        
        existing_pos = existing[0]
        
        # Build update query dynamically
        update_fields = []
        params = []
        
        if position_update.symbol is not None:
            update_fields.append("symbol = ?")
            params.append(position_update.symbol.upper())
        
        if position_update.name is not None:
            update_fields.append("name = ?")
            params.append(position_update.name)
        
        if position_update.type is not None:
            update_fields.append("type = ?")
            params.append(position_update.type)
        
        if position_update.quantity is not None:
            update_fields.append("quantity = ?")
            params.append(position_update.quantity)
        
        if position_update.entry_price is not None:
            update_fields.append("entry_price = ?")
            params.append(position_update.entry_price)
        
        if position_update.notes is not None:
            update_fields.append("notes = ?")
            params.append(position_update.notes)
        
        # Always update timestamp
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        
        if update_fields:
            params.append(position_id)
            query = f"UPDATE positions SET {', '.join(update_fields)} WHERE id = ?"
            db_manager.execute_update(query, tuple(params))
        
        # Get updated position and recalculate values
        updated_pos_data = db_manager.execute_query(
            "SELECT * FROM positions WHERE id = ?",
            (position_id,)
        )[0]
        
        # Update current price and calculations
        symbol = updated_pos_data["symbol"]
        asset_type = updated_pos_data["type"]
        current_price = await data_service.get_current_price(symbol, asset_type)
        
        # Recalculate values
        quantity = updated_pos_data["quantity"]
        entry_price = updated_pos_data["entry_price"]
        position_side = updated_pos_data.get("position_side", "LONG")
        value = quantity * current_price if current_price else 0
        
        # Calculate P&L based on position side
        if current_price:
            if position_side == 'SHORT':
                # SHORT: profit when price goes down
                pnl = (entry_price - current_price) * quantity
            else:
                # LONG: profit when price goes up
                pnl = (current_price - entry_price) * quantity
        else:
            pnl = 0
            
        pnl_percent = (pnl / (entry_price * quantity)) * 100 if entry_price > 0 else 0
        
        # Update calculated fields
        db_manager.execute_update(
            "UPDATE positions SET current_price = ?, value = ?, pnl = ?, pnl_percent = ? WHERE id = ?",
            (current_price, value, pnl, pnl_percent, position_id)
        )
        
        # Return updated position
        final_pos_data = db_manager.execute_query(
            "SELECT * FROM positions WHERE id = ?",
            (position_id,)
        )[0]
        
        position = Position(
            id=final_pos_data["id"],
            symbol=final_pos_data["symbol"],
            name=final_pos_data["name"],
            type=final_pos_data["type"],
            quantity=final_pos_data["quantity"],
            entry_price=final_pos_data["entry_price"],
            current_price=final_pos_data["current_price"],
            value=final_pos_data["value"],
            pnl=final_pos_data["pnl"],
            pnl_percent=final_pos_data["pnl_percent"],
            source=final_pos_data["source"],
            notes=final_pos_data.get("notes"),
            created_at=datetime.fromisoformat(final_pos_data["created_at"]) if final_pos_data["created_at"] else None,
            updated_at=datetime.fromisoformat(final_pos_data["updated_at"]) if final_pos_data["updated_at"] else None
        )
        
        logger.info(f"Updated manual position: {position_id}")
        return position
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating manual position {position_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating position: {str(e)}")

@router.delete("/positions/manual/{position_id}", response_model=SuccessResponse)
async def delete_manual_position(
    position_id: str = Path(..., description="Position ID")
):
    """
    Delete a manual position
    """
    try:
        # Check if position exists and is manual
        existing = db_manager.execute_query(
            "SELECT symbol FROM positions WHERE id = ? AND source = 'manual'",
            (position_id,)
        )
        
        if not existing:
            raise HTTPException(status_code=404, detail="Manual position not found")
        
        symbol = existing[0]["symbol"]
        
        # Delete the position
        rows_affected = db_manager.execute_update(
            "DELETE FROM positions WHERE id = ? AND source = 'manual'",
            (position_id,)
        )
        
        if rows_affected == 0:
            raise HTTPException(status_code=404, detail="Position not found or not manual")
        
        logger.info(f"Deleted manual position: {position_id} ({symbol})")
        return SuccessResponse(
            message="Position deleted successfully",
            data={"id": position_id, "symbol": symbol}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting manual position {position_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting position: {str(e)}")

@router.post("/positions/refresh")
async def refresh_positions_data(
    data_service: DataService = Depends(get_data_service)
):
    """
    Manually refresh current prices for all positions
    """
    try:
        await data_service.update_positions_prices()
        return {"message": "Positions data refreshed successfully"}
        
    except Exception as e:
        logger.error(f"Error refreshing positions data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error refreshing data: {str(e)}")

@router.post("/autotrader/run")
async def run_autotrader_cycle(
    autotrader_service: AutotraderService = Depends(get_autotrader_service)
):
    """
    Manually trigger autotrader cycle
    """
    try:
        results = await autotrader_service.run_trading_cycle()
        return results
        
    except Exception as e:
        logger.error(f"Error running autotrader cycle: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error running autotrader: {str(e)}")

@router.get("/autotrader/summary")
async def get_autotrader_summary(
    autotrader_service: AutotraderService = Depends(get_autotrader_service)
):
    """
    Get autotrader performance summary
    """
    try:
        summary = autotrader_service.get_trading_summary()
        return summary
        
    except Exception as e:
        logger.error(f"Error getting autotrader summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting summary: {str(e)}")

@router.get("/positions/manual/{symbol}/analysis", response_model=ManualPositionAnalysis)
async def analyze_manual_position(
    symbol: str = Path(..., description="Position symbol"),
    data_service: DataService = Depends(get_data_service)
):
    """
    Get detailed analysis for a manual position including technical indicators,
    exit strategies, risk metrics, and recommendations
    """
    try:
        symbol = symbol.upper()
        
        # Get manual position from database
        position_data = db_manager.execute_query(
            "SELECT * FROM positions WHERE symbol = ? AND source = 'manual'",
            (symbol,)
        )
        
        if not position_data:
            raise HTTPException(status_code=404, detail=f"Manual position not found for symbol: {symbol}")
        
        position = position_data[0]
        
        # Get current market data and technical indicators
        current_price = await data_service.get_current_price(symbol, position["type"])
        if not current_price:
            raise HTTPException(status_code=400, detail=f"Unable to fetch current price for {symbol}")
        
        # Calculate basic position metrics
        entry_price = position["entry_price"]
        quantity = position["quantity"]
        entry_value = entry_price * quantity
        current_value = current_price * quantity
        unrealized_pnl = current_value - entry_value
        unrealized_pnl_percent = (unrealized_pnl / entry_value) * 100 if entry_value > 0 else 0
        
        # Calculate days held
        created_at = datetime.fromisoformat(position["created_at"]) if position["created_at"] else datetime.now()
        days_held = (datetime.now() - created_at).days
        
        # Get technical indicators using yfinance directly
        try:
            import yfinance as yf
            import pandas as pd
            import numpy as np
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="200d")  # Get enough data for 200-day MA
            
            if not hist.empty:
                # Calculate technical indicators
                close_prices = hist['Close']
                
                # RSI calculation
                delta = close_prices.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                
                # Moving averages
                ma_20 = close_prices.rolling(window=20).mean()
                ma_50 = close_prices.rolling(window=50).mean()
                ma_200 = close_prices.rolling(window=200).mean()
                
                # MACD calculation
                exp1 = close_prices.ewm(span=12).mean()
                exp2 = close_prices.ewm(span=26).mean()
                macd = exp1 - exp2
                macd_signal = macd.ewm(span=9).mean()
                macd_histogram = macd - macd_signal
                
                # Bollinger Bands
                bb_period = 20
                bb_std = 2
                bb_middle = close_prices.rolling(window=bb_period).mean()
                bb_std_dev = close_prices.rolling(window=bb_period).std()
                bollinger_upper = bb_middle + (bb_std_dev * bb_std)
                bollinger_lower = bb_middle - (bb_std_dev * bb_std)
                
                # Get latest values
                tech_indicators = {
                    'rsi': float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None,
                    'macd': float(macd.iloc[-1]) if not pd.isna(macd.iloc[-1]) else None,
                    'macd_signal': float(macd_signal.iloc[-1]) if not pd.isna(macd_signal.iloc[-1]) else None,
                    'macd_histogram': float(macd_histogram.iloc[-1]) if not pd.isna(macd_histogram.iloc[-1]) else None,
                    'ma_20': float(ma_20.iloc[-1]) if not pd.isna(ma_20.iloc[-1]) else None,
                    'ma_50': float(ma_50.iloc[-1]) if not pd.isna(ma_50.iloc[-1]) else None,
                    'ma_200': float(ma_200.iloc[-1]) if not pd.isna(ma_200.iloc[-1]) else None,
                    'bollinger_upper': float(bollinger_upper.iloc[-1]) if not pd.isna(bollinger_upper.iloc[-1]) else None,
                    'bollinger_lower': float(bollinger_lower.iloc[-1]) if not pd.isna(bollinger_lower.iloc[-1]) else None,
                }
            else:
                tech_indicators = {}
                
        except Exception as e:
            logger.warning(f"Could not calculate technical indicators for {symbol}: {e}")
            tech_indicators = {}
        
        # Create technical indicators object
        technical_indicators = TechnicalIndicators(
            rsi=tech_indicators.get('rsi'),
            macd=tech_indicators.get('macd'),
            macd_signal=tech_indicators.get('macd_signal'),
            macd_histogram=tech_indicators.get('macd_histogram'),
            ma_20=tech_indicators.get('ma_20'),
            ma_50=tech_indicators.get('ma_50'),
            ma_200=tech_indicators.get('ma_200'),
            bollinger_upper=tech_indicators.get('bollinger_upper'),
            bollinger_lower=tech_indicators.get('bollinger_lower')
        )
        
        # Calculate exit strategies
        # Stop loss: 8% below entry for stocks, 12% for crypto
        stop_loss_percent = 0.08 if position["type"] == "stock" else 0.12
        stop_loss = entry_price * (1 - stop_loss_percent)
        
        # Take profit: 15% above entry for stocks, 25% for crypto
        take_profit_percent = 0.15 if position["type"] == "stock" else 0.25
        take_profit = entry_price * (1 + take_profit_percent)
        
        # Partial profit: 7% above entry
        partial_profit = entry_price * 1.07
        
        # Trailing stop: 5% below current high
        trailing_stop = current_price * 0.95
        
        exit_strategies = ExitStrategy(
            stop_loss=stop_loss,
            take_profit=take_profit,
            partial_profit=partial_profit,
            trailing_stop=trailing_stop
        )
        
        # Calculate risk metrics
        risk_amount = entry_value - (stop_loss * quantity)
        reward_amount = (take_profit * quantity) - entry_value
        risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0
        
        # Estimate portfolio size (rough calculation)
        all_positions = db_manager.execute_query("SELECT value FROM positions WHERE value IS NOT NULL")
        total_portfolio_value = sum([pos["value"] for pos in all_positions if pos["value"]]) or 100000
        position_size_percent = (current_value / total_portfolio_value) * 100 if total_portfolio_value > 0 else 0
        
        # Calculate volatility (simple estimation based on price movement)
        volatility = abs(unrealized_pnl_percent) / max(days_held, 1) if days_held > 0 else 0
        
        risk_metrics = RiskMetrics(
            risk_reward_ratio=risk_reward_ratio,
            position_size_percent=position_size_percent,
            days_held=days_held,
            volatility=volatility
        )
        
        # Generate recommendation based on technical analysis
        rsi = technical_indicators.rsi
        reasons = []
        confidence = 50  # Base confidence
        action = "HOLD"
        
        # RSI analysis
        if rsi:
            if rsi > 80:
                action = "SELL"
                confidence += 20
                reasons.append(f"RSI overbought at {rsi:.1f}")
            elif rsi > 70:
                action = "PARTIAL_SELL"
                confidence += 10
                reasons.append(f"RSI elevated at {rsi:.1f}")
            elif rsi < 20:
                action = "HOLD"
                confidence += 15
                reasons.append(f"RSI oversold at {rsi:.1f} - potential bounce")
            elif 40 <= rsi <= 60:
                confidence += 5
                reasons.append(f"RSI neutral at {rsi:.1f}")
        
        # P&L analysis
        if unrealized_pnl_percent > 15:
            action = "PARTIAL_SELL"
            confidence += 15
            reasons.append(f"Strong profit at {unrealized_pnl_percent:.1f}%")
        elif unrealized_pnl_percent > 7:
            if action != "SELL":
                action = "PARTIAL_SELL"
            confidence += 10
            reasons.append(f"Good profit at {unrealized_pnl_percent:.1f}%")
        elif unrealized_pnl_percent < -8:
            action = "SELL"
            confidence += 25
            reasons.append(f"Stop loss triggered at {unrealized_pnl_percent:.1f}%")
        
        # Price vs moving averages
        ma_20 = technical_indicators.ma_20
        ma_50 = technical_indicators.ma_50
        if ma_20 and ma_50:
            if current_price > ma_20 > ma_50:
                confidence += 10
                reasons.append("Price above key moving averages")
            elif current_price < ma_20 < ma_50:
                if action == "HOLD":
                    action = "SELL"
                confidence += 15
                reasons.append("Price below key moving averages")
        
        # Days held consideration
        if days_held > 90 and unrealized_pnl_percent < 5:
            confidence += 5
            reasons.append("Long hold with minimal gains")
        
        # Ensure we have reasons
        if not reasons:
            reasons.append("Standard technical analysis")
        
        recommendation = PositionRecommendation(
            action=action,
            confidence=min(confidence, 95),  # Cap at 95%
            reasons=reasons
        )
        
        # Create final analysis response
        analysis = ManualPositionAnalysis(
            symbol=symbol,
            current_price=current_price,
            entry_price=entry_price,
            quantity=quantity,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_percent=unrealized_pnl_percent,
            technical_indicators=technical_indicators,
            exit_strategies=exit_strategies,
            risk_metrics=risk_metrics,
            recommendation=recommendation,
            analysis_timestamp=datetime.now()
        )
        
        logger.info(f"Generated analysis for manual position: {symbol}")
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing manual position {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing position: {str(e)}")

@router.get("/positions/analysis/{symbol}", response_model=PositionAnalysisResponse)
async def get_position_analysis(
    symbol: str = Path(..., description="Position symbol")
):
    """
    Get fundamental analysis data for a position including news sentiment,
    earnings data, sector performance, and recent alerts
    """
    try:
        symbol = symbol.upper()
        
        # Generate mock fundamental data for Phase 1
        mock_alerts = [
            AlertItem(
                type="technical",
                message="RSI approaching oversold levels",
                timestamp=datetime.now(),
                severity="medium"
            ),
            AlertItem(
                type="volume",
                message="Above average trading volume detected", 
                timestamp=datetime.now(),
                severity="low"
            )
        ]
        
        fundamental_data = FundamentalData(
            newsSentiment=-0.2,
            earningsDate="2025-02-15",
            earningsProximity=12,
            sectorPerformance=-1.5,
            analystRating="buy",
            priceTarget=175.00,
            recentAlerts=mock_alerts
        )
        
        response = PositionAnalysisResponse(
            symbol=symbol,
            fundamental=fundamental_data,
            timestamp=datetime.now()
        )
        
        logger.info(f"Generated fundamental analysis for: {symbol}")
        return response
        
    except Exception as e:
        logger.error(f"Error getting position analysis for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting analysis: {str(e)}")