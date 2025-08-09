#!/usr/bin/env python3
"""
Automated Trader - Sistema de Trading Automatizado (Versión Corregida)
"""

import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Set
import json
import sys
import importlib.util

# Import modules
spec = importlib.util.spec_from_file_location("data_collector", "data-collector.py")
data_collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data_collector)
StockDataCollector = data_collector.StockDataCollector



from position_manager import PositionManager, PositionDecision
from earnings_calendar import EarningsChecker

class AutomatedTrader:
    def verify_portfolio_data(self):
        """Verify portfolio data is correct before trading"""
        print(f"\n🔍 PORTFOLIO VERIFICATION")
        print("=" * 60)
        if not self.position_manager.positions:
            print("No positions loaded")
            return False
        all_reasonable = True
        for symbol, position in self.position_manager.positions.items():
            try:
                stock_data = self.collector.get_stock_data(symbol)
                if 'error' not in stock_data:
                    current_price = stock_data['price_data']['current_price']
                    self.position_manager.update_position(symbol, current_price)
                    pnl_pct = position.unrealized_pnl_percent
                    pnl_color = "📈" if pnl_pct >= 0 else "📉"
                    print(f"{symbol:8} | {pnl_color} {pnl_pct:+6.1f}% | Entry: ${position.entry_price:.2f} | Current: ${current_price:.2f}")
                    if abs(pnl_pct) > 50 and symbol not in ["BTC-USD"]:
                        print(f"   ⚠️ WARNING: Extreme P&L detected for {symbol}")
                        all_reasonable = False
                else:
                    print(f"{symbol:8} | ❌ Data error")
                    all_reasonable = False
            except Exception as e:
                print(f"{symbol:8} | ❌ Exception: {e}")
                all_reasonable = False
        if all_reasonable:
            print(f"\n✅ All position data looks reasonable")
        else:
            print(f"\n❌ Some positions have unreasonable data - check database")
        return all_reasonable
    def __init__(self, max_positions: int = 8, max_investment_per_stock: float = 5000):
        """Initialize el trader automatizado"""
        self.collector = StockDataCollector()
        self.position_manager = PositionManager(self.collector)
        self.earnings_checker = EarningsChecker()
        self.max_positions = max_positions
        self.max_investment_per_stock = max_investment_per_stock
        self.scan_interval = 1800  # 30 minutos
        self.update_interval = 300  # 5 minutos
        self.running = False
        self.last_scan = datetime.min
        self.last_update = datetime.min
        # Watchlist de stocks populares
        # EXPANDED WATCHLIST - 150+ symbols
        self.us_large_cap = [
            # FAANG + Big Tech
            "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "TSLA", "NVDA", "NFLX", "ADBE",
            # Additional Tech
            "CRM", "ORCL", "INTC", "AMD", "QCOM", "AVGO", "TXN", "MU", "AMAT", "LRCX",
            "KLAC", "MRVL", "SWKS", "MCHP", "CTSH", "INFY", "ACN", "IBM", "HPQ", "DELL",
            # Cloud/Software  
            "NOW", "TEAM", "ZM", "DOCU", "CRWD", "ZS", "OKTA", "DDOG", "SNOW", "MDB",
            # Semiconductors
            "TSM", "ASML", "LAM", "KLAC", "AMAT", "TER", "MPWR", "MXIM", "ADI", "ON"
        ]
        self.finance_sector = [
            # Banks
            "JPM", "BAC", "WFC", "C", "GS", "MS", "USB", "PNC", "TFC", "COF",
            # Insurance
            "BRK-B", "AIG", "PGR", "TRV", "AXP", "ALL", "CB", "AON", "MMC", "MARSH",
            # Financial Services
            "V", "MA", "PYPL", "SQ", "COIN", "ICE", "CME", "NDAQ", "SPGI", "MCO",
            "MSCI", "BLK", "SCHW", "TROW", "AMG", "BEN", "IVZ", "FDS"
        ]
        self.healthcare_biotech = [
            # Big Pharma
            "JNJ", "PFE", "ABBV", "MRK", "LLY", "BMY", "AMGN", "GILD", "BIIB", "REGN",
            # Biotech
            "MRNA", "BNTX", "NVAX", "VRTX", "CELG", "ILMN", "BMRN", "TECH", "SRPT", "BLUE",
            # Medical Devices
            "MDT", "ABT", "TMO", "DHR", "SYK", "BSX", "EW", "HOLX", "A", "ZBH",
            # Healthcare Services
            "UNH", "ANTM", "CVS", "CI", "HUM", "CNC", "MOH", "ELV", "VEEV"
        ]
        self.energy_commodities = [
            # Oil & Gas
            "XOM", "CVX", "COP", "EOG", "SLB", "HAL", "BKR", "NOV", "FTI", "HP",
            # Renewables
            "NEE", "ENPH", "SEDG", "FSLR", "SPWR", "RUN", "BE", "PLUG", "BALLARD",
            # Commodities ETFs
            "GLD", "SLV", "PDBC", "DBA", "USO", "UNG", "CPER", "JJN", "JJU", "JJG"
        ]
        self.consumer_retail = [
            # Retail
            "WMT", "HD", "TGT", "LOW", "COST", "TJX", "SBUX", "MCD", "CMG", "BKNG",
            # Consumer Goods
            "PG", "KO", "PEP", "NKE", "UL", "CL", "KMB", "GIS", "K", "CPB",
            # Luxury/Discretionary
            "LVMUY", "TPG", "RL", "COH", "KORS", "LULU", "DECK", "CROX", "ETSY"
        ]
        self.industrial_defense = [
            # Aerospace/Defense
            "BA", "LMT", "RTX", "NOC", "GD", "LHX", "HII", "LDOS", "DFEN",
            # Industrial
            "CAT", "DE", "MMM", "GE", "HON", "UPS", "FDX", "DAL", "UAL", "AAL",
            # Materials
            "FCX", "NEM", "GOLD", "AA", "X", "CLF", "STLD", "NUE", "MLM", "VMC"
        ]
        self.utilities_reits = [
            # Utilities
            "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "PEG", "XEL", "XLU",
            # REITs
            "AMT", "PLD", "CCI", "EQIX", "SPG", "O", "WELL", "DLR", "PSA", "EQR"
        ]
        self.crypto_watchlist = [
            # Major Cryptos
            "BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "SOL-USD", "ADA-USD",
            # DeFi/Alt coins  
            "DOT-USD", "LINK-USD", "MATIC-USD", "AVAX-USD", "UNI-USD", "AAVE-USD",
            # Layer 1s
            "ATOM-USD", "ALGO-USD", "FTM-USD", "ONE-USD", "NEAR-USD", "FLOW-USD",
            # Meme/Popular
            "DOGE-USD", "SHIB-USD", "LTC-USD", "BCH-USD", "ETC-USD"
        ]
        self.international_etfs = [
            # Europe
            "VGK", "EFA", "FEZ", "EWG", "EWU", "EWQ", "EWI", "EWP", "EWN", "EWD",
            # Asia
            "EWJ", "FXI", "EWH", "EWY", "EWT", "EWS", "INDA", "EPI", "EWZ", "EWC",
            # Emerging Markets
            "EEM", "VWO", "IEMG", "SCHE", "EEMV", "SPEM", "DEM", "DFEM", "HEEM"
        ]
        self.sector_etfs = [
            # US Sector ETFs
            "XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLU", "XLB", "XLY", "XLRE",
            # Thematic ETFs
            "ARKK", "ARKQ", "ARKW", "ARKG", "ICLN", "PBW", "QCLN", "JETS", "SKYY", "ROBO"
        ]
        # COMBINE ALL WATCHLISTS
        self.watchlist = (
            self.us_large_cap + 
            self.finance_sector + 
            self.healthcare_biotech + 
            self.energy_commodities + 
            self.consumer_retail + 
            self.industrial_defense + 
            self.utilities_reits + 
            self.crypto_watchlist +
            self.international_etfs + 
            self.sector_etfs +
            # Add your personal positions (always monitor)
            ["NDAQ", "BNTX", "DFEN", "GLD", "XLU", "VOO", "SLV", "BTC-USD"]
        )
        # Remove duplicates
        self.watchlist = list(set(self.watchlist))
        print(f"✅ Expanded watchlist: {len(self.watchlist)} symbols")
        print(f"   - US Large Cap: {len(self.us_large_cap)}")
        print(f"   - Finance: {len(self.finance_sector)}")  
        print(f"   - Healthcare/Biotech: {len(self.healthcare_biotech)}")
        print(f"   - Energy/Commodities: {len(self.energy_commodities)}")
        print(f"   - Crypto: {len(self.crypto_watchlist)}")
        print(f"   - International: {len(self.international_etfs)}")
        self.scanned_today = set()
        self.alerts_today = []
        print(f" AutomatedTrader inicializado")
        print(f" Max posiciones: {max_positions}")
        print(f" Max inversión por stock: ${max_investment_per_stock:,.2f}")
    def get_prioritized_watchlist(self):
        """Get prioritized watchlist based on market conditions"""
        now = datetime.now()
        # Weekend: Focus on crypto (24/7 markets)
        if now.weekday() >= 5:
            priority_list = (
                self.crypto_watchlist + 
                list(self.position_manager.positions.keys()) +  # Always scan open positions
                self.us_large_cap[:20]  # Top 20 stocks
            )
        # Market hours: Full US focus
        elif 9 <= now.hour <= 16:  # US market hours (adjust for timezone)
            priority_list = (
                list(self.position_manager.positions.keys()) +  # Always scan open positions
                self.us_large_cap + 
                self.finance_sector +
                self.healthcare_biotech[:15] +
                self.crypto_watchlist[:10]
            )
        # After hours: International + crypto
        else:
            priority_list = (
                list(self.position_manager.positions.keys()) +
                self.crypto_watchlist +
                self.international_etfs[:20] +
                self.us_large_cap[:30]
            )
        return list(set(priority_list))  # Remove duplicates

    def scan_for_buy_signals(self) -> List[Dict]:
        """Escanea buscando señales de compra con lista priorizada"""
        # Use prioritized watchlist instead of full watchlist
        scanning_list = self.get_prioritized_watchlist()
        buy_opportunities = []
        print(f"\n MARKET SCANNER - {datetime.now().strftime('%H:%M:%S')}")
        print(f"Scanning {len(scanning_list)} prioritized symbols")
        print("=" * 60)
        scanned_count = 0
        opportunities_found = 0
        for symbol in scanning_list:
            if symbol in self.position_manager.positions:
                continue
            if symbol in self.scanned_today:
                continue
            # Earnings check
            try:
                if self.earnings_checker.has_upcoming_earnings(symbol, days=3):
                    # Obtener días hasta earnings para log
                    ticker = self.earnings_checker
                    ticker_obj = None
                    try:
                        ticker_obj = ticker.yf.Ticker(symbol)
                        cal = ticker_obj.calendar
                        earnings_date = None
                        if ticker.EARNINGS_DATE in cal.index:
                            earnings_date = cal.loc[ticker.EARNINGS_DATE][0]
                        elif ticker.EARNINGS_DATE in cal.columns:
                            earnings_date = cal[ticker.EARNINGS_DATE][0]
                        if earnings_date is not None:
                            today = datetime.now().date()
                            earnings_date_val = earnings_date.date() if hasattr(earnings_date, 'date') else earnings_date
                            days_to_earnings = (earnings_date_val - today).days
                        else:
                            days_to_earnings = 'unknown'
                    except Exception:
                        days_to_earnings = 'unknown'
                    print(f" {symbol} skipped - earnings in {days_to_earnings} days")
                    self.scanned_today.add(symbol)
                    continue
            except Exception as e:
                print(f" {symbol} earnings check error: {e}")
                self.scanned_today.add(symbol)
                continue
            try:
                print(f" Escaneando {symbol}...", end=" ")
                stock_data = self.collector.get_stock_data(symbol)
                if 'error' in stock_data:
                    print(" Error")
                    continue
                analysis = self.collector.analyze_stock_potential(stock_data)
                tech_indicators = stock_data.get('technical_indicators', {})
                price_data = stock_data.get('price_data', {})
                # Cálculo de buy score
                buy_score = 0
                buy_reasons = []
                # RSI
                rsi = tech_indicators.get('rsi')
                if rsi and rsi < 35:
                    buy_score += 3
                    buy_reasons.append(f"RSI oversold: {rsi:.1f}")
                elif rsi and rsi < 45:
                    buy_score += 1
                    buy_reasons.append(f"RSI favorable: {rsi:.1f}")
                # MACD
                macd = tech_indicators.get('macd')
                macd_signal = tech_indicators.get('macd_signal')
                if macd and macd_signal and macd > macd_signal:
                    buy_score += 2
                    buy_reasons.append("MACD bullish crossover")
                # Precio vs MA20
                price_vs_ma20 = tech_indicators.get('price_vs_ma20', 0)
                if -5 <= price_vs_ma20 <= 2:
                    buy_score += 2
                    buy_reasons.append(f"Precio cerca MA20: {price_vs_ma20:+.1f}%")
                # Volumen
                volume_ratio = price_data.get('volume_ratio', 1)
                if volume_ratio > 1.2:
                    buy_score += 1
                    buy_reasons.append(f"Volumen alto: {volume_ratio:.1f}x")
                # Análisis general
                classification = analysis.get('classification', 'NEUTRAL')
                if classification in ['BULLISH']:
                    buy_score += 2
                    buy_reasons.append("Análisis técnico bullish")
                scanned_count += 1
                # Decisión de compra
                if buy_score >= 5:
                    current_price = price_data.get('current_price', 0)
                    company_name = stock_data.get('company_info', {}).get('name', symbol)
                    opportunity = {
                        'symbol': symbol,
                        'company_name': company_name,
                        'current_price': current_price,
                        'buy_score': buy_score,
                        'reasons': buy_reasons,
                        'timestamp': datetime.now().isoformat()
                    }
                    buy_opportunities.append(opportunity)
                    opportunities_found += 1
                    print(f" BUY SIGNAL! Score: {buy_score}")
                    self.send_alert("BUY_SIGNAL", symbol, f"Buy signal - Score: {buy_score}")
                else:
                    print(f" Score: {buy_score}")
                    self.scanned_today.add(symbol)
            except Exception as e:
                print(f" Error: {str(e)[:30]}")
                continue
            time.sleep(0.1)  # Rate limiting
        print(f"\n SCAN COMPLETO:")
        print(f"    Stocks escaneados: {scanned_count}")
        print(f"    Oportunidades encontradas: {opportunities_found}")
        return buy_opportunities

    def auto_open_positions(self, opportunities: List[Dict]) -> int:
        """Abre posiciones automáticamente"""
        positions_opened = 0
        available_slots = self.max_positions - len(self.position_manager.positions)
        
        if available_slots <= 0:
            print(f" Portfolio lleno ({self.max_positions} posiciones)")
            return 0
        
        print(f"\n AUTO-OPENING POSITIONS")
        print(f"    Slots disponibles: {available_slots}")
        print("-" * 40)
        
        sorted_opportunities = sorted(opportunities, key=lambda x: x['buy_score'], reverse=True)
        
        for opp in sorted_opportunities[:available_slots]:
            if positions_opened >= available_slots:
                break
            
            symbol = opp['symbol']
            current_price = opp['current_price']
            quantity = max(1, int(self.max_investment_per_stock / current_price))
            
            success = self.position_manager.open_position(
                symbol=symbol,
                entry_price=current_price,
                quantity=quantity,
                stop_loss_percent=5.0,
                take_profit_percent=12.0
            )
            
            if success:
                positions_opened += 1
                investment = current_price * quantity
                
                print(f" Posición abierta: {symbol}")
                print(f"    Inversión: ${investment:,.2f}")
                print(f"    Score: {opp['buy_score']}")
                print(f"    Razones: {', '.join(opp['reasons'][:2])}")
                
                self.send_alert("POSITION_OPENED", symbol, 
                              f"Auto-opened: ${investment:,.2f} @ ${current_price:.2f}")
                
                self.scanned_today.discard(symbol)
        
        return positions_opened

    def is_manual_position(self, symbol):
        """Detect if position is manual/real"""
        if symbol not in self.position_manager.positions:
            return False
        position = self.position_manager.positions[symbol]
        # Check notes for manual indicators
        if hasattr(position, 'notes') and position.notes:
            manual_keywords = ["Real position", "Manual", "DEGIRO", "REVOLUT", "Real"]
            if any(keyword in position.notes for keyword in manual_keywords):
                return True
        # Fallback: assume large positions or specific symbols are manual
        large_position_value = position.entry_price * position.quantity
        if large_position_value > 10000:
            return True
        manual_symbols = ["BTC-USD", "NDAQ", "BNTX", "XAG-USD", "PPFB.L", "SXLE.MI", "DFEN", "VUSD.L"]
        return symbol in manual_symbols

    def update_positions(self):
        """Actualiza todas las posiciones abiertas (acciones y criptos) con protección para MANUAL"""
        if not self.position_manager.positions:
            return
        print(f"\n POSITION UPDATE - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 60)
        position_symbols = list(self.position_manager.positions.keys())
        for symbol in position_symbols:
            try:
                if symbol not in self.position_manager.positions:
                    continue
                print(f" Actualizando {symbol}...", end=" ")
                stock_data = self.collector.get_stock_data(symbol)
                if 'error' in stock_data:
                    print(" Error")
                    continue
                current_price = stock_data['price_data']['current_price']
                self.position_manager.update_position(symbol, current_price)
                decision, reasons = self.position_manager.analyze_position_decision(symbol)
                position = self.position_manager.positions[symbol]
                pnl_color = "📈" if position.unrealized_pnl >= 0 else "📉"
                print(f"{pnl_color} P&L: {position.unrealized_pnl_percent:+.1f}% | {decision.value}")
                # SAFETY CHECK FOR MANUAL POSITIONS
                is_manual = self.is_manual_position(symbol)
                if decision == PositionDecision.SELL_IMMEDIATELY:
                    if is_manual:
                        self.send_alert("MANUAL_REVIEW_URGENT", symbol, f"🚨 MANUAL POSITION NEEDS REVIEW - P&L: {position.unrealized_pnl_percent:+.1f}% - SELL signal detected")
                        print(f"   [SAFETY] Manual position {symbol} requires manual review")
                    else:
                        self.send_alert("SELL_IMMEDIATELY", symbol, f"Sell immediately - P&L: {position.unrealized_pnl_percent:+.1f}%")
                        self.position_manager.close_position(symbol, "Auto-sell: Critical signal")
                elif decision == PositionDecision.CONSIDER_SELL:
                    if abs(position.unrealized_pnl_percent) > 3:
                        alert_type = "MANUAL_REVIEW" if is_manual else "CONSIDER_SELL"
                        self.send_alert(alert_type, symbol, f"Consider sell - P&L: {position.unrealized_pnl_percent:+.1f}%")
            except Exception as e:
                print(f" Error: {str(e)[:20]}")
                continue
        # Portfolio summary
        try:
            total_pnl = sum(pos.unrealized_pnl for pos in self.position_manager.positions.values())
            total_positions = len(self.position_manager.positions)
            pnl_color = "📈" if total_pnl >= 0 else "📉"
            print(f"\n{pnl_color} Portfolio: {total_positions} posiciones | P&L Total: ${total_pnl:.2f}")
        except Exception as e:
            print(f"\nPortfolio summary error: {e}")

    def send_alert(self, alert_type: str, symbol: str, message: str):
        """Sistema de notificaciones mejorado"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        emoji_map = {
            "BUY_SIGNAL": "🎯",
            "POSITION_OPENED": "📈", 
            "SELL_IMMEDIATELY": "🔴",
            "CONSIDER_SELL": "⚠️",
            "PARTIAL_PROFIT": "💰",
            "MANUAL_REVIEW": "👁️",
            "MANUAL_REVIEW_URGENT": "🚨"
        }
        emoji = emoji_map.get(alert_type, "📊")
        alert_text = f"\n{emoji} {timestamp} | {symbol}: {message}"
        # Highlight manual position alerts
        if "MANUAL" in alert_type:
            alert_text = f"\n{'='*60}\n{alert_text}\n{'='*60}"
        print(alert_text)
        alert_record = {
            'timestamp': datetime.now().isoformat(),
            'type': alert_type,
            'symbol': symbol,
            'message': message
        }
        self.alerts_today.append(alert_record)

    def start_automated_trading(self):
        """Inicia trading automatizado"""
        self.running = True
        print(f"\n🔄 RELOADING PORTFOLIO FROM DATABASE...")
        self.position_manager.reload_from_database()
        reloaded = len(self.position_manager.positions)
        if reloaded > 0:
            updated = self.position_manager.force_update_all_positions()
            print(f"   ✅ Reloaded {reloaded} positions, updated {updated} with current prices")
        print(f"\n INICIANDO TRADING AUTOMATIZADO")
        print("=" * 60)
        print(f" Scan: {self.scan_interval/60:.0f} min | Update: {self.update_interval/60:.0f} min")
        print(f"\n Presiona Ctrl+C para detener")
        try:
            cycle_count = 0
            while self.running:
                cycle_count += 1
                now = datetime.now()
                print(f"\n CICLO #{cycle_count} - {now.strftime('%H:%M:%S')}")
                # Market scan cada 30 min
                if (now - self.last_scan).total_seconds() >= self.scan_interval:
                    opportunities = self.scan_for_buy_signals()
                    if opportunities:
                        self.auto_open_positions(opportunities)
                    self.last_scan = now
                # Update cada 5 min
                if (now - self.last_update).total_seconds() >= self.update_interval:
                    self.update_positions()
                    self.last_update = now
                time.sleep(30)  # Ciclo cada 30 segundos
        except KeyboardInterrupt:
            self.stop_trading()

    def stop_trading(self):
        """Detiene el sistema"""
        self.running = False
        print(f"\n Sistema detenido")
        self.position_manager.print_portfolio_dashboard()

def quick_demo():
    """Demo rápido"""
    trader = AutomatedTrader(max_positions=3, max_investment_per_stock=2000)
    
    print(f"\n Escaneando mercado...")
    opportunities = trader.scan_for_buy_signals()
    
    if opportunities:
        print(f"\n Abriendo posiciones...")
        trader.auto_open_positions(opportunities[:2])
        
        print(f"\n Actualizando posiciones...")
        time.sleep(2)
        trader.update_positions()
    
    print(f"\n Demo completado!")
    return trader

def main():
    print(" AUTOMATED TRADER")
    print("1. Demo rápido")
    print("2. Trading automatizado")
    print("3. Verify portfolio data")
    choice = input("Opción (1-3): ")
    if choice == "1":
        trader = quick_demo()
    elif choice == "2":
        trader = AutomatedTrader()
        trader.start_automated_trading()
    elif choice == "3":
        trader = AutomatedTrader()
        trader.verify_portfolio_data()
    else:
        print("Invalid option")

        import argparse
        parser = argparse.ArgumentParser(description="Automated Trading System")
        parser.add_argument('--mode', type=str, default=None, help='Mode: cloud or local')
        args = parser.parse_args()

        if args.mode == 'cloud':
            # Run trading and dashboard in parallel (for Docker/Cloud)
            from multiprocessing import Process
            def run_trader():
                trader = AutomatedTrader()
                trader.start_automated_trading()
            def run_dashboard():
                import subprocess
                subprocess.run([sys.executable, 'web_dashboard.py'])
            p1 = Process(target=run_trader)
            p2 = Process(target=run_dashboard)
            p1.start()
            p2.start()
            p1.join()
            p2.join()
        else:
            print(" AUTOMATED TRADER")
            print("1. Demo rápido")
            print("2. Trading automatizado")
            print("3. Verify portfolio data")
            choice = input("Opción (1-3): ")
            if choice == "1":
                trader = quick_demo()
            elif choice == "2":
                trader = AutomatedTrader()
                trader.start_automated_trading()
            elif choice == "3":
                trader = AutomatedTrader()
                trader.verify_portfolio_data()
            else:
                print("Invalid option")

if __name__ == "__main__":
    main()
