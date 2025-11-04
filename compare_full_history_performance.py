"""
Compare autotrader performance vs SP500 and NASDAQ from September 4, 2025 (all trades)
"""
import yfinance as yf
from datetime import datetime

# First trade date
start_date = "2025-09-04"
today = datetime.now().strftime("%Y-%m-%d")

print("\n" + "="*100)
print("MARKET PERFORMANCE COMPARISON: September 4, 2025 to Today (FULL HISTORY)")
print("="*100)

# Get SP500 data
spy = yf.Ticker("SPY")
spy_hist = spy.history(start=start_date, end=today)

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
qqq_hist = qqq.history(start=start_date, end=today)

if not qqq_hist.empty:
    qqq_start = qqq_hist['Close'].iloc[0]
    qqq_end = qqq_hist['Close'].iloc[-1]
    qqq_return = ((qqq_end - qqq_start) / qqq_start) * 100

    print(f"\nNASDAQ 100 (QQQ):")
    print(f"  Date Range: {qqq_hist.index[0].strftime('%Y-%m-%d')} to {qqq_hist.index[-1].strftime('%Y-%m-%d')}")
    print(f"  Start Price: ${qqq_start:.2f}")
    print(f"  End Price:   ${qqq_end:.2f}")
    print(f"  Return:      {qqq_return:+.2f}%")

# Autotrader performance from full history
# From pnl_analysis_output.txt: Total P&L: $4,121.47 from $100,000
autotrader_return = 4.12

print(f"\n" + "="*100)
print("COMPARATIVE RESULTS (FULL HISTORY)")
print("="*100)
print(f"\nAutotrader Return:  {autotrader_return:+.2f}%")
print(f"S&P 500 Return:     {spy_return:+.2f}%")
print(f"NASDAQ 100 Return:  {qqq_return:+.2f}%")

print(f"\nAutotrader vs S&P 500:   {autotrader_return - spy_return:+.2f}% {'(outperformed)' if autotrader_return > spy_return else '(underperformed)'}")
print(f"Autotrader vs NASDAQ:    {autotrader_return - qqq_return:+.2f}% {'(outperformed)' if autotrader_return > qqq_return else '(underperformed)'}")

# Trading days
trading_days = len(spy_hist)
calendar_days = (datetime.now() - datetime(2025, 9, 4)).days

print(f"\nCalendar days in period: {calendar_days}")
print(f"Trading days in period: {trading_days}")
print(f"\nAutotrader daily average: {autotrader_return/trading_days:+.3f}% (per trading day)")
print(f"S&P 500 daily average:    {spy_return/trading_days:+.3f}% (per trading day)")
print(f"NASDAQ 100 daily average: {qqq_return/trading_days:+.3f}% (per trading day)")

# Annualized returns
days_in_year = 365
annualized_autotrader = (1 + autotrader_return/100) ** (days_in_year/calendar_days) - 1
annualized_spy = (1 + spy_return/100) ** (days_in_year/calendar_days) - 1
annualized_qqq = (1 + qqq_return/100) ** (days_in_year/calendar_days) - 1

print(f"\n{'='*100}")
print("ANNUALIZED RETURNS (projected)")
print("="*100)
print(f"Autotrader:  {annualized_autotrader*100:+.2f}%")
print(f"S&P 500:     {annualized_spy*100:+.2f}%")
print(f"NASDAQ 100:  {annualized_qqq*100:+.2f}%")

print("="*100)
print("\nNOTE: Full history shows $4,121.47 P&L from $100,000 initial capital")
print("      This includes:")
print("        - Realized P&L: $3,634.03")
print("        - Unrealized P&L: $487.45")
print("="*100)
