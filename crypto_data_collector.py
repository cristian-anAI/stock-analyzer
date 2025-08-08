# crypto_data_collector.py
"""
CryptoDataCollector: Fetches crypto data and computes technical indicators (RSI, MACD, Bollinger Bands).
Supports yfinance for BTC-USD, ETH-USD and CoinGecko API for altcoins.
"""
import yfinance as yf
import requests
import pandas as pd

class CryptoDataCollector:
    def __init__(self):
        self.coingecko_url = "https://api.coingecko.com/api/v3"

    def get_yfinance_data(self, symbol, period="90d", interval="1h"):
        try:
            data = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)
            if data.empty:
                print(f"No data returned for {symbol}")
                return None
            print(f"Raw columns for {symbol}: {data.columns.tolist()}")
            # Fix MultiIndex issue FIRST
            if isinstance(data.columns, pd.MultiIndex):
                print(f"MultiIndex detected, flattening...")
                data.columns = data.columns.droplevel(1)  # Remove ticker level
            print(f"After MultiIndex fix: {data.columns.tolist()}")
            # Normalize column names (handle both 'Close' and 'close')
            column_mapping = {}
            for col in data.columns:
                col_lower = col.lower().strip()
                if 'close' in col_lower:
                    column_mapping[col] = 'close'
                elif 'open' in col_lower:
                    column_mapping[col] = 'open'
                elif 'high' in col_lower:
                    column_mapping[col] = 'high'
                elif 'low' in col_lower:
                    column_mapping[col] = 'low'
                elif 'volume' in col_lower:
                    column_mapping[col] = 'volume'
            data = data.rename(columns=column_mapping)
            print(f"After renaming: {data.columns.tolist()}")
            # Verify we have close column
            if 'close' not in data.columns:
                print(f"Available columns: {data.columns.tolist()}")
                raise KeyError(f"No 'close' column found after processing for {symbol}")
            print(f"Success! Close price sample: {data['close'].tail(3).values}")
            return self._add_indicators(data)
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return None

    def get_coingecko_data(self, coin_id, days=90):
        url = f"{self.coingecko_url}/coins/{coin_id}/market_chart"
        params = {"vs_currency": "usd", "days": days}
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            return None
        prices = resp.json().get("prices", [])
        df = pd.DataFrame(prices, columns=["timestamp", "price"])
        df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("date", inplace=True)
        df["close"] = df["price"]
        return self._add_indicators(df[["close"]])

    def _add_indicators(self, df):
        try:
            if 'close' not in df.columns:
                raise ValueError(f"Missing 'close' column. Available: {df.columns.tolist()}")
            if len(df) < 20:
                print(f"Warning: Only {len(df)} rows, indicators may be incomplete")
            # RSI (need at least 15 periods)
            if len(df) >= 15:
                delta = df["close"].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df["rsi"] = 100 - (100 / (1 + rs))
            else:
                df["rsi"] = None
            # MACD (need at least 26 periods)
            if len(df) >= 26:
                ema12 = df["close"].ewm(span=12, adjust=False).mean()
                ema26 = df["close"].ewm(span=26, adjust=False).mean()
                df["macd"] = ema12 - ema26
                df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
            else:
                df["macd"] = None
                df["macd_signal"] = None
            # Bollinger Bands (need at least 20 periods)
            if len(df) >= 20:
                ma20 = df["close"].rolling(window=20).mean()
                std20 = df["close"].rolling(window=20).std()
                df["bb_upper"] = ma20 + 2 * std20
                df["bb_lower"] = ma20 - 2 * std20
            else:
                df["bb_upper"] = None
                df["bb_lower"] = None
            return df
        except Exception as e:
            print(f"Error calculating indicators: {e}")
            return df  # Return original df even if indicators fail
