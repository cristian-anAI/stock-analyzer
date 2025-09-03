"""
Market Timing Service - Advanced market hours and timing restrictions
Handles NYSE/NASDAQ hours with timezone support and volatility-based restrictions
"""

import logging
from datetime import datetime, time, timedelta
from typing import Tuple, Optional
import pytz
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

class MarketTimingService:
    """
    Service for managing market timing restrictions and trading hours
    Supports NYSE/NASDAQ with future expansion for global markets
    """
    
    def __init__(self):
        # NYSE/NASDAQ timezone - handles EST/EDT automatically
        self.market_tz = ZoneInfo("America/New_York")
        
        # Market hours (NYSE/NASDAQ)
        self.market_open = time(9, 30)   # 9:30 AM ET
        self.market_close = time(16, 0)  # 4:00 PM ET
        
        # Trading restrictions after market open
        self.buy_restriction_minutes = 15   # No BUY for first 15 minutes
        self.sell_restriction_minutes = 60  # No SELL for first 60 minutes
        
        logger.info(f"MarketTimingService initialized - Market: NYSE/NASDAQ (ET timezone)")
        logger.info(f"Restrictions: BUY blocked first {self.buy_restriction_minutes}min, SELL blocked first {self.sell_restriction_minutes}min")
    
    def get_current_market_time(self) -> datetime:
        """Get current time in market timezone (ET)"""
        return datetime.now(self.market_tz)
    
    def is_market_open(self, current_time: Optional[datetime] = None) -> bool:
        """Check if market is currently open"""
        if current_time is None:
            current_time = self.get_current_market_time()
        
        # Check if it's a weekend
        if current_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Check if within trading hours
        current_time_only = current_time.time()
        return self.market_open <= current_time_only <= self.market_close
    
    def get_market_session_info(self, current_time: Optional[datetime] = None) -> dict:
        """Get detailed market session information"""
        if current_time is None:
            current_time = self.get_current_market_time()
        
        is_open = self.is_market_open(current_time)
        
        if not is_open:
            return {
                "is_open": False,
                "status": "CLOSED",
                "reason": "Weekend" if current_time.weekday() >= 5 else "Outside trading hours",
                "next_open": self._get_next_market_open(current_time),
                "minutes_since_open": None,
                "minutes_to_close": None
            }
        
        # Calculate times relative to market open
        today_open = current_time.replace(
            hour=self.market_open.hour,
            minute=self.market_open.minute,
            second=0,
            microsecond=0
        )
        
        today_close = current_time.replace(
            hour=self.market_close.hour,
            minute=self.market_close.minute,
            second=0,
            microsecond=0
        )
        
        minutes_since_open = (current_time - today_open).total_seconds() / 60
        minutes_to_close = (today_close - current_time).total_seconds() / 60
        
        return {
            "is_open": True,
            "status": "OPEN",
            "market_open_time": today_open,
            "market_close_time": today_close,
            "minutes_since_open": minutes_since_open,
            "minutes_to_close": minutes_to_close,
            "current_time": current_time
        }
    
    def is_in_cooling_period(self, action: str, current_time: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        Check if we're in cooling period after market open
        
        Args:
            action: 'BUY' or 'SELL'
            current_time: Optional current time (uses market time if None)
        
        Returns:
            Tuple[bool, str]: (is_in_cooling_period, reason)
        """
        session_info = self.get_market_session_info(current_time)
        
        if not session_info["is_open"]:
            return True, f"Market closed: {session_info['reason']}"
        
        minutes_since_open = session_info["minutes_since_open"]
        
        if action.upper() == "BUY" and minutes_since_open < self.buy_restriction_minutes:
            remaining = self.buy_restriction_minutes - minutes_since_open
            return True, f"BUY cooling period: {remaining:.1f} minutes remaining after market open"
        
        if action.upper() == "SELL" and minutes_since_open < self.sell_restriction_minutes:
            remaining = self.sell_restriction_minutes - minutes_since_open
            return True, f"SELL cooling period: {remaining:.1f} minutes remaining after market open"
        
        return False, "Trading allowed"
    
    def is_trading_allowed(self, action: str, current_time: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        Master function to check if trading is allowed
        
        Args:
            action: 'BUY' or 'SELL' 
            current_time: Optional current time
        
        Returns:
            Tuple[bool, str]: (is_allowed, reason)
        """
        # Check cooling period (includes market open check)
        in_cooling, cooling_reason = self.is_in_cooling_period(action, current_time)
        if in_cooling:
            return False, cooling_reason
        
        # Additional checks can be added here:
        # - Holiday checks
        # - High volatility periods
        # - Economic announcements
        
        return True, "Trading allowed"
    
    def _get_next_market_open(self, current_time: datetime) -> datetime:
        """Calculate next market open time"""
        next_day = current_time.replace(
            hour=self.market_open.hour,
            minute=self.market_open.minute,
            second=0,
            microsecond=0
        )
        
        # If market hasn't opened today, return today's open
        if current_time.time() < self.market_open and current_time.weekday() < 5:
            return next_day
        
        # Otherwise find next weekday
        next_day += timedelta(days=1)
        while next_day.weekday() >= 5:  # Skip weekends
            next_day += timedelta(days=1)
        
        return next_day
    
    def get_timing_summary(self, current_time: Optional[datetime] = None) -> dict:
        """Get comprehensive timing information for logging/debugging"""
        if current_time is None:
            current_time = self.get_current_market_time()
        
        session_info = self.get_market_session_info(current_time)
        buy_allowed, buy_reason = self.is_trading_allowed("BUY", current_time)
        sell_allowed, sell_reason = self.is_trading_allowed("SELL", current_time)
        
        return {
            "current_time": current_time.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "market_status": session_info["status"],
            "is_market_open": session_info["is_open"],
            "minutes_since_open": session_info.get("minutes_since_open"),
            "minutes_to_close": session_info.get("minutes_to_close"),
            "buy_allowed": buy_allowed,
            "buy_reason": buy_reason,
            "sell_allowed": sell_allowed,
            "sell_reason": sell_reason,
            "restrictions": {
                "buy_cooling_minutes": self.buy_restriction_minutes,
                "sell_cooling_minutes": self.sell_restriction_minutes
            }
        }

# Global instance
market_timing_service = MarketTimingService()