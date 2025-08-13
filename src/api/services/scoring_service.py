"""
Scoring service for calculating stock and crypto scores
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ScoringService:
    """Service for calculating scores for stocks and cryptos"""
    
    def calculate_stock_score(self, stock_data: Dict[str, Any]) -> int:
        """
        Calculate score for a stock (1-10 scale)
        >8=green, 6-8=blue, 4-6=yellow, <4=red
        """
        try:
            score = 5  # Base score
            
            # Price change factor (40% weight)
            change_percent = stock_data.get('change_percent', 0)
            if change_percent > 5:
                score += 2
            elif change_percent > 2:
                score += 1
            elif change_percent > 0:
                score += 0.5
            elif change_percent > -2:
                score -= 0.5
            elif change_percent > -5:
                score -= 1
            else:
                score -= 2
            
            # Volume factor (20% weight)
            volume = stock_data.get('volume', 0)
            if volume > 10000000:  # High volume
                score += 1
            elif volume > 1000000:  # Medium volume
                score += 0.5
            elif volume < 100000:  # Low volume
                score -= 0.5
            
            # Market cap factor (20% weight)
            market_cap = stock_data.get('market_cap', 0)
            if market_cap > 100000000000:  # Large cap (>100B)
                score += 1
            elif market_cap > 10000000000:  # Mid cap (10B-100B)
                score += 0.5
            elif market_cap < 1000000000:  # Small cap (<1B)
                score -= 0.5
            
            # Sector bonus (20% weight)
            sector = stock_data.get('sector', '').lower()
            tech_sectors = ['technology', 'software', 'semiconductors', 'artificial intelligence']
            growth_sectors = ['healthcare', 'biotechnology', 'renewable energy']
            
            if any(tech in sector for tech in tech_sectors):
                score += 1
            elif any(growth in sector for growth in growth_sectors):
                score += 0.5
            
            # Clamp score to 1-10 range
            score = max(1, min(10, round(score)))
            
            return int(score)
            
        except Exception as e:
            logger.error(f"Error calculating stock score: {str(e)}")
            return 5  # Default score
    
    def calculate_crypto_score(self, crypto_data: Dict[str, Any]) -> int:
        """
        Calculate score for a cryptocurrency (1-10 scale)
        """
        try:
            score = 5  # Base score
            
            # Price change factor (50% weight - more volatile)
            change_percent = crypto_data.get('change_percent', 0)
            if change_percent > 10:
                score += 2.5
            elif change_percent > 5:
                score += 2
            elif change_percent > 2:
                score += 1
            elif change_percent > 0:
                score += 0.5
            elif change_percent > -5:
                score -= 0.5
            elif change_percent > -10:
                score -= 1.5
            else:
                score -= 2.5
            
            # Volume factor (25% weight)
            volume = crypto_data.get('volume', 0)
            if volume > 1000000000:  # High volume (>1B)
                score += 1.5
            elif volume > 100000000:  # Medium volume (100M-1B)
                score += 1
            elif volume > 10000000:  # Low-medium volume (10M-100M)
                score += 0.5
            elif volume < 1000000:  # Very low volume (<1M)
                score -= 1
            
            # Market cap factor (25% weight)
            market_cap = crypto_data.get('market_cap', 0)
            if market_cap > 100000000000:  # Major crypto (>100B)
                score += 1.5
            elif market_cap > 10000000000:  # Large crypto (10B-100B)
                score += 1
            elif market_cap > 1000000000:  # Medium crypto (1B-10B)
                score += 0.5
            elif market_cap < 100000000:  # Small crypto (<100M)
                score -= 1
            
            # Symbol bonus (top cryptos get bonus)
            symbol = crypto_data.get('symbol', '').upper()
            top_cryptos = ['BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'XRP']
            established_cryptos = ['DOT', 'AVAX', 'MATIC', 'LINK', 'UNI', 'ATOM']
            
            if symbol in top_cryptos:
                score += 1
            elif symbol in established_cryptos:
                score += 0.5
            
            # Clamp score to 1-10 range
            score = max(1, min(10, round(score)))
            
            return int(score)
            
        except Exception as e:
            logger.error(f"Error calculating crypto score: {str(e)}")
            return 5  # Default score
    
    def get_score_color(self, score: int) -> str:
        """Get color classification for score"""
        if score > 8:
            return "green"
        elif score >= 6:
            return "blue"
        elif score >= 4:
            return "yellow"
        else:
            return "red"