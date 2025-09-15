"""
Position Monitor Service - Real-time monitoring of open positions
Automatically updates positions when market opens and continuously monitors them
Timezone: Europe/Madrid (6 hours ahead of ET)
Market hours in Spain: 15:30 - 22:00
"""

import asyncio
import logging
from datetime import datetime, time
from typing import Dict, List, Any, Optional
import pytz

from .data_service import DataService
from .market_timing_service import market_timing_service
from ..database.database import db_manager

logger = logging.getLogger(__name__)

class PositionMonitorService:
    """Service for monitoring and updating open positions in real-time"""
    
    def __init__(self):
        self.data_service = DataService()
        self.market_timing = market_timing_service
        self.last_market_open_update = None
        self.monitoring_active = True
        
        # Spanish timezone setup
        self.madrid_tz = pytz.timezone('Europe/Madrid')
        self.ny_tz = pytz.timezone('America/New_York')
        
        # Market hours in Spain (converted from ET)
        self.market_open_spain = time(15, 30)   # 15:30 (9:30 AM ET)
        self.market_close_spain = time(22, 0)   # 22:00 (4:00 PM ET)
        self.pre_market_update = time(15, 25)   # 15:25 (5 min before open)
        self.post_market_summary = time(22, 5)  # 22:05 (5 min after close)
        
    def get_spanish_time(self) -> datetime:
        """Get current time in Madrid timezone"""
        return datetime.now(self.madrid_tz)
        
    def is_market_open_spain(self) -> bool:
        """Check if US market is open from Spanish perspective"""
        now_spain = self.get_spanish_time().time()
        return self.market_open_spain <= now_spain <= self.market_close_spain
    
    async def market_open_position_update(self) -> Dict[str, Any]:
        """
        Comprehensive position update when market opens (15:30 Spanish time)
        Updates all open positions (autotrader + manual) with fresh data
        """
        spanish_time = self.get_spanish_time()
        logger.info(f"🔔 US Market opened (15:30 Spain time) - Starting comprehensive position update at {spanish_time.strftime('%H:%M')}")
        
        try:
            # Get all open positions
            open_positions = self._get_all_open_positions()
            
            if not open_positions:
                logger.info("No open positions to update at market open")
                return {"updated_positions": 0, "message": "No positions to update", "spanish_time": spanish_time.strftime('%H:%M')}
            
            # Extract unique symbols from positions
            stock_symbols = set()
            crypto_symbols = set()
            
            for pos in open_positions:
                symbol = pos['symbol']
                if pos['type'] in ['LONG', 'SHORT']:  # Stock positions
                    stock_symbols.add(symbol)
                elif pos['type'] in ['CRYPTO_LONG', 'CRYPTO_SHORT']:  # Crypto positions  
                    crypto_symbols.add(symbol)
            
            logger.info(f"📊 Market open update (Spain 15:30): {len(stock_symbols)} stocks, {len(crypto_symbols)} cryptos")
            logger.info(f"Stock positions: {list(stock_symbols)}")
            logger.info(f"Crypto positions: {list(crypto_symbols)}")
            
            # Update data for position symbols with priority
            update_results = await self._priority_data_update(list(stock_symbols), list(crypto_symbols))
            
            # Update position P&L with fresh data
            updated_positions = await self._refresh_position_pnl(open_positions)
            
            # Record market open update
            self.last_market_open_update = spanish_time
            
            logger.info(f"✅ Market open update completed at {spanish_time.strftime('%H:%M')}: {len(updated_positions)} positions updated")
            
            return {
                "updated_positions": len(updated_positions),
                "stock_symbols": list(stock_symbols),
                "crypto_symbols": list(crypto_symbols),
                "data_update_results": update_results,
                "spanish_time": spanish_time.strftime('%H:%M'),
                "market_open_spain": "15:30",
                "updated_at": self.last_market_open_update.isoformat(),
                "message": f"Successfully updated {len(updated_positions)} open positions at market open (15:30 Spain)"
            }
            
        except Exception as e:
            logger.error(f"Error in market open position update: {e}")
            return {"error": str(e), "updated_positions": 0, "spanish_time": spanish_time.strftime('%H:%M')}
    
    async def continuous_position_monitoring(self, interval_minutes: int = 5) -> None:
        """
        Continuous monitoring of open positions during market hours (15:30-22:00 Spain)
        """
        logger.info(f"🔄 Starting continuous position monitoring (every {interval_minutes} minutes)")
        logger.info(f"📅 Market hours in Spain: {self.market_open_spain} - {self.market_close_spain}")
        
        while self.monitoring_active:
            try:
                spanish_time = self.get_spanish_time()
                current_time = spanish_time.time()
                
                # Check if we're in market hours (Spanish time)
                if self.is_market_open_spain():
                    logger.debug(f"⏰ Market open - updating positions at {spanish_time.strftime('%H:%M')}")
                    
                    # Update positions with current data
                    await self._update_position_prices()
                else:
                    logger.debug(f"🌙 Market closed ({spanish_time.strftime('%H:%M')}) - skipping position updates")
                
                # Special actions at specific times
                if current_time.hour == 15 and current_time.minute == 25:
                    logger.info("🚀 Pre-market preparation (15:25 Spain)")
                    await self._pre_market_preparation()
                    
                elif current_time.hour == 22 and current_time.minute == 5:
                    logger.info("📋 Post-market summary (22:05 Spain)")
                    await self._post_market_summary()
                
                # Wait for next update
                await asyncio.sleep(interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"Error in continuous monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    def _get_all_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions (autotrader + manual)"""
        return db_manager.execute_query(
            """SELECT * FROM positions 
               WHERE status = 'open' 
               ORDER BY created_at DESC""",
            ()
        )
    
    async def _priority_data_update(self, stock_symbols: List[str], crypto_symbols: List[str]) -> Dict[str, Any]:
        """
        Priority data update for specific symbols (positions)
        Updates these symbols first before others
        """
        results = {"stocks_updated": 0, "cryptos_updated": 0, "errors": []}
        
        try:
            # Update stocks for positions
            if stock_symbols:
                logger.info(f"📈 Priority update for stock positions: {stock_symbols}")
                # Use existing data service update methods
                await self.data_service.update_positions_prices()
                results["stocks_updated"] = len(stock_symbols)
                
            # Update cryptos for positions  
            if crypto_symbols:
                logger.info(f"₿ Priority update for crypto positions: {crypto_symbols}")
                await self.data_service.update_positions_prices()
                results["cryptos_updated"] = len(crypto_symbols)
                
        except Exception as e:
            logger.error(f"Error in priority data update: {e}")
            results["errors"].append(str(e))
            
        return results
    
    async def _refresh_position_pnl(self, positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Refresh P&L calculations for all positions with current prices
        """
        updated_positions = []
        
        for position in positions:
            try:
                symbol = position['symbol']
                position_type = position['type']
                
                # Get current price from database (just updated)
                if position_type in ['LONG', 'SHORT']:
                    price_data = db_manager.execute_query(
                        "SELECT current_price FROM stocks WHERE symbol = ?", (symbol,)
                    )
                else:  # CRYPTO_LONG, CRYPTO_SHORT
                    price_data = db_manager.execute_query(
                        "SELECT current_price FROM cryptos WHERE symbol = ?", (symbol,)
                    )
                
                if price_data:
                    current_price = price_data[0]['current_price']
                    entry_price = position['entry_price']
                    quantity = position['quantity']
                    
                    # Calculate P&L
                    if position_type in ['LONG', 'CRYPTO_LONG']:
                        unrealized_pnl = (current_price - entry_price) * quantity
                    else:  # SHORT positions
                        unrealized_pnl = (entry_price - current_price) * quantity
                    
                    # Calculate percentage gain/loss
                    pnl_percentage = (unrealized_pnl / (entry_price * quantity)) * 100
                    
                    # Update position with current P&L
                    db_manager.execute_update(
                        """UPDATE positions 
                           SET current_price = ?, unrealized_pnl = ?, updated_at = ?
                           WHERE id = ?""",
                        (current_price, unrealized_pnl, datetime.now().isoformat(), position['id'])
                    )
                    
                    position['current_price'] = current_price
                    position['unrealized_pnl'] = unrealized_pnl
                    position['pnl_percentage'] = pnl_percentage
                    updated_positions.append(position)
                    
                    logger.debug(f"💰 {symbol}: ${current_price:.2f} | P&L: ${unrealized_pnl:.2f} ({pnl_percentage:+.1f}%)")
                    
            except Exception as e:
                logger.error(f"Error updating position {position.get('symbol')}: {e}")
        
        return updated_positions
    
    async def _update_position_prices(self) -> None:
        """Update prices for all open positions during continuous monitoring"""
        try:
            open_positions = self._get_all_open_positions()
            
            if open_positions:
                # Quick update using existing data service
                await self.data_service.update_positions_prices()
                
                # Refresh P&L calculations
                await self._refresh_position_pnl(open_positions)
                
                spanish_time = self.get_spanish_time()
                logger.debug(f"🔄 Updated prices for {len(open_positions)} positions at {spanish_time.strftime('%H:%M')}")
                
        except Exception as e:
            logger.error(f"Error in position price update: {e}")
    
    async def _pre_market_preparation(self) -> None:
        """Prepare for market open at 15:25 (5 minutes before)"""
        try:
            logger.info("🚀 Pre-market preparation starting...")
            open_positions = self._get_all_open_positions()
            
            if open_positions:
                logger.info(f"📋 Preparing {len(open_positions)} positions for market open:")
                for pos in open_positions:
                    logger.info(f"  • {pos['symbol']} ({pos['type']}) - Entry: ${pos['entry_price']:.2f}")
                    
        except Exception as e:
            logger.error(f"Error in pre-market preparation: {e}")
    
    async def _post_market_summary(self) -> None:
        """Generate end-of-day summary at 22:05 (5 minutes after close)"""
        try:
            spanish_time = self.get_spanish_time()
            logger.info(f"📋 Generating post-market summary at {spanish_time.strftime('%H:%M')}")
            
            open_positions = self._get_all_open_positions()
            
            if open_positions:
                total_unrealized = sum(pos.get('unrealized_pnl', 0) for pos in open_positions)
                
                logger.info(f"📊 End-of-day summary:")
                logger.info(f"  • Open positions: {len(open_positions)}")
                logger.info(f"  • Total unrealized P&L: ${total_unrealized:.2f}")
                
                for pos in open_positions:
                    pnl = pos.get('unrealized_pnl', 0)
                    logger.info(f"  • {pos['symbol']}: ${pnl:.2f}")
                    
        except Exception as e:
            logger.error(f"Error in post-market summary: {e}")
    
    def stop_monitoring(self) -> None:
        """Stop continuous monitoring"""
        self.monitoring_active = False
        logger.info("Position monitoring stopped")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status"""
        open_positions = self._get_all_open_positions()
        spanish_time = self.get_spanish_time()
        is_market_open = self.is_market_open_spain()
        
        return {
            "monitoring_active": self.monitoring_active,
            "open_positions_count": len(open_positions),
            "last_market_open_update": self.last_market_open_update.isoformat() if self.last_market_open_update else None,
            "spanish_time": spanish_time.strftime('%H:%M'),
            "is_market_open": is_market_open,
            "market_hours_spain": f"{self.market_open_spain} - {self.market_close_spain}",
            "positions_being_monitored": [
                {
                    "symbol": p['symbol'], 
                    "type": p['type'], 
                    "entry_price": p['entry_price'],
                    "current_price": p.get('current_price', 0),
                    "unrealized_pnl": p.get('unrealized_pnl', 0)
                }
                for p in open_positions
            ]
        }

# Singleton instance
position_monitor_service = PositionMonitorService()