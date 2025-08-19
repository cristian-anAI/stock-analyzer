#!/usr/bin/env python3
"""
PORTFOLIO DIAGNOSTIC SCRIPT
Comprehensive analysis of portfolio inconsistencies between dashboard and autotrader

This script checks:
1. Database state and positions
2. Portfolio manager memory state
3. Dashboard endpoints consistency
4. Autotrader logs and execution history
"""

import sqlite3
import requests
import json
from datetime import datetime
from typing import Dict, List, Any
import sys
import os

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

class PortfolioDiagnostic:
    def __init__(self, db_path='trading.db', api_base_url='http://localhost:8000'):
        self.db_path = db_path
        self.api_base_url = api_base_url
        self.report = []
        
    def log(self, message: str, level: str = "INFO"):
        """Add message to diagnostic report"""
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
                self.log(f"API request failed {endpoint}: {response.status_code} - {response.text}", "ERROR")
                return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            self.log(f"API request error {endpoint}: {e}", "ERROR")
            return {"error": str(e)}
    
    def check_database_state(self):
        """1. Check database state and positions"""
        self.log("="*60)
        self.log("1. DATABASE STATE ANALYSIS")
        self.log("="*60)
        
        # Check if database exists
        if not os.path.exists(self.db_path):
            self.log(f"Database file {self.db_path} does not exist!", "ERROR")
            return
        
        # List all tables
        tables = self.execute_query("SELECT name FROM sqlite_master WHERE type='table'")
        self.log(f"Available tables: {[t['name'] for t in tables]}")
        
        # Check positions table
        positions = self.execute_query("SELECT * FROM positions")
        self.log(f"\nPOSITIONS TABLE ({len(positions)} total):")
        
        if positions:
            # Group by source
            autotrader_positions = [p for p in positions if p.get('source') == 'autotrader']
            manual_positions = [p for p in positions if p.get('source') == 'manual']
            
            self.log(f"  Autotrader positions: {len(autotrader_positions)}")
            self.log(f"  Manual positions: {len(manual_positions)}")
            
            # Show detailed position info
            for pos in positions:
                side = pos.get('position_side', 'UNKNOWN')
                asset_type = pos.get('type') or pos.get('asset_type', 'UNKNOWN')
                pnl = pos.get('pnl', 0) or 0
                self.log(f"    {pos['symbol']} | {pos['source']} | {side} | {asset_type} | PnL: ${pnl:.2f}")
        else:
            self.log("  No positions found in database")
        
        # Check portfolio_state table
        portfolio_state = self.execute_query("SELECT * FROM portfolio_state ORDER BY created_at DESC LIMIT 1")
        if portfolio_state:
            state = portfolio_state[0]
            self.log(f"\nPORTFOLIO_STATE (latest):")
            self.log(f"  Date: {state.get('date')}")
            self.log(f"  Stocks - Liquid: ${state.get('liquid_capital_stocks', 0):.2f}, Invested: ${state.get('invested_capital_stocks', 0):.2f}")
            self.log(f"  Crypto - Liquid: ${state.get('liquid_capital_crypto', 0):.2f}, Invested: ${state.get('invested_capital_crypto', 0):.2f}")
            self.log(f"  Total PnL - Stocks: ${state.get('total_pnl_stocks', 0):.2f}, Crypto: ${state.get('total_pnl_crypto', 0):.2f}")
        else:
            self.log("\nPORTFOLIO_STATE: No entries found")
        
        # Check portfolio_config table
        portfolio_config = self.execute_query("SELECT * FROM portfolio_config")
        if portfolio_config:
            self.log(f"\nPORTFOLIO_CONFIG:")
            for config in portfolio_config:
                self.log(f"  {config['type']}: Initial=${config['initial_capital']:.2f}, Current=${config['current_capital']:.2f}, Available=${config['available_cash']:.2f}")
        else:
            self.log("\nPORTFOLIO_CONFIG: No configuration found")
        
        # Check autotrader transactions
        transactions = self.execute_query("SELECT * FROM autotrader_transactions ORDER BY timestamp DESC LIMIT 10")
        if transactions:
            self.log(f"\nRECENT AUTOTRADER TRANSACTIONS ({len(transactions)} shown):")
            for tx in transactions:
                self.log(f"  {tx['timestamp']} | {tx['symbol']} | {tx['action']} | {tx['quantity']} @ ${tx['price']:.2f}")
        else:
            self.log("\nAUTOTRADER_TRANSACTIONS: No transactions found")
        
        # Check portfolio transactions
        portfolio_transactions = self.execute_query("SELECT * FROM portfolio_transactions ORDER BY timestamp DESC LIMIT 10")
        if portfolio_transactions:
            self.log(f"\nRECENT PORTFOLIO TRANSACTIONS ({len(portfolio_transactions)} shown):")
            for tx in portfolio_transactions:
                portfolio_type = tx.get('portfolio_type', 'unknown')
                self.log(f"  {tx['timestamp']} | {portfolio_type} | {tx['symbol']} | {tx['action']} | {tx['quantity']} @ ${tx['price']:.2f}")
        else:
            self.log("\nPORTFOLIO_TRANSACTIONS: No transactions found")
    
    def check_api_endpoints(self):
        """2. Check API endpoints consistency"""
        self.log("\n" + "="*60)
        self.log("2. API ENDPOINTS ANALYSIS")
        self.log("="*60)
        
        # Test health endpoint
        health = self.api_request("/health")
        self.log(f"Health status: {health}")
        
        # Test portfolio summary
        portfolio_summary = self.api_request("/api/v1/portfolio/summary")
        self.log(f"\nPortfolio Summary: {json.dumps(portfolio_summary, indent=2)}")
        
        # Test autotrader positions
        autotrader_positions = self.api_request("/api/v1/positions/autotrader")
        self.log(f"\nAutotrader Positions: {json.dumps(autotrader_positions, indent=2)}")
        
        # Test manual positions  
        manual_positions = self.api_request("/api/v1/positions/manual")
        self.log(f"\nManual Positions: {json.dumps(manual_positions, indent=2)}")
        
        # Test portfolio overview
        portfolio_overview = self.api_request("/api/v1/portfolio/overview")
        self.log(f"\nPortfolio Overview: {json.dumps(portfolio_overview, indent=2)}")
        
        # Test portfolio transactions
        portfolio_transactions = self.api_request("/api/v1/portfolio/transactions")
        self.log(f"\nPortfolio Transactions: {json.dumps(portfolio_transactions, indent=2)}")
        
        # Test autotrader summary
        autotrader_summary = self.api_request("/api/v1/autotrader/summary")
        self.log(f"\nAutotrader Summary: {json.dumps(autotrader_summary, indent=2)}")
    
    def check_portfolio_manager_state(self):
        """3. Check portfolio manager memory state via API"""
        self.log("\n" + "="*60)
        self.log("3. PORTFOLIO MANAGER MEMORY STATE")
        self.log("="*60)
        
        # Try to get detailed autotrader state
        autotrader_status = self.api_request("/api/v1/autotrader/status")
        if "error" not in autotrader_status:
            self.log(f"Autotrader Status: {json.dumps(autotrader_status, indent=2)}")
        else:
            self.log(f"Could not get autotrader status: {autotrader_status}")
        
        # Check if there's a debug endpoint
        debug_info = self.api_request("/api/v1/debug/portfolio")
        if "error" not in debug_info:
            self.log(f"Debug Portfolio Info: {json.dumps(debug_info, indent=2)}")
        else:
            self.log("No debug endpoint available")
    
    def analyze_inconsistencies(self):
        """4. Analyze and report inconsistencies"""
        self.log("\n" + "="*60)
        self.log("4. INCONSISTENCY ANALYSIS")
        self.log("="*60)
        
        # Get data from database
        db_positions = self.execute_query("SELECT * FROM positions")
        db_autotrader = [p for p in db_positions if p.get('source') == 'autotrader']
        
        # Get data from API
        api_autotrader = self.api_request("/api/v1/positions/autotrader")
        api_portfolio = self.api_request("/api/v1/portfolio/summary")
        
        self.log(f"Database autotrader positions: {len(db_autotrader)}")
        
        if "error" not in api_autotrader:
            if isinstance(api_autotrader, list):
                self.log(f"API autotrader positions: {len(api_autotrader)}")
            else:
                self.log(f"API autotrader response: {api_autotrader}")
        else:
            self.log(f"API autotrader error: {api_autotrader}")
        
        if "error" not in api_portfolio:
            self.log(f"API portfolio summary: {json.dumps(api_portfolio, indent=2)}")
        else:
            self.log(f"API portfolio error: {api_portfolio}")
        
        # Compare symbols
        if db_autotrader and "error" not in api_autotrader and isinstance(api_autotrader, list):
            db_symbols = set(pos['symbol'] for pos in db_autotrader)
            api_symbols = set(pos['symbol'] for pos in api_autotrader if 'symbol' in pos)
            
            self.log(f"\nSymbol comparison:")
            self.log(f"  DB symbols: {sorted(db_symbols)}")
            self.log(f"  API symbols: {sorted(api_symbols)}")
            
            missing_in_api = db_symbols - api_symbols
            missing_in_db = api_symbols - db_symbols
            
            if missing_in_api:
                self.log(f"  Missing in API: {missing_in_api}", "WARNING")
            if missing_in_db:
                self.log(f"  Missing in DB: {missing_in_db}", "WARNING")
            if not missing_in_api and not missing_in_db:
                self.log(f"  Symbols match perfectly")
    
    def generate_full_report(self):
        """Generate complete diagnostic report"""
        self.log("PORTFOLIO DIAGNOSTIC REPORT")
        self.log(f"Timestamp: {datetime.now()}")
        self.log(f"Database: {self.db_path}")
        self.log(f"API Base URL: {self.api_base_url}")
        
        self.check_database_state()
        self.check_api_endpoints()
        self.check_portfolio_manager_state()
        self.analyze_inconsistencies()
        
        self.log("\n" + "="*60)
        self.log("DIAGNOSTIC COMPLETE")
        self.log("="*60)
        
        return "\n".join(self.report)

def main():
    """Main diagnostic function"""
    print("Starting Portfolio Diagnostic...")
    
    # Check for custom parameters
    db_path = 'trading.db'
    api_url = 'http://localhost:8000'
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    if len(sys.argv) > 2:
        api_url = sys.argv[2]
    
    diagnostic = PortfolioDiagnostic(db_path, api_url)
    report = diagnostic.generate_full_report()
    
    # Save report to file
    report_filename = f"portfolio_diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_filename, 'w') as f:
        f.write(report)
    
    print(f"\nFull report saved to: {report_filename}")

if __name__ == "__main__":
    main()