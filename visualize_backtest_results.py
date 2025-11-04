"""
Visualize Backtest Results

Generates charts and detailed analysis from backtest JSON files.
"""

import json
import glob
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import os


def load_backtest_results(pattern='backtest_results_*.json'):
    """Load all backtest result files."""
    files = glob.glob(pattern)

    if not files:
        print(f"No files found matching: {pattern}")
        return {}

    results = {}

    for file in files:
        period_name = file.replace('backtest_results_', '').replace('.json', '').split('_')[0]

        with open(file, 'r') as f:
            data = json.load(f)
            results[period_name] = data

        print(f"Loaded: {file} ({period_name})")

    return results


def plot_equity_curve(trades, title="Equity Curve"):
    """Plot equity curve from trades."""
    equity = 0
    equity_curve = [0]

    for trade in trades:
        if trade['outcome'] != 'PENDING':
            equity += trade['pnl']
            equity_curve.append(equity)

    plt.figure(figsize=(14, 6))
    plt.plot(equity_curve, linewidth=2, color='steelblue')
    plt.fill_between(range(len(equity_curve)), equity_curve, alpha=0.3)
    plt.title(title, fontsize=14, fontweight='bold')
    plt.xlabel('Trade Number', fontsize=12)
    plt.ylabel('Cumulative P&L ($)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.axhline(y=0, color='red', linestyle='--', alpha=0.5)

    # Add final value annotation
    if equity_curve:
        final_value = equity_curve[-1]
        plt.text(
            len(equity_curve) - 1,
            final_value,
            f'${final_value:,.0f}',
            fontsize=10,
            ha='right',
            va='bottom' if final_value > 0 else 'top'
        )

    plt.tight_layout()
    return plt


def plot_drawdown(trades, title="Drawdown Analysis"):
    """Plot drawdown curve."""
    equity = 0
    equity_curve = []
    peak = 0
    drawdown_curve = []

    for trade in trades:
        if trade['outcome'] != 'PENDING':
            equity += trade['pnl']
            equity_curve.append(equity)

            if equity > peak:
                peak = equity

            drawdown = peak - equity
            drawdown_pct = (drawdown / peak * 100) if peak > 0 else 0
            drawdown_curve.append(drawdown_pct)

    plt.figure(figsize=(14, 6))
    plt.plot(drawdown_curve, linewidth=2, color='red')
    plt.fill_between(range(len(drawdown_curve)), drawdown_curve, alpha=0.3, color='red')
    plt.title(title, fontsize=14, fontweight='bold')
    plt.xlabel('Trade Number', fontsize=12)
    plt.ylabel('Drawdown (%)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.gca().invert_yaxis()  # Invert so drawdown goes down

    # Mark max drawdown
    if drawdown_curve:
        max_dd = max(drawdown_curve)
        max_dd_idx = drawdown_curve.index(max_dd)
        plt.scatter([max_dd_idx], [max_dd], color='darkred', s=100, zorder=5)
        plt.text(
            max_dd_idx,
            max_dd,
            f'Max DD: {max_dd:.2f}%',
            fontsize=10,
            ha='left',
            va='top'
        )

    plt.tight_layout()
    return plt


def plot_monthly_pnl(monthly_data, title="Monthly P&L"):
    """Plot monthly P&L bar chart."""
    months = sorted(monthly_data.keys())
    pnls = [monthly_data[m]['pnl'] for m in months]
    trade_counts = [monthly_data[m]['trades'] for m in months]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))

    # P&L bars
    colors = ['green' if p > 0 else 'red' for p in pnls]
    ax1.bar(range(len(months)), pnls, color=colors, alpha=0.7)
    ax1.set_title(title, fontsize=14, fontweight='bold')
    ax1.set_ylabel('P&L ($)', fontsize=12)
    ax1.set_xticks(range(len(months)))
    ax1.set_xticklabels(months, rotation=45, ha='right')
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.8)

    # Add value labels
    for i, (m, p) in enumerate(zip(months, pnls)):
        ax1.text(
            i,
            p,
            f'${p:,.0f}',
            fontsize=9,
            ha='center',
            va='bottom' if p > 0 else 'top'
        )

    # Trade count
    ax2.bar(range(len(months)), trade_counts, color='steelblue', alpha=0.7)
    ax2.set_ylabel('Trades', fontsize=12)
    ax2.set_xlabel('Month', fontsize=12)
    ax2.set_xticks(range(len(months)))
    ax2.set_xticklabels(months, rotation=45, ha='right')
    ax2.grid(True, alpha=0.3, axis='y')

    # Add count labels
    for i, count in enumerate(trade_counts):
        ax2.text(
            i,
            count,
            str(count),
            fontsize=9,
            ha='center',
            va='bottom'
        )

    plt.tight_layout()
    return plt


