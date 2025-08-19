#!/usr/bin/env python3
"""
OPTIMIZED TRADING STRATEGY - Efficient API Scanning & Risk Management
Maximizes market coverage while preventing API rate limit issues
"""

import time
from datetime import datetime, timedelta
from typing import List, Dict, Set
import random
from expanded_crypto_watchlist import EXPANDED_CRYPTO_WATCHLIST, get_diversified_portfolio, get_symbols_only

class OptimizedScanningStrategy:
    """
    Smart scanning strategy to handle 150+ symbols efficiently:
    1. Batch processing to avoid API limits
    2. Priority-based scanning (positions > opportunities > watchlist)  
    3. Time-based rotation to ensure all symbols get scanned
    4. Rate limiting and backoff strategies
    """
    
    def __init__(self, max_requests_per_minute=60, max_requests_per_hour=1000):
        self.max_rpm = max_requests_per_minute  # Yahoo Finance: ~60 RPM safe
        self.max_rph = max_requests_per_hour    # Yahoo Finance: ~1000 RPH safe
        self.request_count_minute = 0
        self.request_count_hour = 0
        self.last_minute_reset = datetime.now()
        self.last_hour_reset = datetime.now()
        self.scan_history = {}  # Track when each symbol was last scanned
        self.priority_symbols = set()  # High priority symbols (positions, alerts)
        self.backoff_seconds = 0.5  # Base delay between requests
        
    def can_make_request(self) -> bool:
        """Check if we can make an API request without hitting limits"""
        now = datetime.now()
        
        # Reset counters if needed
        if (now - self.last_minute_reset).total_seconds() >= 60:
            self.request_count_minute = 0
            self.last_minute_reset = now
            
        if (now - self.last_hour_reset).total_seconds() >= 3600:
            self.request_count_hour = 0
            self.last_hour_reset = now
            
        return (self.request_count_minute < self.max_rpm and 
                self.request_count_hour < self.max_rph)
    
    def record_request(self):
        """Record that we made an API request"""
        self.request_count_minute += 1
        self.request_count_hour += 1
        time.sleep(self.backoff_seconds)  # Rate limiting delay
    
    def get_scanning_priority(self, symbol: str, current_positions: Set[str]) -> int:
        """
        Calculate scanning priority for a symbol:
        Higher number = higher priority
        """
        priority = 0
        
        # HIGHEST: Current positions (always scan)
        if symbol in current_positions:
            priority += 1000
            
        # HIGH: Manual/large positions
        if symbol in self.priority_symbols:
            priority += 500
            
        # MEDIUM: Recently active symbols
        if symbol in self.scan_history:
            hours_since_scan = (datetime.now() - self.scan_history[symbol]).total_seconds() / 3600
            if hours_since_scan < 1:  # Scanned within 1 hour
                priority += 100
            elif hours_since_scan < 6:  # Scanned within 6 hours  
                priority += 50
                
        # LOW: Crypto gets slight boost (24/7 market)
        if "USD" in symbol and "-" in symbol:  # Crypto pattern
            priority += 25
            
        # LOWEST: Random factor for equal symbols
        priority += random.randint(1, 10)
        
        return priority
    
    def get_optimized_scan_list(self, all_symbols: List[str], current_positions: Set[str], 
                               max_symbols_per_cycle: int = 50) -> List[str]:
        """
        Get optimized list of symbols to scan this cycle
        Balances comprehensive coverage with API limits
        """
        now = datetime.now()
        
        # 1. ALWAYS SCAN: Current positions (highest priority)
        must_scan = list(current_positions)
        
        # 2. PRIORITY SCAN: Symbols that need attention
        priority_scan = []
        for symbol in all_symbols:
            if symbol in current_positions:
                continue  # Already in must_scan
                
            # Skip if scanned very recently (< 30 minutes) unless high priority
            if symbol in self.scan_history:
                minutes_since_scan = (now - self.scan_history[symbol]).total_seconds() / 60
                if minutes_since_scan < 30 and symbol not in self.priority_symbols:
                    continue
                    
            priority = self.get_scanning_priority(symbol, current_positions)
            priority_scan.append((symbol, priority))
        
        # Sort by priority and take top symbols
        priority_scan.sort(key=lambda x: x[1], reverse=True)
        remaining_capacity = max_symbols_per_cycle - len(must_scan)
        priority_symbols = [symbol for symbol, _ in priority_scan[:remaining_capacity]]
        
        final_scan_list = must_scan + priority_symbols
        
        # Update scan history for selected symbols
        for symbol in final_scan_list:
            self.scan_history[symbol] = now
            
        print(f"\nOPTIMIZED SCANNING STRATEGY")
        print(f"   Must scan (positions): {len(must_scan)}")
        print(f"   Priority scan: {len(priority_symbols)}")
        print(f"   Total this cycle: {len(final_scan_list)}")
        print(f"   API capacity: {self.max_rph - self.request_count_hour}/{self.max_rph}/hour")
        
        return final_scan_list
    
    def batch_process_symbols(self, symbols: List[str], batch_size: int = 10):
        """
        Process symbols in batches with intelligent delay
        """
        batches = [symbols[i:i+batch_size] for i in range(0, len(symbols), batch_size)]
        
        for i, batch in enumerate(batches):
            print(f"   Processing batch {i+1}/{len(batches)} ({len(batch)} symbols)")
            
            for symbol in batch:
                if not self.can_make_request():
                    print(f"   Rate limit reached, waiting...")
                    time.sleep(60)  # Wait for minute reset
                    
                # Process symbol here (yield for actual processing)
                yield symbol
                self.record_request()
            
            # Batch delay (longer between batches)
            if i < len(batches) - 1:  # Don't delay after last batch
                batch_delay = min(5.0, len(batch) * 0.2)  # Scale with batch size
                time.sleep(batch_delay)

