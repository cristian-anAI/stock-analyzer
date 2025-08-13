"""
Scoring service for calculating stock and crypto scores
"""

import logging
from typing import Dict, Any, List
import numpy as np

logger = logging.getLogger(__name__)

class ScoringService:
    """Service for calculating calibrated scores for stocks and cryptos"""
    
    def __init__(self):
        self.recent_scores = {'stocks': [], 'cryptos': []}
        self.max_history = 100  # Keep last 100 scores for percentile calculation
    
    def calculate_stock_score(self, stock_data: Dict[str, Any]) -> float:
        """
        Calculate calibrated score for a stock (1-10 scale)
        REALISTIC SCORING: Score 10 = RARE (1-2% of time), Score 8-9 = Quality (5-10%)
        """
        try:
            score = 3  # Lower base score for more selective system
            
            # Get technical indicators
            change_percent = stock_data.get('change_percent', 0)
            rsi = stock_data.get('rsi', 50)
            volume = stock_data.get('volume', 0)
            market_cap = stock_data.get('market_cap', 0)
            
            # Price change factor with penalties for overextended moves
            if change_percent > 3:
                score -= 2  # Penalize recent rallies (FOMO prevention)
            elif change_percent > 1:
                score -= 0.5
            elif change_percent > -1:
                score += 1
            elif change_percent > -3:
                score += 1.5
            elif change_percent > -5:
                score += 2
            else:
                score += 2.5  # Reward oversold conditions
            
            # RSI penalties for overextended conditions
            if rsi > 75:
                score -= 1.5  # Overbought penalty
            elif rsi > 70:
                score -= 1
            elif rsi < 25:
                score += 2  # Oversold bonus
            elif rsi < 30:
                score += 1
            
            # Volume confirmation
            if volume > 10000000:
                score += 0.5
            elif volume < 100000:
                score -= 1  # Illiquid penalty
            
            # Market cap stability factor
            if market_cap > 100000000000:  # Large cap stability
                score += 0.5
            elif market_cap < 1000000000:  # Small cap volatility penalty
                score -= 0.5
            
            # Quality sector bonus (reduced)
            sector = stock_data.get('sector', '').lower()
            quality_sectors = ['technology', 'healthcare', 'consumer staples']
            if any(sector_name in sector for sector_name in quality_sectors):
                score += 0.5
            
            # Cap maximum score at 10 for stocks
            score = max(1, min(10, round(score * 2) / 2))  # Round to nearest 0.5
            
            # Store score for relative ranking
            self.recent_scores['stocks'].append(score)
            if len(self.recent_scores['stocks']) > self.max_history:
                self.recent_scores['stocks'].pop(0)
            
            return score
            
        except Exception as e:
            logger.error(f"Error calculating stock score: {str(e)}")
            return 3  # Lower default score
    
    def calculate_crypto_score(self, crypto_data: Dict[str, Any]) -> float:
        """
        Calculate calibrated score for a cryptocurrency (1-8 scale MAX)
        CRYPTO SCORING: Max 8.0 (too volatile for 10), Score 8-9 = Exceptional setups only
        """
        try:
            score = 2  # Much lower base score for crypto selectivity
            
            # Get technical indicators
            change_percent = crypto_data.get('change_percent', 0)
            rsi = crypto_data.get('rsi', 50)
            volume = crypto_data.get('volume', 0)
            market_cap = crypto_data.get('market_cap', 0)
            symbol = crypto_data.get('symbol', '').upper()
            
            # Extreme penalties for recent pumps (crypto FOMO prevention)
            if change_percent > 5:
                score -= 3  # Heavy penalty for recent pumps
            elif change_percent > 2:
                score -= 1.5
            elif change_percent > -2:
                score += 0.5
            elif change_percent > -10:
                score += 2
            elif change_percent > -20:
                score += 3
            else:
                score += 2  # Extreme oversold
            
            # RSI adjustments for crypto volatility
            if rsi > 70:
                score -= 2  # Heavy overbought penalty
            elif rsi > 60:
                score -= 1
            elif rsi < 30:
                score += 2.5  # Strong oversold bonus
            elif rsi < 40:
                score += 1
            
            # Volume requirements (crypto needs liquidity)
            if volume > 1000000000:  # >1B volume
                score += 1
            elif volume > 100000000:  # 100M-1B
                score += 0.5
            elif volume < 10000000:  # <10M penalty
                score -= 1.5
            
            # Market cap factor (stability preference)
            if market_cap > 100000000000:  # BTC/ETH level
                score += 1
            elif market_cap > 10000000000:  # Top 10 cryptos
                score += 0.5
            elif market_cap < 1000000000:  # Small cap penalty
                score -= 1
            
            # Quality crypto bonus (reduced and more selective)
            top_tier = ['BTC', 'ETH']  # Only the most established
            second_tier = ['SOL', 'ADA', 'BNB']  # Strong fundamentals
            
            if symbol in top_tier:
                score += 0.5
            elif symbol in second_tier:
                score += 0.25
            
            # HARD CAP at 8.0 for crypto (volatility adjustment)
            crypto_max_score = 8.0
            score = max(1, min(crypto_max_score, round(score * 2) / 2))
            
            # Store score for relative ranking
            self.recent_scores['cryptos'].append(score)
            if len(self.recent_scores['cryptos']) > self.max_history:
                self.recent_scores['cryptos'].pop(0)
            
            return score
            
        except Exception as e:
            logger.error(f"Error calculating crypto score: {str(e)}")
            return 2  # Lower default score for crypto
    
    def apply_relative_ranking(self, asset_scores: List[Dict[str, Any]], asset_type: str) -> List[Dict[str, Any]]:
        """
        Apply relative ranking to ensure only top performers get high scores
        Top 5% = Score 8-9, Top 10% = Score 7-8, Top 25% = Score 6-7
        """
        if not asset_scores:
            return asset_scores
        
        # Sort by raw score (descending)
        sorted_assets = sorted(asset_scores, key=lambda x: x['score'], reverse=True)
        total_assets = len(sorted_assets)
        
        for i, asset in enumerate(sorted_assets):
            percentile = (i / total_assets) * 100
            original_score = asset['score']
            
            # Apply percentile-based caps
            if percentile <= 2:  # Top 2% - exceptional
                max_score = 9 if asset_type == 'stocks' else 8
            elif percentile <= 5:  # Top 5% - very good
                max_score = 8 if asset_type == 'stocks' else 7
            elif percentile <= 10:  # Top 10% - good
                max_score = 7
            elif percentile <= 25:  # Top 25% - decent
                max_score = 6
            else:  # Bottom 75% - cap lower
                max_score = 5
            
            # Apply the cap
            asset['score'] = min(original_score, max_score)
            asset['percentile'] = round(100 - percentile, 1)  # Flip so higher is better
        
        return sorted_assets
    
    def get_market_distribution(self, asset_type: str) -> Dict[str, float]:
        """
        Get current market score distribution for calibration
        """
        scores = self.recent_scores.get(asset_type, [])
        if not scores:
            return {'mean': 5.0, 'std': 2.0, 'high_scores_pct': 0.0}
        
        scores_array = np.array(scores)
        high_scores_pct = (scores_array >= 8).sum() / len(scores_array) * 100
        
        return {
            'mean': float(np.mean(scores_array)),
            'std': float(np.std(scores_array)),
            'high_scores_pct': round(high_scores_pct, 1),
            'total_analyzed': len(scores)
        }
    
    def get_score_color(self, score: float) -> str:
        """Get color classification for score with updated thresholds"""
        if score >= 8:
            return "green"  # Exceptional - rare
        elif score >= 6:
            return "blue"   # Good opportunity
        elif score >= 4:
            return "yellow" # Neutral/speculative
        else:
            return "red"    # Avoid