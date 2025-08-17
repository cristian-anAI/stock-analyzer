"""
Advanced Scoring Service for SHORT Detection
Implements weighted scoring with technical indicators, sentiment, and momentum
"""

import logging
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import requests
import json

logger = logging.getLogger(__name__)

class AdvancedScoringService:
    """Advanced scoring service with weighted factors for SHORT detection"""
    
    def __init__(self):
        self.weights = {
            'technical': 0.60,    # 60% weight - most important
            'sentiment': 0.25,    # 25% weight - sentiment analysis
            'momentum': 0.15      # 15% weight - volume/momentum
        }
        
        # Cache for technical data
        self.technical_cache = {}
        self.cache_duration = timedelta(minutes=15)
    
    def calculate_short_weighted_score(self, crypto_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate weighted score specifically designed for SHORT detection
        Returns score breakdown and final weighted score
        """
        try:
            symbol = crypto_data.get('symbol', '')
            
            # Get technical score (60% weight)
            technical_score, technical_details = self._calculate_technical_score(crypto_data)
            
            # Get sentiment score (25% weight)
            sentiment_score, sentiment_details = self._calculate_sentiment_score(crypto_data)
            
            # Get momentum score (15% weight)
            momentum_score, momentum_details = self._calculate_momentum_score(crypto_data)
            
            # Calculate weighted final score
            weighted_score = (
                technical_score * self.weights['technical'] +
                sentiment_score * self.weights['sentiment'] +
                momentum_score * self.weights['momentum']
            )
            
            # Ensure score is in range 0-10, with <2.0 being SHORT territory
            final_score = max(0, min(10, weighted_score))
            
            return {
                'final_score': final_score,
                'technical_score': technical_score,
                'sentiment_score': sentiment_score,
                'momentum_score': momentum_score,
                'breakdown': {
                    'technical': technical_details,
                    'sentiment': sentiment_details,
                    'momentum': momentum_details
                },
                'short_eligible': final_score < 2.0,
                'confidence': self._calculate_confidence(technical_details, sentiment_details, momentum_details)
            }
            
        except Exception as e:
            logger.error(f"Error calculating advanced score for {symbol}: {e}")
            return {
                'final_score': 5.0,  # Neutral default
                'short_eligible': False,
                'confidence': 0
            }
    
    def _calculate_technical_score(self, crypto_data: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """Calculate technical indicators score (60% weight)"""
        symbol = crypto_data.get('symbol', '')
        base_score = 5.0  # Start neutral
        details = {}
        
        try:
            # Get enhanced technical data
            tech_data = self._get_technical_data(symbol)
            
            if not tech_data:
                return base_score, {'error': 'No technical data available'}
            
            # 1. RSI Analysis (most important for SHORT)
            rsi = tech_data.get('rsi', 50)
            rsi_trend = tech_data.get('rsi_trend', 'neutral')
            
            if rsi > 75 and rsi_trend == 'down':
                base_score -= 2.0  # Strong bearish signal
                details['rsi'] = f"Overbought RSI {rsi:.1f} trending down (-2.0)"
            elif rsi > 70:
                base_score -= 1.0
                details['rsi'] = f"Overbought RSI {rsi:.1f} (-1.0)"
            elif rsi < 30:
                base_score += 1.5  # Don't SHORT oversold
                details['rsi'] = f"Oversold RSI {rsi:.1f} (+1.5)"
            else:
                details['rsi'] = f"Neutral RSI {rsi:.1f}"
            
            # 2. MACD Analysis
            macd_signal = tech_data.get('macd_signal', 'neutral')
            macd_histogram = tech_data.get('macd_histogram', 0)
            
            if macd_signal == 'bearish_crossover':
                base_score -= 2.0
                details['macd'] = "Bearish MACD crossover (-2.0)"
            elif macd_signal == 'bearish' and macd_histogram < 0:
                base_score -= 1.0
                details['macd'] = "MACD bearish with negative histogram (-1.0)"
            elif macd_signal == 'bullish':
                base_score += 1.0  # Don't SHORT during bullish MACD
                details['macd'] = "Bullish MACD (+1.0)"
            else:
                details['macd'] = f"MACD {macd_signal}"
            
            # 3. Moving Average Analysis
            price = crypto_data.get('current_price', 0)
            ma20 = tech_data.get('ma20', price)
            ma50 = tech_data.get('ma50', price)
            
            if price < ma20 and price < ma50 and ma20 < ma50:
                base_score -= 1.5  # Price below both MAs
                details['moving_averages'] = f"Price below MA20 & MA50 (-1.5)"
            elif price < ma20:
                base_score -= 0.5
                details['moving_averages'] = f"Price below MA20 (-0.5)"
            elif price > ma20 and price > ma50:
                base_score += 1.0  # Don't SHORT uptrend
                details['moving_averages'] = f"Price above both MAs (+1.0)"
            else:
                details['moving_averages'] = "Mixed MA signals"
            
            # 4. Bollinger Bands
            bb_position = tech_data.get('bb_position', 'middle')
            bb_squeeze = tech_data.get('bb_squeeze', False)
            
            if bb_position == 'upper_rejection':
                base_score -= 1.0
                details['bollinger'] = "Upper band rejection (-1.0)"
            elif bb_position == 'upper' and not bb_squeeze:
                base_score -= 0.5
                details['bollinger'] = "Near upper band (-0.5)"
            elif bb_position == 'lower':
                base_score += 0.5  # Don't SHORT at lower band
                details['bollinger'] = "Near lower band (+0.5)"
            else:
                details['bollinger'] = f"BB position: {bb_position}"
            
            return max(0, min(10, base_score)), details
            
        except Exception as e:
            logger.error(f"Error calculating technical score: {e}")
            return base_score, {'error': str(e)}
    
    def _calculate_sentiment_score(self, crypto_data: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """Calculate sentiment analysis score (25% weight)"""
        symbol = crypto_data.get('symbol', '').replace('-USD', '')
        base_score = 5.0
        details = {}
        
        try:
            # 1. News Sentiment (simulated - would integrate with news APIs)
            news_sentiment = self._get_news_sentiment(symbol)
            
            if news_sentiment < -0.5:
                base_score -= 2.0
                details['news'] = f"Very negative news sentiment {news_sentiment:.2f} (-2.0)"
            elif news_sentiment < -0.2:
                base_score -= 1.0
                details['news'] = f"Negative news sentiment {news_sentiment:.2f} (-1.0)"
            elif news_sentiment > 0.3:
                base_score += 1.0  # Don't SHORT with positive news
                details['news'] = f"Positive news sentiment {news_sentiment:.2f} (+1.0)"
            else:
                details['news'] = f"Neutral news sentiment {news_sentiment:.2f}"
            
            # 2. Social Sentiment (simulated - would integrate with Twitter/Reddit APIs)
            social_sentiment = self._get_social_sentiment(symbol)
            social_trend = self._get_social_trend(symbol)
            
            if social_sentiment < -0.3 and social_trend == 'declining':
                base_score -= 1.0
                details['social'] = "Declining social sentiment (-1.0)"
            elif social_sentiment > 0.4:
                base_score += 0.5
                details['social'] = "Positive social sentiment (+0.5)"
            else:
                details['social'] = f"Social sentiment {social_sentiment:.2f}"
            
            # 3. Market Fear/Greed (using crypto fear & greed index concept)
            fear_greed = self._get_fear_greed_index()
            
            if fear_greed > 75:  # Extreme greed
                base_score -= 1.5
                details['fear_greed'] = f"Extreme greed {fear_greed} (-1.5)"
            elif fear_greed > 60:
                base_score -= 0.5
                details['fear_greed'] = f"Greed {fear_greed} (-0.5)"
            elif fear_greed < 25:  # Extreme fear - don't SHORT
                base_score += 1.0
                details['fear_greed'] = f"Extreme fear {fear_greed} (+1.0)"
            else:
                details['fear_greed'] = f"Fear/Greed index: {fear_greed}"
            
            return max(0, min(10, base_score)), details
            
        except Exception as e:
            logger.error(f"Error calculating sentiment score: {e}")
            return base_score, {'error': str(e)}
    
    def _calculate_momentum_score(self, crypto_data: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """Calculate volume/momentum score (15% weight)"""
        base_score = 5.0
        details = {}
        
        try:
            volume = crypto_data.get('volume', 0)
            change_percent = crypto_data.get('change_percent', 0)
            symbol = crypto_data.get('symbol', '')
            
            # Get volume analysis
            volume_data = self._get_volume_analysis(symbol)
            
            # 1. High Volume + Price Decline
            avg_volume = volume_data.get('avg_volume_20d', volume)
            volume_ratio = volume / avg_volume if avg_volume > 0 else 1
            
            if volume_ratio > 1.5 and change_percent < -3:
                base_score -= 1.5
                details['volume_decline'] = f"High volume selloff {volume_ratio:.1f}x avg (-1.5)"
            elif volume_ratio > 1.2 and change_percent < 0:
                base_score -= 0.5
                details['volume_decline'] = f"Above avg volume with decline (-0.5)"
            elif volume_ratio > 2.0 and change_percent > 5:
                base_score += 1.0  # Don't SHORT during volume spike up
                details['volume_decline'] = f"High volume pump (+1.0)"
            else:
                details['volume_decline'] = f"Volume ratio {volume_ratio:.1f}x"
            
            # 2. Buying Pressure Analysis
            buying_pressure = volume_data.get('buying_pressure', 0.5)  # 0-1 scale
            
            if buying_pressure < 0.3:
                base_score -= 1.0
                details['buying_pressure'] = f"Low buying pressure {buying_pressure:.2f} (-1.0)"
            elif buying_pressure > 0.7:
                base_score += 0.5
                details['buying_pressure'] = f"Strong buying pressure {buying_pressure:.2f} (+0.5)"
            else:
                details['buying_pressure'] = f"Buying pressure {buying_pressure:.2f}"
            
            # 3. Momentum Oscillators
            momentum_data = self._get_momentum_indicators(symbol)
            
            momentum_bearish_count = 0
            if momentum_data.get('stoch_oversold', False):
                momentum_bearish_count += 1
            if momentum_data.get('williams_r_oversold', False):
                momentum_bearish_count += 1
            if momentum_data.get('cci_bearish', False):
                momentum_bearish_count += 1
            
            if momentum_bearish_count >= 2:
                base_score -= 1.0
                details['momentum'] = f"Multiple bearish oscillators ({momentum_bearish_count}/3) (-1.0)"
            elif momentum_bearish_count == 1:
                base_score -= 0.5
                details['momentum'] = f"Some bearish signals ({momentum_bearish_count}/3) (-0.5)"
            else:
                details['momentum'] = "No strong momentum signals"
            
            return max(0, min(10, base_score)), details
            
        except Exception as e:
            logger.error(f"Error calculating momentum score: {e}")
            return base_score, {'error': str(e)}
    
    def _get_technical_data(self, symbol: str) -> Dict[str, Any]:
        """Get enhanced technical indicators"""
        # Check cache first
        cache_key = f"{symbol}_technical"
        if cache_key in self.technical_cache:
            cached_time, cached_data = self.technical_cache[cache_key]
            if datetime.now() - cached_time < self.cache_duration:
                return cached_data
        
        try:
            # Get historical data for technical analysis
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="60d", interval="1d")
            
            if hist.empty:
                return {}
            
            # Calculate technical indicators
            tech_data = {}
            
            # RSI calculation
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            tech_data['rsi'] = rsi.iloc[-1] if not rsi.empty else 50
            
            # RSI trend
            if len(rsi) >= 5:
                rsi_trend = 'up' if rsi.iloc[-1] > rsi.iloc[-5] else 'down'
                tech_data['rsi_trend'] = rsi_trend
            
            # Moving averages
            tech_data['ma20'] = hist['Close'].rolling(window=20).mean().iloc[-1]
            tech_data['ma50'] = hist['Close'].rolling(window=50).mean().iloc[-1]
            
            # MACD
            exp1 = hist['Close'].ewm(span=12).mean()
            exp2 = hist['Close'].ewm(span=26).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9).mean()
            histogram = macd - signal
            
            tech_data['macd_histogram'] = histogram.iloc[-1]
            
            # MACD signal
            if len(macd) >= 2 and len(signal) >= 2:
                if macd.iloc[-2] <= signal.iloc[-2] and macd.iloc[-1] > signal.iloc[-1]:
                    tech_data['macd_signal'] = 'bullish_crossover'
                elif macd.iloc[-2] >= signal.iloc[-2] and macd.iloc[-1] < signal.iloc[-1]:
                    tech_data['macd_signal'] = 'bearish_crossover'
                elif macd.iloc[-1] > signal.iloc[-1]:
                    tech_data['macd_signal'] = 'bullish'
                else:
                    tech_data['macd_signal'] = 'bearish'
            
            # Bollinger Bands
            sma20 = hist['Close'].rolling(window=20).mean()
            std20 = hist['Close'].rolling(window=20).std()
            upper_band = sma20 + (std20 * 2)
            lower_band = sma20 - (std20 * 2)
            
            current_price = hist['Close'].iloc[-1]
            if current_price >= upper_band.iloc[-1] * 0.98:
                tech_data['bb_position'] = 'upper_rejection' if current_price < hist['Close'].iloc[-2] else 'upper'
            elif current_price <= lower_band.iloc[-1] * 1.02:
                tech_data['bb_position'] = 'lower'
            else:
                tech_data['bb_position'] = 'middle'
            
            # Cache the result
            self.technical_cache[cache_key] = (datetime.now(), tech_data)
            
            return tech_data
            
        except Exception as e:
            logger.error(f"Error getting technical data for {symbol}: {e}")
            return {}
    
    def _get_news_sentiment(self, symbol: str) -> float:
        """Get news sentiment (simulated - would integrate with news APIs)"""
        # Simulate news sentiment based on symbol
        # In production, would integrate with News API, Alpha Vantage, etc.
        import random
        random.seed(hash(symbol) % 1000)  # Consistent random per symbol
        return random.uniform(-1.0, 1.0)
    
    def _get_social_sentiment(self, symbol: str) -> float:
        """Get social media sentiment (simulated)"""
        import random
        random.seed(hash(symbol + "social") % 1000)
        return random.uniform(-1.0, 1.0)
    
    def _get_social_trend(self, symbol: str) -> str:
        """Get social sentiment trend"""
        import random
        random.seed(hash(symbol + "trend") % 1000)
        return random.choice(['rising', 'declining', 'stable'])
    
    def _get_fear_greed_index(self) -> int:
        """Get crypto fear & greed index (simulated)"""
        # In production, would call actual Fear & Greed API
        import random
        return random.randint(0, 100)
    
    def _get_volume_analysis(self, symbol: str) -> Dict[str, Any]:
        """Get volume analysis"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="30d", interval="1d")
            
            if hist.empty:
                return {}
            
            # Calculate average volume
            avg_volume = hist['Volume'].rolling(window=20).mean().iloc[-1]
            
            # Simulate buying pressure (would use order book data in production)
            import random
            random.seed(hash(symbol + "volume") % 1000)
            buying_pressure = random.uniform(0.2, 0.8)
            
            return {
                'avg_volume_20d': avg_volume,
                'buying_pressure': buying_pressure
            }
            
        except Exception as e:
            logger.error(f"Error getting volume analysis for {symbol}: {e}")
            return {}
    
    def _get_momentum_indicators(self, symbol: str) -> Dict[str, Any]:
        """Get momentum oscillators"""
        # Simulated momentum indicators
        import random
        random.seed(hash(symbol + "momentum") % 1000)
        
        return {
            'stoch_oversold': random.random() < 0.3,
            'williams_r_oversold': random.random() < 0.3,
            'cci_bearish': random.random() < 0.4
        }
    
    def _calculate_confidence(self, technical: Dict, sentiment: Dict, momentum: Dict) -> float:
        """Calculate confidence level based on signal strength"""
        confidence = 0.5  # Base confidence
        
        # Higher confidence if multiple strong signals
        strong_signals = 0
        
        # Check for strong technical signals
        if 'rsi' in technical and 'down' in technical.get('rsi', ''):
            strong_signals += 1
        if 'macd' in technical and 'bearish_crossover' in technical.get('macd', ''):
            strong_signals += 1
        if 'moving_averages' in technical and 'below' in technical.get('moving_averages', ''):
            strong_signals += 1
        
        # Check for strong sentiment signals  
        if 'news' in sentiment and 'Very negative' in sentiment.get('news', ''):
            strong_signals += 1
        if 'social' in sentiment and 'Declining' in sentiment.get('social', ''):
            strong_signals += 1
        
        # Check for strong momentum signals
        if 'volume_decline' in momentum and 'High volume selloff' in momentum.get('volume_decline', ''):
            strong_signals += 1
        
        # Calculate confidence based on signal strength
        confidence = min(0.95, 0.5 + (strong_signals * 0.1))
        
        return confidence