class ExpandedTradingConfig:
    """
    Optimized configuration for expanded watchlist trading
    """
    
    def __init__(self):
        # EXPANDED STOCK WATCHLISTS (from automated_trader.py)
        self.us_large_cap = [
            "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "TSLA", "NVDA", "NFLX", "ADBE",
            "CRM", "ORCL", "INTC", "AMD", "QCOM", "AVGO", "TXN", "MU", "AMAT", "LRCX",
            "KLAC", "MRVL", "SWKS", "MCHP", "CTSH", "INFY", "ACN", "IBM", "HPQ", "DELL",
            "NOW", "TEAM", "ZM", "DOCU", "CRWD", "ZS", "OKTA", "DDOG", "SNOW", "MDB",
            "TSM", "ASML", "LAM", "KLAC", "AMAT", "TER", "MPWR", "MXIM", "ADI", "ON"
        ]
        
        self.finance_sector = [
            "JPM", "BAC", "WFC", "C", "GS", "MS", "USB", "PNC", "TFC", "COF",
            "BRK-B", "AIG", "PGR", "TRV", "AXP", "ALL", "CB", "AON", "MMC", "MARSH",
            "V", "MA", "PYPL", "SQ", "COIN", "ICE", "CME", "NDAQ", "SPGI", "MCO",
            "MSCI", "BLK", "SCHW", "TROW", "AMG", "BEN", "IVZ", "FDS"
        ]
        
        self.healthcare_biotech = [
            "JNJ", "PFE", "ABBV", "MRK", "LLY", "BMY", "AMGN", "GILD", "BIIB", "REGN",
            "MRNA", "BNTX", "NVAX", "VRTX", "CELG", "ILMN", "BMRN", "TECH", "SRPT", "BLUE",
            "MDT", "ABT", "TMO", "DHR", "SYK", "BSX", "EW", "HOLX", "A", "ZBH",
            "UNH", "ANTM", "CVS", "CI", "HUM", "CNC", "MOH", "ELV", "VEEV"
        ]
        
        self.energy_commodities = [
            "XOM", "CVX", "COP", "EOG", "SLB", "HAL", "BKR", "NOV", "FTI", "HP",
            "NEE", "ENPH", "SEDG", "FSLR", "SPWR", "RUN", "BE", "PLUG", "BALLARD",
            "GLD", "SLV", "PDBC", "DBA", "USO", "UNG", "CPER", "JJN", "JJU", "JJG"
        ]
        
        self.consumer_retail = [
            "WMT", "HD", "TGT", "LOW", "COST", "TJX", "SBUX", "MCD", "CMG", "BKNG",
            "PG", "KO", "PEP", "NKE", "UL", "CL", "KMB", "GIS", "K", "CPB",
            "LVMUY", "TPG", "RL", "COH", "KORS", "LULU", "DECK", "CROX", "ETSY"
        ]
        
        self.industrial_defense = [
            "BA", "LMT", "RTX", "NOC", "GD", "LHX", "HII", "LDOS", "DFEN",
            "CAT", "DE", "MMM", "GE", "HON", "UPS", "FDX", "DAL", "UAL", "AAL",
            "FCX", "NEM", "GOLD", "AA", "X", "CLF", "STLD", "NUE", "MLM", "VMC"
        ]
        
        self.utilities_reits = [
            "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "PEG", "XEL", "XLU",
            "AMT", "PLD", "CCI", "EQIX", "SPG", "O", "WELL", "DLR", "PSA", "EQR"
        ]
        
        self.international_etfs = [
            "VGK", "EFA", "FEZ", "EWG", "EWU", "EWQ", "EWI", "EWP", "EWN", "EWD",
            "EWJ", "FXI", "EWH", "EWY", "EWT", "EWS", "INDA", "EPI", "EWZ", "EWC",
            "EEM", "VWO", "IEMG", "SCHE", "EEMV", "SPEM", "DEM", "DFEM", "HEEM"
        ]
        
        self.sector_etfs = [
            "XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLU", "XLB", "XLY", "XLRE",
            "ARKK", "ARKQ", "ARKW", "ARKG", "ICLN", "PBW", "QCLN", "JETS", "SKYY", "ROBO"
        ]
        
        # EXPANDED CRYPTO WATCHLIST (50 cryptos)
        crypto_portfolio = get_diversified_portfolio()
        self.crypto_symbols = get_symbols_only(crypto_portfolio)
        
        # COMBINE ALL WATCHLISTS
        self.all_stock_symbols = (
            self.us_large_cap + self.finance_sector + self.healthcare_biotech + 
            self.energy_commodities + self.consumer_retail + self.industrial_defense + 
            self.utilities_reits + self.international_etfs + self.sector_etfs
        )
        
        # Remove duplicates
        self.all_stock_symbols = list(set(self.all_stock_symbols))
        self.all_symbols = self.all_stock_symbols + self.crypto_symbols
        
        print(f"EXPANDED TRADING CONFIGURATION")
        print(f"   Stock symbols: {len(self.all_stock_symbols)}")
        print(f"   Crypto symbols: {len(self.crypto_symbols)}")
        print(f"   Total symbols: {len(self.all_symbols)}")
    
    def get_market_hours_focus(self) -> Dict[str, List[str]]:
        """
        Get symbol focus based on market hours for optimal efficiency
        """
        now = datetime.now()
        hour = now.hour
        
        if 9 <= hour <= 16:  # US market hours
            return {
                "primary": self.us_large_cap + self.finance_sector[:20],
                "secondary": self.healthcare_biotech[:15] + self.crypto_symbols[:10],
                "tertiary": self.energy_commodities + self.consumer_retail
            }
        elif 17 <= hour <= 23 or 0 <= hour <= 8:  # After hours / Pre-market
            return {
                "primary": self.crypto_symbols,  # 24/7 crypto markets
                "secondary": self.international_etfs,  # International exposure
                "tertiary": self.us_large_cap[:30]  # Major US stocks
            }
        else:  # Weekend
            return {
                "primary": self.crypto_symbols,  # Only crypto trading
                "secondary": [],
                "tertiary": []
            }
    
    def get_sector_rotation_focus(self, focus_sectors: List[str] = None) -> List[str]:
        """
        Get symbols focused on specific sectors for sector rotation strategies
        """
        sector_map = {
            "tech": self.us_large_cap[:30],  # Heavy tech weighting in large cap
            "finance": self.finance_sector,
            "healthcare": self.healthcare_biotech,
            "energy": self.energy_commodities,
            "consumer": self.consumer_retail,
            "industrial": self.industrial_defense,
            "utilities": self.utilities_reits,
            "international": self.international_etfs,
            "crypto": self.crypto_symbols
        }
        
        if not focus_sectors:
            # Default balanced rotation
            focus_sectors = ["tech", "finance", "healthcare", "crypto"]
        
        focused_symbols = []
        for sector in focus_sectors:
            focused_symbols.extend(sector_map.get(sector, []))
        
        return list(set(focused_symbols))  # Remove duplicates

