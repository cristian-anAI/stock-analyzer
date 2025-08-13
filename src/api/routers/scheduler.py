"""
Background scheduler control endpoints
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
from pydantic import BaseModel

from ..services.background_scheduler import background_scheduler
from ..models.schemas import SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter()

class SchedulerSettings(BaseModel):
    autotrader_interval: int = None
    data_update_interval: int = None

@router.post("/scheduler/start")
async def start_scheduler():
    """Start the background autotrader scheduler"""
    try:
        result = await background_scheduler.start()
        return SuccessResponse(
            message="Background scheduler started successfully",
            data=result
        )
        
    except Exception as e:
        logger.error(f"Error starting scheduler: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error starting scheduler: {str(e)}")

@router.post("/scheduler/stop")
async def stop_scheduler():
    """Stop the background autotrader scheduler"""
    try:
        result = await background_scheduler.stop()
        return SuccessResponse(
            message="Background scheduler stopped successfully",
            data=result
        )
        
    except Exception as e:
        logger.error(f"Error stopping scheduler: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error stopping scheduler: {str(e)}")

@router.get("/scheduler/status")
async def get_scheduler_status():
    """Get scheduler status and statistics"""
    try:
        status = background_scheduler.get_status()
        return status
        
    except Exception as e:
        logger.error(f"Error getting scheduler status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting scheduler status: {str(e)}")

@router.post("/scheduler/settings")
async def update_scheduler_settings(settings: SchedulerSettings):
    """Update scheduler settings"""
    try:
        background_scheduler.update_settings(
            autotrader_interval=settings.autotrader_interval,
            data_update_interval=settings.data_update_interval
        )
        
        return SuccessResponse(
            message="Scheduler settings updated successfully",
            data=background_scheduler.get_status()["settings"]
        )
        
    except Exception as e:
        logger.error(f"Error updating scheduler settings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating scheduler settings: {str(e)}")

@router.post("/scheduler/restart")
async def restart_scheduler():
    """Restart the background scheduler"""
    try:
        # Stop first
        await background_scheduler.stop()
        # Start again
        result = await background_scheduler.start()
        
        return SuccessResponse(
            message="Background scheduler restarted successfully",
            data=result
        )
        
    except Exception as e:
        logger.error(f"Error restarting scheduler: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error restarting scheduler: {str(e)}")