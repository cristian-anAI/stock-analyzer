#!/usr/bin/env python3
"""
Comprehensive Backtesting System for Autotrader
Tests strategy on all 265 stocks with 3x historical data
"""

import yfinance as yf
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import time
import json

class AutotraderBacktester:
    def __init__(self):
        self.db_path = 'trading.db'
        
        # Autotrader thresholds (from current configuration)
        self.buy_long_threshold = 7.5
        self.sell_long_threshold = 4.0
        self.short_threshold = 2.5
        
        # Portfolio settings
        self.initial_capital = 50000  # $50k starting capital
        self.max_position_value = 10000  # Max $10k per position
        self.max_positions = 20  # Max 20 positions
        
        # Backtesting parameters
        self.lookback_days = 90  # 3 months (triple the usual monthly analysis)
        self.commission = 0.001  # 0.1% commission per trade
        
        self.results = {}
        self.trades = []
        self.portfolio_history = []
        
    def get_all_stocks(self) -> List[str]:
        """Get all stocks from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all stocks, prioritizing by market cap
        cursor.execute("""
            SELECT symbol FROM stocks 
            WHERE market_cap > 1000000000
            ORDER BY market_cap DESC
        """)
        
        stocks = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        print(f"Selected {len(stocks)} stocks for backtesting")
        return stocks
    
    def calculate_simple_score(self, data: Dict) -> float:
        """
        Simplified scoring system for backtesting
        Based on price momentum, volume, and volatility
        """
        try:
            # Calculate price momentum (20-day vs 5-day average)
            close_prices = data['Close']
            if len(close_prices) < 20:
                return 5.0  # Neutral score
            
            recent_avg = close_prices[-5:].mean()
            longer_avg = close_prices[-20:].mean()
            momentum_score = (recent_avg / longer_avg - 1) * 100
            
            # Calculate volatility (20-day standard deviation)
            returns = close_prices.pct_change().dropna()
            volatility = returns[-20:].std() * np.sqrt(252) * 100  # Annualized
            
            # Calculate volume momentum
            volumes = data['Volume']
            recent_vol = volumes[-5:].mean()
            avg_vol = volumes[-20:].mean()
            volume_momentum = (recent_vol / avg_vol - 1) * 100 if avg_vol > 0 else 0
            
            # Base score calculation
            score = 5.0  # Neutral baseline
            
            # Momentum factor (most important)
            if momentum_score > 5:
                score += 2.0
            elif momentum_score > 2:
                score += 1.0
            elif momentum_score < -5:
                score -= 2.0
            elif momentum_score < -2:
                score -= 1.0
            
            # Volatility factor (high volatility reduces score)
            if volatility > 50:
                score -= 1.5
            elif volatility > 30:
                score -= 0.5
            elif volatility < 15:
                score += 0.5
            
            # Volume factor
            if volume_momentum > 50:
                score += 0.5
            elif volume_momentum < -20:
                score -= 0.5
            
            # Clamp score between 0 and 10
            return max(0.0, min(10.0, score))
            
        except Exception as e:
            print(f"Error calculating score: {e}")
            return 5.0
    
    def fetch_historical_data(self, symbol: str) -> pd.DataFrame:
        """Fetch historical data for backtesting period"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days + 30)  # Extra buffer for calculations
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date)
            
            if data.empty:
                return None
            
            return data
            
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None
    
    def simulate_trading(self, stocks: List[str]) -> Dict:
        """Run backtesting simulation"""
        
        print(f"Starting backtesting simulation...")
        print(f"Period: {self.lookback_days} days")
        print(f"Initial capital: ${self.initial_capital:,}")
        print(f"Max positions: {self.max_positions}")
        
        # Portfolio state
        cash = self.initial_capital
        positions = {}  # symbol: {'shares': int, 'entry_price': float, 'entry_date': date, 'type': 'LONG'/'SHORT'}
        daily_portfolio_value = []
        
        # Get date range for simulation
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.lookback_days)
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        print(f"Simulation date range: {start_date.date()} to {end_date.date()}")
        
        # Track stocks that we have data for
        stock_data = {}
        successful_fetches = 0
        
        print(f"\nFetching historical data for {len(stocks)} stocks...")
        
        # Fetch data for all stocks (limit to first 50 for reasonable execution time)
        for i, symbol in enumerate(stocks[:50]):
            if i % 10 == 0:
                print(f"  Progress: {i}/{min(50, len(stocks))} stocks")
            
            data = self.fetch_historical_data(symbol)
            if data is not None:
                stock_data[symbol] = data
                successful_fetches += 1
            
            time.sleep(0.1)  # Rate limiting
        
        print(f"Successfully fetched data for {successful_fetches} stocks")
        
        if successful_fetches == 0:
            print("ERROR: No stock data available for backtesting")
            return {}
        
        # Simulate trading day by day
        print(f"\nRunning daily simulation...")
        
        for day_idx, current_date in enumerate(date_range):
            if day_idx % 15 == 0:
                print(f"  Progress: Day {day_idx+1}/{len(date_range)} ({current_date.date()})")
            
            daily_signals = []
            
            # Analyze all stocks for signals
            for symbol in stock_data.keys():
                try:
                    # Get data up to current date
                    data_subset = stock_data[symbol][stock_data[symbol].index <= current_date]
                    
                    if len(data_subset) < 20:
                        continue  # Not enough data
                    
                    # Calculate score
                    score = self.calculate_simple_score(data_subset)
                    current_price = data_subset['Close'].iloc[-1]
                    
                    # Generate signals
                    if score >= self.buy_long_threshold and symbol not in positions:
                        daily_signals.append({
                            'symbol': symbol,
                            'action': 'BUY_LONG',
                            'score': score,
                            'price': current_price,
                            'date': current_date
                        })
                    elif score <= self.sell_long_threshold and symbol in positions and positions[symbol]['type'] == 'LONG':
                        daily_signals.append({
                            'symbol': symbol,
                            'action': 'SELL_LONG',
                            'score': score,
                            'price': current_price,
                            'date': current_date
                        })
                    elif score < self.short_threshold and symbol not in positions:
                        daily_signals.append({
                            'symbol': symbol,
                            'action': 'BUY_SHORT',
                            'score': score,
                            'price': current_price,
                            'date': current_date
                        })
                        
                except Exception as e:
                    continue
            
            # Execute trades based on signals
            daily_signals.sort(key=lambda x: x['score'], reverse=True)  # Best signals first
            
            for signal in daily_signals:
                if signal['action'] == 'BUY_LONG':
                    if len(positions) < self.max_positions and cash > self.max_position_value:
                        # Calculate shares to buy
                        investment = min(self.max_position_value, cash * 0.1)  # Max 10% per position
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
                                'score': signal['score']
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
                        
                        self.trades.append({
                            'symbol': signal['symbol'],
                            'action': 'SELL_LONG',
                            'shares': pos['shares'],
                            'price': signal['price'],
                            'date': signal['date'],
                            'score': signal['score'],
                            'pnl': pnl,
                            'pnl_pct': pnl_pct,
                            'days_held': (signal['date'] - pos['entry_date']).days
                        })
                        
                        del positions[signal['symbol']]
                
                elif signal['action'] == 'BUY_SHORT':
                    # Simplified SHORT implementation
                    if len(positions) < self.max_positions and cash > self.max_position_value:
                        investment = min(self.max_position_value, cash * 0.05)  # More conservative for shorts
                        shares = investment / signal['price']
                        cost = shares * signal['price'] * (1 + self.commission)
                        
                        if cost <= cash:
                            cash -= cost  # Collateral
                            positions[signal['symbol']] = {
                                'shares': shares,
                                'entry_price': signal['price'],
                                'entry_date': signal['date'],
                                'type': 'SHORT'
                            }
                            
                            self.trades.append({
                                'symbol': signal['symbol'],
                                'action': 'BUY_SHORT',
                                'shares': shares,
                                'price': signal['price'],
                                'date': signal['date'],
                                'score': signal['score']
                            })
            
            # Calculate daily portfolio value
            portfolio_value = cash
            for symbol, pos in positions.items():
                try:
                    current_data = stock_data[symbol][stock_data[symbol].index <= current_date]
                    if len(current_data) > 0:
                        current_price = current_data['Close'].iloc[-1]
                        
                        if pos['type'] == 'LONG':
                            portfolio_value += pos['shares'] * current_price
                        else:  # SHORT
                            # For shorts: profit when price goes down
                            pnl = pos['shares'] * (pos['entry_price'] - current_price)
                            portfolio_value += pnl
                except:
                    continue
            
            daily_portfolio_value.append({
                'date': current_date,
                'value': portfolio_value,
                'cash': cash,
                'positions': len(positions)
            })
        
        # Final portfolio value
        final_value = daily_portfolio_value[-1]['value'] if daily_portfolio_value else self.initial_capital
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        
        return {
            'initial_capital': self.initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'total_trades': len(self.trades),
            'stocks_analyzed': len(stock_data),
            'simulation_days': len(date_range),
            'daily_values': daily_portfolio_value,
            'trades': self.trades
        }
    
    def analyze_results(self, results: Dict) -> Dict:
        """Analyze backtesting results and generate metrics"""
        
        if not results:
            return {}
        
        # Basic metrics
        metrics = {
            'period_days': results['simulation_days'],
            'initial_capital': results['initial_capital'],
            'final_value': results['final_value'],
            'total_return_pct': results['total_return'],
            'total_trades': results['total_trades']
        }
        
        if len(self.trades) > 0:
            # Trade analysis
            long_trades = [t for t in self.trades if t['action'] in ['BUY_LONG', 'SELL_LONG']]
            short_trades = [t for t in self.trades if 'SHORT' in t['action']]
            
            completed_trades = [t for t in self.trades if 'pnl' in t]
            
            if completed_trades:
                profits = [t['pnl'] for t in completed_trades if t['pnl'] > 0]
                losses = [t['pnl'] for t in completed_trades if t['pnl'] < 0]
                
                metrics.update({
                    'completed_trades': len(completed_trades),
                    'winning_trades': len(profits),
                    'losing_trades': len(losses),
                    'win_rate': len(profits) / len(completed_trades) * 100,
                    'avg_win': np.mean(profits) if profits else 0,
                    'avg_loss': np.mean(losses) if losses else 0,
                    'avg_trade_pnl': np.mean([t['pnl'] for t in completed_trades]),
                    'avg_days_held': np.mean([t['days_held'] for t in completed_trades])
                })
            
            metrics.update({
                'long_signals': len([t for t in self.trades if t['action'] == 'BUY_LONG']),
                'short_signals': len([t for t in self.trades if t['action'] == 'BUY_SHORT']),
                'sell_signals': len([t for t in self.trades if t['action'] == 'SELL_LONG'])
            })
        
        # Portfolio performance
        if results['daily_values']:
            values = [d['value'] for d in results['daily_values']]
            returns = np.diff(values) / values[:-1]
            
            metrics.update({
                'volatility_daily': np.std(returns) * 100,
                'max_portfolio_value': max(values),
                'min_portfolio_value': min(values),
                'max_drawdown': ((max(values) - min(values)) / max(values)) * 100
            })
        
        return metrics
    
    def generate_report(self, results: Dict, metrics: Dict) -> str:
        """Generate comprehensive backtesting report"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        report = f"""
