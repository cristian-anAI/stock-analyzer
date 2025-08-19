#!/usr/bin/env python3
"""
Standalone autotrader that keeps running 24/7
Use this if you want autotrader independent of the API server
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from api.services.background_scheduler import BackgroundScheduler
from api.database.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/autotrader_24x7.log')
    ]
)

logger = logging.getLogger(__name__)

class StandaloneAutotrader:
    """Standalone 24/7 autotrader"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.running = False
    
    async def start(self):
        """Start the standalone autotrader"""
        logger.info(" Starting 24/7 Standalone Autotrader...")
        
        # Initialize database
        init_db()
        logger.info(" Database initialized")
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Start scheduler
        await self.scheduler.start()
        self.running = True
        
        logger.info("🤖 Autotrader is now running 24/7!")
        logger.info(" Press Ctrl+C to stop gracefully")
        logger.info(" You can now go to sleep - the autotrader will keep working!")
        
        # Keep running until interrupted
        try:
            while self.running:
                await asyncio.sleep(10)
        except KeyboardInterrupt:
            logger.info(" Keyboard interrupt received")
        
        await self.stop()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f" Received signal {signum}, initiating graceful shutdown...")
        self.running = False
    
    async def stop(self):
        """Stop the autotrader"""
        logger.info(" Stopping autotrader...")
        await self.scheduler.stop()
        logger.info(" Autotrader stopped gracefully")

async def main():
    """Main function"""
    autotrader = StandaloneAutotrader()
    await autotrader.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info(" Goodbye!")
    except Exception as e:
        logger.error(f" Fatal error: {str(e)}")
        sys.exit(1)