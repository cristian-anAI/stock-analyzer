"""
Unified Scoring Service - Combines all scoring systems
Integrates ScoringService, AdvancedScoringService, and MTSS granular scoring
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import yfinance as yf
import json

from .scoring_service import ScoringService
from .advanced_scoring_service import AdvancedScoringService
from .timeframe_data_service import TimeframeDataService
from .monthly_score_debug_logger import monthly_debug_logger
from ..strategies.multi_timeframe_strategy import MTSSParameters, TimeframeScore
from ..database.database import db_manager

logger = logging.getLogger(__name__)

class UnifiedScoringService:
    """
    Unified scoring service that combines all scoring methodologies
    - Traditional scoring (ScoringService) 
    - Advanced weighted scoring (AdvancedScoringService)
    - MTSS granular multi-timeframe scoring
    
    Maintains proven thresholds: buy=6.0, sell=4.0 for compatibility
    """
    
    def __init__(self):
        self.scoring_service = ScoringService()
        self.advanced_scoring_service = AdvancedScoringService()
        self.timeframe_service = TimeframeDataService()
        
        # Proven thresholds from backtesting
        self.buy_threshold = 6.0
        self.sell_threshold = 4.0
        
        # MTSS parameters for monthly filtering
        self.mtss_params = MTSSParameters()
        
        # Scoring method weights (can be adjusted based on market conditions)
        self.method_weights = {
            'traditional': 0.30,    # 30% - Basic technical scoring
            'advanced': 0.30,       # 30% - Advanced weighted scoring
            'mtss': 0.40           # 40% - Multi-timeframe hierarchical scoring
        }
        
        # Cache for storing scores to avoid recalculation
        self.score_cache = {}
        self.cache_expiry = 300  # 5 minutes
        
    def _is_cache_valid(self, symbol: str) -> bool:
        """Check if cached score is still valid"""
        if symbol not in self.score_cache:
            return False
        
        cache_time = self.score_cache[symbol].get('timestamp')
        if not cache_time:
            return False
            
        return (datetime.now() - cache_time).seconds < self.cache_expiry
    
    def _get_cached_score(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached score if valid"""
        if self._is_cache_valid(symbol):
            return self.score_cache[symbol]['data']
        return None
    
    def _cache_score(self, symbol: str, score_data: Dict[str, Any]):
        """Cache score data with timestamp"""
        self.score_cache[symbol] = {
            'data': score_data,
            'timestamp': datetime.now()
        }
    
    def get_crypto_list(self) -> List[str]:
        """Get list of crypto symbols for mass analysis"""
        return [
            'BTC-USD', 'ETH-USD', 'ADA-USD', 'SOL-USD', 'DOT-USD',
            'MATIC-USD', 'AVAX-USD', 'LINK-USD', 'UNI-USD', 'LTC-USD'
        ]
    
    async def analyze_all_cryptos(self) -> Dict[str, Dict[str, Any]]:
        """Analyze all cryptos and return scores with color indicators"""
        cryptos = self.get_crypto_list()
        results = {}
        
        for symbol in cryptos:
            try:
                # Check cache first
                cached_score = self._get_cached_score(symbol)
                if cached_score:
                    results[symbol] = cached_score
                    continue
                
                # Analyze and cache
                score_data = await self.analyze_symbol(symbol, asset_type='crypto')
                self._cache_score(symbol, score_data)
                results[symbol] = score_data
                
            except Exception as e:
                logger.error(f"Failed to analyze {symbol}: {e}")
                results[symbol] = {
                    'unified_score': 0.0,
                    'color_indicator': 'gray',
                    'error': str(e)
                }
        
        return results
    
    def get_color_indicator(self, score: float) -> str:
        """Get color indicator based on score"""
        if score >= 7.0:
            return 'green'  # Strong buy
        elif score >= 6.0:
            return 'lightgreen'  # Buy
        elif score >= 4.0:
            return 'yellow'  # Hold
        elif score >= 2.0:
            return 'orange'  # Weak
        else:
            return 'red'  # Sell/Avoid
        
        # Cache for expensive monthly calculations
        self.monthly_cache = {}
        self.cache_duration = timedelta(hours=6)  # Cache monthly data for 6 hours
        
        logger.info("UnifiedScoringService initialized with proven thresholds (buy=6.0, sell=4.0)")
    
    def calculate_unified_score(self, symbol: str, asset_type: str = 'stock', 
                              market_data: Optional[Dict[str, Any]] = None, 
                              focus_timeframe: str = None) -> Dict[str, Any]:
        """
        Calculate unified score combining all scoring methodologies
        
        Args:
            symbol: Symbol to score (e.g., 'AAPL', 'BTC-USD')
            asset_type: 'stock' or 'crypto'
            market_data: Optional pre-fetched market data
            focus_timeframe: Optional specific timeframe to focus on ('1h', '1d', '1W', '1M')
        
        Returns:
            Comprehensive scoring breakdown with final unified score
        """
        try:
            logger.info(f"Calculating unified score for {symbol} ({asset_type})")
            
            # Get market data if not provided
            if market_data is None:
                market_data = self._fetch_market_data(symbol, asset_type)
            
            # Calculate scores using all methods
            traditional_score = self._calculate_traditional_score(symbol, asset_type, market_data)
            advanced_result = self._calculate_advanced_score(symbol, asset_type, market_data)
            mtss_result = self._calculate_mtss_score(symbol, asset_type, market_data, focus_timeframe)
            
            # Calculate weighted final score
            final_score = (
                traditional_score * self.method_weights['traditional'] +
                advanced_result['score'] * self.method_weights['advanced'] +
                mtss_result['score'] * self.method_weights['mtss']
            )
            
            # Ensure score is within bounds
            final_score = max(0.0, min(10.0, final_score))
            
            # Determine trading signals
            trading_signal = self._determine_trading_signal(final_score, mtss_result)
            
            # Assess confidence based on method agreement
            confidence = self._calculate_confidence(traditional_score, advanced_result, mtss_result)
            
            result = {
                'symbol': symbol,
                'asset_type': asset_type,
                'timestamp': datetime.now().isoformat(),
                
                # Final unified score
                'unified_score': round(final_score, 2),
                'trading_signal': trading_signal['action'],
                'confidence': confidence,
                
                # Individual method scores
                'breakdown': {
                    'traditional': {
                        'score': traditional_score,
                        'weight': self.method_weights['traditional'],
                        'contribution': traditional_score * self.method_weights['traditional']
                    },
                    'advanced': {
                        'score': advanced_result['score'],
                        'weight': self.method_weights['advanced'], 
                        'contribution': advanced_result['score'] * self.method_weights['advanced'],
                        'details': advanced_result.get('details', {})
                    },
                    'mtss': {
                        'score': mtss_result['score'],
                        'weight': self.method_weights['mtss'],
                        'contribution': mtss_result['score'] * self.method_weights['mtss'],
                        'monthly_filter_passed': mtss_result.get('monthly_filter_passed', False),
                        'timeframe_scores': mtss_result.get('timeframe_scores', {}),
                        'data_quality': mtss_result.get('data_quality', {})
                    }
                },
                
                # Trading recommendations
                'recommendations': {
                    'action': trading_signal['action'],
                    'position_size': trading_signal.get('position_size', 0.0),
                    'stop_loss': trading_signal.get('stop_loss'),
                    'take_profit': trading_signal.get('take_profit'),
                    'max_hold_days': trading_signal.get('max_hold_days', 15),
                    'risk_level': self._assess_risk_level(final_score, confidence),
                    'reasoning': trading_signal.get('reasoning', [])
                },
                
                # Debugging information
                'debug_info': {
                    'thresholds': {
                        'buy_threshold': self.buy_threshold,
                        'sell_threshold': self.sell_threshold
                    },
                    'method_weights': self.method_weights,
                    'data_sources_used': mtss_result.get('data_sources', []),
                    'calculation_time_ms': 0  # Will be filled by caller if needed
                }
            }
            
            logger.info(f"Unified score for {symbol}: {final_score:.2f} -> {trading_signal['action']} (confidence: {confidence:.1%})")
            
            # Debug logging for monthly scoring issues
            monthly_debug_logger.log_unified_score_breakdown(symbol, result)
            
            # Add color indicator for frontend
            result['color_indicator'] = self.get_color_indicator(final_score)
            
            # Cache unified score in database for bulk frontend access
            self._cache_unified_score(symbol, result, focus_timeframe)
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating unified score for {symbol}: {e}")
            return self._get_error_result(symbol, asset_type, str(e))
    
    def _fetch_market_data(self, symbol: str, asset_type: str) -> Dict[str, Any]:
        """Fetch comprehensive market data for scoring"""
        try:
            # Get basic price data
            ticker = yf.Ticker(symbol)
            history = ticker.history(period="5d", interval="1d")
            info = ticker.info
            
            if history.empty:
                return {}
            
            current_price = history['Close'].iloc[-1]
            prev_price = history['Close'].iloc[-2] if len(history) > 1 else current_price
            
            market_data = {
                'symbol': symbol,
                'current_price': float(current_price),
                'change_amount': float(current_price - prev_price),
                'change_percent': float((current_price - prev_price) / prev_price * 100) if prev_price != 0 else 0,
                'volume': int(history['Volume'].iloc[-1]) if not history['Volume'].empty else 0,
                'market_cap': info.get('marketCap', 0),
                'sector': info.get('sector', 'Unknown') if asset_type == 'stock' else 'Cryptocurrency'
            }
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {e}")
            return {}
    
    def _calculate_traditional_score(self, symbol: str, asset_type: str, market_data: Dict[str, Any]) -> float:
        """Calculate traditional score using ScoringService"""
        try:
            if asset_type == 'crypto':
                return self.scoring_service.calculate_crypto_score(market_data)
            else:
                return self.scoring_service.calculate_stock_score(market_data)
        except Exception as e:
            logger.error(f"Error calculating traditional score for {symbol}: {e}")
            return 5.0  # Neutral default
    
    def _calculate_advanced_score(self, symbol: str, asset_type: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate advanced weighted score"""
        try:
            if asset_type == 'crypto':
                advanced_result = self.advanced_scoring_service.calculate_short_weighted_score(market_data)
                # Convert SHORT score (0-2 bearish, 8-10 bullish) to standard 0-10 scale
                raw_score = advanced_result.get('final_score', 5.0)
                # Invert SHORT scoring: if raw_score < 2 (SHORT territory), convert to high score for buying
                if raw_score < 2.0:
                    converted_score = 8.0 + (2.0 - raw_score)  # 0->10, 2->8
                elif raw_score > 8.0:
                    converted_score = raw_score * 0.6  # Scale down high scores
                else:
                    converted_score = raw_score
                
                return {
                    'score': min(10.0, max(0.0, converted_score)),
                    'details': advanced_result.get('breakdown', {}),
                    'confidence': advanced_result.get('confidence', 0.5)
                }
            else:
                # For stocks, use a simplified version of advanced scoring
                base_score = self._calculate_traditional_score(symbol, asset_type, market_data)
                return {
                    'score': base_score,
                    'details': {'method': 'traditional_fallback'},
                    'confidence': 0.7
                }
        except Exception as e:
            logger.error(f"Error calculating advanced score for {symbol}: {e}")
            return {'score': 5.0, 'details': {}, 'confidence': 0.3}
    
    def _calculate_mtss_score(self, symbol: str, asset_type: str, market_data: Dict[str, Any], focus_timeframe: str = None) -> Dict[str, Any]:
        """Calculate MTSS multi-timeframe score with improved monthly data handling
        
        Args:
            focus_timeframe: If specified, gives extra weight to this timeframe ('1h', '1d', '1W', '1M')
        """
        try:
            # Get multi-timeframe data
            timeframe_data = self._get_mtss_timeframe_data(symbol, asset_type)
            
            if not timeframe_data:
                logger.warning(f"No timeframe data available for MTSS scoring of {symbol}")
                return {
                    'score': 5.0,
                    'monthly_filter_passed': False,
                    'timeframe_scores': {},
                    'data_quality': {'status': 'insufficient_data'},
                    'data_sources': ['none']
                }
            
            # Calculate scores for each timeframe
            timeframe_scores = {}
            data_quality = {}
            
            # Monthly score (critical filter)
            monthly_score = self._calculate_monthly_macd_score(symbol, timeframe_data.get('1M'))
            timeframe_scores['1M'] = monthly_score
            data_quality['1M'] = self._assess_data_quality(timeframe_data.get('1M'), '1M')
            
            # Weekly score (trend context)
            weekly_result = self._calculate_weekly_ichimoku_score_detailed(symbol, timeframe_data.get('1W'))
            weekly_score = weekly_result['score']
            timeframe_scores['1W'] = weekly_score
            data_quality['1W'] = self._assess_data_quality(timeframe_data.get('1W'), '1W')
            data_quality['1W']['indicator_breakdown'] = weekly_result['breakdown']
            
            # Daily score (momentum)
            daily_score = self._calculate_daily_ma_score(symbol, timeframe_data.get('1d'))
            timeframe_scores['1d'] = daily_score
            data_quality['1d'] = self._assess_data_quality(timeframe_data.get('1d'), '1d')
            
            # Hourly score (timing)
            hourly_score = self._calculate_hourly_rsi_score(symbol, timeframe_data.get('1h'))
            timeframe_scores['1h'] = hourly_score
            data_quality['1h'] = self._assess_data_quality(timeframe_data.get('1h'), '1h')
            
            # Calculate weighted MTSS score
            monthly_filter_passed = monthly_score >= self.mtss_params.monthly_filter_min
            
            if not monthly_filter_passed:
                # Monthly filter blocks trade
                mtss_score = 2.0
                logger.debug(f"MTSS {symbol}: Monthly filter blocked (score: {monthly_score:.1f})")
            else:
                # Calculate weighted score with optional focus timeframe
                if focus_timeframe and focus_timeframe in timeframe_scores:
                    # Give extra weight to focused timeframe for scheduler
                    base_weights = {
                        '1M': self.mtss_params.weight_monthly,
                        '1W': self.mtss_params.weight_weekly, 
                        '1d': self.mtss_params.weight_daily,
                        '1h': self.mtss_params.weight_hourly
                    }
                    
                    # Increase focus timeframe weight by 50%
                    focus_weight_boost = 0.5
                    base_weights[focus_timeframe] *= (1 + focus_weight_boost)
                    
                    # Normalize weights to sum to 1.0
                    total_weight = sum(base_weights.values())
                    normalized_weights = {tf: w/total_weight for tf, w in base_weights.items()}
                    
                    weighted_score = (
                        monthly_score * normalized_weights['1M'] +
                        weekly_score * normalized_weights['1W'] +
                        daily_score * normalized_weights['1d'] +
                        hourly_score * normalized_weights['1h']
                    )
                    logger.debug(f"MTSS {symbol}: Focus timeframe {focus_timeframe} boosted (weight: {normalized_weights[focus_timeframe]:.2f})")
                else:
                    # Standard weighted calculation
                    weighted_score = (
                        monthly_score * self.mtss_params.weight_monthly +
                        weekly_score * self.mtss_params.weight_weekly +
                        daily_score * self.mtss_params.weight_daily +
                        hourly_score * self.mtss_params.weight_hourly
                    )
                
                mtss_score = min(10.0, max(0.0, weighted_score))
            
            return {
                'score': mtss_score,
                'monthly_filter_passed': monthly_filter_passed,
                'timeframe_scores': {
                    '1M': monthly_score,
                    '1W': weekly_score, 
                    '1d': daily_score,
                    '1h': hourly_score
                },
                'data_quality': data_quality,
                'data_sources': list(timeframe_data.keys())
            }
            
        except Exception as e:
            logger.error(f"Error calculating MTSS score for {symbol}: {e}")
            return {
                'score': 5.0,
                'monthly_filter_passed': False,
                'timeframe_scores': {},
                'data_quality': {'status': 'calculation_error', 'error': str(e)},
                'data_sources': []
            }
    
    def _get_mtss_timeframe_data(self, symbol: str, asset_type: str) -> Dict[str, pd.DataFrame]:
        """Get data for all MTSS timeframes with improved monthly data fetching"""
        timeframes = ['1M', '1W', '1d', '1h']
        timeframe_data = {}
        
        for tf in timeframes:
            try:
                if asset_type == 'crypto':
                    data = self.timeframe_service.get_crypto_data(symbol, tf)
                else:
                    data = self.timeframe_service.get_stock_data(symbol, tf)
                
                if data is not None and not data.empty:
                    timeframe_data[tf] = data
                    logger.debug(f"Got {len(data)} periods of {tf} data for {symbol}")
                else:
                    logger.warning(f"No {tf} data for {symbol}")
                    
            except Exception as e:
                logger.error(f"Error fetching {tf} data for {symbol}: {e}")
        
        return timeframe_data
    
    def _calculate_monthly_macd_score(self, symbol: str, data: Optional[pd.DataFrame]) -> float:
        """Calculate monthly MACD score with adaptive parameters for limited data"""
        if data is None or data.empty:
            logger.warning(f"No monthly data for {symbol} - using neutral score")
            return 5.0
        
        try:
            min_periods = 26  # Minimum for MACD calculation
            if len(data) < min_periods:
                logger.warning(f"Insufficient monthly data for {symbol}: {len(data)} < {min_periods}")
                # Fallback to simple momentum calculation
                if len(data) >= 3:
                    recent_change = (data['Close'].iloc[-1] - data['Close'].iloc[-3]) / data['Close'].iloc[-3]
                    if recent_change > 0.05:  # 5% growth over 3 months
                        return 7.0
                    elif recent_change < -0.05:
                        return 3.0
                    else:
                        return 5.0
                return 5.0
            
            # Calculate MACD with adaptive parameters for limited data
            close = data['Close']
            
            # Use shorter periods if we have limited data
            if len(data) < 50:
                fast_period = 8
                slow_period = 16
                signal_period = 6
            else:
                fast_period = self.mtss_params.macd_fast
                slow_period = self.mtss_params.macd_slow
                signal_period = self.mtss_params.macd_signal
            
            # Calculate EMAs
            ema_fast = close.ewm(span=fast_period).mean()
            ema_slow = close.ewm(span=slow_period).mean()
            
            # MACD line
            macd_line = ema_fast - ema_slow
            
            # Signal line
            macd_signal = macd_line.ewm(span=signal_period).mean()
            
            # Current values
            current_macd = macd_line.iloc[-1]
            current_signal = macd_signal.iloc[-1]
            macd_histogram = current_macd - current_signal
            
            # Calculate score based on MACD strength
            if macd_histogram > 0.02:  # Strong bullish
                score = 8.5
            elif macd_histogram > 0:  # Bullish
                score = 7.0
            elif macd_histogram > -0.01:  # Neutral/slightly bearish
                score = 5.5
            else:  # Bearish
                score = 3.0
            
            logger.debug(f"Monthly MACD for {symbol}: histogram={macd_histogram:.4f} -> score={score:.1f}")
            
            # Debug logging for monthly score calculation
            calculation_data = {
                'data_periods': len(data),
                'macd_histogram': macd_histogram,
                'final_score': score,
                'data_quality': 'good' if len(data) >= 26 else 'limited',
                'calculation_method': 'adaptive_macd' if len(data) < 50 else 'standard_macd',
                'macd_params': {
                    'fast_period': fast_period,
                    'slow_period': slow_period,
                    'signal_period': signal_period
                }
            }
            monthly_debug_logger.log_monthly_score_calculation(symbol, 'monthly_macd', calculation_data)
            
            # Log filter decision
            filter_passed = score >= self.mtss_params.monthly_filter_min
            reasoning = f"MACD histogram {macd_histogram:.4f} -> score {score:.1f}"
            monthly_debug_logger.log_monthly_filter_decision(
                symbol, score, self.mtss_params.monthly_filter_min, filter_passed, reasoning
            )
            
            return score
            
        except Exception as e:
            logger.error(f"Error calculating monthly MACD for {symbol}: {e}")
            return 5.0
    
    def _calculate_weekly_ichimoku_score_detailed(self, symbol: str, data: Optional[pd.DataFrame]) -> Dict[str, Any]:
        """Calculate weekly Ichimoku score with detailed breakdown"""
        if data is None or data.empty:
            return {
                'score': 5.0,
                'breakdown': {
                    'indicator': 'Ichimoku Cloud',
                    'status': 'No data available',
                    'reason': 'Insufficient data for Ichimoku analysis',
                    'components': {}
                }
            }
        
        try:
            if len(data) < 52:  # Need at least 1 year of weekly data
                logger.debug(f"Limited weekly data for {symbol}: {len(data)} periods")
                # Simple MA comparison as fallback
                if len(data) >= 10:
                    ma10 = data['Close'].rolling(10).mean().iloc[-1]
                    current_price = data['Close'].iloc[-1]
                    if current_price > ma10:
                        return {
                            'score': 7.0,
                            'breakdown': {
                                'indicator': 'Moving Average (Fallback)',
                                'status': 'Above MA10',
                                'reason': f'Price ${current_price:.2f} above MA10 ${ma10:.2f}',
                                'components': {
                                    'current_price': current_price,
                                    'ma10': ma10,
                                    'position': 'above'
                                }
                            }
                        }
                    else:
                        return {
                            'score': 4.0,
                            'breakdown': {
                                'indicator': 'Moving Average (Fallback)', 
                                'status': 'Below MA10',
                                'reason': f'Price ${current_price:.2f} below MA10 ${ma10:.2f}',
                                'components': {
                                    'current_price': current_price,
                                    'ma10': ma10,
                                    'position': 'below'
                                }
                            }
                        }
                return {
                    'score': 5.0,
                    'breakdown': {
                        'indicator': 'Insufficient Data',
                        'status': 'Neutral',
                        'reason': 'Not enough data for analysis',
                        'components': {}
                    }
                }
            
            # Full Ichimoku calculation
            high = data['High']
            low = data['Low']
            close = data['Close']
            
            # Tenkan-sen (9-period)
            tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
            
            # Kijun-sen (26-period)
            kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
            
            # Current values
            current_price = close.iloc[-1]
            current_tenkan = tenkan.iloc[-1]
            current_kijun = kijun.iloc[-1]
            
            # Determine position relative to cloud
            cloud_top = max(current_tenkan, current_kijun)
            cloud_bottom = min(current_tenkan, current_kijun)
            
            if current_price > cloud_top:
                score = 8.0
                status = 'Above Ichimoku Cloud'
                reason = f'Price ${current_price:.2f} above cloud (${cloud_top:.2f})'
                position = 'above_cloud'
            elif current_price > cloud_bottom:
                score = 6.0
                status = 'Inside Ichimoku Cloud'
                reason = f'Price ${current_price:.2f} within cloud (${cloud_bottom:.2f} - ${cloud_top:.2f})'
                position = 'in_cloud'
            else:
                score = 4.0
                status = 'Below Ichimoku Cloud'
                reason = f'Price ${current_price:.2f} below cloud (${cloud_bottom:.2f})'
                position = 'below_cloud'
            
            return {
                'score': score,
                'breakdown': {
                    'indicator': 'Ichimoku Cloud',
                    'status': status,
                    'reason': reason,
                    'components': {
                        'current_price': current_price,
                        'tenkan_sen': current_tenkan,
                        'kijun_sen': current_kijun,
                        'cloud_top': cloud_top,
                        'cloud_bottom': cloud_bottom,
                        'position': position
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating weekly Ichimoku for {symbol}: {e}")
            return {
                'score': 5.0,
                'breakdown': {
                    'indicator': 'Ichimoku Cloud',
                    'status': 'Error',
                    'reason': f'Calculation error: {str(e)}',
                    'components': {}
                }
            }

    def _calculate_weekly_ichimoku_score(self, symbol: str, data: Optional[pd.DataFrame]) -> float:
        """Calculate weekly Ichimoku score"""
        if data is None or data.empty:
            return 5.0
        
        try:
            if len(data) < 52:  # Need at least 1 year of weekly data
                logger.debug(f"Limited weekly data for {symbol}: {len(data)} periods")
                # Simple MA comparison as fallback
                if len(data) >= 10:
                    ma10 = data['Close'].rolling(10).mean().iloc[-1]
                    current_price = data['Close'].iloc[-1]
                    if current_price > ma10:
                        return 7.0
                    else:
                        return 4.0
                return 5.0
            
            # Simplified Ichimoku calculation
            high = data['High']
            low = data['Low']
            close = data['Close']
            
            # Tenkan-sen (9-period)
            tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
            
            # Kijun-sen (26-period)
            kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
            
            # Current price vs cloud approximation
            current_price = close.iloc[-1]
            current_tenkan = tenkan.iloc[-1]
            current_kijun = kijun.iloc[-1]
            
            if current_price > max(current_tenkan, current_kijun):
                score = 8.0  # Above cloud
            elif current_price > min(current_tenkan, current_kijun):
                score = 6.0  # In cloud
            else:
                score = 4.0  # Below cloud
            
            return score
            
        except Exception as e:
            logger.error(f"Error calculating weekly Ichimoku for {symbol}: {e}")
            return 5.0
    
    def _calculate_daily_ma_score(self, symbol: str, data: Optional[pd.DataFrame]) -> float:
        """Calculate daily moving average score"""
        if data is None or data.empty:
            return 5.0
        
        try:
            if len(data) < 50:
                logger.debug(f"Limited daily data for {symbol}: {len(data)} periods")
                # Use available data with shorter MA periods
                ma_short = min(10, len(data) // 2)
                ma_long = min(20, len(data) * 3 // 4)
            else:
                ma_short = 20
                ma_long = 50
            
            if len(data) < ma_long:
                return 5.0
            
            close = data['Close']
            ma_fast = close.rolling(ma_short).mean().iloc[-1]
            ma_slow = close.rolling(ma_long).mean().iloc[-1]
            current_price = close.iloc[-1]
            
            # Score based on MA alignment
            if current_price > ma_fast > ma_slow:
                score = 8.0  # Strong bullish alignment
            elif current_price > ma_fast:
                score = 7.0  # Price above short MA
            elif current_price > ma_slow:
                score = 6.0  # Price above long MA
            elif ma_fast > ma_slow:
                score = 5.5  # MAs bullish but price below
            else:
                score = 4.0  # Bearish alignment
            
            return score
            
        except Exception as e:
            logger.error(f"Error calculating daily MA for {symbol}: {e}")
            return 5.0
    
    def _calculate_hourly_rsi_score(self, symbol: str, data: Optional[pd.DataFrame]) -> float:
        """Calculate hourly RSI score"""
        if data is None or data.empty:
            return 5.0
        
        try:
            if len(data) < 20:
                return 5.0
            
            # Calculate RSI
            close = data['Close']
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            current_rsi = rsi.iloc[-1]
            
            # Score based on RSI (optimal buying zones)
            if current_rsi < 30:
                score = 8.5  # Oversold - good buying opportunity
            elif current_rsi < 40:
                score = 7.5  # Favorable
            elif current_rsi < 60:
                score = 6.0  # Neutral
            elif current_rsi < 70:
                score = 5.0  # Slightly elevated
            else:
                score = 3.0  # Overbought
            
            return score
            
        except Exception as e:
            logger.error(f"Error calculating hourly RSI for {symbol}: {e}")
            return 5.0
    
    def _assess_data_quality(self, data: Optional[pd.DataFrame], timeframe: str) -> Dict[str, Any]:
        """Assess quality of timeframe data"""
        if data is None or data.empty:
            return {'status': 'no_data', 'periods': 0, 'quality': 'poor'}
        
        periods = len(data)
        expected_periods = {
            '1M': 24,   # 2 years
            '1W': 52,   # 1 year
            '1d': 90,   # 3 months
            '1h': 168   # 1 week
        }
        
        expected = expected_periods.get(timeframe, 50)
        quality_ratio = periods / expected
        
        if quality_ratio >= 0.8:
            quality = 'good'
        elif quality_ratio >= 0.5:
            quality = 'fair'
        else:
            quality = 'poor'
        
        return {
            'status': 'available',
            'periods': periods,
            'expected': expected,
            'quality': quality,
            'quality_ratio': round(quality_ratio, 2)
        }
    
    def _determine_trading_signal(self, final_score: float, mtss_result: Dict[str, Any]) -> Dict[str, Any]:
        """Determine trading action based on unified score"""
        try:
            current_price = 100.0  # Will be filled with actual price
            
            # Monthly filter check
            monthly_filter_passed = mtss_result.get('monthly_filter_passed', True)
            
            if not monthly_filter_passed:
                return {
                    'action': 'HOLD',
                    'reasoning': ['Monthly MACD filter blocked entry'],
                    'confidence': 0.1
                }
            
            # Apply proven thresholds
            if final_score >= self.buy_threshold:
                action = 'BUY'
                position_size_pct = min(3.0, (final_score - self.buy_threshold) * 0.5 + 2.0)  # 2-3% position
                stop_loss = current_price * 0.93  # 7% stop loss
                take_profit = current_price * 1.12  # 12% take profit
                reasoning = [f'Unified score {final_score:.1f} >= buy threshold {self.buy_threshold}']
                
                if final_score >= 8.0:
                    reasoning.append('Strong multi-method alignment')
                if mtss_result.get('monthly_filter_passed', False):
                    reasoning.append('Monthly MACD filter passed')
                    
            elif final_score <= self.sell_threshold:
                action = 'SELL'  # Or exit existing positions
                position_size_pct = 0.0
                stop_loss = None
                take_profit = None
                reasoning = [f'Unified score {final_score:.1f} <= sell threshold {self.sell_threshold}']
            else:
                action = 'HOLD'
                position_size_pct = 0.0
                stop_loss = None
                take_profit = None
                reasoning = [f'Unified score {final_score:.1f} between thresholds ({self.sell_threshold}-{self.buy_threshold})']
            
            return {
                'action': action,
                'position_size': position_size_pct,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'max_hold_days': 15,
                'reasoning': reasoning
            }
            
        except Exception as e:
            logger.error(f"Error determining trading signal: {e}")
            return {'action': 'HOLD', 'reasoning': [f'Error: {str(e)}']}
    
    def _calculate_confidence(self, traditional_score: float, advanced_result: Dict[str, Any], 
                            mtss_result: Dict[str, Any]) -> float:
        """Calculate confidence based on agreement between methods"""
        try:
            scores = [traditional_score, advanced_result['score'], mtss_result['score']]
            
            # Calculate standard deviation (lower = more agreement)
            std_dev = np.std(scores)
            
            # Base confidence from method-specific confidences
            base_confidence = (
                0.7 +  # Traditional method baseline
                advanced_result.get('confidence', 0.5) * 0.3 +
                0.8 * (1 if mtss_result.get('monthly_filter_passed', False) else 0.3)
            ) / 2
            
            # Adjust based on agreement (lower std_dev = higher confidence)
            agreement_factor = max(0.5, 1.0 - (std_dev / 5.0))  # Normalize std_dev
            
            # Data quality adjustment
            data_quality_factor = 1.0
            for tf_quality in mtss_result.get('data_quality', {}).values():
                if isinstance(tf_quality, dict) and tf_quality.get('quality') == 'poor':
                    data_quality_factor *= 0.8
            
            final_confidence = base_confidence * agreement_factor * data_quality_factor
            return max(0.1, min(0.95, final_confidence))
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.5
    
    def _assess_risk_level(self, score: float, confidence: float) -> str:
        """Assess risk level based on score and confidence"""
        if score >= 8.0 and confidence >= 0.8:
            return "LOW"
        elif score >= 6.0 and confidence >= 0.6:
            return "MEDIUM"
        elif score >= 4.0:
            return "HIGH"
        else:
            return "VERY_HIGH"
    
    def _get_error_result(self, symbol: str, asset_type: str, error_msg: str) -> Dict[str, Any]:
        """Return error result with neutral scoring"""
        return {
            'symbol': symbol,
            'asset_type': asset_type,
            'unified_score': 5.0,
            'trading_signal': 'HOLD',
            'confidence': 0.1,
            'error': error_msg,
            'breakdown': {
                'traditional': {'score': 5.0, 'weight': 0.3, 'contribution': 1.5},
                'advanced': {'score': 5.0, 'weight': 0.3, 'contribution': 1.5},
                'mtss': {'score': 5.0, 'weight': 0.4, 'contribution': 2.0}
            }
        }
    
    def update_method_weights(self, new_weights: Dict[str, float]):
        """Update method weights (must sum to 1.0)"""
        if abs(sum(new_weights.values()) - 1.0) < 0.001:
            self.method_weights.update(new_weights)
            logger.info(f"Updated method weights: {self.method_weights}")
        else:
            logger.error(f"Invalid weights (must sum to 1.0): {new_weights}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get status of all scoring components"""
        return {
            'unified_scoring_service': 'active',
            'thresholds': {
                'buy_threshold': self.buy_threshold,
                'sell_threshold': self.sell_threshold
            },
            'method_weights': self.method_weights,
            'mtss_params': {
                'monthly_filter_min': self.mtss_params.monthly_filter_min,
                'timeframe_weights': {
                    'monthly': self.mtss_params.weight_monthly,
                    'weekly': self.mtss_params.weight_weekly,
                    'daily': self.mtss_params.weight_daily,
                    'hourly': self.mtss_params.weight_hourly
                }
            },
            'cache_status': {
                'monthly_cache_entries': len(self.monthly_cache),
                'cache_duration_hours': self.cache_duration.total_seconds() / 3600
            }
        }

    def _cache_unified_score(self, symbol: str, result: Dict[str, Any], focus_timeframe: str = None):
        """Cache unified score result in database for bulk frontend access"""
        try:
            # Determine primary timeframe for caching
            primary_timeframe = focus_timeframe or "unified"
            
            # Extract data for caching
            unified_score = result.get('unified_score', 0)
            trading_signal = result.get('trading_signal', 'HOLD')
            confidence = result.get('confidence', 0)
            
            # Extract MTSS data
            mtss_breakdown = result.get('breakdown', {}).get('mtss', {})
            monthly_filter_passed = mtss_breakdown.get('monthly_filter_passed', False)
            timeframe_scores = mtss_breakdown.get('timeframe_scores', {})
            
            # Calculate data quality score based on available timeframes
            data_quality_score = len([s for s in timeframe_scores.values() if s > 0]) / 4.0 * 10
            
            # If focus_timeframe is specified, cache for that specific timeframe
            if focus_timeframe and focus_timeframe in timeframe_scores:
                specific_score = timeframe_scores[focus_timeframe]
                
                # Cache the timeframe-specific score
                db_manager.execute_update("""
                    INSERT OR REPLACE INTO mtss_scores 
                    (symbol, timeframe, score, timeframe_scores, unified_score, trading_signal, 
                     confidence, monthly_filter_passed, data_quality_score, breakdown, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol.upper(),
                    focus_timeframe,
                    specific_score,
                    json.dumps(timeframe_scores),
                    unified_score,
                    trading_signal,
                    confidence,
                    monthly_filter_passed,
                    data_quality_score,
                    json.dumps(result.get('breakdown', {})),
                    datetime.now().isoformat()
                ))
                
                logger.debug(f"Cached {focus_timeframe} score for {symbol}: {specific_score:.1f}")
            
            # Always cache the unified result
            db_manager.execute_update("""
                INSERT OR REPLACE INTO mtss_scores 
                (symbol, timeframe, score, timeframe_scores, unified_score, trading_signal, 
                 confidence, monthly_filter_passed, data_quality_score, breakdown, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol.upper(),
                "unified",
                unified_score,
                json.dumps(timeframe_scores),
                unified_score,
                trading_signal,
                confidence,
                monthly_filter_passed,
                data_quality_score,
                json.dumps(result.get('breakdown', {})),
                datetime.now().isoformat()
            ))
            
            logger.debug(f"Cached unified score for {symbol}: {unified_score:.2f}")
            
        except Exception as e:
            logger.error(f"Error caching unified score for {symbol}: {e}")
            # Don't raise - caching errors shouldn't break scoring

    async def analyze_symbol(self, symbol: str, asset_type: str = 'stock', focus_timeframe: str = None) -> Dict[str, Any]:
        """
        Analyze a single symbol and return unified scoring result
        
        Args:
            symbol: Symbol to analyze (e.g., 'AAPL', 'BTC-USD')
            asset_type: 'stock' or 'crypto'
            focus_timeframe: Optional specific timeframe to focus on
            
        Returns:
            Dict containing unified score, color indicator, and breakdown
        """
        try:
            # Get cached result if available
            cached_result = self._get_cached_score(symbol)
            if cached_result:
                return cached_result
            
            # Calculate unified score
            result = self.calculate_unified_score(symbol, asset_type, focus_timeframe=focus_timeframe)
            
            # Add color indicator for frontend
            result['color_indicator'] = self.get_color_indicator(result['unified_score'])
            
            # Cache the result
            self._cache_score(symbol, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing symbol {symbol}: {e}")
            return {
                'symbol': symbol,
                'asset_type': asset_type,
                'unified_score': 0.0,
                'color_indicator': 'gray',
                'trading_signal': 'HOLD',
                'confidence': 0.0,
                'error': str(e),
                'breakdown': {
                    'traditional': {'score': 0.0, 'error': str(e)},
                    'advanced': {'score': 0.0, 'error': str(e)},
                    'mtss': {'score': 0.0, 'error': str(e)}
                }
            }