#!/usr/bin/env python3
"""
SHORT POSITIONS DASHBOARD
Real-time monitoring dashboard for SHORT positions with risk analysis
"""

import requests
import json
import time
import sys
import os
from datetime import datetime
from typing import Dict, List, Any

class ShortDashboard:
    def __init__(self, api_base_url='http://localhost:8000'):
        self.api_base_url = api_base_url
        
    def get_data(self, endpoint: str) -> Dict:
        """Get data from API endpoint"""
        try:
            url = f"{self.api_base_url}{endpoint}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def clear_screen(self):
        """Clear the console screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def display_header(self):
        """Display dashboard header"""
        print("=" * 80)
        print("SHORT POSITIONS MONITORING DASHBOARD")
        print(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print()
    
    def display_short_positions(self):
        """Display current SHORT positions"""
        print("CURRENT SHORT POSITIONS:")
        print("-" * 80)
        
        data = self.get_data("/api/v1/short-positions")
        if "error" in data:
            print(f"Error: {data['error']}")
            return
        
        positions = data.get("short_positions", [])
        summary = data.get("summary", {})
        
        if not positions:
            print("No SHORT positions currently open")
            return
        
        # Display summary
        print(f"Total Positions: {summary.get('total_positions', 0)}")
        print(f"Total P&L: ${summary.get('total_pnl', 0):.2f}")
        print(f"Average P&L: {summary.get('avg_pnl_percent', 0):.2f}%")
        print(f"High Risk Positions: {summary.get('high_risk_positions', 0)}")
        print(f"Positions to Exit: {summary.get('positions_to_exit', 0)}")
        print()
        
        # Display positions table
        print(f"{'Symbol':<12} {'Entry':<8} {'Current':<8} {'P&L $':<10} {'P&L %':<8} {'Risk':<8} {'Days':<5} {'Action'}")
        print("-" * 80)
        
        for pos in positions:
            symbol = pos['symbol'][:10]
            entry = f"${pos['entry_price']:.4f}"
            current = f"${pos['current_price'] or 0:.4f}"
            pnl_dollar = f"${pos['pnl'] or 0:.2f}"
            pnl_percent = f"{pos['pnl_percent'] or 0:.2f}%"
            risk = pos['risk_level']
            days = pos['days_held']
            action = "EXIT!" if pos['should_exit'] else "HOLD"
            
            # Color coding for risk
            risk_color = ""
            if risk == "HIGH":
                risk_color = "[HIGH]"
            elif risk == "MEDIUM":
                risk_color = ""
            else:
                risk_color = ""
            
            action_icon = "[!]" if action == "EXIT!" else "[OK]"
            
            print(f"{symbol:<12} {entry:<8} {current:<8} {pnl_dollar:<10} {pnl_percent:<8} {risk_color}{risk:<7} {days:<5} {action_icon}{action}")
        
        print()
    
    def display_alerts(self):
        """Display critical alerts"""
        print("ALERTS & WARNINGS:")
        print("-" * 80)
        
        data = self.get_data("/api/v1/short-alerts")
        if "error" in data:
            print(f"Error: {data['error']}")
            return
        
        alerts = data.get("alerts", [])
        critical_count = data.get("critical_count", 0)
        
        if not alerts:
            print("No alerts - All SHORT positions are within normal parameters")
            return
        
        print(f"Total Alerts: {len(alerts)} | Critical: {critical_count}")
        print()
        
        for alert in alerts:
            severity = alert['severity']
            symbol = alert['symbol']
            message = alert['message']
            action = alert['action']
            
            # Icon based on severity
            if severity == "CRITICAL":
                icon = "[CRIT]"
            elif severity == "HIGH":
                icon = "[HIGH]"
            elif severity == "MEDIUM":
                icon = "[WARN]"
            else:
                icon = "[INFO]"
            
            print(f"{icon} {severity} | {symbol}: {message}")
            print(f"   Recommended Action: {action}")
            print()
    
    def display_performance(self):
        """Display SHORT trading performance"""
        print("SHORT TRADING PERFORMANCE:")
        print("-" * 80)
        
        data = self.get_data("/api/v1/short-performance")
        if "error" in data:
            print(f"Error: {data['error']}")
            return
        
        perf = data.get("performance_summary", {})
        cycles = data.get("cycle_analysis", [])
        
        print(f"Completed Trades: {perf.get('completed_cycles', 0)}")
        print(f"Total Profit: ${perf.get('total_profit', 0):.2f}")
        print(f"Win Rate: {perf.get('win_rate_percent', 0):.1f}%")
        print(f"Winning Trades: {perf.get('winning_trades', 0)}")
        print(f"Losing Trades: {perf.get('losing_trades', 0)}")
        print(f"Avg Profit/Trade: ${perf.get('avg_profit_per_trade', 0):.2f}")
        print(f"Current Open SHORTs: {perf.get('current_open_shorts', 0)}")
        print()
        
        if cycles:
            print("Recent Completed SHORT Cycles:")
            print(f"{'Symbol':<10} {'Entry':<8} {'Exit':<8} {'P&L $':<10} {'P&L %':<8} {'Reason'}")
            print("-" * 70)
            
            for cycle in cycles[-5:]:  # Last 5 cycles
                symbol = cycle['symbol'][:8]
                entry = f"${cycle['entry_price']:.4f}"
                exit_price = f"${cycle['exit_price']:.4f}"
                pnl = f"${cycle['pnl']:.2f}"
                pnl_pct = f"{cycle['pnl_percent']:.2f}%"
                reason = cycle['exit_reason'][:20]
                
                print(f"{symbol:<10} {entry:<8} {exit_price:<8} {pnl:<10} {pnl_pct:<8} {reason}")
        
        print()
    
    def display_controls(self):
        """Display dashboard controls"""
        print("DASHBOARD CONTROLS:")
        print("-" * 80)
        print("Press 'r' + Enter to refresh")
        print("Press 'e' + Enter for emergency exit all SHORTs")
        print("Press 'q' + Enter to quit")
        print("Or just wait 30 seconds for auto-refresh...")
        print()
    
    def run_dashboard(self):
        """Run the interactive dashboard"""
        print("Starting SHORT Positions Dashboard...")
        print("Checking API connection...")
        
        # Test connection
        health = self.get_data("/api/v1/health")
        if "error" in health:
            print(f"Cannot connect to API: {health['error']}")
            print("Make sure the API server is running on http://localhost:8000")
            return
        
        print("Connected to API successfully!")
        time.sleep(2)
        
        while True:
            try:
                self.clear_screen()
                self.display_header()
                self.display_short_positions()
                self.display_alerts()
                self.display_performance()
                self.display_controls()
                
                # Wait for user input or auto-refresh
                import select
                import sys
                
                # Simple input handling (works on Windows and Unix)
                print("Waiting for input (30s timeout)...")
                
                try:
                    # For Windows
                    if os.name == 'nt':
                        import msvcrt
                        start_time = time.time()
                        while time.time() - start_time < 30:
                            if msvcrt.kbhit():
                                key = msvcrt.getch().decode('utf-8').lower()
                                if key == 'q':
                                    print("Exiting dashboard...")
                                    return
                                elif key == 'r':
                                    print("Refreshing...")
                                    break
                                elif key == 'e':
                                    self.emergency_exit()
                                    input("Press Enter to continue...")
                                    break
                            time.sleep(0.1)
                    else:
                        # For Unix/Linux (simplified - just auto-refresh)
                        time.sleep(30)
                except:
                    # Fallback: just auto-refresh
                    time.sleep(30)
                    
            except KeyboardInterrupt:
                print("\nExiting dashboard...")
                return
            except Exception as e:
                print(f"Dashboard error: {e}")
                time.sleep(5)
    
    def emergency_exit(self):
        """Execute emergency exit for all SHORTs"""
        print("\n EMERGENCY EXIT INITIATED")
        print("This will close ALL SHORT positions immediately!")
        
        confirm = input("Type 'YES' to confirm emergency exit: ")
        if confirm.upper() != 'YES':
            print("Emergency exit cancelled.")
            return
        
        print("Executing emergency exit...")
        
        try:
            response = requests.post(f"{self.api_base_url}/api/v1/short-emergency-exit", timeout=30)
            if response.status_code == 200:
                result = response.json()
                print(f"Emergency exit completed!")
                print(f"Positions closed: {result.get('positions_closed', 0)}")
                
                for pos in result.get('closed_positions', []):
                    print(f"  - {pos['symbol']}: P&L ${pos['pnl']:.2f}")
            else:
                print(f"Emergency exit failed: HTTP {response.status_code}")
        except Exception as e:
            print(f"Emergency exit error: {e}")

def main():
    """Main function"""
    print("SHORT Positions Dashboard")
    print("=" * 40)
    
    # Check for custom API URL
    api_url = 'http://localhost:8000'
    if len(sys.argv) > 1:
        api_url = sys.argv[1]
    
    dashboard = ShortDashboard(api_url)
    dashboard.run_dashboard()

if __name__ == "__main__":
    main()