# USAGE EXAMPLE
if __name__ == "__main__":
    # Initialize optimized trading configuration
    config = ExpandedTradingConfig()
    strategy = OptimizedScanningStrategy(max_requests_per_minute=50, max_requests_per_hour=800)
    
    # Simulate current positions
    mock_positions = {"AAPL", "BTC-USD", "MSFT", "ETH-USD", "NVDA"}
    
    # Get optimized scan list
    scan_list = strategy.get_optimized_scan_list(
        all_symbols=config.all_symbols,
        current_positions=mock_positions,
        max_symbols_per_cycle=40
    )
    
    print(f"\nSCANNING SIMULATION")
    print(f"Symbols to scan: {scan_list}")
    print(f"\nProcessing symbols...")
    
    # Simulate batch processing
    processed = 0
    for symbol in strategy.batch_process_symbols(scan_list, batch_size=8):
        processed += 1
        print(f"      {symbol} scanned ({processed}/{len(scan_list)})")
        if processed >= 15:  # Limit demo output
            print(f"      ... (processing remaining {len(scan_list) - processed} symbols)")
            break
    
    print(f"\nSCANNING COMPLETE")
    print(f"   Processed: {min(processed, len(scan_list))}/{len(scan_list)} symbols")
    print(f"   API requests used: {strategy.request_count_minute}/min, {strategy.request_count_hour}/hour")