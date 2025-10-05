"""
Improved Scoring Service - Scoring optimizado con momentum y trend strength
Reduce volatilidad del scoring para evitar overtrading
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ImprovedScoringService:
    """
    Servicio de scoring mejorado que captura tendencias sostenibles
    en vez de fluctuaciones de corto plazo
    """

    def __init__(self):
        self.recent_scores = {'stocks': [], 'cryptos': []}
        self.max_history = 100

    def calculate_stock_score_from_data(self, historical_data: pd.DataFrame) -> float:
        """
        Calculate score from historical OHLCV data
        Uses momentum, trend strength, and volume confirmation

        Args:
            historical_data: DataFrame with OHLCV data, indexed by date

        Returns:
            Score 1-10
        """
        try:
            if len(historical_data) < 30:
                return 3.0

            # Extract price and volume data
            close_prices = historical_data['Close']
            volumes = historical_data['Volume']

            # Base score
            score = 5.0

            # 1. MOMENTUM CONFIRMATION (Multi-period)
            # Must have consistent momentum across multiple timeframes

            if len(close_prices) >= 5:
                momentum_5d = (close_prices.iloc[-1] - close_prices.iloc[-5]) / close_prices.iloc[-5] * 100
            else:
                momentum_5d = 0

            if len(close_prices) >= 10:
                momentum_10d = (close_prices.iloc[-1] - close_prices.iloc[-10]) / close_prices.iloc[-10] * 100
            else:
                momentum_10d = 0

            if len(close_prices) >= 20:
                momentum_20d = (close_prices.iloc[-1] - close_prices.iloc[-20]) / close_prices.iloc[-20] * 100
            else:
                momentum_20d = 0

            # Score based on momentum consistency
            if momentum_5d > 2 and momentum_10d > 3 and momentum_20d > 5:
                score += 2.5  # Strong uptrend
            elif momentum_5d > 1 and momentum_10d > 2:
                score += 1.5  # Moderate uptrend
            elif momentum_5d > 0 and momentum_10d > 0:
                score += 0.5  # Weak uptrend
            elif momentum_5d < -2 and momentum_10d < -3:
                score -= 1.5  # Downtrend

            # 2. TREND STRENGTH (EMA crossovers)
            if len(close_prices) >= 50:
                ema_20 = close_prices.ewm(span=20, adjust=False).mean().iloc[-1]
                ema_50 = close_prices.ewm(span=50, adjust=False).mean().iloc[-1]
                current_price = close_prices.iloc[-1]

                # Strong uptrend: price > EMA20 > EMA50
                if current_price > ema_20 and ema_20 > ema_50:
                    score += 1.5
                    # Extra boost if price is well above EMAs
                    if current_price > ema_20 * 1.02:  # 2% above EMA20
                        score += 0.5
                # Weak uptrend: price > EMA20 but EMA20 < EMA50
                elif current_price > ema_20 and ema_20 < ema_50:
                    score += 0.5
                # Downtrend: price < EMA20 < EMA50
                elif current_price < ema_20 and ema_20 < ema_50:
                    score -= 1.0

            # 3. RSI (Overbought/Oversold)
            returns = close_prices.pct_change().dropna()
            if len(returns) >= 14:
                gains = returns[returns > 0].tail(14).sum()
                losses = abs(returns[returns < 0].tail(14).sum())
                rsi = 100 - (100 / (1 + (gains / (losses + 0.0001))))

                # Avoid overbought
                if rsi > 75:
                    score -= 1.0
                elif rsi > 70:
                    score -= 0.5
                # Reward oversold (contrarian)
                elif rsi < 30:
                    score += 1.0
                elif rsi < 40:
                    score += 0.5

            # 4. VOLUME CONFIRMATION
            if len(volumes) >= 20:
                avg_volume_20d = volumes.tail(20).mean()
                current_volume = volumes.iloc[-1]

                # Volume increasing = strength
                if current_volume > avg_volume_20d * 1.5:
                    score += 1.0
                elif current_volume > avg_volume_20d * 1.2:
                    score += 0.5
                # Volume decreasing = weakness
                elif current_volume < avg_volume_20d * 0.5:
                    score -= 0.5

            # 5. VOLATILITY PENALTY
            # High volatility = risky, lower score
            if len(returns) >= 20:
                volatility = returns.tail(20).std() * np.sqrt(252)

                if volatility > 0.50:  # >50% annual volatility
                    score -= 1.0
                elif volatility > 0.35:  # >35% annual volatility
                    score -= 0.5
                elif volatility < 0.15:  # <15% annual volatility (stable)
                    score += 0.5

            # 6. PRICE POSITION RELATIVE TO RANGE
            # Prefer stocks in middle of range, not at extremes
            if len(close_prices) >= 20:
                high_20d = close_prices.tail(20).max()
                low_20d = close_prices.tail(20).min()
                current_price = close_prices.iloc[-1]

                if high_20d > low_20d:
                    position = (current_price - low_20d) / (high_20d - low_20d)

                    # Avoid stocks at 52-week highs (likely to reverse)
                    if position > 0.95:
                        score -= 0.5
                    # Prefer stocks breaking out (60-80% of range)
                    elif 0.6 <= position <= 0.8:
                        score += 0.5

            # Cap score at 1-10
            score = max(1.0, min(10.0, score))

            # Round to 0.5 for stability
            score = round(score * 2) / 2

            return score

        except Exception as e:
            logger.error(f"Error calculating improved score: {e}")
            return 5.0

    def calculate_stock_score(self, stock_data: Dict[str, Any]) -> float:
        """
        Legacy interface for compatibility with existing code
        Note: This won't have access to historical data, so will be less accurate
        """
        try:
            score = 5.0

            change_percent = stock_data.get('change_percent', 0)
            rsi = stock_data.get('rsi', 50)
            volume = stock_data.get('volume', 0)
            market_cap = stock_data.get('market_cap', 0)

            # Simplified scoring without historical data
            # Prefer moderate positive changes
            if 0 < change_percent < 2:
                score += 1.0
            elif change_percent > 3:
                score -= 0.5  # Overbought
            elif change_percent < -2:
                score -= 1.0

            # RSI
            if 40 <= rsi <= 60:
                score += 0.5  # Neutral RSI is good
            elif rsi > 70:
                score -= 1.0
            elif rsi < 30:
                score += 0.5

            # Volume
            if volume > 10000000:
                score += 0.5

            # Market cap stability
            if market_cap > 100000000000:
                score += 0.5

            score = max(1.0, min(10.0, round(score * 2) / 2))

            return score

        except Exception as e:
            logger.error(f"Error in legacy scoring: {e}")
            return 5.0

    def calculate_crypto_score_from_data(self, historical_data: pd.DataFrame) -> float:
        """
        Calculate crypto score from historical data
        Similar to stock scoring but adjusted for crypto volatility
        """
        try:
            if len(historical_data) < 20:
                return 3.0

            close_prices = historical_data['Close']
            volumes = historical_data['Volume']

            score = 4.0  # Lower base for crypto

            # Momentum (shorter periods for crypto)
            if len(close_prices) >= 3:
                momentum_3d = (close_prices.iloc[-1] - close_prices.iloc[-3]) / close_prices.iloc[-3] * 100
            else:
                momentum_3d = 0

            if len(close_prices) >= 7:
                momentum_7d = (close_prices.iloc[-1] - close_prices.iloc[-7]) / close_prices.iloc[-7] * 100
            else:
                momentum_7d = 0

            # Crypto momentum scoring
            if momentum_3d > 5 and momentum_7d > 10:
                score += 2.0
            elif momentum_3d > 2 and momentum_7d > 5:
                score += 1.0
            elif momentum_3d < -5:
                score -= 1.0

            # Trend strength
            if len(close_prices) >= 20:
                ema_10 = close_prices.ewm(span=10, adjust=False).mean().iloc[-1]
                ema_20 = close_prices.ewm(span=20, adjust=False).mean().iloc[-1]
                current_price = close_prices.iloc[-1]

                if current_price > ema_10 and ema_10 > ema_20:
                    score += 1.0
                elif current_price < ema_10 and ema_10 < ema_20:
                    score -= 1.0

            # RSI
            returns = close_prices.pct_change().dropna()
            if len(returns) >= 14:
                gains = returns[returns > 0].tail(14).sum()
                losses = abs(returns[returns < 0].tail(14).sum())
                rsi = 100 - (100 / (1 + (gains / (losses + 0.0001))))

                if rsi > 70:
                    score -= 1.5
                elif rsi < 30:
                    score += 1.5

            # Volume confirmation
            if len(volumes) >= 10:
                avg_volume = volumes.tail(10).mean()
                current_volume = volumes.iloc[-1]

                if current_volume > avg_volume * 1.5:
                    score += 0.5

            score = max(1.0, min(8.0, score))  # Max 8 for crypto
            score = round(score * 2) / 2

            return score

        except Exception as e:
            logger.error(f"Error calculating crypto score: {e}")
            return 4.0

# Global instance
improved_scoring_service = ImprovedScoringService()
