"""
Rate limiting middleware for external API calls
"""

import asyncio
from asyncio import Semaphore
import time
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter for external API calls"""
    
    def __init__(self):
        # Limits for different services
        self.semaphores = {
            "yahoo_finance": Semaphore(5),  # Max 5 concurrent calls
            "external_api": Semaphore(3),   # Max 3 concurrent calls
        }
        
        # Track last request times for rate limiting
        self.last_requests = {}
        self.min_intervals = {
            "yahoo_finance": 0.1,  # 100ms between requests
            "external_api": 0.2,   # 200ms between requests
        }
    
    async def acquire(self, service: str = "external_api"):
        """Acquire rate limit semaphore"""
        if service not in self.semaphores:
            service = "external_api"
        
        # Wait for semaphore
        await self.semaphores[service].acquire()
        
        # Check minimum interval
        current_time = time.time()
        last_request = self.last_requests.get(service, 0)
        min_interval = self.min_intervals.get(service, 0.1)
        
        time_since_last = current_time - last_request
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_requests[service] = time.time()
        logger.debug(f"Rate limiter acquired for {service}")
    
    def release(self, service: str = "external_api"):
        """Release rate limit semaphore"""
        if service not in self.semaphores:
            service = "external_api"
        
        self.semaphores[service].release()
        logger.debug(f"Rate limiter released for {service}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        return {
            "semaphores": {
                name: {
                    "max_concurrent": sem._value + len(sem._waiters) if hasattr(sem, '_waiters') else sem._value,
                    "available": sem._value,
                    "waiting": len(sem._waiters) if hasattr(sem, '_waiters') else 0
                }
                for name, sem in self.semaphores.items()
            },
            "last_requests": self.last_requests,
            "min_intervals": self.min_intervals
        }

# Global rate limiter instance
rate_limiter = RateLimiter()