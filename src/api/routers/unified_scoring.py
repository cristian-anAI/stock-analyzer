"""
Unified Scoring Router - On-demand MTSS analysis
Provides detailed scoring only when requested by frontend
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from ..services.unified_scoring_service import UnifiedScoringService
from ..services.scoring_service import ScoringService
from ..database.database import db_manager

router = APIRouter(prefix="/api/v1/unified-scoring", tags=["Unified Scoring"])
logger = logging.getLogger(__name__)

# Initialize services
unified_scoring = UnifiedScoringService()
traditional_scoring = ScoringService()

@router.get("/analyze/{symbol}")
async def analyze_symbol_unified(
    symbol: str,
    asset_type: str = Query("stock", description="Asset type: 'stock' or 'crypto'"),
    force_analysis: bool = Query(False, description="Force analysis even if traditional score < 6.0")
) -> Dict[str, Any]:
    """
    On-demand unified scoring analysis for a specific symbol
    
    Only performs expensive MTSS calculation if:
    1. Traditional score >= 6.0 (pre-filter), OR
    2. force_analysis = true
    
    This prevents API saturation by doing expensive calls only when needed.
    """
    try:
        logger.info(f"On-demand unified analysis requested for {symbol} ({asset_type})")
        
        # Get basic market data first
        market_data = await _get_basic_market_data(symbol, asset_type)
        if not market_data:
            raise HTTPException(status_code=404, detail=f"No market data found for {symbol}")
        
        # Pre-filter with traditional scoring (fast)
        if asset_type == 'crypto':
            traditional_score = traditional_scoring.calculate_crypto_score(market_data)
        else:
            traditional_score = traditional_scoring.calculate_stock_score(market_data)
        
        logger.info(f"Traditional pre-filter score for {symbol}: {traditional_score:.1f}")
        
        # Apply pre-filter logic
        if not force_analysis and traditional_score < 6.0:
            return {
                "symbol": symbol,
                "asset_type": asset_type,
                "analysis_performed": False,
                "pre_filter_result": {
                    "traditional_score": traditional_score,
                    "threshold": 6.0,
                    "reason": "Traditional score below threshold - skipping expensive MTSS analysis",
                    "recommendation": "Not suitable for detailed analysis"
                },
                "message": "Use force_analysis=true to override pre-filter",
                "timestamp": datetime.now().isoformat()
            }
        
        # Perform full unified analysis
        start_time = datetime.now()
        unified_result = unified_scoring.calculate_unified_score(symbol, asset_type, market_data)
        analysis_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Add analysis metadata
        unified_result.update({
            "analysis_performed": True,
            "pre_filter_result": {
                "traditional_score": traditional_score,
                "threshold": 6.0,
                "passed": True,
                "forced": force_analysis
            },
            "performance": {
                "analysis_time_ms": analysis_time,
                "api_calls_made": _estimate_api_calls_made()
            }
        })
        
        logger.info(f"Unified analysis completed for {symbol} in {analysis_time:.1f}ms")
        return unified_result
        
    except Exception as e:
        logger.error(f"Error in unified analysis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.get("/batch-analyze")
async def batch_analyze_symbols(
    symbols: str = Query(..., description="Comma-separated list of symbols"),
    asset_type: str = Query("stock", description="Asset type for all symbols"),
    max_symbols: int = Query(5, description="Maximum symbols to analyze (rate limiting)")
) -> Dict[str, Any]:
    """
    Batch analysis with automatic pre-filtering
    
    Only analyzes symbols with traditional score >= 6.0
    Limited to max_symbols to prevent API saturation
    """
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        symbol_list = symbol_list[:max_symbols]  # Rate limiting
        
        logger.info(f"Batch analysis requested for {len(symbol_list)} symbols")
        
        results = []
        analyzed_count = 0
        skipped_count = 0
        
        for symbol in symbol_list:
            try:
                # Get basic data for pre-filtering
                market_data = await _get_basic_market_data(symbol, asset_type)
                if not market_data:
                    results.append({
                        "symbol": symbol,
                        "status": "error",
                        "message": "No market data available"
                    })
                    continue
                
                # Pre-filter with traditional scoring
                if asset_type == 'crypto':
                    traditional_score = traditional_scoring.calculate_crypto_score(market_data)
                else:
                    traditional_score = traditional_scoring.calculate_stock_score(market_data)
                
                if traditional_score >= 6.0:
                    # Perform full analysis
                    unified_result = unified_scoring.calculate_unified_score(symbol, asset_type, market_data)
                    unified_result["pre_filter_score"] = traditional_score
                    results.append(unified_result)
                    analyzed_count += 1
                    logger.info(f"Analyzed {symbol}: unified_score={unified_result.get('unified_score', 0):.1f}")
                else:
                    # Skip expensive analysis
                    results.append({
                        "symbol": symbol,
                        "status": "skipped",
                        "traditional_score": traditional_score,
                        "reason": "Below pre-filter threshold (6.0)",
                        "analysis_performed": False
                    })
                    skipped_count += 1
                    logger.debug(f"Skipped {symbol}: traditional_score={traditional_score:.1f}")
                    
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                results.append({
                    "symbol": symbol,
                    "status": "error", 
                    "message": str(e)
                })
        
        return {
            "batch_analysis": True,
            "symbols_requested": len(symbol_list),
            "symbols_analyzed": analyzed_count,
            "symbols_skipped": skipped_count,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in batch analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")

@router.get("/high-score-candidates")
async def get_high_score_candidates(
    asset_type: str = Query("stock", description="Asset type: 'stock' or 'crypto'"),
    min_score: float = Query(6.0, description="Minimum traditional score threshold"),
    limit: int = Query(10, description="Maximum number of candidates to return")
) -> Dict[str, Any]:
    """
    Get symbols with high traditional scores (candidates for detailed MTSS analysis)
    
    This endpoint helps the frontend identify which symbols are worth
    the expensive unified scoring analysis.
    """
    try:
        logger.info(f"Fetching high-score {asset_type} candidates (score >= {min_score})")
        
        # Query database for high-score symbols
        if asset_type == 'crypto':
            table = "cryptos"
        else:
            table = "stocks"
        
        high_score_symbols = db_manager.execute_query(
            f"SELECT symbol, score, current_price, change_percent, name FROM {table} WHERE score >= ? ORDER BY score DESC LIMIT ?",
            (min_score, limit)
        )
        
        candidates = []
        for row in high_score_symbols:
            candidates.append({
                "symbol": row["symbol"],
                "traditional_score": row["score"],
                "current_price": row["current_price"],
                "change_percent": row["change_percent"],
                "name": row.get("name", row["symbol"]),
                "ready_for_mtss": True
            })
        
        logger.info(f"Found {len(candidates)} {asset_type} candidates with score >= {min_score}")
        
        return {
            "asset_type": asset_type,
            "filter_criteria": {
                "min_traditional_score": min_score,
                "limit": limit
            },
            "candidates_found": len(candidates),
            "candidates": candidates,
            "timestamp": datetime.now().isoformat(),
            "usage_note": "Use /analyze/{symbol} endpoint for detailed MTSS analysis of these candidates"
        }
        
    except Exception as e:
        logger.error(f"Error getting high-score candidates: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get candidates: {str(e)}")

@router.get("/system-status")
async def get_system_status() -> Dict[str, Any]:
    """Get unified scoring system status and configuration"""
    try:
        return {
            "unified_scoring_system": "active",
            "configuration": unified_scoring.get_system_status(),
            "api_optimization": {
                "pre_filtering_enabled": True,
                "traditional_score_threshold": 6.0,
                "on_demand_analysis": True,
                "batch_analysis_limit": 5
            },
            "usage_guidelines": {
                "recommended_workflow": [
                    "1. Use /high-score-candidates to find promising symbols",
                    "2. Use /analyze/{symbol} for detailed MTSS analysis",
                    "3. Use /batch-analyze for multiple symbols (max 5)"
                ],
                "rate_limiting": "Pre-filtering prevents API saturation",
                "performance": "~900ms per full analysis, <100ms for pre-filter"
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _get_basic_market_data(symbol: str, asset_type: str) -> Optional[Dict[str, Any]]:
    """Get basic market data from database (fast, no API calls)"""
    try:
        if asset_type == 'crypto':
            table = "cryptos"
        else:
            table = "stocks"
        
        data = db_manager.execute_query(
            f"SELECT * FROM {table} WHERE symbol = ? LIMIT 1",
            (symbol,)
        )
        
        if data:
            return dict(data[0])
        return None
        
    except Exception as e:
        logger.error(f"Error getting basic market data for {symbol}: {e}")
        return None

def _estimate_api_calls_made() -> Dict[str, int]:
    """Estimate API calls made during analysis (for monitoring)"""
    return {
        "yahoo_finance_calls": 4,  # 1M, 1W, 1d, 1h timeframes
        "estimated_total": 4,
        "note": "Actual calls may vary based on caching"
    }

@router.get("/analyze-all-cryptos")
async def analyze_all_cryptos() -> Dict[str, Any]:
    """
    Analyze all major cryptos and return scores with color indicators
    Uses caching to avoid expensive recalculations
    """
    try:
        logger.info("Mass crypto analysis requested")
        
        results = await unified_scoring.analyze_all_cryptos()
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "total_analyzed": len(results),
            "cryptos": results,
            "color_legend": {
                "green": "Strong Buy (7.0+)",
                "lightgreen": "Buy (6.0-6.9)",
                "yellow": "Hold (4.0-5.9)",
                "orange": "Weak (2.0-3.9)",
                "red": "Sell/Avoid (<2.0)",
                "gray": "Error/No Data"
            }
        }
        
    except Exception as e:
        logger.error(f"Error in mass crypto analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/crypto-overview")
async def get_crypto_overview() -> Dict[str, Any]:
    """
    Quick crypto overview with cached scores and color indicators
    Optimized for dashboard display
    """
    try:
        results = await unified_scoring.analyze_all_cryptos()
        
        # Simplify for overview display
        overview = {}
        for symbol, data in results.items():
            if 'error' in data:
                continue
                
            overview[symbol] = {
                'symbol': symbol,
                'score': data.get('unified_score', 0.0),
                'color': data.get('color_indicator', 'gray'),
                'action': data.get('recommendations', {}).get('action', 'hold'),
                'price': data.get('market_data', {}).get('current_price', 0),
                'change_percent': data.get('market_data', {}).get('change_percent', 0)
            }
        
        return {
            "status": "success",
            "overview": overview,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in crypto overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))