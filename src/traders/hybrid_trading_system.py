#!/usr/bin/env python3
"""
Hybrid Trading System - Stocks + Crypto
Sistema principal que analiza tanto acciones como criptomonedas
"""

import time
from datetime import datetime
import importlib.util

# Import existing modules
def import_data_collector():
    spec = importlib.util.spec_from_file_location("data_collector", "data-collector.py")
    data_collector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(data_collector)
    return data_collector

data_collector = import_data_collector()
from position_manager import PositionManager
from crypto_data_collector import CryptoDataCollector
from unified_trader import UnifiedTrader
from crypto_dashboard import CryptoDashboard

class HybridTradingSystem:
    def __init__(self):
        print(" INITIALIZING HYBRID TRADING SYSTEM")
        print("=" * 60)
        # Initialize collectors
        self.stock_collector = data_collector.StockDataCollector()
        self.crypto_collector = CryptoDataCollector()
        self.position_manager = PositionManager(self.stock_collector)
        # Initialize unified trader
        self.unified_trader = UnifiedTrader(
            stock_collector=self.stock_collector,
            crypto_collector=self.crypto_collector,
            position_manager=self.position_manager,
            max_stock_positions=5,
            max_crypto_positions=3,
            max_investment_per_stock=3000,
            max_investment_per_crypto=1000
        )
        # Initialize crypto dashboard
        self.crypto_dashboard = CryptoDashboard(self.position_manager)
        print(" Stock Collector: Ready")
        print(" Crypto Collector: Ready") 
        print(" Position Manager: Ready")
        print(" Unified Trader: Ready")
    def run_market_analysis(self):
        """Run complete market analysis - both stocks and crypto"""
        print(f"\n MARKET ANALYSIS - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 60)
        try:
            # Run unified analysis
            opportunities = self.unified_trader.run_cycle()
            # Display stock opportunities
            stock_opps = opportunities.get('stock_opportunities', [])
            print(f"\n STOCK OPPORTUNITIES: {len(stock_opps)}")
            for opp in stock_opps:
                print(f"  {opp['symbol']:6} | Score: {opp['score']} | {', '.join(opp['reasons'][:2])}")
            # Display crypto opportunities  
            crypto_opps = opportunities.get('crypto_opportunities', [])
            print(f"\n CRYPTO OPPORTUNITIES: {len(crypto_opps)}")
            for opp in crypto_opps:
                print(f"  {opp['symbol']:10} | Score: {opp['score']} | {', '.join(opp['reasons'][:2])}")
            return opportunities
        except Exception as e:
            print(f" Error in market analysis: {e}")
            return {"stock_opportunities": [], "crypto_opportunities": []}
    def show_portfolio_status(self):
        """Show current portfolio status"""
        print(f"\n PORTFOLIO STATUS")
        print("=" * 60)
        # Regular portfolio dashboard
        self.position_manager.print_portfolio_dashboard()
        # Crypto-specific dashboard
        self.crypto_dashboard.show()
    def run_demo_cycle(self):
        """Run one complete demo cycle"""
        print(f"\n DEMO CYCLE STARTING")
        print("=" * 60)
        # 1. Show current portfolio
        self.show_portfolio_status()
        # 2. Run market analysis
        opportunities = self.run_market_analysis()
        # 3. Summary
        total_stock_opps = len(opportunities.get('stock_opportunities', []))
        total_crypto_opps = len(opportunities.get('crypto_opportunities', []))
        print(f"\n SUMMARY:")
        print(f"  Stock opportunities: {total_stock_opps}")
        print(f"  Crypto opportunities: {total_crypto_opps}")
        print(f"  Total signals: {total_stock_opps + total_crypto_opps}")
        return opportunities
    def run_continuous_monitoring(self, cycles=5, interval_minutes=10):
        """Run continuous monitoring for testing"""
        print(f"\n CONTINUOUS MONITORING")
        print(f"Cycles: {cycles} | Interval: {interval_minutes} min")
        print("=" * 60)
        for i in range(cycles):
            print(f"\n CYCLE #{i+1} - {datetime.now().strftime('%H:%M:%S')}")
            opportunities = self.run_demo_cycle()
            # Check if any strong signals (score >= 6)
            strong_signals = []
            for opp in opportunities.get('stock_opportunities', []) + opportunities.get('crypto_opportunities', []):
                if opp['score'] >= 6:
                    strong_signals.append(opp)
            if strong_signals:
                print(f"\n STRONG SIGNALS DETECTED:")
                for signal in strong_signals:
                    print(f"  {signal['symbol']} | Score: {signal['score']} | Action: POTENTIAL BUY")
            if i < cycles - 1:  # Don't sleep on last cycle
                print(f"\n Waiting {interval_minutes} minutes for next cycle...")
                time.sleep(interval_minutes * 60)
        print(f"\n Continuous monitoring completed!")
def main():
    """Main execution"""
    print(" HYBRID TRADING SYSTEM - STOCKS + CRYPTO")
    print("=" * 60)
    try:
        # Initialize system
        system = HybridTradingSystem()
        # Menu
        print(f"\nSelect mode:")
        print("1. Single market analysis")
        print("2. Portfolio status only") 
        print("3. Demo cycle (analysis + portfolio)")
        print("4. Continuous monitoring (5 cycles, 10 min intervals)")
        print("5. Weekend crypto monitoring (24/7 mode)")
        choice = input("\nChoice (1-5): ").strip()
        if choice == "1":
            system.run_market_analysis()
        elif choice == "2":
            system.show_portfolio_status()
        elif choice == "3":
            system.run_demo_cycle()
        elif choice == "4":
            system.run_continuous_monitoring(cycles=5, interval_minutes=10)
        elif choice == "5":
            print(" WEEKEND CRYPTO MODE - Press Ctrl+C to stop")
            system.run_continuous_monitoring(cycles=999, interval_minutes=30)
        else:
            print("Running default demo cycle...")
            system.run_demo_cycle()
    except KeyboardInterrupt:
        print(f"\n\n System stopped by user")
    except Exception as e:
        print(f"\n System error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
