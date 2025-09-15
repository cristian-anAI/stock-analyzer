"""
Strategy Usage Example - Ejemplo de uso del sistema flexible de estrategias
Demuestra cómo usar StrategyManager para switching fácil entre estrategias
"""

import logging
from typing import Dict, Any

from .strategy_manager import create_strategy_manager
from .strategy_registry import MarketType
from .trading_config import get_config_for_strategy

logger = logging.getLogger(__name__)

def demonstrate_strategy_switching():
    """
    Demuestra el uso básico del sistema de estrategias flexible
    """
    print("🔄 STRATEGY SWITCHING DEMONSTRATION")
    print("=" * 50)
    
    # Crear strategy manager
    strategy_manager = create_strategy_manager()
    
    # 1. Inicializar con estrategia recomendada para stocks
    print("\n1. Inicializando con estrategia recomendada para STOCKS...")
    success = strategy_manager.initialize_default_strategy(
        market_type=MarketType.STOCKS,
        risk_tolerance="MEDIUM"
    )
    
    if success:
        current = strategy_manager.get_current_strategy_name()
        print(f"✅ Estrategia inicial: {current}")
        
        # Obtener configuración de la estrategia actual
        strategy_instance = strategy_manager.get_current_strategy()
        if strategy_instance:
            config = strategy_instance.get_strategy_config()
            print(f"   Thresholds: Buy={config.get('buy_threshold')}, Sell={config.get('sell_threshold')}")
            print(f"   Timeframes: {config.get('timeframe_primary')}, {config.get('timeframe_confirmation')}")
    
    # 2. Listar estrategias disponibles
    print("\n2. Estrategias disponibles:")
    available = strategy_manager.get_available_strategies()
    for name, info in available.items():
        status = "🟢 CURRENT" if info['is_current'] else "⚪ Available"
        proven = "✅ PROVEN" if info['proven_backtesting'] else "🔶 Testing"
        print(f"   {status} {name}: {info['description']} [{proven}]")
        print(f"      Risk: {info['risk_level']} | Timeframes: {info['timeframes']}")
    
    # 3. Cambiar a crypto strategy
    print("\n3. Cambiando a Crypto Competition Strategy...")
    success = strategy_manager.switch_to_strategy(
        strategy_name="crypto_competition",
        reason="Testing crypto strategy",
        initiated_by="demo"
    )
    
    if success:
        current = strategy_manager.get_current_strategy_name()
        print(f"✅ Cambio exitoso: {current}")
        
        strategy_instance = strategy_manager.get_current_strategy()
        if strategy_instance:
            config = strategy_instance.get_strategy_config()
            print(f"   Thresholds: Buy={config.get('buy_threshold')}, Sell={config.get('sell_threshold')}")
            print(f"   Risk per trade: {config.get('risk_per_trade_percent')}%")
    
    # 4. Intentar cambiar a estrategia no implementada (multi_timeframe)
    print("\n4. Intentando cambiar a Multi-Timeframe Strategy (no implementada aún)...")
    success = strategy_manager.switch_to_strategy(
        strategy_name="multi_timeframe",
        reason="Testing MTSS",
        initiated_by="demo"
    )
    
    if not success:
        print("❌ Cambio falló: Estrategia no implementada aún")
        print("   (Esto es esperado - MTSS está en desarrollo)")
    
    # 5. Volver a estrategia probada
    print("\n5. Volviendo a estrategia probada en backtesting...")
    success = strategy_manager.reset_to_proven_strategy(MarketType.STOCKS)
    
    if success:
        current = strategy_manager.get_current_strategy_name()
        print(f"✅ Reset exitoso: {current}")
    
    # 6. Historial de cambios
    print("\n6. Historial de cambios de estrategia:")
    history = strategy_manager.get_switch_history(limit=10)
    for i, switch in enumerate(history, 1):
        print(f"   {i}. {switch['timestamp'][:19]}: {switch['from_strategy']} -> {switch['to_strategy']}")
        print(f"      Razón: {switch['reason']} (por: {switch['initiated_by']})")
    
    # 7. Performance summary
    print("\n7. Resumen de performance:")
    summary = strategy_manager.get_strategy_performance_summary()
    print(f"   Estrategia actual: {summary['current_strategy']}")
    print(f"   Total de cambios: {summary['total_switches']}")
    if summary['last_switch']:
        print(f"   Último cambio: {summary['last_switch'][:19]}")
    
    print(f"\n📊 Strategy Manager Status: {strategy_manager}")
    print("=" * 50)

