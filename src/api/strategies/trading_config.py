"""
Trading Configuration - Configuración unificada de estrategias
Centraliza todos los thresholds y parámetros para backtesting y autotrader
Integrado con sistema flexible de estrategias
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class TradingConfig:
    """Configuración unificada de trading validada por backtesting"""
    
    # STRATEGY MANAGEMENT (NUEVO SISTEMA FLEXIBLE)
    active_strategy: str = "swing_trading"  # Estrategia activa por defecto
    crypto_strategy: str = "competition"  # "competition" o "mtss" 
    auto_strategy_switching: bool = False   # Cambio automático de estrategias
    strategy_performance_threshold: float = 0.8  # 80% win rate para mantener estrategia
    
    # THRESHOLDS PROBADOS EN BACKTESTING (Septiembre 1, 2025)
    # Basado en backtest_simplified.py con 95.8% win rate (30d)
    buy_score_threshold: float = 6.0  # Threshold exacto del backtesting exitoso
    sell_score_threshold: float = 4.5  # Ajustado para mejor timing de salida
    
    # Position Management (validado en backtesting)
    max_position_value: float = 10000.0  # $10k por posición
    max_positions_stocks: int = 10  # Máximo 10 posiciones de stocks
    max_positions_crypto: int = 6   # Máximo 6 posiciones de crypto
    
    # Risk Management
    stop_loss_percent: float = 8.0
    take_profit_percent: float = 15.0
    risk_per_trade_percent: float = 2.0
    
    # Portfolio Allocation (PortfolioManager)
    liquid_capital_stocks: float = 70000.0  # $70k para stocks
    liquid_capital_crypto: float = 30000.0  # $30k para crypto
    
    # Strategy Flags
    short_trading_enabled: bool = False  # Backtest tuvo 0 shorts exitosos
    high_volatility_bypass: bool = True  # Permite trading en alta volatilidad
    
    # Swing Trading Specific
    swing_min_hold_days: int = 3
    swing_max_hold_days: int = 20
    swing_max_position_size_percent: float = 12.0
    
    # Market Conditions
    use_database_scores: bool = True  # Usar scores de DB, no calcular propios
    
    @classmethod
    def get_backtest_proven_config(cls) -> 'TradingConfig':
        """
        Retorna la configuración exacta que demostró éxito en backtesting
        95.8% win rate (30d), 91.7% win rate (60d), 72 trades exitosos
        """
        return cls()
    
    @classmethod
    def get_conservative_config(cls) -> 'TradingConfig':
        """Configuración más conservadora para mercados volátiles"""
        config = cls()
        config.buy_score_threshold = 6.5  # Más selectivo
        config.max_position_value = 8000.0  # Posiciones más pequeñas
        config.stop_loss_percent = 6.0  # Stop loss más ajustado
        config.active_strategy = "swing_trading"  # Mantener estrategia probada
        return config
    
    @classmethod
    def get_multi_timeframe_config(cls) -> 'TradingConfig':
        """Configuración para Multi-Timeframe Strategy (MTSS) - FUTURA"""
        config = cls()
        config.active_strategy = "multi_timeframe"  
        config.buy_score_threshold = 1.0  # MTSS usa scoring binario diferente
        config.sell_score_threshold = 0.0
        config.max_position_value = 8000.0  # Más conservador para nueva estrategia
        config.use_database_scores = False  # MTSS calcula scores propios
        return config
    
    @classmethod
    def get_crypto_competition_config(cls) -> 'TradingConfig':
        """Configuración para Crypto Competition Strategy"""
        config = cls()
        config.active_strategy = "crypto_competition"
        config.buy_score_threshold = 8.0  # Más agresivo para crypto
        config.sell_score_threshold = 3.5
        config.max_position_value = 15000.0  # Posiciones más grandes para crypto
        config.risk_per_trade_percent = 5.0  # Mayor riesgo crypto
        return config
        
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para logging y debugging"""
        return {
            'active_strategy': self.active_strategy,
            'auto_switching': self.auto_strategy_switching,
            'performance_threshold': self.strategy_performance_threshold,
            'buy_threshold': self.buy_score_threshold,
            'sell_threshold': self.sell_score_threshold,
            'max_position_value': self.max_position_value,
            'max_positions_stocks': self.max_positions_stocks,
            'short_enabled': self.short_trading_enabled,
            'volatility_bypass': self.high_volatility_bypass,
            'use_db_scores': self.use_database_scores
        }

# Configuración global por defecto - PROBADA EN BACKTESTING
TRADING_CONFIG = TradingConfig.get_backtest_proven_config()

# Configuraciones específicas para diferentes modos
BACKTEST_CONFIG = TradingConfig.get_backtest_proven_config()
PRODUCTION_CONFIG = TradingConfig.get_backtest_proven_config()
CONSERVATIVE_CONFIG = TradingConfig.get_conservative_config()

# Configuraciones por estrategia (para fácil switching)
STRATEGY_CONFIGS = {
    "swing_trading": TradingConfig.get_backtest_proven_config(),
    "crypto_competition": TradingConfig.get_crypto_competition_config(),
    "multi_timeframe": TradingConfig.get_multi_timeframe_config(),  # FUTURA
    "conservative": TradingConfig.get_conservative_config()
}

def get_config_for_strategy(strategy_name: str) -> Optional[TradingConfig]:
    """
    Obtiene la configuración recomendada para una estrategia específica
    
    Args:
        strategy_name: Nombre de la estrategia
        
    Returns:
        TradingConfig configurada para la estrategia o None si no existe
    """
    return STRATEGY_CONFIGS.get(strategy_name)