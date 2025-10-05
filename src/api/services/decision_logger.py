"""
Decision Logger Service - Tracks all autotrader buy/sell decisions for transparency
Provides complete visibility into why trades are executed or not executed
"""

import logging
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..database.database import db_manager

logger = logging.getLogger(__name__)

class DecisionLogger:
    """Service for logging all trading decisions with full context"""

    def __init__(self):
        self.current_cycle_id = None

    def start_cycle(self) -> str:
        """Start a new trading cycle and return cycle ID"""
        self.current_cycle_id = str(uuid.uuid4())
        return self.current_cycle_id

    def log_buy_evaluation(
        self,
        symbol: str,
        asset_type: str,
        score: float,
        current_price: float,
        action_taken: str,  # 'buy' or 'none'
        filters_passed: Dict[str, bool],
        filters_failed: Dict[str, bool],
        scoring_breakdown: Dict[str, Any],
        buy_threshold: float,
        confidence: Optional[float] = None,
        position_size: Optional[float] = None,
        market_status: Optional[str] = None,
        portfolio_status: Optional[Dict] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Log a buy signal evaluation

        Args:
            symbol: Stock/crypto symbol
            asset_type: 'stock' or 'crypto'
            score: Current score
            current_price: Current asset price
            action_taken: 'buy' if executed, 'none' if not
            filters_passed: Dict of filters that passed (e.g. {'volatility': True})
            filters_failed: Dict of filters that failed (e.g. {'monthly_filter': False})
            scoring_breakdown: Complete scoring breakdown from scoring service
            buy_threshold: Buy threshold used
            confidence: Confidence level (0-100)
            position_size: Position size if buy executed
            market_status: Current market status
            portfolio_status: Current portfolio snapshot
            notes: Additional notes

        Returns:
            Log entry ID
        """
        try:
            decision_type = 'buy_signal' if action_taken == 'buy' else 'no_buy'

            log_id = db_manager.execute_insert("""
                INSERT INTO decision_logs (
                    symbol, asset_type, decision_type, action_taken,
                    score, current_price,
                    filters_passed, filters_failed, scoring_breakdown,
                    buy_threshold, confidence, position_size,
                    market_status, portfolio_status,
                    cycle_id, timestamp, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, asset_type, decision_type, action_taken,
                score, current_price,
                json.dumps(filters_passed), json.dumps(filters_failed), json.dumps(scoring_breakdown),
                buy_threshold, confidence, position_size,
                market_status, json.dumps(portfolio_status) if portfolio_status else None,
                self.current_cycle_id, datetime.now().isoformat(), notes
            ))

            if action_taken == 'none':
                # Log why we didn't buy
                failed_reasons = [f"{k}: {v}" for k, v in filters_failed.items() if not v]
                logger.info(f"❌ NO BUY {symbol}: score={score:.2f}, failed={failed_reasons}")
            else:
                logger.info(f"✅ BUY {symbol}: score={score:.2f}, price=${current_price:.2f}")

            return log_id

        except Exception as e:
            logger.error(f"Error logging buy evaluation for {symbol}: {e}")
            return None

    def log_sell_evaluation(
        self,
        symbol: str,
        asset_type: str,
        score: float,
        current_price: float,
        action_taken: str,  # 'sell' or 'none'
        entry_price: float,
        days_held: int,
        pnl_percent: float,
        exit_reason: Optional[str] = None,
        exit_details: Optional[Dict] = None,
        sell_threshold: Optional[float] = None,
        trailing_stop_price: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
        market_status: Optional[str] = None,
        portfolio_status: Optional[Dict] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Log a sell signal evaluation

        Args:
            symbol: Stock/crypto symbol
            asset_type: 'stock' or 'crypto'
            score: Current score
            current_price: Current asset price
            action_taken: 'sell' if executed, 'none' if holding
            entry_price: Entry price of position
            days_held: Days position has been held
            pnl_percent: Current P&L percentage
            exit_reason: Reason for exit (if selling)
            exit_details: Detailed exit analysis
            sell_threshold: Sell threshold used
            trailing_stop_price: Current trailing stop price
            stop_loss_price: Stop loss price
            take_profit_price: Take profit price
            market_status: Current market status
            portfolio_status: Current portfolio snapshot
            notes: Additional notes

        Returns:
            Log entry ID
        """
        try:
            decision_type = 'sell_signal' if action_taken == 'sell' else 'no_sell'

            log_id = db_manager.execute_insert("""
                INSERT INTO decision_logs (
                    symbol, asset_type, decision_type, action_taken,
                    score, current_price,
                    sell_threshold, entry_price, pnl_percent, days_held,
                    trailing_stop_price, stop_loss_price, take_profit_price,
                    exit_reason, exit_details,
                    market_status, portfolio_status,
                    cycle_id, timestamp, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, asset_type, decision_type, action_taken,
                score, current_price,
                sell_threshold, entry_price, pnl_percent, days_held,
                trailing_stop_price, stop_loss_price, take_profit_price,
                exit_reason, json.dumps(exit_details) if exit_details else None,
                market_status, json.dumps(portfolio_status) if portfolio_status else None,
                self.current_cycle_id, datetime.now().isoformat(), notes
            ))

            if action_taken == 'sell':
                logger.info(f"✅ SELL {symbol}: {exit_reason}, P&L={pnl_percent:.2f}%, held={days_held}d")
            else:
                logger.info(f"⏸️  HOLD {symbol}: score={score:.2f}, P&L={pnl_percent:.2f}%, held={days_held}d")

            return log_id

        except Exception as e:
            logger.error(f"Error logging sell evaluation for {symbol}: {e}")
            return None

    def get_recent_decisions(self, limit: int = 50, decision_type: Optional[str] = None) -> List[Dict]:
        """
        Get recent trading decisions

        Args:
            limit: Maximum number of decisions to return
            decision_type: Filter by type ('buy_signal', 'sell_signal', 'no_buy', 'no_sell')

        Returns:
            List of decision log entries
        """
        try:
            query = """
                SELECT * FROM decision_logs
                WHERE 1=1
            """
            params = []

            if decision_type:
                query += " AND decision_type = ?"
                params.append(decision_type)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            results = db_manager.execute_query(query, tuple(params))

            # Parse JSON fields
            for result in results:
                if result.get('filters_passed'):
                    result['filters_passed'] = json.loads(result['filters_passed'])
                if result.get('filters_failed'):
                    result['filters_failed'] = json.loads(result['filters_failed'])
                if result.get('scoring_breakdown'):
                    result['scoring_breakdown'] = json.loads(result['scoring_breakdown'])
                if result.get('exit_details'):
                    result['exit_details'] = json.loads(result['exit_details'])
                if result.get('portfolio_status'):
                    result['portfolio_status'] = json.loads(result['portfolio_status'])

            return results

        except Exception as e:
            logger.error(f"Error getting recent decisions: {e}")
            return []

    def get_decisions_by_cycle(self, cycle_id: str) -> List[Dict]:
        """Get all decisions from a specific trading cycle"""
        try:
            results = db_manager.execute_query("""
                SELECT * FROM decision_logs
                WHERE cycle_id = ?
                ORDER BY timestamp ASC
            """, (cycle_id,))

            # Parse JSON fields
            for result in results:
                if result.get('filters_passed'):
                    result['filters_passed'] = json.loads(result['filters_passed'])
                if result.get('filters_failed'):
                    result['filters_failed'] = json.loads(result['filters_failed'])
                if result.get('scoring_breakdown'):
                    result['scoring_breakdown'] = json.loads(result['scoring_breakdown'])
                if result.get('exit_details'):
                    result['exit_details'] = json.loads(result['exit_details'])
                if result.get('portfolio_status'):
                    result['portfolio_status'] = json.loads(result['portfolio_status'])

            return results

        except Exception as e:
            logger.error(f"Error getting decisions by cycle: {e}")
            return []

    def get_symbol_decision_history(self, symbol: str, limit: int = 20) -> List[Dict]:
        """Get decision history for a specific symbol"""
        try:
            results = db_manager.execute_query("""
                SELECT * FROM decision_logs
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (symbol, limit))

            # Parse JSON fields
            for result in results:
                if result.get('filters_passed'):
                    result['filters_passed'] = json.loads(result['filters_passed'])
                if result.get('filters_failed'):
                    result['filters_failed'] = json.loads(result['filters_failed'])
                if result.get('scoring_breakdown'):
                    result['scoring_breakdown'] = json.loads(result['scoring_breakdown'])
                if result.get('exit_details'):
                    result['exit_details'] = json.loads(result['exit_details'])
                if result.get('portfolio_status'):
                    result['portfolio_status'] = json.loads(result['portfolio_status'])

            return results

        except Exception as e:
            logger.error(f"Error getting symbol decision history: {e}")
            return []

    def get_decision_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get statistics about recent decisions"""
        try:
            cutoff_time = datetime.now().replace(hour=datetime.now().hour - hours).isoformat()

            # Count by decision type
            type_counts = db_manager.execute_query("""
                SELECT decision_type, action_taken, COUNT(*) as count
                FROM decision_logs
                WHERE timestamp >= ?
                GROUP BY decision_type, action_taken
            """, (cutoff_time,))

            # Get average scores for buys vs no-buys
            score_stats = db_manager.execute_query("""
                SELECT
                    decision_type,
                    AVG(score) as avg_score,
                    MIN(score) as min_score,
                    MAX(score) as max_score
                FROM decision_logs
                WHERE timestamp >= ? AND decision_type IN ('buy_signal', 'no_buy')
                GROUP BY decision_type
            """, (cutoff_time,))

            # Most common failure reasons
            # This would require parsing JSON, so we'll keep it simple for now

            return {
                'period_hours': hours,
                'type_counts': [dict(row) for row in type_counts],
                'score_stats': [dict(row) for row in score_stats]
            }

        except Exception as e:
            logger.error(f"Error getting decision stats: {e}")
            return {}

# Global instance
decision_logger = DecisionLogger()
