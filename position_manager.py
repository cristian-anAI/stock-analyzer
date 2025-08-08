#!/usr/bin/env python3
"""
Position Manager - Sistema de Gestión de Posiciones
Integrado con StockDataCollector para decisiones automatizadas
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd

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

class PositionManager:
    def __init__(self, stock_collector):
        """Initialize con referencia al StockDataCollector"""
        self.stock_collector = stock_collector
        self.positions: Dict[str, Position] = {}
        self.position_history: List[Dict] = []
        self.alerts: List[Dict] = []
        
    def open_position(self, symbol: str, entry_price: float, quantity: int, 
                     stop_loss_percent: float = 5.0, take_profit_percent: float = 15.0) -> bool:
        """Abre una nueva posición"""
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
            trailing_stop=stop_loss
        )
        
        self.positions[symbol] = position
        print(f" Posición abierta: {symbol} | {quantity} acciones @ ${entry_price}")
        return True
    
    def update_position(self, symbol: str, current_price: float) -> None:
        """Actualiza métricas de una posición"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
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
        """Cierra una posición"""
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        result = {
            'symbol': symbol,
            'pnl': position.unrealized_pnl,
            'pnl_percent': position.unrealized_pnl_percent,
            'reason': reason
        }
        
        self.position_history.append(result)
        del self.positions[symbol]
        print(f" Posición cerrada: {symbol} | P&L: ${position.unrealized_pnl:.2f}")
        return result
    
    def print_portfolio_dashboard(self):
        """Dashboard del portfolio"""
        print(f"\n{'='*60}")
        print(" PORTFOLIO DASHBOARD")
        print(f"{'='*60}")
        
        if not self.positions:
            print("No hay posiciones activas")
            return
        
        total_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        print(f" Posiciones activas: {len(self.positions)}")
        print(f" P&L Total: ${total_pnl:.2f}")
        
        for symbol, pos in self.positions.items():
            print(f"\n{symbol}: ${pos.current_price:.2f} | P&L: ${pos.unrealized_pnl:.2f} ({pos.unrealized_pnl_percent:+.1f}%)")
