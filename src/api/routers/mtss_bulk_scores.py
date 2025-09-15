"""
MTSS Bulk Scores Router - Frontend bulk access to cached MTSS scores

Provides efficient endpoints for frontend to get all cached MTSS scores 
without triggering expensive API calls. Uses the mtss_scores cache table
populated by the MTSS scheduler service.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import logging

from ..database.database import db_manager
from ..services.mtss_scheduler_service import mtss_scheduler

router = APIRouter(prefix="/api/v1/mtss-bulk", tags=["MTSS Bulk Scores"])
logger = logging.getLogger(__name__)

@router.get("/scores")
async def get_bulk_mtss_scores(
    asset_type: str = Query("stock", description="Asset type: 'stock' or 'crypto'"),
    timeframe: Optional[str] = Query(None, description="Specific timeframe: '1h', '1d', '1W', '1M'"),
    min_score: Optional[float] = Query(None, description="Minimum score filter"),
    max_age_hours: int = Query(24, description="Maximum age of cached data in hours"),
    limit: int = Query(100, description="Maximum number of results")
) -> Dict[str, Any]:
    """
    Get bulk MTSS scores from cache for frontend display
    
    This endpoint provides fast access to pre-calculated MTSS scores
    without triggering expensive API calls. Perfect for populating
    frontend tables and dashboards.
    """
    try:
        logger.info(f"Bulk MTSS scores requested: {asset_type}, timeframe={timeframe}, limit={limit}")
        
        # Build query conditions
        conditions = []
        params = []
        
        # Filter by timeframe if specified
        if timeframe:
            conditions.append("timeframe = ?")
            params.append(timeframe)
        
        # Filter by minimum score
        if min_score is not None:
            conditions.append("score >= ?")
            params.append(min_score)
        
        # Filter by data freshness
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        conditions.append("updated_at > ?")
        params.append(cutoff_time.isoformat())
        
        # Build WHERE clause
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Query cached scores
        query = f"""
        SELECT 
            symbol, timeframe, score, unified_score, trading_signal, 
            confidence, monthly_filter_passed, timeframe_scores,
            breakdown, updated_at
        FROM mtss_scores 
        {where_clause}
        ORDER BY score DESC, updated_at DESC
        LIMIT ?
        """
        params.append(limit)
        
        cached_scores = db_manager.execute_query(query, tuple(params))
        
        # Process and enrich results
        results = []
        symbols_processed = set()
        
        for row in cached_scores:
            symbol = row["symbol"]
            
            # Get basic symbol info from stocks/cryptos table
            symbol_info = await _get_symbol_info(symbol, asset_type)
            if not symbol_info:
                continue
            
            # Parse JSON fields safely
            try:
                timeframe_scores = json.loads(row["timeframe_scores"]) if row["timeframe_scores"] else {}
                breakdown = json.loads(row["breakdown"]) if row["breakdown"] else {}
            except json.JSONDecodeError:
                timeframe_scores = {}
                breakdown = {}
            
            result = {
                "symbol": symbol,
                "name": symbol_info.get("name", symbol),
                "current_price": symbol_info.get("current_price"),
                "change_percent": symbol_info.get("change_percent"),
                "traditional_score": symbol_info.get("score"),
                "mtss": {
                    "timeframe": row["timeframe"],
                    "score": row["score"],
                    "unified_score": row["unified_score"],
                    "trading_signal": row["trading_signal"],
                    "confidence": row["confidence"],
                    "monthly_filter_passed": bool(row["monthly_filter_passed"]),
                    "timeframe_scores": timeframe_scores,
                    "updated_at": row["updated_at"]
                },
                "analysis_breakdown": breakdown
            }
            
            results.append(result)
            symbols_processed.add(symbol)
        
        # Get missing high-score symbols that haven't been analyzed yet
        missing_symbols = await _get_unanalyzed_high_score_symbols(
            asset_type, min_score or 6.0, symbols_processed, max(0, limit - len(results))
        )
        
        for symbol_info in missing_symbols:
            result = {
                "symbol": symbol_info["symbol"],
                "name": symbol_info.get("name", symbol_info["symbol"]),
                "current_price": symbol_info.get("current_price"),
                "change_percent": symbol_info.get("change_percent"),
                "traditional_score": symbol_info.get("score"),
                "mtss": None,  # Not analyzed yet
                "analysis_available": False,
                "message": "Use /api/v1/unified-scoring/analyze/{symbol} for on-demand analysis"
            }
            results.append(result)
        
        return {
            "asset_type": asset_type,
            "timeframe_filter": timeframe,
            "results_count": len(results),
            "cached_scores": len([r for r in results if r.get("mtss")]),
            "unanalyzed_symbols": len([r for r in results if not r.get("mtss")]),
            "data_freshness_hours": max_age_hours,
            "results": results,
            "timestamp": datetime.now().isoformat(),
            "scheduler_status": mtss_scheduler.get_scheduler_status()
        }
        
    except Exception as e:
        logger.error(f"Error getting bulk MTSS scores: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get bulk scores: {str(e)}")

@router.get("/timeframes/{symbol}")
async def get_symbol_all_timeframes(
    symbol: str,
    asset_type: str = Query("stock", description="Asset type: 'stock' or 'crypto'"),
    max_age_hours: int = Query(24, description="Maximum age of cached data in hours")
) -> Dict[str, Any]:
    """
    Get all timeframe scores for a specific symbol
    
    Returns cached MTSS scores for all timeframes (1h, 1d, 1W, 1M)
    for a single symbol. Useful for detailed symbol analysis view.
    """
    try:
        logger.info(f"All timeframes requested for {symbol} ({asset_type})")
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        # Get all cached scores for this symbol
        cached_scores = db_manager.execute_query("""
            SELECT timeframe, score, unified_score, trading_signal, 
                   confidence, monthly_filter_passed, timeframe_scores, 
                   breakdown, updated_at
            FROM mtss_scores 
            WHERE symbol = ? AND updated_at > ?
            ORDER BY 
                CASE timeframe 
                    WHEN '1M' THEN 1 
                    WHEN '1W' THEN 2 
                    WHEN '1d' THEN 3 
                    WHEN '1h' THEN 4 
                END
        """, (symbol.upper(), cutoff_time.isoformat()))
        
        # Get basic symbol info
        symbol_info = await _get_symbol_info(symbol, asset_type)
        if not symbol_info:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
        
        # Process timeframe results
        timeframe_results = {}
        latest_unified_score = None
        latest_signal = None
        
        for row in cached_scores:
            try:
                timeframe_scores = json.loads(row["timeframe_scores"]) if row["timeframe_scores"] else {}
                breakdown = json.loads(row["breakdown"]) if row["breakdown"] else {}
            except json.JSONDecodeError:
                timeframe_scores = {}
                breakdown = {}
            
            timeframe_results[row["timeframe"]] = {
                "score": row["score"],
                "unified_score": row["unified_score"],
                "trading_signal": row["trading_signal"],
                "confidence": row["confidence"],
                "monthly_filter_passed": bool(row["monthly_filter_passed"]),
                "timeframe_scores": timeframe_scores,
                "breakdown": breakdown,
                "updated_at": row["updated_at"],
                "age_hours": (datetime.now() - datetime.fromisoformat(row["updated_at"])).total_seconds() / 3600
            }
            
            # Use most recent unified score
            if latest_unified_score is None or row["unified_score"]:
                latest_unified_score = row["unified_score"]
                latest_signal = row["trading_signal"]
        
        # Identify missing timeframes
        expected_timeframes = ["1M", "1W", "1d", "1h"]
        missing_timeframes = [tf for tf in expected_timeframes if tf not in timeframe_results]
        
        return {
            "symbol": symbol.upper(),
            "asset_type": asset_type,
            "symbol_info": {
                "name": symbol_info.get("name", symbol),
                "current_price": symbol_info.get("current_price"),
                "change_percent": symbol_info.get("change_percent"),
                "traditional_score": symbol_info.get("score"),
                "market_cap": symbol_info.get("market_cap"),
                "sector": symbol_info.get("sector")
            },
            "unified_analysis": {
                "latest_unified_score": latest_unified_score,
                "latest_trading_signal": latest_signal,
                "overall_recommendation": _get_overall_recommendation(timeframe_results)
            },
            "timeframe_analysis": timeframe_results,
            "missing_timeframes": missing_timeframes,
            "coverage": f"{len(timeframe_results)}/4 timeframes analyzed",
            "data_freshness_hours": max_age_hours,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting timeframes for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get timeframe analysis: {str(e)}")

@router.get("/scheduler/status")
async def get_scheduler_status() -> Dict[str, Any]:
    """Get MTSS scheduler status and statistics"""
    try:
        scheduler_status = mtss_scheduler.get_scheduler_status()
        
        # Add database statistics
        total_cached_scores = db_manager.execute_query("SELECT COUNT(*) as count FROM mtss_scores")[0]["count"]
        
        recent_scores = db_manager.execute_query("""
            SELECT timeframe, COUNT(*) as count 
            FROM mtss_scores 
            WHERE updated_at > datetime('now', '-24 hours')
            GROUP BY timeframe
        """)
        
        recent_by_timeframe = {row["timeframe"]: row["count"] for row in recent_scores}
        
        return {
            "scheduler": scheduler_status,
            "database_stats": {
                "total_cached_scores": total_cached_scores,
                "scores_last_24h": recent_by_timeframe,
                "total_recent": sum(recent_by_timeframe.values())
            },
            "system_health": _assess_system_health(scheduler_status, recent_by_timeframe),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _get_symbol_info(symbol: str, asset_type: str) -> Optional[Dict[str, Any]]:
    """Get basic symbol info from stocks/cryptos table"""
    try:
        table = "cryptos" if asset_type == 'crypto' else "stocks"
        
        data = db_manager.execute_query(
            f"SELECT symbol, name, current_price, change_percent, score, market_cap, sector FROM {table} WHERE symbol = ? LIMIT 1",
            (symbol.upper(),)
        )
        
        return dict(data[0]) if data else None
        
    except Exception as e:
        logger.error(f"Error getting symbol info for {symbol}: {e}")
        return None

async def _get_unanalyzed_high_score_symbols(
    asset_type: str, 
    min_score: float, 
    exclude_symbols: set, 
    limit: int
) -> List[Dict[str, Any]]:
    """Get high-score symbols that haven't been MTSS analyzed yet"""
    try:
        if limit <= 0:
            return []
        
        table = "cryptos" if asset_type == 'crypto' else "stocks"
        
        # Get symbols with high traditional scores that aren't in our cached set
        placeholders = ','.join(['?' for _ in exclude_symbols]) if exclude_symbols else "''"
        exclude_clause = f"AND symbol NOT IN ({placeholders})" if exclude_symbols else ""
        
        params = [min_score] + list(exclude_symbols) + [limit]
        
        query = f"""
        SELECT symbol, name, current_price, change_percent, score, market_cap, sector
        FROM {table} 
        WHERE score >= ? {exclude_clause}
        ORDER BY score DESC 
        LIMIT ?
        """
        
        unanalyzed = db_manager.execute_query(query, params)
        return [dict(row) for row in unanalyzed]
        
    except Exception as e:
        logger.error(f"Error getting unanalyzed symbols: {e}")
        return []

