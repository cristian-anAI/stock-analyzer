#!/usr/bin/env python3
"""
Position Manager - Sistema de Gestión de Posiciones
Integrado con StockDataCollector para decisiones automatizadas
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
import json
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import traceback
from database_manager import DatabaseManager

class PositionDecision(Enum):
    HOLD_STRONG = "HOLD_STRONG"
    HOLD_CAUTIOUS = "HOLD_CAUTIOUS"
    CONSIDER_SELL = "CONSIDER_SELL"
    SELL_IMMEDIATELY = "SELL_IMMEDIATELY"
    TAKE_PARTIAL_PROFIT = "TAKE_PARTIAL_PROFIT"

@dataclass
class Position:
    """Estructura de datos para una posición abierta"""
    symbol: str
    entry_date: str
    entry_price: float
    quantity: int
    stop_loss: float
    take_profit: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0
    days_held: int = 0
    trailing_stop: float = 0.0
    partial_sold: bool = False
    notes: str = ""
    position_type: str = "AUTO"  # "AUTO" o "MANUAL"

class PositionManager:
    def get_portfolio_summary(self):
        """Devuelve resumen del portfolio: total de posiciones y P&L total"""
        total_positions = len(self.positions)
        total_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        return {
            'total_positions': total_positions,
            'total_pnl': total_pnl
        }
    def __init__(self, stock_collector):
        """Initialize con referencia al StockDataCollector y DB"""
        self.stock_collector = stock_collector
        self.positions: Dict[str, Position] = {}
        self.position_history: List[Dict] = []
        self.alerts: List[Dict] = []
        try:
            self.db_manager = DatabaseManager()
        except Exception as e:
            print(f"[DB WARNING] No se pudo inicializar DatabaseManager: {e}")
            self.db_manager = None
        self._last_snapshot_date = None
        self.load_positions_from_db()
        # Backup diario automático
        try:
            if self.db_manager:
                self.db_manager.daily_backup()
        except Exception as e:
            print(f"[DB WARNING] Backup diario fallido: {e}")
        
    def open_position(self, symbol: str, entry_price: float, quantity: int, 
                     stop_loss_percent: float = 5.0, take_profit_percent: float = 15.0, position_type: str = "AUTO") -> bool:
        """Abre una nueva posición y la guarda en la DB. Solo AUTO puede ser gestionada automáticamente."""
        if symbol in self.positions:
            print(f" Ya existe una posición abierta para {symbol}")
            return False
        stop_loss = entry_price * (1 - stop_loss_percent / 100)
        take_profit = entry_price * (1 + take_profit_percent / 100)
        position = Position(
            symbol=symbol,
            entry_date=datetime.now().isoformat()[:10],
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop=stop_loss,
            position_type=position_type
        )
        self.positions[symbol] = position
        try:
            if self.db_manager:
                self.db_manager.save_position(asdict(position))
        except Exception as e:
            print(f"[DB WARNING] No se pudo guardar posición: {e}")
        print(f" Posición abierta: {symbol} | {quantity} acciones @ ${entry_price} | Tipo: {position_type}")
        return True
    def add_real_position(self, symbol: str, entry_price: float, quantity: int, entry_date: str = None):
        """Permite añadir una posición real (MANUAL) al sistema"""
        if not entry_date:
            entry_date = datetime.now().isoformat()[:10]
        return self.open_position(symbol, entry_price, quantity, position_type="MANUAL")

    def convert_manual_to_auto(self, symbol: str):
        """Convierte una posición MANUAL a AUTO para que el sistema la gestione"""
        if symbol in self.positions and self.positions[symbol].position_type == "MANUAL":
            self.positions[symbol].position_type = "AUTO"
            try:
                if self.db_manager:
                    self.db_manager.update_position(asdict(self.positions[symbol]))
            except Exception as e:
                print(f"[DB WARNING] No se pudo convertir a AUTO: {e}")
            print(f"{symbol} ahora es gestionada automáticamente (AUTO)")
        else:
            print(f"No se puede convertir: {symbol} no es MANUAL o no existe.")
    
    def update_position(self, symbol: str, current_price: float) -> None:
        """Actualiza métricas de una posición y la DB, guarda snapshot diario"""
        if symbol not in self.positions:
            return
        position = self.positions[symbol]
        # Solo actualizar automáticamente posiciones AUTO
        if position.position_type == "MANUAL":
            return
        position.current_price = current_price
        # Calcular P&L
        total_value = current_price * position.quantity
        entry_value = position.entry_price * position.quantity
        position.unrealized_pnl = total_value - entry_value
        position.unrealized_pnl_percent = (position.unrealized_pnl / entry_value) * 100
        # Trailing stop
        if position.unrealized_pnl_percent > 3:
            new_trailing = position.entry_price * 0.995
            if new_trailing > position.trailing_stop:
                position.trailing_stop = new_trailing
        # Guardar en DB
        try:
            if self.db_manager:
                self.db_manager.update_position(asdict(position))
        except Exception as e:
            print(f"[DB WARNING] No se pudo actualizar posición: {e}")
        # Snapshot diario (solo una vez por día)
        today_str = date.today().isoformat()
        if self._last_snapshot_date != today_str:
            try:
                if self.db_manager:
                    total_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
                    self.db_manager.save_daily_snapshot(today_str, total_pnl, len(self.positions))
                    self._last_snapshot_date = today_str
            except Exception as e:
                print(f"[DB WARNING] No se pudo guardar snapshot diario: {e}")
    
    def analyze_position_decision(self, symbol: str) -> Tuple[PositionDecision, List[str]]:
        """Analiza una posición y decide acción"""
        if symbol not in self.positions:
            return PositionDecision.HOLD_CAUTIOUS, ["Posición no encontrada"]
        
        position = self.positions[symbol]
        stock_data = self.stock_collector.get_stock_data(symbol)
        
        if 'error' in stock_data:
            return PositionDecision.HOLD_CAUTIOUS, ["Error obteniendo datos"]
        
        analysis = self.stock_collector.analyze_stock_potential(stock_data)
        tech_indicators = stock_data.get('technical_indicators', {})
        
        rsi = tech_indicators.get('rsi')
        reasons = []
        score = 0
        
        # Stop Loss Hit
        if position.current_price <= position.trailing_stop:
            return PositionDecision.SELL_IMMEDIATELY, ["Stop loss activado"]
        
        # Take Profit Hit  
        if position.current_price >= position.take_profit:
            return PositionDecision.SELL_IMMEDIATELY, ["Take profit alcanzado"]
        
        # Profit Parcial >7%
        if position.unrealized_pnl_percent > 7 and not position.partial_sold:
            return PositionDecision.TAKE_PARTIAL_PROFIT, ["Ganancia >7% - vender 50%"]
        
        # Análisis técnico
        if rsi and rsi > 80:
            score -= 3
            reasons.append(f"RSI extremo: {rsi:.1f}")
        elif rsi and rsi > 75:
            score -= 1
            reasons.append(f"RSI alto: {rsi:.1f}")
        elif rsi and 30 <= rsi <= 70:
            score += 2
            reasons.append(f"RSI saludable: {rsi:.1f}")
        
        if analysis.get('classification') in ['BULLISH', 'NEUTRAL_POSITIVE']:
            score += 2
            reasons.append("Señales técnicas positivas")
        
        # Decisión final
        if score <= -4:
            return PositionDecision.SELL_IMMEDIATELY, reasons
        elif score <= -2:
            return PositionDecision.CONSIDER_SELL, reasons
        elif score >= 3:
            return PositionDecision.HOLD_STRONG, reasons
        else:
            return PositionDecision.HOLD_CAUTIOUS, reasons
    
    def close_position(self, symbol: str, reason: str = "Manual close"):
        """Cierra una posición y la mueve a trades_history en la DB. Solo AUTO puede ser cerrada automáticamente."""
        if symbol not in self.positions:
            return None
        if self.positions[symbol].position_type == "MANUAL":
            print(f"[SAFETY] No se puede cerrar automáticamente una posición MANUAL: {symbol}")
            return None
        position = self.positions[symbol]
        result = {
            'symbol': symbol,
            'entry_date': position.entry_date,
            'exit_date': datetime.now().isoformat()[:10],
            'entry_price': position.entry_price,
            'exit_price': position.current_price,
            'quantity': position.quantity,
            'pnl': position.unrealized_pnl,
            'pnl_percent': position.unrealized_pnl_percent,
            'reason': reason
        }
        self.position_history.append(result)
        try:
            if self.db_manager:
                self.db_manager.save_trade_history(result)
                self.db_manager.delete_position(symbol)
        except Exception as e:
            print(f"[DB WARNING] No se pudo mover a trades_history: {e}")
        del self.positions[symbol]
        print(f" Posición cerrada: {symbol} | P&L: ${position.unrealized_pnl:.2f}")
        return result
    def load_positions_from_db(self):
        """Carga posiciones desde la DB al iniciar"""
        if not self.db_manager:
            return
        try:
            db_positions = self.db_manager.load_positions()
            for pos in db_positions:
                # Validar que el precio no sea muy antiguo (máx 3 días)
                entry_date = pos.get('entry_date', '')
                try:
                    entry_dt = datetime.strptime(entry_date, "%Y-%m-%d")
                    if (datetime.now() - entry_dt).days > 3:
                        continue
                except Exception:
                    continue
                # Reconstruir Position
                self.positions[pos['symbol']] = Position(
                    symbol=pos['symbol'],
                    entry_date=pos['entry_date'],
                    entry_price=pos['entry_price'],
                    quantity=pos['quantity'],
                    stop_loss=pos['stop_loss'],
                    take_profit=pos['take_profit'],
                    current_price=pos.get('current_price', 0),
                    unrealized_pnl=pos.get('unrealized_pnl', 0),
                    unrealized_pnl_percent=pos.get('unrealized_pnl_percent', 0),
                    days_held=pos.get('days_held', 0),
                    trailing_stop=pos.get('trailing_stop', 0),
                    partial_sold=bool(pos.get('partial_sold', 0)),
                    notes=pos.get('notes', ''),
                    position_type=pos.get('position_type', 'AUTO')
                )
        except Exception as e:
            print(f"[DB WARNING] No se pudieron cargar posiciones: {e}")
    def export_trades_history_csv(self, filename: str = None):
        """Exporta el historial de trades a CSV"""
        if not self.db_manager:
            print("[DB WARNING] DatabaseManager no disponible")
            return None
        try:
            return self.db_manager.export_trades_history_csv(filename)
        except Exception as e:
            print(f"[DB WARNING] No se pudo exportar trades_history: {e}")
            return None
    
    def print_portfolio_dashboard(self):
        """Dashboard separado para posiciones MANUAL y AUTO"""
        print(f"\n{'='*60}")
        print(" PORTFOLIO DASHBOARD")
        print(f"{'='*60}")
        manual = [p for p in self.positions.values() if p.position_type == "MANUAL"]
        auto = [p for p in self.positions.values() if p.position_type == "AUTO"]
        print(f"\n[MANUAL POSITIONS] ({len(manual)})")
        for pos in manual:
            print(f"{pos.symbol}: ${pos.current_price:.2f} | P&L: ${pos.unrealized_pnl:.2f} ({pos.unrealized_pnl_percent:+.1f}%)")
        print(f"\n[AUTO POSITIONS] ({len(auto)})")
        for pos in auto:
            print(f"{pos.symbol}: ${pos.current_price:.2f} | P&L: ${pos.unrealized_pnl:.2f} ({pos.unrealized_pnl_percent:+.1f}%)")
        print(f"\nP&L MANUAL: ${sum(p.unrealized_pnl for p in manual):.2f} | P&L AUTO: ${sum(p.unrealized_pnl for p in auto):.2f}")
