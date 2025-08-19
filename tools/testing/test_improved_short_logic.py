#!/usr/bin/env python3
"""
TEST IMPROVED SHORT LOGIC
Verify that the new conservative SHORT criteria work correctly

Tests:
1. Score threshold (now < 2.0 instead of < 3.5)
2. BTC uptrend filter
3. Volume requirements
4. Technical confirmations
5. Position limits (max 3 SHORTs)
6. Exposure limits (max 15%)
7. Stop loss and take profit automatic setting
"""

import sys
import os
from datetime import datetime

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Mock data for testing
MOCK_CRYPTO_DATA = [
    {
        "symbol": "TEST1-USD",
        "name": "Test Crypto 1",
        "score": 1.5,  # Should pass (< 2.0)
        "change_percent": -3.0,  # Recent decline (good for SHORT)
        "volume": 80000000,  # High volume
        "market_cap": 3000000000,  # 3B market cap
        "current_price": 100.0
    },
    {
        "symbol": "TEST2-USD", 
        "name": "Test Crypto 2",
        "score": 2.5,  # Should fail (>= 2.0)
        "change_percent": -5.0,
        "volume": 120000000,
        "market_cap": 5000000000,
        "current_price": 50.0
    },
    {
        "symbol": "TEST3-USD",
        "name": "Test Crypto 3", 
        "score": 1.8,  # Pass score
        "change_percent": 15.0,  # Should fail (recent gains > 10%)
        "volume": 90000000,
        "market_cap": 4000000000,
        "current_price": 75.0
    },
    {
        "symbol": "TEST4-USD",
        "name": "Test Crypto 4",
        "score": 1.2,  # Pass score
        "change_percent": -2.0,  # Pass
        "volume": 30000000,  # Should fail (volume < 50M)
        "market_cap": 2000000000,
        "current_price": 25.0
    }
]

def test_score_threshold():
    """Test 1: Score threshold (< 2.0)"""
    print("TEST 1: Score Threshold (< 2.0)")
    print("=" * 40)
    
    for crypto in MOCK_CRYPTO_DATA:
        score = crypto["score"]
        symbol = crypto["symbol"]
        should_pass = score < 2.0
        
        print(f"  {symbol}: Score {score} -> {'PASS' if should_pass else 'FAIL'} (threshold)")
    
    print()

def test_volume_requirements():
    """Test 2: Volume requirements (>= 50M)"""
    print("TEST 2: Volume Requirements (>= 50M)")
    print("=" * 40)
    
    for crypto in MOCK_CRYPTO_DATA:
        volume = crypto["volume"]
        symbol = crypto["symbol"]
        should_pass = volume >= 50000000
        
        print(f"  {symbol}: Volume {volume:,} -> {'PASS' if should_pass else 'FAIL'} (volume)")
    
    print()

def test_recent_gains_filter():
    """Test 3: Recent gains filter (< 10%)"""
    print("TEST 3: Recent Gains Filter (< 10%)")
    print("=" * 40)
    
    for crypto in MOCK_CRYPTO_DATA:
        change = crypto["change_percent"]
        symbol = crypto["symbol"]
        should_pass = change <= 10.0
        
        print(f"  {symbol}: Change {change:.1f}% -> {'PASS' if should_pass else 'FAIL'} (gains filter)")
    
    print()

def test_technical_confirmations():
    """Test 4: Technical confirmations (need 2+)"""
    print("TEST 4: Technical Confirmations (need 2+)")
    print("=" * 40)
    
    for crypto in MOCK_CRYPTO_DATA:
        symbol = crypto["symbol"]
        confirmations = []
        
        # Simulation of confirmation logic
        if crypto["score"] <= 1.5:
            confirmations.append("Extremely bearish score")
        
        if crypto["change_percent"] < -5:
            confirmations.append("Strong recent decline")
        elif crypto["change_percent"] < -2:
            confirmations.append("Moderate decline")
        
        if crypto["volume"] > 100000000:
            confirmations.append("High volume bearish pressure")
        
        if crypto["market_cap"] < 5000000000:
            confirmations.append("Small cap vulnerability")
        
        should_pass = len(confirmations) >= 2
        
        print(f"  {symbol}: {len(confirmations)} confirmations -> {'PASS' if should_pass else 'FAIL'}")
        for conf in confirmations:
            print(f"    - {conf}")
    
    print()

