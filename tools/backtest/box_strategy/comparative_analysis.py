"""
Comparative Market Analysis

Analyzes performance patterns across global markets.
Identifies correlations between market characteristics and strategy performance.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from pathlib import Path
import json

from market_config import get_market_config, MARKET_REGIONS


class ComparativeAnalyzer:
    """Analyze and compare backtest results across markets"""

    def __init__(self, results: Dict[str, Dict]):
        """
        Initialize Comparative Analyzer

        Args:
            results: Dictionary of backtest results by market code
        """
        self.results = results
        self.comparison_df = None
        self._build_comparison_df()

    def _build_comparison_df(self):
        """Build comprehensive comparison dataframe"""
        data = []

        for market_code, result in self.results.items():
            if result.get('error'):
                continue

            metrics = result.get('metrics', {})
            market_info = result.get('market_info', {})

            # Extract all relevant metrics
            basic = metrics.get('basic_stats', {})
            wr = metrics.get('win_rate', {})
            pf = metrics.get('profit_factor', {})
            sharpe = metrics.get('sharpe_ratio', {})
            sortino = metrics.get('sortino_ratio', {})
            mdd = metrics.get('max_drawdown', {})
            r_dist = metrics.get('r_distribution', {})
            monthly = metrics.get('monthly_returns', {})
            duration = metrics.get('trade_duration', {})
            directional = metrics.get('directional_stats', {})
            box_analysis = metrics.get('box_range_analysis', {})

            # Determine region
            region = None
            for reg, markets in MARKET_REGIONS.items():
                if market_code in markets:
                    region = reg
                    break

            row = {
                # Identification
                'market': market_code,
                'name': market_info.get('name', ''),
                'region': region,
                'currency': market_info.get('currency', ''),
                'timezone': market_info.get('timezone', ''),

                # Market characteristics
                'point_value': market_info.get('point_value', 0),
                'liquidity_rating': market_info.get('liquidity_rating', 0),
                'avg_box_range': box_analysis.get('avg_box_range', 0),
                'median_box_range': box_analysis.get('median_box_range', 0),

                # Trading activity
                'total_setups': result.get('total_setups', 0),
                'valid_entries': result.get('valid_entries', 0),
                'invalid_trades': result.get('invalid_trades', 0),
                'execution_rate': (
                    result.get('valid_entries', 0) / result.get('total_setups', 1) * 100
                    if result.get('total_setups', 0) > 0 else 0
                ),

                # Performance metrics
                'total_trades': basic.get('executed_trades', 0),
                'win_rate': wr.get('win_rate', 0),
                'profit_factor': pf.get('profit_factor', 0),
                'avg_r_multiple': r_dist.get('avg_r_multiple', 0),
                'median_r_multiple': r_dist.get('median_r_multiple', 0),

                # Risk-adjusted returns
                'sharpe_ratio': sharpe.get('sharpe_ratio', 0),
                'sortino_ratio': sortino.get('sortino_ratio', 0),
                'max_drawdown_pct': mdd.get('max_drawdown_pct', 0),

                # Returns
                'return_pct': result.get('return_pct', 0),
                'total_pnl_usd': result.get('total_pnl_usd', 0),
                'avg_monthly_return': monthly.get('avg_monthly_return', 0),

                # Win/Loss analysis
                'avg_win': wr.get('avg_win', 0),
                'avg_loss': wr.get('avg_loss', 0),
                'win_loss_ratio': wr.get('win_loss_ratio', 0),

                # Trade characteristics
                'avg_duration_hours': duration.get('avg_duration_hours', 0),
                'trades_under_1hour': duration.get('trades_under_1hour', 0),

                # Directional bias
                'long_trades': directional.get('long', {}).get('count', 0),
                'short_trades': directional.get('short', {}).get('count', 0),
                'long_win_rate': directional.get('long', {}).get('win_rate', 0),
                'short_win_rate': directional.get('short', {}).get('win_rate', 0),
            }

            data.append(row)

        self.comparison_df = pd.DataFrame(data)

    def rank_markets(self, metric: str = 'return_pct', ascending: bool = False) -> pd.DataFrame:
        """
        Rank markets by specific metric

        Args:
            metric: Metric to rank by
            ascending: Sort order

        Returns:
            Ranked dataframe
        """
        if metric not in self.comparison_df.columns:
            raise ValueError(
                f"Unknown metric: {metric}. "
                f"Available: {self.comparison_df.columns.tolist()}"
            )

        return self.comparison_df.sort_values(metric, ascending=ascending)

    def get_top_markets(
        self,
        metric: str = 'sharpe_ratio',
        top_n: int = 5
    ) -> pd.DataFrame:
        """Get top N markets by metric"""
        return self.rank_markets(metric).tail(top_n)

    def analyze_by_region(self) -> pd.DataFrame:
        """
        Analyze performance by geographic region

        Returns:
            DataFrame with regional statistics
        """
        regional_stats = []

        for region in self.comparison_df['region'].unique():
            region_df = self.comparison_df[self.comparison_df['region'] == region]

            stats = {
                'region': region,
                'markets_count': len(region_df),
                'avg_win_rate': region_df['win_rate'].mean(),
                'avg_profit_factor': region_df['profit_factor'].mean(),
                'avg_sharpe': region_df['sharpe_ratio'].mean(),
                'avg_return': region_df['return_pct'].mean(),
                'avg_execution_rate': region_df['execution_rate'].mean(),
                'best_market': region_df.nlargest(1, 'return_pct')['market'].values[0],
                'best_return': region_df['return_pct'].max()
            }

            regional_stats.append(stats)

        return pd.DataFrame(regional_stats).sort_values('avg_return', ascending=False)

    def correlate_characteristics_with_performance(self) -> pd.DataFrame:
        """
        Analyze correlation between market characteristics and performance

        Returns:
            DataFrame with correlation coefficients
        """
        # Select numeric columns for correlation
        characteristics = [
            'liquidity_rating',
            'avg_box_range',
            'execution_rate',
            'avg_duration_hours'
        ]

        performance_metrics = [
            'win_rate',
            'profit_factor',
            'sharpe_ratio',
            'return_pct'
        ]

        correlations = []

        for char in characteristics:
            for metric in performance_metrics:
                if char in self.comparison_df.columns and metric in self.comparison_df.columns:
                    corr = self.comparison_df[char].corr(self.comparison_df[metric])

                    correlations.append({
                        'characteristic': char,
                        'performance_metric': metric,
                        'correlation': corr,
                        'strength': self._interpret_correlation(abs(corr))
                    })

        df_corr = pd.DataFrame(correlations)
        return df_corr.sort_values('correlation', key=abs, ascending=False)

    def _interpret_correlation(self, corr: float) -> str:
        """Interpret correlation strength"""
        if abs(corr) < 0.3:
            return 'Weak'
        elif abs(corr) < 0.7:
            return 'Moderate'
        else:
            return 'Strong'

    def identify_best_market_profiles(self) -> Dict:
        """
        Identify characteristics of best-performing markets

        Returns:
            Dictionary with market profile analysis
        """
        # Get top 3 markets by multiple metrics
        metrics = ['return_pct', 'sharpe_ratio', 'profit_factor', 'win_rate']

        top_markets = set()
        for metric in metrics:
            top_3 = self.comparison_df.nlargest(3, metric)['market'].tolist()
            top_markets.update(top_3)

        # Analyze characteristics of top markets
        top_df = self.comparison_df[self.comparison_df['market'].isin(top_markets)]

        profile = {
            'top_markets': list(top_markets),
            'common_characteristics': {
                'avg_liquidity_rating': top_df['liquidity_rating'].mean(),
                'avg_execution_rate': top_df['execution_rate'].mean(),
                'avg_box_range': top_df['avg_box_range'].mean(),
                'preferred_regions': top_df['region'].value_counts().to_dict()
            },
            'performance_patterns': {
                'avg_win_rate': top_df['win_rate'].mean(),
                'avg_profit_factor': top_df['profit_factor'].mean(),
                'avg_sharpe': top_df['sharpe_ratio'].mean(),
                'avg_return': top_df['return_pct'].mean()
            }
        }

        return profile

    def volatility_analysis(self) -> pd.DataFrame:
        """
        Analyze relationship between box range (volatility) and performance

        Returns:
            DataFrame with volatility analysis
        """
        df = self.comparison_df.copy()

        # Categorize markets by box range
        df['volatility_category'] = pd.cut(
            df['avg_box_range'],
            bins=3,
            labels=['Low', 'Medium', 'High']
        )

        # Group by volatility category
        vol_analysis = df.groupby('volatility_category').agg({
            'market': 'count',
            'win_rate': 'mean',
            'profit_factor': 'mean',
            'sharpe_ratio': 'mean',
            'return_pct': 'mean',
            'execution_rate': 'mean'
        }).rename(columns={'market': 'market_count'})

        return vol_analysis

    def generate_trading_recommendations(self) -> List[Dict]:
        """
        Generate trading recommendations based on analysis

        Returns:
            List of recommendations
        """
        recommendations = []

        # Recommendation 1: Best overall markets
        top_sharpe = self.comparison_df.nlargest(3, 'sharpe_ratio')
        recommendations.append({
            'category': 'Best Risk-Adjusted Returns',
            'recommendation': f"Focus on {', '.join(top_sharpe['market'].tolist())}",
            'rationale': f"Highest Sharpe ratios (avg: {top_sharpe['sharpe_ratio'].mean():.2f})",
            'markets': top_sharpe[['market', 'sharpe_ratio', 'win_rate', 'profit_factor']].to_dict('records')
        })

        # Recommendation 2: Best by region
        regional = self.analyze_by_region()
        best_region = regional.iloc[0]
        recommendations.append({
            'category': 'Best Regional Focus',
            'recommendation': f"Prioritize {best_region['region']} markets",
            'rationale': f"Avg return: {best_region['avg_return']:.2f}%, "
                        f"Win rate: {best_region['avg_win_rate']:.2f}%",
            'best_market': best_region['best_market']
        })

        # Recommendation 3: Execution efficiency
        high_execution = self.comparison_df[self.comparison_df['execution_rate'] > 50]
        if not high_execution.empty:
            recommendations.append({
                'category': 'High Execution Efficiency',
                'recommendation': f"Markets with >50% execution rate: "
                                f"{', '.join(high_execution['market'].tolist())}",
                'rationale': "Higher probability of order fills reduces missed opportunities",
                'avg_execution_rate': high_execution['execution_rate'].mean()
            })

        # Recommendation 4: Consistent performers
        consistent = self.comparison_df[
            (self.comparison_df['win_rate'] > 50) &
            (self.comparison_df['profit_factor'] > 1.5) &
            (self.comparison_df['sharpe_ratio'] > 1.0)
        ]

        if not consistent.empty:
            recommendations.append({
                'category': 'Consistent Performers',
                'recommendation': f"All-around strong markets: "
                                f"{', '.join(consistent['market'].tolist())}",
                'rationale': "Meet multiple quality criteria (WR>50%, PF>1.5, Sharpe>1.0)",
                'markets': consistent[['market', 'win_rate', 'profit_factor', 'sharpe_ratio']].to_dict('records')
            })

        return recommendations

    def export_analysis(self, output_dir: str = "tools/backtest/box_strategy/analysis"):
        """
        Export comprehensive analysis

        Args:
            output_dir: Output directory
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")

        # 1. Full comparison table
        csv_file = output_path / f"market_comparison_{timestamp}.csv"
        self.comparison_df.to_csv(csv_file, index=False)
        print(f"[OK] Comparison table: {csv_file}")

        # 2. Regional analysis
        regional = self.analyze_by_region()
        regional_file = output_path / f"regional_analysis_{timestamp}.csv"
        regional.to_csv(regional_file, index=False)
        print(f"[OK] Regional analysis: {regional_file}")

        # 3. Correlations
        correlations = self.correlate_characteristics_with_performance()
        corr_file = output_path / f"correlations_{timestamp}.csv"
        correlations.to_csv(corr_file, index=False)
        print(f"[OK] Correlations: {corr_file}")

        # 4. Recommendations
        recommendations = self.generate_trading_recommendations()
        rec_file = output_path / f"recommendations_{timestamp}.json"
        with open(rec_file, 'w') as f:
            json.dump(recommendations, f, indent=2)
        print(f"[OK] Recommendations: {rec_file}")

        return csv_file

    def print_analysis_summary(self):
        """Print comprehensive analysis summary"""
        print(f"\n{'='*120}")
        print("COMPARATIVE MARKET ANALYSIS")
        print(f"{'='*120}\n")

        # Top performers
        print("TOP 5 MARKETS BY SHARPE RATIO:")
        print("-" * 120)
        top_sharpe = self.get_top_markets('sharpe_ratio', 5)
        print(top_sharpe[['market', 'name', 'sharpe_ratio', 'win_rate', 'return_pct']].to_string(index=False))

        # Regional analysis
        print(f"\n\nPERFORMANCE BY REGION:")
        print("-" * 120)
        regional = self.analyze_by_region()
        print(regional.to_string(index=False))

        # Correlations
        print(f"\n\nKEY CORRELATIONS:")
        print("-" * 120)
        correlations = self.correlate_characteristics_with_performance()
        strong_corr = correlations[correlations['strength'].isin(['Strong', 'Moderate'])]
        print(strong_corr.to_string(index=False))

        # Recommendations
        print(f"\n\nTRADING RECOMMENDATIONS:")
        print("-" * 120)
        recommendations = self.generate_trading_recommendations()
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec['category']}:")
            print(f"   {rec['recommendation']}")
            print(f"   Rationale: {rec['rationale']}")

        print(f"\n{'='*120}\n")


if __name__ == "__main__":
    # Test with sample data
    print("Comparative Analysis Module - Test mode")
    print("Run multi_market_backtester.py first to generate results")
