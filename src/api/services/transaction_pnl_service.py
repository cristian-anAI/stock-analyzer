"""
Transaction P&L Service - Calculate realized P&L for buy/sell pairs
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import uuid

logger = logging.getLogger(__name__)

class TransactionPnLService:
    """Service to calculate and update realized P&L for transaction pairs"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def calculate_and_update_pnl_for_sell(self, sell_transaction_id: int) -> Optional[float]:
        """
        Calculate realized P&L for a sell transaction by finding matching buy
        
        Args:
            sell_transaction_id: ID of the sell transaction
            
        Returns:
            Realized P&L amount or None if no matching buy found
        """
        try:
            with self.db_manager.get_connection() as conn:
                # Get the sell transaction
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT symbol, quantity, price, timestamp, action
                    FROM autotrader_transactions 
                    WHERE id = ?
                """, (sell_transaction_id,))
                
                sell_record = cursor.fetchone()
                if not sell_record or sell_record[4] != 'sell':
                    logger.warning(f"Sell transaction {sell_transaction_id} not found or not a sell")
                    return None
                
                symbol = sell_record[0]
                sell_quantity = sell_record[1] 
                sell_price = sell_record[2]
                sell_timestamp = sell_record[3]
                
                # Find the most recent matching buy transaction
                cursor.execute("""
                    SELECT id, quantity, price, timestamp
                    FROM autotrader_transactions
                    WHERE symbol = ? 
                    AND action = 'buy'
                    AND timestamp <= ?
                    AND (realized_pnl IS NULL OR realized_pnl = 0)
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (symbol, sell_timestamp))
                
                buy_record = cursor.fetchone()
                if not buy_record:
                    logger.warning(f"No matching buy found for sell transaction {sell_transaction_id}")
                    return None
                
                buy_id = buy_record[0]
                buy_quantity = buy_record[1]
                buy_price = buy_record[2]
                buy_timestamp = buy_record[3]
                
                # Calculate P&L (sell_price - buy_price) * quantity
                # Use the smaller of the two quantities in case of partial fills
                quantity_to_calculate = min(sell_quantity, buy_quantity)
                realized_pnl = (sell_price - buy_price) * quantity_to_calculate
                
                # Calculate hold duration
                buy_dt = datetime.fromisoformat(buy_timestamp)
                sell_dt = datetime.fromisoformat(sell_timestamp)
                hold_duration_hours = (sell_dt - buy_dt).total_seconds() / 3600
                
                # Generate position ID to link the transactions
                position_id = f"pos_{symbol}_{buy_dt.strftime('%Y%m%d_%H%M%S')}"
                
                # Update the sell transaction with P&L info
                cursor.execute("""
                    UPDATE autotrader_transactions
                    SET realized_pnl = ?, entry_price = ?, exit_price = ?, 
                        position_id = ?, hold_duration_hours = ?
                    WHERE id = ?
                """, (realized_pnl, buy_price, sell_price, position_id, hold_duration_hours, sell_transaction_id))
                
                # Update the buy transaction with position ID and exit info
                cursor.execute("""
                    UPDATE autotrader_transactions
                    SET position_id = ?, exit_price = ?, hold_duration_hours = ?
                    WHERE id = ?
                """, (position_id, sell_price, hold_duration_hours, buy_id))
                
                conn.commit()
                
                logger.info(f"Calculated P&L for {symbol}: ${realized_pnl:.2f} "
                          f"(held {hold_duration_hours:.1f}h, {buy_price:.2f} -> {sell_price:.2f})")
                
                return realized_pnl
                
        except Exception as e:
            logger.error(f"Error calculating P&L for sell transaction {sell_transaction_id}: {e}")
            return None
    
    def recalculate_all_historical_pnl(self) -> Dict[str, int]:
        """
        Recalculate P&L for all historical sell transactions
        
        Returns:
            Dictionary with counts of processed transactions
        """
        results = {"processed": 0, "updated": 0, "errors": 0}
        
        try:
            with self.db_manager.get_connection() as conn:
                # Get all sell transactions
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, symbol, timestamp
                    FROM autotrader_transactions
                    WHERE action = 'sell'
                    ORDER BY timestamp
                """)
                
                sell_transactions = cursor.fetchall()
                logger.info(f"Found {len(sell_transactions)} sell transactions to process")
                
                for sell_id, symbol, timestamp in sell_transactions:
                    results["processed"] += 1
                    
                    pnl = self.calculate_and_update_pnl_for_sell(sell_id)
                    if pnl is not None:
                        results["updated"] += 1
                    else:
                        results["errors"] += 1
                
                logger.info(f"Historical P&L calculation complete: {results}")
                return results
                
        except Exception as e:
            logger.error(f"Error in historical P&L recalculation: {e}")
            results["errors"] += 1
            return results
    
    def get_pnl_summary(self) -> Dict:
        """
        Get summary of all realized P&L
        
        Returns:
            Dictionary with P&L summary statistics
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get P&L statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(realized_pnl) as total_pnl,
                        AVG(realized_pnl) as avg_pnl,
                        MIN(realized_pnl) as min_pnl,
                        MAX(realized_pnl) as max_pnl,
                        AVG(hold_duration_hours) as avg_hold_hours
                    FROM autotrader_transactions
                    WHERE realized_pnl IS NOT NULL
                """)
                
                stats = cursor.fetchone()
                if not stats:
                    return {"error": "No P&L data found"}
                
                return {
                    "total_trades": stats[0] or 0,
                    "total_pnl": round(stats[1] or 0, 2),
                    "average_pnl": round(stats[2] or 0, 2),
                    "min_pnl": round(stats[3] or 0, 2),
                    "max_pnl": round(stats[4] or 0, 2),
                    "average_hold_hours": round(stats[5] or 0, 1),
                    "average_hold_days": round((stats[5] or 0) / 24, 1)
                }
                
        except Exception as e:
            logger.error(f"Error getting P&L summary: {e}")
            return {"error": str(e)}
    
    def get_transactions_with_pnl(self, limit: int = 50) -> List[Dict]:
        """
        Get recent transactions with P&L information
        
        Args:
            limit: Maximum number of transactions to return
            
        Returns:
            List of transaction dictionaries with P&L data
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        id, symbol, action, quantity, price, timestamp, reason,
                        realized_pnl, entry_price, exit_price, position_id, hold_duration_hours
                    FROM autotrader_transactions
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
                
                transactions = []
                for row in cursor.fetchall():
                    transaction = {
                        "id": row[0],
                        "symbol": row[1],
                        "action": row[2],
                        "quantity": row[3],
                        "price": row[4],
                        "timestamp": row[5],
                        "reason": row[6],
                        "realized_pnl": row[7],
                        "entry_price": row[8],
                        "exit_price": row[9],
                        "position_id": row[10],
                        "hold_duration_hours": row[11]
                    }
                    transactions.append(transaction)
                
                return transactions
                
        except Exception as e:
            logger.error(f"Error getting transactions with P&L: {e}")
            return []

# Global service instance
transaction_pnl_service = None

def get_transaction_pnl_service(db_manager):
    """Get or create the global transaction P&L service instance"""
    global transaction_pnl_service
    if transaction_pnl_service is None:
        transaction_pnl_service = TransactionPnLService(db_manager)
    return transaction_pnl_service