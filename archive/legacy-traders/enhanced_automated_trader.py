#!/usr/bin/env python3
"""
ENHANCED AUTOMATED TRADER - Optimized for 300+ Symbol Scanning
Integrates expanded watchlists with efficient API management
"""

import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Set
import json
import sys
import importlib.util

# Import existing modules
spec = importlib.util.spec_from_file_location("data_collector", "src/data/data_collector.py")
data_collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data_collector)
StockDataCollector = data_collector.StockDataCollector

from src.core.position_manager import PositionManager, PositionDecision
from src.data.earnings_calendar import EarningsChecker
from expanded_crypto_watchlist import get_diversified_portfolio, get_symbols_only
from optimized_trading_strategy import OptimizedScanningStrategy, ExpandedTradingConfig

class EnhancedAutomatedTrader:
    def __init__(self, max_positions: int = 20, max_investment_per_stock: float = 4000):
        """Initialize enhanced automated trader with expanded capabilities"""
        
        # Core components
        self.collector = StockDataCollector()
        self.position_manager = PositionManager(self.collector)
        self.earnings_checker = EarningsChecker()
        
        # Enhanced configuration
        self.max_positions = max_positions
        self.max_investment_per_stock = max_investment_per_stock
        
        # Timing controls - optimized for larger scanning
        self.scan_interval = 2700  # 45 minutes (more time for larger scans)
        self.update_interval = 450  # 7.5 minutes (more frequent position updates)
        self.running = False
        self.last_scan = datetime.min
        self.last_update = datetime.min
        
        # Enhanced watchlist and strategy
        self.trading_config = ExpandedTradingConfig()
        self.scanning_strategy = OptimizedScanningStrategy(
            max_requests_per_minute=45,  # Conservative API limits
            max_requests_per_hour=750    # Allow for sustained operation
        )
        
        # Tracking
        self.scanned_today = set()
        self.alerts_today = []
        self.scan_performance_stats = {
            'total_scans': 0,
            'successful_scans': 0,
            'api_errors': 0,
            'opportunities_found': 0
        }
        
        print(f"ENHANCED AUTOMATED TRADER INITIALIZED")
        print(f"   Max positions: {max_positions}")
        print(f"   Max investment per position: ${max_investment_per_stock:,.2f}")
        print(f"   Total symbols available: {len(self.trading_config.all_symbols)}")
        print(f"   Scan interval: {self.scan_interval/60:.1f} minutes")
        print(f"   Update interval: {self.update_interval/60:.1f} minutes")

    def get_dynamic_scan_configuration(self) -> Dict:
        """Get dynamic scanning configuration based on market conditions and time"""
        now = datetime.now()
        current_positions = set(self.position_manager.positions.keys())
        
        # Determine max symbols per cycle based on:
        # 1. API capacity remaining
        # 2. Time of day
        # 3. Number of current positions
        
        api_capacity = self.scanning_strategy.max_rph - self.scanning_strategy.request_count_hour
        base_capacity = min(60, api_capacity // 15)  # Conservative use of API quota
        
        # Adjust based on market hours
        if 9 <= now.hour <= 16:  # US market hours - focus more
            max_symbols = min(base_capacity + 20, 80)
            focus = self.trading_config.get_market_hours_focus()
            symbol_pool = focus["primary"] + focus["secondary"][:20]
        elif 17 <= now.hour <= 23 or 0 <= now.hour <= 8:  # After hours
            max_symbols = min(base_capacity + 10, 60)
            focus = self.trading_config.get_market_hours_focus()
            symbol_pool = focus["primary"] + focus["secondary"]
        else:  # Weekends - crypto only
            max_symbols = min(base_capacity, 40)
            symbol_pool = self.trading_config.crypto_symbols
        
        # Add current positions (always monitor)
        symbol_pool.extend(list(current_positions))
        symbol_pool = list(set(symbol_pool))  # Remove duplicates
        
        return {
            "max_symbols_this_cycle": max_symbols,
            "symbol_pool": symbol_pool,
            "api_capacity_remaining": api_capacity,
            "scan_focus": "market_hours" if 9 <= now.hour <= 16 else "after_hours" if now.weekday() < 5 else "weekend"
        }

    def enhanced_scan_for_opportunities(self) -> List[Dict]:
        """Enhanced scanning with intelligent symbol selection and API management"""
        scan_config = self.get_dynamic_scan_configuration()
        current_positions = set(self.position_manager.positions.keys())
        
        print(f"\nENHANCED MARKET SCANNER - {datetime.now().strftime('%H:%M:%S')}")
        print(f"   Focus: {scan_config['scan_focus']}")
        print(f"   API capacity remaining: {scan_config['api_capacity_remaining']}")
        print(f"   Target scan size: {scan_config['max_symbols_this_cycle']}")
        print("=" * 70)
        
        # Get optimized symbol list
        symbols_to_scan = self.scanning_strategy.get_optimized_scan_list(
            all_symbols=scan_config['symbol_pool'],
            current_positions=current_positions,
            max_symbols_per_cycle=scan_config['max_symbols_this_cycle']
        )
        
        opportunities = []
        successful_scans = 0
        api_errors = 0
        
        # Process symbols in batches
        for symbol in self.scanning_strategy.batch_process_symbols(symbols_to_scan, batch_size=8):
            try:
                # Skip if already in portfolio
                if symbol in current_positions:
                    continue
                    
                # Earnings check for stocks
                if not ("-USD" in symbol):  # Stock symbol
                    try:
                        if self.earnings_checker.has_upcoming_earnings(symbol, days=2):
                            print(f"   {symbol} - Skipped (earnings soon)")
                            continue
                    except Exception:
                        pass  # Continue with scan if earnings check fails
                
                # Get stock data
                stock_data = self.collector.get_stock_data(symbol)
                if 'error' in stock_data:
                    print(f"   {symbol} - Data error")
                    api_errors += 1
                    continue
                
                # Enhanced analysis
                opportunity = self.analyze_enhanced_opportunity(symbol, stock_data)
                if opportunity:
                    opportunities.append(opportunity)
                    print(f"   {symbol} - OPPORTUNITY! Score: {opportunity['buy_score']:.1f}")
                else:
                    print(f"   {symbol} - No signal")
                
                successful_scans += 1
                self.scanned_today.add(symbol)
                
            except Exception as e:
                print(f"   {symbol} - Error: {str(e)[:30]}")
                api_errors += 1
                continue
        
        # Update performance stats
        self.scan_performance_stats['total_scans'] += len(symbols_to_scan)
        self.scan_performance_stats['successful_scans'] += successful_scans
        self.scan_performance_stats['api_errors'] += api_errors
        self.scan_performance_stats['opportunities_found'] += len(opportunities)
        
        print(f"\nSCAN RESULTS:")
        print(f"   Scanned: {successful_scans}/{len(symbols_to_scan)} symbols")
        print(f"   Opportunities: {len(opportunities)}")
        print(f"   API errors: {api_errors}")
        print(f"   API usage: {self.scanning_strategy.request_count_hour}/hour")
        
        return opportunities

    def analyze_enhanced_opportunity(self, symbol: str, stock_data: Dict) -> Dict:
        """Enhanced opportunity analysis with improved scoring"""
        try:
            analysis = self.collector.analyze_stock_potential(stock_data)
            tech_indicators = stock_data.get('technical_indicators', {})
            price_data = stock_data.get('price_data', {})
            
            # Enhanced scoring system
            buy_score = 0
            buy_reasons = []
            risk_factors = []
            
            # Technical Analysis (40% of score)
            rsi = tech_indicators.get('rsi')
            if rsi:
                if rsi < 30:
                    buy_score += 4
                    buy_reasons.append(f"RSI oversold: {rsi:.1f}")
                elif rsi < 40:
                    buy_score += 2
                    buy_reasons.append(f"RSI favorable: {rsi:.1f}")
                elif rsi > 70:
                    buy_score -= 2
                    risk_factors.append(f"RSI overbought: {rsi:.1f}")
            
            # MACD
            macd = tech_indicators.get('macd')
            macd_signal = tech_indicators.get('macd_signal')
            if macd and macd_signal:
                if macd > macd_signal and macd > 0:
                    buy_score += 3
                    buy_reasons.append("MACD bullish crossover")
                elif macd > macd_signal:
                    buy_score += 1
                    buy_reasons.append("MACD bullish momentum")
            
            # Price vs Moving Averages (20% of score)
            price_vs_ma20 = tech_indicators.get('price_vs_ma20', 0)
            if -3 <= price_vs_ma20 <= 1:
                buy_score += 2
                buy_reasons.append(f"Price near MA20: {price_vs_ma20:+.1f}%")
            elif price_vs_ma20 < -10:
                buy_score += 1
                buy_reasons.append(f"Price below MA20: {price_vs_ma20:+.1f}%")
            
            # Volume Analysis (15% of score)
            volume_ratio = price_data.get('volume_ratio', 1)
            if volume_ratio > 1.5:
                buy_score += 2
                buy_reasons.append(f"High volume: {volume_ratio:.1f}x")
            elif volume_ratio > 1.2:
                buy_score += 1
                buy_reasons.append(f"Above avg volume: {volume_ratio:.1f}x")
            
            # Market Sentiment (15% of score)
            classification = analysis.get('classification', 'NEUTRAL')
            if classification == 'BULLISH':
                buy_score += 2
                buy_reasons.append("Technical analysis bullish")
            elif classification == 'BEARISH':
                buy_score -= 1
                risk_factors.append("Technical analysis bearish")
            
            # Crypto-specific adjustments (10% of score)
            if "-USD" in symbol:
                # Crypto gets volatility bonus but also risk penalty
                daily_change = price_data.get('change_percent', 0)
                if -5 <= daily_change <= -1:
                    buy_score += 1
                    buy_reasons.append(f"Crypto dip opportunity: {daily_change:+.1f}%")
                elif daily_change < -10:
                    risk_factors.append(f"High volatility: {daily_change:+.1f}%")
                elif daily_change > 10:
                    buy_score -= 2
                    risk_factors.append(f"Crypto pump risk: {daily_change:+.1f}%")
            
            # Risk assessment
            risk_level = "Low"
            if len(risk_factors) >= 2 or "-USD" in symbol:
                risk_level = "High"
            elif len(risk_factors) == 1:
                risk_level = "Medium"
            
            # Final scoring threshold - more selective
            min_score = 6 if "-USD" in symbol else 5  # Higher bar for crypto
            
            if buy_score >= min_score:
                current_price = price_data.get('current_price', 0)
                company_name = stock_data.get('company_info', {}).get('name', symbol)
                
                return {
                    'symbol': symbol,
                    'company_name': company_name,
                    'current_price': current_price,
                    'buy_score': buy_score,
                    'reasons': buy_reasons,
                    'risk_factors': risk_factors,
                    'risk_level': risk_level,
                    'asset_type': 'crypto' if "-USD" in symbol else 'stock',
                    'timestamp': datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            print(f"   Analysis error for {symbol}: {e}")
            return None

    def smart_position_opening(self, opportunities: List[Dict]) -> int:
        """Smart position opening with enhanced risk management"""
        if not opportunities:
            return 0
            
        available_slots = self.max_positions - len(self.position_manager.positions)
        if available_slots <= 0:
            print(f"\nPortfolio full ({self.max_positions} positions)")
            return 0
        
        print(f"\nSMART POSITION OPENING")
        print(f"   Available slots: {available_slots}")
        print(f"   Opportunities: {len(opportunities)}")
        print("-" * 50)
        
        # Sort by score and diversify by asset type
        opportunities.sort(key=lambda x: x['buy_score'], reverse=True)
        
        positions_opened = 0
        crypto_positions = 0
        stock_positions = 0
        
        # Count current positions by type
        for symbol in self.position_manager.positions.keys():
            if "-USD" in symbol:
                crypto_positions += 1
            else:
                stock_positions += 1
        
        # Risk limits
        max_crypto_ratio = 0.4  # Max 40% crypto positions
        max_crypto_positions = int(self.max_positions * max_crypto_ratio)
        
        for opp in opportunities:
            if positions_opened >= available_slots:
                break
                
            symbol = opp['symbol']
            asset_type = opp['asset_type']
            
            # Enforce crypto ratio limits
            if asset_type == 'crypto' and crypto_positions >= max_crypto_positions:
                print(f"   {symbol} - Skipped (crypto limit reached)")
                continue
            
            # Position sizing based on risk
            risk_level = opp['risk_level']
            if risk_level == "High":
                investment = self.max_investment_per_stock * 0.6  # Reduce size for high risk
            elif risk_level == "Medium":
                investment = self.max_investment_per_stock * 0.8
            else:
                investment = self.max_investment_per_stock
            
            current_price = opp['current_price']
            if current_price <= 0:
                print(f"   {symbol} - Invalid price")
                continue
                
            quantity = max(1, int(investment / current_price))
            actual_investment = current_price * quantity
            
            # Open position
            success = self.position_manager.open_position(
                symbol=symbol,
                entry_price=current_price,
                quantity=quantity,
                stop_loss_percent=7.0 if asset_type == 'crypto' else 5.0,  # Higher SL for crypto
                take_profit_percent=15.0 if asset_type == 'crypto' else 12.0  # Higher TP for crypto
            )
            
            if success:
                positions_opened += 1
                if asset_type == 'crypto':
                    crypto_positions += 1
                else:
                    stock_positions += 1
                
                print(f"   OPENED: {symbol}")
                print(f"      Investment: ${actual_investment:,.2f}")
                print(f"      Score: {opp['buy_score']:.1f} | Risk: {risk_level}")
                print(f"      Reasons: {', '.join(opp['reasons'][:2])}")
                
                self.send_alert("POSITION_OPENED", symbol, 
                              f"Auto-opened {asset_type}: ${actual_investment:,.2f} @ ${current_price:.2f}")
        
        print(f"\nPositions opened: {positions_opened}")
        print(f"   Crypto: {crypto_positions}/{max_crypto_positions}")
        print(f"   Stocks: {stock_positions}/{self.max_positions - max_crypto_positions}")
        
        return positions_opened

    def update_positions(self):
        """Enhanced position updates with better risk management"""
        if not self.position_manager.positions:
            return
            
        print(f"\nPOSITION UPDATE - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 60)
        
        position_symbols = list(self.position_manager.positions.keys())
        
        for symbol in position_symbols:
            try:
                if symbol not in self.position_manager.positions:
                    continue
                    
                print(f"   Updating {symbol}...", end=" ")
                stock_data = self.collector.get_stock_data(symbol)
                
                if 'error' in stock_data:
                    print("Data error")
                    continue
                
                current_price = stock_data['price_data']['current_price']
                self.position_manager.update_position(symbol, current_price)
                
                decision, reasons = self.position_manager.analyze_position_decision(symbol)
                position = self.position_manager.positions[symbol]
                
                pnl_pct = position.unrealized_pnl_percent
                pnl_status = "PROFIT" if pnl_pct >= 0 else "LOSS"
                print(f"{pnl_status} {pnl_pct:+.1f}% | {decision.value}")
                
                # Enhanced decision logic
                is_manual = self.is_manual_position(symbol)
                
                if decision == PositionDecision.SELL_IMMEDIATELY:
                    if is_manual:
                        self.send_alert("MANUAL_REVIEW_URGENT", symbol, 
                                      f"URGENT: Manual position needs review - P&L: {pnl_pct:+.1f}%")
                        print(f"      [MANUAL] Requires manual review")
                    else:
                        self.position_manager.close_position(symbol, f"Auto-sell: {reasons[0] if reasons else 'Critical signal'}")
                        print(f"      [AUTO] Position closed")
                        
                elif decision == PositionDecision.CONSIDER_SELL and abs(pnl_pct) > 2:
                    alert_type = "MANUAL_REVIEW" if is_manual else "CONSIDER_SELL"
                    self.send_alert(alert_type, symbol, f"Consider sell - P&L: {pnl_pct:+.1f}%")
                    
            except Exception as e:
                print(f"Error: {str(e)[:20]}")
                continue
        
        # Portfolio summary
        try:
            total_positions = len(self.position_manager.positions)
            total_pnl = sum(pos.unrealized_pnl for pos in self.position_manager.positions.values())
            crypto_positions = sum(1 for symbol in self.position_manager.positions.keys() if "-USD" in symbol)
            stock_positions = total_positions - crypto_positions
            
            print(f"\nPORTFOLIO SUMMARY:")
            print(f"   Total positions: {total_positions}")
            print(f"   Stocks: {stock_positions} | Crypto: {crypto_positions}")
            print(f"   Total P&L: ${total_pnl:.2f}")
            
        except Exception as e:
            print(f"Portfolio summary error: {e}")

    def is_manual_position(self, symbol):
        """Enhanced manual position detection"""
        if symbol not in self.position_manager.positions:
            return False
            
        position = self.position_manager.positions[symbol]
        
        # Check for manual indicators
        if hasattr(position, 'notes') and position.notes:
            manual_keywords = ["Real position", "Manual", "DEGIRO", "REVOLUT", "Real", "manual"]
            if any(keyword.lower() in position.notes.lower() for keyword in manual_keywords):
                return True
        
        # Large position detection
        position_value = position.entry_price * position.quantity
        if position_value > self.max_investment_per_stock * 2:
            return True
            
        # Known manual symbols
        manual_symbols = ["BTC-USD", "NDAQ", "BNTX", "XAG-USD", "PPFB.L", "SXLE.MI", "DFEN", "VUSD.L"]
        return symbol in manual_symbols

    def send_alert(self, alert_type: str, symbol: str, message: str):
        """Enhanced alert system"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        alert_text = f"\n[{timestamp}] {symbol}: {message}"
        
        # Highlight important alerts
        if "MANUAL" in alert_type or "URGENT" in alert_type:
            alert_text = f"\n{'='*60}\nURGENT{alert_text}\n{'='*60}"
        elif "POSITION_OPENED" in alert_type:
            alert_text = f"\nNEW POSITION{alert_text}"
            
        print(alert_text)
        
        alert_record = {
            'timestamp': datetime.now().isoformat(),
            'type': alert_type,
            'symbol': symbol,
            'message': message
        }
        self.alerts_today.append(alert_record)

    def start_enhanced_trading(self):
        """Start enhanced trading with performance monitoring"""
        self.running = True
        
        print(f"\nRELOADING PORTFOLIO...")
        self.position_manager.reload_from_database()
        reloaded = len(self.position_manager.positions)
        if reloaded > 0:
            updated = self.position_manager.force_update_all_positions()
            print(f"   Reloaded {reloaded} positions, updated {updated} prices")
        
        print(f"\nENHANCED AUTOMATED TRADING STARTED")
        print("=" * 70)
        print(f"   Scan interval: {self.scan_interval/60:.1f} minutes")
        print(f"   Update interval: {self.update_interval/60:.1f} minutes")
        print(f"   Max positions: {self.max_positions}")
        print(f"   Available symbols: {len(self.trading_config.all_symbols)}")
        print(f"\nPress Ctrl+C to stop")
        
        try:
            cycle_count = 0
            while self.running:
                cycle_count += 1
                now = datetime.now()
                
                print(f"\nCYCLE #{cycle_count} - {now.strftime('%H:%M:%S')}")
                print(f"Performance: {self.scan_performance_stats['successful_scans']} scans, "
                      f"{self.scan_performance_stats['opportunities_found']} opportunities")
                
                # Market scan
                if (now - self.last_scan).total_seconds() >= self.scan_interval:
                    opportunities = self.enhanced_scan_for_opportunities()
                    if opportunities:
                        self.smart_position_opening(opportunities)
                    self.last_scan = now
                
                # Position updates
                if (now - self.last_update).total_seconds() >= self.update_interval:
                    self.update_positions()
                    self.last_update = now
                
                # Brief pause between cycles
                time.sleep(45)
                
        except KeyboardInterrupt:
            self.stop_trading()

    def stop_trading(self):
        """Stop trading with performance summary"""
        self.running = False
        print(f"\nENHANCED TRADING STOPPED")
        print(f"Performance Summary:")
        for key, value in self.scan_performance_stats.items():
            print(f"   {key}: {value}")
        
        self.position_manager.print_portfolio_dashboard()

# USAGE
def main():
    print("ENHANCED AUTOMATED TRADER")
    print("1. Demo with enhanced features")
    print("2. Start enhanced automated trading")
    print("3. Performance test")
    
    choice = input("Choose option (1-3): ")
    
    if choice == "1":
        trader = EnhancedAutomatedTrader(max_positions=5, max_investment_per_stock=3000)
        opportunities = trader.enhanced_scan_for_opportunities()
        if opportunities:
            trader.smart_position_opening(opportunities[:2])
    
    elif choice == "2":
        trader = EnhancedAutomatedTrader()
        trader.start_enhanced_trading()
    
    elif choice == "3":
        trader = EnhancedAutomatedTrader(max_positions=15)
        config = trader.get_dynamic_scan_configuration()
        print(f"\nPerformance test results:")
        for key, value in config.items():
            if key != 'symbol_pool':
                print(f"   {key}: {value}")
            else:
                print(f"   symbol_pool_size: {len(value)}")
    
    else:
        print("Invalid option")

if __name__ == "__main__":
    main()