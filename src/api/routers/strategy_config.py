"""
Strategy Configuration Router
Permite configurar y cambiar estrategias de trading
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional

from ..strategies.trading_config import TRADING_CONFIG

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/strategy", tags=["Strategy Configuration"])

class StrategyConfigUpdate(BaseModel):
    """Request model para actualizar configuración de estrategias"""
    crypto_strategy: Optional[str] = None  # "competition" o "mtss"
    active_strategy: Optional[str] = None  # Estrategia general activa
    buy_score_threshold: Optional[float] = None
    sell_score_threshold: Optional[float] = None
    high_volatility_bypass: Optional[bool] = None

@router.get("/config")
async def get_strategy_config():
    """Get current strategy configuration"""
    try:
        config_dict = {
            "active_strategy": TRADING_CONFIG.active_strategy,
            "crypto_strategy": TRADING_CONFIG.crypto_strategy,
            "buy_score_threshold": TRADING_CONFIG.buy_score_threshold,
            "sell_score_threshold": TRADING_CONFIG.sell_score_threshold,
            "short_trading_enabled": TRADING_CONFIG.short_trading_enabled,
            "high_volatility_bypass": TRADING_CONFIG.high_volatility_bypass,
            "max_positions_stocks": TRADING_CONFIG.max_positions_stocks,
            "max_positions_crypto": TRADING_CONFIG.max_positions_crypto,
            "auto_strategy_switching": TRADING_CONFIG.auto_strategy_switching
        }
        
        return {
            "status": "success",
            "config": config_dict,
            "available_crypto_strategies": ["competition", "mtss"],
            "crypto_strategy_details": {
                "competition": {
                    "name": "Crypto Competition Strategy", 
                    "description": "4H/1H timeframes, aggressive thresholds (8.0/3.5), volatility filters",
                    "risk_level": "HIGH",
                    "timeframes": ["4h", "1h"]
                },
                "mtss": {
                    "name": "MTSS Crypto Strategy",
                    "description": "1M→1W→1D→4H multi-timeframe scoring, comprehensive analysis",  
                    "risk_level": "MEDIUM-HIGH",
                    "timeframes": ["1M", "1W", "1d", "4h"]
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting strategy config: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving strategy configuration: {str(e)}")

@router.post("/config")
async def update_strategy_config(config_update: StrategyConfigUpdate):
    """Update strategy configuration"""
    try:
        updated_fields = {}
        
        # Update crypto strategy
        if config_update.crypto_strategy is not None:
            if config_update.crypto_strategy not in ["competition", "mtss"]:
                raise HTTPException(
                    status_code=400, 
                    detail="crypto_strategy must be 'competition' or 'mtss'"
                )
            TRADING_CONFIG.crypto_strategy = config_update.crypto_strategy
            updated_fields["crypto_strategy"] = config_update.crypto_strategy
            logger.info(f"Updated crypto strategy to: {config_update.crypto_strategy}")
        
        # Update other fields if provided
        if config_update.active_strategy is not None:
            TRADING_CONFIG.active_strategy = config_update.active_strategy
            updated_fields["active_strategy"] = config_update.active_strategy
            
        if config_update.buy_score_threshold is not None:
            if not (0.0 <= config_update.buy_score_threshold <= 10.0):
                raise HTTPException(status_code=400, detail="buy_score_threshold must be between 0.0 and 10.0")
            TRADING_CONFIG.buy_score_threshold = config_update.buy_score_threshold
            updated_fields["buy_score_threshold"] = config_update.buy_score_threshold
            
        if config_update.sell_score_threshold is not None:
            if not (0.0 <= config_update.sell_score_threshold <= 10.0):
                raise HTTPException(status_code=400, detail="sell_score_threshold must be between 0.0 and 10.0")
            TRADING_CONFIG.sell_score_threshold = config_update.sell_score_threshold
            updated_fields["sell_score_threshold"] = config_update.sell_score_threshold
            
        if config_update.high_volatility_bypass is not None:
            TRADING_CONFIG.high_volatility_bypass = config_update.high_volatility_bypass
            updated_fields["high_volatility_bypass"] = config_update.high_volatility_bypass
        
        return {
            "status": "success",
            "message": "Strategy configuration updated successfully",
            "updated_fields": updated_fields,
            "current_config": {
                "crypto_strategy": TRADING_CONFIG.crypto_strategy,
                "active_strategy": TRADING_CONFIG.active_strategy,
                "buy_score_threshold": TRADING_CONFIG.buy_score_threshold,
                "sell_score_threshold": TRADING_CONFIG.sell_score_threshold,
                "high_volatility_bypass": TRADING_CONFIG.high_volatility_bypass
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating strategy config: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating strategy configuration: {str(e)}")

@router.get("/crypto/comparison")
async def compare_crypto_strategies():
    """Compare available crypto strategies"""
    try:
        comparison = {
            "strategies": {
                "competition": {
                    "name": "Crypto Competition Strategy",
                    "description": "Fast-moving crypto strategy optimized for high volatility",
                    "characteristics": {
                        "timeframes": ["4h", "1h"],
                        "buy_threshold": 8.0,
                        "sell_threshold": 3.5,
                        "hold_period": "1-10 days",
                        "risk_per_trade": "5%",
                        "stop_loss": "12%",
                        "take_profit": "25%",
                        "volatility_limit": "15%"
                    },
                    "pros": [
                        "Fast execution with 4H/1H analysis",
                        "High profit targets (25%)",
                        "Optimized for volatile crypto markets",
                        "Built-in volatility filters"
                    ],
                    "cons": [
                        "Higher risk (5% per trade)",
                        "Less comprehensive analysis",
                        "May miss longer-term trends"
                    ]
                },
                "mtss": {
                    "name": "MTSS Crypto Strategy", 
                    "description": "Comprehensive multi-timeframe analysis for crypto",
                    "characteristics": {
                        "timeframes": ["1M", "1W", "1d", "4h"],
                        "buy_threshold": "Variable (7.0-9.0)",
                        "sell_threshold": "Variable",
                        "hold_period": "1-10 days",
                        "risk_per_trade": "5%",
                        "stop_loss": "15%",
                        "take_profit": "30%",
                        "volatility_limit": "20%"
                    },
                    "pros": [
                        "Comprehensive 4-timeframe analysis",
                        "Monthly filter prevents bad macro entries",
                        "Position sizing based on confidence",
                        "RSI divergence detection",
                        "Higher profit targets (30%)"
                    ],
                    "cons": [
                        "More complex analysis (slower)",
                        "Requires more historical data",
                        "May miss some fast opportunities"
                    ]
                }
            },
            "recommendations": {
                "use_competition_when": [
                    "Market is highly volatile (>15% daily)",
                    "You want faster trade execution",
                    "Short-term opportunities (1-3 days)",
                    "Limited historical data available"
                ],
                "use_mtss_when": [
                    "Want comprehensive analysis",
                    "Looking for higher confidence trades",
                    "Medium-term holds (3-10 days)",
                    "Sufficient historical data available",
                    "Want to avoid bad macro timing"
                ]
            }
        }
        
        return {
            "status": "success", 
            "comparison": comparison,
            "current_strategy": TRADING_CONFIG.crypto_strategy
        }
        
    except Exception as e:
        logger.error(f"Error comparing crypto strategies: {e}")
        raise HTTPException(status_code=500, detail=f"Error comparing strategies: {str(e)}")

@router.post("/crypto/switch")
async def switch_crypto_strategy(strategy: str):
    """Quick switch crypto strategy"""
    try:
        if strategy not in ["competition", "mtss"]:
            raise HTTPException(
                status_code=400,
                detail="Strategy must be 'competition' or 'mtss'"
            )
        
        old_strategy = TRADING_CONFIG.crypto_strategy
        TRADING_CONFIG.crypto_strategy = strategy
        
        logger.info(f"Switched crypto strategy from '{old_strategy}' to '{strategy}'")
        
        return {
            "status": "success",
            "message": f"Crypto strategy switched to '{strategy}'",
            "previous_strategy": old_strategy,
            "new_strategy": strategy,
            "next_autotrader_cycle_will_use": strategy
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching crypto strategy: {e}")
        raise HTTPException(status_code=500, detail=f"Error switching strategy: {str(e)}")