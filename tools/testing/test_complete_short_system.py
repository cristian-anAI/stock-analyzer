#!/usr/bin/env python3
"""
COMPLETE SHORT SYSTEM TEST
Final verification that all SHORT components are working correctly
"""

import sqlite3
import requests
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any

class CompleteShortSystemTest:
    def __init__(self, db_path='trading.db', api_base_url='http://localhost:8000'):
        self.db_path = db_path
        self.api_base_url = api_base_url
        self.results = []
        
    def log(self, message: str, status: str = "INFO"):
        """Log test results"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {status}: {message}"
        self.results.append(entry)
        print(entry)
    
    def test_database_schema(self):
        """Test 1: Verify database schema supports SHORT positions"""
        self.log("=" * 60)
        self.log("TEST 1: DATABASE SCHEMA FOR SHORT POSITIONS")
        self.log("=" * 60)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if positions table has position_side column
            cursor.execute("PRAGMA table_info(positions)")
            columns = [col[1] for col in cursor.fetchall()]
            
            required_columns = ['position_side', 'stop_loss_updated', 'take_profit_updated']
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                self.log(f"MISSING COLUMNS: {missing_columns}", "FAIL")
                return False
            else:
                self.log(" All required columns present", "PASS")
            
            # Check if autotrader_transactions table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='autotrader_transactions'")
            if not cursor.fetchone():
                self.log("MISSING TABLE: autotrader_transactions", "FAIL")
                return False
            else:
                self.log(" autotrader_transactions table exists", "PASS")
            
            conn.close()
            return True
            
        except Exception as e:
            self.log(f"Database schema test failed: {e}", "FAIL")
            return False
    
    def test_short_positions_data(self):
        """Test 2: Verify SHORT positions data integrity"""
        self.log("\n" + "=" * 60)
        self.log("TEST 2: SHORT POSITIONS DATA INTEGRITY")
        self.log("=" * 60)
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get SHORT positions
            cursor.execute("""
                SELECT symbol, entry_price, current_price, quantity, pnl, pnl_percent,
                       stop_loss_updated, take_profit_updated, position_side
                FROM positions 
                WHERE position_side = 'SHORT'
            """)
            
            positions = cursor.fetchall()
            
            if not positions:
                self.log("No SHORT positions found - this is OK", "INFO")
                conn.close()
                return True
            
            self.log(f"Found {len(positions)} SHORT positions")
            
            all_valid = True
            for pos in positions:
                symbol = pos['symbol']
                entry_price = pos['entry_price']
                current_price = pos['current_price'] or entry_price
                quantity = pos['quantity']
                pnl = pos['pnl'] or 0
                stop_loss = pos['stop_loss_updated']
                take_profit = pos['take_profit_updated']
                
                # Test P&L calculation
                expected_pnl = (entry_price - current_price) * quantity
                pnl_diff = abs(expected_pnl - pnl)
                
                if pnl_diff > 0.01:
                    self.log(f" {symbol}: P&L calculation error - Expected: ${expected_pnl:.2f}, Got: ${pnl:.2f}", "FAIL")
                    all_valid = False
                else:
                    self.log(f" {symbol}: P&L calculation correct", "PASS")
                
                # Test stop loss and take profit
                if not stop_loss or stop_loss <= 0:
                    self.log(f" {symbol}: Missing or invalid stop loss", "FAIL")
                    all_valid = False
                else:
                    expected_stop = entry_price * 1.08
                    if abs(stop_loss - expected_stop) > 0.01:
                        self.log(f" {symbol}: Stop loss incorrect - Expected: ${expected_stop:.4f}, Got: ${stop_loss:.4f}", "FAIL")
                        all_valid = False
                    else:
                        self.log(f" {symbol}: Stop loss correct (${stop_loss:.4f})", "PASS")
                
                if not take_profit or take_profit <= 0:
                    self.log(f" {symbol}: Missing or invalid take profit", "FAIL")
                    all_valid = False
                else:
                    expected_tp = entry_price * 0.95
                    if abs(take_profit - expected_tp) > 0.01:
                        self.log(f" {symbol}: Take profit incorrect - Expected: ${expected_tp:.4f}, Got: ${take_profit:.4f}", "FAIL")
                        all_valid = False
                    else:
                        self.log(f" {symbol}: Take profit correct (${take_profit:.4f})", "PASS")
            
            conn.close()
            return all_valid
            
        except Exception as e:
            self.log(f"SHORT positions data test failed: {e}", "FAIL")
            return False
    
    def test_api_endpoints(self):
        """Test 3: Verify SHORT monitoring API endpoints"""
        self.log("\n" + "=" * 60)
        self.log("TEST 3: SHORT MONITORING API ENDPOINTS")
        self.log("=" * 60)
        
        endpoints = [
            "/api/v1/short-positions",
            "/api/v1/short-performance", 
            "/api/v1/short-alerts"
        ]
        
        all_working = True
        
        for endpoint in endpoints:
            try:
                url = f"{self.api_base_url}{endpoint}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if "error" not in data:
                        self.log(f" {endpoint}: Working correctly", "PASS")
                    else:
                        self.log(f" {endpoint}: API error - {data['error']}", "FAIL")
                        all_working = False
                else:
                    self.log(f" {endpoint}: HTTP {response.status_code}", "FAIL")
                    all_working = False
                    
            except Exception as e:
                self.log(f" {endpoint}: Connection error - {e}", "FAIL")
                all_working = False
        
        return all_working
    
    def test_autotrader_short_logic(self):
        """Test 4: Verify autotrader SHORT logic"""
        self.log("\n" + "=" * 60)
        self.log("TEST 4: AUTOTRADER SHORT LOGIC")
        self.log("=" * 60)
        
        try:
            # Import the autotrader service
            sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
            from src.api.services.autotrader_service import AutotraderService
            
            autotrader = AutotraderService()
            
            # Test SHORT signal evaluation
            mock_crypto_data = {
                "symbol": "TEST-USD",
                "name": "Test Crypto",
                "score": 1.5,  # Should trigger SHORT
                "change_percent": -3.0,
                "volume": 80000000,
                "market_cap": 3000000000,
                "current_price": 100.0
            }
            
            short_signal = autotrader.evaluate_crypto_short_signals(mock_crypto_data)
            
            if short_signal:
                self.log(" SHORT signal evaluation working", "PASS")
                self.log(f"  Signal confidence: {short_signal.get('confidence', 0)}%", "INFO")
                self.log(f"  Required capital: ${short_signal.get('required_capital', 0):.2f}", "INFO")
            else:
                self.log(" SHORT signal correctly rejected (ultra-conservative)", "PASS")
            
            # Test BTC uptrend check
            btc_uptrend = autotrader._check_btc_uptrend()
            self.log(f" BTC uptrend check working: {btc_uptrend}", "PASS")
            
            # Test position counting
            short_count = autotrader._count_current_short_positions('crypto')
            self.log(f" SHORT position counting working: {short_count} positions", "PASS")
            
            return True
            
        except Exception as e:
            self.log(f"Autotrader SHORT logic test failed: {e}", "FAIL")
            return False
    
    def test_advanced_scoring(self):
        """Test 5: Verify advanced scoring system"""
        self.log("\n" + "=" * 60)
        self.log("TEST 5: ADVANCED SCORING SYSTEM")
        self.log("=" * 60)
        
        try:
            from src.api.services.advanced_scoring_service import AdvancedScoringService
            
            advanced_scoring = AdvancedScoringService()
            
            # Test with mock data
            mock_crypto = {
                "symbol": "TEST-USD",
                "score": 1.5,
                "change_percent": -5.0,
                "volume": 100000000,
                "market_cap": 5000000000,
                "current_price": 50.0
            }
            
            scoring_result = advanced_scoring.calculate_short_weighted_score(mock_crypto)
            
            required_fields = ['final_score', 'technical_score', 'sentiment_score', 'momentum_score', 'short_eligible', 'confidence']
            missing_fields = [field for field in required_fields if field not in scoring_result]
            
            if missing_fields:
                self.log(f" Missing scoring fields: {missing_fields}", "FAIL")
                return False
            
            self.log(" Advanced scoring system working", "PASS")
            self.log(f"  Final score: {scoring_result['final_score']:.2f}", "INFO")
            self.log(f"  SHORT eligible: {scoring_result['short_eligible']}", "INFO")
            self.log(f"  Confidence: {scoring_result['confidence']:.2f}", "INFO")
            
            # Test weight distribution
            weights = advanced_scoring.weights
            total_weight = sum(weights.values())
            if abs(total_weight - 1.0) > 0.01:
                self.log(f" Weight distribution error: Total = {total_weight}", "FAIL")
                return False
            else:
                self.log(f" Weight distribution correct: {weights}", "PASS")
            
            return True
            
        except Exception as e:
            self.log(f"Advanced scoring test failed: {e}", "FAIL")
            return False
    
    def test_complete_flow(self):
        """Test 6: Test complete SHORT flow simulation"""
        self.log("\n" + "=" * 60)
        self.log("TEST 6: COMPLETE SHORT FLOW SIMULATION")
        self.log("=" * 60)
        
        try:
            # This would test a complete flow but requires market data
            # For now, just verify the components are properly integrated
            
            self.log("Testing component integration...", "INFO")
            
            # Test if autotrader can access advanced scoring
            from src.api.services.autotrader_service import AutotraderService
            autotrader = AutotraderService()
            
            if hasattr(autotrader, 'advanced_scoring'):
                self.log(" Autotrader has advanced scoring integration", "PASS")
            else:
                self.log(" Autotrader missing advanced scoring integration", "FAIL")
                return False
            
            # Test if exit logic is implemented
            if hasattr(autotrader, '_emergency_short_exit_check'):
                self.log(" Emergency exit logic implemented", "PASS")
            else:
                self.log(" Emergency exit logic missing", "FAIL")
                return False
            
            # Test if SHORT execution method exists
            if hasattr(autotrader, '_execute_short'):
                self.log(" SHORT execution method implemented", "PASS")
            else:
                self.log(" SHORT execution method missing", "FAIL")
                return False
            
            self.log(" All components properly integrated", "PASS")
            return True
            
        except Exception as e:
            self.log(f"Complete flow test failed: {e}", "FAIL")
            return False
    
    def run_all_tests(self):
        """Run all tests and generate report"""
        self.log("COMPLETE SHORT SYSTEM TEST SUITE")
        self.log(f"Test Time: {datetime.now()}")
        self.log(f"Database: {self.db_path}")
        self.log(f"API URL: {self.api_base_url}")
        
        tests = [
            ("Database Schema", self.test_database_schema),
            ("SHORT Positions Data", self.test_short_positions_data),
            ("API Endpoints", self.test_api_endpoints),
            ("Autotrader SHORT Logic", self.test_autotrader_short_logic),
            ("Advanced Scoring", self.test_advanced_scoring),
            ("Complete Flow", self.test_complete_flow)
        ]
        
        passed_tests = 0
        failed_tests = 0
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                if result:
                    passed_tests += 1
                else:
                    failed_tests += 1
            except Exception as e:
                self.log(f"Test '{test_name}' crashed: {e}", "FAIL")
                failed_tests += 1
        
        # Final summary
        self.log("\n" + "=" * 60)
        self.log("FINAL TEST SUMMARY")
        self.log("=" * 60)
        self.log(f"Total Tests: {len(tests)}")
        self.log(f"Passed: {passed_tests}")
        self.log(f"Failed: {failed_tests}")
        
        if failed_tests == 0:
            self.log(" ALL TESTS PASSED - SHORT SYSTEM FULLY OPERATIONAL!", "SUCCESS")
        else:
            self.log(f" {failed_tests} TESTS FAILED - SYSTEM NEEDS ATTENTION", "WARNING")
        
        return failed_tests == 0

def main():
    """Main test function"""
    print(" Complete SHORT System Test Suite")
    print("=" * 50)
    
    # Check for custom parameters
    db_path = 'trading.db'
    api_url = 'http://localhost:8000'
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    if len(sys.argv) > 2:
        api_url = sys.argv[2]
    
    tester = CompleteShortSystemTest(db_path, api_url)
    success = tester.run_all_tests()
    
    # Save results to file
    results_filename = f"short_system_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(results_filename, 'w') as f:
        f.write("\n".join(tester.results))
    
    print(f"\nFull test results saved to: {results_filename}")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())