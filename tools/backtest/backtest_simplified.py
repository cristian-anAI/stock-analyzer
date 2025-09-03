#!/usr/bin/env python3
"""
Backtest simplificado basado en analyze_win_rate_profit.py que funcionaba
Con rate limiting para evitar saturación de API
"""

import yfinance as yf
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import time
from typing import Dict, List

class SimplifiedBacktest:
    def __init__(self):
        self.db_path = 'trading.db'
        self.initial_capital = 100000
        self.max_position_value = 10000
        self.max_positions = 10
        self.commission = 0.001
        self.trades = []
        
        # Thresholds que funcionaban en analyze_win_rate_profit.py
        self.buy_long_threshold = 6.0
        self.sell_long_threshold = 4.0
        self.short_threshold = 1.8
        
        # Rate limiting
        self.api_calls = 0
        self.last_api_time = time.time()
        self.max_calls_per_minute = 60  # Leaky bucket
        
    def rate_limit(self):
        """Rate limiting - leaky bucket implementation"""
        current_time = time.time()
        time_passed = current_time - self.last_api_time
        
        # Reset counter every minute
        if time_passed >= 60:
            self.api_calls = 0
            self.last_api_time = current_time
        
        # If too many calls, wait
        if self.api_calls >= self.max_calls_per_minute:
            sleep_time = 60 - time_passed
            if sleep_time > 0:
                print(f"  Rate limiting: waiting {sleep_time:.1f}s...")
                time.sleep(sleep_time)
                self.api_calls = 0
                self.last_api_time = time.time()
        
        self.api_calls += 1
        
    def get_qualifying_stocks(self) -> Dict[str, List[str]]:
        """Obtener stocks que califican usando thresholds que funcionaban"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # LONGs: score >= 6.0
        cursor.execute("""
            SELECT symbol, score FROM stocks 
            WHERE market_cap > 50000000000 AND score >= ?
            ORDER BY market_cap DESC
        """, (self.buy_long_threshold,))
        
        long_stocks = [(row[0], row[1]) for row in cursor.fetchall()]
        
        # SHORTs: score < 1.8 (ultra selectivos)
        cursor.execute("""
            SELECT symbol, score FROM stocks 
            WHERE market_cap > 100000000000 AND score < ?
            ORDER BY market_cap DESC
            LIMIT 5
        """, (self.short_threshold,))
        
        short_stocks = [(row[0], row[1]) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'longs': [s[0] for s in long_stocks],
            'shorts': [s[0] for s in short_stocks],
            'long_scores': dict(long_stocks),
            'short_scores': dict(short_stocks)
        }
    
    def fetch_historical_data(self, symbol: str, days: int = 365) -> pd.DataFrame:
        """Obtener datos históricos con rate limiting"""
        try:
            self.rate_limit()  # Apply rate limiting
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days + 30)  # Extra buffer
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date)
            
            if data.empty or len(data) < 200:
                return None
            
            return data
            
        except Exception as e:
            print(f"  Error fetching {symbol}: {e}")
            return None
    
    def calculate_returns(self, entry_date: datetime, exit_date: datetime, 
                         entry_price: float, exit_price: float, 
                         position_type: str) -> Dict:
        """Calcular returns para una posición"""
        days_held = (exit_date - entry_date).days
        
        if position_type == 'LONG':
            raw_return = (exit_price - entry_price) / entry_price
        else:  # SHORT
            raw_return = (entry_price - exit_price) / entry_price
            
        # Apply commission
        net_return = raw_return - (2 * self.commission)  # Buy + sell commission
        
        return {
            'days_held': days_held,
            'raw_return': raw_return * 100,
            'net_return': net_return * 100,
            'profit_loss': net_return * self.max_position_value
        }
    
    def simulate_trading_strategy(self, stocks_data: Dict, timeframes: List[int]) -> Dict:
        """Simular estrategia usando método de analyze_win_rate_profit.py"""
        
        results = {}
        
        for timeframe in timeframes:
            print(f"\n  Análisis {timeframe} días...")
            
            long_results = []
            short_results = []
            
            # Simulate LONG positions
            for symbol, data in stocks_data['longs'].items():
                if data is None:
                    continue
                    
                # Use multiple entry points during the year
                total_days = len(data)
                entry_points = max(1, min(4, total_days // 90))  # Max 4 entries per year
                
                for i in range(entry_points):
                    entry_idx = (total_days // entry_points) * i + 30  # Start after 30 days
                    exit_idx = entry_idx + timeframe
                    
                    if exit_idx < total_days:
                        entry_date = data.index[entry_idx]
                        exit_date = data.index[exit_idx]
                        entry_price = data['Close'].iloc[entry_idx]
                        exit_price = data['Close'].iloc[exit_idx]
                        
                        trade_result = self.calculate_returns(
                            entry_date, exit_date, entry_price, exit_price, 'LONG'
                        )
                        
                        trade_result.update({
                            'symbol': symbol,
                            'position_type': 'LONG',
                            'timeframe': timeframe,
                            'entry_date': entry_date,
                            'exit_date': exit_date,
                            'entry_price': entry_price,
                            'exit_price': exit_price
                        })
                        
                        long_results.append(trade_result)
                        self.trades.append(trade_result)
            
            # Simulate SHORT positions (fewer, more selective)
            for symbol, data in stocks_data['shorts'].items():
                if data is None:
                    continue
                    
                # Only 1-2 short entries per year (ultra conservative)
                total_days = len(data)
                entry_points = min(2, total_days // 120)
                
                for i in range(entry_points):
                    entry_idx = (total_days // entry_points) * i + 30
                    exit_idx = entry_idx + timeframe
                    
                    if exit_idx < total_days:
                        entry_date = data.index[entry_idx]
                        exit_date = data.index[exit_idx]
                        entry_price = data['Close'].iloc[entry_idx]
                        exit_price = data['Close'].iloc[exit_idx]
                        
                        trade_result = self.calculate_returns(
                            entry_date, exit_date, entry_price, exit_price, 'SHORT'
                        )
                        
                        trade_result.update({
                            'symbol': symbol,
                            'position_type': 'SHORT',
                            'timeframe': timeframe,
                            'entry_date': entry_date,
                            'exit_date': exit_date,
                            'entry_price': entry_price,
                            'exit_price': exit_price
                        })
                        
                        short_results.append(trade_result)
                        self.trades.append(trade_result)
            
            # Calculate statistics for this timeframe
            all_results = long_results + short_results
            
            if all_results:
                winning_trades = [r for r in all_results if r['net_return'] > 0]
                losing_trades = [r for r in all_results if r['net_return'] <= 0]
                
                win_rate = len(winning_trades) / len(all_results) * 100
                avg_return = sum(r['net_return'] for r in all_results) / len(all_results)
                total_pnl = sum(r['profit_loss'] for r in all_results)
                
                results[timeframe] = {
                    'total_trades': len(all_results),
                    'winning_trades': len(winning_trades),
                    'losing_trades': len(losing_trades),
                    'win_rate': win_rate,
                    'avg_return': avg_return,
                    'total_pnl': total_pnl,
                    'long_trades': len(long_results),
                    'short_trades': len(short_results),
                    'trades': all_results
                }
                
                print(f"    Trades: {len(all_results)} | Win Rate: {win_rate:.1f}% | Avg Return: {avg_return:.2f}%")
            
        return results
    
    def run_simplified_backtest(self) -> Dict:
        """Ejecutar backtest simplificado basado en el método exitoso"""
        print("BACKTEST SIMPLIFICADO - BASADO EN MÉTODO EXITOSO")
        print("=" * 60)
        
        # 1. Get qualifying stocks
        print("1. Obteniendo stocks que califican...")
        qualifying_stocks = self.get_qualifying_stocks()
        
        print(f"   LONG candidates: {len(qualifying_stocks['longs'])}")
        print(f"   SHORT candidates: {len(qualifying_stocks['shorts'])}")
        
        if not qualifying_stocks['longs'] and not qualifying_stocks['shorts']:
            return {'error': 'No qualifying stocks found'}
        
        # 2. Fetch historical data
        print("\n2. Obteniendo datos históricos...")
        
        stocks_data = {'longs': {}, 'shorts': {}}
        
        # Fetch LONG data
        for symbol in qualifying_stocks['longs'][:15]:  # Limit to avoid API saturation
            print(f"   Fetching {symbol}...")
            data = self.fetch_historical_data(symbol)
            stocks_data['longs'][symbol] = data
            
        # Fetch SHORT data
        for symbol in qualifying_stocks['shorts'][:5]:  # Very limited SHORTs
            print(f"   Fetching {symbol} (SHORT)...")
            data = self.fetch_historical_data(symbol)
            stocks_data['shorts'][symbol] = data
        
        print(f"   Data obtenida: {len([d for d in stocks_data['longs'].values() if d is not None])} LONGs, {len([d for d in stocks_data['shorts'].values() if d is not None])} SHORTs")
        
        # 3. Run simulation
        print("\n3. Ejecutando simulación...")
        timeframes = [7, 30, 60]  # Same as analyze_win_rate_profit.py
        
        simulation_results = self.simulate_trading_strategy(stocks_data, timeframes)
        
        # 4. Calculate portfolio performance
        portfolio_results = self.calculate_portfolio_performance(simulation_results)
        
        return {
            'qualifying_stocks': qualifying_stocks,
            'simulation_results': simulation_results,
            'portfolio_results': portfolio_results,
            'total_trades': len(self.trades),
            'stocks_analyzed': len([d for d in stocks_data['longs'].values() if d is not None]) + len([d for d in stocks_data['shorts'].values() if d is not None])
        }
    
    def calculate_portfolio_performance(self, simulation_results: Dict) -> Dict:
        """Calculate overall portfolio performance"""
        portfolio = {}
        
        for timeframe, results in simulation_results.items():
            if results['total_trades'] > 0:
                # Portfolio mix: 80% LONG, 20% SHORT (as per original analysis)
                long_weight = 0.8
                short_weight = 0.2
                
                long_trades = [t for t in results['trades'] if t['position_type'] == 'LONG']
                short_trades = [t for t in results['trades'] if t['position_type'] == 'SHORT']
                
                long_return = sum(t['net_return'] for t in long_trades) / len(long_trades) if long_trades else 0
                short_return = sum(t['net_return'] for t in short_trades) / len(short_trades) if short_trades else 0
                
                weighted_return = (long_return * long_weight) + (short_return * short_weight)
                portfolio_pnl = (weighted_return / 100) * self.initial_capital
                
                portfolio[timeframe] = {
                    'portfolio_return': weighted_return,
                    'portfolio_pnl': portfolio_pnl,
                    'long_return': long_return,
                    'short_return': short_return
                }
        
        return portfolio
    
    def save_results(self, results: Dict) -> str:
        """Save results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reports/backtest_simplified_{timestamp}.json"
        
        # Convert datetime objects to strings
        results_copy = json.loads(json.dumps(results, default=str))
        
        with open(filename, 'w') as f:
            json.dump(results_copy, f, indent=2)
        
        return filename

