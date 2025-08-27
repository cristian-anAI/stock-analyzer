"""
SwingTradingStrategy - Estrategia de swing trading para stocks
Timeframe principal: Daily (1d), confirmación: 4H, entrada: 1H
Holding period: 3-20 días, Risk per trade: 2%
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from .base_strategy import BaseStrategy, TradingSignal

logger = logging.getLogger(__name__)

class SwingTradingStrategy(BaseStrategy):
    """
    Estrategia de Swing Trading optimizada para stocks
    
    Características:
    - Timeframe principal: 1D para identificar tendencia
    - Confirmación: 4H para validar señales
    - Entrada: 1H para timing preciso
    - Hold: 3-20 días
    - Conservadora: buy threshold 7.5, sell threshold 4.0
    """
    
    def __init__(self):
        super().__init__("SwingTrading")
        
        # Configuración específica para swing trading
        self.timeframe_primary = "1d"
        self.timeframe_confirmation = "4h" 
        self.timeframe_entry = "1h"
        
        # Thresholds más conservadores para swing trading
        self.buy_threshold = 7.5  # Más conservador que trading diario
        self.sell_threshold = 4.0
        self.strong_buy_threshold = 8.5
        self.strong_sell_threshold = 3.0
        
        # Swing trading parameters
        self.min_hold_days = 3
        self.max_hold_days = 20
        self.stop_loss_percent = 8.0
        self.take_profit_percent = 15.0
        self.risk_per_trade_percent = 2.0
        
        # Position sizing
        self.max_position_size_percent = 12.0  # Más conservador
        
        logger.info("Initialized Swing Trading Strategy for stocks")
    
    def calculate_score(self, symbol: str, data: Dict[str, pd.DataFrame]) -> float:
        """
        Calcula score de swing trading basado en análisis de múltiples timeframes
        
        Score components:
        - Daily RSI (30%): Sweet spot 20-30 para compra, 70-80 para venta
        - Daily MACD (25%): Crossover con volumen
        - Daily MA position (20%): Precio vs MA20, MA50
        - Volume confirmation (15%): >1.5x promedio
        - 4H confirmation (10%): Validación de señal
        """
        try:
            daily_data = data.get("1d")
            h4_data = data.get("4h")
            
            if daily_data is None or daily_data.empty:
                logger.warning(f"No daily data for {symbol}")
                return 5.0
            
            score = 5.0  # Neutral base
            factors = []
            
            # Get latest values
            latest_daily = daily_data.iloc[-1]
            latest_price = latest_daily['Close']
            
            # 1. RSI Analysis (30% weight) - Daily timeframe
            daily_rsi = latest_daily.get('RSI')
            if daily_rsi is not None:
                rsi_score = self._calculate_rsi_score(daily_rsi)
                score += rsi_score * 0.30
                factors.append(f"Daily RSI: {daily_rsi:.1f} -> {rsi_score:+.1f}")
            
            # 2. MACD Analysis (25% weight) - Daily timeframe
            macd = latest_daily.get('MACD')
            macd_signal = latest_daily.get('MACD_Signal')
            macd_hist = latest_daily.get('MACD_Histogram')
            
            if all(x is not None for x in [macd, macd_signal, macd_hist]):
                macd_score = self._calculate_macd_score(daily_data, macd, macd_signal, macd_hist)
                score += macd_score * 0.25
                factors.append(f"Daily MACD: {macd_score:+.1f}")
            
            # 3. Moving Average Position (20% weight) - Daily
            ma_20 = latest_daily.get('MA_20')
            ma_50 = latest_daily.get('MA_50')
            
            if ma_20 is not None and ma_50 is not None:
                ma_score = self._calculate_ma_score(latest_price, ma_20, ma_50)
                score += ma_score * 0.20
                factors.append(f"MA Position: {ma_score:+.1f}")
            
            # 4. Volume Confirmation (15% weight) - Daily
            volume = latest_daily.get('Volume', 0)
            volume_ma = latest_daily.get('Volume_MA')
            
            if volume_ma is not None and volume_ma > 0:
                volume_score = self._calculate_volume_score(volume, volume_ma)
                score += volume_score * 0.15
                factors.append(f"Volume: {volume_score:+.1f}")
            
            # 5. 4H Confirmation (10% weight)
            if h4_data is not None and not h4_data.empty:
                h4_score = self._calculate_4h_confirmation(h4_data)
                score += h4_score * 0.10
                factors.append(f"4H Confirm: {h4_score:+.1f}")
            
            # Cap score between 0-10
            final_score = max(0, min(10, score))
            
            logger.debug(f"Swing score for {symbol}: {final_score:.2f} | {' | '.join(factors)}")
            return final_score
            
        except Exception as e:
            logger.error(f"Error calculating swing score for {symbol}: {e}")
            return 5.0
    
    def _calculate_rsi_score(self, rsi: float) -> float:
        """Calculate RSI score for swing trading"""
        if rsi <= 25:
            return 2.5  # Strong oversold - good for swing entry
        elif rsi <= 35:
            return 1.5  # Oversold
        elif rsi <= 45:
            return 0.5  # Slightly oversold
        elif rsi <= 55:
            return 0.0  # Neutral
        elif rsi <= 65:
            return -0.5  # Slightly overbought
        elif rsi <= 75:
            return -1.5  # Overbought
        else:
            return -2.5  # Strong overbought - good for swing exit
    
    def _calculate_macd_score(self, data: pd.DataFrame, macd: float, macd_signal: float, macd_hist: float) -> float:
        """Calculate MACD score with trend analysis"""
        score = 0.0
        
        # MACD crossover
        if macd > macd_signal and macd_hist > 0:
            score += 1.0  # Bullish
        elif macd < macd_signal and macd_hist < 0:
            score -= 1.0  # Bearish
        
        # MACD histogram momentum
        if len(data) >= 2:
            prev_hist = data.iloc[-2].get('MACD_Histogram', 0)
            if macd_hist > prev_hist and macd_hist > 0:
                score += 0.5  # Strengthening bullish momentum
            elif macd_hist < prev_hist and macd_hist < 0:
                score -= 0.5  # Strengthening bearish momentum
        
        # MACD zero line
        if macd > 0:
            score += 0.3  # Above zero line
        else:
            score -= 0.3  # Below zero line
        
        return score
    
    def _calculate_ma_score(self, price: float, ma_20: float, ma_50: float) -> float:
        """Calculate moving average position score"""
        score = 0.0
        
        # Price vs MA20
        ma20_diff_percent = ((price - ma_20) / ma_20) * 100
        
        if -3 <= ma20_diff_percent <= 2:
            score += 1.0  # Sweet spot for swing entry
        elif ma20_diff_percent > 2:
            score += 0.5 if ma20_diff_percent < 5 else -0.5  # Slightly extended
        elif ma20_diff_percent < -3:
            score += 0.5 if ma20_diff_percent > -6 else -0.5  # Oversold but not too much
        
        # MA20 vs MA50 trend
        if ma_20 > ma_50:
            score += 0.5  # Uptrend
        else:
            score -= 0.5  # Downtrend
        
        return score
    
    def _calculate_volume_score(self, volume: float, volume_ma: float) -> float:
        """Calculate volume confirmation score"""
        volume_ratio = volume / volume_ma
        
        if volume_ratio >= 1.5:
            return 1.0  # Strong volume confirmation
        elif volume_ratio >= 1.2:
            return 0.5  # Good volume
        elif volume_ratio >= 0.8:
            return 0.0  # Normal volume
        else:
            return -0.5  # Low volume - weak signal
    
    def _calculate_4h_confirmation(self, h4_data: pd.DataFrame) -> float:
        """Calculate 4H timeframe confirmation"""
        if len(h4_data) < 2:
            return 0.0
        
        latest_4h = h4_data.iloc[-1]
        score = 0.0
        
        # 4H RSI confirmation
        h4_rsi = latest_4h.get('RSI')
        if h4_rsi is not None:
            if h4_rsi < 40:
                score += 0.3  # 4H oversold supports daily signal
            elif h4_rsi > 60:
                score -= 0.3  # 4H overbought
        
        # 4H MACD alignment
        h4_macd = latest_4h.get('MACD')
        h4_macd_signal = latest_4h.get('MACD_Signal')
        
        if h4_macd is not None and h4_macd_signal is not None:
            if h4_macd > h4_macd_signal:
                score += 0.2  # 4H bullish alignment
            else:
                score -= 0.2  # 4H bearish alignment
        
        return score
    
    def generate_signal(self, symbol: str, current_price: float, data: Dict[str, pd.DataFrame]) -> TradingSignal:
        """Generate swing trading signal"""
        try:
            # Calculate score
            score = self.calculate_score(symbol, data)
            
            # Determine action
            if score >= self.strong_buy_threshold:
                action = "BUY"
                confidence = min(9.5, score)
                risk_level = "MEDIUM"
            elif score >= self.buy_threshold:
                action = "BUY"
                confidence = score
                risk_level = "MEDIUM"
            elif score <= self.strong_sell_threshold:
                action = "SELL"
                confidence = min(9.5, 10 - score)
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
            reasons = self._generate_reasons(symbol, score, data)
            
            # Calculate suggested position size and levels
            suggested_size = 0.0
            stop_loss = None
            take_profit = None
            
            if action == "BUY":
                # Position sizing for swing trades
                suggested_size = current_price * 0.02  # Base 2% of current price for calculation
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
            
            logger.info(f"Swing signal for {symbol}: {action} (score: {score:.2f}, confidence: {confidence:.1f})")
            return signal
            
        except Exception as e:
            logger.error(f"Error generating swing signal for {symbol}: {e}")
            return TradingSignal(
                action="HOLD",
                confidence=0.0,
                symbol=symbol,
                timeframe=self.timeframe_primary,
                reasons=[f"Error in analysis: {str(e)}"],
                score=5.0
            )
    
    def _generate_reasons(self, symbol: str, score: float, data: Dict[str, pd.DataFrame]) -> List[str]:
        """Generate detailed reasons for the signal"""
        reasons = []
        
        daily_data = data.get("1d")
        if daily_data is None or daily_data.empty:
            return ["No daily data available"]
        
        latest = daily_data.iloc[-1]
        
        # RSI reason
        rsi = latest.get('RSI')
        if rsi is not None:
            if rsi < 30:
                reasons.append(f"Daily RSI oversold at {rsi:.1f}")
            elif rsi > 70:
                reasons.append(f"Daily RSI overbought at {rsi:.1f}")
        
        # MACD reason
        macd = latest.get('MACD')
        macd_signal = latest.get('MACD_Signal')
        if macd is not None and macd_signal is not None:
            if macd > macd_signal:
                reasons.append("Daily MACD bullish crossover")
            else:
                reasons.append("Daily MACD bearish crossover")
        
        # Volume reason
        volume_ratio = latest.get('Volume_Ratio', 1.0)
        if volume_ratio > 1.5:
            reasons.append(f"Strong volume confirmation ({volume_ratio:.1f}x)")
        elif volume_ratio < 0.8:
            reasons.append(f"Weak volume ({volume_ratio:.1f}x)")
        
        # Add score context
        if score >= 8.0:
            reasons.append("Strong bullish setup")
        elif score <= 3.0:
            reasons.append("Strong bearish setup")
        elif 4.5 <= score <= 5.5:
            reasons.append("Neutral/consolidation pattern")
        
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
        """Override exit logic for swing trading"""
        
        # Call base class logic first
        should_exit, reason = super().should_exit_position(
            symbol, entry_price, current_price, days_held, position_side, data
        )
        
        if should_exit:
            return should_exit, reason
        
        # Swing trading specific exit logic
        try:
            if data is not None:
                daily_data = data.get("1d")
                if daily_data is not None and not daily_data.empty:
                    latest = daily_data.iloc[-1]
                    
                    # Check for swing reversal signals
                    rsi = latest.get('RSI')
                    if position_side == "LONG" and rsi is not None:
                        if rsi > 75 and days_held >= self.min_hold_days:
                            return True, f"Swing exit: RSI overbought {rsi:.1f} after {days_held} days"
                    
                    # MACD divergence exit
                    macd = latest.get('MACD')
                    macd_signal = latest.get('MACD_Signal')
                    
                    if position_side == "LONG" and macd is not None and macd_signal is not None:
                        if macd < macd_signal and days_held >= self.min_hold_days:
                            return True, f"Swing exit: MACD bearish crossover after {days_held} days"
            
            # Hold if minimum days not reached (unless stop loss/take profit)
            if days_held < self.min_hold_days:
                profit_percent = abs((current_price - entry_price) / entry_price) * 100
                if profit_percent < self.take_profit_percent * 0.8:  # 80% of take profit
                    return False, f"Hold: Only {days_held} days (min {self.min_hold_days})"
            
            return False, "Continue swing trade"
            
        except Exception as e:
            logger.error(f"Error in swing exit logic for {symbol}: {e}")
            return False, "Error in exit analysis"