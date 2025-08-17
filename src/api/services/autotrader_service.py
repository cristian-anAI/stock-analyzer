"""
Autotrader service for automated position management
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..database.database import db_manager
from .data_service import DataService
from .scoring_service import ScoringService
from .portfolio_manager import portfolio_manager

logger = logging.getLogger(__name__)

class AutotraderService:
    """Service for automated trading based on scores"""
    
    def __init__(self):
        self.data_service = DataService()
        self.scoring_service = ScoringService()
        
        # Trading parameters
        self.buy_score_threshold = 8  # Buy if score >= 8
        self.sell_score_threshold = 4  # Sell if score <= 4
        self.max_position_value = 10000  # Max value per position in USD
        self.max_total_positions = 20  # Max number of positions
        
    async def run_trading_cycle(self) -> Dict[str, Any]:
        """Run a complete trading cycle"""
        logger.info("Starting autotrader cycle...")
        
        try:
            # Update all market data first
            await self.data_service.update_stocks_data()
            await self.data_service.update_cryptos_data()
            await self.data_service.update_positions_prices()
            
            results = {
                "cycle_start": datetime.now().isoformat(),
                "actions_taken": [],
                "positions_analyzed": 0,
                "buy_signals": 0,
                "sell_signals": 0,
                "errors": []
            }
            
            # Check for sell signals first (exit positions)
            sell_results = await self._check_sell_signals()
            results["actions_taken"].extend(sell_results)
            results["sell_signals"] = len(sell_results)
            
            # Check for buy signals (enter new positions)
            buy_results = await self._check_buy_signals()
            results["actions_taken"].extend(buy_results)
            results["buy_signals"] = len(buy_results)
            
            # Update position counts
            results["positions_analyzed"] = self._get_autotrader_position_count()
            
            logger.info(f"Autotrader cycle completed: {len(results['actions_taken'])} actions taken")
            return results
            
        except Exception as e:
            logger.error(f"Error in autotrader cycle: {str(e)}")
            return {
                "cycle_start": datetime.now().isoformat(),
                "error": str(e),
                "actions_taken": [],
                "positions_analyzed": 0,
                "buy_signals": 0,
                "sell_signals": 0
            }
    
    async def _check_sell_signals(self) -> List[Dict[str, Any]]:
        """Check existing positions for sell signals"""
        actions = []
        
        try:
            # Get all autotrader positions
            positions = db_manager.execute_query(
                "SELECT * FROM positions WHERE source = 'autotrader'"
            )
            
            for position in positions:
                symbol = position['symbol']
                position_type = position['type']
                
                # Get current score
                if position_type == 'stock':
                    asset_data = db_manager.execute_query(
                        "SELECT score FROM stocks WHERE symbol = ?", (symbol,)
                    )
                else:  # crypto
                    asset_data = db_manager.execute_query(
                        "SELECT score FROM cryptos WHERE symbol = ?", (symbol,)
                    )
                
                if asset_data:
                    current_score = asset_data[0]['score']
                    
                    # Check sell condition
                    if current_score <= self.sell_score_threshold:
                        action = await self._execute_sell(position, f"Score dropped to {current_score}")
                        if action:
                            actions.append(action)
        
        except Exception as e:
            logger.error(f"Error checking sell signals: {str(e)}")
        
        return actions
    
    async def _check_buy_signals(self) -> List[Dict[str, Any]]:
        """Check market for buy signals"""
        actions = []
        
        try:
            # Use portfolio manager to check position limits per asset type
            # Remove the old global position limit check since we now use specific limits per asset type
            
            # Get high-scoring stocks
            high_score_stocks = db_manager.execute_query(
                "SELECT * FROM stocks WHERE score >= ? ORDER BY score DESC LIMIT 10",
                (self.buy_score_threshold,)
            )
            
            # Get high-scoring cryptos
            high_score_cryptos = db_manager.execute_query(
                "SELECT * FROM cryptos WHERE score >= ? ORDER BY score DESC LIMIT 10",
                (self.buy_score_threshold,)
            )
            
            # Check if we already have positions in these assets
            existing_symbols = set()
            existing_positions = db_manager.execute_query(
                "SELECT symbol FROM positions WHERE source = 'autotrader'"
            )
            for pos in existing_positions:
                existing_symbols.add(pos['symbol'])
            
            # Process buy signals for stocks (portfolio manager handles limits)
            for stock in high_score_stocks:
                if stock['symbol'] not in existing_symbols and len(actions) < 5:  # Allow more actions per cycle
                    action = await self._execute_buy(stock, 'stock', f"High score: {stock['score']}")
                    if action:
                        actions.append(action)
                        existing_symbols.add(stock['symbol'])
            
            # Process buy signals for cryptos (portfolio manager handles limits)
            for crypto in high_score_cryptos:
                if crypto['symbol'] not in existing_symbols and len(actions) < 5:  # Allow more actions per cycle
                    action = await self._execute_buy(crypto, 'crypto', f"High score: {crypto['score']}")
                    if action:
                        actions.append(action)
                        existing_symbols.add(crypto['symbol'])
            
            # Check for SHORT signals (portfolio manager handles capacity)
            # Get low-scoring cryptos for SHORT signals
            low_score_cryptos = db_manager.execute_query(
                "SELECT * FROM cryptos WHERE score < 3.5 ORDER BY score ASC LIMIT 5"
            )
            
            # Get low-scoring stocks for SHORT signals  
            low_score_stocks = db_manager.execute_query(
                "SELECT * FROM stocks WHERE score < 2.5 ORDER BY score ASC LIMIT 5"
            )
                
            # Process SHORT signals for cryptos
            for crypto in low_score_cryptos:
                if crypto['symbol'] not in existing_symbols and len(actions) < 5:
                    short_signal = self.evaluate_crypto_short_signals(crypto)
                    if short_signal:
                        action = await self._execute_short(crypto, short_signal)
                        if action:
                            actions.append(action)
                            existing_symbols.add(crypto['symbol'])
            
            # Process SHORT signals for stocks
            for stock in low_score_stocks:
                if stock['symbol'] not in existing_symbols and len(actions) < 5:
                    short_signal = self.evaluate_stock_short_signals(stock)
                    if short_signal:
                        action = await self._execute_short(stock, short_signal)
                        if action:
                            actions.append(action)
                            existing_symbols.add(stock['symbol'])
        
        except Exception as e:
            logger.error(f"Error checking buy signals: {str(e)}")
        
        return actions
    
    async def _execute_buy(self, asset_data: Dict[str, Any], asset_type: str, reason: str) -> Optional[Dict[str, Any]]:
        """Execute a buy order"""
        try:
            symbol = asset_data['symbol']
            current_price = asset_data['current_price']
            
            if not current_price or current_price <= 0:
                logger.warning(f"Invalid price for {symbol}: {current_price}")
                return None
            
            # Use portfolio manager to get position size and check if we can open
            score = asset_data.get('score', 5)
            confidence = min(100, (score - 5) * 10) if score > 5 else 0
            position_size = portfolio_manager.get_position_size(asset_type, confidence)
            
            if not portfolio_manager.can_open_position(asset_type, position_size):
                logger.info(f"Cannot open {asset_type} position for {symbol}: insufficient capital or max positions")
                return None
                
            # Calculate quantity based on portfolio manager allocation
            quantity = position_size / current_price
            
            # Create position
            position_id = str(uuid.uuid4())
            value = quantity * current_price
            
            db_manager.execute_insert(
                """INSERT INTO positions 
                   (id, symbol, name, type, quantity, entry_price, current_price, 
                    value, pnl, pnl_percent, source, position_side, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 'autotrader', 'LONG', ?, ?)""",
                (
                    position_id, symbol, asset_data['name'], asset_type,
                    quantity, current_price, current_price, value,
                    datetime.now().isoformat(), datetime.now().isoformat()
                )
            )
            
            # Update portfolio manager
            portfolio_manager.execute_buy(symbol, current_price, quantity, asset_type)
            
            # Log transaction
            db_manager.execute_insert(
                """INSERT INTO autotrader_transactions 
                   (symbol, action, quantity, price, reason)
                   VALUES (?, 'buy', ?, ?, ?)""",
                (symbol, quantity, current_price, reason)
            )
            
            action = {
                "action": "buy",
                "symbol": symbol,
                "type": asset_type,
                "quantity": quantity,
                "price": current_price,
                "value": value,
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"BUY: {symbol} ({asset_type}) - {quantity:.4f} @ ${current_price:.2f} - {reason}")
            return action
            
        except Exception as e:
            logger.error(f"Error executing buy for {asset_data.get('symbol', 'unknown')}: {str(e)}")
            return None
    
    async def _execute_sell(self, position: Dict[str, Any], reason: str) -> Optional[Dict[str, Any]]:
        """Execute a sell order"""
        try:
            symbol = position['symbol']
            quantity = position['quantity']
            current_price = position['current_price']
            entry_price = position['entry_price']
            
            if not current_price or current_price <= 0:
                logger.warning(f"Invalid current price for {symbol}: {current_price}")
                return None
            
            # Calculate P&L based on position side
            position_side = position.get('position_side', 'LONG')
            if position_side == 'LONG':
                pnl = (current_price - entry_price) * quantity
            else:  # SHORT
                pnl = (entry_price - current_price) * quantity
                
            pnl_percent = (pnl / (entry_price * quantity)) * 100 if entry_price > 0 else 0
            
            # Update portfolio manager before removing position
            asset_type = position.get('type', 'stock')
            portfolio_manager.execute_sell(symbol, current_price, quantity, asset_type, pnl)
            
            # Remove position
            db_manager.execute_update(
                "DELETE FROM positions WHERE id = ?",
                (position['id'],)
            )
            
            # Log transaction
            db_manager.execute_insert(
                """INSERT INTO autotrader_transactions 
                   (symbol, action, quantity, price, reason)
                   VALUES (?, 'sell', ?, ?, ?)""",
                (symbol, quantity, current_price, reason)
            )
            
            action = {
                "action": "sell",
                "symbol": symbol,
                "type": position['type'],
                "quantity": quantity,
                "price": current_price,
                "value": quantity * current_price,
                "pnl": pnl,
                "pnl_percent": pnl_percent,
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"SELL: {symbol} ({position['type']}) - {quantity:.4f} @ ${current_price:.2f} - P&L: ${pnl:.2f} ({pnl_percent:.2f}%) - {reason}")
            return action
            
        except Exception as e:
            logger.error(f"Error executing sell for {position.get('symbol', 'unknown')}: {str(e)}")
            return None
    
    def _get_autotrader_position_count(self) -> int:
        """Get current number of autotrader positions"""
        try:
            result = db_manager.execute_query(
                "SELECT COUNT(*) as count FROM positions WHERE source = 'autotrader'"
            )
            return result[0]['count'] if result else 0
        except Exception as e:
            logger.error(f"Error getting position count: {str(e)}")
            return 0
    
    def get_trading_summary(self) -> Dict[str, Any]:
        """Get trading performance summary"""
        try:
            # Get current positions
            positions = db_manager.execute_query(
                """SELECT COUNT(*) as count, SUM(value) as total_value, 
                   SUM(pnl) as total_pnl, AVG(pnl_percent) as avg_pnl_percent
                   FROM positions WHERE source = 'autotrader'"""
            )
            
            # Get recent transactions
            recent_transactions = db_manager.execute_query(
                """SELECT * FROM autotrader_transactions 
                   ORDER BY timestamp DESC LIMIT 10"""
            )
            
            # Calculate win rate
            completed_trades = db_manager.execute_query(
                """SELECT action, COUNT(*) as count 
                   FROM autotrader_transactions 
                   WHERE action = 'sell' 
                   GROUP BY action"""
            )
            
            pos_data = positions[0] if positions else {}
            
            return {
                "current_positions": pos_data.get('count', 0),
                "total_position_value": pos_data.get('total_value', 0) or 0,
                "total_pnl": pos_data.get('total_pnl', 0) or 0,
                "average_pnl_percent": pos_data.get('avg_pnl_percent', 0) or 0,
                "recent_transactions": [dict(tx) for tx in recent_transactions],
                "max_positions": self.max_total_positions,
                "buy_threshold": self.buy_score_threshold,
                "sell_threshold": self.sell_score_threshold
            }
            
        except Exception as e:
            logger.error(f"Error getting trading summary: {str(e)}")
            return {
                "error": str(e),
                "current_positions": 0,
                "total_position_value": 0,
                "total_pnl": 0,
                "average_pnl_percent": 0,
                "recent_transactions": []
            }
    
    def evaluate_crypto_short_signals(self, crypto_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Evaluate SHORT signals for crypto"""
        try:
            score = crypto_data.get('score', 0)
            symbol = crypto_data.get('symbol', '')
            
            # Only SHORT if score is very low and we can open position
            if score < 3.5:
                required_capital = portfolio_manager.get_position_size('crypto', (4 - score) * 20)
                
                if portfolio_manager.can_open_position('crypto', required_capital):
                    return {
                        'action': 'SHORT',
                        'confidence': min(90, (4 - score) * 20),
                        'reasons': [f'Low score: {score}', 'Bearish technical signals'],
                        'required_capital': required_capital
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error evaluating crypto SHORT signals: {e}")
            return None
    
    def evaluate_stock_short_signals(self, stock_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Evaluate SHORT signals for stocks"""
        try:
            score = stock_data.get('score', 0)
            symbol = stock_data.get('symbol', '')
            
            # More conservative SHORT threshold for stocks
            if score < 2.5:
                required_capital = portfolio_manager.get_position_size('stock', (3 - score) * 25)
                
                if portfolio_manager.can_open_position('stock', required_capital):
                    return {
                        'action': 'SHORT',
                        'confidence': min(85, (3 - score) * 25),
                        'reasons': [f'Very low score: {score}', 'Strong bearish signals'],
                        'required_capital': required_capital
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error evaluating stock SHORT signals: {e}")
            return None
    
    async def _execute_short(self, asset_data: Dict[str, Any], signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute a SHORT position"""
        try:
            symbol = asset_data['symbol']
            name = asset_data['name']
            # Determine asset type correctly
            asset_type = asset_data.get('type', 'stock')
            # If symbol ends with -USD, it's definitely crypto
            if symbol.endswith('-USD'):
                asset_type = 'crypto'
            # If no type field, infer from context: cryptos don't have a 'sector' field
            elif 'type' not in asset_data and 'sector' not in asset_data:
                asset_type = 'crypto'
            current_price = asset_data['current_price']
            required_capital = signal['required_capital']
            
            # Calculate quantity based on capital allocation
            quantity = required_capital / current_price
            
            if quantity <= 0:
                logger.warning(f"Invalid quantity calculated for SHORT {symbol}: {quantity}")
                return None
            
            # Create SHORT position in database
            position_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            db_manager.execute_insert(
                """INSERT INTO positions 
                   (id, symbol, name, type, quantity, entry_price, current_price, 
                    value, pnl, pnl_percent, source, position_side, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'autotrader', 'SHORT', ?, ?)""",
                (position_id, symbol, name, asset_type, quantity, current_price, current_price,
                 quantity * current_price, 0.0, 0.0, now, now)
            )
            
            # Update portfolio manager
            reason = f"SHORT signal - {', '.join(signal['reasons'])}"
            portfolio_manager.execute_buy(symbol, current_price, quantity, asset_type)
            
            # Log transaction
            db_manager.execute_insert(
                """INSERT INTO autotrader_transactions 
                   (symbol, action, quantity, price, reason)
                   VALUES (?, 'short', ?, ?, ?)""",
                (symbol, quantity, current_price, reason)
            )
            
            action = {
                "action": "short",
                "symbol": symbol,
                "type": asset_type,
                "quantity": quantity,
                "price": current_price,
                "value": quantity * current_price,
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"SHORT: {symbol} ({asset_type}) - {quantity:.4f} @ ${current_price:.2f} - {reason}")
            return action
            
        except Exception as e:
            logger.error(f"Error executing SHORT for {asset_data.get('symbol', 'unknown')}: {str(e)}")
            return None