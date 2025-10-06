"""
Performance Metrics Calculator for Box Strategy

Calculates comprehensive trading metrics including:
- Win rate
- Profit factor
- Sharpe ratio
- Maximum drawdown
- Average monthly returns
- R-multiple distribution
- Trade statistics
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import json


class PerformanceMetrics:
    """Calculate and analyze trading performance metrics"""

    def __init__(self, trades_df: pd.DataFrame, equity_curve_df: pd.DataFrame):
        """
        Initialize metrics calculator

        Args:
            trades_df: DataFrame with trade records
            equity_curve_df: DataFrame with equity curve
        """
        self.trades_df = trades_df.copy()
        self.equity_curve_df = equity_curve_df.copy()

        # Convert date columns to datetime
        if 'date' in self.trades_df.columns:
            self.trades_df['date'] = pd.to_datetime(self.trades_df['date'])

    def calculate_all_metrics(self) -> Dict:
        """
        Calculate all performance metrics

        Returns:
            Dictionary with all metrics
        """
        metrics = {
            'basic_stats': self.calculate_basic_stats(),
            'win_rate': self.calculate_win_rate(),
            'profit_factor': self.calculate_profit_factor(),
            'sharpe_ratio': self.calculate_sharpe_ratio(),
            'sortino_ratio': self.calculate_sortino_ratio(),
            'max_drawdown': self.calculate_max_drawdown(),
            'monthly_returns': self.calculate_monthly_returns(),
            'r_distribution': self.calculate_r_distribution(),
            'trade_duration': self.calculate_trade_duration(),
            'directional_stats': self.calculate_directional_stats(),
            'take_profit_analysis': self.analyze_take_profits(),
            'box_range_analysis': self.analyze_box_ranges()
        }

        return metrics

    def calculate_basic_stats(self) -> Dict:
        """Calculate basic trading statistics"""
        if self.trades_df.empty:
            return {}

        # Calculate P&L metrics
        total_pnl = self.equity_curve_df['pnl'].sum()
        total_trades = len(self.trades_df)

        # Filter only executed trades (exclude invalid)
        executed_trades = self.trades_df[self.trades_df['status'] != 'INVALID']

        return {
            'total_trades': total_trades,
            'executed_trades': len(executed_trades),
            'invalid_trades': total_trades - len(executed_trades),
            'total_pnl': float(total_pnl),
            'avg_pnl_per_trade': float(total_pnl / len(executed_trades)) if len(executed_trades) > 0 else 0,
            'best_trade': float(self.trades_df['pnl_points'].max()),
            'worst_trade': float(self.trades_df['pnl_points'].min()),
            'avg_pnl_points': float(self.trades_df['pnl_points'].mean()),
            'median_pnl_points': float(self.trades_df['pnl_points'].median())
        }

    def calculate_win_rate(self) -> Dict:
        """Calculate win rate and related statistics"""
        if self.trades_df.empty:
            return {}

        # Exclude invalid trades
        executed = self.trades_df[self.trades_df['status'] != 'INVALID']

        if executed.empty:
            return {}

        winning_trades = executed[executed['pnl_points'] > 0]
        losing_trades = executed[executed['pnl_points'] <= 0]

        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        total_count = len(executed)

        return {
            'win_rate': (win_count / total_count * 100) if total_count > 0 else 0,
            'winning_trades': win_count,
            'losing_trades': loss_count,
            'breakeven_trades': len(executed[executed['pnl_points'] == 0]),
            'avg_win': float(winning_trades['pnl_points'].mean()) if win_count > 0 else 0,
            'avg_loss': float(losing_trades['pnl_points'].mean()) if loss_count > 0 else 0,
            'largest_win': float(winning_trades['pnl_points'].max()) if win_count > 0 else 0,
            'largest_loss': float(losing_trades['pnl_points'].min()) if loss_count > 0 else 0,
            'win_loss_ratio': abs(winning_trades['pnl_points'].mean() / losing_trades['pnl_points'].mean())
                if loss_count > 0 and win_count > 0 else 0
        }

    def calculate_profit_factor(self) -> Dict:
        """Calculate profit factor"""
        if self.trades_df.empty:
            return {}

        executed = self.trades_df[self.trades_df['status'] != 'INVALID']

        if executed.empty:
            return {}

        gross_profit = executed[executed['pnl_points'] > 0]['pnl_points'].sum()
        gross_loss = abs(executed[executed['pnl_points'] < 0]['pnl_points'].sum())

        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

        return {
            'profit_factor': float(profit_factor) if profit_factor != float('inf') else 999.99,
            'gross_profit': float(gross_profit),
            'gross_loss': float(gross_loss),
            'net_profit': float(gross_profit - gross_loss)
        }

    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> Dict:
        """
        Calculate Sharpe ratio

        Args:
            risk_free_rate: Annual risk-free rate (default 2%)
        """
        if self.equity_curve_df.empty:
            return {}

        # Calculate daily returns
        daily_returns = self.equity_curve_df['pnl_r'].values

        if len(daily_returns) == 0:
            return {}

        # Annualize (assuming 252 trading days per year)
        mean_return = np.mean(daily_returns) * 252
        std_return = np.std(daily_returns) * np.sqrt(252)

        sharpe = (mean_return - risk_free_rate) / std_return if std_return > 0 else 0

        return {
            'sharpe_ratio': float(sharpe),
            'annual_return': float(mean_return),
            'annual_volatility': float(std_return),
            'daily_avg_return': float(np.mean(daily_returns)),
            'daily_std': float(np.std(daily_returns))
        }

    def calculate_sortino_ratio(self, risk_free_rate: float = 0.02) -> Dict:
        """Calculate Sortino ratio (uses downside deviation)"""
        if self.equity_curve_df.empty:
            return {}

        daily_returns = self.equity_curve_df['pnl_r'].values

        if len(daily_returns) == 0:
            return {}

        # Calculate downside deviation (only negative returns)
        negative_returns = daily_returns[daily_returns < 0]
        downside_std = np.std(negative_returns) * np.sqrt(252) if len(negative_returns) > 0 else 0

        mean_return = np.mean(daily_returns) * 252

        sortino = (mean_return - risk_free_rate) / downside_std if downside_std > 0 else 0

        return {
            'sortino_ratio': float(sortino),
            'downside_deviation': float(downside_std)
        }

    def calculate_max_drawdown(self) -> Dict:
        """Calculate maximum drawdown"""
        if self.equity_curve_df.empty:
            return {}

        # Calculate cumulative equity
        equity = self.equity_curve_df['equity'].values
        running_max = np.maximum.accumulate(equity)
        drawdown = (equity - running_max) / running_max * 100

        max_dd = abs(drawdown.min())
        max_dd_idx = drawdown.argmin()

        # Find drawdown start (previous peak)
        dd_start_idx = np.where(equity[:max_dd_idx] == running_max[max_dd_idx])[0]
        dd_start_idx = dd_start_idx[-1] if len(dd_start_idx) > 0 else 0

        # Find recovery point
        recovery_idx = None
        if max_dd_idx < len(equity) - 1:
            recovery_points = np.where(equity[max_dd_idx:] >= running_max[max_dd_idx])[0]
            if len(recovery_points) > 0:
                recovery_idx = max_dd_idx + recovery_points[0]

        return {
            'max_drawdown_pct': float(max_dd),
            'max_drawdown_value': float(running_max[max_dd_idx] - equity[max_dd_idx]),
            'drawdown_start_date': str(self.equity_curve_df.index[dd_start_idx].date()),
            'drawdown_bottom_date': str(self.equity_curve_df.index[max_dd_idx].date()),
            'drawdown_recovery_date': str(self.equity_curve_df.index[recovery_idx].date())
                if recovery_idx is not None else "Not recovered",
            'current_drawdown_pct': float(drawdown[-1]) if len(drawdown) > 0 else 0
        }

    def calculate_monthly_returns(self) -> Dict:
        """Calculate monthly returns statistics"""
        if self.equity_curve_df.empty:
            return {}

        # Group by month
        monthly_pnl = self.equity_curve_df.resample('ME')['pnl'].sum()

        if monthly_pnl.empty:
            return {}

        # Convert monthly_returns keys to strings for JSON serialization
        monthly_returns_dict = {str(k): float(v) for k, v in monthly_pnl.to_dict().items()}

        return {
            'avg_monthly_return': float(monthly_pnl.mean()),
            'median_monthly_return': float(monthly_pnl.median()),
            'best_month': float(monthly_pnl.max()),
            'worst_month': float(monthly_pnl.min()),
            'positive_months': int((monthly_pnl > 0).sum()),
            'negative_months': int((monthly_pnl < 0).sum()),
            'monthly_win_rate': float((monthly_pnl > 0).sum() / len(monthly_pnl) * 100),
            'monthly_returns': monthly_returns_dict
        }

    def calculate_r_distribution(self) -> Dict:
        """Calculate R-multiple distribution"""
        if self.trades_df.empty:
            return {}

        executed = self.trades_df[self.trades_df['status'] != 'INVALID']

        if executed.empty:
            return {}

        r_values = executed['pnl_r'].values

        # Create distribution bins
        bins = [-10, -3, -2, -1, 0, 1, 2, 3, 5, 10, 100]
        labels = ['< -3R', '-3R to -2R', '-2R to -1R', '-1R to 0R',
                  '0R to 1R', '1R to 2R', '2R to 3R', '3R to 5R', '5R to 10R', '> 10R']

        hist, _ = np.histogram(r_values, bins=bins)
        distribution = {label: int(count) for label, count in zip(labels, hist)}

        return {
            'avg_r_multiple': float(r_values.mean()),
            'median_r_multiple': float(np.median(r_values)),
            'max_r_multiple': float(r_values.max()),
            'min_r_multiple': float(r_values.min()),
            'std_r_multiple': float(r_values.std()),
            'r_distribution': distribution,
            'trades_above_1r': int((r_values >= 1).sum()),
            'trades_above_2r': int((r_values >= 2).sum()),
            'trades_above_3r': int((r_values >= 3).sum())
        }

    def calculate_trade_duration(self) -> Dict:
        """Calculate trade duration statistics"""
        if self.trades_df.empty or 'holding_time_minutes' not in self.trades_df.columns:
            return {}

        executed = self.trades_df[self.trades_df['status'] != 'INVALID']

        if executed.empty:
            return {}

        durations = executed['holding_time_minutes'].values

        return {
            'avg_duration_minutes': float(durations.mean()),
            'median_duration_minutes': float(np.median(durations)),
            'min_duration_minutes': float(durations.min()),
            'max_duration_minutes': float(durations.max()),
            'avg_duration_hours': float(durations.mean() / 60),
            'trades_under_1hour': int((durations < 60).sum()),
            'trades_1to3_hours': int(((durations >= 60) & (durations < 180)).sum()),
            'trades_over_3hours': int((durations >= 180).sum())
        }

    def calculate_directional_stats(self) -> Dict:
        """Calculate statistics by trade direction"""
        if self.trades_df.empty or 'direction' not in self.trades_df.columns:
            return {}

        executed = self.trades_df[self.trades_df['status'] != 'INVALID']

        if executed.empty:
            return {}

        long_trades = executed[executed['direction'] == 'LONG']
        short_trades = executed[executed['direction'] == 'SHORT']

        return {
            'long': {
                'count': len(long_trades),
                'win_rate': float((long_trades['pnl_points'] > 0).sum() / len(long_trades) * 100)
                    if len(long_trades) > 0 else 0,
                'avg_pnl': float(long_trades['pnl_points'].mean()) if len(long_trades) > 0 else 0,
                'total_pnl': float(long_trades['pnl_points'].sum()) if len(long_trades) > 0 else 0
            },
            'short': {
                'count': len(short_trades),
                'win_rate': float((short_trades['pnl_points'] > 0).sum() / len(short_trades) * 100)
                    if len(short_trades) > 0 else 0,
                'avg_pnl': float(short_trades['pnl_points'].mean()) if len(short_trades) > 0 else 0,
                'total_pnl': float(short_trades['pnl_points'].sum()) if len(short_trades) > 0 else 0
            }
        }

    def analyze_take_profits(self) -> Dict:
        """Analyze take profit level achievements"""
        if self.trades_df.empty or 'status' not in self.trades_df.columns:
            return {}

        executed = self.trades_df[self.trades_df['status'] != 'INVALID']

        if executed.empty:
            return {}

        status_counts = executed['status'].value_counts().to_dict()

        # Count partial exits
        total_partials = 0
        tp1_hits = 0
        tp2_hits = 0

        for _, trade in executed.iterrows():
            if isinstance(trade.get('partial_exits'), list):
                total_partials += len(trade['partial_exits'])
                for exit in trade['partial_exits']:
                    if 'TP1' in exit.get('reason', ''):
                        tp1_hits += 1
                    elif 'TP2' in exit.get('reason', ''):
                        tp2_hits += 1

        return {
            'status_distribution': status_counts,
            'stopped_out': status_counts.get('STOPPED_OUT', 0),
            'tp1_achieved': tp1_hits,
            'tp2_achieved': tp2_hits,
            'tp3_achieved': status_counts.get('TP3_HIT', 0),
            'total_partial_exits': total_partials,
            'avg_partials_per_trade': float(total_partials / len(executed)) if len(executed) > 0 else 0
        }

    def analyze_box_ranges(self) -> Dict:
        """Analyze box range distribution and performance"""
        if self.trades_df.empty or 'box_range' not in self.trades_df.columns:
            return {}

        executed = self.trades_df[self.trades_df['status'] != 'INVALID']

        if executed.empty:
            return {}

        ranges = executed['box_range'].values

        # Group by range size
        small_ranges = executed[executed['box_range'] < 15]
        medium_ranges = executed[(executed['box_range'] >= 15) & (executed['box_range'] < 30)]
        large_ranges = executed[executed['box_range'] >= 30]

        return {
            'avg_box_range': float(ranges.mean()),
            'median_box_range': float(np.median(ranges)),
            'min_box_range': float(ranges.min()),
            'max_box_range': float(ranges.max()),
            'small_ranges': {
                'count': len(small_ranges),
                'win_rate': float((small_ranges['pnl_points'] > 0).sum() / len(small_ranges) * 100)
                    if len(small_ranges) > 0 else 0,
                'avg_pnl': float(small_ranges['pnl_points'].mean()) if len(small_ranges) > 0 else 0
            },
            'medium_ranges': {
                'count': len(medium_ranges),
                'win_rate': float((medium_ranges['pnl_points'] > 0).sum() / len(medium_ranges) * 100)
                    if len(medium_ranges) > 0 else 0,
                'avg_pnl': float(medium_ranges['pnl_points'].mean()) if len(medium_ranges) > 0 else 0
            },
            'large_ranges': {
                'count': len(large_ranges),
                'win_rate': float((large_ranges['pnl_points'] > 0).sum() / len(large_ranges) * 100)
                    if len(large_ranges) > 0 else 0,
                'avg_pnl': float(large_ranges['pnl_points'].mean()) if len(large_ranges) > 0 else 0
            }
        }

    def print_summary(self, metrics: Dict):
        """Print formatted metrics summary"""
        print("\n" + "="*80)
        print("PERFORMANCE METRICS SUMMARY")
        print("="*80)

        # Basic Stats
        basic = metrics.get('basic_stats', {})
        print(f"\n[BASIC STATISTICS]")
        print(f"  Total Trades: {basic.get('total_trades', 0)}")
        print(f"  Executed Trades: {basic.get('executed_trades', 0)}")
        print(f"  Invalid Trades: {basic.get('invalid_trades', 0)}")
        print(f"  Total P&L: ${basic.get('total_pnl', 0):,.2f}")
        print(f"  Avg P&L per Trade: ${basic.get('avg_pnl_per_trade', 0):,.2f}")

        # Win Rate
        wr = metrics.get('win_rate', {})
        print(f"\n[WIN RATE ANALYSIS]")
        print(f"  Win Rate: {wr.get('win_rate', 0):.2f}%")
        print(f"  Winning Trades: {wr.get('winning_trades', 0)}")
        print(f"  Losing Trades: {wr.get('losing_trades', 0)}")
        print(f"  Avg Win: {wr.get('avg_win', 0):.2f} points")
        print(f"  Avg Loss: {wr.get('avg_loss', 0):.2f} points")
        print(f"  Win/Loss Ratio: {wr.get('win_loss_ratio', 0):.2f}")

        # Profit Factor
        pf = metrics.get('profit_factor', {})
        print(f"\n[PROFIT FACTOR]")
        print(f"  Profit Factor: {pf.get('profit_factor', 0):.2f}")
        print(f"  Gross Profit: {pf.get('gross_profit', 0):.2f} points")
        print(f"  Gross Loss: {pf.get('gross_loss', 0):.2f} points")

        # Sharpe & Sortino
        sharpe = metrics.get('sharpe_ratio', {})
        sortino = metrics.get('sortino_ratio', {})
        print(f"\n[RISK-ADJUSTED RETURNS]")
        print(f"  Sharpe Ratio: {sharpe.get('sharpe_ratio', 0):.2f}")
        print(f"  Sortino Ratio: {sortino.get('sortino_ratio', 0):.2f}")
        print(f"  Annual Return: {sharpe.get('annual_return', 0):.2f}R")
        print(f"  Annual Volatility: {sharpe.get('annual_volatility', 0):.2f}R")

        # Max Drawdown
        mdd = metrics.get('max_drawdown', {})
        print(f"\n[DRAWDOWN ANALYSIS]")
        print(f"  Max Drawdown: {mdd.get('max_drawdown_pct', 0):.2f}%")
        print(f"  Max DD Value: ${mdd.get('max_drawdown_value', 0):,.2f}")
        print(f"  Current Drawdown: {mdd.get('current_drawdown_pct', 0):.2f}%")

        # R-Multiple
        r_dist = metrics.get('r_distribution', {})
        print(f"\n[R-MULTIPLE DISTRIBUTION]")
        print(f"  Avg R-Multiple: {r_dist.get('avg_r_multiple', 0):.2f}R")
        print(f"  Median R-Multiple: {r_dist.get('median_r_multiple', 0):.2f}R")
        print(f"  Trades >= 1R: {r_dist.get('trades_above_1r', 0)}")
        print(f"  Trades >= 2R: {r_dist.get('trades_above_2r', 0)}")
        print(f"  Trades >= 3R: {r_dist.get('trades_above_3r', 0)}")

        # Monthly Returns
        monthly = metrics.get('monthly_returns', {})
        print(f"\n[MONTHLY PERFORMANCE]")
        print(f"  Avg Monthly Return: ${monthly.get('avg_monthly_return', 0):,.2f}")
        print(f"  Best Month: ${monthly.get('best_month', 0):,.2f}")
        print(f"  Worst Month: ${monthly.get('worst_month', 0):,.2f}")
        print(f"  Monthly Win Rate: {monthly.get('monthly_win_rate', 0):.2f}%")

        print("\n" + "="*80)


def main():
    """Test metrics calculation"""
    # Load sample data (you would load real backtest results here)
    # This is just a placeholder
    pass


if __name__ == "__main__":
    main()
