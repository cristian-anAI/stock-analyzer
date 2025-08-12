
import datetime
from typing import Optional
try:
    import yfinance as yf
except ImportError:
    yf = None
try:
    import pandas as pd
except ImportError:
    pd = None

class EarningsChecker:
    EARNINGS_DATE = 'Earnings Date'

    def __init__(self):
        if yf is None:
            raise ImportError("yfinance is required for EarningsChecker")
        if pd is None:
            raise ImportError("pandas is required for EarningsChecker")

    def has_upcoming_earnings(self, symbol: str, days: int = 3) -> bool:
        """
        Returns True if the symbol has earnings in the next `days` days.
        Compatible con yfinance >=0.2.36 (calendar puede ser DataFrame o dict).
        """
        ticker = yf.Ticker(symbol)
        cal = ticker.calendar
        earnings_date = None
        # Soporta DataFrame (antiguo) o dict (nuevo)
        if cal is None:
            return False
        if hasattr(cal, 'empty'):
            if cal.empty:
                return False
            if self.EARNINGS_DATE in cal.index:
                earnings_date = cal.loc[self.EARNINGS_DATE][0]
            elif self.EARNINGS_DATE in cal.columns:
                earnings_date = cal[self.EARNINGS_DATE][0]
        elif isinstance(cal, dict):
            # yfinance >=0.2.36
            if self.EARNINGS_DATE in cal:
                val = cal[self.EARNINGS_DATE]
                if isinstance(val, (list, tuple)) and val:
                    earnings_date = val[0]
                else:
                    earnings_date = val
        if earnings_date is None:
            return False
        if not isinstance(earnings_date, (datetime.datetime, datetime.date)):
            try:
                earnings_date = pd.to_datetime(earnings_date)
            except Exception:
                return False
        today = datetime.datetime.now().date()
        earnings_date_val = earnings_date.date() if hasattr(earnings_date, 'date') else earnings_date
        delta = (earnings_date_val - today).days
        return 0 <= delta <= days