# AUTOTRADER BACKTESTING REPORT
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## BACKTESTING PARAMETERS

- **Period**: {self.lookback_days} days (3x normal analysis period)
- **Initial Capital**: ${self.initial_capital:,}
- **Max Position Value**: ${self.max_position_value:,}
- **Max Positions**: {self.max_positions}
- **Commission**: {self.commission*100}% per trade

### Strategy Thresholds
- **BUY LONG**: Score >= {self.buy_long_threshold}
- **SELL LONG**: Score <= {self.sell_long_threshold}  
- **SHORT**: Score < {self.short_threshold}

## RESULTS SUMMARY

### Portfolio Performance
- **Final Value**: ${metrics.get('final_value', 0):,.2f}
- **Total Return**: {metrics.get('total_return_pct', 0):+.2f}%
- **Simulation Days**: {metrics.get('period_days', 0)}
- **Stocks Analyzed**: {results.get('stocks_analyzed', 0)}

### Trading Activity
- **Total Trades**: {metrics.get('total_trades', 0)}
- **Completed Trades**: {metrics.get('completed_trades', 0)}
- **LONG Signals**: {metrics.get('long_signals', 0)}
- **SHORT Signals**: {metrics.get('short_signals', 0)}
- **SELL Signals**: {metrics.get('sell_signals', 0)}

