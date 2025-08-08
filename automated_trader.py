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

class AutomatedTrader:
    def __init__(self, max_positions: int = 8, max_investment_per_stock: float = 5000):
        """Initialize el trader automatizado"""
        self.collector = StockDataCollector()
        self.position_manager = PositionManager(self.collector)
        
        self.max_positions = max_positions
        self.max_investment_per_stock = max_investment_per_stock
        self.scan_interval = 1800  # 30 minutos
        self.update_interval = 300  # 5 minutos
        
        self.running = False
        self.last_scan = datetime.min
        self.last_update = datetime.min
        
        # Watchlist de stocks populares
        self.watchlist = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "NFLX", "ADBE", "CRM",
            "JPM", "BAC", "WFC", "GS", "MS", "AXP", "BLK", "SCHW",
            "JNJ", "UNH", "PFE", "ABBV", "BMY", "MRK", "LLY", "TMO",
            "WMT", "HD", "PG", "KO", "PEP", "MCD", "NKE", "SBUX", "TGT", "LOW",
            "BA", "CAT", "MMM", "GE", "XOM", "CVX", "COP", "SLB",
            "SPY", "QQQ", "IWM", "DIA", "VTI", "SQQQ", "TQQQ", "SOXL", "DFEN"
        ]
        
        self.scanned_today: Set[str] = set()
        self.alerts_today = []
        
        print(f" AutomatedTrader inicializado")
        print(f" Watchlist: {len(self.watchlist)} stocks")
        print(f" Max posiciones: {max_positions}")
        print(f" Max inversión por stock: ${max_investment_per_stock:,.2f}")

    def scan_for_buy_signals(self) -> List[Dict]:
        """Escanea buscando señales de compra"""
        buy_opportunities = []
        
        print(f"\n MARKET SCANNER - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 60)
        
        scanned_count = 0
        opportunities_found = 0
        
        for symbol in self.watchlist:
            if symbol in self.position_manager.positions:
                continue
            
            if symbol in self.scanned_today:
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

    def update_positions(self):
        """Actualiza todas las posiciones abiertas"""
        if not self.position_manager.positions:
            return
        
        print(f"\n POSITION UPDATE - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 60)
        
        for symbol in list(self.position_manager.positions.keys()):
            try:
                print(f" Actualizando {symbol}...", end=" ")
                
                stock_data = self.collector.get_stock_data(symbol)
                if 'error' in stock_data:
                    print(" Error")
                    continue
                
                current_price = stock_data['price_data']['current_price']
                self.position_manager.update_position(symbol, current_price)
                
                decision, reasons = self.position_manager.analyze_position_decision(symbol)
                position = self.position_manager.positions[symbol]
                
                pnl_color = "" if position.unrealized_pnl >= 0 else ""
                print(f"{pnl_color} P&L: {position.unrealized_pnl_percent:+.1f}% | {decision.value}")
                
                # Generar alertas
                if decision == PositionDecision.SELL_IMMEDIATELY:
                    self.send_alert("SELL_IMMEDIATELY", symbol, 
                                  f"Sell immediately - P&L: {position.unrealized_pnl_percent:+.1f}%")
                    self.position_manager.close_position(symbol, "Auto-sell: Critical signal")
                    
                elif decision == PositionDecision.CONSIDER_SELL:
                    if abs(position.unrealized_pnl_percent) > 3:
                        self.send_alert("CONSIDER_SELL", symbol, 
                                      f"Consider sell - P&L: {position.unrealized_pnl_percent:+.1f}%")
                
            except Exception as e:
                print(f" Error: {str(e)[:20]}")
                continue
        
        summary = self.position_manager.get_portfolio_summary()
        total_pnl_color = "" if summary['total_pnl'] >= 0 else ""
        print(f"\n Portfolio: {summary['total_positions']} posiciones")
        print(f"{total_pnl_color} P&L Total: ${summary['total_pnl']:.2f}")

    def send_alert(self, alert_type: str, symbol: str, message: str):
        """Sistema de notificaciones"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        emoji_map = {
            "BUY_SIGNAL": "",
            "POSITION_OPENED": "", 
            "SELL_IMMEDIATELY": "",
            "CONSIDER_SELL": "",
            "PARTIAL_PROFIT": ""
        }
        
        emoji = emoji_map.get(alert_type, "")
        alert_text = f"\n{emoji} {timestamp} | {symbol}: {message}"
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

if __name__ == "__main__":
    print(" AUTOMATED TRADER")
    choice = input("1. Demo rápido\n2. Trading automatizado\n\nOpción: ")
    
    if choice == "1":
        trader = quick_demo()
    else:
        trader = AutomatedTrader()
        trader.start_automated_trading()
