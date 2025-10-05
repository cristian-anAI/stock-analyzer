"""
Optimized Trading Configuration - Configuración optimizada basada en backtest real
Reduce overtrading, aumenta holding period, mejora scoring
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class OptimizedTradingConfig:
    """Configuración optimizada validada por análisis de backtest"""

    # STRATEGY MANAGEMENT
    active_strategy: str = "swing_trading_optimized"
    crypto_strategy: str = "competition"
    auto_strategy_switching: bool = False
    strategy_performance_threshold: float = 0.8

    # THRESHOLDS OPTIMIZADOS (reducir overtrading)
    buy_score_threshold: float = 6.5  # Aumentado de 6.0 → más selectivo
    sell_score_threshold: float = 5.5  # Aumentado de 4.5 → menos salidas prematuras

    # TRAILING STOP (nuevo sistema basado en precio, no score)
    use_trailing_stop: bool = True
    trailing_stop_percent: float = 5.0  # 5% trailing stop
    take_profit_percent: float = 15.0   # 15% take profit
    stop_loss_percent: float = 8.0      # 8% stop loss

    # Position Management (mismo que antes)
    max_position_value: float = 10000.0
    max_positions_stocks: int = 10
    max_positions_crypto: int = 6

    # HOLDING PERIOD OPTIMIZADO (aumentar de 2.1 días → 7-14 días)
    swing_min_hold_days: int = 7   # Mínimo 7 días (aumentado de 3)
    swing_max_hold_days: int = 30  # Máximo 30 días (aumentado de 20)

    # COOLDOWN para reducir overtrading (nuevo)
    symbol_cooldown_days: int = 7  # 7 días entre trades del mismo símbolo

    # SCORING SYSTEM (nuevo)
    use_improved_scoring: bool = True  # Usar ImprovedScoringService

    # Portfolio Allocation (mismo)
    liquid_capital_stocks: float = 70000.0
    liquid_capital_crypto: float = 30000.0

    # Strategy Flags
    short_trading_enabled: bool = False
    high_volatility_bypass: bool = True

    # Market Conditions
    use_database_scores: bool = False  # CAMBIO: calcular scores propios

    @classmethod
    def get_optimized_config(cls) -> 'OptimizedTradingConfig':
        """
        Retorna la configuración optimizada basada en análisis de backtest real
        Objetivo: Win rate >55%, Sharpe >1.0, <30 trades/año
        """
        return cls()

    @classmethod
    def get_conservative_config(cls) -> 'OptimizedTradingConfig':
        """Configuración aún más conservadora"""
        config = cls()
        config.buy_score_threshold = 7.0  # Muy selectivo
        config.max_position_value = 8000.0
        config.trailing_stop_percent = 4.0  # Stop más ajustado
        config.symbol_cooldown_days = 10   # Más cooldown
        return config

    @classmethod
    def get_aggressive_config(cls) -> 'OptimizedTradingConfig':
        """Configuración más agresiva (para testing)"""
        config = cls()
        config.buy_score_threshold = 6.0
        config.sell_score_threshold = 5.0
        config.trailing_stop_percent = 6.0  # Stop más amplio
        config.swing_min_hold_days = 5
        config.symbol_cooldown_days = 3
        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para logging"""
        return {
            'active_strategy': self.active_strategy,
            'buy_threshold': self.buy_score_threshold,
            'sell_threshold': self.sell_score_threshold,
            'trailing_stop': self.use_trailing_stop,
            'trailing_stop_pct': self.trailing_stop_percent,
            'min_hold_days': self.swing_min_hold_days,
            'max_hold_days': self.swing_max_hold_days,
            'cooldown_days': self.symbol_cooldown_days,
            'use_improved_scoring': self.use_improved_scoring,
            'max_position_value': self.max_position_value,
            'max_positions_stocks': self.max_positions_stocks
        }

# Configuración global optimizada
OPTIMIZED_TRADING_CONFIG = OptimizedTradingConfig.get_optimized_config()

# Configuraciones específicas
OPTIMIZED_CONFIG = OptimizedTradingConfig.get_optimized_config()
CONSERVATIVE_CONFIG = OptimizedTradingConfig.get_conservative_config()
AGGRESSIVE_CONFIG = OptimizedTradingConfig.get_aggressive_config()
