"""
Portfolio Manager for capital allocation and position management
"""

import logging
from typing import Dict, Any
from datetime import datetime

from ..database.database import db_manager

logger = logging.getLogger(__name__)

class PortfolioManager:
    """Manages portfolio capital allocation and position limits"""
    
    def __init__(self):
        self.liquid_capital_stocks = 70000.0  # $70k para stocks (70% of $100k)
        self.liquid_capital_crypto = 30000.0  # $30k para crypto (30% of $100k)
        self.invested_capital_stocks = 0.0
        self.invested_capital_crypto = 0.0
        self.total_pnl_stocks = 0.0
        self.total_pnl_crypto = 0.0
        self.max_positions_stocks = 8
        self.max_positions_crypto = 6
        
        # Load current state from database if exists
        self._load_portfolio_state()
        
    def _load_portfolio_state(self):
        """Load portfolio state from database"""
        try:
            # Get latest portfolio state
            result = db_manager.execute_query("""
                SELECT * FROM portfolio_state 
                ORDER BY created_at DESC 
                LIMIT 1
            """)
            
            if result:
                state = result[0]
                self.liquid_capital_stocks = state.get('liquid_capital_stocks', 70000.0)
                self.liquid_capital_crypto = state.get('liquid_capital_crypto', 30000.0)
                self.invested_capital_stocks = state.get('invested_capital_stocks', 0.0)
                self.invested_capital_crypto = state.get('invested_capital_crypto', 0.0)
                self.total_pnl_stocks = state.get('total_pnl_stocks', 0.0)
                self.total_pnl_crypto = state.get('total_pnl_crypto', 0.0)
                
                logger.info(f"Loaded portfolio state - Stocks: ${self.liquid_capital_stocks:.2f}, Crypto: ${self.liquid_capital_crypto:.2f}")
            else:
                # First time - save initial state
                self._save_portfolio_state()
                logger.info("Initialized portfolio with default values")
                
        except Exception as e:
            logger.warning(f"Could not load portfolio state: {e}")
            # Continue with default values
            
    def _save_portfolio_state(self):
        """Save current portfolio state to database"""
        try:
            current_positions_stocks = self.get_open_positions_count('stock')
            current_positions_crypto = self.get_open_positions_count('crypto')
            
            db_manager.execute_update("""
                INSERT INTO portfolio_state (
                    date, liquid_capital_stocks, liquid_capital_crypto,
                    invested_capital_stocks, invested_capital_crypto,
                    total_pnl_stocks, total_pnl_crypto,
                    total_positions_stocks, total_positions_crypto
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                self.liquid_capital_stocks,
                self.liquid_capital_crypto,
                self.invested_capital_stocks,
                self.invested_capital_crypto,
                self.total_pnl_stocks,
                self.total_pnl_crypto,
                current_positions_stocks,
                current_positions_crypto
            ))
            
        except Exception as e:
            logger.error(f"Failed to save portfolio state: {e}")
    
    def get_open_positions_count(self, asset_type: str) -> int:
        """Get count of open positions by asset type"""
        try:
            result = db_manager.execute_query("""
                SELECT COUNT(*) as count FROM positions 
                WHERE source = 'autotrader' AND type = ?
            """, (asset_type,))
            
            return result[0]['count'] if result else 0
            
        except Exception as e:
            logger.error(f"Error getting positions count: {e}")
            return 0
        
    def get_threshold_multiplier(self, asset_type: str) -> float:
        """Threshold adaptativos basado en posiciones abiertas"""
        current_positions = self.get_open_positions_count(asset_type)
        max_positions = self.max_positions_stocks if asset_type == 'stock' else self.max_positions_crypto
        
        if current_positions == 0:
            return 0.7  # Más agresivo sin posiciones
        elif current_positions >= (max_positions - 2):
            return 1.5  # Más selectivo cerca del límite
        else:
            return 1.0  # Normal
    
    def can_open_position(self, asset_type: str, required_capital: float) -> bool:
        """Verificar si se puede abrir nueva posición"""
        if asset_type == 'stock':
            return (self.liquid_capital_stocks >= required_capital and 
                   self.get_open_positions_count('stock') < self.max_positions_stocks)
        else:
            return (self.liquid_capital_crypto >= required_capital and 
                   self.get_open_positions_count('crypto') < self.max_positions_crypto)
    
    def get_position_size(self, asset_type: str, confidence: float) -> float:
        """Calculate position size based on confidence and available capital"""
        if asset_type == 'stock':
            base_capital = self.liquid_capital_stocks * 0.2  # 20% max per position
        else:
            base_capital = self.liquid_capital_crypto * 0.15  # 15% max per position
            
        # Adjust by confidence (0.5 to 1.0 multiplier)
        confidence_multiplier = 0.5 + (confidence / 100) * 0.5
        
        return base_capital * confidence_multiplier
    
    def execute_buy(self, symbol: str, price: float, quantity: float, asset_type: str) -> bool:
        """Ejecutar compra y actualizar capital"""
        try:
            total_cost = price * quantity
            
            if not self.can_open_position(asset_type, total_cost):
                logger.warning(f"Cannot open position for {symbol}: insufficient capital or max positions reached")
                return False
                
            if asset_type == 'stock':
                self.liquid_capital_stocks -= total_cost
                self.invested_capital_stocks += total_cost
            else:
                self.liquid_capital_crypto -= total_cost
                self.invested_capital_crypto += total_cost
                
            # Save updated state
            self._save_portfolio_state()
            
            logger.info(f"Executed BUY: {symbol} - {quantity:.4f} @ ${price:.2f} (Total: ${total_cost:.2f})")
            return True
            
        except Exception as e:
            logger.error(f"Error executing buy for {symbol}: {e}")
            return False
        
    def execute_sell(self, symbol: str, price: float, quantity: float, asset_type: str, pnl: float) -> bool:
        """Ejecutar venta y actualizar capital"""
        try:
            total_proceeds = price * quantity
            original_investment = total_proceeds - pnl
            
            if asset_type == 'stock':
                self.liquid_capital_stocks += total_proceeds
                self.invested_capital_stocks -= original_investment
                self.total_pnl_stocks += pnl
            else:
                self.liquid_capital_crypto += total_proceeds  
                self.invested_capital_crypto -= original_investment
                self.total_pnl_crypto += pnl
                
            # Save updated state
            self._save_portfolio_state()
            
            logger.info(f"Executed SELL: {symbol} - {quantity:.4f} @ ${price:.2f} (P&L: ${pnl:.2f})")
            return True
            
        except Exception as e:
            logger.error(f"Error executing sell for {symbol}: {e}")
            return False
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get complete portfolio summary"""
        current_positions_stocks = self.get_open_positions_count('stock')
        current_positions_crypto = self.get_open_positions_count('crypto')
        
        # Calculate total values
        total_liquid = self.liquid_capital_stocks + self.liquid_capital_crypto
        total_invested = self.invested_capital_stocks + self.invested_capital_crypto
        total_pnl = self.total_pnl_stocks + self.total_pnl_crypto
        total_portfolio_value = total_liquid + total_invested
        
        return {
            "stocks": {
                "liquid_capital": self.liquid_capital_stocks,
                "invested_capital": self.invested_capital_stocks,
                "total_pnl": self.total_pnl_stocks,
                "current_positions": current_positions_stocks,
                "max_positions": self.max_positions_stocks,
                "utilization_percent": (current_positions_stocks / self.max_positions_stocks) * 100
            },
            "crypto": {
                "liquid_capital": self.liquid_capital_crypto,
                "invested_capital": self.invested_capital_crypto,
                "total_pnl": self.total_pnl_crypto,
                "current_positions": current_positions_crypto,
                "max_positions": self.max_positions_crypto,
                "utilization_percent": (current_positions_crypto / self.max_positions_crypto) * 100
            },
            "totals": {
                "total_liquid": total_liquid,
                "total_invested": total_invested,
                "total_pnl": total_pnl,
                "total_portfolio_value": total_portfolio_value,
                "total_positions": current_positions_stocks + current_positions_crypto,
                "roi_percent": (total_pnl / (100000)) * 100 if total_pnl != 0 else 0  # $100k initial capital
            }
        }
        
    def reset_portfolio(self):
        """Reset portfolio to initial state"""
        try:
            self.liquid_capital_stocks = 70000.0
            self.liquid_capital_crypto = 30000.0
            self.invested_capital_stocks = 0.0
            self.invested_capital_crypto = 0.0
            self.total_pnl_stocks = 0.0
            self.total_pnl_crypto = 0.0
            
            # Save reset state
            self._save_portfolio_state()
            
            logger.info("Portfolio reset to initial state")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting portfolio: {e}")
            return False

# Global portfolio manager instance
portfolio_manager = PortfolioManager()