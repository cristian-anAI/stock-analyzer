#!/usr/bin/env python3
"""
Documenta TODAS las reglas que sigue el autotrader para backtesting
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.api.services.autotrader_service import AutotraderService
from src.api.strategies.swing_trading_strategy import SwingTradingStrategy
from src.api.strategies.trading_config import TRADING_CONFIG

def analyze_autotrader_rules():
    print("DOCUMENTACIÓN COMPLETA DE REGLAS DEL AUTOTRADER")
    print("="*80)
    
    # Crear instancias
    autotrader = AutotraderService()
    swing_strategy = SwingTradingStrategy()
    config = TRADING_CONFIG
    
    print("\n1. CONFIGURACIÓN PRINCIPAL:")
    print("-"*40)
    print(f"  Buy Score Threshold: {config.buy_score_threshold}")
    print(f"  Sell Score Threshold: {config.sell_score_threshold}")
    print(f"  Max Position Value: ${config.max_position_value:,.2f}")
    print(f"  Max Positions Stocks: {config.max_positions_stocks}")
    print(f"  Stop Loss %: {config.stop_loss_percent}%")
    print(f"  Take Profit %: {config.take_profit_percent}%")
    print(f"  Use Database Scores: {config.use_database_scores}")
    
    print(f"\n2. SWING STRATEGY ESPECÍFICA:")
    print("-"*40)
    print(f"  Min Hold Days: {swing_strategy.min_hold_days}")
    print(f"  Max Hold Days: {swing_strategy.max_hold_days}")
    print(f"  Strategy Type: {type(swing_strategy).__name__}")
    
    print(f"\n3. MARKET TIMING RESTRICTIONS:")
    print("-"*40)
    timing_service = autotrader.market_timing
    print(f"  BUY Restriction: {timing_service.buy_restriction_minutes} minutes after open")
    print(f"  SELL Restriction: {timing_service.sell_restriction_minutes} minutes after open")
    print(f"  Market Hours: {timing_service.market_open} - {timing_service.market_close} ET")
    
    print(f"\n4. CICLO DE TRADING (run_trading_cycle):")
    print("-"*40)
    print("  4.1. VALIDACIONES INICIALES:")
    print("    - Market timing check (is_market_open)")
    print("    - Portfolio risk limits")
    print("    - Volatility service check")
    
    print("\n  4.2. ANÁLISIS DE POSICIONES EXISTENTES:")
    print("    - Check each position for exit criteria")
    print("    - Call strategy.should_exit_position()")
    print("    - Execute sell if exit criteria met")
    
    print("\n  4.3. BÚSQUEDA DE NUEVAS OPORTUNIDADES:")
    print("    - Filter stocks/crypto by score >= buy_threshold")
    print("    - Apply overtrading prevention")
    print("    - Check position limits")
    print("    - Execute buy if criteria met")

def analyze_exit_criteria():
    print(f"\n5. CRITERIOS DE SALIDA (CRITICAL!):")
    print("-"*40)
    
    swing_strategy = SwingTradingStrategy()
    
    print("  5.1. SWING TRADING STRATEGY EXIT LOGIC:")
    print("    - should_exit_position() method")
    
    # Verificar si el fix se aplicó
    try:
        # Test con valores mock
        should_exit, reason = swing_strategy.should_exit_position(
            symbol="TEST", 
            entry_price=100.0, 
            current_price=102.0,
            days_held=1,
            position_side="LONG",
            data=None
        )
        
        print(f"    - TEST (day 1, +2%): should_exit={should_exit}, reason='{reason}'")
        
        if "SWING HOLD" in reason:
            print("    ✓ FIX APLICADO: Minimum hold period enforced")
        else:
            print("    ❌ FIX NO APLICADO: Still using old logic")
            
    except Exception as e:
        print(f"    ❌ ERROR testing exit logic: {e}")
    
    print("\n  5.2. BASE STRATEGY EXIT CRITERIA (si no overridden):")
    print("    - Stop loss: >= 8.0% loss")
    print("    - Take profit: >= 15.0% profit") 
    print("    - Max hold period: >= max_hold_days")
    print("    - Score drops below sell_threshold (4.5)")
    
    print("\n  5.3. ANÁLISIS DEL PROBLEMA ACTUAL:")
    print("    - Ventas con razón 'Score dropped to X.X'")
    print("    - Esto indica que Base Strategy exit logic se está usando")
    print("    - El fix de SwingTradingStrategy no se aplicó o no funciona")

def analyze_buy_criteria():
    print(f"\n6. CRITERIOS DE COMPRA:")
    print("-"*40)
    
    print("  6.1. FILTROS PRINCIPALES:")
    print("    - Score >= 6.0 (buy_score_threshold)")
    print("    - Market timing: No BUY primeros 15min después de apertura")
    print("    - Portfolio limits: Max 10 posiciones stocks")
    print("    - Position value: $10,000 per position")
    
    print("\n  6.2. SWING STRATEGY SIGNAL GENERATION:")
    print("    - generate_signal() method")
    print("    - Database scores vs calculated scores")
    print("    - Technical indicators: RSI, MACD, volume")
    print("    - Multi-timeframe confirmation")
    
    print("\n  6.3. OVERTRADING PREVENTION:")
    print("    - Prevent same symbol multiple times per day")
    print("    - Risk management checks")

def identify_backtest_gaps():
    print(f"\n7. GAPS ENTRE AUTOTRADER Y BACKTESTING:")
    print("-"*40)
    
    print("  7.1. PROBLEMAS IDENTIFICADOS:")
    print("    ❌ Backtesting no incluye market timing restrictions")
    print("    ❌ Backtesting no usa swing trading exit logic")
    print("    ❌ Backtesting no simula ciclos de 5 minutos")
    print("    ❌ Backtesting no incluye overtrading prevention")
    print("    ❌ Backtesting no simula volatility service checks")
    
    print("\n  7.2. REGLAS QUE FALTAN EN BACKTESTING:")
    print("    - 15min BUY restriction after market open")
    print("    - 60min SELL restriction after market open")
    print("    - 3-day minimum hold period (si fix aplicado)")
    print("    - Score-based exits every 5 minutes")
    print("    - Position sizing exact ($10K per position)")
    print("    - Database score usage vs calculated scores")

def generate_recommendations():
    print(f"\n8. RECOMENDACIONES PARA ARREGLAR BACKTESTING:")
    print("-"*40)
    
    print("  8.1. INMEDIATO:")
    print("    1. Verificar que el fix de SwingTradingStrategy esté funcionando")
    print("    2. Reiniciar el backend para aplicar cambios")
    print("    3. Confirmar que minimum hold period se respeta")
    
    print("\n  8.2. PARA BACKTESTING ACCURATE:")
    print("    1. Implementar market timing en backtesting")
    print("    2. Usar misma exit logic (SwingTradingStrategy)")
    print("    3. Simular ciclos de 5 minutos con score checks")
    print("    4. Incluir all restrictions y validaciones")
    print("    5. Usar database scores, no calculated")

if __name__ == "__main__":
    analyze_autotrader_rules()
    analyze_exit_criteria()
    analyze_buy_criteria() 
    identify_backtest_gaps()
    generate_recommendations()