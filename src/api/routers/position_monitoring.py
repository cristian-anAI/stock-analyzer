"""
Position Monitoring API Router
Endpoints for real-time position monitoring and market open updates
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

from ..services.position_monitor_service import position_monitor_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/position-monitoring", tags=["Position Monitoring"])

@router.get("/status")
async def get_position_monitoring_status() -> Dict[str, Any]:
    """
    Get current position monitoring status
    Shows all open positions being monitored and their current status
    """
    try:
        return position_monitor_service.get_monitoring_status()
    except Exception as e:
        logger.error(f"Error getting position monitoring status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/market-open-update")
async def trigger_market_open_update() -> Dict[str, Any]:
    """
    Manually trigger market open position update
    Updates all open positions with current market prices
    """
    try:
        logger.info("Manual market open update triggered via API")
        result = await position_monitor_service.market_open_position_update()
        return result
    except Exception as e:
        logger.error(f"Error in manual market open update: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refresh-positions")
async def refresh_position_prices() -> Dict[str, Any]:
    """
    Manually refresh all position prices
    Updates current prices and P&L for all open positions
    """
    try:
        logger.info("Manual position refresh triggered via API")
        
        # Get open positions before update
        open_positions = position_monitor_service._get_all_open_positions()
        
        if not open_positions:
            return {"message": "No open positions to refresh", "updated_positions": 0}
        
        # Update position prices
        await position_monitor_service._update_position_prices()
        
        # Get updated positions
        updated_positions = position_monitor_service._get_all_open_positions()
        
        spanish_time = position_monitor_service.get_spanish_time()
        
        return {
            "message": f"Refreshed {len(updated_positions)} positions",
            "updated_positions": len(updated_positions),
            "spanish_time": spanish_time.strftime('%H:%M'),
            "positions": [
                {
                    "symbol": pos['symbol'],
                    "type": pos['type'],
                    "entry_price": pos['entry_price'],
                    "current_price": pos.get('current_price', 0),
                    "unrealized_pnl": pos.get('unrealized_pnl', 0),
                    "pnl_percentage": (pos.get('unrealized_pnl', 0) / (pos['entry_price'] * pos['quantity'])) * 100 if pos.get('entry_price') else 0
                }
                for pos in updated_positions
            ]
        }
        
    except Exception as e:
        logger.error(f"Error refreshing position prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market-hours")
async def get_market_hours_info() -> Dict[str, Any]:
    """
    Get market hours information in Spanish timezone
    """
    try:
        spanish_time = position_monitor_service.get_spanish_time()
        is_market_open = position_monitor_service.is_market_open_spain()
        
        return {
            "spanish_time": spanish_time.strftime('%H:%M'),
            "spanish_date": spanish_time.strftime('%Y-%m-%d'),
            "is_market_open": is_market_open,
            "market_hours_spain": {
                "open": "15:30",
                "close": "22:00"
            },
            "market_hours_et": {
                "open": "09:30",
                "close": "16:00"  
            },
            "timezone": "Europe/Madrid (CEST/CET)",
            "next_events": _get_next_market_events(spanish_time, is_market_open)
        }
        
    except Exception as e:
        logger.error(f"Error getting market hours info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/positions/summary")
async def get_positions_summary() -> Dict[str, Any]:
    """
    Get summary of all open positions with current P&L
    """
    try:
        open_positions = position_monitor_service._get_all_open_positions()
        spanish_time = position_monitor_service.get_spanish_time()
        
        if not open_positions:
            return {
                "message": "No open positions",
                "total_positions": 0,
                "spanish_time": spanish_time.strftime('%H:%M')
            }
        
        # Calculate summary statistics
        total_unrealized_pnl = sum(pos.get('unrealized_pnl', 0) for pos in open_positions)
        total_invested = sum(pos['entry_price'] * pos['quantity'] for pos in open_positions)
        
        # Separate by type
        stock_positions = [p for p in open_positions if p['type'] in ['LONG', 'SHORT']]
        crypto_positions = [p for p in open_positions if p['type'] in ['CRYPTO_LONG', 'CRYPTO_SHORT']]
        
        return {
            "summary": {
                "total_positions": len(open_positions),
                "stock_positions": len(stock_positions),
                "crypto_positions": len(crypto_positions),
                "total_invested": round(total_invested, 2),
                "total_unrealized_pnl": round(total_unrealized_pnl, 2),
                "total_pnl_percentage": round((total_unrealized_pnl / total_invested) * 100, 2) if total_invested > 0 else 0
            },
            "positions": [
                {
                    "symbol": pos['symbol'],
                    "type": pos['type'],
                    "quantity": pos['quantity'],
                    "entry_price": pos['entry_price'],
                    "current_price": pos.get('current_price', 0),
                    "invested": pos['entry_price'] * pos['quantity'],
                    "unrealized_pnl": pos.get('unrealized_pnl', 0),
                    "pnl_percentage": round((pos.get('unrealized_pnl', 0) / (pos['entry_price'] * pos['quantity'])) * 100, 2) if pos.get('entry_price') else 0,
                    "created_at": pos['created_at']
                }
                for pos in open_positions
            ],
            "spanish_time": spanish_time.strftime('%H:%M'),
            "last_updated": position_monitor_service.last_market_open_update.isoformat() if position_monitor_service.last_market_open_update else None
        }
        
    except Exception as e:
        logger.error(f"Error getting positions summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _get_next_market_events(spanish_time, is_market_open):
    """Helper function to calculate next market events"""
    from datetime import timedelta, time
    
    current_time = spanish_time.time()
    
    if is_market_open:
        # Market is open, next event is close at 22:00
        return {
            "next_event": "Market Close",
            "next_time": "22:00",
            "status": "Market is currently OPEN"
        }
    elif current_time < time(15, 30):
        # Before market open today
        return {
            "next_event": "Market Open",
            "next_time": "15:30", 
            "status": "Market will open today"
        }
    else:
        # After market close, next open is tomorrow
        tomorrow = spanish_time + timedelta(days=1)
        return {
            "next_event": "Market Open", 
            "next_time": "15:30",
            "next_date": tomorrow.strftime('%Y-%m-%d'),
            "status": "Market is closed until tomorrow"
        }