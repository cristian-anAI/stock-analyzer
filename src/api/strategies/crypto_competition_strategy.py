"""
CryptoCompetitionStrategy - Estrategia competitiva para crypto
Timeframe principal: 4H, entrada: 1H, holding: 1-10 días, Risk: 5%
Con filtro de volatilidad: NO entrar si volatilidad diaria > 15%
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from .base_strategy import BaseStrategy, TradingSignal

logger = logging.getLogger(__name__)

class CryptoCompetitionStrategy(BaseStrategy):
    """
    Estrategia competitiva para crypto trading
    
    Características:
    - Timeframe principal: 4H para momentum
    - Entrada: 1H para timing preciso  
    - Hold: 1-10 días (más agresivo que swing)
    - Volatility filter: NO entrar si volatilidad > 15%
    - Risk per trade: 5% (mayor que stocks)
    - Más agresivo: buy threshold 8.0, sell threshold 3.5
    """
    
    def __init__(self):
        super().__init__("CryptoCompetition")
        
        # Configuración específica para crypto competition
        self.timeframe_primary = "4h"
        self.timeframe_entry = "1h"
        self.timeframe_confirmation = None  # No confirmation needed - move fast
        
        # Thresholds más agresivos para crypto
        self.buy_threshold = 8.0  # Más alto, más selectivo
        self.sell_threshold = 3.5  # Más bajo, salir rápido
        self.strong_buy_threshold = 9.0
        self.strong_sell_threshold = 2.5
        
        # Crypto competition parameters
        self.min_hold_days = 1  # Muy agresivo
        self.max_hold_days = 10
        self.stop_loss_percent = 12.0  # Más amplio por volatilidad
        self.take_profit_percent = 25.0  # Mayor objetivo
        self.risk_per_trade_percent = 5.0  # Más agresivo
        
        # Position sizing  
        self.max_position_size_percent = 20.0  # Más concentrado
        
        # Volatility limits
        self.volatility_limit = 0.15  # 15% daily max
        self.emergency_exit_volatility = 0.25  # 25% emergency exit
        
        logger.info("Initialized Crypto Competition Strategy")
    
    def calculate_score(self, symbol: str, data: Dict[str, pd.DataFrame]) -> float:
        """
        Calcula score de momentum crypto basado en timeframes 4H y 1H
        
        Score components:
        - 4H RSI momentum (25%): <25 strong buy, >75 strong sell
        - 4H EMA crossover (25%): 8H vs 21H with volume
        - 4H Bollinger squeeze/breakout (20%): Volatility expansion
        - 1H entry timing (15%): Short-term momentum
        - Support/Resistance (10%): Key levels
        - Volume momentum (5%): Increasing volume trends
        """
        try:
            h4_data = data.get("4h")
            h1_data = data.get("1h")
            
            if h4_data is None or h4_data.empty:
                logger.warning(f"No 4H data for {symbol}")
                return 5.0
            
            score = 5.0  # Neutral base
            factors = []
            
            # Get latest values
            latest_4h = h4_data.iloc[-1]
            latest_price = latest_4h['Close']
            
            # 1. 4H RSI Momentum Analysis (25% weight)
            h4_rsi = latest_4h.get('RSI')
            if h4_rsi is not None:
                rsi_score = self._calculate_crypto_rsi_score(h4_rsi)
                score += rsi_score * 0.25
                factors.append(f"4H RSI: {h4_rsi:.1f} -> {rsi_score:+.1f}")
            
            # 2. 4H EMA Crossover with Volume (25% weight)
            ema_8 = latest_4h.get('EMA_8')
            ema_21 = latest_4h.get('EMA_21')
            volume = latest_4h.get('Volume', 0)
            volume_ma = latest_4h.get('Volume_MA', 1)
            
            if ema_8 is not None and ema_21 is not None:
                ema_score = self._calculate_ema_crossover_score(h4_data, ema_8, ema_21, volume, volume_ma)
                score += ema_score * 0.25
                factors.append(f"4H EMA Cross: {ema_score:+.1f}")
            
            # 3. 4H Bollinger Squeeze/Breakout (20% weight)
            bb_upper = latest_4h.get('BB_Upper')
            bb_lower = latest_4h.get('BB_Lower')
            bb_position = latest_4h.get('BB_Position')
            
            if all(x is not None for x in [bb_upper, bb_lower, bb_position]):
                bb_score = self._calculate_bollinger_breakout_score(h4_data, latest_price, bb_upper, bb_lower, bb_position)
                score += bb_score * 0.20
                factors.append(f"4H BB: {bb_score:+.1f}")
            
            # 4. 1H Entry Timing (15% weight)
            if h1_data is not None and not h1_data.empty:
                timing_score = self._calculate_1h_timing_score(h1_data)
                score += timing_score * 0.15
                factors.append(f"1H Timing: {timing_score:+.1f}")
            
            # 5. Support/Resistance Levels (10% weight)
            support_resistance_score = self._calculate_support_resistance_score(h4_data, latest_price)
            score += support_resistance_score * 0.10
            factors.append(f"S/R: {support_resistance_score:+.1f}")
            
            # 6. Volume Momentum (5% weight)
            volume_momentum_score = self._calculate_volume_momentum_score(h4_data)
            score += volume_momentum_score * 0.05
            factors.append(f"Vol Mom: {volume_momentum_score:+.1f}")
            
            # Cap score between 0-10
            final_score = max(0, min(10, score))
            
            logger.debug(f"Crypto score for {symbol}: {final_score:.2f} | {' | '.join(factors)}")
            return final_score
            
        except Exception as e:
            logger.error(f"Error calculating crypto score for {symbol}: {e}")
            return 5.0
    
    def _calculate_crypto_rsi_score(self, rsi: float) -> float:
        """Calculate RSI score optimized for crypto momentum"""
        if rsi <= 20:
            return 3.0  # Extremely oversold - strong buy
        elif rsi <= 30:
            return 2.0  # Oversold
        elif rsi <= 40:
            return 1.0  # Slightly oversold
        elif rsi <= 60:
            return 0.0  # Neutral zone
        elif rsi <= 70:
            return -1.0  # Slightly overbought
        elif rsi <= 80:
            return -2.0  # Overbought
        else:
            return -3.0  # Extremely overbought - strong sell
    
    def _calculate_ema_crossover_score(self, data: pd.DataFrame, ema_8: float, ema_21: float, volume: float, volume_ma: float) -> float:
        """Calculate EMA crossover score with volume confirmation"""
        score = 0.0
        
        # Current EMA position
        if ema_8 > ema_21:
            score += 1.5  # Bullish alignment
        else:
            score -= 1.5  # Bearish alignment
        
        # Check for recent crossover
        if len(data) >= 3:
            recent_data = data.tail(3)
            ema_8_series = recent_data['EMA_8']
            ema_21_series = recent_data['EMA_21']
            
            # Look for crossover in last 2 periods
            for i in range(1, len(ema_8_series)):
                prev_8, curr_8 = ema_8_series.iloc[i-1], ema_8_series.iloc[i]
                prev_21, curr_21 = ema_21_series.iloc[i-1], ema_21_series.iloc[i]
                
                # Bullish crossover
                if prev_8 <= prev_21 and curr_8 > curr_21:
                    score += 1.5
                # Bearish crossover
                elif prev_8 >= prev_21 and curr_8 < curr_21:
                    score -= 1.5
        
        # Volume confirmation
        volume_ratio = volume / volume_ma if volume_ma > 0 else 1
        if volume_ratio > 1.5:
            score += 0.5  # Strong volume confirms signal
        elif volume_ratio < 0.7:
            score -= 0.3  # Weak volume reduces confidence
        
        return score
    
    def _calculate_bollinger_breakout_score(self, data: pd.DataFrame, price: float, bb_upper: float, bb_lower: float, bb_position: float) -> float:
        """Calculate Bollinger Bands breakout/squeeze score"""
        score = 0.0
        
        # BB position analysis
        if bb_position > 0.8:  # Near upper band
            score -= 1.0  # Overbought
        elif bb_position < 0.2:  # Near lower band  
            score += 1.0  # Oversold
        elif 0.4 <= bb_position <= 0.6:  # Middle zone
            score += 0.5  # Good for breakout setup
        
        # Check for squeeze (narrow bands)
        if len(data) >= 20:
            recent_data = data.tail(20)
            bb_width = (recent_data['BB_Upper'] - recent_data['BB_Lower']) / recent_data['BB_Middle']
            current_width = (bb_upper - bb_lower) / ((bb_upper + bb_lower) / 2)
            avg_width = bb_width.mean()
            
            if current_width < avg_width * 0.7:
                score += 1.0  # Squeeze setup - breakout potential
        
        # Breakout detection
        if len(data) >= 2:
            prev_price = data.iloc[-2]['Close']
            prev_bb_upper = data.iloc[-2].get('BB_Upper', bb_upper)
            prev_bb_lower = data.iloc[-2].get('BB_Lower', bb_lower)
            
            # Bullish breakout
            if prev_price <= prev_bb_upper and price > bb_upper:
                score += 2.0
            # Bearish breakdown
            elif prev_price >= prev_bb_lower and price < bb_lower:
                score -= 2.0
        
        return score
    
    def _calculate_1h_timing_score(self, h1_data: pd.DataFrame) -> float:
        """Calculate 1H timing score for entry precision"""
        if len(h1_data) < 5:
            return 0.0
        
        latest_1h = h1_data.iloc[-1]
        score = 0.0
        
        # 1H RSI for timing
        h1_rsi = latest_1h.get('RSI')
        if h1_rsi is not None:
            if h1_rsi < 35:
                score += 1.0  # Good timing for buy
            elif h1_rsi > 65:
                score -= 1.0  # Poor timing for buy
        
        # 1H MACD momentum  
        macd = latest_1h.get('MACD')
        macd_signal = latest_1h.get('MACD_Signal')
        macd_hist = latest_1h.get('MACD_Histogram')
        
        if all(x is not None for x in [macd, macd_signal, macd_hist]):
            if macd > macd_signal and macd_hist > 0:
                score += 0.8  # Bullish momentum
            elif macd < macd_signal and macd_hist < 0:
                score -= 0.8  # Bearish momentum
        
        # Recent price momentum (last 3 hours)
        recent_closes = h1_data.tail(3)['Close']
        if len(recent_closes) >= 3:
            price_momentum = (recent_closes.iloc[-1] - recent_closes.iloc[0]) / recent_closes.iloc[0]
            if price_momentum > 0.02:  # 2% up in 3H
                score += 0.5
            elif price_momentum < -0.02:  # 2% down in 3H
                score -= 0.5
        
        return score
    
    def _calculate_support_resistance_score(self, data: pd.DataFrame, current_price: float) -> float:
        """Calculate support/resistance score"""
        if len(data) < 20:
            return 0.0
        
        recent_data = data.tail(50)  # Last 50 periods for S/R
        highs = recent_data['High']
        lows = recent_data['Low']
        
        score = 0.0
        
        # Find recent significant levels
        resistance_levels = []
        support_levels = []
        
        # Simple pivot detection
        for i in range(2, len(recent_data) - 2):
            high = highs.iloc[i]
            low = lows.iloc[i]
            
            # Pivot high (resistance)
            if (high > highs.iloc[i-1] and high > highs.iloc[i-2] and 
                high > highs.iloc[i+1] and high > highs.iloc[i+2]):
                resistance_levels.append(high)
            
            # Pivot low (support)
            if (low < lows.iloc[i-1] and low < lows.iloc[i-2] and 
                low < lows.iloc[i+1] and low < lows.iloc[i+2]):
                support_levels.append(low)
        
        # Check proximity to levels
        price_tolerance = current_price * 0.02  # 2% tolerance
        
        # Near support (bullish)
        for support in support_levels:
            if abs(current_price - support) <= price_tolerance and current_price >= support:
                score += 1.0
                break
        
        # Near resistance (bearish)
        for resistance in resistance_levels:
            if abs(current_price - resistance) <= price_tolerance and current_price <= resistance:
                score -= 1.0
                break
        
        return score
    
    def _calculate_volume_momentum_score(self, data: pd.DataFrame) -> float:
        """Calculate volume momentum score"""
        if len(data) < 10:
            return 0.0
        
        recent_volume = data.tail(5)['Volume']
        older_volume = data.tail(10).head(5)['Volume']
        
        if len(recent_volume) >= 5 and len(older_volume) >= 5:
            recent_avg = recent_volume.mean()
            older_avg = older_volume.mean()
            
            if recent_avg > older_avg * 1.3:
                return 1.0  # Increasing volume momentum
            elif recent_avg < older_avg * 0.7:
                return -0.5  # Decreasing volume
        
        return 0.0
    
    def generate_signal(self, symbol: str, current_price: float, data: Dict[str, pd.DataFrame]) -> TradingSignal:
        """Generate crypto competition trading signal"""
        try:
            # First check volatility filter
            if not self._passes_volatility_filter(symbol, data):
                return TradingSignal(
                    action="HOLD",
                    confidence=0.0,
                    symbol=symbol,
                    timeframe=self.timeframe_primary,
                    reasons=["Volatility too high - filter blocked entry"],
                    score=5.0,
                    risk_level="HIGH"
                )
            
            # Calculate score
            score = self.calculate_score(symbol, data)
            
            # Determine action (more aggressive thresholds)
            if score >= self.strong_buy_threshold:
                action = "BUY"
                confidence = min(9.8, score)
                risk_level = "HIGH"
            elif score >= self.buy_threshold:
                action = "BUY" 
                confidence = score
                risk_level = "MEDIUM"
            elif score <= self.strong_sell_threshold:
                action = "SELL"
                confidence = min(9.8, 10 - score)
                risk_level = "HIGH"
            elif score <= self.sell_threshold:
                action = "SELL"
                confidence = 10 - score
                risk_level = "MEDIUM"
            else:
                action = "HOLD"
                confidence = 5.0
                risk_level = "LOW"
            
            # Generate reasons
            reasons = self._generate_crypto_reasons(symbol, score, data)
            
            # Calculate position sizing and levels
            suggested_size = 0.0
            stop_loss = None
            take_profit = None
            
            if action == "BUY":
                suggested_size = current_price * 0.05  # Base 5% calculation
                stop_loss = current_price * (1 - self.stop_loss_percent / 100)
                take_profit = current_price * (1 + self.take_profit_percent / 100)
            
            signal = TradingSignal(
                action=action,
                confidence=confidence,
                symbol=symbol,
                timeframe=self.timeframe_primary,
                reasons=reasons,
                score=score,
                risk_level=risk_level,
                suggested_position_size=suggested_size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                max_hold_days=self.max_hold_days
            )
            
            logger.info(f"Crypto signal for {symbol}: {action} (score: {score:.2f}, confidence: {confidence:.1f})")
            return signal
            
        except Exception as e:
            logger.error(f"Error generating crypto signal for {symbol}: {e}")
            return TradingSignal(
                action="HOLD",
                confidence=0.0,
                symbol=symbol,
                timeframe=self.timeframe_primary,
                reasons=[f"Error in analysis: {str(e)}"],
                score=5.0
            )
    
    def _passes_volatility_filter(self, symbol: str, data: Dict[str, pd.DataFrame]) -> bool:
        """Check if symbol passes volatility filter"""
        try:
            h4_data = data.get("4h")
            if h4_data is None or len(h4_data) < 7:
                return True  # If no data, allow trade
            
            # Calculate recent volatility
            recent_closes = h4_data.tail(28)['Close']  # Last week of 4H data
            if len(recent_closes) >= 7:
                daily_returns = recent_closes.pct_change().dropna()
                daily_volatility = daily_returns.std() * np.sqrt(6)  # 6 periods per day for 4H
                
                if daily_volatility > self.volatility_limit:
                    logger.info(f"Volatility filter blocked {symbol}: {daily_volatility:.1%} > {self.volatility_limit:.1%}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in volatility filter for {symbol}: {e}")
            return True  # Allow trade if filter fails
    
    def _generate_crypto_reasons(self, symbol: str, score: float, data: Dict[str, pd.DataFrame]) -> List[str]:
        """Generate detailed reasons for crypto signals"""
        reasons = []
        
        h4_data = data.get("4h")
        if h4_data is None or h4_data.empty:
            return ["No 4H data available"]
        
        latest_4h = h4_data.iloc[-1]
        
        # RSI reason
        rsi = latest_4h.get('RSI')
        if rsi is not None:
            if rsi < 25:
                reasons.append(f"4H RSI extremely oversold at {rsi:.1f}")
            elif rsi > 75:
                reasons.append(f"4H RSI extremely overbought at {rsi:.1f}")
        
        # EMA crossover reason
        ema_8 = latest_4h.get('EMA_8')
        ema_21 = latest_4h.get('EMA_21')
        if ema_8 is not None and ema_21 is not None:
            if ema_8 > ema_21:
                reasons.append("4H EMA bullish alignment")
            else:
                reasons.append("4H EMA bearish alignment")
        
        # Volume reason
        volume_ratio = latest_4h.get('Volume_Ratio', 1.0)
        if volume_ratio > 1.5:
            reasons.append(f"Strong 4H volume ({volume_ratio:.1f}x)")
        
        # Bollinger position
        bb_position = latest_4h.get('BB_Position')
        if bb_position is not None:
            if bb_position > 0.8:
                reasons.append("Near 4H Bollinger upper band")
            elif bb_position < 0.2:
                reasons.append("Near 4H Bollinger lower band")
        
        # Score context
        if score >= 8.5:
            reasons.append("Strong bullish momentum setup")
        elif score <= 2.5:
            reasons.append("Strong bearish breakdown")
        elif 4.0 <= score <= 6.0:
            reasons.append("Consolidation/neutral pattern")
        
        return reasons[:5]  # Limit to top 5 reasons
    
    def should_exit_position(
        self, 
        symbol: str, 
        entry_price: float, 
        current_price: float,
        days_held: int,
        position_side: str = "LONG",
        data: Dict[str, pd.DataFrame] = None
    ) -> tuple[bool, str]:
        """Override exit logic for crypto competition strategy"""
        
        # Emergency volatility exit
        if data is not None:
            try:
                h4_data = data.get("4h")
                if h4_data is not None and len(h4_data) >= 7:
                    recent_closes = h4_data.tail(14)['Close']
                    daily_returns = recent_closes.pct_change().dropna()
                    current_volatility = daily_returns.std() * np.sqrt(6)
                    
                    if current_volatility > self.emergency_exit_volatility:
                        return True, f"Emergency exit: volatility {current_volatility:.1%} > {self.emergency_exit_volatility:.1%}"
            except Exception as e:
                logger.error(f"Error checking volatility exit for {symbol}: {e}")
        
        # Call base class logic
        should_exit, reason = super().should_exit_position(
            symbol, entry_price, current_price, days_held, position_side, data
        )
        
        if should_exit:
            return should_exit, reason
        
        # Crypto-specific quick exit logic
        try:
            if data is not None:
                h4_data = data.get("4h")
                if h4_data is not None and not h4_data.empty:
                    latest_4h = h4_data.iloc[-1]
                    
                    # Quick profit taking for crypto
                    profit_percent = abs((current_price - entry_price) / entry_price) * 100
                    
                    if position_side == "LONG":
                        # Take profits faster in crypto
                        if profit_percent > 15 and days_held >= 1:
                            h4_rsi = latest_4h.get('RSI')
                            if h4_rsi is not None and h4_rsi > 70:
                                return True, f"Quick profit: +{profit_percent:.1f}% with RSI {h4_rsi:.1f}"
                    
                    # Momentum reversal exit
                    ema_8 = latest_4h.get('EMA_8')
                    ema_21 = latest_4h.get('EMA_21')
                    
                    if position_side == "LONG" and ema_8 is not None and ema_21 is not None:
                        if ema_8 < ema_21 and days_held >= 1:
                            return True, f"Momentum reversal: 4H EMA bearish after {days_held} days"
            
            return False, "Continue crypto position"
            
        except Exception as e:
            logger.error(f"Error in crypto exit logic for {symbol}: {e}")
            return False, "Error in exit analysis"