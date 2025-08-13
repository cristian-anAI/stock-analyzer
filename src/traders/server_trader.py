#!/usr/bin/env python3
"""
Server Trader - Versión servidor 24/7 con logging completo
"""

import logging
import os
import json
import time
from datetime import datetime
from .automated_trader import AutomatedTrader
import threading
import traceback

class ServerTrader:
    def __init__(self):
        self.setup_logging()
        self.setup_directories()
        self.trader = None
        self.running = False
        self.start_time = datetime.now()
        
    def setup_directories(self):
        """Create necessary directories"""
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data', exist_ok=True)
        os.makedirs('web', exist_ok=True)
        
    def setup_logging(self):
        """Setup comprehensive logging system"""
        # Create logs directory
        os.makedirs('logs', exist_ok=True)
        
        # Main logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'logs/trader_{datetime.now().strftime("%Y%m%d")}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Trading specific logger
        self.trade_logger = logging.getLogger('trading')
        trade_handler = logging.FileHandler(f'logs/trades_{datetime.now().strftime("%Y%m%d")}.log')
        trade_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        self.trade_logger.addHandler(trade_handler)
        self.trade_logger.setLevel(logging.INFO)
        
        # Positions logger
        self.position_logger = logging.getLogger('positions')
        pos_handler = logging.FileHandler(f'logs/positions_{datetime.now().strftime("%Y%m%d")}.log')
        pos_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        self.position_logger.addHandler(pos_handler)
        self.position_logger.setLevel(logging.INFO)
        
        # Error logger
        self.error_logger = logging.getLogger('errors')
        error_handler = logging.FileHandler(f'logs/errors_{datetime.now().strftime("%Y%m%d")}.log')
        error_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.error_logger.addHandler(error_handler)
        self.error_logger.setLevel(logging.ERROR)
        
        self.logger.info("=== SERVER TRADER INICIADO ===")
        self.logger.info(f"Directorio de trabajo: {os.getcwd()}")
        
    def log_trade_event(self, event_type, symbol, message, data=None):
        """Log trading events with structured data"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'symbol': symbol,
            'message': message,
            'data': data or {}
        }
        self.trade_logger.info(json.dumps(event))
        
    def log_position_update(self, symbol, position_data):
        """Log position updates"""
        update = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'data': position_data
        }
        self.position_logger.info(json.dumps(update))
        
    def create_status_file(self):
        """Create status file for web dashboard"""
        try:
            status = {
                'timestamp': datetime.now().isoformat(),
                'uptime_hours': (datetime.now() - self.start_time).total_seconds() / 3600,
                'running': self.running,
                'positions': {},
                'total_pnl': 0
            }
            
            if self.trader and self.trader.position_manager:
                for symbol, pos in self.trader.position_manager.positions.items():
                    is_manual = self.trader.is_manual_position(symbol)
                    status['positions'][symbol] = {
                        'type': 'MANUAL' if is_manual else 'AUTO',
                        'quantity': pos.quantity,
                        'entry_price': pos.entry_price,
                        'current_price': getattr(pos, 'current_price', pos.entry_price),
                        'pnl_percent': pos.unrealized_pnl_percent,
                        'pnl_usd': pos.unrealized_pnl
                    }
                
                status['total_pnl'] = sum(pos.unrealized_pnl for pos in self.trader.position_manager.positions.values())
            
            with open('web/status.json', 'w') as f:
                json.dump(status, f, indent=2)
                
        except Exception as e:
            self.error_logger.error(f"Error creating status file: {e}")
            
    def start_server_trading(self):
        """Start 24/7 server trading with recovery"""
        self.running = True
        retry_count = 0
        max_retries = 5
        
        while self.running:
            try:
                self.logger.info(f"Iniciando trader (intento {retry_count + 1})")
                
                # Create trader instance
                self.trader = AutomatedTrader(max_positions=8, max_investment_per_stock=5000)
                
                # Custom logging for trader events
                self.override_trader_logging()
                
                # Start trading
                self.trader.start_automated_trading()
                
                retry_count = 0  # Reset on successful run
                
            except KeyboardInterrupt:
                self.logger.info("Detenido por usuario (Ctrl+C)")
                self.running = False
                break
                
            except Exception as e:
                retry_count += 1
                self.error_logger.error(f"Error en trader: {e}")
                self.error_logger.error(f"Traceback: {traceback.format_exc()}")
                
                if retry_count >= max_retries:
                    self.logger.error(f"Máximo de reintentos alcanzado ({max_retries}). Deteniendo...")
                    self.running = False
                    break
                
                wait_time = min(60 * retry_count, 300)  # Max 5 minutes
                self.logger.info(f"Reintentando en {wait_time} segundos...")
                time.sleep(wait_time)
        
        self.logger.info("=== SERVER TRADER DETENIDO ===")
    
    def override_trader_logging(self):
        """Override trader methods to add logging"""
        if not self.trader:
            return
            
        # Store original methods
        original_open_position = self.trader.position_manager.open_position
        original_close_position = self.trader.position_manager.close_position
        original_update_position = self.trader.position_manager.update_position
        original_send_alert = self.trader.send_alert
        
        def logged_open_position(symbol, entry_price, quantity, **kwargs):
            result = original_open_position(symbol, entry_price, quantity, **kwargs)
            if result:
                investment = entry_price * quantity
                self.log_trade_event('POSITION_OPENED', symbol, 
                    f"Opened position: {quantity:.8f} @ ${entry_price:.4f}", 
                    {'investment': investment, 'kwargs': kwargs})
            return result
        
        def logged_close_position(symbol, reason=""):
            if symbol in self.trader.position_manager.positions:
                pos = self.trader.position_manager.positions[symbol]
                pnl = pos.unrealized_pnl
                pnl_pct = pos.unrealized_pnl_percent
                self.log_trade_event('POSITION_CLOSED', symbol,
                    f"Closed position: P&L {pnl_pct:+.2f}% (${pnl:+.2f}). Reason: {reason}",
                    {'pnl': pnl, 'pnl_percent': pnl_pct, 'reason': reason})
            return original_close_position(symbol, reason)
        
        def logged_update_position(symbol, current_price):
            result = original_update_position(symbol, current_price)
            if symbol in self.trader.position_manager.positions:
                pos = self.trader.position_manager.positions[symbol]
                self.log_position_update(symbol, {
                    'current_price': current_price,
                    'pnl_percent': pos.unrealized_pnl_percent,
                    'pnl_usd': pos.unrealized_pnl
                })
            return result
        
        def logged_send_alert(alert_type, symbol, message):
            self.log_trade_event('ALERT', symbol, f"{alert_type}: {message}", 
                {'alert_type': alert_type})
            return original_send_alert(alert_type, symbol, message)
        
        # Replace methods
        self.trader.position_manager.open_position = logged_open_position
        self.trader.position_manager.close_position = logged_close_position  
        self.trader.position_manager.update_position = logged_update_position
        self.trader.send_alert = logged_send_alert
        
    def start_status_updater(self):
        """Start background thread to update status file"""
        def update_loop():
            while self.running:
                try:
                    self.create_status_file()
                    time.sleep(30)  # Update every 30 seconds
                except Exception as e:
                    self.error_logger.error(f"Error updating status: {e}")
                    time.sleep(60)
        
        status_thread = threading.Thread(target=update_loop, daemon=True)
        status_thread.start()
        self.logger.info("Status updater iniciado")

def main():
    print("[SERVER] INICIANDO SERVER TRADER 24/7")
    print("=" * 50)
    print("Para detener: Ctrl+C")
    print("Logs en: ./logs/")
    print("Status web en: ./web/status.json")
    print("=" * 50)
    
    server = ServerTrader()
    
    # Start status updater
    server.start_status_updater()
    
    # Start main trading loop
    server.start_server_trading()

if __name__ == "__main__":
    main()