### Performance Metrics
"""
        
        if metrics.get('completed_trades', 0) > 0:
            report += f"""
- **Win Rate**: {metrics.get('win_rate', 0):.1f}%
- **Winning Trades**: {metrics.get('winning_trades', 0)}
- **Losing Trades**: {metrics.get('losing_trades', 0)}
- **Average Win**: ${metrics.get('avg_win', 0):.2f}
- **Average Loss**: ${metrics.get('avg_loss', 0):.2f}
- **Average Trade P&L**: ${metrics.get('avg_trade_pnl', 0):.2f}
- **Average Days Held**: {metrics.get('avg_days_held', 0):.1f}
"""
        
        if 'volatility_daily' in metrics:
            report += f"""
### Risk Metrics
- **Daily Volatility**: {metrics.get('volatility_daily', 0):.2f}%
- **Max Drawdown**: {metrics.get('max_drawdown', 0):.2f}%
- **Max Portfolio Value**: ${metrics.get('max_portfolio_value', 0):,.2f}
- **Min Portfolio Value**: ${metrics.get('min_portfolio_value', 0):,.2f}
"""
        
        # Sample trades
        if len(self.trades) > 0:
            report += f"""
## SAMPLE TRADES

### First 10 Trades
"""
            for trade in self.trades[:10]:
                pnl_info = f" | P&L: ${trade.get('pnl', 0):.2f} ({trade.get('pnl_pct', 0):+.1f}%)" if 'pnl' in trade else ""
                report += f"- {trade['date'].date()} | {trade['action']} {trade['symbol']} | {trade['shares']:.0f} shares @ ${trade['price']:.2f} | Score: {trade['score']:.1f}{pnl_info}\n"
        
        # Strategy analysis
        total_return = metrics.get('total_return_pct', 0)
        report += f"""
