"""
Overtrading Prevention Service - Prevents excessive trading and implements cooldowns
Manages trading frequency, symbol cooldowns, and blacklist functionality
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta

from ..database.database import db_manager

logger = logging.getLogger(__name__)

class OvertradingPreventionService:
    """Service to prevent overtrading and manage trading frequency"""
    
    def __init__(self):
        # Trading frequency limits
        self.max_daily_trades = {
            'stock': 5,
            'crypto': 3,
            'total': 8
        }
        
        self.max_weekly_trades = {
            'stock': 20,
            'crypto': 15,
            'total': 30
        }
        
        # Cooldown periods (in hours)
        self.symbol_cooldowns = {
            'stock': {
                'after_buy': 4,    # 4 hours after buying same stock
                'after_sell': 6,   # 6 hours after selling same stock
                'after_loss': 24   # 24 hours after losing trade
            },
            'crypto': {
                'after_buy': 2,    # 2 hours after buying same crypto
                'after_sell': 4,   # 4 hours after selling same crypto  
                'after_loss': 12   # 12 hours after losing trade
            }
        }
        
        # Blacklist parameters
        self.blacklist_triggers = {
            'consecutive_losses': 3,      # 3 losses in a row
            'loss_threshold_pct': 15,     # 15% loss triggers blacklist
            'blacklist_duration_days': 7  # 7 days blacklist
        }
        
        logger.info("Initialized Overtrading Prevention Service")
    
    def can_trade_symbol(self, symbol: str, asset_type: str, action: str = "buy") -> Tuple[bool, str]:
        """
        Check if we can trade a symbol considering cooldowns and blacklists
        
        Args:
            symbol: Symbol to check
            asset_type: 'stock' or 'crypto'
            action: 'buy' or 'sell'
        
        Returns:
            (can_trade, reason)
        """
        try:
            # Check if symbol is blacklisted
            if self._is_symbol_blacklisted(symbol):
                blacklist_info = self._get_blacklist_info(symbol)
                return False, f"Symbol blacklisted until {blacklist_info['blacklist_until']}"
            
            # Check symbol cooldown
            cooldown_active, cooldown_reason = self._check_symbol_cooldown(symbol, asset_type, action)
            if cooldown_active:
                return False, cooldown_reason
            
            # Check daily trading limits
            daily_limit_ok, daily_reason = self._check_daily_trade_limits(asset_type)
            if not daily_limit_ok:
                return False, daily_reason
            
            return True, "Trading allowed"
            
        except Exception as e:
            logger.error(f"Error checking trading eligibility for {symbol}: {e}")
            return False, f"Error in trading check: {str(e)}"
    
    def _is_symbol_blacklisted(self, symbol: str) -> bool:
        """Check if symbol is currently blacklisted"""
        try:
            blacklist_data = db_manager.execute_query(
                """SELECT blacklist_until FROM symbol_blacklist 
                   WHERE symbol = ? AND datetime(blacklist_until) > datetime('now')
                   ORDER BY blacklist_until DESC LIMIT 1""",
                (symbol,)
            )
            return len(blacklist_data) > 0
        except Exception as e:
            logger.error(f"Error checking blacklist for {symbol}: {e}")
            return False
    
    def _get_blacklist_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get blacklist information for symbol"""
        try:
            blacklist_data = db_manager.execute_query(
                """SELECT * FROM symbol_blacklist 
                   WHERE symbol = ? AND datetime(blacklist_until) > datetime('now')
                   ORDER BY blacklist_until DESC LIMIT 1""",
                (symbol,)
            )
            return dict(blacklist_data[0]) if blacklist_data else None
        except Exception as e:
            logger.error(f"Error getting blacklist info for {symbol}: {e}")
            return None
    
    def _check_symbol_cooldown(self, symbol: str, asset_type: str, action: str) -> Tuple[bool, str]:
        """Check if symbol is in cooldown period"""
        try:
            cooldown_data = db_manager.execute_query(
                """SELECT cooldown_until, reason FROM trading_cooldowns 
                   WHERE symbol = ? AND datetime(cooldown_until) > datetime('now')
                   LIMIT 1""",
                (symbol,)
            )
            
            if cooldown_data:
                cooldown_until = cooldown_data[0]['cooldown_until']
                reason = cooldown_data[0]['reason']
                return True, f"Symbol in cooldown until {cooldown_until} ({reason})"
            
            return False, "No active cooldown"
            
        except Exception as e:
            logger.error(f"Error checking cooldown for {symbol}: {e}")
            return False, "Error in cooldown check"
    
    def _check_daily_trade_limits(self, asset_type: str) -> Tuple[bool, str]:
        """Check daily trading limits"""
        try:
            today_trades = db_manager.execute_query(
                """SELECT COUNT(*) as count FROM autotrader_transactions 
                   WHERE date(timestamp) = date('now')"""
            )
            
            total_today = today_trades[0]['count'] if today_trades else 0
            
            if total_today >= self.max_daily_trades['total']:
                return False, f"Daily total trade limit reached: {total_today}/{self.max_daily_trades['total']}"
            
            return True, "Daily limits OK"
            
        except Exception as e:
            logger.error(f"Error checking daily limits: {e}")
            return True, "Error in daily limit check - allowing trade"
    
    def record_trade_action(self, symbol: str, asset_type: str, action: str, price: float, pnl: Optional[float] = None) -> None:
        """Record a trade action and set appropriate cooldowns"""
        try:
            now = datetime.now()
            cooldown_hours = 0
            cooldown_reason = ""
            
            if action == "buy":
                cooldown_hours = self.symbol_cooldowns[asset_type]['after_buy']
                cooldown_reason = f"After {action} cooldown"
            elif action == "sell":
                if pnl is not None and pnl < 0:
                    cooldown_hours = self.symbol_cooldowns[asset_type]['after_loss']
                    cooldown_reason = f"After loss cooldown (PnL: ${pnl:.2f})"
                    self._check_blacklist_trigger(symbol, asset_type, pnl)
                else:
                    cooldown_hours = self.symbol_cooldowns[asset_type]['after_sell']
                    cooldown_reason = f"After {action} cooldown"
            
            # Set cooldown if needed
            if cooldown_hours > 0:
                cooldown_until = now + timedelta(hours=cooldown_hours)
                
                db_manager.execute_insert(
                    """INSERT OR REPLACE INTO trading_cooldowns 
                       (symbol, last_trade_timestamp, cooldown_until, reason)
                       VALUES (?, ?, ?, ?)""",
                    (symbol, now.isoformat(), cooldown_until.isoformat(), cooldown_reason)
                )
                
                logger.info(f"Set cooldown for {symbol}: {cooldown_hours}h ({cooldown_reason})")
            
        except Exception as e:
            logger.error(f"Error recording trade action for {symbol}: {e}")
    
    def _check_blacklist_trigger(self, symbol: str, asset_type: str, current_pnl: float) -> None:
        """Check if symbol should be blacklisted based on performance"""
        try:
            consecutive_losses = 1 if current_pnl < 0 else 0
            loss_pct = abs(current_pnl) / 1000 * 100
            
            should_blacklist = False
            blacklist_reason = ""
            
            if consecutive_losses >= self.blacklist_triggers['consecutive_losses']:
                should_blacklist = True
                blacklist_reason = f"{consecutive_losses} consecutive losses"
            
            if loss_pct >= self.blacklist_triggers['loss_threshold_pct']:
                should_blacklist = True
                blacklist_reason = f"{loss_pct:.1f}% loss threshold"
            
            if should_blacklist:
                self._add_to_blacklist(symbol, asset_type, blacklist_reason, consecutive_losses)
                
        except Exception as e:
            logger.error(f"Error checking blacklist trigger for {symbol}: {e}")
    
    def _add_to_blacklist(self, symbol: str, asset_type: str, reason: str, consecutive_losses: int) -> None:
        """Add symbol to blacklist"""
        try:
            blacklist_until = datetime.now() + timedelta(days=self.blacklist_triggers['blacklist_duration_days'])
            
            db_manager.execute_insert(
                """INSERT INTO symbol_blacklist 
                   (symbol, blacklist_until, reason, consecutive_losses, asset_type)
                   VALUES (?, ?, ?, ?, ?)""",
                (symbol, blacklist_until.isoformat(), reason, consecutive_losses, asset_type)
            )
            
            logger.warning(f"BLACKLISTED {symbol} ({asset_type}): {reason}")
            
        except Exception as e:
            logger.error(f"Error adding {symbol} to blacklist: {e}")
    
    def clean_expired_data(self) -> Dict[str, int]:
        """Clean up expired cooldowns and blacklist entries"""
        try:
            results = {"expired_cooldowns": 0, "expired_blacklists": 0}
            
            cooldown_result = db_manager.execute_update(
                "DELETE FROM trading_cooldowns WHERE datetime(cooldown_until) <= datetime('now')"
            )
            results["expired_cooldowns"] = cooldown_result
            
            blacklist_result = db_manager.execute_update(
                "DELETE FROM symbol_blacklist WHERE datetime(blacklist_until) <= datetime('now')"
            )
            results["expired_blacklists"] = blacklist_result
            
            return results
            
        except Exception as e:
            logger.error(f"Error cleaning expired data: {e}")
            return {"error": str(e), "expired_cooldowns": 0, "expired_blacklists": 0}
    
    def get_trading_status_summary(self) -> Dict[str, Any]:
        """Get summary of current trading restrictions"""
        try:
            self.clean_expired_data()
            
            today_trades = db_manager.execute_query(
                """SELECT COUNT(*) as count FROM autotrader_transactions 
                   WHERE date(timestamp) = date('now')"""
            )
            
            return {
                "timestamp": datetime.now().isoformat(),
                "active_cooldowns": [],
                "active_blacklists": [],
                "trade_counts": {
                    "today": today_trades[0]['count'] if today_trades else 0,
                    "this_week": 0
                },
                "limits": {
                    "daily_total": self.max_daily_trades['total'],
                    "daily_stock": self.max_daily_trades['stock'],
                    "daily_crypto": self.max_daily_trades['crypto']
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting trading status summary: {e}")
            return {"error": str(e)}

# Global instance
overtrading_prevention = OvertradingPreventionService()