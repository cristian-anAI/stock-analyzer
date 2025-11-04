"""
Analyze correlation between US equity indices for Box Strategy

Analyzes:
- SPX (S&P 500) - Broad market 500 large caps
- NDX (NASDAQ 100) - Tech-heavy 100 largest non-financial
- Russell 2000 - Small cap index

Purpose: Understand how these markets move together to improve ML predictions
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Market tickers
MARKETS = {
    'SPX': '^GSPC',      # S&P 500
    'NDX': '^NDX',       # NASDAQ 100
    'RUT': '^RUT'        # Russell 2000
}

def download_market_data(lookback_days=365):
    """Download historical data for all markets"""
    print(f"\n Downloading {lookback_days} days of data...")

    data = {}
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)

    for market, ticker in MARKETS.items():
        print(f"  - {market} ({ticker})")
        df = yf.download(ticker, start=start_date, end=end_date, interval='1d', progress=False)

        if df.empty:
            print(f"     No data for {market}")
            continue

        # Handle both single and multi-level column indexes
        if isinstance(df.columns, pd.MultiIndex):
            close_col = df['Close'].iloc[:, 0] if df['Close'].shape[1] > 0 else df['Close']
        else:
            close_col = df['Close']

        data[market] = close_col
        print(f"     {len(df)} days")

    # Combine into single DataFrame
    df_combined = pd.DataFrame(data)
    df_combined = df_combined.dropna()

    print(f"\n Combined data: {len(df_combined)} days with all markets")
    return df_combined

def calculate_returns(df):
    """Calculate daily returns"""
    returns = df.pct_change().dropna()
    return returns

def analyze_correlation(returns):
    """Analyze correlation between markets"""
    print("\n" + "="*60)
    print(" CORRELATION ANALYSIS")
    print("="*60)

    # Overall correlation
    corr_matrix = returns.corr()
    print("\n1. Overall Correlation Matrix:")
    print(corr_matrix.round(3))

    # Correlation over different time windows
    windows = [30, 60, 90, 180, 365]
    rolling_corr = {}

    print("\n2. Correlation by Time Window:")
    print("-" * 60)
    for window in windows:
        if len(returns) < window:
            continue

        recent_returns = returns.tail(window)
        recent_corr = recent_returns.corr()
        rolling_corr[window] = recent_corr

        print(f"\nLast {window} days:")
        print(recent_corr.round(3))

    return corr_matrix, rolling_corr

def analyze_directional_agreement(returns):
    """Analyze how often markets move in same direction"""
    print("\n" + "="*60)
    print(" DIRECTIONAL AGREEMENT ANALYSIS")
    print("="*60)

    # Convert returns to direction (up/down)
    directions = (returns > 0).astype(int)

    # Calculate agreement rates
    print("\n% of days markets move in SAME direction:")
    print("-" * 60)

    pairs = [
        ('SPX', 'NDX'),
        ('SPX', 'RUT'),
        ('NDX', 'RUT')
    ]

    agreement_stats = {}

    for market1, market2 in pairs:
        same_direction = (directions[market1] == directions[market2]).sum()
        total_days = len(directions)
        agreement_pct = (same_direction / total_days) * 100

        # When they move together, how correlated is the magnitude?
        same_dir_mask = directions[market1] == directions[market2]
        magnitude_corr = returns[same_dir_mask][[market1, market2]].corr().iloc[0, 1]

        agreement_stats[f"{market1}-{market2}"] = {
            'agreement_pct': agreement_pct,
            'magnitude_corr': magnitude_corr,
            'days': same_direction,
            'total': total_days
        }

        print(f"\n{market1} <-> {market2}:")
        print(f"  Same direction: {agreement_pct:.1f}% ({same_direction}/{total_days} days)")
        print(f"  Magnitude correlation when aligned: {magnitude_corr:.3f}")

    return agreement_stats

def analyze_divergences(returns, threshold=0.01):
    """Find significant divergences between markets"""
    print("\n" + "="*60)
    print("  DIVERGENCE ANALYSIS")
    print("="*60)

    directions = np.sign(returns)

    # Find days with significant divergences
    divergences = {
        'SPX_up_NDX_down': 0,
        'SPX_down_NDX_up': 0,
        'SPX_up_RUT_down': 0,
        'SPX_down_RUT_up': 0,
        'NDX_up_RUT_down': 0,
        'NDX_down_RUT_up': 0
    }

    # Only count significant moves (> threshold)
    significant = returns.abs() > threshold

    for idx in returns.index:
        if not all(significant.loc[idx]):
            continue

        if directions.loc[idx, 'SPX'] > 0 and directions.loc[idx, 'NDX'] < 0:
            divergences['SPX_up_NDX_down'] += 1
        elif directions.loc[idx, 'SPX'] < 0 and directions.loc[idx, 'NDX'] > 0:
            divergences['SPX_down_NDX_up'] += 1

        if directions.loc[idx, 'SPX'] > 0 and directions.loc[idx, 'RUT'] < 0:
            divergences['SPX_up_RUT_down'] += 1
        elif directions.loc[idx, 'SPX'] < 0 and directions.loc[idx, 'RUT'] > 0:
            divergences['SPX_down_RUT_up'] += 1

        if directions.loc[idx, 'NDX'] > 0 and directions.loc[idx, 'RUT'] < 0:
            divergences['NDX_up_RUT_down'] += 1
        elif directions.loc[idx, 'NDX'] < 0 and directions.loc[idx, 'RUT'] > 0:
            divergences['NDX_down_RUT_up'] += 1

    print(f"\nSignificant divergences (moves > {threshold*100}%):")
    print("-" * 60)
    for div_type, count in divergences.items():
        market1, dir1, market2, dir2 = div_type.replace('_', ' ').split()
        print(f"{market1:>4} {dir1:>4} while {market2:>4} {dir2:>4}: {count:>3} days")

    return divergences

def analyze_box_strategy_implications(df, returns):
    """Analyze implications for box strategy"""
    print("\n" + "="*60)
    print(" BOX STRATEGY IMPLICATIONS")
    print("="*60)

    # Simulate box period (first 90 minutes = 8:30-10:00 AM)
    # We'll use 5-minute data for this
    print("\nDownloading intraday data for correlation analysis...")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    intraday_data = {}
    for market, ticker in MARKETS.items():
        print(f"  - {market} (5min data)")
        df_5min = yf.download(ticker, start=start_date, end=end_date, interval='5m', progress=False)
        if not df_5min.empty:
            intraday_data[market] = df_5min

    if not intraday_data:
        print(" No intraday data available")
        return

    # Analyze breakout correlation
    print("\n1. Breakout Timing Correlation:")
    print("-" * 60)
    print("Analyzing if breakouts happen simultaneously across markets...")

    # For each day, check if box breakouts happen in same direction
    # (This requires actual box strategy output - simplified here)

    print("\n2. Recommendations for ML Model:")
    print("-" * 60)
    print("""
    Based on correlation analysis, add these features:

     INTER-MARKET FEATURES:
       - correlation_spx_ndx_30d: 30-day rolling correlation
       - correlation_spx_rut_30d: 30-day rolling correlation
       - correlation_ndx_rut_30d: 30-day rolling correlation

     RELATIVE STRENGTH FEATURES:
       - relative_strength_vs_spx: (NDX return - SPX return) over 5d
       - relative_strength_vs_rut: (NDX return - RUT return) over 5d

     DIVERGENCE FEATURES:
       - direction_alignment_spx_ndx: 1 if same direction, 0 if opposite
       - direction_alignment_spx_rut: 1 if same direction, 0 if opposite
       - magnitude_difference_spx_ndx: abs(SPX_return - NDX_return)

     BREAKOUT CONFLUENCE:
       - other_markets_breaking_same_dir: Count of correlated markets breaking same way
       - market_strength_rank: Where does this market rank in strength today?
    """)

def plot_correlation_heatmap(corr_matrix, output_dir):
    """Plot correlation heatmap"""
    plt.figure(figsize=(10, 8))
    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0,
                vmin=-1, vmax=1, square=True, linewidths=1)
    plt.title('Market Correlation Matrix (Daily Returns)', fontsize=14, fontweight='bold')
    plt.tight_layout()

    output_path = output_dir / 'market_correlation_heatmap.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n Saved heatmap: {output_path}")
    plt.close()

def plot_rolling_correlation(returns, output_dir):
    """Plot rolling correlation over time"""
    window = 30

    fig, axes = plt.subplots(3, 1, figsize=(12, 10))

    pairs = [
        ('SPX', 'NDX', 'S&P 500 vs NASDAQ 100'),
        ('SPX', 'RUT', 'S&P 500 vs Russell 2000'),
        ('NDX', 'RUT', 'NASDAQ 100 vs Russell 2000')
    ]

    for idx, (market1, market2, title) in enumerate(pairs):
        rolling_corr = returns[[market1, market2]].rolling(window).corr().iloc[0::2, 1]

        axes[idx].plot(rolling_corr.index, rolling_corr.values, linewidth=2)
        axes[idx].axhline(y=0.7, color='green', linestyle='--', alpha=0.5, label='High correlation')
        axes[idx].axhline(y=0, color='gray', linestyle='-', alpha=0.3)
        axes[idx].set_title(f'{title} - {window}d Rolling Correlation', fontweight='bold')
        axes[idx].set_ylabel('Correlation')
        axes[idx].grid(True, alpha=0.3)
        axes[idx].legend()
        axes[idx].set_ylim(-1, 1)

    axes[-1].set_xlabel('Date')
    plt.tight_layout()

    output_path = output_dir / 'rolling_correlation.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f" Saved rolling correlation: {output_path}")
    plt.close()

def save_correlation_features_to_csv(returns, output_dir):
    """Save daily correlation features that can be used for ML training"""
    print("\n" + "="*60)
    print(" SAVING CORRELATION FEATURES FOR ML")
    print("="*60)

    # Calculate features for each day
    features = pd.DataFrame(index=returns.index)

    # Rolling correlations (30-day window)
    for window in [30, 60, 90]:
        features[f'corr_spx_ndx_{window}d'] = returns[['SPX', 'NDX']].rolling(window).corr().iloc[0::2, 1].values
        features[f'corr_spx_rut_{window}d'] = returns[['SPX', 'RUT']].rolling(window).corr().iloc[0::2, 1].values
        features[f'corr_ndx_rut_{window}d'] = returns[['NDX', 'RUT']].rolling(window).corr().iloc[0::2, 1].values

    # Relative strength (5-day rolling)
    for window in [5, 10, 20]:
        features[f'rel_strength_ndx_vs_spx_{window}d'] = (
            returns['NDX'].rolling(window).sum() - returns['SPX'].rolling(window).sum()
        )
        features[f'rel_strength_rut_vs_spx_{window}d'] = (
            returns['RUT'].rolling(window).sum() - returns['SPX'].rolling(window).sum()
        )

    # Direction alignment
    directions = (returns > 0).astype(int)
    features['direction_align_spx_ndx'] = (directions['SPX'] == directions['NDX']).astype(int)
    features['direction_align_spx_rut'] = (directions['SPX'] == directions['RUT']).astype(int)
    features['direction_align_ndx_rut'] = (directions['NDX'] == directions['RUT']).astype(int)

    # Magnitude differences
    features['magnitude_diff_spx_ndx'] = (returns['SPX'] - returns['NDX']).abs()
    features['magnitude_diff_spx_rut'] = (returns['SPX'] - returns['RUT']).abs()
    features['magnitude_diff_ndx_rut'] = (returns['NDX'] - returns['RUT']).abs()

    # Market strength rank (1=strongest, 3=weakest)
    for idx in returns.index:
        day_returns = returns.loc[idx]
        features.loc[idx, 'rank_spx'] = day_returns.rank(ascending=False)['SPX']
        features.loc[idx, 'rank_ndx'] = day_returns.rank(ascending=False)['NDX']
        features.loc[idx, 'rank_rut'] = day_returns.rank(ascending=False)['RUT']

    # Drop NaN rows
    features = features.dropna()

    # Save to CSV
    output_path = output_dir / 'market_correlation_features.csv'
    features.to_csv(output_path)

    print(f"\n Saved {len(features)} days of correlation features")
    print(f"   File: {output_path}")
    print(f"\nFeatures included ({len(features.columns)} total):")
    for col in sorted(features.columns):
        print(f"  - {col}")

    return features

def main():
    """Main analysis"""
    print("="*60)
    print("MARKET CORRELATION ANALYSIS")
    print("   SPX | NDX | Russell 2000")
    print("="*60)

    # Setup output directory
    output_dir = Path('ml/correlation_analysis')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Download data
    df = download_market_data(lookback_days=365)

    if df.empty:
        print(" No data available")
        return

    # Calculate returns
    returns = calculate_returns(df)

    # Analyze correlation
    corr_matrix, rolling_corr = analyze_correlation(returns)

    # Analyze directional agreement
    agreement_stats = analyze_directional_agreement(returns)

    # Analyze divergences
    divergences = analyze_divergences(returns)

    # Box strategy implications
    analyze_box_strategy_implications(df, returns)

    # Plot results
    plot_correlation_heatmap(corr_matrix, output_dir)
    plot_rolling_correlation(returns, output_dir)

    # Save features for ML
    features = save_correlation_features_to_csv(returns, output_dir)

    # Save summary report
    summary_path = output_dir / 'correlation_summary.txt'
    with open(summary_path, 'w') as f:
        f.write("MARKET CORRELATION SUMMARY\n")
        f.write("="*60 + "\n\n")
        f.write("Overall Correlation Matrix:\n")
        f.write(corr_matrix.to_string() + "\n\n")
        f.write("Directional Agreement:\n")
        for pair, stats in agreement_stats.items():
            f.write(f"{pair}: {stats['agreement_pct']:.1f}% agreement\n")

    print(f"\n Analysis complete!")
    print(f"   Results saved to: {output_dir}")

if __name__ == '__main__':
    main()
