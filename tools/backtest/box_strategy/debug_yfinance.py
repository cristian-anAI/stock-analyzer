"""Debug yfinance data for SPX and NDX"""
import yfinance as yf
from datetime import datetime, timedelta

end = datetime(2025, 10, 4)
start = end - timedelta(days=5)

print("="*80)
print("DOWNLOADING ES=F (SPX FUTURES)")
print("="*80)
spx = yf.download('ES=F', start=start, end=end, interval='5m', progress=False)
print(f"Shape: {spx.shape}")
print(f"Columns: {spx.columns.tolist()}")
print(f"\nOct 3 data:")
try:
    oct3_spx = spx[spx.index.date == datetime(2025, 10, 3).date()]
    if len(oct3_spx) > 0:
        print(f"  Rows: {len(oct3_spx)}")
        print(f"  Close range: {oct3_spx['Close'].min():.2f} - {oct3_spx['Close'].max():.2f}")
        print(f"  10:00 AM close: {oct3_spx[oct3_spx.index.hour == 10].iloc[0]['Close'] if len(oct3_spx[oct3_spx.index.hour == 10]) > 0 else 'N/A'}")
    else:
        print("  No data for Oct 3")
except Exception as e:
    print(f"  Error: {e}")

print("\n" + "="*80)
print("DOWNLOADING NQ=F (NDX FUTURES)")
print("="*80)
ndx = yf.download('NQ=F', start=start, end=end, interval='5m', progress=False)
print(f"Shape: {ndx.shape}")
print(f"Columns: {ndx.columns.tolist()}")
print(f"\nOct 3 data:")
try:
    oct3_ndx = ndx[ndx.index.date == datetime(2025, 10, 3).date()]
    if len(oct3_ndx) > 0:
        print(f"  Rows: {len(oct3_ndx)}")
        print(f"  Close range: {oct3_ndx['Close'].min():.2f} - {oct3_ndx['Close'].max():.2f}")
        print(f"  10:00 AM close: {oct3_ndx[oct3_ndx.index.hour == 10].iloc[0]['Close'] if len(oct3_ndx[oct3_ndx.index.hour == 10]) > 0 else 'N/A'}")
    else:
        print("  No data for Oct 3")
except Exception as e:
    print(f"  Error: {e}")

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)

if spx.shape == ndx.shape:
    first_spx = spx.iloc[0]['Close']
    first_ndx = ndx.iloc[0]['Close']

    if abs(first_spx - first_ndx) < 1.0:
        print("[BUG] SPX and NDX have IDENTICAL data!")
        print(f"Both start at close: {first_spx:.2f}")
    else:
        print("[OK] SPX and NDX have DIFFERENT data")
        print(f"SPX starts at: {first_spx:.2f}")
        print(f"NDX starts at: {first_ndx:.2f}")
else:
    print("[OK] SPX and NDX have different shapes (likely different data)")
