"""
PupupuV3 Bot - Main Orchestrator

Integrates all PupupuV3 components:
- 1-minute data fetching (Binance)
- EMA(15) calculation
- Pivot detection (100 lookback)
- VWAP filter
- 7-day Volume Profile
- ML predictions
- Trade lifecycle management
- Database persistence

Modes:
- monitor: Continuous monitoring with 60s polling
- check: Single check for signals
"""

import sys
import time
import argparse
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from src.data.binance_client_v3 import BinanceClientV3
from src.strategy.pupupuv3_signals import PupupuV3Strategy, signal_to_dict
from src.core.trade_lifecycle_manager_v3 import TradeLifecycleManager
from src.data.database_pupupuv3 import PupupuV3Database


class PupupuV3Bot:
    """
    Main bot orchestrator for PupupuV3 strategy
    """

    def __init__(
        self,
        symbol: str = "BTC/USDT",
        capital: float = 30000,
        cache_dir: str = "cache",
        db_path: str = "pupupuv3.db"
    ):
        """
        Initialize bot

        Args:
            symbol: Trading pair
            capital: Trading capital
            cache_dir: Directory for data caching
            db_path: Database file path
        """
        self.symbol = symbol
        self.capital = capital

        # Configuration
        self.config = {
            'ema_period': 15,
            'pivot_lookback': 100,
            'capital_crypto': capital,
            'risk_per_trade_pct': 0.02,
            'risk_reduced_pct': 0.01,
            'tp1_ratio': 1.0,
            'pivot_touch_threshold': 0.1
        }

        # Initialize components
        print(f"Initializing PupupuV3 Bot for {symbol}...")
        print(f"Capital: ${capital:,}")

        self.data_client = BinanceClientV3(cache_dir=cache_dir)
        self.strategy = PupupuV3Strategy(self.config)
        self.trade_manager = TradeLifecycleManager()
        self.db = PupupuV3Database(db_path)

        print("[OK] Bot initialized")

    def run_single_check(self):
        """
        Run a single check for signals
        """
        print(f"\n{'='*70}")
        print(f"SINGLE CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")

        try:
            # Fetch data
            print(f"\nFetching 1-min data for {self.symbol}...")
            ohlcv_data = self.data_client.get_1min_data(self.symbol, days=7)
            current_price = ohlcv_data[-1, 4]
            print(f"Current Price: ${current_price:.2f}")
            print(f"Data: {len(ohlcv_data)} candles")

            # Check for signal
            print(f"\nAnalyzing for signals...")
            signal = self.strategy.analyze_for_signals(ohlcv_data, self.symbol)

            if signal:
                self._handle_signal(signal)
            else:
                print("No signal detected")

            # Update active trades
            self._update_active_trades(ohlcv_data)

            # Show summary
            self._show_summary()

        except Exception as e:
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()

    def run_continuous_monitor(self, check_interval: int = 60):
        """
        Run continuous monitoring mode

        Args:
            check_interval: Seconds between checks (default: 60)
        """
        print(f"\n{'='*70}")
        print(f"CONTINUOUS MONITORING MODE")
        print(f"{'='*70}")
        print(f"Symbol: {self.symbol}")
        print(f"Check Interval: {check_interval}s")
        print(f"Press Ctrl+C to stop")
        print(f"{'='*70}\n")

        iteration = 0

        try:
            while True:
                iteration += 1
                print(f"\n--- Iteration {iteration} - {datetime.now().strftime('%H:%M:%S')} ---")

                try:
                    # Fetch latest data
                    ohlcv_data = self.data_client.get_1min_data(self.symbol, days=7, use_cache=True)
                    current_price = ohlcv_data[-1, 4]
                    print(f"Current Price: ${current_price:.2f}")

                    # Check for signals
                    signal = self.strategy.analyze_for_signals(ohlcv_data, self.symbol)

                    if signal:
                        print(f"\n[SIGNAL DETECTED] {signal.direction}")
                        self._handle_signal(signal)
                    else:
                        print("No new signals")

                    # Update active trades
                    active_count = self._update_active_trades(ohlcv_data)

                    if active_count > 0:
                        print(f"Active trades: {active_count}")

                except Exception as e:
                    print(f"[ERROR] Iteration error: {e}")

                # Wait for next check
                print(f"Waiting {check_interval}s for next check...")
                time.sleep(check_interval)

        except KeyboardInterrupt:
            print("\n\n[STOPPED] Bot stopped by user")
            self._show_summary()

    def _handle_signal(self, signal):
        """Process a detected signal"""
        signal_dict = signal_to_dict(signal)

        print(f"\n{'='*60}")
        print(f"SIGNAL: {signal.direction}")
        print(f"{'='*60}")
        print(f"Entry: ${signal.entry_price:.2f}")
        print(f"SL: ${signal.stop_loss:.2f}")
        print(f"TP1: ${signal.take_profit_1:.2f}")
        print(f"")
        print(f"Pivot: ${signal.pivot_price:.2f} ({signal.pivot_type}) | Strength: {signal.pivot_strength:.1f}")
        print(f"EMA: ${signal.ema_value:.2f} | Cross: {signal.cross_type}")
        print(f"")
        print(f"VWAP: ${signal.vwap_value:.2f} | Bias: {signal.vwap_bias}")
        print(f"With VWAP: {'YES' if signal.with_vwap_bias else 'NO'}")
        print(f"")
        print(f"ML Confidence: {signal.ml_confidence:.1f}%")
        print(f"Risk: ${signal.risk_usd:.2f} (multiplier: {signal.risk_multiplier})")
        print(f"Position Size: ${signal.position_size_usd:.2f}")
        print(f"")
        print(f"Valid: {'YES' if signal.is_valid else 'NO'}")
        print(f"Reason: {signal.reason}")
        print(f"{'='*60}")

        # Save to database
        self.db.save_signal(signal_dict)
        print("[OK] Signal saved to database")

        # Create trade if valid
        if signal.is_valid:
            trade = self.trade_manager.create_trade_from_signal(
                signal_id=signal.signal_id,
                symbol=signal.symbol,
                direction=signal.direction,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profit_1=signal.take_profit_1,
                position_size_usd=signal.position_size_usd,
                position_size_units=signal.position_size_usd / signal.entry_price,
                ema_value=signal.ema_value
            )

            # In semi-automatic mode, the trade stays PENDING until manual entry
            # For testing, we can auto-activate it
            # self.trade_manager.activate_trade(trade.trade_id, int(datetime.now().timestamp() * 1000))

            self.db.save_trade(trade)
            print(f"[OK] Trade created: {trade.trade_id} (PENDING manual entry)")

    def _update_active_trades(self, ohlcv_data):
        """Update all active trades with current market data"""
        active_trades = self.trade_manager.get_active_trades()

        if not active_trades:
            return 0

        current_candle = ohlcv_data[-1]
        current_price = current_candle[4]
        current_timestamp = int(current_candle[0])

        # Calculate current EMA
        closes = ohlcv_data[:, 4]
        from src.indicators.ema import calculate_ema
        ema_values = calculate_ema(closes, period=self.config['ema_period'])
        current_ema = ema_values[-1]

        for trade in active_trades:
            result = self.trade_manager.update_trade(
                trade.trade_id,
                current_price=current_price,
                current_ema=current_ema,
                timestamp=current_timestamp
            )

            if result:
                print(f"\n[TRADE UPDATE] {trade.trade_id}: {result}")

                # Update in database
                self.db.update_trade(trade)

        return len(active_trades)

    def _show_summary(self):
        """Show bot summary"""
        print(f"\n{'='*70}")
        print(f"BOT SUMMARY")
        print(f"{'='*70}")

        # Database statistics
        stats = self.db.get_statistics(days=30)

        print(f"\nSignals (last 30 days):")
        print(f"  Total: {stats['signals_total']}")
        print(f"  Valid: {stats['signals_valid']}")

        print(f"\nTrades:")
        print(f"  Total: {stats['trades_total']}")
        print(f"  Wins: {stats['trades_wins']} ({stats['win_rate']:.2f}%)")
        print(f"  Losses: {stats['trades_losses']}")
        print(f"  Total PnL: ${stats['total_pnl']:.2f}")

        if stats['trades_wins'] > 0:
            print(f"  Avg Win: ${stats['avg_win']:.2f}")
        if stats['trades_losses'] > 0:
            print(f"  Avg Loss: ${stats['avg_loss']:.2f}")

        print(f"  NO_TEST Count: {stats['no_test_count']}")

        # Active trades
        active = self.trade_manager.get_active_trades()
        print(f"\nActive Trades: {len(active)}")

        for trade in active:
            print(f"  - {trade.trade_id}: {trade.direction} @ ${trade.entry_price:.2f} | State: {trade.state.value}")

        print(f"{'='*70}\n")

    def close(self):
        """Cleanup and close connections"""
        print("\nClosing bot...")
        self.db.close()
        print("[OK] Database closed")


def main():
    """Main entry point for command line"""
    parser = argparse.ArgumentParser(description='PupupuV3 Trading Bot')

    parser.add_argument(
        '--mode',
        type=str,
        choices=['check', 'monitor'],
        default='check',
        help='Bot mode: check (single) or monitor (continuous)'
    )

    parser.add_argument(
        '--symbol',
        type=str,
        default='BTC/USDT',
        help='Trading pair (default: BTC/USDT)'
    )

    parser.add_argument(
        '--capital',
        type=float,
        default=30000,
        help='Trading capital (default: 30000)'
    )

    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Check interval in seconds for monitor mode (default: 60)'
    )

    args = parser.parse_args()

    # Initialize bot
    bot = PupupuV3Bot(
        symbol=args.symbol,
        capital=args.capital
    )

    try:
        if args.mode == 'check':
            bot.run_single_check()
        else:
            bot.run_continuous_monitor(check_interval=args.interval)

    finally:
        bot.close()


if __name__ == "__main__":
    main()
