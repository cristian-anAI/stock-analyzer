"""
BaseStrategy - Clase base para todas las estrategias de trading
Define la interfaz común que deben implementar todas las estrategias
"""

import logging
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class TradingSignal:
    """Representa una señal de trading"""
    
    def __init__(
        self, 
        action: str,  # "BUY", "SELL", "HOLD"
        confidence: float,  # 0-10
        symbol: str,
        timeframe: str,
        reasons: List[str],
        score: float,
        risk_level: str = "MEDIUM",  # "LOW", "MEDIUM", "HIGH"
        suggested_position_size: float = 0.0,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        max_hold_days: Optional[int] = None
    ):
        self.action = action
        self.confidence = confidence
        self.symbol = symbol
        self.timeframe = timeframe
        self.reasons = reasons
        self.score = score
        self.risk_level = risk_level
        self.suggested_position_size = suggested_position_size
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.max_hold_days = max_hold_days
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert signal to dictionary"""
        return {
            "action": self.action,
            "confidence": self.confidence,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "reasons": self.reasons,
            "score": self.score,
            "risk_level": self.risk_level,
            "suggested_position_size": self.suggested_position_size,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "max_hold_days": self.max_hold_days,
            "timestamp": self.timestamp.isoformat()
        }

class BaseStrategy(ABC):
    """
    Clase base abstracta para estrategias de trading
    Define la interfaz que deben implementar todas las estrategias
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
        # Configuración base - debe ser sobrescrita por subclases
        self.timeframe_primary = "1d"
        self.timeframe_confirmation = None
        self.timeframe_entry = None
        
        # Thresholds
        self.buy_threshold = 7.5
        self.sell_threshold = 4.0
        self.strong_buy_threshold = 8.5
        self.strong_sell_threshold = 3.0
        
        # Risk management
        self.max_position_size_percent = 15.0  # % of portfolio
        self.stop_loss_percent = 8.0
        self.take_profit_percent = 15.0
        self.max_hold_days = 30
        
        # Trading limits
        self.max_positions = 10
        self.risk_per_trade_percent = 2.0
        
        self.logger.info(f"Initialized {self.name} strategy")
    
    @abstractmethod
    def calculate_score(self, symbol: str, data: Dict[str, pd.DataFrame]) -> float:
        """
        Calcular score principal para el símbolo usando datos de múltiples timeframes
        
        Args:
            symbol: Símbolo a analizar
            data: Dict con DataFrames por timeframe
        
        Returns:
            Score de 0-10
        """
        pass
    
    @abstractmethod
    def generate_signal(self, symbol: str, current_price: float, data: Dict[str, pd.DataFrame]) -> TradingSignal:
        """
        Generar señal de trading basada en el análisis
        
        Args:
            symbol: Símbolo a analizar
            current_price: Precio actual
            data: Dict con DataFrames por timeframe
        
        Returns:
            TradingSignal con recomendación
        """
        pass
    
    def should_exit_position(
        self, 
        symbol: str, 
        entry_price: float, 
        current_price: float,
        days_held: int,
        position_side: str = "LONG",
        data: Dict[str, pd.DataFrame] = None
    ) -> Tuple[bool, str]:
        """
        Determinar si se debe salir de una posición existente
        
        Args:
            symbol: Símbolo de la posición
            entry_price: Precio de entrada
            current_price: Precio actual
            days_held: Días que se ha mantenido la posición
            position_side: "LONG" o "SHORT"
            data: Datos de mercado (opcional)
        
        Returns:
            (should_exit, reason)
        """
        try:
            # Stop loss check
            if position_side == "LONG":
                loss_percent = ((entry_price - current_price) / entry_price) * 100
                profit_percent = ((current_price - entry_price) / entry_price) * 100
            else:  # SHORT
                loss_percent = ((current_price - entry_price) / entry_price) * 100
                profit_percent = ((entry_price - current_price) / entry_price) * 100
            
            # Stop loss triggered
            if loss_percent >= self.stop_loss_percent:
                return True, f"Stop loss triggered: -{loss_percent:.1f}%"
            
            # Take profit triggered
            if profit_percent >= self.take_profit_percent:
                return True, f"Take profit triggered: +{profit_percent:.1f}%"
            
            # Max hold period
            if days_held >= self.max_hold_days:
                return True, f"Max hold period reached: {days_held} days"
            
            # Strategy-specific exit logic (using current score if data available)
            if data is not None:
                current_score = self.calculate_score(symbol, data)
                
                if position_side == "LONG" and current_score <= self.sell_threshold:
                    return True, f"Score dropped to {current_score:.1f}"
                elif position_side == "SHORT" and current_score >= self.buy_threshold:
                    return True, f"Score rose to {current_score:.1f}"
            
            return False, "Hold position"
            
        except Exception as e:
            self.logger.error(f"Error checking exit for {symbol}: {e}")
            return False, "Error in exit analysis"
    
    def validate_entry_conditions(self, symbol: str, signal: TradingSignal) -> Tuple[bool, str]:
        """
        Validar condiciones adicionales antes de entrar en posición
        Puede ser sobrescrito por subclases para validaciones específicas
        
        Args:
            symbol: Símbolo a validar
            signal: Señal generada
        
        Returns:
            (is_valid, reason)
        """
        # Validaciones base
        if signal.confidence < 6.0:
            return False, f"Confidence too low: {signal.confidence}"
        
        if signal.score < self.buy_threshold and signal.action == "BUY":
            return False, f"Score below buy threshold: {signal.score}"
        
        if signal.risk_level == "HIGH":
            return False, "Risk level too high"
        
        return True, "Entry conditions met"
    
    def calculate_position_size(
        self, 
        symbol: str, 
        current_price: float, 
        available_capital: float,
        volatility: Optional[float] = None
    ) -> float:
        """
        Calcular tamaño de posición basado en riesgo y capital disponible
        
        Args:
            symbol: Símbolo 
            current_price: Precio actual
            available_capital: Capital disponible
            volatility: Volatilidad opcional para ajuste
        
        Returns:
            Valor en USD para la posición
        """
        try:
            # Base position size
            base_size = available_capital * (self.risk_per_trade_percent / 100)
            
            # Adjust for volatility if provided
            if volatility is not None:
                # Reduce position size for high volatility
                if volatility > 0.3:  # 30% volatility
                    base_size *= 0.5
                elif volatility > 0.2:  # 20% volatility
                    base_size *= 0.7
            
            # Cap at max position size
            max_size = available_capital * (self.max_position_size_percent / 100)
            position_size = min(base_size, max_size)
            
            self.logger.debug(f"Calculated position size for {symbol}: ${position_size:.2f}")
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating position size for {symbol}: {e}")
            return available_capital * 0.02  # Default 2% if calculation fails
    
    def get_required_timeframes(self) -> List[str]:
        """
        Retorna lista de timeframes requeridos por esta estrategia
        
        Returns:
            Lista de timeframes necesarios
        """
        timeframes = [self.timeframe_primary]
        
        if self.timeframe_confirmation:
            timeframes.append(self.timeframe_confirmation)
        
        if self.timeframe_entry and self.timeframe_entry not in timeframes:
            timeframes.append(self.timeframe_entry)
        
        return timeframes
    
    def get_strategy_config(self) -> Dict[str, Any]:
        """
        Retorna configuración actual de la estrategia
        
        Returns:
            Dict con configuración
        """
        return {
            "name": self.name,
            "timeframe_primary": self.timeframe_primary,
            "timeframe_confirmation": self.timeframe_confirmation,
            "timeframe_entry": self.timeframe_entry,
            "buy_threshold": self.buy_threshold,
            "sell_threshold": self.sell_threshold,
            "max_position_size_percent": self.max_position_size_percent,
            "stop_loss_percent": self.stop_loss_percent,
            "take_profit_percent": self.take_profit_percent,
            "max_hold_days": self.max_hold_days,
            "risk_per_trade_percent": self.risk_per_trade_percent
        }
    
    def __str__(self):
        return f"{self.name} Strategy (Primary: {self.timeframe_primary})"