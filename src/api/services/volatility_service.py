"""
Volatility Service - Manages volatility tracking and filtering
Implements volatility-based entry/exit rules and risk management
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta

from ..database.database import db_manager
from .timeframe_data_service import TimeframeDataService

logger = logging.getLogger(__name__)

class VolatilityService:
    """Service for volatility analysis and risk management"""
    
    def __init__(self):
        self.timeframe_service = TimeframeDataService()
        
        # Volatility thresholds
        self.high_volatility_threshold = 0.25  # 25% daily volatility
        self.extreme_volatility_threshold = 0.40  # 40% daily volatility
        self.low_volatility_threshold = 0.10   # 10% daily volatility
        
        # Risk management parameters
        self.max_portfolio_volatility = 0.20   # 20% portfolio volatility
        self.volatility_lookback_days = 30     # 30 days for volatility calculation
        
        logger.info("Initialized Volatility Service")
    
    async def update_volatility_tracking(self) -> Dict[str, Any]:
        """Update volatility tracking for all symbols"""
        try:
            results = {
                "stocks_updated": 0,
                "cryptos_updated": 0,
                "errors": []
            }
            
            # Get all active symbols
            stocks = db_manager.execute_query("SELECT symbol FROM stocks")
            cryptos = db_manager.execute_query("SELECT symbol FROM cryptos")
            
            # Update stock volatilities
            for stock in stocks:
                try:
                    volatility_data = await self._calculate_symbol_volatility(stock['symbol'], 'stock')
                    if volatility_data:
                        self._save_volatility_data(stock['symbol'], volatility_data)
                        results["stocks_updated"] += 1
                except Exception as e:
                    results["errors"].append(f"Stock {stock['symbol']}: {str(e)}")
                    logger.error(f"Error updating volatility for stock {stock['symbol']}: {e}")
            
            # Update crypto volatilities
            for crypto in cryptos:
                try:
                    volatility_data = await self._calculate_symbol_volatility(crypto['symbol'], 'crypto')
                    if volatility_data:
                        self._save_volatility_data(crypto['symbol'], volatility_data)
                        results["cryptos_updated"] += 1
                except Exception as e:
                    results["errors"].append(f"Crypto {crypto['symbol']}: {str(e)}")
                    logger.error(f"Error updating volatility for crypto {crypto['symbol']}: {e}")
            
            logger.info(f"Updated volatility tracking: {results['stocks_updated']} stocks, {results['cryptos_updated']} cryptos")
            return results
            
        except Exception as e:
            logger.error(f"Error in update_volatility_tracking: {e}")
            return {"error": str(e), "stocks_updated": 0, "cryptos_updated": 0, "errors": []}
    
    async def _calculate_symbol_volatility(self, symbol: str, asset_type: str) -> Optional[Dict[str, Any]]:
        """Calculate volatility metrics for a symbol"""
        try:
            # Get daily data for volatility calculation
            if asset_type == 'stock':
                daily_data = await self.timeframe_service.get_stock_data(symbol, "1d", periods=50)
            else:
                daily_data = await self.timeframe_service.get_crypto_data(symbol, "1d", periods=50)
            
            if daily_data is None or len(daily_data) < 20:
                return None
            
            # Calculate returns
            daily_data['returns'] = daily_data['Close'].pct_change()
            
            # Calculate volatility metrics
            recent_data = daily_data.tail(self.volatility_lookback_days)
            
            # Daily volatility (annualized)
            daily_vol = recent_data['returns'].std() * np.sqrt(252)
            
            # ATR (Average True Range) - 14 periods
            daily_data['high_low'] = daily_data['High'] - daily_data['Low']
            daily_data['high_close'] = abs(daily_data['High'] - daily_data['Close'].shift(1))
            daily_data['low_close'] = abs(daily_data['Low'] - daily_data['Close'].shift(1))
            daily_data['true_range'] = daily_data[['high_low', 'high_close', 'low_close']].max(axis=1)
            atr_14 = daily_data['true_range'].tail(14).mean()
            
            # Volatility percentile (current vs historical)
            if len(daily_data) >= 100:
                historical_vol = daily_data['returns'].rolling(30).std() * np.sqrt(252)
                current_vol_percentile = (historical_vol.tail(100) <= daily_vol).sum() / 100
            else:
                current_vol_percentile = 0.5
            
            # Price range percent (today's high-low range)
            latest = daily_data.iloc[-1]
            price_range_percent = (latest['High'] - latest['Low']) / latest['Close']
            
            # Volume volatility
            volume_volatility = recent_data['Volume'].std() / recent_data['Volume'].mean() if recent_data['Volume'].mean() > 0 else 0
            
            # Determine if high volatility
            is_high_volatility = daily_vol > self.high_volatility_threshold
            
            return {
                'daily_volatility': daily_vol,
                'atr_14': atr_14,
                'volatility_percentile': current_vol_percentile,
                'is_high_volatility': 1 if is_high_volatility else 0,
                'price_range_percent': price_range_percent,
                'volume_volatility': volume_volatility,
                'date': datetime.now().strftime('%Y-%m-%d')
            }
            
        except Exception as e:
            logger.error(f"Error calculating volatility for {symbol}: {e}")
            return None
    
    def _save_volatility_data(self, symbol: str, volatility_data: Dict[str, Any]) -> None:
        """Save volatility data to database"""
        try:
            db_manager.execute_insert(
                """INSERT OR REPLACE INTO volatility_tracking 
                   (symbol, date, daily_volatility, atr_14, volatility_percentile, 
                    is_high_volatility, price_range_percent, volume_volatility)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    symbol, volatility_data['date'], volatility_data['daily_volatility'],
                    volatility_data['atr_14'], volatility_data['volatility_percentile'],
                    volatility_data['is_high_volatility'], volatility_data['price_range_percent'],
                    volatility_data['volume_volatility']
                )
            )
        except Exception as e:
            logger.error(f"Error saving volatility data for {symbol}: {e}")
    
    def check_volatility_filter(self, symbol: str, strategy_type: str = "swing") -> Tuple[bool, str]:
        """
        Check if symbol passes volatility filter for entry
        
        Args:
            symbol: Symbol to check
            strategy_type: 'swing' or 'crypto_competition'
        
        Returns:
            (passes_filter, reason)
        """
        try:
            # Get latest volatility data
            volatility_data = db_manager.execute_query(
                """SELECT * FROM volatility_tracking 
                   WHERE symbol = ? ORDER BY date DESC LIMIT 1""",
                (symbol,)
            )
            
            if not volatility_data:
                return True, "No volatility data available - allowing entry"
            
            vol_data = volatility_data[0]
            daily_vol = vol_data.get('daily_volatility', 0)
            is_high_vol = vol_data.get('is_high_volatility', 0)
            vol_percentile = vol_data.get('volatility_percentile', 0.5)
            
            # Strategy-specific volatility filters
            if strategy_type == "swing":
                # Swing trading - avoid extreme volatility
                if daily_vol > self.extreme_volatility_threshold:
                    return False, f"Extreme volatility {daily_vol:.1%} > {self.extreme_volatility_threshold:.1%}"
                if vol_percentile > 0.9:  # Top 10% volatility
                    return False, f"Volatility in top 10% (percentile: {vol_percentile:.1%})"
                    
            elif strategy_type == "crypto_competition":
                # Crypto competition - more permissive but still have limits
                if daily_vol > 0.50:  # 50% daily volatility limit for crypto
                    return False, f"Crypto volatility too high {daily_vol:.1%} > 50%"
                # Allow high volatility crypto (it's expected)
                    
            return True, "Volatility filter passed"
            
        except Exception as e:
            logger.error(f"Error checking volatility filter for {symbol}: {e}")
            return True, "Error in volatility check - allowing entry"
    
    def check_exit_volatility_spike(self, symbol: str, position_entry_date: str) -> Tuple[bool, str]:
        """
        Check if there's a volatility spike requiring position exit
        
        Args:
            symbol: Symbol to check
            position_entry_date: When position was entered
        
        Returns:
            (should_exit, reason)
        """
        try:
            # Get volatility data since position entry
            volatility_data = db_manager.execute_query(
                """SELECT * FROM volatility_tracking 
                   WHERE symbol = ? AND date >= ? ORDER BY date DESC LIMIT 5""",
                (symbol, position_entry_date)
            )
            
            if not volatility_data:
                return False, "No recent volatility data"
            
            # Check for extreme volatility spike
            for vol_data in volatility_data:
                daily_vol = vol_data.get('daily_volatility', 0)
                
                if daily_vol > self.extreme_volatility_threshold:
                    return True, f"Extreme volatility spike {daily_vol:.1%} - emergency exit"
            
            # Check for sustained high volatility
            recent_high_vol = sum(1 for v in volatility_data if v.get('is_high_volatility', 0) == 1)
            if recent_high_vol >= 3:  # 3+ days of high volatility
                return True, f"Sustained high volatility ({recent_high_vol} days) - exit recommended"
            
            return False, "No volatility exit signal"
            
        except Exception as e:
            logger.error(f"Error checking exit volatility for {symbol}: {e}")
            return False, "Error in volatility exit check"
    
    def get_volatility_adjusted_position_size(
        self, 
        base_size: float, 
        symbol: str, 
        strategy_type: str = "swing"
    ) -> Tuple[float, str]:
        """
        Adjust position size based on volatility
        
        Args:
            base_size: Base position size in USD
            symbol: Symbol for volatility check
            strategy_type: Strategy type for adjustment rules
        
        Returns:
            (adjusted_size, reason)
        """
        try:
            # Get latest volatility data
            volatility_data = db_manager.execute_query(
                """SELECT * FROM volatility_tracking 
                   WHERE symbol = ? ORDER BY date DESC LIMIT 1""",
                (symbol,)
            )
            
            if not volatility_data:
                return base_size, "No volatility data - using base size"
            
            vol_data = volatility_data[0]
            daily_vol = vol_data.get('daily_volatility', 0.15)  # Default 15%
            vol_percentile = vol_data.get('volatility_percentile', 0.5)
            
            # Calculate adjustment factor
            adjustment_factor = 1.0
            reason = "Standard sizing"
            
            if strategy_type == "swing":
                # Swing trading adjustments
                if daily_vol > 0.30:  # 30% volatility
                    adjustment_factor = 0.6  # Reduce size by 40%
                    reason = f"High volatility {daily_vol:.1%} - reduced size 40%"
                elif daily_vol > 0.20:  # 20% volatility
                    adjustment_factor = 0.8  # Reduce size by 20%
                    reason = f"Moderate volatility {daily_vol:.1%} - reduced size 20%"
                elif daily_vol < 0.08:  # Low volatility
                    adjustment_factor = 1.2  # Increase size by 20%
                    reason = f"Low volatility {daily_vol:.1%} - increased size 20%"
                    
            elif strategy_type == "crypto_competition":
                # Crypto competition adjustments (more aggressive)
                if daily_vol > 0.40:  # 40% volatility
                    adjustment_factor = 0.7  # Reduce size by 30%
                    reason = f"High crypto volatility {daily_vol:.1%} - reduced size 30%"
                elif daily_vol > 0.25:  # 25% volatility
                    adjustment_factor = 0.9  # Reduce size by 10%
                    reason = f"Moderate crypto volatility {daily_vol:.1%} - reduced size 10%"
                # Don't increase crypto sizes for low volatility
            
            # Apply percentile adjustment
            if vol_percentile > 0.8:  # Top 20% volatility
                adjustment_factor *= 0.9  # Additional 10% reduction
                reason += " (top quintile volatility)"
            
            adjusted_size = base_size * adjustment_factor
            
            logger.debug(f"Volatility adjustment for {symbol}: {base_size:.2f} -> {adjusted_size:.2f} ({reason})")
            return adjusted_size, reason
            
        except Exception as e:
            logger.error(f"Error calculating volatility-adjusted size for {symbol}: {e}")
            return base_size, f"Error in volatility adjustment - using base size"
    
    def get_volatility_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get volatility summary for the past N days"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            # Get high volatility symbols
            high_vol_data = db_manager.execute_query(
                """SELECT symbol, daily_volatility, date 
                   FROM volatility_tracking 
                   WHERE is_high_volatility = 1 AND date >= ?
                   ORDER BY daily_volatility DESC""",
                (cutoff_date,)
            )
            
            # Get overall volatility stats
            vol_stats = db_manager.execute_query(
                """SELECT 
                     AVG(daily_volatility) as avg_volatility,
                     MAX(daily_volatility) as max_volatility,
                     MIN(daily_volatility) as min_volatility,
                     COUNT(CASE WHEN is_high_volatility = 1 THEN 1 END) as high_vol_count,
                     COUNT(*) as total_count
                   FROM volatility_tracking 
                   WHERE date >= ?""",
                (cutoff_date,)
            )
            
            stats = vol_stats[0] if vol_stats else {}
            
            return {
                "period_days": days,
                "high_volatility_symbols": [dict(row) for row in high_vol_data[:10]],
                "average_volatility": stats.get('avg_volatility', 0),
                "max_volatility": stats.get('max_volatility', 0),
                "min_volatility": stats.get('min_volatility', 0),
                "high_vol_percentage": (stats.get('high_vol_count', 0) / max(stats.get('total_count', 1), 1)) * 100,
                "total_symbols_tracked": stats.get('total_count', 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting volatility summary: {e}")
            return {"error": str(e)}
    
    def is_market_stressed(self) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Determine if market is in stressed/high volatility environment
        
        Returns:
            (is_stressed, reason, metrics)
        """
        try:
            # Get recent volatility data
            recent_data = db_manager.execute_query(
                """SELECT symbol, daily_volatility, is_high_volatility 
                   FROM volatility_tracking 
                   WHERE date >= date('now', '-3 days')"""
            )
            
            if not recent_data:
                return False, "No recent volatility data", {}
            
            # Calculate stress metrics
            total_symbols = len(recent_data)
            high_vol_count = sum(1 for row in recent_data if row['is_high_volatility'] == 1)
            avg_volatility = np.mean([row['daily_volatility'] for row in recent_data])
            max_volatility = max([row['daily_volatility'] for row in recent_data])
            
            high_vol_percentage = (high_vol_count / total_symbols) * 100
            
            metrics = {
                "high_vol_percentage": high_vol_percentage,
                "average_volatility": avg_volatility,
                "max_volatility": max_volatility,
                "symbols_tracked": total_symbols
            }
            
            # Determine if market is stressed
            is_stressed = False
            reasons = []
            
            if high_vol_percentage > 50:  # More than 50% of symbols high vol
                is_stressed = True
                reasons.append(f"{high_vol_percentage:.1f}% symbols high volatility")
            
            if avg_volatility > 0.35:  # Average volatility > 35%
                is_stressed = True
                reasons.append(f"Market average volatility {avg_volatility:.1%}")
            
            if max_volatility > 0.60:  # Any symbol > 60% volatility
                is_stressed = True
                reasons.append(f"Extreme volatility detected {max_volatility:.1%}")
            
            reason = "; ".join(reasons) if is_stressed else "Market volatility normal"
            
            logger.info(f"Market stress check: {is_stressed} - {reason}")
            return is_stressed, reason, metrics
            
        except Exception as e:
            logger.error(f"Error checking market stress: {e}")
            return False, "Error in stress analysis", {}

# Global instance
volatility_service = VolatilityService()