"""
MTSS Crypto Strategy - Multi-Timeframe Scoring optimizado para criptomonedas
Hereda de MultiTimeframeScoringStrategy con parámetros crypto-específicos

Características Crypto:
- Mercado 24/7: Puede usar todos los timeframes
- Mayor volatilidad: Thresholds más altos
- Timeframes ajustados: Mayor peso en timeframes menores
- Risk management específico para crypto
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .multi_timeframe_strategy import MultiTimeframeScoringStrategy, MTSSParameters, TimeframeScore
from .base_strategy import TradingSignal

logger = logging.getLogger(__name__)

@dataclass
class MTSSCryptoParameters(MTSSParameters):
    """Parámetros MTSS optimizados para criptomonedas"""
    
    # Thresholds más altos por volatilidad crypto
    monthly_filter_min: float = 6.5      # vs 6.0 stocks
    confidence_aggressive: float = 9.0   # vs 8.5 stocks  
    confidence_full: float = 8.0         # vs 7.5 stocks
    confidence_partial: float = 7.0      # vs 6.5 stocks
    
    # Pesos ajustados para crypto (más peso en timeframes menores por volatilidad)
    weight_monthly: float = 0.35         # vs 0.40 stocks
    weight_weekly: float = 0.25          # vs 0.30 stocks  
    weight_daily: float = 0.25           # vs 0.20 stocks
    weight_hourly: float = 0.15          # vs 0.10 stocks
    
    # RSI más agresivo para crypto
    rsi_oversold: float = 20.0           # vs 25.0 stocks
    rsi_neutral_min: float = 25.0        # vs 30.0 stocks
    rsi_neutral_max: float = 75.0        # vs 80.0 stocks
    
    # MACD más sensible para crypto
    macd_very_bullish: float = 0.3       # vs 0.5 stocks
    macd_bullish: float = 0.1            # vs 0.2 stocks
    
    # Risk management crypto
    stop_loss_percent: float = 15.0      # Mayor por volatilidad
    take_profit_percent: float = 30.0    # Mayor objetivo
    risk_per_trade_percent: float = 5.0  # Mayor riesgo
    
    # Volatility limits específicos
    volatility_limit: float = 0.20       # 20% daily max
    emergency_exit_volatility: float = 0.35  # 35% emergency exit

class MTSSCryptoStrategy(MultiTimeframeScoringStrategy):
    """
    MTSS Strategy optimizada para criptomonedas
    
    Mejoras crypto-específicas:
    - Timeframes 24/7: 1M → 1W → 1D → 4H (en vez de 1H)
    - Thresholds más altos por volatilidad
    - Risk management específico
    - Filtros de volatilidad mejorados
    """
    
    def __init__(self, parameters: Optional[MTSSCryptoParameters] = None):
        # Usar parámetros crypto por defecto
        crypto_params = parameters or MTSSCryptoParameters()
        super().__init__(crypto_params)
        
        # Override strategy name
        self.name = "MTSS_Crypto"
        
        # Timeframes específicos crypto (usar 4H en vez de 1H para mejor señal)
        self.timeframe_primary = "1M"
        self.timeframe_confirmation = "1W"  
        self.timeframe_daily = "1d"
        self.timeframe_entry = "4h"  # 4H en vez de 1H para crypto
        
        # Timeframes requeridos actualizados
        self.required_timeframes = ["1M", "1W", "1d", "4h"]
        
        # Crypto specific parameters
        self.crypto_params = crypto_params
        
        # Override risk management para crypto
        self.max_hold_days = 10  # Más corto para crypto
        self.stop_loss_percent = self.crypto_params.stop_loss_percent
        self.take_profit_percent = self.crypto_params.take_profit_percent
        self.risk_per_trade_percent = self.crypto_params.risk_per_trade_percent
        
        logger.info("MTSS Crypto Strategy initialized with optimized parameters")
    
    def get_required_timeframes(self) -> List[str]:
        """Return list of required timeframes for MTSS crypto strategy"""
        return self.required_timeframes
    
    def calculate_timeframe_scores(self, symbol: str, data: Dict[str, pd.DataFrame]) -> List[TimeframeScore]:
        """
        Override para usar timeframes crypto (4H en vez de 1H)
        """
        scores = []
        
        # 1M: MACD Filter (OBLIGATORIO)
        monthly_score = self._calculate_monthly_macd_score(symbol, data.get("1M"))
        scores.append(monthly_score)
        
        # 1W: Ichimoku Cloud Position
        weekly_score = self._calculate_weekly_ichimoku_score(symbol, data.get("1W"))  
        scores.append(weekly_score)
        
        # 1D: Moving Averages Alignment
        daily_score = self._calculate_daily_ma_score(symbol, data.get("1d"))
        scores.append(daily_score)
        
        # 4H: RSI Modified Timing (crypto usa 4H en vez de 1H)
        hourly_score = self._calculate_4h_rsi_score(symbol, data.get("4h"))
        scores.append(hourly_score)
        
        return scores
    
    def _calculate_4h_rsi_score(self, symbol: str, data: Optional[pd.DataFrame]) -> TimeframeScore:
        """
        Calcula score 4H específico para crypto con RSI optimizado
        """
        if data is None or data.empty or len(data) < 50:
            return TimeframeScore("4h", 5.0, 0.0, 0.5, "No 4H data", "LOW", ["No data"])
        
        try:
            # Calcular RSI
            close = data['Close']
            delta = close.diff()
            
            # Calcular gains y losses
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            
            # RSI
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # Scoring granular para crypto (más agresivo)
            risk_factors = []
            
            if current_rsi <= self.crypto_params.rsi_oversold:
                score = 10.0
                confidence = "EXCELLENT"
                reasoning = f"4H RSI extremely oversold: {current_rsi:.1f}"
            elif current_rsi <= 35:
                score = 8.0
                confidence = "HIGH"
                reasoning = f"4H RSI oversold: {current_rsi:.1f}"
            elif current_rsi <= 45:
                score = 7.0
                confidence = "MEDIUM"
                reasoning = f"4H RSI favorable: {current_rsi:.1f}"
            elif current_rsi <= 55:
                score = 6.0
                confidence = "MEDIUM"
                reasoning = f"4H RSI neutral: {current_rsi:.1f}"
            elif current_rsi <= 65:
                score = 5.0
                confidence = "MEDIUM"
                reasoning = f"4H RSI slightly elevated: {current_rsi:.1f}"
                risk_factors.append("RSI approaching overbought")
            elif current_rsi <= self.crypto_params.rsi_neutral_max:
                score = 3.0
                confidence = "LOW"
                reasoning = f"4H RSI overbought: {current_rsi:.1f}"
                risk_factors.append("RSI overbought")
            else:
                score = 1.0
                confidence = "LOW"
                reasoning = f"4H RSI extremely overbought: {current_rsi:.1f}"
                risk_factors.append("RSI extremely overbought")
            
            # Check RSI momentum (rising/falling)
            if len(rsi) >= 3:
                rsi_momentum = rsi.iloc[-1] - rsi.iloc[-3]
                if rsi_momentum > 5 and current_rsi < 50:
                    score += 0.5  # Positive momentum bonus
                    reasoning += " + rising momentum"
                elif rsi_momentum < -5 and current_rsi > 50:
                    score -= 0.5  # Negative momentum penalty
                    reasoning += " + falling momentum"
            
            # Check for RSI divergences (advanced feature)
            divergence_score = self._check_rsi_divergence(data, rsi)
            if divergence_score != 0:
                score += divergence_score
                if divergence_score > 0:
                    reasoning += " + bullish divergence"
                else:
                    reasoning += " + bearish divergence"
            
            # Cap score
            final_score = max(1.0, min(10.0, score))
            signal_strength = (final_score - 1) / 9.0  # Normalize to 0-1
            
            return TimeframeScore("4h", final_score, current_rsi, signal_strength, reasoning, confidence, risk_factors)
            
        except Exception as e:
            logger.error(f"Error calculating 4H RSI score for {symbol}: {e}")
            return TimeframeScore("4h", 5.0, 0.0, 0.5, f"Error: {str(e)}", "LOW", ["Calculation error"])
    
    def _check_rsi_divergence(self, data: pd.DataFrame, rsi: pd.Series) -> float:
        """
        Detecta divergencias RSI vs precio (feature avanzada para crypto)
        Returns: -1.0 to +1.0 (bearish to bullish divergence)
        """
        try:
            if len(data) < 20 or len(rsi) < 20:
                return 0.0
            
            # Get last 20 periods for analysis
            recent_data = data.tail(20)
            recent_rsi = rsi.tail(20)
            
            # Find recent highs and lows
            price_highs = recent_data['High'].rolling(3).max()
            price_lows = recent_data['Low'].rolling(3).min()
            rsi_highs = recent_rsi.rolling(3).max()
            rsi_lows = recent_rsi.rolling(3).min()
            
            # Simple divergence detection (could be enhanced)
            current_price = recent_data['Close'].iloc[-1]
            prev_high_price = price_highs.iloc[-5:-1].max()
            
            current_rsi = recent_rsi.iloc[-1]
            prev_high_rsi = rsi_highs.iloc[-5:-1].max()
            
            # Bullish divergence: price lower high, RSI higher high
            if (current_price > prev_high_price * 0.98 and 
                current_rsi > prev_high_rsi and 
                current_rsi < 50):
                return 0.5  # Moderate bullish divergence
            
            # Bearish divergence: price higher high, RSI lower high  
            if (current_price > prev_high_price and 
                current_rsi < prev_high_rsi and 
                current_rsi > 50):
                return -0.5  # Moderate bearish divergence
            
            return 0.0
            
        except Exception as e:
            logger.debug(f"Error checking RSI divergence: {e}")
            return 0.0
    
    def _passes_crypto_volatility_filter(self, symbol: str, data: Dict[str, pd.DataFrame]) -> tuple[bool, str]:
        """
        Filtro de volatilidad específico para crypto
        """
        try:
            daily_data = data.get("1d")
            if daily_data is None or len(daily_data) < 10:
                return True, "Insufficient data for volatility check"
            
            # Calculate recent volatility
            recent_closes = daily_data.tail(14)['Close']  # Last 2 weeks
            daily_returns = recent_closes.pct_change().dropna()
            
            if len(daily_returns) < 7:
                return True, "Insufficient volatility data"
            
            daily_volatility = daily_returns.std()
            
            # Check against crypto limits
            if daily_volatility > self.crypto_params.volatility_limit:
                return False, f"Volatility {daily_volatility:.1%} > limit {self.crypto_params.volatility_limit:.1%}"
            
            # Emergency check
            if daily_volatility > self.crypto_params.emergency_exit_volatility:
                return False, f"EMERGENCY: Volatility {daily_volatility:.1%} > emergency limit"
            
            return True, f"Volatility OK: {daily_volatility:.1%}"
            
        except Exception as e:
            logger.error(f"Error in crypto volatility filter for {symbol}: {e}")
            return True, "Volatility filter error - allowing trade"
    
    def generate_signal(self, symbol: str, current_price: float, data: Dict[str, pd.DataFrame]) -> TradingSignal:
        """
        Override para generar señales crypto con filtros específicos
        """
        try:
            # Check crypto volatility filter first
            passes_vol, vol_reason = self._passes_crypto_volatility_filter(symbol, data)
            if not passes_vol:
                return TradingSignal(
                    action="HOLD",
                    confidence=0.0,
                    symbol=symbol,
                    timeframe=self.timeframe_primary,
                    reasons=[f"Volatility filter: {vol_reason}"],
                    score=5.0,
                    risk_level="HIGH"
                )
            
            # Calculate MTSS score
            score = self.calculate_score(symbol, data)
            
            # Determine action with crypto-specific thresholds
            reasons = [vol_reason]
            
            if score >= self.crypto_params.confidence_aggressive:
                action = "BUY"
                confidence = min(9.8, score)
                risk_level = "HIGH"
                reasons.append(f"AGGRESSIVE: Score {score:.1f} ≥ {self.crypto_params.confidence_aggressive}")
            elif score >= self.crypto_params.confidence_full:
                action = "BUY"
                confidence = score
                risk_level = "MEDIUM" 
                reasons.append(f"FULL: Score {score:.1f} ≥ {self.crypto_params.confidence_full}")
            elif score >= self.crypto_params.confidence_partial:
                action = "BUY"
                confidence = score * 0.7  # Reduced confidence for partial
                risk_level = "MEDIUM"
                reasons.append(f"PARTIAL: Score {score:.1f} ≥ {self.crypto_params.confidence_partial}")
            elif score >= self.crypto_params.monthly_filter_min:
                action = "HOLD"
                confidence = score
                risk_level = "LOW"
                reasons.append(f"WAIT: Score {score:.1f} below partial threshold")
            else:
                action = "HOLD"
                confidence = 0.0
                risk_level = "HIGH"
                reasons.append(f"NO_TRADE: Monthly filter blocked (score {score:.1f})")
            
            # Position sizing based on confidence level
            position_size = 0.0
            if action == "BUY":
                if score >= self.crypto_params.confidence_aggressive:
                    position_size = current_price * 0.05  # Full position
                elif score >= self.crypto_params.confidence_full:
                    position_size = current_price * 0.04  # 80% position
                else:
                    position_size = current_price * 0.025  # 50% position (partial)
            
            # Calculate stop loss and take profit
            stop_loss = None
            take_profit = None
            if action == "BUY":
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
                suggested_position_size=position_size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                max_hold_days=self.max_hold_days
            )
            
            logger.info(f"MTSS Crypto signal for {symbol}: {action} (score: {score:.2f}, confidence: {confidence:.1f})")
            return signal
            
        except Exception as e:
            logger.error(f"Error generating MTSS crypto signal for {symbol}: {e}")
            return TradingSignal(
                action="HOLD",
                confidence=0.0,
                symbol=symbol,
                timeframe=self.timeframe_primary,
                reasons=[f"Error in MTSS crypto analysis: {str(e)}"],
                score=5.0,
                risk_level="HIGH"
            )
    
    def should_exit_position(
        self, 
        symbol: str, 
        entry_price: float, 
        current_price: float,
        days_held: int,
        position_side: str = "LONG",
        data: Dict[str, pd.DataFrame] = None
    ) -> tuple[bool, str]:
        """
        Override exit logic para crypto con volatilidad específica
        """
        
        # Emergency volatility exit
        if data is not None:
            passes_vol, vol_reason = self._passes_crypto_volatility_filter(symbol, data)
            if not passes_vol and "EMERGENCY" in vol_reason:
                return True, f"Emergency volatility exit: {vol_reason}"
        
        # Quick profit taking para crypto (más agresivo)
        profit_percent = ((current_price - entry_price) / entry_price) * 100
        
        if position_side == "LONG":
            # Take profits más rápido en crypto si volatilidad alta
            if profit_percent > 20 and days_held >= 1:
                if data is not None:
                    daily_data = data.get("1d")
                    if daily_data is not None and len(daily_data) >= 7:
                        recent_vol = daily_data.tail(7)['Close'].pct_change().std()
                        if recent_vol > 0.15:  # High volatility
                            return True, f"Quick profit in high volatility: +{profit_percent:.1f}%"
            
            # Standard crypto profit taking
            if profit_percent > self.take_profit_percent:
                return True, f"Take profit: +{profit_percent:.1f}%"
            
            # Stop loss
            if profit_percent < -self.stop_loss_percent:
                return True, f"Stop loss: {profit_percent:.1f}%"
        
        # Call base class for additional exit logic
        base_exit, base_reason = super().should_exit_position(
            symbol, entry_price, current_price, days_held, position_side, data
        )
        
        return base_exit, base_reason