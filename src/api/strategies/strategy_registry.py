"""
Strategy Registry - Sistema centralizado de gestión de estrategias
Permite fácil switching entre estrategias para backtesting y autotrader
"""

import logging
from typing import Dict, Type, List, Optional
from enum import Enum
from dataclasses import dataclass

from .base_strategy import BaseStrategy
from .swing_trading_strategy import SwingTradingStrategy
from .crypto_competition_strategy import CryptoCompetitionStrategy
from .multi_timeframe_strategy import MultiTimeframeScoringStrategy

logger = logging.getLogger(__name__)

class StrategyType(Enum):
    """Tipos de estrategias disponibles"""
    SWING_TRADING = "swing_trading"
    CRYPTO_COMPETITION = "crypto_competition"
    MULTI_TIMEFRAME = "multi_timeframe"  # Para futura MTSS
    CUSTOM = "custom"

class MarketType(Enum):
    """Tipos de mercado"""
    STOCKS = "stocks"
    CRYPTO = "crypto"
    BOTH = "both"

@dataclass
class StrategyInfo:
    """Información de registro de estrategia"""
    name: str
    strategy_type: StrategyType
    market_type: MarketType
    description: str
    class_ref: Type[BaseStrategy]
    recommended_for: List[str]
    min_timeframes: List[str]
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    proven_backtesting: bool = False
    active: bool = True

