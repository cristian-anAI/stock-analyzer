"""
Backtesting Engine for Box Strategy

Simulates historical trading with the Box/Opening Range strategy.
Tracks all trades, calculates performance metrics, and generates detailed reports.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import json
from pathlib import Path

from data_loader import DataLoader
from strategy import (
    BoxStrategy,
    Direction,
    TradeStatus,
    BoxSetup,
    TradeEntry,
    TradeExit
)


@dataclass
class TradeRecord:
    """Complete trade record for analysis"""
    # Box info
    date: str
    box_high: float
    box_low: float
    box_range: float

    # Entry info
    direction: str
    entry_time: str
    entry_price: float
    stop_loss: float
    risk_points: float

    # Exit info
    exit_time: str
    exit_price: float
    status: str
    pnl_points: float
    pnl_r: float

    # Trade details
    partial_exits: List[Dict]
    holding_time_minutes: float

    def to_dict(self):
        """Convert to dictionary"""
        return asdict(self)


class BacktestEngine:
    """Backtesting engine for Box Strategy"""

    def __init__(
        self,
        initial_capital: float = 100000,
        risk_per_trade: float = 0.02,
        slippage_points: float = 1.0,
        point_value: float = 50.0,  # S&P 500 E-mini: $50 per point
        **strategy_kwargs
    ):
        """
        Initialize backtest engine

        Args:
            initial_capital: Starting account balance
            risk_per_trade: Percentage of capital to risk per trade
            slippage_points: Slippage in index points
            point_value: Dollar value per index point (ES: $50, NQ: $20)
            **strategy_kwargs: Additional arguments for BoxStrategy
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.point_value = point_value

        # Initialize strategy
        self.strategy = BoxStrategy(
            risk_per_trade=risk_per_trade,
            slippage_points=slippage_points,
            **strategy_kwargs
        )

        # Initialize data loader
        self.data_loader = DataLoader()

        # Trade tracking
        self.trades: List[TradeRecord] = []
        self.equity_curve: List[Dict] = []
        self.daily_returns: List[float] = []

    def resample_to_hourly(self, df_5min: pd.DataFrame) -> pd.DataFrame:
        """
        Resample 5-minute data to 1-hour bars

        Args:
            df_5min: 5-minute OHLCV data

        Returns:
            1-hour OHLCV data
        """
        df_1hour = df_5min.resample('1h').agg({
            'Open': lambda x: x.iloc[0] if len(x) > 0 else None,
            'High': 'max',
            'Low': 'min',
            'Close': lambda x: x.iloc[-1] if len(x) > 0 else None,
            'Volume': 'sum'
        }).dropna()

        return df_1hour

    def calculate_position_size(self, risk_points: float) -> int:
        """
        Calculate position size based on risk

        Args:
            risk_points: Distance to stop loss in points

        Returns:
            Number of contracts
        """
        if risk_points <= 0:
            return 0

        risk_amount = self.current_capital * self.risk_per_trade
        dollar_risk_per_contract = risk_points * self.point_value

        position_size = int(risk_amount / dollar_risk_per_contract)

        return max(1, position_size)  # Minimum 1 contract

    def run_backtest(
        self,
        symbol_key: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """
        Run backtest for a specific symbol

        Args:
            symbol_key: Symbol to backtest ('SPX', 'NDX', etc.)
            start_date: Start date for backtest
            end_date: End date for backtest

        Returns:
            Dictionary with backtest results
        """
        print(f"\n{'='*60}")
        print(f"Running backtest for {symbol_key}")
        print(f"{'='*60}")

        # Load 5-minute data
        df_5min = self.data_loader.download_5min_data(
            symbol_key,
            start_date=start_date,
            end_date=end_date
        )

        # Resample to hourly for TP3
        df_1hour = self.resample_to_hourly(df_5min)

        # Get trading days
        trading_days = self.data_loader.get_trading_days(df_5min)
        print(f"Total trading days: {len(trading_days)}")

        # Reset capital
        self.current_capital = self.initial_capital
        self.trades = []
        self.equity_curve = []

        # Track statistics
        total_setups = 0
        valid_entries = 0
        invalid_trades = 0

        # Simulate trading day by day
        for day in trading_days:
            # 1. Identify box setup
            box_setup = self.strategy.identify_box(df_5min, day)

            if not box_setup:
                # No valid box for this day
                continue

            total_setups += 1

            # 2. Detect breakout
            breakout = self.strategy.detect_breakout(df_5min, box_setup)

            if not breakout:
                # No breakout occurred
                continue

            direction, breakout_time, _ = breakout

            # 3. Check entry execution
            entry = self.strategy.check_entry_execution(
                df_5min,
                direction,
                breakout_time,
                box_setup
            )

            if not entry:
                # Order not filled within time window
                invalid_trades += 1
                continue

            valid_entries += 1

            # 4. Manage trade
            exit_result = self.strategy.manage_trade(
                df_5min,
                df_1hour,
                entry
            )

            # 5. Calculate position size and P&L
            position_size = self.calculate_position_size(entry.risk_points)
            pnl_dollars = exit_result.pnl_points * self.point_value * position_size

            # 6. Update capital
            self.current_capital += pnl_dollars

            # 7. Record trade
            holding_time = (exit_result.exit_time - entry.entry_time).total_seconds() / 60

            trade_record = TradeRecord(
                date=entry.date.isoformat(),
                box_high=box_setup.box_high,
                box_low=box_setup.box_low,
                box_range=box_setup.box_range,
                direction=entry.direction.value,
                entry_time=entry.entry_time.isoformat(),
                entry_price=entry.entry_price,
                stop_loss=entry.stop_loss,
                risk_points=entry.risk_points,
                exit_time=exit_result.exit_time.isoformat(),
                exit_price=exit_result.exit_price,
                status=exit_result.status.value,
                pnl_points=exit_result.pnl_points,
                pnl_r=exit_result.pnl_r,
                partial_exits=exit_result.partial_exits,
                holding_time_minutes=holding_time
            )

            self.trades.append(trade_record)

            # 8. Update equity curve
            self.equity_curve.append({
                'date': entry.date.isoformat(),
                'equity': self.current_capital,
                'pnl': pnl_dollars,
                'pnl_r': exit_result.pnl_r
            })

            # Print trade summary
            status_symbol = "[WIN]" if pnl_dollars > 0 else "[LOSS]"
            print(f"{status_symbol} {day} | {direction.value:5s} | "
                  f"Entry: {entry.entry_price:.2f} | "
                  f"Exit: {exit_result.exit_price:.2f} | "
                  f"P&L: ${pnl_dollars:+,.2f} ({exit_result.pnl_r:+.2f}R) | "
                  f"Status: {exit_result.status.value}")

        # Generate summary
        print(f"\n{'='*60}")
        print(f"Backtest Summary")
        print(f"{'='*60}")
        print(f"Total setups identified: {total_setups}")
        print(f"Valid entries: {valid_entries}")
        print(f"Invalid trades (not filled): {invalid_trades}")
        print(f"Total trades executed: {len(self.trades)}")
        print(f"Initial capital: ${self.initial_capital:,.2f}")
        print(f"Final capital: ${self.current_capital:,.2f}")
        print(f"Total P&L: ${self.current_capital - self.initial_capital:+,.2f}")
        print(f"Return: {((self.current_capital / self.initial_capital) - 1) * 100:+.2f}%")

        return {
            'symbol': symbol_key,
            'initial_capital': self.initial_capital,
            'final_capital': self.current_capital,
            'total_pnl': self.current_capital - self.initial_capital,
            'return_pct': ((self.current_capital / self.initial_capital) - 1) * 100,
            'total_trades': len(self.trades),
            'total_setups': total_setups,
            'valid_entries': valid_entries,
            'invalid_trades': invalid_trades,
            'trades': [trade.to_dict() for trade in self.trades],
            'equity_curve': self.equity_curve
        }

    def save_results(self, results: Dict, output_dir: str = "tools/backtest/box_strategy/results"):
        """
        Save backtest results to JSON file

        Args:
            results: Backtest results dictionary
            output_dir: Output directory
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{results['symbol']}_backtest_{timestamp}.json"
        filepath = output_path / filename

        # Convert non-serializable objects to JSON-compatible formats
        def json_serial(obj):
            """JSON serializer for objects not serializable by default json code"""
            if isinstance(obj, (datetime, pd.Timestamp)):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=json_serial)

        print(f"\nResults saved to: {filepath}")

        # Also save trades as CSV for easy analysis
        if results['trades']:
            df_trades = pd.DataFrame(results['trades'])
            csv_filename = f"{results['symbol']}_trades_{timestamp}.csv"
            csv_filepath = output_path / csv_filename
            df_trades.to_csv(csv_filepath, index=False)
            print(f"Trades CSV saved to: {csv_filepath}")

        return filepath

    def export_trades_to_df(self) -> pd.DataFrame:
        """Export trades to pandas DataFrame"""
        if not self.trades:
            return pd.DataFrame()

        return pd.DataFrame([trade.to_dict() for trade in self.trades])

    def export_equity_curve_to_df(self) -> pd.DataFrame:
        """Export equity curve to pandas DataFrame"""
        if not self.equity_curve:
            return pd.DataFrame()

        df = pd.DataFrame(self.equity_curve)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

        return df


def main():
    """Test backtesting engine"""
    # Initialize engine
    engine = BacktestEngine(
        initial_capital=100000,
        risk_per_trade=0.02,
        slippage_points=1.0,
        point_value=50.0,  # S&P 500 E-mini
        min_box_range=5.0,
        max_box_range=100.0,
        use_volatility_filter=False
    )

    # Run backtest for S&P 500
    results = engine.run_backtest('SPX')

    # Save results
    engine.save_results(results)

    # Show equity curve
    df_equity = engine.export_equity_curve_to_df()
    print(f"\nEquity Curve:\n{df_equity.tail(10)}")


if __name__ == "__main__":
    main()