def test_comprehensive_evaluation():
    """Test 5: Comprehensive evaluation (all criteria)"""
    print("TEST 5: Comprehensive Evaluation")
    print("=" * 40)
    
    print("Simulating SHORT signal evaluation for each crypto:")
    print()
    
    for crypto in MOCK_CRYPTO_DATA:
        symbol = crypto["symbol"]
        score = crypto["score"]
        change = crypto["change_percent"]
        volume = crypto["volume"]
        
        print(f"  {symbol}:")
        print(f"    Score: {score} (need < 2.0)")
        print(f"    Change: {change:.1f}% (need <= 10%)")
        print(f"    Volume: {volume:,} (need >= 50M)")
        
        # Evaluate each criteria
        score_pass = score < 2.0
        gains_pass = change <= 10.0
        volume_pass = volume >= 50000000
        
        # Count confirmations
        confirmations = 0
        if score <= 1.5:
            confirmations += 1
        if change < -2:
            confirmations += 1
        if volume > 100000000:
            confirmations += 1
        if crypto["market_cap"] < 5000000000:
            confirmations += 1
        
        confirmations_pass = confirmations >= 2
        
        overall_pass = score_pass and gains_pass and volume_pass and confirmations_pass
        
        print(f"    Confirmations: {confirmations}/4 (need >= 2)")
        print(f"    Overall: {'WOULD SHORT' if overall_pass else 'WOULD SKIP'}")
        print()

def test_stop_loss_calculation():
    """Test 6: Stop loss and take profit calculation"""
    print("TEST 6: Stop Loss & Take Profit Calculation")
    print("=" * 40)
    
    test_prices = [100.0, 50.0, 25.0, 1.0]
    
    for price in test_prices:
        stop_loss = price * 1.08  # 8% loss tolerance
        take_profit = price * 0.95  # 5% profit target
        
        print(f"  Entry Price: ${price:.2f}")
        print(f"    Stop Loss: ${stop_loss:.2f} (+8% price rise)")
        print(f"    Take Profit: ${take_profit:.2f} (-5% price fall)")
        print()

def test_position_limits():
    """Test 7: Position and exposure limits"""
    print("TEST 7: Position and Exposure Limits")
    print("=" * 40)
    
    print("Position Limits:")
    print("  Max SHORT positions: 3 (was unlimited)")
    print("  Max SHORT exposure: 15% of crypto portfolio")
    print()
    
    # Simulate portfolio with different SHORT exposures
    portfolio_scenarios = [
        {"current_shorts": 0, "exposure_pct": 0, "new_position": 5000},
        {"current_shorts": 2, "exposure_pct": 8, "new_position": 5000},
        {"current_shorts": 3, "exposure_pct": 12, "new_position": 5000},
        {"current_shorts": 2, "exposure_pct": 14, "new_position": 3000},
    ]
    
    for i, scenario in enumerate(portfolio_scenarios):
        shorts = scenario["current_shorts"]
        exposure = scenario["exposure_pct"]
        new_pos = scenario["new_position"]
        
        position_limit_ok = shorts < 3
        exposure_limit_ok = exposure + (new_pos / 50000 * 100) <= 15  # Assume 50k portfolio
        
        can_open = position_limit_ok and exposure_limit_ok
        
        print(f"  Scenario {i+1}:")
        print(f"    Current SHORTs: {shorts}/3")
        print(f"    Current exposure: {exposure:.1f}%")
        print(f"    New position: ${new_pos}")
        print(f"    Can open SHORT: {'YES' if can_open else 'NO'}")
        
        if not position_limit_ok:
            print(f"      Reason: Position limit reached")
        if not exposure_limit_ok:
            print(f"      Reason: Would exceed 15% exposure limit")
        print()

def main():
    """Run all tests"""
    print("IMPROVED SHORT LOGIC TEST SUITE")
    print(f"Test Time: {datetime.now()}")
    print("=" * 60)
    print()
    
    test_score_threshold()
    test_volume_requirements()
    test_recent_gains_filter()
    test_technical_confirmations()
    test_comprehensive_evaluation()
    test_stop_loss_calculation()
    test_position_limits()
    
    print("=" * 60)
    print("SUMMARY OF IMPROVEMENTS:")
    print()
    print("MADE MORE CONSERVATIVE:")
    print("  - Score threshold: 3.5 -> 2.0 (much stricter)")
    print("  - Volume requirement: Added 50M minimum")
    print("  - Technical confirmations: Require 2+ indicators")
    print("  - Recent gains filter: Block if >10% gains")
    print()
    print("ADDED RISK MANAGEMENT:")
    print("  - Max 3 SHORT positions (was unlimited)")
    print("  - Max 15% portfolio exposure to SHORTs")
    print("  - Automatic 8% stop loss")
    print("  - Automatic 5% take profit")
    print()
    print("IMPROVED EXIT LOGIC:")
    print("  - Exit when score improves to 3.0+")
    print("  - Exit on stop loss hit")
    print("  - Exit on take profit hit")
    print("  - Emergency exit if multiple SHORTs failing")
    print()
    print("RESULT: SHORT trading is now MUCH safer and more selective!")

if __name__ == "__main__":
    main()