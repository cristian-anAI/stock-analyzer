# add_manual_crypto_position.py
"""
Script to add a manual crypto position (e.g. BNB) to the portfolio for monitoring.
"""

from position_manager import PositionManager
from crypto_data_collector import CryptoDataCollector
from datetime import datetime
import importlib.util

# Import StockDataCollector from data-collector.py
spec = importlib.util.spec_from_file_location("data_collector", "data-collector.py")
spec.loader.exec_module(data_collector)
stock_collector = data_collector.StockDataCollector()

# --- User input ---
symbol = "BNB-USD"  # Use USD for compatibility
entry_price_eur = 616.397
quantity = 0.158
entry_date = "2025-07-17"


# Convert EUR to USD using FX rate from the purchase date
import requests
fx_url = f"https://api.exchangerate.host/convert?from=EUR&to=USD&date={entry_date}"
try:
    fx = requests.get(fx_url).json()
    eur_usd = fx['result']
except Exception:
    eur_usd = 1.1  # fallback
entry_price_usd = round(entry_price_eur * eur_usd, 2)

print(f"Adding manual position: {symbol} | {quantity} @ ${entry_price_usd} (original EUR: {entry_price_eur}) on {entry_date}")

# --- Add to system ---
pos_manager = PositionManager(stock_collector)
pos_manager.add_real_position(symbol, entry_price_usd, quantity, entry_date)
print("Position added!")
