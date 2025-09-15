"""
MTSS Scheduler Service - Multi-Timeframe Scoring Strategy Scheduler

Distributes MTSS analysis across different timeframes to optimize API usage:
- Hourly (1h): Every hour, ~100 high-priority stocks
- Daily (1d): 2-3 times/day, ~200 stocks  
- Weekly (1W): 2 times/week, ~300 stocks
- Monthly (1M): Once/week, all relevant stocks

Prevents API saturation while maintaining comprehensive coverage.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json
from enum import Enum

from ..database.database import db_manager
from .unified_scoring_service import UnifiedScoringService
from .scoring_service import ScoringService

logger = logging.getLogger(__name__)

class TimeframeType(Enum):
    HOURLY = "1h"
    DAILY = "1d" 
    WEEKLY = "1W"
    MONTHLY = "1M"

class MTSSSchedulerService:
    """Multi-Timeframe Scoring Strategy Scheduler"""
    
    def __init__(self):
        self.unified_scoring = UnifiedScoringService()
        self.traditional_scoring = ScoringService()
        
        # API Rate Limiting (total 60 calls/minute distributed)
        self.api_budget_per_timeframe = {
            TimeframeType.HOURLY: 15,   # 15 calls/hour (most frequent)
            TimeframeType.DAILY: 20,    # 20 calls per daily run
            TimeframeType.WEEKLY: 15,   # 15 calls per weekly run  
            TimeframeType.MONTHLY: 10   # 10 calls per monthly run
        }
        
        # Update intervals (in minutes)
        self.update_intervals = {
            TimeframeType.HOURLY: 60,    # Every hour
            TimeframeType.DAILY: 480,    # Every 8 hours (3x/day)
            TimeframeType.WEEKLY: 5040,  # Every 3.5 days (2x/week)
            TimeframeType.MONTHLY: 10080 # Every week
        }
        
        # Priority thresholds for each timeframe
        self.priority_thresholds = {
            TimeframeType.HOURLY: 7.0,   # Only highest scores
            TimeframeType.DAILY: 6.0,    # High scores
            TimeframeType.WEEKLY: 5.5,   # Medium-high scores
            TimeframeType.MONTHLY: 5.0   # All relevant scores
        }
        
        # Last run tracking
        self.last_runs = {
            TimeframeType.HOURLY: None,
            TimeframeType.DAILY: None,
            TimeframeType.WEEKLY: None,
            TimeframeType.MONTHLY: None
        }
        
        # Queue management
        self.processing_queues = {
            TimeframeType.HOURLY: [],
            TimeframeType.DAILY: [],
            TimeframeType.WEEKLY: [],
            TimeframeType.MONTHLY: []
        }
        
        self.is_running = False
        self.stats = {
            "total_symbols_processed": 0,
            "api_calls_made": 0,
            "cache_hits": 0,
            "errors": 0,
            "last_full_cycle": None
        }

    async def start_scheduler(self) -> Dict[str, Any]:
        """Start the MTSS scheduler"""
        if self.is_running:
            logger.warning("MTSS Scheduler already running")
            return {"status": "already_running"}
        
        self.is_running = True
        logger.info("🚀 Starting MTSS Multi-Timeframe Scheduler...")
        
        # Initialize processing queues
        await self._initialize_queues()
        
        logger.info(f"✅ MTSS Scheduler initialized with {sum(len(q) for q in self.processing_queues.values())} total symbols")
        
        return {
            "status": "started",
            "queue_sizes": {tf.value: len(queue) for tf, queue in self.processing_queues.items()},
            "api_budgets": {tf.value: budget for tf, budget in self.api_budget_per_timeframe.items()},
            "update_intervals": {tf.value: interval for tf, interval in self.update_intervals.items()}
        }

    async def stop_scheduler(self) -> Dict[str, Any]:
        """Stop the MTSS scheduler"""
        self.is_running = False
        logger.info("🛑 MTSS Scheduler stopped")
        return {"status": "stopped", "stats": self.stats}

    async def process_timeframe_cycle(self, timeframe: TimeframeType) -> Dict[str, Any]:
        """Process one cycle for a specific timeframe"""
        if not self.is_running:
            return {"status": "scheduler_not_running"}
        
        start_time = datetime.now()
        logger.info(f"🔄 Starting {timeframe.value} scoring cycle...")
        
        # Check if it's time to run this timeframe
        if not self._should_run_timeframe(timeframe):
            return {"status": "not_time_to_run", "timeframe": timeframe.value}
        
        # Get symbols to process for this timeframe
        symbols_to_process = await self._get_symbols_for_timeframe(timeframe)
        api_budget = self.api_budget_per_timeframe[timeframe]
        
        # Limit to budget
        symbols_to_process = symbols_to_process[:api_budget]
        
        processed = 0
        cached = 0
        errors = 0
        results = []
        
        logger.info(f"📊 Processing {len(symbols_to_process)} symbols for {timeframe.value} (budget: {api_budget})")
        
        for symbol_info in symbols_to_process:
            try:
                symbol = symbol_info["symbol"]
                asset_type = symbol_info["asset_type"]
                
                # Check if we have recent cached data for this timeframe
                cached_score = await self._get_cached_score(symbol, timeframe)
                if cached_score:
                    cached += 1
                    results.append({
                        "symbol": symbol,
                        "status": "cached",
                        "score": cached_score["score"],
                        "cached_at": cached_score["updated_at"]
                    })
                    continue
                
                # Perform actual MTSS scoring for this specific timeframe
                mtss_result = await self._score_symbol_timeframe(symbol, asset_type, timeframe)
                
                if mtss_result:
                    # Cache the result
                    await self._cache_score(symbol, timeframe, mtss_result)
                    processed += 1
                    results.append({
                        "symbol": symbol,
                        "status": "processed",
                        "score": mtss_result.get("score", 0),
                        "timeframe": timeframe.value
                    })
                    
                    # Brief delay to respect rate limits
                    await asyncio.sleep(1.0)
                else:
                    errors += 1
                    
            except Exception as e:
                logger.error(f"Error processing {symbol} for {timeframe.value}: {e}")
                errors += 1
        
        # Update last run time
        self.last_runs[timeframe] = datetime.now()
        
        # Update stats
        self.stats["total_symbols_processed"] += processed
        self.stats["api_calls_made"] += processed
        self.stats["cache_hits"] += cached
        self.stats["errors"] += errors
        
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"✅ {timeframe.value} cycle completed in {duration:.1f}s: {processed} processed, {cached} cached, {errors} errors")
        
        return {
            "timeframe": timeframe.value,
            "duration_seconds": duration,
            "processed": processed,
            "cached": cached,
            "errors": errors,
            "total_symbols": len(symbols_to_process),
            "results_sample": results[:5]  # First 5 results for debugging
        }

    async def _initialize_queues(self):
        """Initialize processing queues with symbols prioritized by traditional score"""
        logger.info("🔄 Initializing MTSS processing queues...")
        
        # Get all stocks and cryptos with their traditional scores
        stocks = db_manager.execute_query(
            "SELECT symbol, score, 'stock' as asset_type FROM stocks WHERE score IS NOT NULL ORDER BY score DESC"
        )
        
        cryptos = db_manager.execute_query(
            "SELECT symbol, score, 'crypto' as asset_type FROM cryptos WHERE score IS NOT NULL ORDER BY score DESC"  
        )
        
        all_symbols = stocks + cryptos
        
        # Distribute symbols across timeframes based on priority thresholds
        for timeframe in TimeframeType:
            threshold = self.priority_thresholds[timeframe]
            qualified_symbols = [
                {
                    "symbol": s["symbol"],
                    "asset_type": s["asset_type"], 
                    "traditional_score": s["score"]
                }
                for s in all_symbols 
                if s["score"] >= threshold
            ]
            
            self.processing_queues[timeframe] = qualified_symbols
            logger.info(f"📊 {timeframe.value}: {len(qualified_symbols)} symbols (score >= {threshold})")

    def _should_run_timeframe(self, timeframe: TimeframeType) -> bool:
        """Check if it's time to run a specific timeframe"""
        if self.last_runs[timeframe] is None:
            return True  # Never run before
        
        interval_minutes = self.update_intervals[timeframe]
        time_since_last = datetime.now() - self.last_runs[timeframe]
        
        return time_since_last.total_seconds() >= (interval_minutes * 60)

    async def _get_symbols_for_timeframe(self, timeframe: TimeframeType) -> List[Dict[str, Any]]:
        """Get symbols to process for a specific timeframe"""
        return self.processing_queues[timeframe].copy()

    async def _get_cached_score(self, symbol: str, timeframe: TimeframeType) -> Optional[Dict[str, Any]]:
        """Get cached MTSS score for symbol and timeframe"""
        try:
            # Check cache freshness based on timeframe
            freshness_hours = {
                TimeframeType.HOURLY: 1,    # 1 hour freshness
                TimeframeType.DAILY: 6,     # 6 hours freshness  
                TimeframeType.WEEKLY: 36,   # 1.5 days freshness
                TimeframeType.MONTHLY: 120  # 5 days freshness
            }
            
            hours_limit = freshness_hours[timeframe]
            cutoff_time = datetime.now() - timedelta(hours=hours_limit)
            
            cached_data = db_manager.execute_query(
                """SELECT score, timeframe_scores, updated_at 
                   FROM mtss_scores 
                   WHERE symbol = ? AND timeframe = ? AND updated_at > ?""",
                (symbol, timeframe.value, cutoff_time.isoformat())
            )
            
            if cached_data:
                return {
                    "score": cached_data[0]["score"],
                    "timeframe_scores": json.loads(cached_data[0]["timeframe_scores"]),
                    "updated_at": cached_data[0]["updated_at"]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached score for {symbol} {timeframe.value}: {e}")
            return None

    async def _cache_score(self, symbol: str, timeframe: TimeframeType, score_data: Dict[str, Any]):
        """Cache MTSS score for symbol and timeframe"""
        try:
            # Extract timeframe-specific score
            timeframe_score = score_data.get("breakdown", {}).get("mtss", {}).get("timeframe_scores", {}).get(timeframe.value, 0)
            
            # Upsert cached score
            db_manager.execute_update(
                """INSERT OR REPLACE INTO mtss_scores 
                   (symbol, timeframe, score, timeframe_scores, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    symbol,
                    timeframe.value, 
                    timeframe_score,
                    json.dumps(score_data.get("breakdown", {}).get("mtss", {}).get("timeframe_scores", {})),
                    datetime.now().isoformat()
                )
            )
            
        except Exception as e:
            logger.error(f"Error caching score for {symbol} {timeframe.value}: {e}")

    async def _score_symbol_timeframe(self, symbol: str, asset_type: str, timeframe: TimeframeType) -> Optional[Dict[str, Any]]:
        """Score a symbol for a specific timeframe"""
        try:
            # Get basic market data 
            market_data = await self._get_basic_market_data(symbol, asset_type)
            if not market_data:
                return None
            
            # Calculate unified score with emphasis on specific timeframe
            unified_result = self.unified_scoring.calculate_unified_score(
                symbol, asset_type, market_data, 
                focus_timeframe=timeframe.value
            )
            
            return unified_result
            
        except Exception as e:
            logger.error(f"Error scoring {symbol} for {timeframe.value}: {e}")
            return None

    async def _get_basic_market_data(self, symbol: str, asset_type: str) -> Optional[Dict[str, Any]]:
        """Get basic market data from database"""
        try:
            if asset_type == 'crypto':
                table = "cryptos"
            else:
                table = "stocks"
            
            data = db_manager.execute_query(
                f"SELECT * FROM {table} WHERE symbol = ? LIMIT 1",
                (symbol,)
            )
            
            if data:
                return dict(data[0])
            return None
            
        except Exception as e:
            logger.error(f"Error getting basic market data for {symbol}: {e}")
            return None

    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status and statistics"""
        return {
            "is_running": self.is_running,
            "stats": self.stats,
            "queue_sizes": {tf.value: len(queue) for tf, queue in self.processing_queues.items()},
            "last_runs": {tf.value: last_run.isoformat() if last_run else None 
                         for tf, last_run in self.last_runs.items()},
            "next_scheduled_runs": self._get_next_scheduled_runs(),
            "api_budgets": {tf.value: budget for tf, budget in self.api_budget_per_timeframe.items()},
            "priority_thresholds": {tf.value: threshold for tf, threshold in self.priority_thresholds.items()}
        }

    def _get_next_scheduled_runs(self) -> Dict[str, Optional[str]]:
        """Get next scheduled run times for each timeframe"""
        next_runs = {}
        
        for timeframe in TimeframeType:
            if self.last_runs[timeframe]:
                interval_minutes = self.update_intervals[timeframe]
                next_run = self.last_runs[timeframe] + timedelta(minutes=interval_minutes)
                next_runs[timeframe.value] = next_run.isoformat()
            else:
                next_runs[timeframe.value] = "ready_to_run"
        
        return next_runs

# Global MTSS scheduler instance
mtss_scheduler = MTSSSchedulerService()