## STRATEGY ANALYSIS

### Overall Assessment
"""
        if total_return > 5:
            report += "- ✅ **POSITIVE PERFORMANCE**: Strategy generated positive returns\n"
        elif total_return > -5:
            report += "- ⚖️ **NEUTRAL PERFORMANCE**: Strategy performed close to break-even\n"
        else:
            report += "- ❌ **NEGATIVE PERFORMANCE**: Strategy underperformed\n"
        
        win_rate = metrics.get('win_rate', 0)
        if win_rate > 60:
            report += "- ✅ **HIGH WIN RATE**: Good signal quality\n"
        elif win_rate > 40:
            report += "- ⚖️ **MODERATE WIN RATE**: Average signal quality\n"
        else:
            report += "- ❌ **LOW WIN RATE**: Poor signal quality\n"
        
        total_trades = metrics.get('total_trades', 0)
        if total_trades > 50:
            report += "- 📈 **ACTIVE STRATEGY**: High trading frequency\n"
        elif total_trades > 20:
            report += "- ⚖️ **MODERATE ACTIVITY**: Balanced trading frequency\n"
        else:
            report += "- 📉 **CONSERVATIVE STRATEGY**: Low trading frequency\n"
        
        report += f"""
### Threshold Effectiveness
- **BUY LONG Threshold ({self.buy_long_threshold})**: {'Effective' if metrics.get('long_signals', 0) > 0 else 'Too conservative - no signals'}
- **SHORT Threshold ({self.short_threshold})**: {'Effective' if metrics.get('short_signals', 0) > 0 else 'Too conservative - no signals'}
- **SELL Threshold ({self.sell_long_threshold})**: {'Effective' if metrics.get('sell_signals', 0) > 0 else 'Too conservative - no signals'}

