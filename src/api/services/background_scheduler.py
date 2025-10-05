"""
Background scheduler for continuous autotrader operation
"""

import asyncio
import logging
from datetime import datetime, time
from typing import Dict, Any
import threading

from .autotrader_service import AutotraderService
from .data_service import DataService
from .excel_reports_service import excel_reports_service
from .position_monitor_service import position_monitor_service
from .mtss_scheduler_service import mtss_scheduler

logger = logging.getLogger(__name__)

class BackgroundScheduler:
    """Background scheduler for autotrader and data updates"""
    
    def __init__(self):
        self.autotrader_service = AutotraderService()
        self.data_service = DataService()
        self.position_monitor = position_monitor_service
        self.is_running = False
        self.task = None
        self.stats = {
            "started_at": None,
            "last_autotrader_run": None,
            "last_data_update": None,
            "last_position_update": None,
            "last_crypto_scoring_update": None,
            "cycles_completed": 0,
            "trades_executed": 0,
            "errors": 0,
            "status": "stopped"
        }
        
        # Schedule settings
        self.autotrader_interval = 300  # 5 minutes
        self.data_update_interval = 180  # 3 minutes
        self.crypto_update_interval = 60   # 1 minute for cryptos (24/7)
        self.crypto_scoring_interval = 900  # 15 minutes for crypto scoring updates
        self.reports_interval = 3600  # 1 hour (Excel reports)
        self.position_monitor_interval = 300  # 5 minutes (position updates)
        self.mtss_scheduler_interval = 600  # 10 minutes (MTSS scheduler cycle)
        
        # Market open tracking
        self.market_open_update_done_today = False
        self.last_market_date = None
        
        # Market hours (optional - set to None to trade 24/7)
        self.market_start = None  # time(9, 30)  # 9:30 AM
        self.market_end = None    # time(16, 0)   # 4:00 PM
    
    async def start(self):
        """Start the background scheduler"""
        if self.is_running:
            logger.warning("Background scheduler is already running")
            return
        
        self.is_running = True
        self.stats["started_at"] = datetime.now().isoformat()
        self.stats["status"] = "running"
        
        logger.info(" Starting background autotrader scheduler...")
        logger.info(f" Autotrader interval: {self.autotrader_interval}s")
        logger.info(f" Data update interval: {self.data_update_interval}s")
        logger.info(f" Excel reports interval: {self.reports_interval}s")
        logger.info(f" MTSS scheduler interval: {self.mtss_scheduler_interval}s")
        
        # Start background task
        self.task = asyncio.create_task(self._run_scheduler())
        
        return {
            "status": "started",
            "autotrader_interval": self.autotrader_interval,
            "data_update_interval": self.data_update_interval,
            "started_at": self.stats["started_at"]
        }
    
    async def stop(self):
        """Stop the background scheduler"""
        if not self.is_running:
            logger.warning("Background scheduler is not running")
            return
        
        self.is_running = False
        self.stats["status"] = "stopping"
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        self.stats["status"] = "stopped"
        logger.info(" Background autotrader scheduler stopped")
        
        return {"status": "stopped", "stats": self.stats}
    
    async def _run_scheduler(self):
        """Main scheduler loop"""
        logger.info(" Background scheduler loop started")
        
        last_autotrader_run = 0
        last_data_update = 0
        last_crypto_update = 0
        last_crypto_scoring_update = 0
        last_reports_generation = 0
        last_position_update = 0
        last_mtss_scheduler_run = 0
        
        try:
            while self.is_running:
                current_time = asyncio.get_event_loop().time()
                
                # Check for market open position update (15:30 Spanish time)
                await self._check_market_open_update()
                
                # Update crypto data (runs 24/7)
                if current_time - last_crypto_update >= self.crypto_update_interval:
                    await self._update_crypto_data()
                    last_crypto_update = current_time
                
                # Update crypto scoring for frontend (runs 24/7)
                if current_time - last_crypto_scoring_update >= self.crypto_scoring_interval:
                    await self._update_crypto_scoring()
                    last_crypto_scoring_update = current_time
                
                # Check if it's market hours (if configured)
                if self._is_market_hours():
                    
                    # Run data update (stocks only during market hours)
                    if current_time - last_data_update >= self.data_update_interval:
                        await self._update_stocks_data()
                        last_data_update = current_time
                    
                    # Run autotrader
                    if current_time - last_autotrader_run >= self.autotrader_interval:
                        await self._run_autotrader_cycle()
                        last_autotrader_run = current_time
                    
                    # Update position monitoring
                    if current_time - last_position_update >= self.position_monitor_interval:
                        await self._update_position_monitoring()
                        last_position_update = current_time
                    
                    # Generate Excel reports
                    if current_time - last_reports_generation >= self.reports_interval:
                        await self._generate_excel_reports()
                        last_reports_generation = current_time
                
                # Run MTSS scheduler (24/7 - independent of market hours)
                if current_time - last_mtss_scheduler_run >= self.mtss_scheduler_interval:
                    await self._run_mtss_scheduler_cycle()
                    last_mtss_scheduler_run = current_time
                
                # Sleep for 10 seconds before next check
                await asyncio.sleep(10)
                
        except asyncio.CancelledError:
            logger.info(" Scheduler loop cancelled")
            raise
        except Exception as e:
            logger.error(f" Scheduler loop error: {str(e)}")
            self.stats["errors"] += 1
            # Continue running despite errors
            await asyncio.sleep(30)  # Wait 30s before retrying
            if self.is_running:
                await self._run_scheduler()  # Restart loop
    
    def _is_market_hours(self) -> bool:
        """Check if current time is within market hours"""
        if self.market_start is None or self.market_end is None:
            return True  # 24/7 trading
        
        now = datetime.now().time()
        return self.market_start <= now <= self.market_end
    
    async def _update_stocks_data(self):
        """Update stocks data during market hours"""
        try:
            logger.info("STOCKS: Background stocks data update starting...")
            await self.data_service.update_stocks_data(force_refresh=True)
            
            self.stats["last_data_update"] = datetime.now().isoformat()
            logger.info("STOCKS: Background stocks data update completed")
            
        except Exception as e:
            logger.error(f"STOCKS ERROR: Background stocks data update error: {str(e)}")
            self.stats["errors"] += 1
    
    async def _update_crypto_data(self):
        """Update crypto data 24/7 with focus on BTC, ETH, SOL"""
        try:
            logger.info("CRYPTO: Background crypto data update starting...")
            
            # Focus on high-priority cryptos: BTC, ETH, SOL
            priority_cryptos = ["BTC-USD", "ETH-USD", "SOL-USD"]
            
            # Update priority cryptos first
            for symbol in priority_cryptos:
                crypto_symbol = symbol.replace('-USD', '')
                await self.data_service.update_single_crypto(crypto_symbol)
                await asyncio.sleep(0.5)  # Short delay between priority cryptos
            
            # Update remaining cryptos less frequently (every 5th cycle)
            import random
            if random.randint(1, 5) == 1:
                logger.info("💎 Updating remaining cryptos...")
                await self.data_service.update_cryptos_data(force_refresh=True)
            
            logger.info("CRYPTO: Background crypto data update completed")
            
        except Exception as e:
            logger.error(f"CRYPTO ERROR: Background crypto data update error: {str(e)}")
            self.stats["errors"] += 1
    
    async def _run_autotrader_cycle(self):
        """Run autotrader cycle"""
        try:
            logger.info(" Background autotrader cycle starting...")
            
            results = await self.autotrader_service.run_trading_cycle()
            
            self.stats["cycles_completed"] += 1
            self.stats["trades_executed"] += len(results.get("actions_taken", []))
            self.stats["last_autotrader_run"] = datetime.now().isoformat()
            
            actions_count = len(results.get("actions_taken", []))
            if actions_count > 0:
                logger.info(f"Autotrader completed: {actions_count} actions taken")
                for action in results.get("actions_taken", []):
                    logger.info(f"  {action['action'].upper()}: {action['symbol']} - {action['quantity']:.2f} @ ${action['price']:.2f}")
            else:
                logger.info(" Autotrader completed: No actions taken")
            
        except Exception as e:
            logger.error(f"Background autotrader error: {str(e)}")
            self.stats["errors"] += 1
    
    async def _generate_excel_reports(self):
        """Generate Excel reports in background"""
        try:
            logger.info(" Starting Excel reports generation...")
            
            # Run in executor to avoid blocking the async loop
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, excel_reports_service.generate_all_reports)
            
            if success:
                logger.info(" Excel reports generated successfully")
                # Cleanup old reports
                await loop.run_in_executor(None, excel_reports_service.cleanup_old_reports, 7)
                logger.info(" Old reports cleaned up")
            else:
                logger.error(" Failed to generate Excel reports")
                self.stats["errors"] += 1
            
        except Exception as e:
            logger.error(f"Excel reports generation error: {str(e)}")
            self.stats["errors"] += 1
    
    async def _check_market_open_update(self):
        """Check if it's time for market open position update (15:30 Spanish time)"""
        try:
            spanish_time = self.position_monitor.get_spanish_time()
            current_date = spanish_time.date()
            current_time = spanish_time.time()
            
            # Reset flag for new day
            if self.last_market_date != current_date:
                self.market_open_update_done_today = False
                self.last_market_date = current_date
            
            # Check if it's market open time (15:30) and we haven't done update today
            if (current_time.hour == 15 and current_time.minute >= 30 and 
                current_time.minute <= 35 and not self.market_open_update_done_today):
                
                logger.info("🔔 Market open detected (15:30 Spain) - Starting position update")
                
                # Run market open position update
                update_result = await self.position_monitor.market_open_position_update()
                
                # Mark as done for today
                self.market_open_update_done_today = True
                self.stats["last_position_update"] = spanish_time.isoformat()
                
                logger.info(f"MARKET: Market open update completed: {update_result.get('message', 'Update done')}")
                
        except Exception as e:
            logger.error(f"Error in market open update check: {e}")
            self.stats["errors"] += 1
    
    async def _update_position_monitoring(self):
        """Update position monitoring during market hours"""
        try:
            # This runs the continuous monitoring logic
            spanish_time = self.position_monitor.get_spanish_time()
            
            if self.position_monitor.is_market_open_spain():
                await self.position_monitor._update_position_prices()
                self.stats["last_position_update"] = spanish_time.isoformat()
                logger.debug(f"Position prices updated at {spanish_time.strftime('%H:%M')}")
            
        except Exception as e:
            logger.error(f"Error in position monitoring update: {e}")
            self.stats["errors"] += 1

    async def _run_mtss_scheduler_cycle(self):
        """Run MTSS scheduler cycle to update scores for different timeframes"""
        try:
            logger.info("📊 Starting MTSS scheduler cycle...")
            
            # Start MTSS scheduler if not already running
            if not mtss_scheduler.is_running:
                await mtss_scheduler.start_scheduler()
            
            # Run cycles for all timeframes that need updates
            from .mtss_scheduler_service import TimeframeType
            
            cycle_results = {}
            for timeframe in TimeframeType:
                try:
                    result = await mtss_scheduler.process_timeframe_cycle(timeframe)
                    if result.get("status") != "not_time_to_run":
                        cycle_results[timeframe.value] = result
                        logger.info(f"📈 {timeframe.value} cycle: {result.get('processed', 0)} processed, {result.get('cached', 0)} cached")
                        
                        # Brief delay between timeframe cycles to respect rate limits
                        await asyncio.sleep(2)
                        
                except Exception as tf_error:
                    logger.error(f"Error in {timeframe.value} cycle: {tf_error}")
                    self.stats["errors"] += 1
            
            # Log summary
            total_processed = sum(r.get('processed', 0) for r in cycle_results.values())
            total_cached = sum(r.get('cached', 0) for r in cycle_results.values())
            
            if total_processed > 0 or total_cached > 0:
                logger.info(f"MTSS: MTSS cycle completed: {total_processed} analyzed, {total_cached} cached, {len(cycle_results)} timeframes active")
            else:
                logger.debug("💤 MTSS cycle: No timeframes ready for update")
            
        except Exception as e:
            logger.error(f"Error in MTSS scheduler cycle: {e}")
            self.stats["errors"] += 1
    
    async def _update_crypto_scoring(self):
        """Update crypto scoring for frontend dashboard"""
        try:
            logger.info("🔄 Background crypto scoring update starting...")
            
            # Import here to avoid circular imports
            from .unified_scoring_service import UnifiedScoringService
            
            unified_scoring = UnifiedScoringService()
            
            # Get crypto scores and cache them
            crypto_results = await unified_scoring.analyze_all_cryptos()
            
            # Update stats
            successful_updates = len([r for r in crypto_results.values() if 'error' not in r])
            failed_updates = len([r for r in crypto_results.values() if 'error' in r])
            
            logger.info(f"CRYPTO SCORING: Crypto scoring update completed: {successful_updates} success, {failed_updates} errors")
            
            self.stats["last_crypto_scoring_update"] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"Error in crypto scoring update: {e}")
            self.stats["errors"] += 1
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status and statistics"""
        return {
            "is_running": self.is_running,
            "stats": self.stats,
            "settings": {
                "autotrader_interval": self.autotrader_interval,
                "data_update_interval": self.data_update_interval,
                "market_start": str(self.market_start) if self.market_start else "24/7",
                "market_end": str(self.market_end) if self.market_end else "24/7"
            }
        }
    
    def update_settings(self, autotrader_interval: int = None, data_update_interval: int = None):
        """Update scheduler settings"""
        if autotrader_interval:
            self.autotrader_interval = autotrader_interval
            logger.info(f" Autotrader interval updated to {autotrader_interval}s")
        
        if data_update_interval:
            self.data_update_interval = data_update_interval
            logger.info(f" Data update interval updated to {data_update_interval}s")

# Global scheduler instance
background_scheduler = BackgroundScheduler()