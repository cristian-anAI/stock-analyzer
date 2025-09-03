#!/usr/bin/env python3
"""
Implementar estrategia refinada basada en análisis real de performance
- Solo LONGs (eliminar SHORTs temporalmente)
- Enfoque en top performers
- Backtesting de 1 año completo
"""

import yfinance as yf
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import json
import time

class RefinedStrategyImplementation:
    def __init__(self):
        self.db_path = 'trading.db'
        
        # REFINED STRATEGY - Solo LONGs basado en datos reales
        self.buy_long_threshold = 6.0      # Mantener - funciona a 60 días
        self.sell_long_threshold = 4.0     # Mantener
        self.short_enabled = False         # ELIMINAR SHORTs temporalmente
        
        # Portfolio settings optimizado
        self.initial_capital = 100000      # $100k
        self.max_position_value = 12500    # $12.5k por posición (8 posiciones max)
        self.max_positions = 8             # Enfoque en top performers
        
        # Backtesting extendido
        self.lookback_days = 365          # 1 AÑO COMPLETO
        self.commission = 0.001
        
        # Top performers identificados
        self.preferred_stocks = ['INTC', 'AVGO', 'MU', 'AMD', 'TSLA', 'NVDA', 'ORCL', 'TSM']
        
        self.results = {}
        self.trades = []
        self.portfolio_history = []
        
    def update_autotrader_config(self):
        """Actualizar configuración del autotrader en el código"""
        
        print("ACTUALIZANDO CONFIGURACIÓN AUTOTRADER")
        print("=" * 50)
        
        config_changes = f"""
CAMBIOS A IMPLEMENTAR EN src/api/services/autotrader_service.py:

1. CONFIGURACIÓN PRINCIPAL (líneas 37-41):
   ANTES:
   self.buy_score_threshold = 6.0
   
   DESPUÉS:
   self.buy_score_threshold = 6.0  # Mantener - funciona bien a 60 días
   self.short_trading_enabled = False  # DESHABILITAR SHORTs temporalmente
   self.max_position_value = 12500  # Aumentar a $12.5k por posición
   self.max_total_positions = 8  # Reducir a 8 posiciones enfocadas

2. LÓGICA DE SHORTS (líneas ~270-280 y ~670-680):
   COMENTAR O DESHABILITAR:
   # Deshabilitar temporalmente SHORTs
   # if score < 1.8:  # Comentar esta lógica
   #     return None   # No ejecutar SHORTs

3. PRIORIZACIÓN DE STOCKS:
   Priorizar: {', '.join(self.preferred_stocks)}
   (Basado en performance real de 60 días: 83.3% win rate, +14.47% promedio)
"""
        
        print(config_changes)
        return config_changes
    
    def get_refined_stocks(self) -> List[str]:
        """Obtener stocks refinados para la nueva estrategia"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Priorizar top performers, luego otros con score >= 6.0
        cursor.execute("""
            SELECT symbol FROM stocks 
            WHERE market_cap > 50000000000 AND score >= 6.0
            ORDER BY 
                CASE WHEN symbol IN ('INTC', 'AVGO', 'MU', 'AMD', 'TSLA', 'NVDA', 'ORCL', 'TSM') THEN 0 ELSE 1 END,
                score DESC,
                market_cap DESC
        """)
        
        stocks = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        print(f"Selected {len(stocks)} stocks for REFINED strategy")
        print(f"Top performers prioritized: {self.preferred_stocks}")
        
        return stocks
    
    def calculate_improved_score(self, data: Dict) -> float:
        """Scoring mejorado basado en análisis de performance real"""
        try:
            close_prices = data['Close']
            if len(close_prices) < 60:  # Necesitamos más historia para mejor análisis
                return 5.0
            
            # Análisis de múltiples timeframes (basado en win rates reales)
            recent_5d = close_prices[-5:].mean()
            medium_20d = close_prices[-20:].mean()
            long_60d = close_prices[-60:].mean()
            
            # Performance trends
            short_trend = (recent_5d / medium_20d - 1) * 100
            long_trend = (medium_20d / long_60d - 1) * 100
            
            # Volatility analysis
            returns = close_prices.pct_change().dropna()
            volatility_20d = returns[-20:].std() * np.sqrt(252) * 100
            volatility_60d = returns[-60:].std() * np.sqrt(252) * 100
            
            # Volume analysis
            volumes = data['Volume']
            recent_vol = volumes[-10:].mean()
            avg_vol = volumes[-60:].mean()
            volume_trend = (recent_vol / avg_vol - 1) * 100 if avg_vol > 0 else 0
            
            # Base score
            score = 5.0
            
            # Long-term trend (más peso - basado en win rate 83.3% a 60 días)
            if long_trend > 10:
                score += 2.5
            elif long_trend > 5:
                score += 1.5
            elif long_trend > 0:
                score += 0.5
            elif long_trend < -10:
                score -= 2.0
            elif long_trend < -5:
                score -= 1.0
            
            # Short-term momentum
            if short_trend > 5:
                score += 1.0
            elif short_trend > 2:
                score += 0.5
            elif short_trend < -5:
                score -= 1.0
            elif short_trend < -2:
                score -= 0.5
            
            # Volatility factor (penalizar alta volatilidad)
            if volatility_60d > 40:
                score -= 1.5
            elif volatility_60d > 30:
                score -= 1.0
            elif volatility_60d < 20:
                score += 0.5
            
            # Volume confirmation
            if volume_trend > 30:
                score += 0.5
            elif volume_trend < -30:
                score -= 0.5
            
            # Consistency bonus (volatilidad estable es buena)
            vol_stability = abs(volatility_60d - volatility_20d)
            if vol_stability < 5:
                score += 0.3
            
            return max(0.0, min(10.0, score))
            
        except Exception as e:
            return 5.0
    
    def fetch_extended_data(self, symbol: str) -> pd.DataFrame:
        """Obtener datos históricos de 1 año + buffer"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days + 60)  # +60 días buffer
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date)
            
            if data.empty or len(data) < 200:  # Necesitamos datos suficientes
                return None
            
            return data
            
        except Exception as e:
            return None
    
    def simulate_refined_strategy(self, stocks: List[str]) -> Dict:
        """Ejecutar backtesting de 1 año con estrategia refinada"""
        
        print(f"BACKTESTING ESTRATEGIA REFINADA - 1 AÑO COMPLETO")
        print(f"=" * 70)
        print(f"CONFIGURACIÓN REFINADA:")
        print(f"  Strategy: SOLO LONGs (SHORTs deshabilitados)")
        print(f"  BUY LONG: >= {self.buy_long_threshold}")
        print(f"  SELL LONG: <= {self.sell_long_threshold}")
        print(f"  Capital inicial: ${self.initial_capital:,}")
        print(f"  Max posiciones: {self.max_positions}")
        print(f"  Capital por posición: ${self.max_position_value:,}")
        print(f"  Período: {self.lookback_days} días (1 año)")
        print(f"  Top performers prioritized: {len(self.preferred_stocks)}")
        
        # Portfolio state
        cash = self.initial_capital
        positions = {}
        daily_portfolio_value = []
        
        # Date range - 1 AÑO COMPLETO
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.lookback_days)
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        print(f"\nSimulación: {start_date.date()} a {end_date.date()}")
        
        # Fetch data - enfoque en top performers y candidatos
        stock_data = {}
        successful_fetches = 0
        
        print(f"\nObteniendo datos históricos de 1 año...")
        
        # Priorizar top performers + otros candidatos (máximo 30 para tiempo razonable)
        prioritized_stocks = []
        for stock in self.preferred_stocks:
            if stock in stocks:
                prioritized_stocks.append(stock)
        
        # Agregar otros hasta 30 total
        for stock in stocks:
            if stock not in prioritized_stocks and len(prioritized_stocks) < 30:
                prioritized_stocks.append(stock)
        
        for i, symbol in enumerate(prioritized_stocks):
            if i % 5 == 0:
                print(f"  Progress: {i}/{len(prioritized_stocks)} stocks")
            
            data = self.fetch_extended_data(symbol)
            if data is not None:
                stock_data[symbol] = data
                successful_fetches += 1
            
            time.sleep(0.05)  # Rate limiting
        
        print(f"Datos obtenidos exitosamente: {successful_fetches} stocks")
        
        if successful_fetches < 5:
            print("ERROR: Datos insuficientes para backtesting")
            return {}
        
        # Simulación diaria - 1 año completo
        print(f"\nEjecutando simulación diaria (365 días)...")
        
        for day_idx, current_date in enumerate(date_range):
            if day_idx % 30 == 0:  # Update cada 30 días
                print(f"  Mes {day_idx//30 + 1}/12: {current_date.date()}")
            
            daily_signals = []
            
            # Analizar stocks con estrategia REFINADA
            for symbol in stock_data.keys():
                try:
                    data_subset = stock_data[symbol][stock_data[symbol].index <= current_date]
                    
                    if len(data_subset) < 60:  # Necesitamos más historia
                        continue
                    
                    # Usar scoring mejorado
                    score = self.calculate_improved_score(data_subset)
                    current_price = data_subset['Close'].iloc[-1]
                    
                    # SOLO LONGS - SHORTs deshabilitados
                    if score >= self.buy_long_threshold and symbol not in positions:
                        priority = 0 if symbol in self.preferred_stocks else 1
                        daily_signals.append({
                            'symbol': symbol,
                            'action': 'BUY_LONG',
                            'score': score,
                            'price': current_price,
                            'date': current_date,
                            'priority': priority
                        })
                    elif score <= self.sell_long_threshold and symbol in positions:
                        daily_signals.append({
                            'symbol': symbol,
                            'action': 'SELL_LONG',
                            'score': score,
                            'price': current_price,
                            'date': current_date,
                            'priority': priority
                        })
                        
                except Exception as e:
                    continue
            
            # Ejecutar trades - priorizar top performers
            daily_signals.sort(key=lambda x: (x['priority'], -x['score']))
            
            for signal in daily_signals:
                if signal['action'] == 'BUY_LONG':
                    if len(positions) < self.max_positions and cash > self.max_position_value:
                        # Asignación más agresiva para estrategia enfocada
                        investment = min(self.max_position_value, cash * 0.2)  # Hasta 20% por posición
                        shares = investment / signal['price']
                        cost = shares * signal['price'] * (1 + self.commission)
                        
                        if cost <= cash:
                            cash -= cost
                            positions[signal['symbol']] = {
                                'shares': shares,
                                'entry_price': signal['price'],
                                'entry_date': signal['date'],
                                'type': 'LONG'
                            }
                            
                            self.trades.append({
                                'symbol': signal['symbol'],
                                'action': 'BUY_LONG',
                                'shares': shares,
                                'price': signal['price'],
                                'date': signal['date'],
                                'score': signal['score'],
                                'priority': 'TOP' if signal['symbol'] in self.preferred_stocks else 'OTHER'
                            })
                
                elif signal['action'] == 'SELL_LONG':
                    if signal['symbol'] in positions:
                        pos = positions[signal['symbol']]
                        proceeds = pos['shares'] * signal['price'] * (1 - self.commission)
                        cash += proceeds
                        
                        # Calculate P&L
                        entry_value = pos['shares'] * pos['entry_price']
                        pnl = proceeds - entry_value
                        pnl_pct = (pnl / entry_value) * 100
                        days_held = (signal['date'] - pos['entry_date']).days
                        
                        self.trades.append({
                            'symbol': signal['symbol'],
                            'action': 'SELL_LONG',
                            'shares': pos['shares'],
                            'price': signal['price'],
                            'date': signal['date'],
                            'score': signal['score'],
                            'pnl': pnl,
                            'pnl_pct': pnl_pct,
                            'days_held': days_held,
                            'priority': 'TOP' if signal['symbol'] in self.preferred_stocks else 'OTHER'
                        })
                        
                        del positions[signal['symbol']]
            
            # Calcular valor diario del portfolio
            portfolio_value = cash
            for symbol, pos in positions.items():
                try:
                    current_data = stock_data[symbol][stock_data[symbol].index <= current_date]
                    if len(current_data) > 0:
                        current_price = current_data['Close'].iloc[-1]
                        portfolio_value += pos['shares'] * current_price
                except:
                    # Use entry price if current data unavailable
                    portfolio_value += pos['shares'] * pos['entry_price']
            
            daily_portfolio_value.append({
                'date': current_date,
                'value': portfolio_value,
                'cash': cash,
                'positions': len(positions)
            })
        
        # Liquidar posiciones restantes al final
        print(f"\nLiquidando posiciones finales...")
        for symbol, pos in list(positions.items()):
            try:
                final_data = stock_data[symbol]
                final_price = final_data['Close'].iloc[-1]
                proceeds = pos['shares'] * final_price * (1 - self.commission)
                cash += proceeds
                
                entry_value = pos['shares'] * pos['entry_price']
                pnl = proceeds - entry_value
                pnl_pct = (pnl / entry_value) * 100
                days_held = (end_date - pos['entry_date']).days
                
                self.trades.append({
                    'symbol': symbol,
                    'action': 'FINAL_SELL',
                    'shares': pos['shares'],
                    'price': final_price,
                    'date': end_date,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'days_held': days_held,
                    'priority': 'TOP' if symbol in self.preferred_stocks else 'OTHER'
                })
                
            except Exception as e:
                print(f"Error liquidating {symbol}: {e}")
        
        # Calcular resultado final
        final_value = cash
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        
        print(f"\nBACKTESTING 1 AÑO COMPLETADO!")
        print(f"  Capital inicial: ${self.initial_capital:,}")
        print(f"  Capital final: ${final_value:,.2f}")
        print(f"  Retorno total: {total_return:+.2f}%")
        print(f"  Total trades: {len(self.trades)}")
        
        return {
            'strategy': 'REFINED_LONGS_ONLY',
            'period_days': self.lookback_days,
            'initial_capital': self.initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'total_trades': len(self.trades),
            'stocks_analyzed': len(stock_data),
            'daily_values': daily_portfolio_value,
            'trades': self.trades,
            'preferred_stocks': self.preferred_stocks,
            'config': {
                'buy_threshold': self.buy_long_threshold,
                'sell_threshold': self.sell_long_threshold,
                'shorts_enabled': self.short_enabled,
                'max_positions': self.max_positions,
                'position_size': self.max_position_value
            }
        }

