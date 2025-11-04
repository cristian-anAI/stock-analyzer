"""
Box Strategy API Router

Endpoints for monitoring and evaluating box strategy trades across multiple markets.

Endpoints:
- GET /api/v1/box-strategy/markets - Get all markets status
- GET /api/v1/box-strategy/market/{code} - Get specific market details
- GET /api/v1/box-strategy/tradeable - Get only tradeable setups
- GET /api/v1/box-strategy/dashboard - Dashboard data with summaries
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from ..services.box_strategy_service import BoxStrategyService, MARKET_CONFIGS
from ..services.box_strategy_monitor import box_strategy_monitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/box-strategy")

# Initialize service (singleton pattern)
_box_service = None


def get_box_service(ml_version: str = "1") -> BoxStrategyService:
    """Get or create box strategy service instance"""
    global _box_service
    if _box_service is None or _box_service.ml_version != ml_version:
        _box_service = BoxStrategyService(ml_version=ml_version)
    return _box_service


@router.get("/markets", summary="Get all markets status")
async def get_all_markets(
    ml_version: str = Query("1", description="ML model version to use")
) -> Dict[str, Any]:
    """
    Get status and predictions for all supported markets.

    Returns box formations, breakouts, and ML confidence predictions for each market
    based on their local trading hours.

    **Response includes**:
    - Market status (box period, post-box, next box time)
    - Box formation details (high, low, range)
    - Breakout detection (LONG/SHORT)
    - ML predictions (win probability, confidence, recommendation)

    **Markets covered**:
    - SPX (S&P 500) - 8:30-10:00 AM ET
    - NDX (NASDAQ 100) - 8:30-10:00 AM ET
    - DAX (Germany) - 8:00-9:30 AM CET
    - FTSE (UK) - 8:00-9:30 AM GMT
    - STOXX (Europe) - 8:00-9:30 AM CET
    - CAC (France) - 8:00-9:30 AM CET
    - NKY (Japan) - 9:00-10:30 AM JST
    - HSI (Hong Kong) - 9:30-11:00 AM HKT
    - ASX (Australia) - 10:00-11:30 AM AEST
    - IBEX (Spain) - 9:00-10:30 AM CET
    """
    try:
        service = get_box_service(ml_version)
        markets = service.get_all_markets_status()

        # Calculate summary statistics
        total_markets = len(markets)
        box_complete_count = sum(
            1 for m in markets
            if m.get('status') and m['status'].get('box_complete')
        )
        breakout_count = sum(
            1 for m in markets
            if m.get('box_setup') and m['box_setup'].get('breakout_detected')
        )
        high_confidence_count = sum(
            1 for m in markets
            if m.get('ml_prediction') and m['ml_prediction'].get('confidence_level') == 'HIGH'
        )

        return {
            "timestamp": datetime.now().isoformat(),
            "ml_version": ml_version,
            "summary": {
                "total_markets": total_markets,
                "box_complete": box_complete_count,
                "breakouts_detected": breakout_count,
                "high_confidence_setups": high_confidence_count
            },
            "markets": markets
        }

    except Exception as e:
        logger.error(f"Error getting all markets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/{market_code}", summary="Get specific market details")
async def get_market_detail(
    market_code: str,
    ml_version: str = Query("1", description="ML model version to use")
) -> Dict[str, Any]:
    """
    Get detailed information for a specific market.

    **Path Parameters**:
    - market_code: Market code (SPX, NDX, DAX, FTSE, STOXX, CAC, NKY, HSI, ASX, IBEX)

    **Returns**:
    - Complete market status
    - Box formation details
    - Breakout analysis
    - ML prediction with confidence levels
    - Trade setup details (entry, stop, targets)
    """
    market_code = market_code.upper()

    if market_code not in MARKET_CONFIGS:
        raise HTTPException(
            status_code=404,
            detail=f"Market '{market_code}' not found. Available: {list(MARKET_CONFIGS.keys())}"
        )

    try:
        service = get_box_service(ml_version)

        # Get market status
        status = service.get_market_status(market_code)

        # Get box setup
        box_setup = None
        ml_prediction = None

        if status.box_complete:
            box_setup = service.get_box_setup(market_code)

            if box_setup and box_setup.breakout_detected:
                ml_prediction = service.get_ml_prediction(box_setup)

        # Get market config
        config = MARKET_CONFIGS[market_code]

        return {
            "timestamp": datetime.now().isoformat(),
            "market": market_code,
            "name": config.name,
            "timezone": config.timezone,
            "box_hours": {
                "start": config.box_start.strftime("%H:%M"),
                "end": config.box_end.strftime("%H:%M")
            },
            "status": status.__dict__,
            "box_setup": box_setup.__dict__ if box_setup else None,
            "ml_prediction": ml_prediction.__dict__ if ml_prediction else None
        }

    except Exception as e:
        logger.error(f"Error getting market {market_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tradeable", summary="Get tradeable setups")
async def get_tradeable_setups(
    ml_version: str = Query("1", description="ML model version to use"),
    min_confidence: str = Query(None, description="Minimum confidence level (HIGH, MEDIUM, LOW)")
) -> Dict[str, Any]:
    """
    Get only markets with tradeable setups (box complete + breakout detected).

    Useful for filtering markets that currently have active trade opportunities.

    **Query Parameters**:
    - ml_version: ML model version (default: "1")
    - min_confidence: Filter by minimum confidence (HIGH, MEDIUM, LOW)

    **Returns**:
    - List of markets with breakouts
    - ML predictions for each
    - Trade setup details
    """
    try:
        service = get_box_service(ml_version)
        tradeable = service.get_tradeable_setups()

        # Filter by confidence if specified
        if min_confidence:
            min_confidence = min_confidence.upper()
            confidence_order = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}

            if min_confidence not in confidence_order:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid confidence level. Use: HIGH, MEDIUM, or LOW"
                )

            min_level = confidence_order[min_confidence]

            tradeable = [
                m for m in tradeable
                if m.get('ml_prediction') and
                confidence_order.get(m['ml_prediction'].get('confidence_level', 'LOW'), 0) >= min_level
            ]

        return {
            "timestamp": datetime.now().isoformat(),
            "ml_version": ml_version,
            "filter": {
                "min_confidence": min_confidence
            },
            "count": len(tradeable),
            "setups": tradeable
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tradeable setups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard", summary="Get dashboard data")
async def get_dashboard_data(
    ml_version: str = Query("1", description="ML model version to use")
) -> Dict[str, Any]:
    """
    Get comprehensive dashboard data for box strategy monitoring.

    **Returns**:
    - Summary statistics
    - Markets by status (pending, active, complete)
    - High confidence setups
    - Recent breakouts
    - Next box times for each market
    """
    try:
        service = get_box_service(ml_version)
        all_markets = service.get_all_markets_status()

        # Categorize markets
        pending_box = []
        active_box = []
        box_complete = []
        breakouts = []
        high_confidence = []

        for market in all_markets:
            if 'error' in market:
                continue

            status = market.get('status')
            if status is None:
                logger.warning(f"Market {market.get('market', 'UNKNOWN')} has no status")
                continue

            if status.get('is_box_period'):
                active_box.append(market)
            elif status.get('box_complete'):
                box_complete.append(market)

                box_setup = market.get('box_setup')
                if box_setup and box_setup.get('breakout_detected'):
                    breakouts.append(market)

                    ml_pred = market.get('ml_prediction')
                    if ml_pred and ml_pred.get('confidence_level') == 'HIGH':
                        high_confidence.append(market)
            else:
                pending_box.append(market)

        # Calculate statistics
        total_markets = len([m for m in all_markets if 'error' not in m])
        avg_win_prob = 0.0

        if breakouts:
            win_probs = [
                m['ml_prediction']['win_probability']
                for m in breakouts
                if m.get('ml_prediction') and m['ml_prediction'] is not None
            ]
            if win_probs:
                avg_win_prob = sum(win_probs) / len(win_probs)

        # Get active trades summary
        active_trades = box_strategy_monitor.active_trades
        active_trades_count = len(active_trades)
        tp1_achieved_count = sum(1 for t in active_trades.values() if t.tp1_hit)
        stop_moved_to_breakeven_count = sum(1 for t in active_trades.values() if t.stop_moved_to_breakeven)

        # Build active trades summary
        active_trades_summary = []
        for trade in active_trades.values():
            active_trades_summary.append({
                "market": trade.market,
                "direction": trade.direction,
                "entry_price": trade.entry_price,
                "entry_time": trade.entry_time,
                "stop_loss": trade.stop_loss,
                "tp1": trade.tp1,
                "tp2": trade.tp2,
                "tp3": trade.tp3,
                "risk_points": trade.risk_points,
                "ml_confidence": trade.ml_confidence,
                "ml_win_probability": trade.ml_probability,
                "tp1_hit": trade.tp1_hit,
                "stop_moved_to_breakeven": trade.stop_moved_to_breakeven
            })

        return {
            "timestamp": datetime.now().isoformat(),
            "ml_version": ml_version,
            "summary": {
                "total_markets": total_markets,
                "pending_box": len(pending_box),
                "active_box": len(active_box),
                "box_complete": len(box_complete),
                "breakouts": len(breakouts),
                "high_confidence": len(high_confidence),
                "avg_win_probability": round(avg_win_prob, 3),
                # NEW: Active trades statistics
                "active_trades_count": active_trades_count,
                "tp1_achieved_count": tp1_achieved_count,
                "stop_moved_to_breakeven_count": stop_moved_to_breakeven_count
            },
            "markets_by_status": {
                "pending": [m['market'] for m in pending_box],
                "active": [m['market'] for m in active_box],
                "complete": [m['market'] for m in box_complete]
            },
            "high_confidence_setups": high_confidence,
            "all_breakouts": breakouts,
            "all_markets": all_markets,
            # NEW: Active trades summary
            "active_trades_summary": active_trades_summary
        }

    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config", summary="Get market configurations")
async def get_market_configs() -> Dict[str, Any]:
    """
    Get configuration for all supported markets.

    **Returns**:
    - Market codes and names
    - Timezones
    - Box formation hours (local time)
    - Currency and contract specifications
    """
    configs = {}

    for code, config in MARKET_CONFIGS.items():
        configs[code] = {
            "code": code,
            "name": config.name,
            "ticker": config.ticker,
            "timezone": config.timezone,
            "box_hours": {
                "start": config.box_start.strftime("%H:%M"),
                "end": config.box_end.strftime("%H:%M")
            },
            "currency": config.currency,
            "points_per_contract": config.points_per_contract
        }

    return {
        "markets": configs,
        "total": len(configs)
    }


@router.get("/active-trades", summary="Get active box strategy trades")
async def get_active_trades() -> Dict[str, Any]:
    """
    Get currently active box strategy trades (NDX, SPX, RTY).

    **Returns**:
    - Active trades count
    - Trade details with entry, stops, targets
    - ML confidence and win probability
    - TP1 status and breakeven info
    - RSI divergence status (15min timeframe)

    **Monitored Markets**: NDX (NASDAQ), SPX (S&P 500), RTY (Russell 2000)
    """
    try:
        active_trades = box_strategy_monitor.active_trades

        trades_list = []
        for breakout_key, trade in active_trades.items():
            trades_list.append({
                "market": trade.market,
                "direction": trade.direction,
                "entry_price": trade.entry_price,
                "entry_time": trade.entry_time,
                "stop_loss": trade.stop_loss,
                "current_stop_loss": trade.stop_loss,  # May be different if moved to BE
                "tp1": trade.tp1,
                "tp2": trade.tp2,
                "tp3": trade.tp3,
                "box_high": trade.box_high,
                "box_low": trade.box_low,
                "box_range": trade.box_range,
                "risk_points": trade.risk_points,
                "ml_confidence": trade.ml_confidence,
                "ml_win_probability": trade.ml_probability,
                "tp1_hit": trade.tp1_hit,
                "stop_moved_to_breakeven": trade.stop_moved_to_breakeven,
                "breakout_key": breakout_key
            })

        return {
            "timestamp": datetime.now().isoformat(),
            "active_trades_count": len(trades_list),
            "trades": trades_list
        }

    except Exception as e:
        logger.error(f"Error getting active trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))
