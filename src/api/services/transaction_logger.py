"""
Unified Transaction Logger
Ensures consistent logging of transactions across autotrader_transactions and portfolio_transactions tables
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from ..database.database import db_manager

logger = logging.getLogger(__name__)

class TransactionLogger:
    """Unified transaction logger for consistent SHORT transaction handling"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def log_transaction(self, 
                       symbol: str, 
                       action: str, 
                       quantity: float, 
                       price: float, 
                       reason: str, 
                       portfolio_type: str = None,
                       source: str = "autotrader") -> bool:
        """
        Log transaction consistently to both tables
        
        Args:
            symbol: Trading symbol (e.g., 'SHIB-USD')
            action: 'buy', 'sell', 'short' - uses CORRECT action names
            quantity: Number of shares/units
            price: Price per unit
            reason: Trading reason/signal
            portfolio_type: 'stocks' or 'crypto' (auto-detected if None)
            source: 'autotrader' or 'manual'
        
        Returns:
            bool: Success status
        """
        try:
            # Auto-detect portfolio type if not provided
            if portfolio_type is None:
                portfolio_type = 'crypto' if '-USD' in symbol else 'stocks'
            
            # Determine if this is a SHORT position based on reason or existing position
            is_short_position = self._is_short_related(symbol, action, reason)
            
            # Log to autotrader_transactions (this table is already correct)
            self._log_autotrader_transaction(symbol, action, quantity, price, reason)
            
            # Log to portfolio_transactions with consistent action mapping
            portfolio_action = self._map_action_for_portfolio(action, is_short_position)
            self._log_portfolio_transaction(
                symbol, portfolio_action, quantity, price, reason, portfolio_type, source
            )
            
            logger.info(f"Transaction logged: {symbol} {action} {quantity} @ {price} (reason: {reason})")
            return True
            
        except Exception as e:
            logger.error(f"Error logging transaction: {e}")
            return False
    
    def _is_short_related(self, symbol: str, action: str, reason: str) -> bool:
        """Check if transaction is SHORT-related"""
        if action == "short":
            return True
        
        if "SHORT" in reason.upper():
            return True
            
        if action == "sell":
            # Check if we have an existing SHORT position for this symbol
            existing_short = db_manager.execute_query(
                "SELECT id FROM positions WHERE symbol = ? AND position_side = 'SHORT'",
                (symbol,)
            )
            return len(existing_short) > 0
            
        return False
    
    def _map_action_for_portfolio(self, action: str, is_short_position: bool) -> str:
        """Map action to portfolio_transactions format"""
        if action == "short":
            return "short"  # Keep as 'short', not 'buy'
        elif action == "sell" and is_short_position:
            return "cover"  # SHORT exit becomes 'cover'
        else:
            return action   # 'buy' and 'sell' stay as-is for LONG positions
    
    def _log_autotrader_transaction(self, symbol: str, action: str, quantity: float, 
                                  price: float, reason: str) -> None:
        """Log to autotrader_transactions table"""
        db_manager.execute_insert(
            """INSERT INTO autotrader_transactions 
               (symbol, action, quantity, price, timestamp, reason)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (symbol, action, quantity, price, datetime.now().isoformat(), reason)
        )
    
    def _log_portfolio_transaction(self, symbol: str, action: str, quantity: float,
                                 price: float, reason: str, portfolio_type: str,
                                 source: str) -> None:
        """Log to portfolio_transactions table"""
        total_amount = quantity * price
        
        # Determine buy_reason vs sell_reason based on action
        buy_reason = None
        sell_reason = None
        
        if action in ['buy', 'short']:
            buy_reason = reason
        elif action in ['sell', 'cover']:
            sell_reason = reason
        
        db_manager.execute_insert(
            """INSERT INTO portfolio_transactions 
               (portfolio_type, symbol, action, quantity, price, total_amount, 
                buy_reason, sell_reason, timestamp, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (portfolio_type, symbol, action, quantity, price, total_amount,
             buy_reason, sell_reason, datetime.now().isoformat(), source)
        )
    
    def get_transaction_summary(self) -> Dict[str, Any]:
        """Get summary of logged transactions"""
        try:
            # Get counts from both tables
            autotrader_count = db_manager.execute_query(
                "SELECT COUNT(*) as count FROM autotrader_transactions"
            )[0]['count']
            
            portfolio_count = db_manager.execute_query(
                "SELECT COUNT(*) as count FROM portfolio_transactions"
            )[0]['count']
            
            # Get action breakdown
            action_counts = db_manager.execute_query(
                """SELECT action, COUNT(*) as count 
                   FROM portfolio_transactions 
                   GROUP BY action"""
            )
            
            return {
                'autotrader_transactions': autotrader_count,
                'portfolio_transactions': portfolio_count,
                'sync_ratio': portfolio_count / autotrader_count if autotrader_count > 0 else 0,
                'action_breakdown': {row['action']: row['count'] for row in action_counts},
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting transaction summary: {e}")
            return {'error': str(e)}

# Global instance
transaction_logger = TransactionLogger()