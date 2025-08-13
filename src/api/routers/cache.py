"""
Cache management endpoints
"""

from fastapi import APIRouter, HTTPException, Path
from typing import Dict, Any
import logging

from ..services.cache_service import cache_service
from ..models.schemas import SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/cache/status")
async def get_cache_status():
    """Get cache statistics and status"""
    try:
        stats = await cache_service.get_cache_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting cache status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting cache status: {str(e)}")

@router.post("/cache/invalidate/{cache_key}")
async def invalidate_cache(cache_key: str = Path(..., description="Cache key to invalidate")):
    """Invalidate specific cache key"""
    try:
        success = await cache_service.delete(cache_key)
        
        if success:
            return SuccessResponse(
                message=f"Cache key '{cache_key}' invalidated successfully",
                data={"key": cache_key}
            )
        else:
            raise HTTPException(status_code=404, detail=f"Cache key '{cache_key}' not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error invalidating cache key {cache_key}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error invalidating cache: {str(e)}")

@router.post("/cache/invalidate-pattern/{pattern}")
async def invalidate_cache_pattern(pattern: str = Path(..., description="Cache pattern to invalidate (use * for wildcards)")):
    """Invalidate cache keys matching pattern"""
    try:
        count = await cache_service.invalidate_pattern(pattern)
        
        return SuccessResponse(
            message=f"Invalidated {count} cache keys matching pattern '{pattern}'",
            data={"pattern": pattern, "invalidated_count": count}
        )
        
    except Exception as e:
        logger.error(f"Error invalidating cache pattern {pattern}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error invalidating cache pattern: {str(e)}")

@router.post("/cache/refresh-stocks")
async def refresh_stocks_cache():
    """Force refresh stocks cache"""
    try:
        from ..services.data_service import DataService
        
        data_service = DataService()
        await data_service.update_stocks_data(force_refresh=True)
        
        return SuccessResponse(
            message="Stocks cache refreshed successfully",
            data={"cache_type": "stocks"}
        )
        
    except Exception as e:
        logger.error(f"Error refreshing stocks cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error refreshing stocks cache: {str(e)}")

@router.post("/cache/refresh-cryptos")
async def refresh_cryptos_cache():
    """Force refresh cryptos cache"""
    try:
        from ..services.data_service import DataService
        
        data_service = DataService()
        await data_service.update_cryptos_data(force_refresh=True)
        
        return SuccessResponse(
            message="Cryptos cache refreshed successfully",
            data={"cache_type": "cryptos"}
        )
        
    except Exception as e:
        logger.error(f"Error refreshing cryptos cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error refreshing cryptos cache: {str(e)}")

@router.post("/cache/clear-all")
async def clear_all_cache():
    """Clear all cache entries"""
    try:
        count = await cache_service.invalidate_pattern("*")
        
        return SuccessResponse(
            message=f"Cleared all cache entries ({count} keys)",
            data={"cleared_count": count}
        )
        
    except Exception as e:
        logger.error(f"Error clearing all cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")