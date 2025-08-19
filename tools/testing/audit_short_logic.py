#!/usr/bin/env python3
"""
SHORT LOGIC AUDIT SCRIPT
Comprehensive analysis of SHORT position logic in autotrader

This script audits:
1. SHORT signal criteria and thresholds
2. Score calculation logic
3. P&L calculation for SHORT positions
4. Exit logic and risk management
5. Current position analysis
"""

import sqlite3
import requests
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

class ShortLogicAudit:
    def __init__(self, db_path='trading.db', api_base_url='http://localhost:8000'):
        self.db_path = db_path
        self.api_base_url = api_base_url
        self.report = []
        
    def log(self, message: str, level: str = "INFO"):
        """Add message to audit report"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {level}: {message}"
        self.report.append(entry)
        print(entry)
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute database query safely"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            self.log(f"Database query error: {e}", "ERROR")
            return []
    
    def api_request(self, endpoint: str) -> Dict:
        """Make API request safely"""
        try:
            url = f"{self.api_base_url}{endpoint}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                self.log(f"API request failed {endpoint}: {response.status_code}", "ERROR")
                return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            self.log(f"API request error {endpoint}: {e}", "ERROR")
            return {"error": str(e)}
    
    def audit_short_criteria(self):
        """1. Audit SHORT signal criteria"""
        self.log("="*60)
        self.log("1. SHORT SIGNAL CRITERIA ANALYSIS")
        self.log("="*60)
        
        # From code analysis
        self.log("SHORT SIGNAL THRESHOLDS:")
        self.log("  CRYPTO SHORT: score < 3.5")
        self.log("    - Confidence: min(90, (4 - score) * 20)")
        self.log("    - Reasons: 'Low score', 'Bearish technical signals'")
        self.log("")
        self.log("  STOCK SHORT: score < 2.5")
        self.log("    - Confidence: min(85, (3 - score) * 25)")
        self.log("    - Reasons: 'Very low score', 'Strong bearish signals'")
        self.log("")
        
        self.log("SCORING LOGIC ANALYSIS:")
        self.log("  Crypto base score: 2.0")
        self.log("  Stock base score: 3.0")
        self.log("")
        self.log("  Crypto penalties that lead to LOW scores:")
        self.log("    - Recent pump >5%: -3 points")
        self.log("    - Recent pump >2%: -1.5 points")
        self.log("    - RSI >70: -2 points")
        self.log("    - Low volume <10M: -1.5 points")
        self.log("    - Small market cap <1B: -1 point")
        self.log("")
        self.log("  RESULT: Crypto needs MULTIPLE negative factors to hit <3.5")
        self.log("  ANALYSIS: This is AGGRESSIVE - could be triggered by:")
        self.log("    - Recent pump + overbought RSI + low volume")
        self.log("    - Any recent gains >2% + any other negative factor")
    
    def audit_current_positions(self):
        """2. Audit current SHORT positions"""
        self.log("\n" + "="*60)
        self.log("2. CURRENT SHORT POSITIONS ANALYSIS")
        self.log("="*60)
        
        # Get current SHORT positions
        short_positions = self.execute_query("""
            SELECT symbol, entry_price, current_price, quantity, pnl, pnl_percent, created_at
            FROM positions 
            WHERE position_side = 'SHORT'
            ORDER BY created_at DESC
        """)
        
        if not short_positions:
            self.log("No SHORT positions found in database")
            return
        
        self.log(f"Found {len(short_positions)} SHORT positions:")
        self.log("")
        
        total_pnl = 0
        for pos in short_positions:
            symbol = pos['symbol']
            entry = pos['entry_price']
            current = pos['current_price'] or 0
            quantity = pos['quantity']
            pnl = pos['pnl'] or 0
            pnl_pct = pos['pnl_percent'] or 0
            created = pos['created_at']
            
            # Verify P&L calculation
            expected_pnl = (entry - current) * quantity
            pnl_diff = abs(expected_pnl - pnl)
            
            self.log(f"  {symbol}:")
            self.log(f"    Entry: ${entry:.4f}, Current: ${current:.4f}")
            self.log(f"    Quantity: {quantity:.2f}")
            self.log(f"    P&L: ${pnl:.2f} ({pnl_pct:.2f}%)")
            self.log(f"    Created: {created}")
            
            if pnl_diff > 0.01:  # More than 1 cent difference
                self.log(f"    WARNING: P&L CALCULATION ERROR: Expected ${expected_pnl:.2f}, Got ${pnl:.2f}", "WARNING")
            else:
                self.log(f"    P&L calculation correct")
            
            # Price movement analysis
            price_change_pct = ((current - entry) / entry) * 100 if entry > 0 else 0
            if price_change_pct > 0:
                self.log(f"    Price moved UP {price_change_pct:.2f}% (BAD for SHORT)")
            else:
                self.log(f"    Price moved DOWN {abs(price_change_pct):.2f}% (GOOD for SHORT)")
            
            total_pnl += pnl
            self.log("")
        
        self.log(f"TOTAL SHORT P&L: ${total_pnl:.2f}")
        
        # Get current scores for these symbols
        self.log("\nCURRENT SCORES FOR SHORT POSITIONS:")
        try:
            cryptos_response = self.api_request("/api/v1/cryptos?sort=score")
            if "error" not in cryptos_response:
                crypto_scores = {crypto['symbol']: crypto['score'] for crypto in cryptos_response}
                
                for pos in short_positions:
                    symbol = pos['symbol']
                    current_score = crypto_scores.get(symbol, "N/A")
                    self.log(f"  {symbol}: Score = {current_score}")
                    
                    if isinstance(current_score, (int, float)):
                        if current_score >= 3.5:
                            self.log(f"    WARNING: Score {current_score} >= 3.5 - Should consider CLOSING SHORT", "WARNING")
                        else:
                            self.log(f"    Score {current_score} < 3.5 - SHORT signal still valid")
        except Exception as e:
            self.log(f"Could not fetch current scores: {e}", "ERROR")
    
    def audit_pnl_calculation(self):
        """3. Audit P&L calculation logic"""
        self.log("\n" + "="*60)
        self.log("3. P&L CALCULATION LOGIC AUDIT")
        self.log("="*60)
        
        self.log("SHORT P&L FORMULA:")
        self.log("  P&L = (entry_price - current_price) * quantity")
        self.log("  Profit when: current_price < entry_price")
        self.log("  Loss when: current_price > entry_price")
        self.log("")
        
        # Test with examples
        test_cases = [
            {"entry": 100, "current": 90, "quantity": 10, "expected_pnl": 100},
            {"entry": 100, "current": 110, "quantity": 10, "expected_pnl": -100},
            {"entry": 3.50, "current": 3.40, "quantity": 1000, "expected_pnl": 100},
        ]
        
        self.log("TEST CASES:")
        for i, case in enumerate(test_cases):
            entry = case["entry"]
            current = case["current"]
            quantity = case["quantity"]
            expected = case["expected_pnl"]
            calculated = (entry - current) * quantity
            
            self.log(f"  Test {i+1}: Entry=${entry}, Current=${current}, Qty={quantity}")
            self.log(f"    Expected P&L: ${expected}")
            self.log(f"    Calculated P&L: ${calculated}")
            self.log(f"    Result: {'PASS' if abs(calculated - expected) < 0.01 else 'FAIL'}")
            self.log("")
    
    def audit_risk_management(self):
        """4. Audit risk management for SHORT positions"""
        self.log("\n" + "="*60)
        self.log("4. SHORT RISK MANAGEMENT AUDIT")
        self.log("="*60)
        
        self.log("RISK MANAGEMENT CONCERNS FOR SHORT:")
        self.log("  1. INFINITE LOSS POTENTIAL: Prices can rise indefinitely")
        self.log("  2. VOLATILITY RISK: Crypto can spike 50%+ in hours")
        self.log("  3. LIQUIDITY RISK: Need to buy back to close position")
        self.log("")
        
        # Check if there are stop losses
        positions_with_stops = self.execute_query("""
            SELECT symbol, entry_price, stop_loss_updated, take_profit_updated
            FROM positions 
            WHERE position_side = 'SHORT' AND (stop_loss_updated IS NOT NULL OR take_profit_updated IS NOT NULL)
        """)
        
        if positions_with_stops:
            self.log(f"STOP LOSSES FOUND: {len(positions_with_stops)} positions have stops")
            for pos in positions_with_stops:
                self.log(f"  {pos['symbol']}: Stop=${pos['stop_loss_updated']}, TP=${pos['take_profit_updated']}")
        else:
            self.log("WARNING: NO STOP LOSSES FOUND - HIGH RISK!", "WARNING")
            self.log("  SHORT positions without stops can cause unlimited losses")
        
        # Check position sizes
        self.log("\nPOSITION SIZE ANALYSIS:")
        short_positions = self.execute_query("""
            SELECT symbol, quantity, entry_price, (quantity * entry_price) as position_value
            FROM positions 
            WHERE position_side = 'SHORT'
        """)
        
        total_short_exposure = sum(pos['position_value'] for pos in short_positions)
        self.log(f"  Total SHORT exposure: ${total_short_exposure:.2f}")
        
        # Get available crypto capital
        try:
            portfolio_summary = self.api_request("/api/v1/portfolio/summary")
            if "error" not in portfolio_summary and "data" in portfolio_summary:
                crypto_data = portfolio_summary["data"].get("crypto", {})
                liquid_capital = crypto_data.get("liquid_capital", 0)
                self.log(f"  Available crypto capital: ${liquid_capital:.2f}")
                
                if total_short_exposure > liquid_capital:
                    self.log(f"  WARNING: SHORT exposure (${total_short_exposure:.2f}) > Available capital (${liquid_capital:.2f})", "WARNING")
                else:
                    self.log(f"  SHORT exposure within available capital")
        except Exception as e:
            self.log(f"Could not check capital limits: {e}", "ERROR")
    
    def audit_exit_logic(self):
        """5. Audit exit logic for SHORT positions"""
        self.log("\n" + "="*60)
        self.log("5. SHORT EXIT LOGIC AUDIT")
        self.log("="*60)
        
        self.log("EXIT CRITERIA ANALYSIS:")
        self.log("  Looking for exit logic in autotrader...")
        
        # Check recent transactions for SHORT exits
        recent_exits = self.execute_query("""
            SELECT symbol, action, quantity, price, reason, timestamp
            FROM autotrader_transactions 
            WHERE action = 'sell' AND symbol IN (
                SELECT DISTINCT symbol FROM positions WHERE position_side = 'SHORT'
            )
            ORDER BY timestamp DESC
            LIMIT 10
        """)
        
        if recent_exits:
            self.log(f"RECENT SHORT EXITS: {len(recent_exits)} found")
            for exit in recent_exits:
                self.log(f"  {exit['timestamp']}: {exit['symbol']} SELL {exit['quantity']:.2f} @ ${exit['price']:.4f}")
                self.log(f"    Reason: {exit['reason']}")
        else:
            self.log("WARNING: NO RECENT SHORT EXITS FOUND", "WARNING")
            self.log("  This suggests SHORT positions may not have exit logic")
        
        self.log("\nEXIT LOGIC REQUIREMENTS FOR SHORT:")
        self.log("  1. Score improvement: If score rises above SHORT threshold")
        self.log("  2. Stop loss: Price rises beyond acceptable loss")
        self.log("  3. Take profit: Price falls to target profit level")
        self.log("  4. Time-based: Maximum holding period for SHORT")
    
    def generate_recommendations(self):
        """6. Generate recommendations"""
        self.log("\n" + "="*60)
        self.log("6. RECOMMENDATIONS")
        self.log("="*60)
        
        self.log("CRITICAL ISSUES IDENTIFIED:")
        self.log("  1. AGGRESSIVE SHORT THRESHOLDS")
        self.log("     - Crypto SHORT at score <3.5 may be too sensitive")
        self.log("     - Any recent gain >2% can trigger SHORT signal")
        self.log("")
        
        self.log("  2. MISSING RISK MANAGEMENT")
        self.log("     - No apparent stop losses for SHORT positions")
        self.log("     - SHORT positions have unlimited loss potential")
        self.log("")
        
        self.log("  3. UNCLEAR EXIT STRATEGY")
        self.log("     - Need clear exit criteria for SHORT positions")
        self.log("     - Should exit when score improves or reaches stop loss")
        self.log("")
        
        self.log("RECOMMENDED FIXES:")
        self.log("  1. TIGHTEN SHORT CRITERIA:")
        self.log("     - Crypto: score <2.5 (instead of 3.5)")
        self.log("     - Require multiple bearish indicators")
        self.log("     - Add momentum confirmation")
        self.log("")
        
        self.log("  2. ADD STOP LOSSES:")
        self.log("     - Automatic stop loss at +15% price move")
        self.log("     - Take profit at -10% price move")
        self.log("     - Maximum holding period: 7 days")
        self.log("")
        
        self.log("  3. IMPROVE EXIT LOGIC:")
        self.log("     - Exit when score rises above 4.0")
        self.log("     - Exit on any strong bullish reversal signal")
        self.log("     - Regular position review every 24 hours")
    
    def generate_full_audit(self):
        """Generate complete SHORT logic audit"""
        self.log("SHORT LOGIC AUDIT REPORT")
        self.log(f"Timestamp: {datetime.now()}")
        self.log(f"Database: {self.db_path}")
        self.log(f"API Base URL: {self.api_base_url}")
        
        self.audit_short_criteria()
        self.audit_current_positions()
        self.audit_pnl_calculation()
        self.audit_risk_management()
        self.audit_exit_logic()
        self.generate_recommendations()
        
        self.log("\n" + "="*60)
        self.log("AUDIT COMPLETE")
        self.log("="*60)
        
        return "\n".join(self.report)

def main():
    """Main audit function"""
    print("Starting SHORT Logic Audit...")
    
    # Check for custom parameters
    db_path = 'trading.db'
    api_url = 'http://localhost:8000'
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    if len(sys.argv) > 2:
        api_url = sys.argv[2]
    
    audit = ShortLogicAudit(db_path, api_url)
    report = audit.generate_full_audit()
    
    # Save report to file
    report_filename = f"short_logic_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_filename, 'w') as f:
        f.write(report)
    
    print(f"\nFull audit report saved to: {report_filename}")

if __name__ == "__main__":
    main()