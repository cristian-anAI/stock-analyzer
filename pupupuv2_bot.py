"""
PupupuV2 Scalping Bot - Main Orchestrator

Semi-automatic trading system that generates alerts when high-probability
setups are detected. User manually executes trades to avoid fundamental events
like Trump speeches, NFP, FOMC, etc.

Architecture:
1. Fetch real-time BTC/USDT 5-min data from Binance
2. Calculate Volume Profile (4h, 24h, 7d contexts)
3. Detect pivots using Pupupu logic
4. Generate signals when pivot touch + EMA cross occurs
5. Apply market filters (liquidity, volatility, events)
6. Calculate position size based on risk management
7. Alert user with complete trade plan
"""

import sys
import time
import json
from datetime import datetime, timedelta
from typing import Optional, Dict

# Add project root to path
sys.path.append('c:/repos/stock-analyzer')

from src.data.binance_client import BinanceDataClient
from src.indicators.volume_profile import get_multi_timeframe_vp
from src.strategy.pupupuv2_signals import PupupuV2Strategy, TradeSignal
from src.risk.position_sizer import calculate_position_size, validate_risk_limits
from src.filters.market_context import apply_all_filters, should_trade_direction


class PupupuV2Bot:
    """
    Main bot orchestrator for pupupuv2 scalping strategy.

    Config:
    - symbol: Trading pair (default: BTC/USDT)
    - timeframe: Candle timeframe (default: 5m)
    - account_balance: Capital in USD
    - risk_per_trade: % of capital to risk (default: 0.02 = 2%)
    - max_position_size: Max position size in USD
    """

    def __init__(self, config: Optional[Dict] = None):
        if config is None:
            config = {}

        # Trading config
        self.symbol = config.get('symbol', 'BTC/USDT')
        self.timeframe = config.get('timeframe', '5m')
        self.account_balance = config.get('account_balance', 10000)
        self.risk_per_trade = config.get('risk_per_trade', 0.02)
        self.max_position_size = config.get('max_position_size', 5000)

        # Initialize components
        self.binance_client = BinanceDataClient()
        self.strategy = PupupuV2Strategy({
            'ema_period': 12,
            'lookback_periods': 400,
            'tp_rr': 1.7,
            'sl_padding': 2.5
        })

        # State
        self.last_signal_time = None
        self.signal_cooldown_minutes = config.get('signal_cooldown', 15)
        self.running = False

        print(f"[{datetime.now().strftime('%H:%M:%S')}] PupupuV2 Bot initialized")
        print(f"Symbol: {self.symbol}")
        print(f"Timeframe: {self.timeframe}")
        print(f"Account: ${self.account_balance:,.2f}")
        print(f"Risk per trade: {self.risk_per_trade:.1%}")

    def run_continuous(self, check_interval_seconds: int = 60):
        """
        Run bot in continuous mode - checks for signals every N seconds.

        Args:
            check_interval_seconds: Seconds between checks (default: 60)
        """
        self.running = True
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Starting continuous monitoring...")
        print(f"Checking every {check_interval_seconds} seconds")
        print("Press Ctrl+C to stop\n")

        iteration = 0

        try:
            while self.running:
                iteration += 1
                print(f"\n{'='*70}")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Iteration #{iteration}")
                print(f"{'='*70}")

                # Run analysis
                signal = self.analyze_and_generate_signal()

                if signal:
                    self._alert_user(signal)
                    self.last_signal_time = datetime.now()
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] No signal - waiting...")

                # Wait for next check
                time.sleep(check_interval_seconds)

        except KeyboardInterrupt:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Bot stopped by user")
            self.running = False

    def run_single_check(self) -> Optional[TradeSignal]:
        """
        Run a single analysis check (for testing/manual use).

        Returns:
            TradeSignal if found, None otherwise
        """
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Running single analysis...")
        return self.analyze_and_generate_signal()

    def analyze_and_generate_signal(self) -> Optional[TradeSignal]:
        """
        Main analysis pipeline.

        Steps:
        1. Fetch fresh data (5m and 1h)
        2. Check signal cooldown
        3. Calculate Volume Profile
        4. Run strategy to find setup
        5. Apply market filters
        6. Calculate position size
        7. Validate risk limits

        Returns:
            Complete TradeSignal or None
        """
        # 1. Fetch data
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching data from Binance...")
        try:
            data = self.binance_client.fetch_multiple_timeframes(
                self.symbol,
                ['5m', '1h'],
                limit=500
            )
            ohlcv_5m = data['5m']
            ohlcv_1h = data['1h']

            if ohlcv_5m is None:
                print(f"[ERROR] Could not fetch 5m data")
                return None

            current_price = ohlcv_5m[-1, 4]
            print(f"[OK] Current {self.symbol} price: ${current_price:,.2f}")

        except Exception as e:
            print(f"[ERROR] Data fetch failed: {e}")
            return None

        # 2. Check cooldown
        if self._is_in_cooldown():
            mins_left = self._cooldown_minutes_remaining()
            print(f"[COOLDOWN] {mins_left:.1f} minutes remaining since last signal")
            return None

        # 3. Calculate Volume Profile
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Calculating Volume Profile...")
        try:
            # Use last 2016 candles for VP (7 days)
            vp_data = get_multi_timeframe_vp(ohlcv_5m[-2016:], num_bins=60)
            print(f"[OK] VP calculated - POC (4h): ${vp_data['vp_corto']['poc']:,.2f}")
        except Exception as e:
            print(f"[WARNING] VP calculation failed: {e}")
            vp_data = None

        # 4. Run strategy
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Analyzing for trade setups...")
        signal = self.strategy.analyze_for_signals(ohlcv_5m, vp_data)

        if not signal:
            print(f"[NO SETUP] No valid pivot touch + EMA cross found")
            self._show_active_levels()
            return None

        print(f"\n[SETUP FOUND] {signal.direction} signal detected!")
        print(f"Entry: ${signal.entry_price:,.2f}")
        print(f"Confidence: {signal.confidence:.1%}")

        # 5. Apply market filters
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Applying market filters...")
        current_candle = {
            'timestamp': ohlcv_5m[-1, 0],
            'open': ohlcv_5m[-1, 1],
            'high': ohlcv_5m[-1, 2],
            'low': ohlcv_5m[-1, 3],
            'close': ohlcv_5m[-1, 4],
            'volume': ohlcv_5m[-1, 5]
        }

        filters = apply_all_filters(current_candle, ohlcv_5m, ohlcv_1h)

        if not filters['pass_all']:
            print(f"[FILTERED OUT] Signal blocked by filters:")
            if filters['fundamental_event'][0]:
                print(f"  - Fundamental event: {filters['fundamental_event'][1]}")
            if not filters['liquidity'][0]:
                print(f"  - Low liquidity: {filters['liquidity'][1]}")
            if not filters['volatility'][0]:
                print(f"  - High volatility: {filters['volatility'][1]}")
            return None

        print(f"[OK] All filters passed")
        print(f"  HT Trend: {filters['ht_trend'][0]}")

        # Optional: Check trend alignment
        # should_trade, reason = should_trade_direction(
        #     signal.direction,
        #     filters['ht_trend'][0],
        #     require_trend_alignment=False
        # )
        # if not should_trade:
        #     print(f"[FILTERED] {reason}")
        #     return None

        # 6. Calculate position size
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Calculating position size...")
        sizing = calculate_position_size(
            self.account_balance,
            self.risk_per_trade,
            signal.entry_price,
            signal.stop_loss,
            max_position_usd=self.max_position_size
        )

        signal.position_size_usd = sizing['position_size_usd']
        signal.risk_usd = sizing['risk_usd']

        print(f"[OK] Position size: ${signal.position_size_usd:,.2f}")
        print(f"     Risk: ${signal.risk_usd:,.2f} ({sizing['risk_pct']:.2f}%)")

        # 7. Validate risk limits
        validation = validate_risk_limits(
            signal.position_size_usd,
            signal.risk_usd,
            self.account_balance
        )

        if not validation['valid']:
            print(f"[RISK ERROR] {', '.join(validation['violations'])}")
            return None

        if validation['warnings']:
            print(f"[WARNINGS] {', '.join(validation['warnings'])}")

        return signal

    def _alert_user(self, signal: TradeSignal):
        """
        Alert user about trade signal.

        In production, this could:
        - Send Telegram message
        - Play sound alert
        - Send email
        - Log to file
        """
        print("\n" + "!"*70)
        print("🚨 TRADE ALERT 🚨")
        print("!"*70)
        print(signal)

        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"signals/signal_{signal.direction}_{timestamp}.json"

        try:
            import os
            os.makedirs('signals', exist_ok=True)

            with open(filename, 'w') as f:
                json.dump(signal.to_dict(), f, indent=2)

            print(f"\n[SAVED] Signal saved to: {filename}")
        except Exception as e:
            print(f"\n[WARNING] Could not save signal: {e}")

        # TODO: Add Telegram/email notification here
        print("\n" + "!"*70)
        print("⚠️  MANUAL EXECUTION REQUIRED - Check for fundamental events!")
        print("!"*70)

    def _show_active_levels(self):
        """Display currently active support/resistance levels."""
        levels = self.strategy.get_active_levels()

        if levels['resistances']:
            print(f"\nActive resistances ({len(levels['resistances'])}):")
            for p in levels['resistances'][:3]:
                print(f"  ${p.price:,.2f} - strength={p.strength:.2f}, touches={p.touches}")

        if levels['supports']:
            print(f"\nActive supports ({len(levels['supports'])}):")
            for p in levels['supports'][:3]:
                print(f"  ${p.price:,.2f} - strength={p.strength:.2f}, touches={p.touches}")

    def _is_in_cooldown(self) -> bool:
        """Check if we're still in cooldown from last signal."""
        if self.last_signal_time is None:
            return False

        elapsed = datetime.now() - self.last_signal_time
        return elapsed.total_seconds() < (self.signal_cooldown_minutes * 60)

    def _cooldown_minutes_remaining(self) -> float:
        """Get remaining cooldown time in minutes."""
        if self.last_signal_time is None:
            return 0

        elapsed = datetime.now() - self.last_signal_time
        remaining_sec = (self.signal_cooldown_minutes * 60) - elapsed.total_seconds()
        return max(0, remaining_sec / 60)