def plot_win_loss_distribution(trades, title="Win/Loss Distribution"):
    """Plot distribution of wins and losses."""
    wins = [t['pnl'] for t in trades if t['outcome'] == 'WIN' and t['outcome'] != 'PENDING']
    losses = [abs(t['pnl']) for t in trades if t['outcome'] == 'LOSS' and t['outcome'] != 'PENDING']

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Wins histogram
    if wins:
        ax1.hist(wins, bins=20, color='green', alpha=0.7, edgecolor='black')
        ax1.set_title('Win Distribution', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Win Amount ($)', fontsize=12)
        ax1.set_ylabel('Frequency', fontsize=12)
        ax1.axvline(np.mean(wins), color='darkgreen', linestyle='--', linewidth=2, label=f'Avg: ${np.mean(wins):.2f}')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

    # Losses histogram
    if losses:
        ax2.hist(losses, bins=20, color='red', alpha=0.7, edgecolor='black')
        ax2.set_title('Loss Distribution', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Loss Amount ($)', fontsize=12)
        ax2.set_ylabel('Frequency', fontsize=12)
        ax2.axvline(np.mean(losses), color='darkred', linestyle='--', linewidth=2, label=f'Avg: ${np.mean(losses):.2f}')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

    plt.suptitle(title, fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    return plt


def generate_summary_report(results):
    """Generate text summary report."""
    print("\n" + "="*70)
    print("BACKTEST SUMMARY REPORT")
    print("="*70)

    for period, data in results.items():
        summary = data['summary']
        risk = data['risk_metrics']
        perf = data['performance']

        print(f"\n{'─'*70}")
        print(f"PERIOD: {period.upper()}")
        print(f"{'─'*70}")

        print(f"\n📊 PERFORMANCE")
        print(f"  Total Trades:    {summary['total_trades']}")
        print(f"  Wins:            {summary['wins']} ({summary['win_rate']})")
        print(f"  Losses:          {summary['losses']}")
        print(f"  Total P&L:       ${summary['total_pnl']:,.2f}")
        print(f"  Profit Factor:   {summary['profit_factor']}")
        print(f"  Expectancy:      ${summary['expectancy']:.2f}/trade")

        print(f"\n⚠️  RISK")
        print(f"  Max Drawdown:    ${risk['max_drawdown']:,.2f} ({risk['max_drawdown_pct']})")
        print(f"  Largest Win:     ${risk['largest_win']:,.2f}")
        print(f"  Largest Loss:    ${risk['largest_loss']:,.2f}")

        print(f"\n📈 STATS")
        print(f"  Avg Win:         ${perf['avg_win']:,.2f}")
        print(f"  Avg Loss:        ${perf['avg_loss']:,.2f}")
        print(f"  Avg Duration:    {perf['avg_trade_duration_bars']:.1f} bars")
        print(f"  Max Win Streak:  {perf['max_consecutive_wins']}")
        print(f"  Max Loss Streak: {perf['max_consecutive_losses']}")

    print("\n" + "="*70)


def main():
    """Main visualization workflow."""
    print("="*70)
    print("BACKTEST RESULTS VISUALIZATION")
    print("="*70)

    # Load all results
    results = load_backtest_results()

    if not results:
        print("\nNo backtest results found!")
        print("Make sure backtest_results_*.json files exist.")
        return

    # Generate summary report
    generate_summary_report(results)

    # Create output directory
    os.makedirs('backtest_charts', exist_ok=True)

    # Generate visualizations for each period
    for period, data in results.items():
        trades = data['trades']

        print(f"\n[GENERATING CHARTS] {period}...")

        # Equity curve
        plot_equity_curve(trades, f"Equity Curve - {period.upper()}")
        plt.savefig(f'backtest_charts/equity_curve_{period}.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  [OK] Equity curve saved")

        # Drawdown
        plot_drawdown(trades, f"Drawdown Analysis - {period.upper()}")
        plt.savefig(f'backtest_charts/drawdown_{period}.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  [OK] Drawdown chart saved")

        # Win/Loss distribution
        plot_win_loss_distribution(trades, f"Win/Loss Distribution - {period.upper()}")
        plt.savefig(f'backtest_charts/win_loss_dist_{period}.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  [OK] Win/Loss distribution saved")

        # Monthly P&L
        if data['monthly_breakdown']:
            plot_monthly_pnl(data['monthly_breakdown'], f"Monthly P&L - {period.upper()}")
            plt.savefig(f'backtest_charts/monthly_pnl_{period}.png', dpi=150, bbox_inches='tight')
            plt.close()
            print(f"  [OK] Monthly P&L saved")

    print("\n" + "="*70)
    print("VISUALIZATION COMPLETE")
    print("="*70)
    print(f"\nCharts saved to: backtest_charts/")
    print(f"Files generated: {len(results) * 4} charts")
    print("\nCharts:")
    print("  - equity_curve_[period].png")
    print("  - drawdown_[period].png")
    print("  - win_loss_dist_[period].png")
    print("  - monthly_pnl_[period].png")
    print("="*70)


if __name__ == "__main__":
    main()
