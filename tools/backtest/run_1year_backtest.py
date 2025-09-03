#!/usr/bin/env python3
"""
Ejecutar backtesting de 1 año - solo generar archivos de salida
"""

import yfinance as yf
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
import json
import time

class OneYearBacktest:
    def __init__(self):
        self.db_path = 'trading.db'
        self.buy_long_threshold = 5.8
        self.sell_long_threshold = 4.5
        self.initial_capital = 100000
        self.max_position_value = 10000
        self.max_positions = 10
        self.lookback_days = 365
        self.commission = 0.001
        self.trades = []
        
    def get_stocks_for_backtest(self) -> List[str]:
        """Obtener stocks para backtesting"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT symbol FROM stocks 
            WHERE market_cap > 50000000000 AND score >= 5.0
            ORDER BY market_cap DESC
        """)
        
        stocks = [row[0] for row in cursor.fetchall()]
        conn.close()
        return stocks
    
    def calculate_score(self, data: Dict) -> float:
        """Scoring dinámico mejorado"""
        try:
            close_prices = data['Close']
            if len(close_prices) < 20:
                return 5.0
            
            # Múltiples períodos de momentum
            momentum_5 = (close_prices[-5:].mean() / close_prices[-10:-5].mean() - 1) * 100
            momentum_10 = (close_prices[-10:].mean() / close_prices[-20:].mean() - 1) * 100
            momentum_20 = (close_prices[-20:].mean() / close_prices[-40:].mean() - 1) * 100 if len(close_prices) >= 40 else 0
            
            # RSI simplificado
            returns = close_prices.pct_change().dropna()
            recent_returns = returns[-14:] if len(returns) >= 14 else returns
            gains = recent_returns[recent_returns > 0].sum()
            losses = abs(recent_returns[recent_returns < 0].sum())
            rsi = 100 - (100 / (1 + (gains / (losses + 0.0001))))
            
            # Volatilidad
            volatility = returns[-20:].std() * np.sqrt(252) * 100 if len(returns) >= 20 else 30
            
            # Score base
            score = 5.0
            
            # Momentum scoring (más granular)
            if momentum_5 > 8:
                score += 2.5
            elif momentum_5 > 5:
                score += 2.0
            elif momentum_5 > 2:
                score += 1.5
            elif momentum_5 > 0:
                score += 1.0
            elif momentum_5 < -8:
                score -= 2.5
            elif momentum_5 < -5:
                score -= 2.0
            elif momentum_5 < -2:
                score -= 1.0
            
            # Momentum medio plazo
            if momentum_10 > 5:
                score += 1.0
            elif momentum_10 < -5:
                score -= 1.0
            
            # RSI scoring
            if 30 <= rsi <= 70:  # Rango neutral
                score += 0.5
            elif rsi > 80:  # Sobrecomprado
                score -= 1.0
            elif rsi < 20:  # Sobrevendido
                score += 1.0
            
            # Volatilidad scoring
            if volatility > 50:
                score -= 1.5
            elif volatility > 30:
                score -= 0.5
            elif volatility < 15:
                score += 1.0
            elif volatility < 25:
                score += 0.5
            
            # Consistencia de tendencia
            if momentum_5 > 0 and momentum_10 > 0:
                score += 0.5
            elif momentum_5 < 0 and momentum_10 < 0:
                score -= 0.5
            
            return max(1.0, min(10.0, score))
        except Exception as e:
            return 5.0
    
    def fetch_data(self, symbol: str) -> pd.DataFrame:
        """Obtener datos históricos"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days + 60)
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date)
            
            if data.empty or len(data) < 200:
                return None
            return data
        except:
            return None
    
    def run_backtest(self, stocks: List[str]) -> Dict:
        """Ejecutar backtesting de 1 año"""
        print(f"Ejecutando backtesting de 1 año...")
        print(f"Stocks: {len(stocks)}")
        print(f"Período: {self.lookback_days} días")
        print(f"Capital inicial: ${self.initial_capital:,}")
        
        # Estados del portfolio
        cash = self.initial_capital
        positions = {}
        daily_values = []
        
        # Rango de fechas
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.lookback_days)
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Obtener datos
        stock_data = {}
        print(f"Obteniendo datos...")
        
        for i, symbol in enumerate(stocks):
            if i % 5 == 0:
                print(f"  {i}/{len(stocks)} stocks")
            
            data = self.fetch_data(symbol)
            if data is not None:
                stock_data[symbol] = data
            time.sleep(0.05)
        
        print(f"Datos obtenidos: {len(stock_data)} stocks")
        
        # Simulación diaria
        print(f"Ejecutando simulación...")
        print(f"Thresholds: BUY >= {self.buy_long_threshold}, SELL <= {self.sell_long_threshold}")
        
        total_buy_signals = 0
        total_sell_signals = 0
        
        for day_idx, current_date in enumerate(date_range):
            if day_idx % 60 == 0:
                print(f"  Día {day_idx}/{len(date_range)}")
            
            daily_signals = []
            
            for symbol in stock_data.keys():
                try:
                    data_subset = stock_data[symbol][stock_data[symbol].index <= current_date]
                    if len(data_subset) < 20:
                        continue
                    
                    score = self.calculate_score(data_subset)
                    current_price = data_subset['Close'].iloc[-1]
                    
                    if score >= self.buy_long_threshold and symbol not in positions:
                        daily_signals.append({
                            'symbol': symbol,
                            'action': 'BUY',
                            'score': score,
                            'price': current_price,
                            'date': current_date
                        })
                        total_buy_signals += 1
                    elif score <= self.sell_long_threshold and symbol in positions:
                        daily_signals.append({
                            'symbol': symbol,
                            'action': 'SELL',
                            'score': score,
                            'price': current_price,
                            'date': current_date
                        })
                        total_sell_signals += 1
                        
                    # Debug: log some samples
                    if day_idx == 180:  # Day 180, log all scores
                        if len(daily_signals) == 0:  # First sample of the day
                            print(f"  Sample scores on day 180:")
                        if len(daily_signals) < 10:
                            print(f"    {symbol}: score={score:.2f}")
                except:
                    continue
            
            # Ejecutar trades
            daily_signals.sort(key=lambda x: x['score'], reverse=True)
            
            for signal in daily_signals:
                if signal['action'] == 'BUY':
                    if len(positions) < self.max_positions and cash > self.max_position_value:
                        investment = min(self.max_position_value, cash * 0.2)
                        shares = investment / signal['price']
                        cost = shares * signal['price'] * (1 + self.commission)
                        
                        if cost <= cash:
                            cash -= cost
                            positions[signal['symbol']] = {
                                'shares': shares,
                                'entry_price': signal['price'],
                                'entry_date': signal['date']
                            }
                            
                            self.trades.append({
                                'symbol': signal['symbol'],
                                'action': 'BUY',
                                'shares': shares,
                                'price': signal['price'],
                                'date': signal['date'],
                                'score': signal['score']
                            })
                
                elif signal['action'] == 'SELL':
                    if signal['symbol'] in positions:
                        pos = positions[signal['symbol']]
                        proceeds = pos['shares'] * signal['price'] * (1 - self.commission)
                        cash += proceeds
                        
                        entry_value = pos['shares'] * pos['entry_price']
                        pnl = proceeds - entry_value
                        pnl_pct = (pnl / entry_value) * 100
                        days_held = (signal['date'] - pos['entry_date']).days
                        
                        self.trades.append({
                            'symbol': signal['symbol'],
                            'action': 'SELL',
                            'shares': pos['shares'],
                            'price': signal['price'],
                            'date': signal['date'],
                            'score': signal['score'],
                            'pnl': pnl,
                            'pnl_pct': pnl_pct,
                            'days_held': days_held
                        })
                        
                        del positions[signal['symbol']]
            
            # Portfolio value diario
            portfolio_value = cash
            for symbol, pos in positions.items():
                try:
                    current_data = stock_data[symbol][stock_data[symbol].index <= current_date]
                    if len(current_data) > 0:
                        current_price = current_data['Close'].iloc[-1]
                        portfolio_value += pos['shares'] * current_price
                except:
                    portfolio_value += pos['shares'] * pos['entry_price']
            
            daily_values.append({
                'date': current_date,
                'value': portfolio_value,
                'cash': cash,
                'positions': len(positions)
            })
        
        # Liquidación final
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
                    'days_held': days_held
                })
            except:
                pass
        
        final_value = cash
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        
        print(f"SIGNALS GENERATED: BUY={total_buy_signals}, SELL={total_sell_signals}")
        
        return {
            'initial_capital': self.initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'total_trades': len(self.trades),
            'stocks_analyzed': len(stock_data),
            'simulation_days': len(date_range),
            'daily_values': daily_values,
            'trades': self.trades,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
    
    def save_results(self, results: Dict) -> List[str]:
        """Guardar resultados y retornar lista de archivos"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        files_created = []
        
        # 1. Archivo JSON completo
        json_file = f"reports/backtest_1year_full_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        files_created.append(json_file)
        
        # 2. Archivo de trades solamente
        trades_file = f"reports/backtest_1year_trades_{timestamp}.json"
        with open(trades_file, 'w') as f:
            json.dump(self.trades, f, indent=2, default=str)
        files_created.append(trades_file)
        
        # 3. Archivo de resumen
        summary_file = f"reports/backtest_1year_summary_{timestamp}.txt"
        with open(summary_file, 'w') as f:
            f.write(f"BACKTESTING 1 YEAR SUMMARY\n")
            f.write(f"Generated: {datetime.now()}\n\n")
            f.write(f"Period: {results['start_date']} to {results['end_date']}\n")
            f.write(f"Initial Capital: ${results['initial_capital']:,}\n")
            f.write(f"Final Value: ${results['final_value']:,.2f}\n")
            f.write(f"Total Return: {results['total_return']:+.2f}%\n")
            f.write(f"Total Trades: {results['total_trades']}\n")
            f.write(f"Stocks Analyzed: {results['stocks_analyzed']}\n")
            f.write(f"Simulation Days: {results['simulation_days']}\n")
        files_created.append(summary_file)
        
        # 4. Archivo CSV de valores diarios
        csv_file = f"reports/backtest_1year_daily_{timestamp}.csv"
        df = pd.DataFrame(results['daily_values'])
        df.to_csv(csv_file, index=False)
        files_created.append(csv_file)
        
        return files_created

def main():
    print("BACKTESTING 1 AÑO - SOLO GENERACIÓN DE ARCHIVOS")
    print("=" * 50)
    
    backtest = OneYearBacktest()
    stocks = backtest.get_stocks_for_backtest()
    
    if len(stocks) < 5:
        print("ERROR: Insuficientes stocks")
        return []
    
    # Ejecutar backtesting
    results = backtest.run_backtest(stocks)
    
    # Guardar archivos
    files_created = backtest.save_results(results)
    
    print(f"\nBACKTESTING COMPLETADO")
    print(f"Archivos generados: {len(files_created)}")
    
    return files_created

if __name__ == "__main__":
    output_files = main()
    
    print(f"\nARCHIVOS DE SALIDA:")
    for i, file_path in enumerate(output_files, 1):
        print(f"{i}. {file_path}")