"""
Compare autotrader performance vs SP500 and NASDAQ from October 21, 2025
"""
import yfinance as yf
from datetime import datetime

# Reset date
reset_date = "2025-10-21"
today = datetime.now().strftime("%Y-%m-%d")

print("\n" + "="*100)
print("MARKET PERFORMANCE COMPARISON: October 21, 2025 to Today")
print("="*100)

# Get SP500 data
spy = yf.Ticker("SPY")
spy_hist = spy.history(start=reset_date, end=today)

if not spy_hist.empty:
    spy_start = spy_hist['Close'].iloc[0]
    spy_end = spy_hist['Close'].iloc[-1]
    spy_return = ((spy_end - spy_start) / spy_start) * 100

    print(f"\nS&P 500 (SPY):")
    print(f"  Date Range: {spy_hist.index[0].strftime('%Y-%m-%d')} to {spy_hist.index[-1].strftime('%Y-%m-%d')}")
    print(f"  Start Price: ${spy_start:.2f}")
    print(f"  End Price:   ${spy_end:.2f}")
    print(f"  Return:      {spy_return:+.2f}%")

# Get NASDAQ data
qqq = yf.Ticker("QQQ")
qqq_hist = qqq.history(start=reset_date, end=today)

if not qqq_hist.empty:
    qqq_start = qqq_hist['Close'].iloc[0]
    qqq_end = qqq_hist['Close'].iloc[-1]
    qqq_return = ((qqq_end - qqq_start) / qqq_start) * 100

    print(f"\nNASDAQ 100 (QQQ):")
    print(f"  Date Range: {qqq_hist.index[0].strftime('%Y-%m-%d')} to {qqq_hist.index[-1].strftime('%Y-%m-%d')}")
    print(f"  Start Price: ${qqq_start:.2f}")
    print(f"  End Price:   ${qqq_end:.2f}")
    print(f"  Return:      {qqq_return:+.2f}%")

# Autotrader performance
autotrader_return = 1.66

print(f"\n" + "="*100)
print("COMPARATIVE RESULTS")
print("="*100)
print(f"\nAutotrader Return:  {autotrader_return:+.2f}%")
print(f"S&P 500 Return:     {spy_return:+.2f}%")
print(f"NASDAQ 100 Return:  {qqq_return:+.2f}%")

print(f"\nAutotrader vs S&P 500:   {autotrader_return - spy_return:+.2f}% {'(outperformed)' if autotrader_return > spy_return else '(underperformed)'}")
print(f"Autotrader vs NASDAQ:    {autotrader_return - qqq_return:+.2f}% {'(outperformed)' if autotrader_return > qqq_return else '(underperformed)'}")

# Trading days
trading_days = len(spy_hist)
print(f"\nTrading days in period: {trading_days}")
print(f"Autotrader daily average: {autotrader_return/trading_days:+.3f}%")
print(f"S&P 500 daily average:    {spy_return/trading_days:+.3f}%")
print(f"NASDAQ 100 daily average: {qqq_return/trading_days:+.3f}%")

print("="*100)
