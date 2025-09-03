#!/usr/bin/env python3
"""
Quick backtesting sample for immediate results
Tests top 10 stocks with 30 days of data
"""

import yfinance as yf
import sqlite3
import numpy as np
from datetime import datetime, timedelta
import time

def quick_backtest():
    print("QUICK BACKTESTING SAMPLE")
    print("=" * 40)
    
    # Get top 10 stocks by market cap
    conn = sqlite3.connect('trading.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT symbol, name, market_cap, score 
        FROM stocks 
        WHERE market_cap > 10000000000 
        ORDER BY market_cap DESC 
        LIMIT 10
    """)
    
    stocks = cursor.fetchall()
    conn.close()
    
    if not stocks:
        print("No stocks found")
        return
    
    print(f"Testing {len(stocks)} top stocks:")
    for symbol, name, mcap, score in stocks:
        print(f"  {symbol}: {name[:30]:<30} | Score: {score} | MCap: ${mcap/1e9:.1f}B")
    
    # Quick analysis
    thresholds = {
        'buy_long': 7.5,
        'sell_long': 4.0,
        'short': 2.5
    }
    
    signals = {'buy_long': [], 'sell_long': [], 'short': []}
    
    print(f"\nAnalyzing signals with current thresholds:")
    print(f"  BUY LONG: >= {thresholds['buy_long']}")
    print(f"  SELL LONG: <= {thresholds['sell_long']}")  
    print(f"  SHORT: < {thresholds['short']}")
    
    for symbol, name, mcap, score in stocks:
        if score >= thresholds['buy_long']:
            signals['buy_long'].append((symbol, score))
        elif score <= thresholds['sell_long']:
            signals['sell_long'].append((symbol, score))
        elif score < thresholds['short']:
            signals['short'].append((symbol, score))
    
    print(f"\nSIGNALS DETECTED:")
    print(f"  BUY LONG: {len(signals['buy_long'])} signals")
    for symbol, score in signals['buy_long']:
        print(f"    {symbol}: Score {score}")
    
    print(f"  SELL LONG: {len(signals['sell_long'])} signals")
    for symbol, score in signals['sell_long']:
        print(f"    {symbol}: Score {score}")
    
    print(f"  SHORT: {len(signals['short'])} signals")
    for symbol, score in signals['short']:
        print(f"    {symbol}: Score {score}")
    
    # Quick historical performance check on a few stocks
    print(f"\nQUICK PERFORMANCE CHECK (last 30 days):")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    total_return = 0
    stocks_checked = 0
    
    for symbol, name, mcap, score in stocks[:5]:  # Check first 5
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date)
            
            if len(data) > 1:
                start_price = data['Close'].iloc[0]
                end_price = data['Close'].iloc[-1]
                stock_return = (end_price - start_price) / start_price * 100
                total_return += stock_return
                stocks_checked += 1
                
                print(f"  {symbol}: {stock_return:+.2f}% (Score: {score})")
            
        except Exception as e:
            print(f"  {symbol}: Error - {str(e)[:30]}")
        
        time.sleep(0.2)
    
    if stocks_checked > 0:
        avg_return = total_return / stocks_checked
        print(f"\nAVERAGE RETURN (last 30 days): {avg_return:+.2f}%")
    
    # Threshold effectiveness analysis
    print(f"\nTHRESHOLD EFFECTIVENESS:")
    total_signals = sum(len(signals[key]) for key in signals)
    
    if total_signals == 0:
        print("  ❌ NO SIGNALS - Thresholds may be too conservative")
        print("  💡 Suggestions:")
        print("     - Lower BUY LONG threshold from 7.5 to 6.5-7.0")
        print("     - Raise SHORT threshold from 2.5 to 3.0-3.5")
    else:
        print(f"  ✅ {total_signals} SIGNALS DETECTED")
        if len(signals['buy_long']) == 0:
            print("  ⚠️  No LONG opportunities - BUY threshold too high")
        if len(signals['short']) == 0:
            print("  ⚠️  No SHORT opportunities - SHORT threshold too low")
    
    return signals

if __name__ == "__main__":
    quick_backtest()