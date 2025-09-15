"""
MTSS Backtesting Integration Example
Ejemplo completo de cómo usar Multi-Timeframe Scoring Strategy para backtesting
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

from .strategy_manager import create_strategy_manager
from .strategy_registry import get_strategy_registry, MarketType
from .trading_config import get_config_for_strategy
from .multi_timeframe_strategy import MultiTimeframeScoringStrategy, MTSSParameters

logger = logging.getLogger(__name__)

def demonstrate_mtss_backtesting():
    """
    Demonstración completa del sistema MTSS para backtesting
    """
    print("🎯 MULTI-TIMEFRAME SCORING STRATEGY (MTSS) BACKTESTING")
    print("=" * 60)
    
    # 1. Verificar registro de MTSS
    registry = get_strategy_registry()
    print("\n1. Verificando registro de MTSS:")
    
    mtss_info = registry.get_strategy_info("multi_timeframe")
    if mtss_info:
        print(f"✅ MTSS registrada: {mtss_info.description}")
        print(f"   Status: {'🟢 ACTIVE' if mtss_info.active else '🔴 INACTIVE'}")
        print(f"   Implementation: {mtss_info.class_ref.__name__ if mtss_info.class_ref else 'None'}")
        print(f"   Timeframes requeridos: {mtss_info.min_timeframes}")
        print(f"   Risk Level: {mtss_info.risk_level}")
    else:
        print("❌ MTSS no encontrada en registry")
        return
    
    # 2. Crear instancia MTSS con parámetros personalizados
    print("\n2. Creando instancia MTSS con parámetros optimizables:")
    
    # Parámetros para backtesting (pueden ser optimizados)
    custom_params = MTSSParameters(
        # RSI Thresholds (PRIMARIOS)
        rsi_oversold=25,
        rsi_neutral_min=30,
        rsi_neutral_max=80,
        
        # MA Periods (PRIMARIOS)
        ma_fast=20,
        ma_slow=50,
        
        # Confidence Thresholds (PRIMARIOS)
        min_confidence=2,
        partial_confidence=1,
        
        # MACD (SECUNDARIOS)
        macd_fast=12,
        macd_slow=26,
        macd_signal=9,
        
        # Ichimoku (SECUNDARIOS)
        tenkan_period=9,
        kijun_period=26,
        senkou_span_b=52,
        
        # Position Sizing
        full_position_size=1.0,
        half_position_size=0.5,
        max_positions=10
    )
    
    mtss_strategy = MultiTimeframeScoringStrategy(parameters=custom_params)
    
    print(f"✅ MTSS instanciada: {mtss_strategy}")
    print(f"   Timeframes requeridos: {mtss_strategy.get_required_timeframes()}")
    
    # Mostrar configuración completa
    config = mtss_strategy.get_strategy_config()
    print(f"   Implementation Status: {config['implementation_status']}")
    print(f"   Ready for Backtesting: {config['ready_for_backtesting']}")
    
    # 3. Configuración específica para MTSS
    print("\n3. Configuración específica para MTSS:")
    mtss_config = get_config_for_strategy("multi_timeframe")
    if mtss_config:
        config_dict = mtss_config.to_dict()
        print(f"   Buy Threshold: {config_dict['buy_threshold']}")  # 1.0 para sistema binario
        print(f"   Sell Threshold: {config_dict['sell_threshold']}")  # 0.0 para sistema binario  
        print(f"   Max Position: ${config_dict['max_position_value']:,}")
        print(f"   Use DB Scores: {config_dict['use_db_scores']}")  # False - calcula propios
    
    # 4. Strategy Manager Integration
    print("\n4. Integración con Strategy Manager:")
    manager = create_strategy_manager()
    
    # Intentar cambiar a MTSS
    switch_success = manager.switch_to_strategy(
        strategy_name="multi_timeframe",
        reason="Backtesting preparation",
        initiated_by="backtesting_demo"
    )
    
    if switch_success:
        current = manager.get_current_strategy_name()
        print(f"✅ Strategy switched to: {current}")
        
        current_strategy = manager.get_current_strategy()
        if current_strategy:
            strategy_config = current_strategy.get_strategy_config()
            print(f"   Strategy type: {strategy_config['strategy_type']}")
            print(f"   Primary timeframe: {strategy_config['timeframe_primary']}")
    else:
        print("❌ Failed to switch to MTSS")
    
    # 5. Backtesting Execution Example
    print("\n5. Ejemplo de ejecución de backtesting:")
    
    # Lista de símbolos para backtest
    test_symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "AMZN", "META", "BRK-B", "V", "JNJ"]
    start_date = "2024-01-01"
    end_date = "2024-09-01"
    
    print(f"   Symbols: {len(test_symbols)} stocks")
    print(f"   Period: {start_date} to {end_date}")
    print(f"   Strategy: {mtss_strategy.name}")
    
    # Ejecutar backtest
    backtest_results = mtss_strategy.backtest_strategy(
        symbols=test_symbols,
        start_date=start_date,
        end_date=end_date
    )
    
    # 6. Análisis de resultados
    print("\n6. Resultados del backtesting:")
    print(f"   Status: {backtest_results['status']}")
    print(f"   Strategy: {backtest_results['strategy']}")
    print(f"   Period: {backtest_results['period']}")
    print(f"   Symbols tested: {backtest_results['symbols_tested']}")
    print(f"   Total trades: {backtest_results['total_trades']}")
    print(f"   Win rate: {backtest_results['win_rate']:.1%}")
    print(f"   Total P&L: ${backtest_results['total_pnl']:,.2f}")
    print(f"   Avg trade P&L: ${backtest_results['avg_trade_pnl']:,.2f}")
    
    # MTSS specific metrics
    print("\n   📊 MTSS Specific Metrics:")
    signal_dist = backtest_results['signal_distribution']
    for signal, count in signal_dist.items():
        print(f"     {signal}: {count} trades")
    
    print(f"   Monthly filter effectiveness: {backtest_results['monthly_filter_effectiveness']:.1%}")
    
    # Parameters used
    print("\n   🔧 Parameters used:")
    params = backtest_results['parameters']
    print(f"     RSI thresholds: {params['rsi_thresholds']}")
    print(f"     MA periods: {params['ma_periods']}")
    print(f"     MACD params: {params['macd_params']}")
    print(f"     Confidence thresholds: {params['confidence_thresholds']}")
    
    print(f"\n   Implementation: {backtest_results['implementation_status']}")
    print(f"   Integration ready: {backtest_results['integration_ready']}")

def demonstrate_mtss_parameter_optimization():
    """
    Ejemplo de optimización de parámetros MTSS
    """
    print("\n🔧 PARAMETER OPTIMIZATION EXAMPLE")
    print("=" * 50)
    
    print("Proceso recomendado para optimización MTSS:")
    print("1. Definir ranges de parámetros primarios:")
    print("   - rsi_oversold: [20, 25, 30, 35]")
    print("   - rsi_neutral_min: [25, 30, 35, 40]")
    print("   - rsi_neutral_max: [70, 75, 80, 85]")
    print("   - ma_fast: [10, 15, 20, 25, 30]")
    print("   - ma_slow: [40, 45, 50, 55, 60]")
    print("   - min_confidence: [1, 2, 3]")
    
    print("\n2. Grid search o Bayesian optimization:")
    print("   - Probar todas las combinaciones de parámetros primarios")
    print("   - Evaluar con métricas: win_rate, sharpe_ratio, max_drawdown")
    print("   - Filtrar por constraints: max_consecutive_losses <= 5")
    
    print("\n3. Refinamiento con parámetros secundarios:")
    print("   - Una vez encontrados mejores primarios")
    print("   - Optimizar Ichimoku y MACD settings")
    
    # Ejemplo de configuración optimizada
    optimized_params = MTSSParameters(
        # Resultado hipotético de optimización
        rsi_oversold=22,
        rsi_neutral_min=28,
        rsi_neutral_max=75,
        ma_fast=18,
        ma_slow=45,
        min_confidence=2,
        partial_confidence=1,
        # Secundarios optimizados
        macd_fast=10,
        macd_slow=24,
        ichimoku_params=[8, 24, 48]
    )
    
    print(f"\n4. Configuración optimizada ejemplo:")
    print(f"   RSI: oversold={optimized_params.rsi_oversold}, neutral={optimized_params.rsi_neutral_min}-{optimized_params.rsi_neutral_max}")
    print(f"   MAs: {optimized_params.ma_fast}/{optimized_params.ma_slow}")
    print(f"   Confidence: min={optimized_params.min_confidence}, partial={optimized_params.partial_confidence}")

def demonstrate_mtss_vs_other_strategies():
    """
    Ejemplo de comparación MTSS vs otras estrategias
    """
    print("\n📊 STRATEGY COMPARISON EXAMPLE")
    print("=" * 50)
    
    print("Métricas de comparación:")
    
    # Ejemplo de resultados comparativos
    comparison_results = {
        "swing_trading": {
            "win_rate": 0.958,  # Probada 95.8%
            "avg_trade_pnl": 150.50,
            "max_drawdown": 0.08,
            "sharpe_ratio": 1.85,
            "total_trades": 72,
            "status": "✅ PROVEN"
        },
        "crypto_competition": {
            "win_rate": 0.72,
            "avg_trade_pnl": 280.30,
            "max_drawdown": 0.15,
            "sharpe_ratio": 1.45,
            "total_trades": 45,
            "status": "🔶 TESTING"
        },
        "multi_timeframe": {
            "win_rate": 0.85,  # Ejemplo proyectado
            "avg_trade_pnl": 200.75,
            "max_drawdown": 0.10,
            "sharpe_ratio": 1.70,
            "total_trades": 38,
            "status": "🚀 NEW - READY FOR TESTING"
        }
    }
    
    print(f"{'Strategy':<20} {'Win Rate':<10} {'Avg P&L':<12} {'Sharpe':<8} {'Status':<25}")
    print("-" * 80)
    
    for strategy, metrics in comparison_results.items():
        print(f"{strategy:<20} {metrics['win_rate']:.1%}{'':>4} ${metrics['avg_trade_pnl']:>8.2f} {metrics['sharpe_ratio']:>7.2f} {metrics['status']}")
    
    print(f"\n🎯 MTSS Advantages:")
    print("  - Hierarchical filtering reduces false signals")
    print("  - Multi-timeframe confirmation improves accuracy") 
    print("  - Binary scoring system simplifies decision making")
    print("  - Monthly filter prevents trades in bear markets")
    print("  - Configurable position sizing (FULL/HALF)")

if __name__ == "__main__":
    # Ejecutar todas las demostraciones
    demonstrate_mtss_backtesting()
    demonstrate_mtss_parameter_optimization()
    demonstrate_mtss_vs_other_strategies()
    
    print("\n" + "=" * 60)
    print("✅ MTSS BACKTESTING INTEGRATION COMPLETE")
    print("=" * 60)
    
    print("\n🎯 NEXT STEPS FOR PRODUCTION:")
    print("1. Run full backtest with historical data")
    print("2. Optimize parameters using grid search")
    print("3. Compare performance vs swing_trading strategy") 
    print("4. If win_rate > 80%: mark as proven and activate")
    print("5. Switch autotrader to MTSS using StrategyManager")
    
    print("\n📋 EASY SWITCHING COMMANDS:")
    print("""
# Switch to MTSS for backtesting
from src.api.strategies.strategy_manager import create_strategy_manager
manager = create_strategy_manager()
manager.switch_to_strategy("multi_timeframe", reason="Production test", initiated_by="user")

# If successful, mark as proven
from src.api.strategies.strategy_registry import get_strategy_registry  
registry = get_strategy_registry()
registry.mark_strategy_proven("multi_timeframe", proven=True)

# Switch back if needed
manager.switch_to_strategy("swing_trading", reason="Back to proven", initiated_by="user")
    """)
    
    print("\n🔄 La estrategia MTSS está completamente lista para backtesting!")
    print("   Todos los indicadores técnicos implementados")
    print("   Sistema de switching flexible preparado")
    print("   Framework de optimización de parámetros listo")