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
from .advanced_scoring_service import AdvancedScoringService
from .portfolio_manager import portfolio_manager

logger = logging.getLogger(__name__)

class AutotraderService:
    """Service for automated trading based on scores"""
    
    def __init__(self):
        self.data_service = DataService()
        self.scoring_service = ScoringService()
        self.advanced_scoring = AdvancedScoringService()
        
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
                position_side = position.get('position_side', 'LONG')
                entry_price = position['entry_price']
                current_price = position.get('current_price', entry_price)
                stop_loss = position.get('stop_loss_updated')
                take_profit = position.get('take_profit_updated')
                
                # Get current asset data
                if position_type == 'stock':
                    asset_data = db_manager.execute_query(
                        "SELECT score, current_price FROM stocks WHERE symbol = ?", (symbol,)
                    )
                else:  # crypto
                    asset_data = db_manager.execute_query(
                        "SELECT score, current_price FROM cryptos WHERE symbol = ?", (symbol,)
                    )
                
                if asset_data:
                    current_score = asset_data[0]['score']
                    latest_price = asset_data[0]['current_price']
                    
                    sell_reason = None
                    
                    if position_side == 'SHORT':
                        # SHORT position exit logic
                        # 1. Score improvement (exit when score rises above 3.0)
                        if current_score >= 3.0:
                            sell_reason = f"Score improved to {current_score} - EXIT SHORT"
                        # 2. Stop loss triggered (price rose 8%)
                        elif stop_loss and latest_price >= stop_loss:
                            sell_reason = f"Stop loss triggered at ${latest_price:.4f} (limit: ${stop_loss:.4f})"
                        # 3. Take profit triggered (price fell 5%)
                        elif take_profit and latest_price <= take_profit:
                            sell_reason = f"Take profit triggered at ${latest_price:.4f} (target: ${take_profit:.4f})"
                        # 4. Emergency exit if multiple SHORTs hitting stops
                        elif self._emergency_short_exit_check():
                            sell_reason = "Emergency SHORT exit - multiple positions at risk"
                    else:
                        # LONG position exit logic (original)
                        if current_score <= self.sell_score_threshold:
                            sell_reason = f"Score dropped to {current_score}"
                    
                    if sell_reason:
                        action = await self._execute_sell(position, sell_reason)
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
        """Evaluate SHORT signals for crypto with advanced weighted scoring"""
        try:
            symbol = crypto_data.get('symbol', '')
            
            # Use advanced scoring system for SHORT detection
            scoring_result = self.advanced_scoring.calculate_short_weighted_score(crypto_data)
            
            final_score = scoring_result.get('final_score', 5.0)
            short_eligible = scoring_result.get('short_eligible', False)
            confidence = scoring_result.get('confidence', 0)
            breakdown = scoring_result.get('breakdown', {})
            
            # ULTRA CONSERVATIVE: Only SHORT if advanced system confirms AND confidence > 70%
            if not short_eligible or confidence < 0.7:
                logger.debug(f"Advanced scoring rejected SHORT {symbol}: score={final_score:.2f}, confidence={confidence:.2f}")
                return None
            
            # Log detailed breakdown for analysis
            logger.info(f"Advanced SHORT signal {symbol}: score={final_score:.2f}, confidence={confidence:.2f}")
            logger.info(f"  Technical: {breakdown.get('technical', {})}")
            logger.info(f"  Sentiment: {breakdown.get('sentiment', {})}")
            logger.info(f"  Momentum: {breakdown.get('momentum', {})}")
            
            # Basic market filters still apply
            change_percent = crypto_data.get('change_percent', 0)
            volume = crypto_data.get('volume', 0)
            
            # Market condition filters - get BTC trend
            btc_uptrend = self._check_btc_uptrend()
            if btc_uptrend:
                logger.debug(f"Skipping SHORT {symbol}: BTC in uptrend")
                return None
            
            # No SHORT if crypto had recent strong gains (>10% in 3 days)
            recent_strong_gains = change_percent > 10
            if recent_strong_gains:
                logger.debug(f"Skipping SHORT {symbol}: Recent strong gains {change_percent:.2f}%")
                return None
            
            # Volume confirmation (require high volume for SHORT)
            if volume < 50000000:  # Require at least 50M volume
                logger.debug(f"Skipping SHORT {symbol}: Insufficient volume {volume}")
                return None
            
            # Advanced scoring already includes technical confirmations
            # Extract reasons from advanced scoring breakdown
            advanced_reasons = []
            for category, details in breakdown.items():
                for key, value in details.items():
                    if isinstance(value, str) and ('(-' in value or 'bearish' in value.lower() or 'negative' in value.lower()):
                        advanced_reasons.append(f"{category.title()}: {value}")
            
            if len(advanced_reasons) < 3:  # Require at least 3 negative signals
                logger.debug(f"Skipping SHORT {symbol}: Insufficient negative signals ({len(advanced_reasons)}/3)")
                return None
            
            # Check if we can open SHORT (max 3 SHORT positions)
            current_shorts = self._count_current_short_positions('crypto')
            if current_shorts >= 3:
                logger.debug(f"Skipping SHORT {symbol}: Max SHORT positions reached ({current_shorts}/3)")
                return None
            
            # Position sizing - more conservative
            required_capital = portfolio_manager.get_position_size('crypto', (2 - score) * 30)
            
            # Check portfolio SHORT exposure limit (max 15%)
            if not self._check_short_exposure_limit('crypto', required_capital):
                logger.debug(f"Skipping SHORT {symbol}: Would exceed SHORT exposure limit")
                return None
            
            if portfolio_manager.can_open_position('crypto', required_capital):
                return {
                    'action': 'SHORT',
                    'confidence': int(confidence * 100),  # Use advanced scoring confidence
                    'reasons': advanced_reasons,  # Use detailed breakdown reasons
                    'required_capital': required_capital,
                    'advanced_score': final_score,
                    'scoring_breakdown': breakdown
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
            
            # Calculate automatic stop loss (8% loss = price rises 8%)
            stop_loss_price = current_price * 1.08
            take_profit_price = current_price * 0.95  # 5% profit = price falls 5%
            
            db_manager.execute_insert(
                """INSERT INTO positions 
                   (id, symbol, name, type, quantity, entry_price, current_price, 
                    value, pnl, pnl_percent, source, position_side, stop_loss_updated, take_profit_updated, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'autotrader', 'SHORT', ?, ?, ?, ?)""",
                (position_id, symbol, name, asset_type, quantity, current_price, current_price,
                 quantity * current_price, 0.0, 0.0, stop_loss_price, take_profit_price, now, now)
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
    
    def _check_btc_uptrend(self) -> bool:
        """Check if BTC is in uptrend (simplified - check if recent change is positive)"""
        try:
            # Get BTC data
            btc_data = db_manager.execute_query(
                "SELECT change_percent FROM cryptos WHERE symbol = 'BTC-USD' LIMIT 1"
            )
            if btc_data:
                btc_change = btc_data[0].get('change_percent', 0)
                # Consider uptrend if BTC is up more than 2% recently
                return btc_change > 2.0
            return False
        except Exception as e:
            logger.error(f"Error checking BTC trend: {e}")
            return False  # Conservative default
    
    def _get_technical_confirmations(self, crypto_data: Dict[str, Any]) -> List[str]:
        """Get technical analysis confirmations for SHORT signal"""
        confirmations = []
        
        try:
            score = crypto_data.get('score', 0)
            change_percent = crypto_data.get('change_percent', 0)
            volume = crypto_data.get('volume', 0)
            
            # Confirmation 1: Extremely low score
            if score <= 1.5:
                confirmations.append("Extremely bearish score")
            
            # Confirmation 2: Recent decline
            if change_percent < -5:
                confirmations.append("Strong recent decline")
            
            # Confirmation 3: High volume selloff
            if volume > 100000000:  # 100M+ volume
                confirmations.append("High volume bearish pressure")
            
            # Confirmation 4: Poor fundamentals (if small market cap)
            market_cap = crypto_data.get('market_cap', 0)
            if market_cap < 5000000000:  # Less than 5B market cap
                confirmations.append("Small cap vulnerability")
            
        except Exception as e:
            logger.error(f"Error getting technical confirmations: {e}")
        
        return confirmations
    
    def _count_current_short_positions(self, asset_type: str) -> int:
        """Count current SHORT positions for asset type"""
        try:
            # Count SHORT positions from database
            result = db_manager.execute_query("""
                SELECT COUNT(*) as count 
                FROM positions 
                WHERE position_side = 'SHORT' 
                AND type = ?
            """, (asset_type,))
            
            if result:
                return result[0]['count']
            return 0
        except Exception as e:
            logger.error(f"Error counting SHORT positions: {e}")
            return 999  # Conservative default - block SHORT if error
    
    def _check_short_exposure_limit(self, asset_type: str, additional_capital: float) -> bool:
        """Check if adding this SHORT position would exceed exposure limit (15%)"""
        try:
            # Get current SHORT exposure
            current_shorts = db_manager.execute_query("""
                SELECT SUM(quantity * entry_price) as total_exposure
                FROM positions 
                WHERE position_side = 'SHORT' 
                AND type = ?
            """, (asset_type,))
            
            current_exposure = 0
            if current_shorts and current_shorts[0]['total_exposure']:
                current_exposure = current_shorts[0]['total_exposure']
            
            # Get total portfolio value for this asset type
            if asset_type == 'crypto':
                total_portfolio = portfolio_manager.liquid_capital_crypto + portfolio_manager.invested_capital_crypto
            else:
                total_portfolio = portfolio_manager.liquid_capital_stocks + portfolio_manager.invested_capital_stocks
            
            # Calculate new exposure percentage
            new_exposure = current_exposure + additional_capital
            exposure_percentage = (new_exposure / total_portfolio) * 100 if total_portfolio > 0 else 100
            
            # Limit SHORT exposure to 15% of portfolio
            return exposure_percentage <= 15.0
            
        except Exception as e:
            logger.error(f"Error checking SHORT exposure limit: {e}")
            return False  # Conservative default
    
    def _emergency_short_exit_check(self) -> bool:
        """Check if emergency SHORT exit is needed (multiple positions hitting stop loss)"""
        try:
            # Get SHORT positions with current P&L
            short_positions = db_manager.execute_query("""
                SELECT symbol, pnl_percent, stop_loss_updated, current_price, entry_price
                FROM positions 
                WHERE position_side = 'SHORT' 
                AND type = 'crypto'
            """)
            
            if len(short_positions) < 2:
                return False  # Need at least 2 positions for emergency exit
            
            # Count how many are near stop loss (within 2% of stop loss)
            near_stop_count = 0
            losing_positions = 0
            
            for pos in short_positions:
                current_price = pos.get('current_price', 0)
                stop_loss = pos.get('stop_loss_updated', 0)
                pnl_percent = pos.get('pnl_percent', 0)
                
                # Count losing positions
                if pnl_percent < -3:  # Losing more than 3%
                    losing_positions += 1
                
                # Count positions near stop loss
                if stop_loss and current_price > 0:
                    distance_to_stop = ((stop_loss - current_price) / current_price) * 100
                    if distance_to_stop < 2:  # Within 2% of stop loss
                        near_stop_count += 1
            
            # Emergency exit if 2+ positions losing >3% OR 2+ positions near stop loss
            return losing_positions >= 2 or near_stop_count >= 2
            
        except Exception as e:
            logger.error(f"Error checking emergency SHORT exit: {e}")
            return False