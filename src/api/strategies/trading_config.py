"""
Trading Configuration - Configuración unificada de estrategias
Centraliza todos los thresholds y parámetros para backtesting y autotrader
"""

from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class TradingConfig:
    """Configuración unificada de trading validada por backtesting"""
    
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
        return config
        
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para logging y debugging"""
        return {
            'buy_threshold': self.buy_score_threshold,
            'sell_threshold': self.sell_score_threshold,
            'max_position_value': self.max_position_value,
            'max_positions_stocks': self.max_positions_stocks,
            'short_enabled': self.short_trading_enabled,
            'volatility_bypass': self.high_volatility_bypass,
            'use_db_scores': self.use_database_scores
        }

# Configuración global por defecto
TRADING_CONFIG = TradingConfig.get_backtest_proven_config()

# Configuraciones específicas para diferentes modos
BACKTEST_CONFIG = TradingConfig.get_backtest_proven_config()
PRODUCTION_CONFIG = TradingConfig.get_backtest_proven_config()
CONSERVATIVE_CONFIG = TradingConfig.get_conservative_config()