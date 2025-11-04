"""
Daily Automated Learning System

Automatically collects completed trades and retrains ML models with new data.
Runs when computer is on, scheduled to execute daily after market close.

Architecture:
1. Trade Logger: Collects completed trades from daily activity
2. Data Aggregator: Combines new trades with historical data
3. Incremental Trainer: Retrains models when threshold reached
4. Scheduler: Runs daily at market close (5:00 PM ET)

Usage:
    # Run once to collect today's trades and retrain if needed
    python daily_learning_system.py --run-once

    # Run in background with scheduler (checks every hour)
    python daily_learning_system.py --daemon

    # Manual: Add a completed trade
    python daily_learning_system.py --add-trade trade_data.json

    # Manual: Force retrain with accumulated trades
    python daily_learning_system.py --force-retrain
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, time, timedelta
from typing import List, Dict, Optional
import schedule
import time as time_module
import subprocess

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from data_loader import DataLoader


class TradeLogger:
    """
    Logs completed trades for daily learning

    Stores trades in daily_trades/ directory with standardized format
    """

    def __init__(self, storage_dir: str = "tools/backtest/box_strategy/daily_trades"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def log_trade(self, trade: Dict) -> Path:
        """
        Log a completed trade

        Args:
            trade: Trade dictionary with all required fields

        Returns:
            Path to saved trade file
        """
        # Validate required fields
        required_fields = [
            'market', 'date', 'direction', 'entry_price', 'exit_price',
            'entry_time', 'exit_time', 'outcome', 'pnl_points',
            'box_high', 'box_low', 'box_range', 'stop_loss'
        ]

        missing = [f for f in required_fields if f not in trade]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        # Add timestamp
        trade['logged_at'] = datetime.now().isoformat()

        # Generate filename: MARKET_DATE_DIRECTION_TIMESTAMP.json
        date_str = trade['date'].replace('-', '')
        timestamp = datetime.now().strftime('%H%M%S')
        filename = f"{trade['market']}_{date_str}_{trade['direction']}_{timestamp}.json"

        filepath = self.storage_dir / filename

        # Save trade
        with open(filepath, 'w') as f:
            json.dump(trade, f, indent=2)

        print(f"[LOGGED] Trade saved: {filepath}")
        return filepath

    def get_pending_trades(self) -> List[Dict]:
        """
        Get all trades that haven't been used for training yet

        Returns:
            List of trade dictionaries
        """
        pending = []

        for trade_file in sorted(self.storage_dir.glob("*.json")):
            # Skip if already processed (marked by .trained suffix)
            if trade_file.with_suffix('.json.trained').exists():
                continue

            with open(trade_file, 'r') as f:
                trade = json.load(f)
                pending.append({
                    'trade': trade,
                    'file': trade_file
                })

        return pending

    def mark_as_trained(self, trade_files: List[Path]):
        """Mark trades as used for training"""
        for trade_file in trade_files:
            marker = trade_file.with_suffix('.json.trained')
            marker.touch()
            print(f"[TRAINED] Marked: {trade_file.name}")

    def get_trade_count(self) -> Dict[str, int]:
        """Get count of pending vs trained trades"""
        all_trades = list(self.storage_dir.glob("*.json"))
        trained = list(self.storage_dir.glob("*.json.trained"))

        return {
            'total': len(all_trades),
            'pending': len(all_trades) - len(trained),
            'trained': len(trained)
        }


class IncrementalTrainer:
    """
    Handles incremental model training with new trades

    Combines historical backtest data with new daily trades
    """

    def __init__(self, min_new_trades: int = 5):
        """
        Initialize trainer

        Args:
            min_new_trades: Minimum new trades before retraining (default: 5)
        """
        self.min_new_trades = min_new_trades
        self.results_dir = Path("tools/backtest/box_strategy/results")
        self.daily_trades_dir = Path("tools/backtest/box_strategy/daily_trades")
        self.models_dir = Path("tools/backtest/box_strategy/models")

    def should_retrain(self, pending_count: int) -> bool:
        """Check if we have enough new trades to retrain"""
        return pending_count >= self.min_new_trades

    def get_latest_backtest_data(self) -> Optional[Path]:
        """Get most recent backtest results file"""
        if not self.results_dir.exists():
            return None

        json_files = sorted(
            self.results_dir.glob("multi_market_results_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        return json_files[0] if json_files else None

    def merge_trades(self, backtest_file: Path, daily_trades: List[Dict]) -> Path:
        """
        Merge backtest data with new daily trades

        Args:
            backtest_file: Path to backtest results JSON
            daily_trades: List of new trade dictionaries

        Returns:
            Path to merged data file
        """
        # Load backtest data
        with open(backtest_file, 'r') as f:
            backtest_data = json.load(f)

        # Convert daily trades to backtest format
        for trade_entry in daily_trades:
            trade = trade_entry['trade']
            market = trade['market']

            # Create trade entry in backtest format
            backtest_trade = {
                'date': trade['date'],
                'direction': trade['direction'],
                'entry_price': trade['entry_price'],
                'entry_time': trade['entry_time'],
                'exit_price': trade['exit_price'],
                'exit_time': trade['exit_time'],
                'outcome': trade['outcome'],
                'pnl': trade['pnl_points'],
                'box_high': trade['box_high'],
                'box_low': trade['box_low'],
                'box_range': trade['box_range'],
                'stop_loss': trade['stop_loss'],
                'tp1': trade.get('tp1'),
                'tp2': trade.get('tp2'),
                'tp3': trade.get('tp3'),
                'source': 'daily_learning'  # Mark as from daily learning
            }

            # Add to appropriate market
            if market not in backtest_data:
                backtest_data[market] = {
                    'trades': [],
                    'metrics': {}
                }

            backtest_data[market]['trades'].append(backtest_trade)

        # Save merged data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        merged_file = self.results_dir / f"merged_data_{timestamp}.json"

        with open(merged_file, 'w') as f:
            json.dump(backtest_data, f, indent=2)

        print(f"[MERGED] Combined {len(daily_trades)} new trades with backtest data")
        print(f"[SAVED] {merged_file}")

        return merged_file

    def train_models(self, data_file: Path, version: Optional[str] = None) -> bool:
        """
        Train ML models with merged data

        Args:
            data_file: Path to training data (merged)
            version: Model version (auto-increment if None)

        Returns:
            True if training successful
        """
        # Auto-increment version
        if version is None:
            existing_versions = list(self.models_dir.glob("*_v*.pkl"))
            if existing_versions:
                # Extract version numbers
                versions = []
                for f in existing_versions:
                    parts = f.stem.split('_v')
                    if len(parts) == 2:
                        try:
                            versions.append(int(parts[1]))
                        except ValueError:
                            continue
                version = str(max(versions) + 1) if versions else "1"
            else:
                version = "1"

        print(f"[TRAINING] Starting model training (version {version})")

        # Run training script
        cmd = [
            sys.executable,
            "ml/train_models.py",
            "--data", str(data_file),
            "--version", version,
            "--models", "random_forest", "xgboost"
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=Path.cwd() / "tools/backtest/box_strategy",
                capture_output=True,
                text=True,
                timeout=600  # 10 min timeout
            )

            if result.returncode == 0:
                print(f"[OK] Training completed successfully (version {version})")
                return True
            else:
                print(f"[ERROR] Training failed:")
                print(result.stderr)
                return False

        except subprocess.TimeoutExpired:
            print(f"[ERROR] Training timed out after 10 minutes")
            return False
        except Exception as e:
            print(f"[ERROR] Training error: {e}")
            return False


class DailyLearningScheduler:
    """
    Schedules daily learning tasks

    Runs after market close (5:00 PM ET) to collect and process trades
    """

    def __init__(self, trade_logger: TradeLogger, trainer: IncrementalTrainer):
        self.trade_logger = trade_logger
        self.trainer = trainer

    def run_daily_learning(self):
        """Main daily learning task"""
        print("\n" + "="*80)
        print(f"DAILY LEARNING SYSTEM - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")

        # Check pending trades
        counts = self.trade_logger.get_trade_count()
        print(f"Trade Status:")
        print(f"  Total:   {counts['total']}")
        print(f"  Pending: {counts['pending']}")
        print(f"  Trained: {counts['trained']}")

        if counts['pending'] == 0:
            print("\n[SKIP] No new trades to process")
            return

        # Check if should retrain
        if not self.trainer.should_retrain(counts['pending']):
            print(f"\n[WAIT] Need {self.trainer.min_new_trades} trades to retrain")
            print(f"       Currently have {counts['pending']} pending")
            return

        print(f"\n[OK] Sufficient trades for retraining ({counts['pending']} >= {self.trainer.min_new_trades})")

        # Get pending trades
        pending_trades = self.trade_logger.get_pending_trades()
        print(f"\nPending Trades:")
        for i, entry in enumerate(pending_trades, 1):
            trade = entry['trade']
            print(f"  {i}. {trade['market']} {trade['date']} {trade['direction']} "
                  f"{'WIN' if trade['outcome'] == 'WIN' else 'LOSS'}")

        # Get latest backtest data
        backtest_file = self.trainer.get_latest_backtest_data()
        if not backtest_file:
            print("\n[ERROR] No backtest data found. Run backtest first.")
            return

        print(f"\nUsing backtest data: {backtest_file.name}")

        # Merge trades
        merged_file = self.trainer.merge_trades(backtest_file, pending_trades)

        # Train models
        print("\n" + "-"*80)
        success = self.trainer.train_models(merged_file)

        if success:
            # Mark trades as trained
            trade_files = [entry['file'] for entry in pending_trades]
            self.trade_logger.mark_as_trained(trade_files)

            print("\n" + "="*80)
            print("[OK] DAILY LEARNING COMPLETE")
            print("="*80 + "\n")
        else:
            print("\n" + "="*80)
            print("[ERROR] DAILY LEARNING FAILED")
            print("="*80 + "\n")

    def schedule_daily_task(self):
        """Schedule daily task at 5:00 PM ET (market close + 30 min)"""
        # Schedule at 5:00 PM ET
        schedule.every().day.at("17:00").do(self.run_daily_learning)

        print("="*80)
        print("DAILY LEARNING SCHEDULER STARTED")
        print("="*80)
        print(f"Scheduled to run daily at 5:00 PM ET")
        print(f"Next run: {schedule.next_run()}")
        print("Press Ctrl+C to stop\n")

        # Run forever
        try:
            while True:
                schedule.run_pending()
                time_module.sleep(3600)  # Check every hour
        except KeyboardInterrupt:
            print("\n[STOPPED] Scheduler stopped by user")


def main():
    parser = argparse.ArgumentParser(
        description='Daily Automated Learning System',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--run-once', action='store_true',
                      help='Run learning task once (for testing or manual runs)')
    group.add_argument('--daemon', action='store_true',
                      help='Run as daemon with scheduler')
    group.add_argument('--add-trade', type=str,
                      help='Add a completed trade from JSON file')
    group.add_argument('--force-retrain', action='store_true',
                      help='Force retrain with accumulated trades')
    group.add_argument('--status', action='store_true',
                      help='Show current status')

    parser.add_argument('--min-trades', type=int, default=5,
                       help='Minimum new trades before retraining (default: 5)')

    args = parser.parse_args()

    # Initialize components
    trade_logger = TradeLogger()
    trainer = IncrementalTrainer(min_new_trades=args.min_trades)
    scheduler = DailyLearningScheduler(trade_logger, trainer)

    if args.status:
        # Show status
        counts = trade_logger.get_trade_count()
        print("\n" + "="*80)
        print("DAILY LEARNING SYSTEM STATUS")
        print("="*80 + "\n")
        print(f"Trade Statistics:")
        print(f"  Total trades:   {counts['total']}")
        print(f"  Pending:        {counts['pending']}")
        print(f"  Trained:        {counts['trained']}")
        print(f"\nRetrain threshold: {args.min_trades} trades")
        print(f"Ready to retrain:  {'YES' if counts['pending'] >= args.min_trades else 'NO'}")
        print("\n" + "="*80 + "\n")

    elif args.add_trade:
        # Add trade manually
        trade_file = Path(args.add_trade)
        if not trade_file.exists():
            print(f"[ERROR] Trade file not found: {trade_file}")
            sys.exit(1)

        with open(trade_file, 'r') as f:
            trade = json.load(f)

        saved_path = trade_logger.log_trade(trade)
        print(f"[OK] Trade added: {saved_path}")

    elif args.force_retrain:
        # Force retrain
        print("[FORCE] Running retrain with accumulated trades...")
        scheduler.run_daily_learning()

    elif args.run_once:
        # Run once
        scheduler.run_daily_learning()

    elif args.daemon:
        # Run as daemon
        scheduler.schedule_daily_task()


if __name__ == "__main__":
    main()
