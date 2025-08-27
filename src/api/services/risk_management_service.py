"""
Risk Management Service - Comprehensive risk management for autotrader
Handles position sizing, portfolio risk, correlation analysis, and drawdown protection
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta

from ..database.database import db_manager
from .portfolio_manager import portfolio_manager
from .volatility_service import volatility_service

logger = logging.getLogger(__name__)

class RiskManagementService:
    """Service for portfolio risk management and position sizing"""
    
    def __init__(self):
        # Portfolio risk limits
        self.max_portfolio_risk = 0.20  # 20% max portfolio risk
        self.max_sector_concentration = 0.30  # 30% max in any sector
        self.max_correlation_exposure = 0.40  # 40% max in highly correlated assets
        
        # Drawdown protection
        self.max_drawdown_threshold = 0.15  # 15% max drawdown before defensive mode
        self.stop_trading_drawdown = 0.25   # 25% stop all trading
        
        # Position sizing
        self.min_position_size = 100  # Min $100 position
        self.max_position_size_portfolio_pct = 0.15  # 15% max single position
        
        # Risk per asset type
        self.stock_risk_limits = {
            'max_positions': 15,
            'max_allocation_pct': 70,
            'max_single_position_pct': 12,
            'daily_trade_limit': 5
        }
        
        self.crypto_risk_limits = {
            'max_positions': 8,
            'max_allocation_pct': 30,
            'max_single_position_pct': 15,
            'daily_trade_limit': 3
        }
        
        logger.info("Initialized Risk Management Service")
    
    def calculate_position_size(
        self, 
        symbol: str, 
        asset_type: str, 
        strategy_confidence: float,
        current_price: float,
        volatility: Optional[float] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate optimal position size based on multiple risk factors
        
        Args:
            symbol: Symbol to size
            asset_type: 'stock' or 'crypto'
            strategy_confidence: 0-10 confidence from strategy
            current_price: Current market price
            volatility: Optional volatility measure
        
        Returns:
            (position_size_usd, sizing_details)
        """
        try:
            # Get portfolio info
            portfolio_value = portfolio_manager.get_total_portfolio_value()
            available_capital = self._get_available_capital_for_asset_type(asset_type)
            
            sizing_details = {
                "base_method": "kelly_criterion",
                "adjustments": [],
                "portfolio_value": portfolio_value,
                "available_capital": available_capital
            }
            
            # 1. Base sizing using modified Kelly Criterion
            base_size = self._calculate_kelly_size(
                available_capital, strategy_confidence, asset_type, volatility
            )
            sizing_details["base_kelly_size"] = base_size
            
            # 2. Apply volatility adjustment
            vol_adjusted_size, vol_reason = volatility_service.get_volatility_adjusted_position_size(
                base_size, symbol, "swing" if asset_type == "stock" else "crypto_competition"
            )
            sizing_details["volatility_adjustment"] = vol_reason
            
            # 3. Apply portfolio concentration limits
            concentration_size = self._apply_concentration_limits(
                vol_adjusted_size, asset_type, portfolio_value
            )
            sizing_details["concentration_limit"] = concentration_size != vol_adjusted_size
            
            # 4. Apply correlation limits (if symbol is correlated with existing positions)
            correlation_size = self._apply_correlation_limits(
                concentration_size, symbol, asset_type
            )
            sizing_details["correlation_adjustment"] = correlation_size != concentration_size
            
            # 5. Apply minimum/maximum position size
            final_size = max(self.min_position_size, 
                           min(correlation_size, portfolio_value * self.max_position_size_portfolio_pct))
            
            sizing_details["final_size"] = final_size
            sizing_details["size_as_portfolio_pct"] = (final_size / portfolio_value) * 100
            
            # Validate against asset type limits
            asset_limits = self.stock_risk_limits if asset_type == 'stock' else self.crypto_risk_limits
            max_single_position = portfolio_value * (asset_limits['max_single_position_pct'] / 100)
            
            if final_size > max_single_position:
                final_size = max_single_position
                sizing_details["adjustments"].append(f"Capped at {asset_type} single position limit")
            
            logger.debug(f"Position sizing for {symbol}: ${final_size:.2f} ({(final_size/portfolio_value)*100:.1f}%)")
            return final_size, sizing_details
            
        except Exception as e:
            logger.error(f"Error calculating position size for {symbol}: {e}")
            # Conservative fallback
            fallback_size = min(1000, portfolio_manager.get_total_portfolio_value() * 0.02)
            return fallback_size, {"error": str(e), "fallback_used": True}
    
    def _calculate_kelly_size(
        self, 
        available_capital: float, 
        confidence: float, 
        asset_type: str,
        volatility: Optional[float] = None
    ) -> float:
        """Calculate position size using modified Kelly Criterion"""
        try:
            # Convert confidence to win probability (0-10 scale to 0.5-0.9 probability)
            win_prob = 0.5 + (confidence - 5) * 0.08  # Maps 5->0.5, 10->0.9
            win_prob = max(0.5, min(0.9, win_prob))
            
            # Estimate expected return based on asset type and confidence
            if asset_type == 'stock':
                # Conservative estimates for stocks
                expected_return = 0.08 + (confidence - 5) * 0.02  # 8-18% expected return
                max_loss = 0.08  # 8% max loss (stop loss)
            else:
                # More aggressive estimates for crypto
                expected_return = 0.15 + (confidence - 5) * 0.05  # 15-40% expected return
                max_loss = 0.12  # 12% max loss (wider stops for volatility)
            
            # Adjust for volatility if provided
            if volatility and volatility > 0:
                # Higher volatility reduces position size
                volatility_adjustment = min(1.0, 0.2 / volatility)  # Cap at 20% volatility
                expected_return *= volatility_adjustment
            
            # Modified Kelly formula: f = (bp - q) / b
            # Where b = odds received (expected_return/max_loss), p = win_prob, q = 1-p
            odds = expected_return / max_loss
            kelly_fraction = (odds * win_prob - (1 - win_prob)) / odds
            
            # Conservative scaling: use 25% of Kelly (Kelly can be aggressive)
            conservative_kelly = kelly_fraction * 0.25
            conservative_kelly = max(0.01, min(0.15, conservative_kelly))  # Cap between 1-15%
            
            position_size = available_capital * conservative_kelly
            
            logger.debug(f"Kelly calculation: prob={win_prob:.3f}, return={expected_return:.3f}, "
                        f"fraction={kelly_fraction:.3f}, conservative={conservative_kelly:.3f}")
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error in Kelly calculation: {e}")
            return available_capital * 0.02  # Fallback to 2%
    
    def _get_available_capital_for_asset_type(self, asset_type: str) -> float:
        """Get available capital for asset type considering allocation limits"""
        try:
            if asset_type == 'stock':
                total_capital = portfolio_manager.liquid_capital_stocks + portfolio_manager.invested_capital_stocks
                return portfolio_manager.liquid_capital_stocks
            else:  # crypto
                total_capital = portfolio_manager.liquid_capital_crypto + portfolio_manager.invested_capital_crypto
                return portfolio_manager.liquid_capital_crypto
        except Exception as e:
            logger.error(f"Error getting available capital: {e}")
            return 1000  # Conservative fallback
    
    def _apply_concentration_limits(self, position_size: float, asset_type: str, portfolio_value: float) -> float:
        """Apply portfolio concentration limits"""
        try:
            # Get current allocation for asset type
            current_positions = db_manager.execute_query(
                "SELECT SUM(value) as total_value FROM positions WHERE type = ? AND source = 'autotrader'",
                (asset_type,)
            )
            
            current_allocation = current_positions[0]['total_value'] if current_positions and current_positions[0]['total_value'] else 0
            
            # Check against asset type allocation limits
            asset_limits = self.stock_risk_limits if asset_type == 'stock' else self.crypto_risk_limits
            max_allocation = portfolio_value * (asset_limits['max_allocation_pct'] / 100)
            
            remaining_capacity = max_allocation - current_allocation
            
            if position_size > remaining_capacity:
                logger.warning(f"Position size reduced due to {asset_type} allocation limit: "
                             f"${position_size:.2f} -> ${remaining_capacity:.2f}")
                return max(0, remaining_capacity)
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error applying concentration limits: {e}")
            return position_size
    
    def _apply_correlation_limits(self, position_size: float, symbol: str, asset_type: str) -> float:
        """Apply correlation-based position size limits"""
        try:
            # Get existing positions
            existing_positions = db_manager.execute_query(
                "SELECT symbol, value FROM positions WHERE type = ? AND source = 'autotrader'",
                (asset_type,)
            )
            
            if not existing_positions:
                return position_size
            
            # Simple sector/correlation check for stocks
            if asset_type == 'stock':
                # Check if we already have positions in same sector
                symbol_sector = self._get_stock_sector(symbol)
                if symbol_sector:
                    sector_exposure = sum(pos['value'] for pos in existing_positions 
                                        if self._get_stock_sector(pos['symbol']) == symbol_sector)
                    
                    portfolio_value = portfolio_manager.get_total_portfolio_value()
                    sector_percentage = (sector_exposure / portfolio_value) * 100
                    
                    if sector_percentage > self.max_sector_concentration * 100:
                        # Reduce position size to maintain sector limit
                        reduction_factor = 0.5  # 50% reduction for sector concentration
                        return position_size * reduction_factor
            
            # For crypto, check for major coin correlation (BTC, ETH dominance)
            elif asset_type == 'crypto':
                if symbol in ['BTC-USD', 'ETH-USD']:
                    # Major coins - allow full size
                    return position_size
                else:
                    # Alt coins - check total alt exposure
                    major_coins = ['BTC-USD', 'ETH-USD']
                    alt_exposure = sum(pos['value'] for pos in existing_positions 
                                     if pos['symbol'] not in major_coins)
                    
                    portfolio_value = portfolio_manager.get_total_portfolio_value()
                    alt_percentage = (alt_exposure / portfolio_value) * 100
                    
                    if alt_percentage > 15:  # 15% max alt coin exposure
                        return position_size * 0.7  # Reduce alt coin position
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error applying correlation limits: {e}")
            return position_size
    
    def _get_stock_sector(self, symbol: str) -> Optional[str]:
        """Get sector for stock symbol"""
        try:
            stock_data = db_manager.execute_query(
                "SELECT sector FROM stocks WHERE symbol = ?", (symbol,)
            )
            return stock_data[0]['sector'] if stock_data else None
        except Exception:
            return None
    
    def check_portfolio_risk_limits(self) -> Tuple[bool, List[str]]:
        """
        Check if portfolio is within risk limits
        
        Returns:
            (is_within_limits, warnings)
        """
        try:
            warnings = []
            is_within_limits = True
            
            # 1. Check drawdown
            drawdown_pct = self._calculate_current_drawdown()
            if drawdown_pct > self.max_drawdown_threshold:
                is_within_limits = False
                warnings.append(f"Portfolio drawdown {drawdown_pct:.1%} exceeds limit {self.max_drawdown_threshold:.1%}")
            
            if drawdown_pct > self.stop_trading_drawdown:
                is_within_limits = False
                warnings.append(f"CRITICAL: Drawdown {drawdown_pct:.1%} - trading should be stopped")
            
            # 2. Check position count limits
            stock_count = self._get_position_count('stock')
            crypto_count = self._get_position_count('crypto')
            
            if stock_count > self.stock_risk_limits['max_positions']:
                warnings.append(f"Too many stock positions: {stock_count}/{self.stock_risk_limits['max_positions']}")
                is_within_limits = False
                
            if crypto_count > self.crypto_risk_limits['max_positions']:
                warnings.append(f"Too many crypto positions: {crypto_count}/{self.crypto_risk_limits['max_positions']}")
                is_within_limits = False
            
            # 3. Check asset allocation limits
            portfolio_value = portfolio_manager.get_total_portfolio_value()
            
            stock_allocation = self._get_asset_allocation('stock') / portfolio_value * 100
            crypto_allocation = self._get_asset_allocation('crypto') / portfolio_value * 100
            
            if stock_allocation > self.stock_risk_limits['max_allocation_pct']:
                warnings.append(f"Stock allocation {stock_allocation:.1f}% exceeds limit {self.stock_risk_limits['max_allocation_pct']}%")
                
            if crypto_allocation > self.crypto_risk_limits['max_allocation_pct']:
                warnings.append(f"Crypto allocation {crypto_allocation:.1f}% exceeds limit {self.crypto_risk_limits['max_allocation_pct']}%")
            
            # 4. Check daily trading limits
            today_trades = self._get_daily_trade_count()
            total_limit = self.stock_risk_limits['daily_trade_limit'] + self.crypto_risk_limits['daily_trade_limit']
            
            if today_trades > total_limit:
                warnings.append(f"Daily trade limit exceeded: {today_trades}/{total_limit}")
                is_within_limits = False
            
            return is_within_limits, warnings
            
        except Exception as e:
            logger.error(f"Error checking portfolio risk limits: {e}")
            return False, [f"Error in risk check: {str(e)}"]
    
    def _calculate_current_drawdown(self) -> float:
        """Calculate current portfolio drawdown from peak"""
        try:
            # Get portfolio value history from transactions
            recent_transactions = db_manager.execute_query(
                """SELECT DATE(timestamp) as date, 
                   SUM(CASE WHEN action = 'buy' THEN -total_amount ELSE total_amount END) as daily_pnl
                   FROM portfolio_transactions 
                   WHERE timestamp >= date('now', '-30 days')
                   GROUP BY DATE(timestamp)
                   ORDER BY date"""
            )
            
            if not recent_transactions:
                return 0.0
            
            # Calculate cumulative P&L
            cumulative_pnl = 0
            peak_value = 0
            max_drawdown = 0
            
            for tx in recent_transactions:
                cumulative_pnl += tx['daily_pnl']
                peak_value = max(peak_value, cumulative_pnl)
                
                if peak_value > 0:
                    current_drawdown = (peak_value - cumulative_pnl) / peak_value
                    max_drawdown = max(max_drawdown, current_drawdown)
            
            return max_drawdown
            
        except Exception as e:
            logger.error(f"Error calculating drawdown: {e}")
            return 0.0
    
    def _get_position_count(self, asset_type: str) -> int:
        """Get current position count for asset type"""
        try:
            result = db_manager.execute_query(
                "SELECT COUNT(*) as count FROM positions WHERE type = ? AND source = 'autotrader'",
                (asset_type,)
            )
            return result[0]['count'] if result else 0
        except Exception:
            return 0
    
    def _get_asset_allocation(self, asset_type: str) -> float:
        """Get current allocation in USD for asset type"""
        try:
            result = db_manager.execute_query(
                "SELECT SUM(value) as total FROM positions WHERE type = ? AND source = 'autotrader'",
                (asset_type,)
            )
            return result[0]['total'] if result and result[0]['total'] else 0.0
        except Exception:
            return 0.0
    
    def _get_daily_trade_count(self) -> int:
        """Get number of trades today"""
        try:
            result = db_manager.execute_query(
                """SELECT COUNT(*) as count FROM autotrader_transactions 
                   WHERE date(timestamp) = date('now')"""
            )
            return result[0]['count'] if result else 0
        except Exception:
            return 0
    
    def should_reduce_position_sizes(self) -> Tuple[bool, str]:
        """Determine if position sizes should be reduced due to risk factors"""
        try:
            # Check market stress
            is_stressed, stress_reason, stress_metrics = volatility_service.is_market_stressed()
            
            # Check portfolio drawdown
            drawdown = self._calculate_current_drawdown()
            
            # Check current risk exposure
            within_limits, warnings = self.check_portfolio_risk_limits()
            
            # Determine if size reduction needed
            should_reduce = False
            reasons = []
            
            if is_stressed:
                should_reduce = True
                reasons.append(f"Market stress: {stress_reason}")
            
            if drawdown > self.max_drawdown_threshold * 0.5:  # 7.5% drawdown
                should_reduce = True
                reasons.append(f"Portfolio drawdown: {drawdown:.1%}")
            
            if not within_limits and len(warnings) > 2:
                should_reduce = True
                reasons.append("Multiple risk limit breaches")
            
            reason = "; ".join(reasons) if should_reduce else "Risk levels normal"
            return should_reduce, reason
            
        except Exception as e:
            logger.error(f"Error checking position size reduction: {e}")
            return True, f"Error in risk assessment - reducing sizes as precaution"
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary"""
        try:
            portfolio_value = portfolio_manager.get_total_portfolio_value()
            within_limits, warnings = self.check_portfolio_risk_limits()
            should_reduce, reduce_reason = self.should_reduce_position_sizes()
            drawdown = self._calculate_current_drawdown()
            
            # Get position counts and allocations
            stock_positions = self._get_position_count('stock')
            crypto_positions = self._get_position_count('crypto')
            stock_allocation = self._get_asset_allocation('stock')
            crypto_allocation = self._get_asset_allocation('crypto')
            
            # Get volatility summary
            vol_summary = volatility_service.get_volatility_summary(7)
            
            return {
                "timestamp": datetime.now().isoformat(),
                "portfolio_value": portfolio_value,
                "risk_status": "OK" if within_limits and not should_reduce else "WARNING",
                "within_risk_limits": within_limits,
                "should_reduce_sizes": should_reduce,
                "current_drawdown_pct": drawdown * 100,
                "position_counts": {
                    "stocks": stock_positions,
                    "crypto": crypto_positions,
                    "total": stock_positions + crypto_positions
                },
                "allocations": {
                    "stocks_usd": stock_allocation,
                    "crypto_usd": crypto_allocation,
                    "stocks_pct": (stock_allocation / portfolio_value) * 100 if portfolio_value > 0 else 0,
                    "crypto_pct": (crypto_allocation / portfolio_value) * 100 if portfolio_value > 0 else 0
                },
                "risk_warnings": warnings,
                "size_reduction_reason": reduce_reason,
                "volatility_summary": vol_summary,
                "limits": {
                    "max_drawdown_pct": self.max_drawdown_threshold * 100,
                    "max_stock_positions": self.stock_risk_limits['max_positions'],
                    "max_crypto_positions": self.crypto_risk_limits['max_positions'],
                    "max_stock_allocation_pct": self.stock_risk_limits['max_allocation_pct'],
                    "max_crypto_allocation_pct": self.crypto_risk_limits['max_allocation_pct']
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating risk summary: {e}")
            return {"error": str(e)}

# Global instance
risk_management_service = RiskManagementService()