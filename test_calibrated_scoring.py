#!/usr/bin/env python3
"""
Test script for the new calibrated scoring system
Validates realistic score distribution and FOMO prevention
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.api.services.scoring_service import ScoringService

def test_scoring_calibration():
    """Test the new calibrated scoring system"""
    scoring = ScoringService()
    
    print("CALIBRATED SCORING SYSTEM TEST")
    print("=" * 50)
    
    # Test stock scenarios
    print("\nSTOCKS - Realistic Scenarios:")
    
    stock_scenarios = [
        # FOMO scenarios (should get low scores)
        {"name": "AAPL ATH Rally", "change_percent": 5.2, "rsi": 78, "volume": 50000000, "market_cap": 3000000000000, "sector": "technology"},
        {"name": "AMD Pump", "change_percent": 8.1, "rsi": 82, "volume": 80000000, "market_cap": 200000000000, "sector": "semiconductors"},
        
        # Quality opportunities (should get good scores)
        {"name": "MSFT Dip", "change_percent": -2.1, "rsi": 32, "volume": 30000000, "market_cap": 2800000000000, "sector": "technology"},
        {"name": "Quality Value", "change_percent": -1.5, "rsi": 28, "volume": 15000000, "market_cap": 150000000000, "sector": "healthcare"},
        
        # Neutral scenarios
        {"name": "Sideways Stock", "change_percent": 0.3, "rsi": 52, "volume": 5000000, "market_cap": 50000000000, "sector": "consumer staples"},
    ]
    
    stock_scores = []
    for scenario in stock_scenarios:
        score = scoring.calculate_stock_score(scenario)
        stock_scores.append({"symbol": scenario["name"], "score": score})
        color = scoring.get_score_color(score)
        print(f"  {scenario['name']:<20} Score: {score:4.1f} ({color:>6}) - {scenario['change_percent']:+.1f}% RSI:{scenario['rsi']}")
    
    print("\nCRYPTO - Realistic Scenarios:")
    
    crypto_scenarios = [
        # FOMO scenarios (should get very low scores)
        {"name": "BTC ATH", "change_percent": 12.5, "rsi": 85, "volume": 25000000000, "market_cap": 1200000000000, "symbol": "BTC"},
        {"name": "ETH Pump", "change_percent": 15.8, "rsi": 79, "volume": 15000000000, "market_cap": 400000000000, "symbol": "ETH"},
        
        # Quality setups (should get decent scores but capped at 8)
        {"name": "SOL Oversold", "change_percent": -18.2, "rsi": 22, "volume": 2000000000, "market_cap": 45000000000, "symbol": "SOL"},
        {"name": "ADA Dip", "change_percent": -12.5, "rsi": 28, "volume": 800000000, "market_cap": 35000000000, "symbol": "ADA"},
        
        # Struggling scenarios
        {"name": "Small Alt Pump", "change_percent": 25.0, "rsi": 88, "volume": 50000000, "market_cap": 500000000, "symbol": "SHIB"},
    ]
    
    crypto_scores = []
    for scenario in crypto_scenarios:
        score = scoring.calculate_crypto_score(scenario)
        crypto_scores.append({"symbol": scenario["name"], "score": score})
        color = scoring.get_score_color(score)
        print(f"  {scenario['name']:<20} Score: {score:4.1f} ({color:>6}) - {scenario['change_percent']:+.1f}% RSI:{scenario['rsi']}")
    
    # Test relative ranking
    print("\nRELATIVE RANKING TEST:")
    ranked_stocks = scoring.apply_relative_ranking(stock_scores, 'stocks')
    ranked_cryptos = scoring.apply_relative_ranking(crypto_scores, 'cryptos')
    
    print("  Stocks (post-ranking):")
    for asset in ranked_stocks:
        color = scoring.get_score_color(asset['score'])
        print(f"    {asset['symbol']:<20} Score: {asset['score']:4.1f} ({color:>6}) Percentile: {asset['percentile']:5.1f}%")
    
    print("  Cryptos (post-ranking):")
    for asset in ranked_cryptos:
        color = scoring.get_score_color(asset['score'])
        print(f"    {asset['symbol']:<20} Score: {asset['score']:4.1f} ({color:>6}) Percentile: {asset['percentile']:5.1f}%")
    
    # Test market distribution
    print("\nMARKET DISTRIBUTION:")
    stock_dist = scoring.get_market_distribution('stocks')
    crypto_dist = scoring.get_market_distribution('cryptos')
    
    print(f"  Stocks: Mean={stock_dist['mean']:.1f}, High Scores={stock_dist['high_scores_pct']:.1f}%, Total={stock_dist['total_analyzed']}")
    print(f"  Cryptos: Mean={crypto_dist['mean']:.1f}, High Scores={crypto_dist['high_scores_pct']:.1f}%, Total={crypto_dist['total_analyzed']}")
    
    # Validation checks
    print("\nVALIDATION CHECKS:")
    
    # Check crypto max score cap
    max_crypto_score = max(s['score'] for s in crypto_scores)
    print(f"  Max crypto score: {max_crypto_score:.1f} (should be <= 8.0)")
    
    # Check FOMO penalties
    fomo_stocks = [s for s in ranked_stocks if s['symbol'] in ['AAPL ATH Rally', 'AMD Pump']]
    fomo_cryptos = [s for s in ranked_cryptos if s['symbol'] in ['BTC ATH', 'ETH Pump']]
    
    print(f"  FOMO stocks avg score: {sum(s['score'] for s in fomo_stocks) / len(fomo_stocks):.1f} (should be low)")
    print(f"  FOMO cryptos avg score: {sum(s['score'] for s in fomo_cryptos) / len(fomo_cryptos):.1f} (should be very low)")
    
    # Check high score distribution
    high_score_stocks = [s for s in ranked_stocks if s['score'] >= 8]
    high_score_cryptos = [s for s in ranked_cryptos if s['score'] >= 8]
    
    high_pct_stocks = len(high_score_stocks) / len(ranked_stocks) * 100
    high_pct_cryptos = len(high_score_cryptos) / len(ranked_cryptos) * 100
    
    print(f"  High score stocks: {high_pct_stocks:.1f}% (target: 5-10%)")
    print(f"  High score cryptos: {high_pct_cryptos:.1f}% (target: <5%)")
    
    print("\nSUMMARY:")
    print("  - FOMO prevention: Recent rallies get low scores")
    print("  - Volatility cap: Crypto max score = 8.0")
    print("  - Selective scoring: Lower base scores, higher standards")
    print("  - Relative ranking: Top performers only get high scores")
    print("  - Quality over quantity: Realistic score distribution")

if __name__ == "__main__":
    test_scoring_calibration()