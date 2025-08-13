"""
Cache service for Redis integration
"""

import json
import logging
from typing import Any, Optional, Dict
from datetime import timedelta
import asyncio

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

class CacheService:
    """Redis-based cache service with fallback to in-memory cache"""
    
    def __init__(self):
        self.redis_client = None
        self.in_memory_cache = {}  # Fallback cache
        self.cache_settings = {
            "stocks": 300,      # 5 minutes
            "cryptos": 180,     # 3 minutes  
            "positions": 120,   # 2 minutes
            "summary": 60,      # 1 minute
            "health": 30,       # 30 seconds
        }
        
        # Try to connect to Redis
        self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection with fallback"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using in-memory cache")
            return
        
        try:
            self.redis_client = redis.Redis(
                host='localhost', 
                port=6379, 
                db=0,
                decode_responses=True,
                socket_timeout=1,
                socket_connect_timeout=1
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed: {str(e)}, using in-memory cache")
            self.redis_client = None
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self.redis_client:
                # Try Redis first
                cached_value = self.redis_client.get(key)
                if cached_value:
                    return json.loads(cached_value)
            else:
                # Use in-memory cache
                if key in self.in_memory_cache:
                    return self.in_memory_cache[key]['data']
            
            return None
            
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, cache_type: str = "default") -> bool:
        """Set value in cache with TTL"""
        try:
            ttl = self.cache_settings.get(cache_type, 300)
            serialized_value = json.dumps(value, default=str)
            
            if self.redis_client:
                # Use Redis
                self.redis_client.setex(key, ttl, serialized_value)
            else:
                # Use in-memory cache with simple TTL
                import time
                self.in_memory_cache[key] = {
                    'data': value,
                    'expires': time.time() + ttl
                }
                # Clean expired entries
                await self._cleanup_memory_cache()
            
            logger.debug(f"Cached {key} for {ttl} seconds")
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            if self.redis_client:
                self.redis_client.delete(key)
            else:
                self.in_memory_cache.pop(key, None)
            
            logger.debug(f"Deleted cache key: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {str(e)}")
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        try:
            count = 0
            if self.redis_client:
                keys = self.redis_client.keys(pattern)
                if keys:
                    count = self.redis_client.delete(*keys)
            else:
                # Pattern matching for in-memory cache
                keys_to_delete = [k for k in self.in_memory_cache.keys() if pattern.replace('*', '') in k]
                for key in keys_to_delete:
                    del self.in_memory_cache[key]
                count = len(keys_to_delete)
            
            logger.info(f"Invalidated {count} keys matching pattern: {pattern}")
            return count
            
        except Exception as e:
            logger.error(f"Cache invalidate error for pattern {pattern}: {str(e)}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            if self.redis_client:
                info = self.redis_client.info()
                keys = self.redis_client.keys("*")
                return {
                    "type": "redis",
                    "connected": True,
                    "keys_count": len(keys),
                    "memory_usage": info.get("used_memory_human", "N/A"),
                    "keys": keys[:10] if keys else []  # Show first 10 keys
                }
            else:
                import time
                # Clean expired entries first
                await self._cleanup_memory_cache()
                return {
                    "type": "in_memory",
                    "connected": False,
                    "keys_count": len(self.in_memory_cache),
                    "keys": list(self.in_memory_cache.keys())[:10]
                }
                
        except Exception as e:
            logger.error(f"Cache stats error: {str(e)}")
            return {"type": "error", "connected": False, "error": str(e)}
    
    async def _cleanup_memory_cache(self):
        """Clean expired entries from in-memory cache"""
        if not self.redis_client:
            import time
            current_time = time.time()
            expired_keys = [
                key for key, data in self.in_memory_cache.items()
                if data.get('expires', 0) < current_time
            ]
            for key in expired_keys:
                del self.in_memory_cache[key]

# Global cache instance
cache_service = CacheService()