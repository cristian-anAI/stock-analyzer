"""
Strategy Manager - Sistema de gestión y switching dinámico de estrategias
Integra con autotrader y backtesting para cambio fácil de estrategias
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass

from .base_strategy import BaseStrategy
from .strategy_registry import StrategyRegistry, MarketType, get_strategy_registry
from .trading_config import TradingConfig

logger = logging.getLogger(__name__)

@dataclass
class StrategySwitch:
    """Registro de cambio de estrategia"""
    timestamp: datetime
    from_strategy: str
    to_strategy: str
    reason: str
    initiated_by: str  # "user", "backtesting", "auto_optimization"

class StrategyManager:
    """
    Manager central para gestión de estrategias
    Permite switching dinámico entre estrategias
    """
    
    def __init__(self, config: Optional[TradingConfig] = None):
        self.registry = get_strategy_registry()
        self.config = config or TradingConfig()
        
        # Estado actual
        self.current_strategy_name: Optional[str] = None
        self.current_strategy: Optional[BaseStrategy] = None
        
        # Historial de cambios
        self.switch_history: List[StrategySwitch] = []
        
        # Configuración de switching automático
        self.auto_switching_enabled = False
        self.performance_threshold = 0.8  # 80% win rate mínimo
        self.evaluation_period_trades = 20  # Evaluar cada 20 trades
        
        logger.info("Strategy Manager initialized")
    
    def initialize_default_strategy(self, market_type: MarketType = MarketType.STOCKS,
                                   risk_tolerance: str = "MEDIUM") -> bool:
        """
        Inicializa con la estrategia recomendada por defecto
        
        Args:
            market_type: Tipo de mercado
            risk_tolerance: Tolerancia al riesgo
            
        Returns:
            bool: True si se inicializó exitosamente
        """
        recommended_strategy = self.registry.get_recommended_strategy(
            market_type=market_type,
            risk_tolerance=risk_tolerance
        )
        
        if not recommended_strategy:
            logger.error(f"No suitable strategy found for {market_type.value}")
            return False
        
        return self.switch_to_strategy(
            strategy_name=recommended_strategy,
            reason="Default initialization",
            initiated_by="system"
        )
    
    def switch_to_strategy(self, strategy_name: str, reason: str = "Manual switch",
                          initiated_by: str = "user") -> bool:
        """
        Cambia a una estrategia específica
        
        Args:
            strategy_name: Nombre de la estrategia destino
            reason: Razón del cambio
            initiated_by: Quien inició el cambio
            
        Returns:
            bool: True si el cambio fue exitoso
        """
        try:
            # Verificar que la estrategia existe y está activa
            new_strategy = self.registry.create_strategy(strategy_name)
            if new_strategy is None:
                logger.error(f"Cannot switch to strategy '{strategy_name}' - not available")
                return False
            
            # Registrar el cambio
            old_strategy_name = self.current_strategy_name or "None"
            switch_record = StrategySwitch(
                timestamp=datetime.now(),
                from_strategy=old_strategy_name,
                to_strategy=strategy_name,
                reason=reason,
                initiated_by=initiated_by
            )
            
            # Realizar el cambio
            old_strategy = self.current_strategy
            self.current_strategy = new_strategy
            self.current_strategy_name = strategy_name
            self.switch_history.append(switch_record)
            
            logger.info(f"Strategy switched: {old_strategy_name} -> {strategy_name} ({reason})")
            
            # Log de configuración de la nueva estrategia
            if hasattr(self.current_strategy, 'get_strategy_config'):
                config = self.current_strategy.get_strategy_config()
                logger.debug(f"New strategy config: {config}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error switching to strategy '{strategy_name}': {e}")
            return False
    
    def get_current_strategy(self) -> Optional[BaseStrategy]:
        """Obtiene la estrategia actual activa"""
        return self.current_strategy
    
    def get_current_strategy_name(self) -> Optional[str]:
        """Obtiene el nombre de la estrategia actual"""
        return self.current_strategy_name
    
    def get_available_strategies(self, market_type: Optional[MarketType] = None) -> Dict[str, Any]:
        """
        Obtiene las estrategias disponibles con información completa
        
        Args:
            market_type: Filtrar por tipo de mercado
            
        Returns:
            Dict con información de estrategias disponibles
        """
        strategies = self.registry.list_strategies(
            market_type=market_type,
            active_only=True
        )
        
        result = {}
        for name, info in strategies.items():
            result[name] = {
                "name": name,
                "type": info.strategy_type.value,
                "market_type": info.market_type.value,
                "description": info.description,
                "risk_level": info.risk_level,
                "proven_backtesting": info.proven_backtesting,
                "recommended_for": info.recommended_for,
                "timeframes": info.min_timeframes,
                "is_current": name == self.current_strategy_name
            }
        
        return result
    
    def validate_strategy_switch(self, target_strategy: str, 
                               available_timeframes: List[str]) -> tuple[bool, str]:
        """
        Valida si es posible cambiar a una estrategia específica
        
        Args:
            target_strategy: Estrategia objetivo
            available_timeframes: Timeframes disponibles
            
        Returns:
            (is_valid, reason)
        """
        # Verificar que existe y está activa
        if target_strategy not in self.registry._strategies:
            return False, f"Strategy '{target_strategy}' does not exist"
        
        strategy_info = self.registry._strategies[target_strategy]
        
        if not strategy_info.active:
            return False, f"Strategy '{target_strategy}' is inactive"
        
        if strategy_info.class_ref is None:
            return False, f"Strategy '{target_strategy}' not implemented yet"
        
        # Verificar timeframes requeridos
        if not self.registry.validate_strategy_requirements(target_strategy, available_timeframes):
            missing = set(strategy_info.min_timeframes) - set(available_timeframes)
            return False, f"Missing required timeframes: {missing}"
        
        return True, "Valid strategy switch"
    
    def get_strategy_performance_summary(self) -> Dict[str, Any]:
        """
        Obtiene resumen de performance de la estrategia actual
        Nota: Requiere integración con sistema de métricas
        """
        if not self.current_strategy_name:
            return {"error": "No active strategy"}
        
        # TODO: Integrar con sistema de métricas de performance
        # Por ahora retorna información básica
        return {
            "current_strategy": self.current_strategy_name,
            "total_switches": len(self.switch_history),
            "last_switch": self.switch_history[-1].timestamp if self.switch_history else None,
            "switch_history": [
                {
                    "timestamp": switch.timestamp.isoformat(),
                    "from": switch.from_strategy,
                    "to": switch.to_strategy,
                    "reason": switch.reason,
                    "initiated_by": switch.initiated_by
                }
                for switch in self.switch_history[-10:]  # Últimos 10 cambios
            ]
        }
    
    def enable_auto_switching(self, performance_threshold: float = 0.8,
                            evaluation_trades: int = 20) -> None:
        """
        Habilita switching automático basado en performance
        
        Args:
            performance_threshold: Threshold mínimo de win rate (0.0-1.0)
            evaluation_trades: Número de trades para evaluar
        """
        self.auto_switching_enabled = True
        self.performance_threshold = performance_threshold
        self.evaluation_period_trades = evaluation_trades
        
        logger.info(f"Auto-switching enabled: {performance_threshold:.1%} threshold, {evaluation_trades} trades evaluation")
    
    def disable_auto_switching(self) -> None:
        """Deshabilita switching automático"""
        self.auto_switching_enabled = False
        logger.info("Auto-switching disabled")
    
    def evaluate_strategy_performance(self, recent_trades_data: List[Dict]) -> Dict[str, Any]:
        """
        Evalúa performance de la estrategia actual y sugiere cambios si es necesario
        
        Args:
            recent_trades_data: Lista de trades recientes con resultados
            
        Returns:
            Dict con evaluación y sugerencias
        """
        if not self.current_strategy_name or not recent_trades_data:
            return {"status": "insufficient_data"}
        
        # Calcular métricas básicas
        total_trades = len(recent_trades_data)
        if total_trades < self.evaluation_period_trades:
            return {"status": "insufficient_trades", "need_trades": self.evaluation_period_trades - total_trades}
        
        # Analizar performance
        winning_trades = len([t for t in recent_trades_data if t.get('pnl', 0) > 0])
        win_rate = winning_trades / total_trades
        
        total_pnl = sum(t.get('pnl', 0) for t in recent_trades_data)
        avg_trade = total_pnl / total_trades if total_trades > 0 else 0
        
        evaluation = {
            "status": "evaluated",
            "current_strategy": self.current_strategy_name,
            "total_trades": total_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_trade_pnl": avg_trade,
            "performance_threshold": self.performance_threshold,
            "needs_switch": win_rate < self.performance_threshold,
            "auto_switching_enabled": self.auto_switching_enabled
        }
        
        # Si está habilitado el auto-switching y la performance es baja
        if self.auto_switching_enabled and win_rate < self.performance_threshold:
            # Buscar estrategia alternativa probada
            current_info = self.registry.get_strategy_info(self.current_strategy_name)
            if current_info:
                alternatives = self.registry.list_strategies(
                    market_type=current_info.market_type,
                    proven_only=True
                )
                
                # Filtrar la estrategia actual
                alternatives = {name: info for name, info in alternatives.items() 
                              if name != self.current_strategy_name}
                
                if alternatives:
                    best_alternative = next(iter(alternatives.keys()))
                    evaluation["suggested_switch"] = best_alternative
                    evaluation["switch_reason"] = f"Low performance: {win_rate:.1%} < {self.performance_threshold:.1%}"
        
        return evaluation
    
    def get_switch_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Obtiene historial de cambios de estrategia
        
        Args:
            limit: Máximo número de registros a retornar
            
        Returns:
            Lista con historial de cambios
        """
        recent_switches = self.switch_history[-limit:] if limit else self.switch_history
        
        return [
            {
                "timestamp": switch.timestamp.isoformat(),
                "from_strategy": switch.from_strategy,
                "to_strategy": switch.to_strategy,
                "reason": switch.reason,
                "initiated_by": switch.initiated_by
            }
            for switch in recent_switches
        ]
    
    def reset_to_proven_strategy(self, market_type: MarketType = MarketType.STOCKS) -> bool:
        """
        Resetea a una estrategia probada en backtesting
        
        Args:
            market_type: Tipo de mercado
            
        Returns:
            bool: True si se cambió exitosamente
        """
        proven_strategies = self.registry.list_strategies(
            market_type=market_type,
            proven_only=True
        )
        
        if not proven_strategies:
            logger.error(f"No proven strategies available for {market_type.value}")
            return False
        
        # Tomar la primera estrategia probada
        strategy_name = next(iter(proven_strategies.keys()))
        
        return self.switch_to_strategy(
            strategy_name=strategy_name,
            reason="Reset to proven strategy",
            initiated_by="system"
        )
    
    def __str__(self) -> str:
        current = self.current_strategy_name or "None"
        switches = len(self.switch_history)
        return f"StrategyManager: Current={current}, Switches={switches}, AutoSwitch={self.auto_switching_enabled}"


# Factory function para fácil creación
def create_strategy_manager(config: Optional[TradingConfig] = None) -> StrategyManager:
    """Factory para crear StrategyManager con configuración"""
    return StrategyManager(config=config)