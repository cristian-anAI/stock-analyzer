"""
Default configuration for crypto-scalper
All strategy parameters in one place
"""

# =============================================================================
# STRATEGY: PupupuV3 (1-minute scalping)
# =============================================================================
PUPUPU_V3 = {
    "ema_period": 15,               # EMA(15) on 1-min candles = 15 min lookback
    "pivot_lookback": 100,           # Rolling window for pivot detection (100 bars)
    "tp1_ratio": 1.0,               # Take Profit 1 at 1:1 risk/reward
    "pivot_touch_threshold": 0.1,    # % threshold for pivot touch detection
    "sl_padding": 2.5,              # Points padding beyond pivot for SL
}

# =============================================================================
# STRATEGY: PupupuV2 (5-minute scalping)
# =============================================================================
PUPUPU_V2 = {
    "ema_period": 12,               # EMA(12) on 5-min candles = 60 min lookback
    "pivot_lookback": 400,           # Rolling window for pivot detection (400 bars = ~33h)
    "swing_bars": 5,                # Bars on each side for swing detection
    "tp_rr": 1.7,                   # Take Profit at 1.7:1 risk/reward
    "sl_padding": 2.5,              # Points padding beyond pivot for SL
    "cooldown_candles": 5,          # Min candles between signals
}

# =============================================================================
# RISK MANAGEMENT
# =============================================================================
RISK = {
    "capital": 30000,               # Total capital in USD
    "risk_per_trade_pct": 0.02,     # 2% risk per trade ($600)
    "risk_reduced_pct": 0.01,       # 1% reduced risk (against VWAP bias)
    "max_concurrent_trades": 3,      # Max open trades simultaneously
    "max_daily_loss_pct": 0.06,     # 6% max daily loss ($1800) -> stop trading
    "max_daily_trades": 10,          # Max trades per day
}

# =============================================================================
# VOLUME PROFILE
# =============================================================================
VOLUME_PROFILE = {
    "lookback_days": 7,             # 7-day volume profile
    "num_bins": 60,                 # Price level granularity
    "hvn_threshold_pct": 0.5,       # % distance to consider "near" HVN
    "lvn_threshold_pct": 0.3,       # % distance to consider "near" LVN
    "value_area_pct": 0.70,         # 70% of volume defines value area
}

# =============================================================================
# VWAP FILTER
# =============================================================================
VWAP = {
    "session_reset_hour": 0,        # Reset VWAP at midnight UTC (crypto)
    "neutral_threshold_pct": 0.05,  # % distance to consider "at" VWAP
}

# =============================================================================
# DATA SOURCE
# =============================================================================
EXCHANGE = {
    "name": "binance",              # Exchange (binance, bybit, etc.)
    "symbol": "BTC/USDT",           # Default trading pair
    "timeframe_primary": "1m",      # Primary timeframe for V3
    "timeframe_v2": "5m",           # Primary timeframe for V2
    "use_testnet": True,            # Use testnet by default (safety)
}

# =============================================================================
# TELEGRAM NOTIFICATIONS
# =============================================================================
TELEGRAM = {
    "enabled": False,               # Disabled by default
    "bot_token": "",                # Set via env var TELEGRAM_BOT_TOKEN
    "chat_id": "",                  # Set via env var TELEGRAM_CHAT_ID
}

# =============================================================================
# BACKTESTING
# =============================================================================
BACKTEST = {
    "initial_capital": 30000,
    "commission_pct": 0.001,        # 0.1% per trade (taker fee)
    "slippage_pct": 0.0005,         # 0.05% slippage estimate
    "data_source": "ccxt",          # ccxt for historical data
}