def main():
    print("IMPLEMENTACIÓN DE ESTRATEGIA REFINADA")
    print("Basada en análisis real de performance")
    print("=" * 60)
    
    refiner = RefinedStrategyImplementation()
    
    # 1. Mostrar cambios de configuración
    config_changes = refiner.update_autotrader_config()
    
    # 2. Obtener stocks refinados
    stocks = refiner.get_refined_stocks()
    
    if len(stocks) < 5:
        print("ERROR: Stocks insuficientes")
        return
    
    # 3. Ejecutar backtesting de 1 año
    results = refiner.simulate_refined_strategy(stocks)
    
    if not results:
        print("ERROR: Backtesting failed")
        return
    
    # 4. Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = f"reports/refined_strategy_1year_{timestamp}.json"
    
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # 5. Generar reporte
    print(f"\n" + "=" * 60)
    print("RESULTADOS ESTRATEGIA REFINADA - 1 AÑO")
    print("=" * 60)
    
    # Analizar trades
    completed_trades = [t for t in results['trades'] if 'pnl' in t]
    top_performer_trades = [t for t in completed_trades if t.get('priority') == 'TOP']
    
    if completed_trades:
        win_trades = [t for t in completed_trades if t['pnl'] > 0]
        win_rate = len(win_trades) / len(completed_trades) * 100
        avg_pnl = np.mean([t['pnl'] for t in completed_trades])
        avg_days = np.mean([t['days_held'] for t in completed_trades])
        
        print(f"PERFORMANCE MÉTRICAS:")
        print(f"  Total return: {results['total_return']:+.2f}%")
        print(f"  Trades completados: {len(completed_trades)}")
        print(f"  Win rate: {win_rate:.1f}%")
        print(f"  P&L promedio: ${avg_pnl:+.2f}")
        print(f"  Días promedio: {avg_days:.1f}")
        
        if top_performer_trades:
            top_win_rate = len([t for t in top_performer_trades if t['pnl'] > 0]) / len(top_performer_trades) * 100
            top_avg_pnl = np.mean([t['pnl'] for t in top_performer_trades])
            
            print(f"\nTOP PERFORMERS ({len(refiner.preferred_stocks)} stocks):")
            print(f"  Trades: {len(top_performer_trades)}")
            print(f"  Win rate: {top_win_rate:.1f}%")
            print(f"  P&L promedio: ${top_avg_pnl:+.2f}")
    
    print(f"\nArchivos generados:")
    print(f"  Datos: {json_file}")
    print(f"\nEstrategia refinada lista para implementación!")

if __name__ == "__main__":
    main()