# ==================== MAIN ENTRY POINT ====================

if __name__ == "__main__":
    print("="*70)
    print("PUPUPUV2 SCALPING BOT")
    print("="*70)
    print("Semi-automatic trading system for BTC/USDT 5-min scalping")
    print("Generates alerts - manual execution required")
    print("="*70)

    # Configuration
    bot_config = {
        'symbol': 'BTC/USDT',
        'timeframe': '5m',
        'account_balance': 10000,  # $10k account
        'risk_per_trade': 0.02,     # 2% risk per trade
        'max_position_size': 5000,  # Max $5k per position
        'signal_cooldown': 15       # 15 minutes between signals
    }

    bot = PupupuV2Bot(bot_config)

    # Choose mode
    print("\nSelect mode:")
    print("1. Single check (analyze once)")
    print("2. Continuous monitoring (check every 60s)")

    choice = input("\nEnter choice (1 or 2): ").strip()

    if choice == "1":
        # Single check mode
        signal = bot.run_single_check()

        if signal:
            bot._alert_user(signal)
        else:
            print(f"\n[NO SIGNAL] No valid setup found")
            bot._show_active_levels()

    elif choice == "2":
        # Continuous mode
        bot.run_continuous(check_interval_seconds=60)

    else:
        print("Invalid choice - exiting")