def main():
    backtest = SimplifiedBacktest()
    
    results = backtest.run_simplified_backtest()
    
    if 'error' in results:
        print(f"ERROR: {results['error']}")
        return
    
    # Save results
    output_file = backtest.save_results(results)
    
    # Print summary
    print("\n" + "="*60)
    print("RESUMEN DE RESULTADOS")
    print("="*60)
    
    print(f"Total trades ejecutados: {results['total_trades']}")
    print(f"Stocks analizados: {results['stocks_analyzed']}")
    
    for timeframe, sim_results in results['simulation_results'].items():
        print(f"\nTimeframe {timeframe} días:")
        print(f"  Trades: {sim_results['total_trades']}")
        print(f"  Win Rate: {sim_results['win_rate']:.1f}%")
        print(f"  Avg Return: {sim_results['avg_return']:.2f}%")
        print(f"  Total P&L: ${sim_results['total_pnl']:,.0f}")
    
    if results['portfolio_results']:
        print("\nPortfolio Performance:")
        for timeframe, portfolio in results['portfolio_results'].items():
            print(f"  {timeframe}d: {portfolio['portfolio_return']:.2f}% (${portfolio['portfolio_pnl']:,.0f})")
    
    print(f"\nResultados guardados en: {output_file}")

if __name__ == "__main__":
    main()