"""
Positions API endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Path
from typing import List, Optional
import logging
import uuid
from datetime import datetime

from ..models.schemas import Position, PositionCreate, PositionUpdate, SuccessResponse
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
                   created_at, updated_at
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
                created_at=datetime.fromisoformat(pos_data["created_at"]) if pos_data["created_at"] else None,
                updated_at=datetime.fromisoformat(pos_data["updated_at"]) if pos_data["updated_at"] else None
            )
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
        pnl = (current_price - position_data.entry_price) * position_data.quantity if current_price else 0
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
        value = quantity * current_price if current_price else 0
        pnl = (current_price - entry_price) * quantity if current_price else 0
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