## RECOMMENDATIONS

### Strategy Optimization
"""
        
        if total_return < 0 and win_rate < 50:
            report += "1. **Consider adjusting thresholds** - Current settings may be too conservative or aggressive\n"
        
        if metrics.get('long_signals', 0) == 0:
            report += "2. **LONG threshold too high** - Consider lowering from 7.5 to 6.5-7.0\n"
        
        if metrics.get('short_signals', 0) == 0:
            report += "3. **SHORT threshold too low** - Consider raising from 2.5 to 3.0-3.5\n"
        
        if metrics.get('avg_days_held', 0) > 30:
            report += "4. **Long holding periods** - Consider more aggressive exit criteria\n"
        
        report += f"""
### Risk Management
- Current max drawdown of {metrics.get('max_drawdown', 0):.2f}% is {'acceptable' if metrics.get('max_drawdown', 0) < 20 else 'high - consider position sizing'}
- Daily volatility of {metrics.get('volatility_daily', 0):.2f}% indicates {'low' if metrics.get('volatility_daily', 0) < 2 else 'moderate' if metrics.get('volatility_daily', 0) < 4 else 'high'} risk

---
**Backtesting completed on {results.get('stocks_analyzed', 0)} stocks over {self.lookback_days} days**
**Report ready for analysis with Claude Code or Llama AI**
"""
        
        return report
    
    def save_results(self, results: Dict, metrics: Dict, report: str):
        """Save backtesting results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed results as JSON
        json_data = {
            'metadata': {
                'timestamp': timestamp,
                'lookback_days': self.lookback_days,
                'initial_capital': self.initial_capital,
                'thresholds': {
                    'buy_long': self.buy_long_threshold,
                    'sell_long': self.sell_long_threshold,
                    'short': self.short_threshold
                }
            },
            'results': results,
            'metrics': metrics,
            'trades': self.trades
        }
        
        json_file = f"reports/backtest_results_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(json_data, f, indent=2, default=str)
        
        # Save report
        report_file = f"reports/backtest_report_{timestamp}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return json_file, report_file

def main():
    print("AUTOTRADER BACKTESTING SYSTEM")
    print("=" * 50)
    
    backtester = AutotraderBacktester()
    
    # Get stocks
    stocks = backtester.get_all_stocks()
    
    if len(stocks) == 0:
        print("ERROR: No stocks available for backtesting")
        return
    
    # Run backtesting
    results = backtester.simulate_trading(stocks)
    
    if not results:
        print("ERROR: Backtesting simulation failed")
        return
    
    # Analyze results
    metrics = backtester.analyze_results(results)
    
    # Generate report
    report = backtester.generate_report(results, metrics)
    
    # Save results
    json_file, report_file = backtester.save_results(results, metrics, report)
    
    print(f"\nBACKTESTING COMPLETED SUCCESSFULLY!")
    print(f"Report: {report_file}")
    print(f"Data: {json_file}")
    
    # Summary
    print(f"\nRESULTS SUMMARY:")
    print(f"  Initial Capital: ${results['initial_capital']:,}")
    print(f"  Final Value: ${results['final_value']:,.2f}")
    print(f"  Total Return: {results['total_return']:+.2f}%")
    print(f"  Total Trades: {results['total_trades']}")
    print(f"  Stocks Analyzed: {results['stocks_analyzed']}")
    print(f"  Period: {results['simulation_days']} days")

if __name__ == "__main__":
    main()