class StrategyRegistry:
    """
    Registry centralizado de todas las estrategias
    Permite fácil switching y gestión de estrategias
    """
    
    def __init__(self):
        self._strategies: Dict[str, StrategyInfo] = {}
        self._register_default_strategies()
        logger.info("Strategy Registry initialized")
    
    def _register_default_strategies(self):
        """Registra las estrategias por defecto del sistema"""
        
        # Swing Trading Strategy (PROBADA EN BACKTESTING)
        self.register_strategy(StrategyInfo(
            name="swing_trading",
            strategy_type=StrategyType.SWING_TRADING,
            market_type=MarketType.STOCKS,
            description="Estrategia de swing trading validada con 95.8% win rate",
            class_ref=SwingTradingStrategy,
            recommended_for=["stocks", "medium_risk", "3-20_day_holds"],
            min_timeframes=["1d", "4h", "1h"],
            risk_level="MEDIUM",
            proven_backtesting=True,
            active=True
        ))
        
        # Crypto Competition Strategy
        self.register_strategy(StrategyInfo(
            name="crypto_competition",
            strategy_type=StrategyType.CRYPTO_COMPETITION,
            market_type=MarketType.CRYPTO,
            description="Estrategia agresiva para crypto con filtros de volatilidad",
            class_ref=CryptoCompetitionStrategy,
            recommended_for=["crypto", "high_risk", "1-10_day_holds"],
            min_timeframes=["4h", "1h"],
            risk_level="HIGH",
            proven_backtesting=False,
            active=True
        ))
        
        # Multi-Timeframe Strategy (COMPLETAMENTE IMPLEMENTADA)
        self.register_strategy(StrategyInfo(
            name="multi_timeframe",
            strategy_type=StrategyType.MULTI_TIMEFRAME,
            market_type=MarketType.STOCKS,
            description="Multi-Timeframe Scoring Strategy: Hierarchical 1M→1W→1D→1H with real indicators",
            class_ref=MultiTimeframeScoringStrategy,  # ✅ IMPLEMENTADA
            recommended_for=["stocks", "systematic", "hierarchical_filtering", "technical_analysis"],
            min_timeframes=["1M", "1W", "1d", "1h"],
            risk_level="MEDIUM",
            proven_backtesting=False,  # Lista para backtesting
            active=True  # ✅ ACTIVA PARA BACKTESTING
        ))
    
    def register_strategy(self, strategy_info: StrategyInfo) -> bool:
        """
        Registra una nueva estrategia en el sistema
        
        Args:
            strategy_info: Información completa de la estrategia
            
        Returns:
            bool: True si se registró exitosamente
        """
        try:
            self._strategies[strategy_info.name] = strategy_info
            logger.info(f"Registered strategy: {strategy_info.name} ({strategy_info.strategy_type.value})")
            return True
        except Exception as e:
            logger.error(f"Error registering strategy {strategy_info.name}: {e}")
            return False
    
    def get_strategy_class(self, strategy_name: str) -> Optional[Type[BaseStrategy]]:
        """
        Obtiene la clase de una estrategia por nombre
        
        Args:
            strategy_name: Nombre de la estrategia
            
        Returns:
            Clase de la estrategia o None si no existe/no está activa
        """
        if strategy_name not in self._strategies:
            logger.error(f"Strategy '{strategy_name}' not found in registry")
            return None
        
        strategy_info = self._strategies[strategy_name]
        
        if not strategy_info.active:
            logger.warning(f"Strategy '{strategy_name}' is inactive")
            return None
        
        if strategy_info.class_ref is None:
            logger.warning(f"Strategy '{strategy_name}' not implemented yet")
            return None
            
        return strategy_info.class_ref
    
    def create_strategy(self, strategy_name: str) -> Optional[BaseStrategy]:
        """
        Instancia una estrategia por nombre
        
        Args:
            strategy_name: Nombre de la estrategia
            
        Returns:
            Instancia de la estrategia o None
        """
        strategy_class = self.get_strategy_class(strategy_name)
        if strategy_class is None:
            return None
        
        try:
            strategy_instance = strategy_class()
            logger.info(f"Created strategy instance: {strategy_name}")
            return strategy_instance
        except Exception as e:
            logger.error(f"Error creating strategy {strategy_name}: {e}")
            return None
    
    def list_strategies(self, market_type: Optional[MarketType] = None, 
                       active_only: bool = True,
                       proven_only: bool = False) -> Dict[str, StrategyInfo]:
        """
        Lista estrategias disponibles con filtros
        
        Args:
            market_type: Filtrar por tipo de mercado
            active_only: Solo estrategias activas
            proven_only: Solo estrategias probadas en backtesting
            
        Returns:
            Dict con estrategias que cumplen los filtros
        """
        filtered_strategies = {}
        
        for name, info in self._strategies.items():
            # Filtros
            if active_only and not info.active:
                continue
            
            if proven_only and not info.proven_backtesting:
                continue
            
            if market_type is not None and info.market_type not in [market_type, MarketType.BOTH]:
                continue
            
            filtered_strategies[name] = info
        
        return filtered_strategies
    
    def get_recommended_strategy(self, market_type: MarketType, 
                               risk_tolerance: str = "MEDIUM") -> Optional[str]:
        """
        Obtiene la estrategia recomendada para un mercado y tolerancia al riesgo
        
        Args:
            market_type: Tipo de mercado (STOCKS, CRYPTO)
            risk_tolerance: Tolerancia al riesgo ("LOW", "MEDIUM", "HIGH")
            
        Returns:
            Nombre de la estrategia recomendada
        """
        # Priorizar estrategias probadas en backtesting
        strategies = self.list_strategies(market_type=market_type, proven_only=True)
        
        # Si no hay estrategias probadas, usar todas las activas
        if not strategies:
            strategies = self.list_strategies(market_type=market_type, active_only=True)
        
        # Filtrar por risk level
        matching_strategies = []
        for name, info in strategies.items():
            if info.risk_level == risk_tolerance:
                matching_strategies.append((name, info))
        
        # Si no hay match exacto, usar la primera disponible
        if not matching_strategies and strategies:
            first_strategy = next(iter(strategies.items()))
            matching_strategies = [first_strategy]
        
        if matching_strategies:
            # Priorizar probadas en backtesting
            proven_strategies = [(name, info) for name, info in matching_strategies if info.proven_backtesting]
            if proven_strategies:
                return proven_strategies[0][0]
            return matching_strategies[0][0]
        
        logger.warning(f"No suitable strategy found for {market_type.value} with {risk_tolerance} risk")
        return None
    
    def get_strategy_info(self, strategy_name: str) -> Optional[StrategyInfo]:
        """Obtiene información completa de una estrategia"""
        return self._strategies.get(strategy_name)
    
    def set_strategy_status(self, strategy_name: str, active: bool) -> bool:
        """
        Activa o desactiva una estrategia
        
        Args:
            strategy_name: Nombre de la estrategia
            active: True para activar, False para desactivar
            
        Returns:
            bool: True si se cambió el estado exitosamente
        """
        if strategy_name not in self._strategies:
            logger.error(f"Strategy '{strategy_name}' not found")
            return False
        
        self._strategies[strategy_name].active = active
        status = "activated" if active else "deactivated"
        logger.info(f"Strategy '{strategy_name}' {status}")
        return True
    
    def mark_strategy_proven(self, strategy_name: str, proven: bool = True) -> bool:
        """
        Marca una estrategia como probada en backtesting
        
        Args:
            strategy_name: Nombre de la estrategia
            proven: True si está probada
            
        Returns:
            bool: True si se actualizó exitosamente
        """
        if strategy_name not in self._strategies:
            logger.error(f"Strategy '{strategy_name}' not found")
            return False
        
        self._strategies[strategy_name].proven_backtesting = proven
        status = "marked as proven" if proven else "marked as unproven"
        logger.info(f"Strategy '{strategy_name}' {status}")
        return True
    
    def get_all_timeframes(self) -> List[str]:
        """Obtiene todos los timeframes requeridos por las estrategias activas"""
        timeframes = set()
        
        for info in self._strategies.values():
            if info.active and info.class_ref is not None:
                timeframes.update(info.min_timeframes)
        
        return sorted(list(timeframes))
    
    def validate_strategy_requirements(self, strategy_name: str, available_timeframes: List[str]) -> bool:
        """
        Valida si una estrategia puede ejecutarse con los timeframes disponibles
        
        Args:
            strategy_name: Nombre de la estrategia
            available_timeframes: Lista de timeframes disponibles
            
        Returns:
            bool: True si se pueden satisfacer los requerimientos
        """
        if strategy_name not in self._strategies:
            return False
        
        strategy_info = self._strategies[strategy_name]
        required_timeframes = set(strategy_info.min_timeframes)
        available_set = set(available_timeframes)
        
        missing_timeframes = required_timeframes - available_set
        
        if missing_timeframes:
            logger.warning(f"Strategy '{strategy_name}' missing timeframes: {missing_timeframes}")
            return False
        
        return True
    
    def __str__(self) -> str:
        active_count = len([s for s in self._strategies.values() if s.active])
        proven_count = len([s for s in self._strategies.values() if s.proven_backtesting])
        return f"StrategyRegistry: {len(self._strategies)} total, {active_count} active, {proven_count} proven"


# Global registry instance
strategy_registry = StrategyRegistry()


def get_strategy_registry() -> StrategyRegistry:
    """Obtiene la instancia global del registry"""
    return strategy_registry