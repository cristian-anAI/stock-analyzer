#!/usr/bin/env python3
"""
Backtest Metrics - Professional metrics for backtesting
Includes Sharpe ratio, Sortino ratio, max drawdown, Calmar ratio, etc.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class BacktestMetrics:
    """Calculate professional backtesting metrics"""

    def __init__(self, trades: List, daily_states: List, initial_capital: float):
        self.trades = trades
        self.daily_states = daily_states
        self.initial_capital = initial_capital

        # Create DataFrame for easier analysis
        self.daily_df = self._create_daily_dataframe()

    def _create_daily_dataframe(self) -> pd.DataFrame:
        """Create DataFrame from daily states"""
        if not self.daily_states:
            return pd.DataFrame()

        data = []
        for state in self.daily_states:
            data.append({
                'date': state.date,
                'total_value': state.total_value,
                'cash': state.cash_stocks + state.cash_crypto,
                'invested': state.invested_stocks + state.invested_crypto,
                'positions': state.positions_count
            })

        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

        # Calculate returns
        df['daily_return'] = df['total_value'].pct_change()

        return df

    def calculate_all_metrics(self) -> Dict[str, Any]:
        """Calculate all backtest metrics"""
        logger.info("Calculating professional backtest metrics...")

        metrics = {
            # Returns
            **self._calculate_returns(),

            # Risk metrics
            **self._calculate_risk_metrics(),

            # Drawdown metrics
            **self._calculate_drawdown_metrics(),

            # Trade statistics
            **self._calculate_trade_statistics(),

            # Risk-adjusted returns
            **self._calculate_risk_adjusted_returns(),

            # Consistency metrics
            **self._calculate_consistency_metrics(),

            # Benchmark comparison
            **self._calculate_benchmark_comparison()
        }

        return metrics

    def _calculate_returns(self) -> Dict[str, float]:
        """Calculate return metrics"""
        if self.daily_df.empty:
            return {}

        final_value = self.daily_df['total_value'].iloc[-1]
        total_return = (final_value - self.initial_capital) / self.initial_capital

        # CAGR (Compound Annual Growth Rate)
        days = len(self.daily_df)
        years = days / 252  # Trading days per year
        cagr = (final_value / self.initial_capital) ** (1 / years) - 1 if years > 0 else 0

        # Monthly returns
        monthly_returns = self.daily_df['total_value'].resample('M').last().pct_change()
        avg_monthly_return = monthly_returns.mean()

        return {
            'total_return': total_return * 100,
            'cagr': cagr * 100,
            'avg_monthly_return': avg_monthly_return * 100,
            'best_month': monthly_returns.max() * 100 if len(monthly_returns) > 0 else 0,
            'worst_month': monthly_returns.min() * 100 if len(monthly_returns) > 0 else 0
        }

    def _calculate_risk_metrics(self) -> Dict[str, float]:
        """Calculate risk metrics"""
        if self.daily_df.empty or 'daily_return' not in self.daily_df.columns:
            return {}

        returns = self.daily_df['daily_return'].dropna()

        # Volatility (annualized)
        volatility = returns.std() * np.sqrt(252)

        # Downside volatility (for Sortino)
        negative_returns = returns[returns < 0]
        downside_volatility = negative_returns.std() * np.sqrt(252)

        # Value at Risk (VaR) at 95% confidence
        var_95 = np.percentile(returns, 5) * 100

        # Maximum single day loss
        max_daily_loss = returns.min() * 100

        # Maximum single day gain
        max_daily_gain = returns.max() * 100

        return {
            'volatility_annual': volatility * 100,
            'downside_volatility': downside_volatility * 100,
            'var_95': var_95,
            'max_daily_loss': max_daily_loss,
            'max_daily_gain': max_daily_gain
        }

    def _calculate_drawdown_metrics(self) -> Dict[str, Any]:
        """Calculate drawdown metrics"""
        if self.daily_df.empty:
            return {}

        # Calculate running maximum
        running_max = self.daily_df['total_value'].expanding().max()

        # Calculate drawdown
        drawdown = (self.daily_df['total_value'] - running_max) / running_max

        # Maximum drawdown
        max_drawdown = drawdown.min()

        # Average drawdown
        avg_drawdown = drawdown[drawdown < 0].mean() if len(drawdown[drawdown < 0]) > 0 else 0

        # Find max drawdown period
        if max_drawdown < 0:
            max_dd_idx = drawdown.idxmin()
            # Find peak before max drawdown
            peak_idx = running_max[:max_dd_idx].idxmax()
            # Find recovery (if any)
            recovery_idx = None
            peak_value = running_max[peak_idx]

            for idx in self.daily_df[max_dd_idx:].index:
                if self.daily_df.loc[idx, 'total_value'] >= peak_value:
                    recovery_idx = idx
                    break

            drawdown_days = (max_dd_idx - peak_idx).days
            recovery_days = (recovery_idx - max_dd_idx).days if recovery_idx else None
        else:
            drawdown_days = 0
            recovery_days = 0

        return {
            'max_drawdown': max_drawdown * 100,
            'avg_drawdown': avg_drawdown * 100,
            'max_drawdown_days': drawdown_days,
            'recovery_days': recovery_days if recovery_days is not None else 'Not recovered'
        }

    def _calculate_trade_statistics(self) -> Dict[str, Any]:
        """Calculate trade-level statistics"""
        if not self.trades:
            return {}

        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl <= 0]

        # Win rate
        win_rate = len(winning_trades) / len(self.trades) * 100

        # Profit factor
        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Average trade
        avg_trade = np.mean([t.pnl for t in self.trades])

        # Average win/loss
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0

        # Win/Loss ratio
        win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')

        # Largest win/loss
        largest_win = max([t.pnl for t in self.trades])
        largest_loss = min([t.pnl for t in self.trades])

        # Average holding period
        avg_hold_days = np.mean([t.days_held for t in self.trades])

        # Total costs
        total_costs = sum(t.total_costs for t in self.trades)

        # Consecutive losses
        max_consecutive_losses = self._calculate_max_consecutive_losses()

        return {
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_trade_pnl': avg_trade,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'win_loss_ratio': win_loss_ratio,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'avg_hold_days': avg_hold_days,
            'total_costs_paid': total_costs,
            'max_consecutive_losses': max_consecutive_losses
        }

    def _calculate_max_consecutive_losses(self) -> int:
        """Calculate maximum consecutive losses"""
        if not self.trades:
            return 0

        max_consecutive = 0
        current_consecutive = 0

        for trade in sorted(self.trades, key=lambda t: t.exit_date):
            if trade.pnl < 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return max_consecutive

    def _calculate_risk_adjusted_returns(self) -> Dict[str, float]:
        """Calculate risk-adjusted return metrics"""
        if self.daily_df.empty or 'daily_return' not in self.daily_df.columns:
            return {}

        returns = self.daily_df['daily_return'].dropna()

        # Sharpe Ratio (assuming 4% risk-free rate)
        risk_free_rate = 0.04 / 252  # Daily risk-free rate
        excess_returns = returns - risk_free_rate
        sharpe_ratio = (excess_returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0

        # Sortino Ratio (uses downside deviation)
        negative_returns = returns[returns < risk_free_rate]
        downside_std = negative_returns.std()
        sortino_ratio = (excess_returns.mean() / downside_std) * np.sqrt(252) if downside_std > 0 else 0

        # Calmar Ratio (CAGR / Max Drawdown)
        cagr = self._calculate_returns().get('cagr', 0) / 100
        max_dd = abs(self._calculate_drawdown_metrics().get('max_drawdown', 1) / 100)
        calmar_ratio = cagr / max_dd if max_dd > 0 else 0

        # Information Ratio (vs SPY benchmark)
        # This would require SPY data, for now we'll use a simplified version
        info_ratio = sharpe_ratio  # Placeholder

        return {
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'information_ratio': info_ratio
        }

    def _calculate_consistency_metrics(self) -> Dict[str, Any]:
        """Calculate consistency metrics"""
        if self.daily_df.empty:
            return {}

        # Monthly returns
        monthly_returns = self.daily_df['total_value'].resample('M').last().pct_change()

        # Winning months
        winning_months = len(monthly_returns[monthly_returns > 0])
        total_months = len(monthly_returns.dropna())
        monthly_win_rate = (winning_months / total_months * 100) if total_months > 0 else 0

        # Standard deviation of monthly returns
        monthly_volatility = monthly_returns.std()

        # Longest winning streak
        longest_winning_streak = self._calculate_longest_streak(monthly_returns, positive=True)

        # Longest losing streak
        longest_losing_streak = self._calculate_longest_streak(monthly_returns, positive=False)

        return {
            'monthly_win_rate': monthly_win_rate,
            'total_months': total_months,
            'winning_months': winning_months,
            'monthly_volatility': monthly_volatility * 100,
            'longest_winning_streak': longest_winning_streak,
            'longest_losing_streak': longest_losing_streak
        }

    def _calculate_longest_streak(self, returns: pd.Series, positive: bool = True) -> int:
        """Calculate longest winning or losing streak"""
        max_streak = 0
        current_streak = 0

        for ret in returns.dropna():
            if (positive and ret > 0) or (not positive and ret < 0):
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0

        return max_streak

    def _calculate_benchmark_comparison(self) -> Dict[str, Any]:
        """Calculate metrics vs benchmark (S&P 500)"""
        if self.daily_df.empty:
            return {}

        # For now, use simplified benchmark comparison
        # In a real implementation, you would download SPY data
        strategy_return = self._calculate_returns().get('total_return', 0)

        # Assume SPY returns ~10% annually (historical average)
        days = len(self.daily_df)
        years = days / 252
        spy_benchmark = 10 * years  # 10% per year

        alpha = strategy_return - spy_benchmark

        return {
            'benchmark': 'S&P 500 (estimated)',
            'benchmark_return': spy_benchmark,
            'strategy_return': strategy_return,
            'alpha': alpha,
            'outperformance': alpha > 0
        }

    def generate_report(self) -> str:
        """Generate a text report of all metrics"""
        metrics = self.calculate_all_metrics()

        report = []
        report.append("="*70)
        report.append("PROFESSIONAL BACKTEST METRICS REPORT")
        report.append("="*70)

        # Returns
        report.append("\n📈 RETURNS")
        report.append("-"*70)
        report.append(f"Total Return:           {metrics.get('total_return', 0):>10.2f}%")
        report.append(f"CAGR:                   {metrics.get('cagr', 0):>10.2f}%")
        report.append(f"Avg Monthly Return:     {metrics.get('avg_monthly_return', 0):>10.2f}%")
        report.append(f"Best Month:             {metrics.get('best_month', 0):>10.2f}%")
        report.append(f"Worst Month:            {metrics.get('worst_month', 0):>10.2f}%")

        # Risk
        report.append("\n⚠️  RISK METRICS")
        report.append("-"*70)
        report.append(f"Annual Volatility:      {metrics.get('volatility_annual', 0):>10.2f}%")
        report.append(f"Downside Volatility:    {metrics.get('downside_volatility', 0):>10.2f}%")
        report.append(f"VaR (95%):              {metrics.get('var_95', 0):>10.2f}%")
        report.append(f"Max Daily Loss:         {metrics.get('max_daily_loss', 0):>10.2f}%")
        report.append(f"Max Daily Gain:         {metrics.get('max_daily_gain', 0):>10.2f}%")

        # Drawdown
        report.append("\n📉 DRAWDOWN METRICS")
        report.append("-"*70)
        report.append(f"Max Drawdown:           {metrics.get('max_drawdown', 0):>10.2f}%")
        report.append(f"Avg Drawdown:           {metrics.get('avg_drawdown', 0):>10.2f}%")
        report.append(f"Max Drawdown Days:      {metrics.get('max_drawdown_days', 0):>10.0f}")
        recovery = metrics.get('recovery_days', 'N/A')
        report.append(f"Recovery Days:          {str(recovery):>10}")

        # Trade Statistics
        report.append("\n💹 TRADE STATISTICS")
        report.append("-"*70)
        report.append(f"Total Trades:           {metrics.get('total_trades', 0):>10}")
        report.append(f"Winning Trades:         {metrics.get('winning_trades', 0):>10}")
        report.append(f"Losing Trades:          {metrics.get('losing_trades', 0):>10}")
        report.append(f"Win Rate:               {metrics.get('win_rate', 0):>10.2f}%")
        report.append(f"Profit Factor:          {metrics.get('profit_factor', 0):>10.2f}")
        report.append(f"Avg Trade P&L:          ${metrics.get('avg_trade_pnl', 0):>9,.2f}")
        report.append(f"Avg Win:                ${metrics.get('avg_win', 0):>9,.2f}")
        report.append(f"Avg Loss:               ${metrics.get('avg_loss', 0):>9,.2f}")
        report.append(f"Win/Loss Ratio:         {metrics.get('win_loss_ratio', 0):>10.2f}")
        report.append(f"Largest Win:            ${metrics.get('largest_win', 0):>9,.2f}")
        report.append(f"Largest Loss:           ${metrics.get('largest_loss', 0):>9,.2f}")
        report.append(f"Avg Hold Days:          {metrics.get('avg_hold_days', 0):>10.1f}")
        report.append(f"Total Costs Paid:       ${metrics.get('total_costs_paid', 0):>9,.2f}")
        report.append(f"Max Consecutive Losses: {metrics.get('max_consecutive_losses', 0):>10}")

        # Risk-Adjusted Returns
        report.append("\n📊 RISK-ADJUSTED RETURNS")
        report.append("-"*70)
        report.append(f"Sharpe Ratio:           {metrics.get('sharpe_ratio', 0):>10.2f}")
        report.append(f"Sortino Ratio:          {metrics.get('sortino_ratio', 0):>10.2f}")
        report.append(f"Calmar Ratio:           {metrics.get('calmar_ratio', 0):>10.2f}")

        # Consistency
        report.append("\n✅ CONSISTENCY")
        report.append("-"*70)
        report.append(f"Monthly Win Rate:       {metrics.get('monthly_win_rate', 0):>10.2f}%")
        report.append(f"Total Months:           {metrics.get('total_months', 0):>10}")
        report.append(f"Winning Months:         {metrics.get('winning_months', 0):>10}")
        report.append(f"Monthly Volatility:     {metrics.get('monthly_volatility', 0):>10.2f}%")
        report.append(f"Longest Win Streak:     {metrics.get('longest_winning_streak', 0):>10}")
        report.append(f"Longest Loss Streak:    {metrics.get('longest_losing_streak', 0):>10}")

        # Benchmark
        report.append("\n🎯 BENCHMARK COMPARISON")
        report.append("-"*70)
        report.append(f"Benchmark:              {metrics.get('benchmark', 'N/A')}")
        report.append(f"Benchmark Return:       {metrics.get('benchmark_return', 0):>10.2f}%")
        report.append(f"Strategy Return:        {metrics.get('strategy_return', 0):>10.2f}%")
        report.append(f"Alpha:                  {metrics.get('alpha', 0):>10.2f}%")
        outperf = "YES ✓" if metrics.get('outperformance', False) else "NO ✗"
        report.append(f"Outperformance:         {outperf:>10}")

        report.append("\n" + "="*70)

        # REALITY CHECK
        report.append("\n🚨 REALITY CHECK")
        report.append("-"*70)
        sharpe = metrics.get('sharpe_ratio', 0)
        win_rate = metrics.get('win_rate', 0)
        max_dd = abs(metrics.get('max_drawdown', 0))

        if sharpe > 2.0:
            report.append("⚠️  Sharpe > 2.0 is exceptionally rare - verify results")
        if win_rate > 70:
            report.append("⚠️  Win rate > 70% is suspicious - check for look-ahead bias")
        if max_dd < 5:
            report.append("⚠️  Max drawdown < 5% is unusual - check risk parameters")

        report.append("="*70)

        return "\n".join(report)
