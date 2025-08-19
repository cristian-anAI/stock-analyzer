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

logger = logging.getLogger(__name__)

class BackgroundScheduler:
    """Background scheduler for autotrader and data updates"""
    
    def __init__(self):
        self.autotrader_service = AutotraderService()
        self.data_service = DataService()
        self.is_running = False
        self.task = None
        self.stats = {
            "started_at": None,
            "last_autotrader_run": None,
            "last_data_update": None,
            "cycles_completed": 0,
            "trades_executed": 0,
            "errors": 0,
            "status": "stopped"
        }
        
        # Schedule settings
        self.autotrader_interval = 300  # 5 minutes
        self.data_update_interval = 180  # 3 minutes
        self.reports_interval = 3600  # 1 hour (Excel reports)
        
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
        last_reports_generation = 0
        
        try:
            while self.is_running:
                current_time = asyncio.get_event_loop().time()
                
                # Check if it's market hours (if configured)
                if self._is_market_hours():
                    
                    # Run data update
                    if current_time - last_data_update >= self.data_update_interval:
                        await self._update_data()
                        last_data_update = current_time
                    
                    # Run autotrader
                    if current_time - last_autotrader_run >= self.autotrader_interval:
                        await self._run_autotrader_cycle()
                        last_autotrader_run = current_time
                    
                    # Generate Excel reports
                    if current_time - last_reports_generation >= self.reports_interval:
                        await self._generate_excel_reports()
                        last_reports_generation = current_time
                
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
    
    async def _update_data(self):
        """Update stocks and cryptos data"""
        try:
            logger.info(" Background data update starting...")
            
            # Update stocks and cryptos in parallel
            await asyncio.gather(
                self.data_service.update_stocks_data(force_refresh=True),
                self.data_service.update_cryptos_data(force_refresh=True),
                return_exceptions=True
            )
            
            self.stats["last_data_update"] = datetime.now().isoformat()
            logger.info(" Background data update completed")
            
        except Exception as e:
            logger.error(f"Background data update error: {str(e)}")
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