def demonstrate_config_integration():
    """
    Demuestra integración con sistema de configuración
    """
    print("\n🔧 CONFIGURATION INTEGRATION DEMONSTRATION")
    print("=" * 50)
    
    # Mostrar configuraciones por estrategia
    from .trading_config import STRATEGY_CONFIGS
    
    print("Configuraciones disponibles por estrategia:")
    for strategy_name, config in STRATEGY_CONFIGS.items():
        print(f"\n📋 {strategy_name.upper()}:")
        config_dict = config.to_dict()
        print(f"   Buy Threshold: {config_dict['buy_threshold']}")
        print(f"   Sell Threshold: {config_dict['sell_threshold']}")
        print(f"   Max Position: ${config_dict['max_position_value']:,.0f}")
        print(f"   Use DB Scores: {config_dict['use_db_scores']}")
        
        if 'auto_switching' in config_dict:
            print(f"   Auto Switching: {config_dict['auto_switching']}")

def demonstrate_backtesting_integration():
    """
    Demuestra cómo integrar con sistema de backtesting
    """
    print("\n📈 BACKTESTING INTEGRATION EXAMPLE")
    print("=" * 50)
    
    print("Proceso recomendado para nueva estrategia:")
    print("1. Crear nueva estrategia heredando de BaseStrategy")
    print("2. Implementar calculate_score() y generate_signal()")
    print("3. Registrar en StrategyRegistry (activa=False)")
    print("4. Ejecutar backtesting con nueva estrategia")
    print("5. Si results > threshold: marcar como probada y activar")
    print("6. Usar StrategyManager.switch_to_strategy() en producción")
    
    # Ejemplo de código para backtesting
    print("\nEjemplo de código para backtesting:")
    print("""
    # En tu script de backtesting
    from src.api.strategies.strategy_registry import get_strategy_registry
    from src.api.strategies.strategy_manager import create_strategy_manager
    
    # Registrar nueva estrategia para testing
    registry = get_strategy_registry()
    registry.set_strategy_status("multi_timeframe", active=True)  # Activar temporalmente
    
    # Crear strategy manager y cambiar a nueva estrategia
    manager = create_strategy_manager()
    manager.switch_to_strategy("multi_timeframe", reason="Backtesting", initiated_by="backtest")
    
    # Ejecutar backtest...
    # Si win_rate > 80%:
    registry.mark_strategy_proven("multi_timeframe", proven=True)
    
    # Si win_rate < 60%:
    registry.set_strategy_status("multi_timeframe", active=False)
    """)

def demonstrate_autotrader_integration():
    """
    Demuestra cómo integrar con autotrader
    """
    print("\n🤖 AUTOTRADER INTEGRATION EXAMPLE")
    print("=" * 50)
    
    print("Integración recomendada con autotrader:")
    print("1. AutoTrader inicializa StrategyManager al arrancar")
    print("2. Lee estrategia activa desde TradingConfig")
    print("3. Evalúa performance cada N trades")
    print("4. Switch automático si performance < threshold")
    
    print("\nEjemplo de integración en autotrader_service.py:")
    print("""
    # En AutotraderService.__init__()
    self.strategy_manager = create_strategy_manager(self.config)
    self.strategy_manager.initialize_default_strategy(MarketType.STOCKS)
    
    # En cada ciclo de trading
    current_strategy = self.strategy_manager.get_current_strategy()
    signals = []
    for symbol in symbols:
        signal = current_strategy.generate_signal(symbol, price, data)
        signals.append(signal)
    
    # Cada 20 trades: evaluar performance
    if self.trades_since_evaluation >= 20:
        recent_trades = self.get_recent_trades(20)
        evaluation = self.strategy_manager.evaluate_strategy_performance(recent_trades)
        
        if evaluation.get("needs_switch") and evaluation.get("suggested_switch"):
            self.strategy_manager.switch_to_strategy(
                evaluation["suggested_switch"],
                reason=evaluation["switch_reason"],
                initiated_by="auto_optimization"
            )
    """)

if __name__ == "__main__":
    # Ejecutar demostraciones
    demonstrate_strategy_switching()
    demonstrate_config_integration()
    demonstrate_backtesting_integration() 
    demonstrate_autotrader_integration()
    
    print("\n✅ DEMONSTRATION COMPLETE")
    print("El sistema flexible de estrategias está listo para:")
    print("- Easy switching entre estrategias existentes")
    print("- Integración con backtesting para validar nuevas estrategias") 
    print("- Auto-switching basado en performance")
    print("- Futura implementación de Multi-Timeframe Scoring Strategy")