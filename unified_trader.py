# unified_trader.py
"""
UnifiedTrader: Handles both stocks and crypto with separate limits and risk management.
- max_crypto_positions, max_stock_positions
- Uses existing PositionManager, CryptoDataCollector, and StockDataCollector
- Calls crypto_specific_analysis for crypto, stock analysis for stocks
"""
from crypto_data_collector import CryptoDataCollector
from crypto_watchlist import CRYPTO_WATCHLIST
from crypto_specific_analysis import analyze_crypto_signals
# from stock_data_collector import StockDataCollector  # assumed to exist
# from stock_analysis import analyze_stock_signals     # assumed to exist
from position_manager import PositionManager

class UnifiedTrader:
    def __init__(self, stock_collector, crypto_collector=None, position_manager=None,
                 max_stock_positions=8, max_crypto_positions=4, max_investment_per_stock=5000, max_investment_per_crypto=2000):
        self.stock_collector = stock_collector
        self.crypto_collector = crypto_collector or CryptoDataCollector()
        self.position_manager = position_manager or PositionManager()
        self.max_stock_positions = max_stock_positions
        self.max_crypto_positions = max_crypto_positions
        self.max_investment_per_stock = max_investment_per_stock
        self.max_investment_per_crypto = max_investment_per_crypto

    def run_cycle(self):
        # --- STOCKS ---
        stock_opportunities = []
        # for symbol in STOCK_WATCHLIST:
        #     stock_data = self.stock_collector.get_stock_data(symbol)
        #     score, reasons = analyze_stock_signals(stock_data)
        #     if score >= 5:
        #         stock_opportunities.append({"symbol": symbol, "score": score, "reasons": reasons})
        # # Open stock positions up to max_stock_positions
        # ...existing code for stocks...

        # --- CRYPTO ---
        crypto_opportunities = []
        for coin in CRYPTO_WATCHLIST:
            symbol = coin["symbol"]
            data = self.crypto_collector.get_yfinance_data(symbol)
            if data is None or data.empty:
                continue
            # Ensure 'close' column exists (yfinance returns 'Close' by default)
            if "close" not in data.columns and "Close" in data.columns:
                data["close"] = data["Close"]
            tech_ind = data.iloc[-1].to_dict()
            price_data = {"close": tech_ind.get("close")}
            # Optionally add pct_change_24h if available
            score, reasons = analyze_crypto_signals(tech_ind, price_data)
            if score >= 5:
                crypto_opportunities.append({"symbol": symbol, "score": score, "reasons": reasons})
        # Open crypto positions up to max_crypto_positions
        # ...existing code for crypto position management...
        return {"stock_opportunities": stock_opportunities, "crypto_opportunities": crypto_opportunities}