def _get_overall_recommendation(timeframe_results: Dict[str, Any]) -> str:
    """Generate overall recommendation based on all timeframes"""
    if not timeframe_results:
        return "No analysis available"
    
    # Count BUY vs SELL signals
    buy_signals = sum(1 for tf_data in timeframe_results.values() 
                     if tf_data.get("trading_signal") == "BUY")
    sell_signals = sum(1 for tf_data in timeframe_results.values() 
                      if tf_data.get("trading_signal") == "SELL")
    
    total_signals = buy_signals + sell_signals
    if total_signals == 0:
        return "HOLD - No clear signals"
    
    # Check monthly filter
    monthly_blocked = any(not tf_data.get("monthly_filter_passed", True) 
                         for tf_data in timeframe_results.values())
    
    if monthly_blocked:
        return "HOLD - Monthly filter blocked"
    
    # Determine recommendation
    if buy_signals > sell_signals * 1.5:
        return f"BUY - Strong consensus ({buy_signals}/{total_signals} timeframes)"
    elif sell_signals > buy_signals * 1.5:
        return f"SELL - Strong consensus ({sell_signals}/{total_signals} timeframes)"
    else:
        return f"HOLD - Mixed signals ({buy_signals} BUY, {sell_signals} SELL)"

def _assess_system_health(scheduler_status: Dict[str, Any], recent_scores: Dict[str, int]) -> Dict[str, Any]:
    """Assess overall system health"""
    total_recent = sum(recent_scores.values())
    expected_minimum = 50  # Minimum expected scores in 24h
    
    if not scheduler_status.get("is_running", False):
        health = "CRITICAL"
        message = "MTSS Scheduler not running"
    elif total_recent < expected_minimum:
        health = "WARNING" 
        message = f"Low activity: {total_recent} scores in 24h (expected {expected_minimum}+)"
    elif scheduler_status.get("stats", {}).get("errors", 0) > 10:
        health = "WARNING"
        message = f"High error count: {scheduler_status['stats']['errors']}"
    else:
        health = "HEALTHY"
        message = f"System operating normally: {total_recent} scores processed in 24h"
    
    return {
        "status": health,
        "message": message,
        "scores_24h": total_recent,
        "expected_minimum": expected_minimum
    }