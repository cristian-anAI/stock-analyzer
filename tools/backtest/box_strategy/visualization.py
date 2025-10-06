"""
Visualization Module for Box Strategy Backtesting

Creates comprehensive charts and visual reports:
- Equity curve
- Drawdown chart
- R-multiple distribution
- Monthly returns heatmap
- Trade distribution
- Win rate analysis
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import calendar


class StrategyVisualizer:
    """Create visualizations for backtest results"""

    def __init__(self, output_dir: str = "tools/backtest/box_strategy/charts"):
        """
        Initialize visualizer

        Args:
            output_dir: Directory to save charts
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set style
        plt.style.use('seaborn-v0_8-darkgrid')
        sns.set_palette("husl")

    def create_full_report(
        self,
        trades_df: pd.DataFrame,
        equity_curve_df: pd.DataFrame,
        metrics: Dict,
        symbol: str
    ) -> List[Path]:
        """
        Create complete visual report

        Args:
            trades_df: DataFrame with trades
            equity_curve_df: DataFrame with equity curve
            metrics: Metrics dictionary
            symbol: Symbol name

        Returns:
            List of saved chart paths
        """
        saved_charts = []

        print("\n[CHARTS] Generating visualizations...")

        # 1. Equity Curve
        chart_path = self.plot_equity_curve(equity_curve_df, metrics, symbol)
        if chart_path:
            saved_charts.append(chart_path)

        # 2. Drawdown Chart
        chart_path = self.plot_drawdown(equity_curve_df, symbol)
        if chart_path:
            saved_charts.append(chart_path)

        # 3. R-Multiple Distribution
        chart_path = self.plot_r_distribution(trades_df, symbol)
        if chart_path:
            saved_charts.append(chart_path)

        # 4. Monthly Returns Heatmap
        chart_path = self.plot_monthly_heatmap(equity_curve_df, symbol)
        if chart_path:
            saved_charts.append(chart_path)

        # 5. Trade Analysis Dashboard
        chart_path = self.plot_trade_dashboard(trades_df, metrics, symbol)
        if chart_path:
            saved_charts.append(chart_path)

        # 6. Box Range Analysis
        chart_path = self.plot_box_analysis(trades_df, symbol)
        if chart_path:
            saved_charts.append(chart_path)

        print(f"[OK] Generated {len(saved_charts)} charts in {self.output_dir}")

        return saved_charts

    def plot_equity_curve(
        self,
        equity_df: pd.DataFrame,
        metrics: Dict,
        symbol: str
    ) -> Optional[Path]:
        """Plot equity curve with key metrics"""
        if equity_df.empty:
            return None

        fig, ax = plt.subplots(figsize=(14, 7))

        # Plot equity curve
        ax.plot(equity_df.index, equity_df['equity'], linewidth=2, label='Equity')

        # Add initial capital line
        initial_capital = equity_df['equity'].iloc[0] - equity_df['pnl'].iloc[0]
        ax.axhline(y=initial_capital, color='gray', linestyle='--',
                   alpha=0.5, label='Initial Capital')

        # Formatting
        ax.set_title(f'{symbol} - Equity Curve', fontsize=16, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Equity ($)', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left')

        # Format y-axis as currency
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

        # Add metrics text box
        basic = metrics.get('basic_stats', {})
        sharpe = metrics.get('sharpe_ratio', {})
        mdd = metrics.get('max_drawdown', {})

        metrics_text = (
            f"Total P&L: ${basic.get('total_pnl', 0):,.2f}\n"
            f"Sharpe Ratio: {sharpe.get('sharpe_ratio', 0):.2f}\n"
            f"Max DD: {mdd.get('max_drawdown_pct', 0):.2f}%"
        )

        ax.text(0.02, 0.98, metrics_text,
                transform=ax.transAxes,
                fontsize=10,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.tight_layout()

        # Save
        filename = f'{symbol}_equity_curve.png'
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"  [OK] Equity curve: {filename}")
        return filepath

    def plot_drawdown(self, equity_df: pd.DataFrame, symbol: str) -> Optional[Path]:
        """Plot drawdown chart"""
        if equity_df.empty:
            return None

        # Calculate drawdown
        equity = equity_df['equity'].values
        running_max = np.maximum.accumulate(equity)
        drawdown = (equity - running_max) / running_max * 100

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

        # Plot equity
        ax1.plot(equity_df.index, equity, linewidth=2, color='steelblue')
        ax1.fill_between(equity_df.index, equity, running_max,
                         where=(equity < running_max), alpha=0.3, color='red',
                         label='Drawdown')
        ax1.plot(equity_df.index, running_max, linewidth=1, color='gray',
                linestyle='--', alpha=0.7, label='Peak Equity')
        ax1.set_ylabel('Equity ($)', fontsize=12)
        ax1.set_title(f'{symbol} - Drawdown Analysis', fontsize=16, fontweight='bold')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

        # Plot drawdown percentage
        ax2.fill_between(equity_df.index, 0, drawdown, color='red', alpha=0.5)
        ax2.plot(equity_df.index, drawdown, color='darkred', linewidth=1)
        ax2.set_ylabel('Drawdown (%)', fontsize=12)
        ax2.set_xlabel('Date', fontsize=12)
        ax2.grid(True, alpha=0.3)
        ax2.axhline(y=0, color='black', linewidth=0.5)

        plt.tight_layout()

        # Save
        filename = f'{symbol}_drawdown.png'
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"  [OK] Drawdown chart: {filename}")
        return filepath

    def plot_r_distribution(self, trades_df: pd.DataFrame, symbol: str) -> Optional[Path]:
        """Plot R-multiple distribution"""
        if trades_df.empty:
            return None

        executed = trades_df[trades_df['status'] != 'INVALID']

        if executed.empty:
            return None

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

        # Histogram
        r_values = executed['pnl_r'].values
        ax1.hist(r_values, bins=30, edgecolor='black', alpha=0.7, color='steelblue')
        ax1.axvline(x=0, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Breakeven')
        ax1.axvline(x=r_values.mean(), color='green', linestyle='--',
                   linewidth=2, alpha=0.7, label=f'Mean: {r_values.mean():.2f}R')
        ax1.set_xlabel('R-Multiple', fontsize=12)
        ax1.set_ylabel('Frequency', fontsize=12)
        ax1.set_title('R-Multiple Distribution', fontsize=14, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Cumulative distribution
        sorted_r = np.sort(r_values)
        cumulative = np.arange(1, len(sorted_r) + 1) / len(sorted_r) * 100
        ax2.plot(sorted_r, cumulative, linewidth=2, color='steelblue')
        ax2.axvline(x=0, color='red', linestyle='--', linewidth=2, alpha=0.7)
        ax2.axhline(y=50, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax2.set_xlabel('R-Multiple', fontsize=12)
        ax2.set_ylabel('Cumulative Probability (%)', fontsize=12)
        ax2.set_title('Cumulative R-Multiple Distribution', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)

        plt.suptitle(f'{symbol} - R-Multiple Analysis', fontsize=16, fontweight='bold', y=1.02)
        plt.tight_layout()

        # Save
        filename = f'{symbol}_r_distribution.png'
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"  [OK] R-distribution: {filename}")
        return filepath

    def plot_monthly_heatmap(self, equity_df: pd.DataFrame, symbol: str) -> Optional[Path]:
        """Plot monthly returns heatmap"""
        if equity_df.empty:
            return None

        # Calculate monthly returns
        monthly_pnl = equity_df.resample('ME')['pnl'].sum()

        if monthly_pnl.empty:
            return None

        # Create pivot table for heatmap
        monthly_pnl.index = pd.to_datetime(monthly_pnl.index)
        monthly_returns_pct = (monthly_pnl / equity_df['equity'].iloc[0] * 100).round(2)

        # Create year-month matrix
        years = monthly_returns_pct.index.year.unique()
        months = range(1, 13)

        data = []
        for year in years:
            row = []
            for month in months:
                try:
                    value = monthly_returns_pct[
                        (monthly_returns_pct.index.year == year) &
                        (monthly_returns_pct.index.month == month)
                    ].values[0]
                    row.append(value)
                except IndexError:
                    row.append(np.nan)
            data.append(row)

        df_heatmap = pd.DataFrame(
            data,
            index=years,
            columns=[calendar.month_abbr[i] for i in months]
        )

        # Plot
        fig, ax = plt.subplots(figsize=(14, max(6, len(years) * 0.8)))

        sns.heatmap(
            df_heatmap,
            annot=True,
            fmt='.1f',
            cmap='RdYlGn',
            center=0,
            cbar_kws={'label': 'Monthly Return (%)'},
            linewidths=0.5,
            ax=ax
        )

        ax.set_title(f'{symbol} - Monthly Returns Heatmap', fontsize=16, fontweight='bold')
        ax.set_xlabel('Month', fontsize=12)
        ax.set_ylabel('Year', fontsize=12)

        plt.tight_layout()

        # Save
        filename = f'{symbol}_monthly_heatmap.png'
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"  [OK] Monthly heatmap: {filename}")
        return filepath

    def plot_trade_dashboard(
        self,
        trades_df: pd.DataFrame,
        metrics: Dict,
        symbol: str
    ) -> Optional[Path]:
        """Plot comprehensive trade analysis dashboard"""
        if trades_df.empty:
            return None

        executed = trades_df[trades_df['status'] != 'INVALID']

        if executed.empty:
            return None

        fig = plt.figure(figsize=(18, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

        # 1. Win/Loss Bar Chart
        ax1 = fig.add_subplot(gs[0, 0])
        wr_data = metrics.get('win_rate', {})
        ax1.bar(['Wins', 'Losses'], [wr_data.get('winning_trades', 0),
                                      wr_data.get('losing_trades', 0)],
                color=['green', 'red'], alpha=0.7)
        ax1.set_title('Win/Loss Count', fontweight='bold')
        ax1.set_ylabel('Number of Trades')

        # 2. Direction Distribution
        ax2 = fig.add_subplot(gs[0, 1])
        dir_stats = metrics.get('directional_stats', {})
        directions = ['LONG', 'SHORT']
        counts = [dir_stats.get('long', {}).get('count', 0),
                  dir_stats.get('short', {}).get('count', 0)]
        ax2.pie(counts, labels=directions, autopct='%1.1f%%', startangle=90)
        ax2.set_title('Trade Direction', fontweight='bold')

        # 3. Status Distribution
        ax3 = fig.add_subplot(gs[0, 2])
        tp_analysis = metrics.get('take_profit_analysis', {})
        status_dist = tp_analysis.get('status_distribution', {})
        if status_dist:
            ax3.barh(list(status_dist.keys()), list(status_dist.values()), alpha=0.7)
            ax3.set_title('Exit Status Distribution', fontweight='bold')
            ax3.set_xlabel('Count')

        # 4. Trade Duration
        ax4 = fig.add_subplot(gs[1, 0])
        durations = executed['holding_time_minutes'].values
        ax4.hist(durations / 60, bins=20, edgecolor='black', alpha=0.7, color='steelblue')
        ax4.set_xlabel('Duration (hours)')
        ax4.set_ylabel('Frequency')
        ax4.set_title('Trade Duration Distribution', fontweight='bold')
        ax4.axvline(x=durations.mean() / 60, color='red', linestyle='--',
                   label=f'Mean: {durations.mean()/60:.1f}h')
        ax4.legend()

        # 5. P&L by Trade Number
        ax5 = fig.add_subplot(gs[1, 1:])
        trade_nums = range(1, len(executed) + 1)
        colors = ['green' if x > 0 else 'red' for x in executed['pnl_points'].values]
        ax5.bar(trade_nums, executed['pnl_points'].values, color=colors, alpha=0.6)
        ax5.axhline(y=0, color='black', linewidth=0.5)
        ax5.set_xlabel('Trade Number')
        ax5.set_ylabel('P&L (points)')
        ax5.set_title('P&L by Trade', fontweight='bold')
        ax5.grid(True, alpha=0.3)

        # 6. Box Range vs P&L Scatter
        ax6 = fig.add_subplot(gs[2, :2])
        winning = executed[executed['pnl_points'] > 0]
        losing = executed[executed['pnl_points'] <= 0]

        ax6.scatter(winning['box_range'], winning['pnl_r'],
                   color='green', alpha=0.6, label='Winning Trades', s=50)
        ax6.scatter(losing['box_range'], losing['pnl_r'],
                   color='red', alpha=0.6, label='Losing Trades', s=50)
        ax6.axhline(y=0, color='black', linewidth=0.5)
        ax6.set_xlabel('Box Range (points)')
        ax6.set_ylabel('P&L (R-multiple)')
        ax6.set_title('Box Range vs P&L', fontweight='bold')
        ax6.legend()
        ax6.grid(True, alpha=0.3)

        # 7. Key Metrics Table
        ax7 = fig.add_subplot(gs[2, 2])
        ax7.axis('off')

        basic = metrics.get('basic_stats', {})
        wr_metrics = metrics.get('win_rate', {})
        pf = metrics.get('profit_factor', {})
        r_dist = metrics.get('r_distribution', {})

        table_data = [
            ['Win Rate', f"{wr_metrics.get('win_rate', 0):.1f}%"],
            ['Profit Factor', f"{pf.get('profit_factor', 0):.2f}"],
            ['Avg R', f"{r_dist.get('avg_r_multiple', 0):.2f}"],
            ['Best Trade', f"{basic.get('best_trade', 0):.1f} pts"],
            ['Worst Trade', f"{basic.get('worst_trade', 0):.1f} pts"],
            ['Avg Win', f"{wr_metrics.get('avg_win', 0):.1f} pts"],
            ['Avg Loss', f"{wr_metrics.get('avg_loss', 0):.1f} pts"]
        ]

        table = ax7.table(cellText=table_data, cellLoc='left',
                         colWidths=[0.6, 0.4], loc='center',
                         bbox=[0, 0, 1, 1])
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)

        for i in range(len(table_data)):
            table[(i, 0)].set_facecolor('#E8E8E8')

        plt.suptitle(f'{symbol} - Trade Analysis Dashboard',
                    fontsize=18, fontweight='bold', y=0.995)

        # Save
        filename = f'{symbol}_trade_dashboard.png'
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"  [OK] Trade dashboard: {filename}")
        return filepath

    def plot_box_analysis(self, trades_df: pd.DataFrame, symbol: str) -> Optional[Path]:
        """Plot box range analysis"""
        if trades_df.empty or 'box_range' not in trades_df.columns:
            return None

        executed = trades_df[trades_df['status'] != 'INVALID']

        if executed.empty:
            return None

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # 1. Box Range Distribution
        ax1 = axes[0, 0]
        ax1.hist(executed['box_range'], bins=20, edgecolor='black', alpha=0.7, color='steelblue')
        ax1.axvline(x=executed['box_range'].mean(), color='red', linestyle='--',
                   label=f"Mean: {executed['box_range'].mean():.1f}")
        ax1.set_xlabel('Box Range (points)')
        ax1.set_ylabel('Frequency')
        ax1.set_title('Box Range Distribution', fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 2. Win Rate by Box Range
        ax2 = axes[0, 1]
        bins = [0, 10, 20, 30, 40, 100]
        labels = ['0-10', '10-20', '20-30', '30-40', '40+']
        executed['range_bin'] = pd.cut(executed['box_range'], bins=bins, labels=labels)

        win_rates = []
        for label in labels:
            bin_trades = executed[executed['range_bin'] == label]
            if len(bin_trades) > 0:
                wr = (bin_trades['pnl_points'] > 0).sum() / len(bin_trades) * 100
                win_rates.append(wr)
            else:
                win_rates.append(0)

        ax2.bar(labels, win_rates, alpha=0.7, color='steelblue')
        ax2.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='50% WR')
        ax2.set_xlabel('Box Range (points)')
        ax2.set_ylabel('Win Rate (%)')
        ax2.set_title('Win Rate by Box Range', fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis='y')

        # 3. Avg P&L by Box Range
        ax3 = axes[1, 0]
        avg_pnl = []
        for label in labels:
            bin_trades = executed[executed['range_bin'] == label]
            if len(bin_trades) > 0:
                avg_pnl.append(bin_trades['pnl_points'].mean())
            else:
                avg_pnl.append(0)

        colors = ['green' if x > 0 else 'red' for x in avg_pnl]
        ax3.bar(labels, avg_pnl, alpha=0.7, color=colors)
        ax3.axhline(y=0, color='black', linewidth=0.5)
        ax3.set_xlabel('Box Range (points)')
        ax3.set_ylabel('Avg P&L (points)')
        ax3.set_title('Average P&L by Box Range', fontweight='bold')
        ax3.grid(True, alpha=0.3, axis='y')

        # 4. Trade Count by Box Range
        ax4 = axes[1, 1]
        trade_counts = [len(executed[executed['range_bin'] == label]) for label in labels]
        ax4.bar(labels, trade_counts, alpha=0.7, color='steelblue')
        ax4.set_xlabel('Box Range (points)')
        ax4.set_ylabel('Number of Trades')
        ax4.set_title('Trade Count by Box Range', fontweight='bold')
        ax4.grid(True, alpha=0.3, axis='y')

        plt.suptitle(f'{symbol} - Box Range Analysis',
                    fontsize=18, fontweight='bold', y=0.995)
        plt.tight_layout()

        # Save
        filename = f'{symbol}_box_analysis.png'
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"  [OK] Box analysis: {filename}")
        return filepath


def main():
    """Test visualization"""
    pass


if __name__ == "__main__":
    main()
