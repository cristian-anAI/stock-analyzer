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
from .unified_scoring_service import UnifiedScoringService
from .improved_scoring_service import ImprovedScoringService
from .decision_logger import decision_logger
from .portfolio_manager import portfolio_manager
from .timeframe_data_service import TimeframeDataService
from .volatility_service import volatility_service
from .risk_management_service import risk_management_service
from .overtrading_prevention_service import overtrading_prevention
from .market_timing_service import market_timing_service
from .transaction_pnl_service import get_transaction_pnl_service
from .telegram_service import telegram_service
from ..strategies.swing_trading_strategy import SwingTradingStrategy
from ..strategies.crypto_competition_strategy import CryptoCompetitionStrategy
from ..strategies.mtss_crypto_strategy import MTSSCryptoStrategy
from ..strategies.optimized_trading_config import OptimizedTradingConfig

logger = logging.getLogger(__name__)

class AutotraderService:
    """Service for automated trading based on scores"""
    
    def __init__(self, use_optimized_config: bool = True):
        self.data_service = DataService()
        self.scoring_service = ScoringService()
        self.advanced_scoring = AdvancedScoringService()
        self.unified_scoring = UnifiedScoringService()
        self.improved_scoring = ImprovedScoringService()  # NEW: Optimized scoring
        self.decision_logger = decision_logger  # NEW: Decision transparency
        self.timeframe_service = TimeframeDataService()
        self.market_timing = market_timing_service
        self.pnl_service = get_transaction_pnl_service(db_manager)

        # Initialize new multi-timeframe strategies
        self.swing_strategy = SwingTradingStrategy()  # For stocks
        self.crypto_strategy = CryptoCompetitionStrategy()  # For crypto
        self.mtss_crypto_strategy = MTSSCryptoStrategy()  # MTSS for crypto (alternative)

        # Choose configuration based on parameter
        if use_optimized_config:
            # NEW: OPTIMIZED CONFIGURATION - Proven in 1-year backtest
            # Results: 18.79% return, Sharpe 2.43, 83.33% monthly win rate
            self.config = OptimizedTradingConfig.get_optimized_config()
            logger.info("🚀 Using OPTIMIZED trading configuration (backtest proven: 18.79% CAGR)")
        else:
            # Legacy configuration
            from ..strategies.trading_config import TRADING_CONFIG
            self.config = TRADING_CONFIG
            logger.info("Using legacy trading configuration")

        # Trading parameters from optimized config
        self.buy_score_threshold = self.config.buy_score_threshold  # 6.5 (optimized)
        self.sell_score_threshold = self.config.sell_score_threshold  # 5.5 (optimized)
        self.short_trading_enabled = self.config.short_trading_enabled  # False
        self.high_volatility_bypass = self.config.high_volatility_bypass  # True
        self.max_position_value = self.config.max_position_value  # $10k per position
        self.max_total_positions = self.config.max_positions_stocks  # 10 positions
        self.use_improved_scoring = self.config.use_improved_scoring  # True (NEW)
        self.use_trailing_stop = self.config.use_trailing_stop  # True (NEW)
        self.trailing_stop_percent = self.config.trailing_stop_percent  # 5.0% (NEW)
        self.min_hold_days = self.config.swing_min_hold_days  # 7 days (NEW)
        self.max_hold_days = self.config.swing_max_hold_days  # 30 days (NEW)
        self.cooldown_days = self.config.symbol_cooldown_days  # 7 days (NEW)

        # Track trailing stops for positions
        self.trailing_stops = {}  # {position_id: {highest_price, trailing_stop_price}}

        logger.info(f"Initialized AutoTrader with optimized config: buy={self.buy_score_threshold}, sell={self.sell_score_threshold}, trailing_stop={self.trailing_stop_percent}%")
        
    async def run_trading_cycle(self) -> Dict[str, Any]:
        """Run a complete trading cycle"""
        # Start decision logging cycle
        cycle_id = self.decision_logger.start_cycle()

        logger.info("=" * 70)
        logger.info(f"🔄 Starting optimized autotrader cycle {cycle_id[:8]}...")
        logger.info(f"Config: buy>={self.buy_score_threshold}, sell<={self.sell_score_threshold}, trailing_stop={self.trailing_stop_percent}%")
        logger.info("=" * 70)

        try:
            # 0. Market timing checks
            timing_summary = self.market_timing.get_timing_summary()
            logger.info(f"Market timing check: {timing_summary['market_status']} - {timing_summary['current_time']}")
            
            # TEMPORARILY DISABLED FOR TESTING - REMOVE FOR PRODUCTION
            # if not timing_summary['is_market_open']:
            #     logger.info(f"Market closed - cycle skipped: {timing_summary.get('buy_reason', 'Market not open')}")
            #     return {
            #         "cycle_start": datetime.now().isoformat(),
            #         "market_status": "CLOSED",
            #         "market_timing": timing_summary,
            #         "actions_taken": [],
            #         "positions_analyzed": 0,
            #         "buy_signals": 0,
            #         "sell_signals": 0,
            #         "message": "Trading cycle skipped - market closed"
            #     }
            
            logger.info(f"Market timing: BUY {timing_summary['buy_reason']}, SELL {timing_summary['sell_reason']}")
            
            # 1. Pre-cycle checks and updates
            logger.info("DEBUG: Checking portfolio risk limits...")
            risk_within_limits, risk_warnings = risk_management_service.check_portfolio_risk_limits()
            should_reduce_sizes, size_reason = risk_management_service.should_reduce_position_sizes()
            logger.info(f"DEBUG: Risk within limits: {risk_within_limits}, Should reduce sizes: {should_reduce_sizes}")
            
            # Stop trading if critical risk levels reached
            if not risk_within_limits and any("CRITICAL" in w for w in risk_warnings):
                logger.warning("CRITICAL risk levels - stopping trading cycle")
                return {
                    "cycle_start": datetime.now().isoformat(),
                    "error": "Trading stopped due to critical risk levels",
                    "risk_warnings": risk_warnings,
                    "actions_taken": [],
                    "positions_analyzed": 0,
                    "buy_signals": 0,
                    "sell_signals": 0
                }
            
            # Update all market data first
            await self.data_service.update_stocks_data()
            await self.data_service.update_cryptos_data()
            await self.data_service.update_positions_prices()
            
            # Update volatility tracking (run in background)
            volatility_update = await volatility_service.update_volatility_tracking()
            
            # Clean expired trading restrictions
            cleanup_results = overtrading_prevention.clean_expired_data()
            
            results = {
                "cycle_start": datetime.now().isoformat(),
                "actions_taken": [],
                "positions_analyzed": 0,
                "buy_signals": 0,
                "sell_signals": 0,
                "errors": [],
                "risk_status": {
                    "within_limits": risk_within_limits,
                    "warnings": risk_warnings,
                    "should_reduce_sizes": should_reduce_sizes,
                    "size_reduction_reason": size_reason
                },
                "volatility_update": volatility_update,
                "cleanup_results": cleanup_results
            }
            
            # Check for sell signals first (exit positions)
            sell_results = await self._check_sell_signals()
            results["actions_taken"].extend(sell_results)
            results["sell_signals"] = len(sell_results)
            
            # Check for buy signals (enter new positions)
            logger.info("DEBUG: About to call _check_buy_signals()")
            buy_results = await self._check_buy_signals()
            logger.info(f"DEBUG: _check_buy_signals() returned {len(buy_results)} results")
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
    
    def _update_trailing_stop(self, position: Dict[str, Any], current_price: float) -> tuple:
        """
        Update trailing stop for a position

        Returns:
            (trailing_stop_price, highest_price, should_sell, sell_reason)
        """
        position_id = position['id']
        entry_price = position['entry_price']

        # Initialize trailing stop data if not exists
        if position_id not in self.trailing_stops:
            self.trailing_stops[position_id] = {
                'highest_price': max(entry_price, current_price),
                'trailing_stop_price': entry_price * (1 - self.trailing_stop_percent / 100)
            }

        # Update highest price seen
        if current_price > self.trailing_stops[position_id]['highest_price']:
            self.trailing_stops[position_id]['highest_price'] = current_price
            # Update trailing stop price
            self.trailing_stops[position_id]['trailing_stop_price'] = current_price * (1 - self.trailing_stop_percent / 100)

        trailing_stop_price = self.trailing_stops[position_id]['trailing_stop_price']
        highest_price = self.trailing_stops[position_id]['highest_price']

        # Check if trailing stop hit
        should_sell = current_price < trailing_stop_price
        sell_reason = None
        if should_sell:
            pnl_from_highest = ((current_price - highest_price) / highest_price) * 100
            sell_reason = f"Trailing stop hit: ${current_price:.2f} < ${trailing_stop_price:.2f} (down {abs(pnl_from_highest):.2f}% from peak)"

        return (trailing_stop_price, highest_price, should_sell, sell_reason)

    async def _check_sell_signals(self) -> List[Dict[str, Any]]:
        """Check existing positions for sell signals with OPTIMIZED strategy"""
        actions = []

        try:
            # Get all autotrader positions
            positions = db_manager.execute_query(
                "SELECT * FROM positions WHERE source = 'autotrader'"
            )

            logger.info(f"Checking sell signals for {len(positions)} positions")

            for position in positions:
                symbol = position['symbol']
                position_type = position['type']
                position_side = position.get('position_side', 'LONG')
                entry_price = position['entry_price']
                current_price = position.get('current_price', entry_price)
                created_at = position.get('created_at', datetime.now().isoformat())

                # Calculate days held
                days_held = (datetime.now() - datetime.fromisoformat(created_at)).days

                # Get current asset data and score
                if position_type == 'stock':
                    asset_data = db_manager.execute_query(
                        "SELECT * FROM stocks WHERE symbol = ?", (symbol,)
                    )
                else:  # crypto
                    asset_data = db_manager.execute_query(
                        "SELECT * FROM cryptos WHERE symbol = ?", (symbol,)
                    )

                if not asset_data:
                    logger.warning(f"No data found for {symbol}, skipping sell check")
                    continue

                asset = asset_data[0]
                latest_price = asset['current_price']

                # Calculate current score using improved scoring if enabled
                if self.use_improved_scoring and position_side == 'LONG':
                    try:
                        # Get historical data for improved scoring
                        import yfinance as yf
                        ticker_symbol = symbol if position_type == 'stock' else symbol
                        ticker = yf.Ticker(ticker_symbol)
                        hist = ticker.history(period="60d")

                        if not hist.empty:
                            current_score = self.improved_scoring.calculate_stock_score_from_data(hist)
                        else:
                            current_score = asset.get('score', 5.0)
                    except:
                        current_score = asset.get('score', 5.0)
                else:
                    current_score = asset.get('score', 5.0)

                # Calculate P&L
                pnl_percent = ((latest_price - entry_price) / entry_price) * 100 if position_side == 'LONG' else ((entry_price - latest_price) / entry_price) * 100

                sell_reason = None
                exit_details = {}

                if position_side == 'SHORT':
                    # SHORT exit logic (unchanged)
                    stop_loss = position.get('stop_loss_updated')
                    take_profit = position.get('take_profit_updated')

                    if current_score >= 3.0:
                        sell_reason = f"Score improved to {current_score} - EXIT SHORT"
                    elif stop_loss and latest_price >= stop_loss:
                        sell_reason = f"Stop loss triggered"
                    elif take_profit and latest_price <= take_profit:
                        sell_reason = f"Take profit triggered"
                    elif self._emergency_short_exit_check():
                        sell_reason = "Emergency SHORT exit"
                else:
                    # OPTIMIZED LONG EXIT LOGIC
                    exit_details = {
                        'current_score': current_score,
                        'days_held': days_held,
                        'pnl_percent': pnl_percent,
                        'min_hold_days': self.min_hold_days,
                        'max_hold_days': self.max_hold_days,
                        'sell_threshold': self.sell_score_threshold
                    }

                    # 1. Check minimum hold time
                    if days_held < self.min_hold_days:
                        # Only sell if stop loss hit (significant loss)
                        if pnl_percent <= -self.config.stop_loss_percent:
                            sell_reason = f"Stop loss hit: {pnl_percent:.2f}% (before min hold)"
                            exit_details['exit_type'] = 'stop_loss'
                    else:
                        # 2. Check trailing stop
                        if self.use_trailing_stop:
                            trailing_stop_price, highest_price, should_sell, ts_reason = self._update_trailing_stop(position, latest_price)
                            exit_details['trailing_stop_price'] = trailing_stop_price
                            exit_details['highest_price'] = highest_price

                            if should_sell:
                                sell_reason = ts_reason
                                exit_details['exit_type'] = 'trailing_stop'

                        # 3. Check take profit
                        if not sell_reason and pnl_percent >= self.config.take_profit_percent:
                            sell_reason = f"Take profit target hit: {pnl_percent:.2f}%"
                            exit_details['exit_type'] = 'take_profit'

                        # 4. Check score threshold
                        if not sell_reason and current_score <= self.sell_score_threshold:
                            sell_reason = f"Score dropped to {current_score:.2f}"
                            exit_details['exit_type'] = 'score_threshold'

                        # 5. Check max hold time
                        if not sell_reason and days_held >= self.max_hold_days:
                            sell_reason = f"Max hold time reached: {days_held} days"
                            exit_details['exit_type'] = 'max_hold'

                # Log sell evaluation
                self.decision_logger.log_sell_evaluation(
                    symbol=symbol,
                    asset_type=position_type,
                    score=current_score,
                    current_price=latest_price,
                    action_taken='sell' if sell_reason else 'none',
                    entry_price=entry_price,
                    days_held=days_held,
                    pnl_percent=pnl_percent,
                    exit_reason=sell_reason,
                    exit_details=exit_details,
                    sell_threshold=self.sell_score_threshold,
                    trailing_stop_price=self.trailing_stops.get(position['id'], {}).get('trailing_stop_price'),
                    stop_loss_price=entry_price * (1 - self.config.stop_loss_percent / 100),
                    take_profit_price=entry_price * (1 + self.config.take_profit_percent / 100)
                )

                if sell_reason:
                    action = await self._execute_sell(position, sell_reason)
                    if action:
                        actions.append(action)
                        # Clean up trailing stop data
                        if position['id'] in self.trailing_stops:
                            del self.trailing_stops[position['id']]

        except Exception as e:
            logger.error(f"Error checking sell signals: {str(e)}")

        return actions
    
    async def _check_buy_signals(self) -> List[Dict[str, Any]]:
        """Check market for buy signals"""
        actions = []
        
        try:
            # Use portfolio manager to check position limits per asset type
            # Remove the old global position limit check since we now use specific limits per asset type
            
            # Get candidate stocks and cryptos for analysis
            candidate_stocks = db_manager.execute_query(
                "SELECT * FROM stocks WHERE score >= 6.0 ORDER BY score DESC LIMIT 15",
                ()
            )
            
            candidate_cryptos = db_manager.execute_query(
                "SELECT * FROM cryptos WHERE score >= 6.0 ORDER BY score DESC LIMIT 15",
                ()
            )
            
            # Check if we already have positions in these assets
            existing_symbols = set()
            existing_positions = db_manager.execute_query(
                "SELECT symbol FROM positions WHERE source = 'autotrader'"
            )
            for pos in existing_positions:
                existing_symbols.add(pos['symbol'])
            
            # Process buy signals for stocks with OPTIMIZED strategy
            logger.info(f"🔍 Processing {len(candidate_stocks)} stock candidates")
            for stock in candidate_stocks:
                symbol = stock['symbol']
                current_price = stock.get('current_price', 0)

                if symbol in existing_symbols:
                    logger.debug(f"⏭️  {symbol}: Already have position")
                    continue

                if len(actions) >= 10:
                    logger.info("🛑 Maximum 10 buys per cycle reached")
                    break

                filters_passed = {}
                filters_failed = {}
                scoring_breakdown = {}

                try:
                    # Filter 1: Overtrading prevention
                    can_trade, trade_reason = overtrading_prevention.can_trade_symbol(
                        symbol, 'stock', 'buy'
                    )
                    filters_passed['overtrading'] = can_trade
                    if not can_trade:
                        filters_failed['overtrading'] = trade_reason

                    # Filter 2: Volatility check
                    passes_volatility, vol_reason = volatility_service.check_volatility_filter(
                        symbol, 'swing'
                    )
                    if passes_volatility or self.high_volatility_bypass:
                        filters_passed['volatility'] = True
                    else:
                        filters_failed['volatility'] = vol_reason

                    # Filter 3: Score calculation using improved scoring
                    if self.use_improved_scoring:
                        try:
                            import yfinance as yf
                            ticker = yf.Ticker(symbol)
                            hist = ticker.history(period="60d")

                            if not hist.empty:
                                improved_score = self.improved_scoring.calculate_stock_score_from_data(hist)
                                scoring_breakdown = {
                                    'improved_score': improved_score,
                                    'method': 'ImprovedScoringService',
                                    'period': '60d'
                                }
                            else:
                                improved_score = stock.get('score', 5.0)
                                scoring_breakdown = {
                                    'score': improved_score,
                                    'method': 'fallback',
                                    'reason': 'no_historical_data'
                                }
                        except Exception as e:
                            improved_score = stock.get('score', 5.0)
                            scoring_breakdown = {
                                'score': improved_score,
                                'method': 'fallback',
                                'error': str(e)
                            }
                    else:
                        improved_score = stock.get('score', 5.0)
                        scoring_breakdown = {'score': improved_score, 'method': 'traditional'}

                    # Filter 4: Score threshold
                    score_passes = improved_score >= self.buy_score_threshold
                    filters_passed['score_threshold'] = score_passes
                    if not score_passes:
                        filters_failed['score_threshold'] = f"Score {improved_score:.2f} < {self.buy_score_threshold}"

                    # Filter 5: Portfolio capacity
                    confidence = min(100, (improved_score - 5) * 10) if improved_score > 5 else 0
                    position_size = portfolio_manager.get_position_size('stock', confidence)
                    can_open = portfolio_manager.can_open_position('stock', position_size)
                    filters_passed['portfolio_capacity'] = can_open
                    if not can_open:
                        filters_failed['portfolio_capacity'] = "Insufficient capital or max positions reached"

                    # Determine if buy should execute
                    all_filters_passed = (
                        can_trade and
                        (passes_volatility or self.high_volatility_bypass) and
                        score_passes and
                        can_open
                    )

                    # Log buy evaluation
                    self.decision_logger.log_buy_evaluation(
                        symbol=symbol,
                        asset_type='stock',
                        score=improved_score,
                        current_price=current_price,
                        action_taken='buy' if all_filters_passed else 'none',
                        filters_passed=filters_passed,
                        filters_failed=filters_failed,
                        scoring_breakdown=scoring_breakdown,
                        buy_threshold=self.buy_score_threshold,
                        confidence=confidence,
                        position_size=position_size if all_filters_passed else None
                    )

                    # Execute buy if all filters passed
                    if all_filters_passed:
                        # Create simplified signal object for execution
                        signal = type('Signal', (), {
                            'action': 'BUY',
                            'confidence': improved_score,
                            'symbol': symbol,
                            'score': improved_score,
                            'reasons': [f'Improved score: {improved_score:.2f}'],
                            'stop_loss': current_price * (1 - self.config.stop_loss_percent / 100),
                            'take_profit': current_price * (1 + self.config.take_profit_percent / 100),
                            'timeframe': 'optimized',
                            'max_hold_days': self.max_hold_days,
                            'risk_level': 'MEDIUM'
                        })()

                        action = await self._execute_strategy_buy(stock, 'stock', signal)
                        if action:
                            actions.append(action)
                            existing_symbols.add(symbol)
                    else:
                        # Send Telegram alert for high-score opportunity that wasn't bought
                        if improved_score >= 6.0:
                            # Determine the main reason it wasn't bought
                            reason_not_bought = None
                            if not can_open:
                                reason_not_bought = "Sin capital o max posiciones alcanzado"
                            elif not can_trade:
                                reason_not_bought = f"Overtrading: {trade_reason}"
                            elif not (passes_volatility or self.high_volatility_bypass):
                                reason_not_bought = f"Alta volatilidad: {vol_reason}"
                            elif not score_passes:
                                reason_not_bought = f"Score {improved_score:.2f} < threshold {self.buy_score_threshold}"

                            try:
                                telegram_service.send_opportunity_alert(
                                    symbol=symbol,
                                    price=current_price,
                                    score=improved_score,
                                    position_type="LONG",
                                    reason_not_bought=reason_not_bought
                                )
                            except Exception as e:
                                logger.error(f"Failed to send Telegram opportunity alert for {symbol}: {e}")

                except Exception as e:
                    logger.error(f"Error evaluating buy signal for {symbol}: {e}")
                    continue
            
            # Process buy signals for cryptos with OPTIMIZED strategy
            logger.info(f"🔍 Processing {len(candidate_cryptos)} crypto candidates")
            for crypto in candidate_cryptos:
                symbol = crypto['symbol']
                current_price = crypto.get('current_price', 0)

                if symbol in existing_symbols:
                    logger.debug(f"⏭️  {symbol}: Already have position")
                    continue

                if len(actions) >= 10:
                    logger.info("🛑 Maximum 10 buys per cycle reached")
                    break

                filters_passed = {}
                filters_failed = {}
                scoring_breakdown = {}

                try:
                    # Filter 1: Overtrading prevention
                    can_trade, trade_reason = overtrading_prevention.can_trade_symbol(
                        symbol, 'crypto', 'buy'
                    )
                    filters_passed['overtrading'] = can_trade
                    if not can_trade:
                        filters_failed['overtrading'] = trade_reason

                    # Filter 2: Volatility check
                    passes_volatility, vol_reason = volatility_service.check_volatility_filter(
                        symbol, 'crypto_competition'
                    )
                    if passes_volatility or self.high_volatility_bypass:
                        filters_passed['volatility'] = True
                    else:
                        filters_failed['volatility'] = vol_reason

                    # Filter 3: Score calculation using improved scoring
                    if self.use_improved_scoring:
                        try:
                            import yfinance as yf
                            ticker = yf.Ticker(symbol)
                            hist = ticker.history(period="60d")

                            if not hist.empty:
                                improved_score = self.improved_scoring.calculate_crypto_score_from_data(hist)
                                scoring_breakdown = {
                                    'improved_score': improved_score,
                                    'method': 'ImprovedScoringService',
                                    'period': '60d'
                                }
                            else:
                                improved_score = crypto.get('score', 5.0)
                                scoring_breakdown = {
                                    'score': improved_score,
                                    'method': 'fallback',
                                    'reason': 'no_historical_data'
                                }
                        except Exception as e:
                            improved_score = crypto.get('score', 5.0)
                            scoring_breakdown = {
                                'score': improved_score,
                                'method': 'fallback',
                                'error': str(e)
                            }
                    else:
                        improved_score = crypto.get('score', 5.0)
                        scoring_breakdown = {'score': improved_score, 'method': 'traditional'}

                    # Filter 4: Score threshold
                    score_passes = improved_score >= self.buy_score_threshold
                    filters_passed['score_threshold'] = score_passes
                    if not score_passes:
                        filters_failed['score_threshold'] = f"Score {improved_score:.2f} < {self.buy_score_threshold}"

                    # Filter 5: Portfolio capacity
                    confidence = min(100, (improved_score - 5) * 10) if improved_score > 5 else 0
                    position_size = portfolio_manager.get_position_size('crypto', confidence)
                    can_open = portfolio_manager.can_open_position('crypto', position_size)
                    filters_passed['portfolio_capacity'] = can_open
                    if not can_open:
                        filters_failed['portfolio_capacity'] = "Insufficient capital or max positions reached"

                    # Determine if buy should execute
                    all_filters_passed = (
                        can_trade and
                        (passes_volatility or self.high_volatility_bypass) and
                        score_passes and
                        can_open
                    )

                    # Log buy evaluation
                    self.decision_logger.log_buy_evaluation(
                        symbol=symbol,
                        asset_type='crypto',
                        score=improved_score,
                        current_price=current_price,
                        action_taken='buy' if all_filters_passed else 'none',
                        filters_passed=filters_passed,
                        filters_failed=filters_failed,
                        scoring_breakdown=scoring_breakdown,
                        buy_threshold=self.buy_score_threshold,
                        confidence=confidence,
                        position_size=position_size if all_filters_passed else None
                    )

                    # Execute buy if all filters passed
                    if all_filters_passed:
                        # Create simplified signal object for execution
                        signal = type('Signal', (), {
                            'action': 'BUY',
                            'confidence': improved_score,
                            'symbol': symbol,
                            'score': improved_score,
                            'reasons': [f'Improved score: {improved_score:.2f}'],
                            'stop_loss': current_price * (1 - self.config.stop_loss_percent / 100),
                            'take_profit': current_price * (1 + self.config.take_profit_percent / 100),
                            'timeframe': 'optimized',
                            'max_hold_days': self.max_hold_days,
                            'risk_level': 'MEDIUM'
                        })()

                        action = await self._execute_strategy_buy(crypto, 'crypto', signal)
                        if action:
                            actions.append(action)
                            existing_symbols.add(symbol)
                    else:
                        # Send Telegram alert for high-score opportunity that wasn't bought
                        if improved_score >= 6.0:
                            # Determine the main reason it wasn't bought
                            reason_not_bought = None
                            if not can_open:
                                reason_not_bought = "Sin capital o max posiciones alcanzado"
                            elif not can_trade:
                                reason_not_bought = f"Overtrading: {trade_reason}"
                            elif not (passes_volatility or self.high_volatility_bypass):
                                reason_not_bought = f"Alta volatilidad: {vol_reason}"
                            elif not score_passes:
                                reason_not_bought = f"Score {improved_score:.2f} < threshold {self.buy_score_threshold}"

                            try:
                                telegram_service.send_opportunity_alert(
                                    symbol=symbol,
                                    price=current_price,
                                    score=improved_score,
                                    position_type="CRYPTO_LONG",
                                    reason_not_bought=reason_not_bought
                                )
                            except Exception as e:
                                logger.error(f"Failed to send Telegram opportunity alert for {symbol}: {e}")

                except Exception as e:
                    logger.error(f"Error evaluating buy signal for {symbol}: {e}")
                    continue
            
            # Check for SHORT signals - CONTROLLED BY BACKTEST PROVEN FLAG
            if self.short_trading_enabled:
                # Get low-scoring cryptos for SHORT signals
                low_score_cryptos = db_manager.execute_query(
                    "SELECT * FROM cryptos WHERE score < 3.5 ORDER BY score ASC LIMIT 5"
                )
                low_score_stocks = db_manager.execute_query(
                    "SELECT * FROM stocks WHERE score < 1.8 ORDER BY score ASC LIMIT 5"
                )
                    
                # Process SHORT signals for cryptos
                for crypto in low_score_cryptos:
                    if crypto['symbol'] not in existing_symbols and len(actions) < 10:
                        short_signal = self.evaluate_crypto_short_signals(crypto)
                        if short_signal:
                            action = await self._execute_short(crypto, short_signal)
                            if action:
                                actions.append(action)
                                existing_symbols.add(crypto['symbol'])
                
                # Process SHORT signals for stocks
                for stock in low_score_stocks:
                    if stock['symbol'] not in existing_symbols and len(actions) < 10:
                        short_signal = self.evaluate_stock_short_signals(stock)
                        if short_signal:
                            action = await self._execute_short(stock, short_signal)
                            if action:
                                actions.append(action)
                                existing_symbols.add(stock['symbol'])
            else:
                logger.info("SHORT trading disabled per backtest results - skipping all SHORT signals")
        
        except Exception as e:
            logger.error(f"Error checking buy signals: {str(e)}")
        
        return actions
    
    async def _execute_buy(self, asset_data: Dict[str, Any], asset_type: str, reason: str) -> Optional[Dict[str, Any]]:
        """Execute a buy order"""
        try:
            symbol = asset_data['symbol']
            current_price = asset_data['current_price']
            
            # Market timing validation for BUY orders
            buy_allowed, buy_reason = self.market_timing.is_trading_allowed("BUY")
            if not buy_allowed:
                logger.info(f"BUY order blocked for {symbol}: {buy_reason}")
                return None
            
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
            
            # Log transaction in both tables
            db_manager.execute_insert(
                """INSERT INTO autotrader_transactions 
                   (symbol, action, quantity, price, timestamp, reason)
                   VALUES (?, 'buy', ?, ?, ?, ?)""",
                (symbol, quantity, current_price, datetime.now().isoformat(), reason)
            )
            
            # Log transaction in portfolio_transactions for frontend
            portfolio_type = 'stocks' if asset_type == 'stock' else 'crypto'
            total_amount = quantity * current_price
            db_manager.execute_insert(
                """INSERT INTO portfolio_transactions 
                   (portfolio_type, symbol, action, quantity, price, total_amount, 
                    buy_reason, timestamp, source)
                   VALUES (?, ?, 'buy', ?, ?, ?, ?, ?, 'autotrader')""",
                (portfolio_type, symbol, quantity, current_price, total_amount, reason, 
                 datetime.now().isoformat())
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

            # Send Telegram notification
            try:
                score = asset_data.get('score', 0.0)
                remaining_capital = portfolio_manager.get_available_capital(asset_type)
                telegram_service.send_buy_notification(
                    symbol=symbol,
                    price=current_price,
                    quantity=int(quantity),
                    score=score,
                    total_value=value,
                    remaining_capital=remaining_capital,
                    position_type=asset_type.upper()
                )
            except Exception as e:
                logger.error(f"Failed to send Telegram buy notification: {e}")

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
            
            # Market timing validation for SELL orders
            sell_allowed, sell_reason = self.market_timing.is_trading_allowed("SELL")
            if not sell_allowed:
                logger.info(f"SELL order blocked for {symbol}: {sell_reason}")
                return None
            
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
            
            # Record trade action for overtrading prevention
            overtrading_prevention.record_trade_action(symbol, asset_type, "sell", current_price, pnl)
            
            # Remove position
            db_manager.execute_update(
                "DELETE FROM positions WHERE id = ?",
                (position['id'],)
            )
            
            # Log transaction and get the ID for P&L calculation
            sell_transaction_id = db_manager.execute_insert(
                """INSERT INTO autotrader_transactions 
                   (symbol, action, quantity, price, timestamp, reason)
                   VALUES (?, 'sell', ?, ?, ?, ?)""",
                (symbol, quantity, current_price, datetime.now().isoformat(), reason)
            )
            
            # Calculate and update realized P&L for this sell transaction
            if sell_transaction_id:
                try:
                    realized_pnl = self.pnl_service.calculate_and_update_pnl_for_sell(sell_transaction_id)
                    if realized_pnl is not None:
                        logger.info(f"P&L calculated for {symbol}: ${realized_pnl:.2f}")
                    else:
                        logger.warning(f"Could not calculate P&L for sell transaction {sell_transaction_id}")
                except Exception as e:
                    logger.error(f"Error calculating P&L for sell transaction {sell_transaction_id}: {e}")
            
            # Log transaction in portfolio_transactions for frontend
            portfolio_type = 'stocks' if position['type'] == 'stock' else 'crypto'
            total_amount = quantity * current_price
            db_manager.execute_insert(
                """INSERT INTO portfolio_transactions 
                   (portfolio_type, symbol, action, quantity, price, total_amount, 
                    sell_reason, timestamp, source)
                   VALUES (?, ?, 'sell', ?, ?, ?, ?, ?, 'autotrader')""",
                (portfolio_type, symbol, quantity, current_price, total_amount, reason, 
                 datetime.now().isoformat())
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

            # Send Telegram notification
            try:
                telegram_service.send_sell_notification(
                    symbol=symbol,
                    entry_price=entry_price,
                    exit_price=current_price,
                    quantity=int(quantity),
                    pnl=pnl,
                    pnl_percent=pnl_percent,
                    position_type=position.get('type', 'stock').upper()
                )
            except Exception as e:
                logger.error(f"Failed to send Telegram sell notification: {e}")

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
        """Get trading performance summary - ENHANCED with detailed stats"""
        try:
            # Get current positions with breakdown by type
            positions = db_manager.execute_query(
                """SELECT COUNT(*) as count, SUM(value) as total_value, 
                   SUM(pnl) as total_pnl, AVG(pnl_percent) as avg_pnl_percent,
                   type
                   FROM positions WHERE source = 'autotrader'
                   GROUP BY type"""
            )
            
            # Get overall totals
            total_positions = db_manager.execute_query(
                """SELECT COUNT(*) as count, SUM(value) as total_value, 
                   SUM(pnl) as total_pnl, AVG(pnl_percent) as avg_pnl_percent
                   FROM positions WHERE source = 'autotrader'"""
            )
            
            # Get transaction counts
            transaction_counts = db_manager.execute_query(
                """SELECT action, COUNT(*) as count 
                   FROM autotrader_transactions 
                   GROUP BY action"""
            )
            
            # Get recent transactions
            recent_transactions = db_manager.execute_query(
                """SELECT * FROM autotrader_transactions 
                   ORDER BY timestamp DESC LIMIT 10"""
            )
            
            # Get today's actions
            todays_actions = db_manager.execute_query(
                """SELECT action, COUNT(*) as count
                   FROM autotrader_transactions 
                   WHERE date(timestamp) = date('now')
                   GROUP BY action"""
            )
            
            # Process data
            total_data = total_positions[0] if total_positions else {}
            
            # Build action counts
            action_counts = {"buy": 0, "sell": 0, "short": 0}
            for tx in transaction_counts:
                action_counts[tx['action']] = tx['count']
            
            # Today's action counts
            today_counts = {"buy": 0, "sell": 0, "short": 0}
            for tx in todays_actions:
                today_counts[tx['action']] = tx['count']
            
            # Asset breakdown
            asset_breakdown = {"stock": {"count": 0, "value": 0, "pnl": 0}, 
                             "crypto": {"count": 0, "value": 0, "pnl": 0}}
            
            for pos in positions:
                asset_type = pos['type']
                asset_breakdown[asset_type] = {
                    "count": pos['count'],
                    "value": pos['total_value'] or 0,
                    "pnl": pos['total_pnl'] or 0
                }
            
            return {
                "current_positions": total_data.get('count', 0),
                "total_position_value": total_data.get('total_value', 0) or 0,
                "total_pnl": total_data.get('total_pnl', 0) or 0,
                "average_pnl_percent": total_data.get('avg_pnl_percent', 0) or 0,
                
                # Action counts (REAL data)
                "total_buy_actions": action_counts["buy"],
                "total_sell_actions": action_counts["sell"], 
                "total_short_actions": action_counts["short"],
                "total_actions": sum(action_counts.values()),
                
                # Today's activity
                "todays_buy_actions": today_counts["buy"],
                "todays_sell_actions": today_counts["sell"],
                "todays_short_actions": today_counts["short"],
                "todays_total_actions": sum(today_counts.values()),
                
                # Asset breakdown
                "asset_breakdown": asset_breakdown,
                
                # Recent activity
                "recent_transactions": [dict(tx) for tx in recent_transactions],
                
                # System parameters
                "max_positions": self.max_total_positions,
                "buy_threshold": self.buy_score_threshold,
                "sell_threshold": self.sell_score_threshold,
                
                # Status
                "last_updated": datetime.now().isoformat(),
                "status": "active" if total_data.get('count', 0) > 0 else "idle"
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
            
            # SHORT trading temporarily DISABLED - losing -17.64% avg
            if False and score < 1.8:  # Disabled based on performance analysis
                # required_capital = portfolio_manager.get_position_size('stock', (3 - score) * 25)
                # 
                # if portfolio_manager.can_open_position('stock', required_capital):
                #     return {
                #         'action': 'SHORT',
                #         'confidence': min(85, (3 - score) * 25),
                #         'reasons': [f'Very low score: {score}', 'Strong bearish signals'],
                #         'required_capital': required_capital
                #     }
                pass
            
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
            
            # Log transaction in both tables
            db_manager.execute_insert(
                """INSERT INTO autotrader_transactions 
                   (symbol, action, quantity, price, timestamp, reason)
                   VALUES (?, 'short', ?, ?, ?, ?)""",
                (symbol, quantity, current_price, datetime.now().isoformat(), reason)
            )
            
            # Log transaction in portfolio_transactions for frontend 
            portfolio_type = 'stocks' if asset_type == 'stock' else 'crypto'
            total_amount = quantity * current_price
            db_manager.execute_insert(
                """INSERT INTO portfolio_transactions 
                   (portfolio_type, symbol, action, quantity, price, total_amount, 
                    buy_reason, timestamp, source)
                   VALUES (?, ?, 'buy', ?, ?, ?, ?, ?, 'autotrader')""",
                (portfolio_type, symbol, quantity, current_price, total_amount, reason, 
                 datetime.now().isoformat())
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
    
    async def _analyze_stock_signal(self, stock_data: Dict[str, Any]) -> Optional[Any]:
        """Analyze stock using traditional pre-filtering + unified scoring for high-score candidates"""
        try:
            symbol = stock_data['symbol']
            current_price = stock_data['current_price']
            
            # STEP 1: Traditional pre-filtering (fast, no API calls)
            traditional_score = self.scoring_service.calculate_stock_score(stock_data)
            logger.debug(f"Traditional pre-filter for {symbol}: {traditional_score:.1f}")
            
            # Skip expensive unified analysis if traditional score is too low
            if traditional_score < self.buy_score_threshold:
                logger.debug(f"❌ Stock {symbol} skipped: traditional score {traditional_score:.1f} < {self.buy_score_threshold}")
                return None
            
            logger.info(f"✅ Stock {symbol} passed pre-filter: {traditional_score:.1f} >= {self.buy_score_threshold} - performing unified analysis")
            
            # STEP 2: Full unified scoring only for high-score candidates
            unified_result = self.unified_scoring.calculate_unified_score(
                symbol=symbol,
                asset_type='stock',
                market_data=stock_data
            )
            
            # Check unified score and filters
            unified_score = unified_result.get('unified_score', 0)
            trading_signal = unified_result.get('trading_signal', 'HOLD')
            monthly_filter_passed = unified_result.get('breakdown', {}).get('mtss', {}).get('monthly_filter_passed', False)
            confidence = unified_result.get('confidence', 0)
            
            logger.info(f"Stock {symbol}: Traditional={traditional_score:.1f}, Unified={unified_score:.2f}, Monthly={monthly_filter_passed}, Confidence={confidence:.1%}")
            
            # Decision logic: unified score must also pass threshold + monthly filter
            if (unified_score >= self.buy_score_threshold and 
                trading_signal == 'BUY' and 
                monthly_filter_passed and 
                confidence >= 0.5):
                
                # Convert unified result to signal format
                signal = type('Signal', (), {
                    'action': 'BUY',
                    'confidence': unified_score,
                    'symbol': symbol,
                    'traditional_score': traditional_score,
                    'unified_result': unified_result,
                    'reasons': unified_result.get('recommendations', {}).get('reasoning', []),
                    'stop_loss': unified_result.get('recommendations', {}).get('stop_loss'),
                    'take_profit': unified_result.get('recommendations', {}).get('take_profit')
                })()
                
                logger.info(f"🎯 Stock BUY signal for {symbol}: Traditional={traditional_score:.1f}, Unified={unified_score:.2f}")
                return signal
            else:
                logger.debug(f"❌ Stock {symbol} failed unified criteria: score={unified_score:.2f}, monthly={monthly_filter_passed}")
                return None
            
        except Exception as e:
            logger.error(f"Error analyzing stock signal for {symbol}: {e}")
            return None
    
    async def _analyze_crypto_signal(self, crypto_data: Dict[str, Any]) -> Optional[Any]:
        """Analyze crypto using traditional pre-filtering + unified scoring for high-score candidates"""
        try:
            symbol = crypto_data['symbol']
            current_price = crypto_data['current_price']
            
            # STEP 1: Traditional pre-filtering (fast, no API calls)
            traditional_score = self.scoring_service.calculate_crypto_score(crypto_data)
            logger.debug(f"Traditional pre-filter for {symbol}: {traditional_score:.1f}")
            
            # Skip expensive unified analysis if traditional score is too low
            if traditional_score < self.buy_score_threshold:
                logger.debug(f"❌ Crypto {symbol} skipped: traditional score {traditional_score:.1f} < {self.buy_score_threshold}")
                return None
            
            logger.info(f"✅ Crypto {symbol} passed pre-filter: {traditional_score:.1f} >= {self.buy_score_threshold} - performing unified analysis")
            
            # STEP 2: Full unified scoring only for high-score candidates
            unified_result = self.unified_scoring.calculate_unified_score(
                symbol=symbol,
                asset_type='crypto',
                market_data=crypto_data
            )
            
            # Check unified score and filters
            unified_score = unified_result.get('unified_score', 0)
            trading_signal = unified_result.get('trading_signal', 'HOLD')
            monthly_filter_passed = unified_result.get('breakdown', {}).get('mtss', {}).get('monthly_filter_passed', False)
            confidence = unified_result.get('confidence', 0)
            
            logger.info(f"Crypto {symbol}: Traditional={traditional_score:.1f}, Unified={unified_score:.2f}, Monthly={monthly_filter_passed}, Confidence={confidence:.1%}")
            
            # Decision logic: unified score must also pass threshold + monthly filter
            if (unified_score >= self.buy_score_threshold and 
                trading_signal == 'BUY' and 
                monthly_filter_passed and 
                confidence >= 0.5):
                
                # Convert unified result to signal format
                signal = type('Signal', (), {
                    'action': 'BUY',
                    'confidence': unified_score,
                    'symbol': symbol,
                    'traditional_score': traditional_score,
                    'unified_result': unified_result,
                    'reasons': unified_result.get('recommendations', {}).get('reasoning', []),
                    'stop_loss': unified_result.get('recommendations', {}).get('stop_loss'),
                    'take_profit': unified_result.get('recommendations', {}).get('take_profit')
                })()
                
                logger.info(f"🎯 Crypto BUY signal for {symbol}: Traditional={traditional_score:.1f}, Unified={unified_score:.2f}")
                return signal
            else:
                logger.debug(f"❌ Crypto {symbol} failed unified criteria: score={unified_score:.2f}, monthly={monthly_filter_passed}")
                return None
            
        except Exception as e:
            logger.error(f"Error analyzing crypto signal for {symbol}: {e}")
            return None
    
    async def _analyze_crypto_signal_mtss(self, crypto_data: Dict[str, Any]) -> Optional[Any]:
        """Analyze crypto using MTSS (Multi-Timeframe Scoring Strategy)"""
        try:
            symbol = crypto_data['symbol']
            current_price = crypto_data['current_price']
            
            logger.debug(f"MTSS Crypto analysis for {symbol} at ${current_price}")
            
            # Fetch multi-timeframe data for MTSS
            required_timeframes = self.mtss_crypto_strategy.get_required_timeframes()
            logger.debug(f"Fetching MTSS timeframes for {symbol}: {required_timeframes}")
            
            timeframe_data = {}
            for tf in required_timeframes:
                try:
                    data = self.timeframe_service.get_crypto_data(symbol, tf)
                    if data is not None and not data.empty:
                        timeframe_data[tf] = data
                        logger.debug(f"Fetched {len(data)} periods of {tf} data for {symbol}")
                    else:
                        logger.warning(f"No {tf} data available for {symbol}")
                except Exception as tf_error:
                    logger.warning(f"Could not fetch {tf} data for {symbol}: {tf_error}")
            
            if not timeframe_data:
                logger.warning(f"No timeframe data available for MTSS analysis of {symbol}")
                return None
            
            # Generate MTSS signal
            signal = self.mtss_crypto_strategy.generate_signal(symbol, current_price, timeframe_data)
            
            if signal.action == "BUY":
                logger.info(f"🎯 MTSS Crypto BUY signal for {symbol}: Score={signal.score:.2f}, Confidence={signal.confidence:.1f}")
                logger.info(f"MTSS Reasons: {', '.join(signal.reasons)}")
                return signal
            else:
                logger.debug(f"❌ MTSS Crypto {symbol}: {signal.action} (Score={signal.score:.2f}) - {', '.join(signal.reasons)}")
                return None
                
        except Exception as e:
            logger.error(f"Error in MTSS crypto analysis for {symbol}: {e}")
            return None
    
    async def _analyze_stock_exit_signal(self, position: Dict[str, Any]) -> Any:
        """Analyze stock exit using swing trading strategy"""
        try:
            symbol = position['symbol']
            entry_price = position['entry_price']
            current_price = position.get('current_price', entry_price)
            
            # Calculate days held
            from datetime import datetime
            created_at = position.get('created_at', datetime.now().isoformat())
            days_held = (datetime.now() - datetime.fromisoformat(created_at)).days
            
            # Fetch current multi-timeframe data
            required_timeframes = self.swing_strategy.get_required_timeframes()
            timeframe_data = {}
            
            for tf in required_timeframes:
                try:
                    data = self.timeframe_service.get_stock_data(symbol, tf)
                    if data is not None and not data.empty:
                        timeframe_data[tf] = data
                except Exception as e:
                    logger.warning(f"Failed to get {tf} data for {symbol}: {e}")
            
            # Use strategy's exit logic
            should_exit, reason = self.swing_strategy.should_exit_position(
                symbol, entry_price, current_price, days_held, "LONG", timeframe_data
            )
            
            return reason if should_exit else False
            
        except Exception as e:
            logger.error(f"Error analyzing stock exit signal for {symbol}: {e}")
            return False
    
    async def _analyze_crypto_exit_signal(self, position: Dict[str, Any]) -> Any:
        """Analyze crypto exit using competition strategy"""
        try:
            symbol = position['symbol']
            entry_price = position['entry_price']
            current_price = position.get('current_price', entry_price)
            
            # Calculate days held
            from datetime import datetime
            created_at = position.get('created_at', datetime.now().isoformat())
            days_held = (datetime.now() - datetime.fromisoformat(created_at)).days
            
            # Fetch current multi-timeframe data
            required_timeframes = self.crypto_strategy.get_required_timeframes()
            timeframe_data = {}
            
            for tf in required_timeframes:
                try:
                    data = self.timeframe_service.get_crypto_data(symbol, tf)
                    if data is not None and not data.empty:
                        timeframe_data[tf] = data
                except Exception as e:
                    logger.warning(f"Failed to get {tf} data for {symbol}: {e}")
            
            # Use strategy's exit logic
            should_exit, reason = self.crypto_strategy.should_exit_position(
                symbol, entry_price, current_price, days_held, "LONG", timeframe_data
            )
            
            return reason if should_exit else False
            
        except Exception as e:
            logger.error(f"Error analyzing crypto exit signal for {symbol}: {e}")
            return False
    
    async def _execute_strategy_buy(self, asset_data: Dict[str, Any], asset_type: str, signal: Any) -> Optional[Dict[str, Any]]:
        """Execute a buy order using strategy signal"""
        try:
            symbol = asset_data['symbol']
            current_price = asset_data['current_price']
            
            # Market timing validation for strategy BUY orders
            buy_allowed, buy_reason = self.market_timing.is_trading_allowed("BUY")
            if not buy_allowed:
                logger.info(f"Strategy BUY order blocked for {symbol}: {buy_reason}")
                return None
            
            if not current_price or current_price <= 0:
                logger.warning(f"Invalid price for {symbol}: {current_price}")
                return None
            
            # Use signal's suggested position size and risk level
            confidence = signal.confidence
            risk_level = getattr(signal, 'risk_level', 'MEDIUM')  # Default to MEDIUM if not present
            
            # Adjust position size based on risk level
            risk_multiplier = {"LOW": 1.2, "MEDIUM": 1.0, "HIGH": 0.8}.get(risk_level, 1.0)
            base_size = portfolio_manager.get_position_size(asset_type, confidence * 10)
            position_size = base_size * risk_multiplier
            
            if not portfolio_manager.can_open_position(asset_type, position_size):
                logger.info(f"Cannot open {asset_type} position for {symbol}: insufficient capital")
                return None
            
            # Calculate quantity
            quantity = position_size / current_price
            
            # Create position with strategy information
            position_id = str(uuid.uuid4())
            value = quantity * current_price
            now = datetime.now().isoformat()
            
            db_manager.execute_insert(
                """INSERT INTO positions 
                   (id, symbol, name, type, quantity, entry_price, current_price, 
                    value, pnl, pnl_percent, source, position_side, strategy_used, 
                    timeframe_primary, entry_score, stop_loss_updated, take_profit_updated, 
                    max_hold_days, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 'autotrader', 'LONG', ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    position_id, symbol, asset_data['name'], asset_type,
                    quantity, current_price, current_price, value,
                    signal.timeframe, signal.timeframe, signal.score,
                    signal.stop_loss, signal.take_profit, signal.max_hold_days,
                    now, now
                )
            )
            
            # Update portfolio manager
            portfolio_manager.execute_buy(symbol, current_price, quantity, asset_type)
            
            # Record trade action for overtrading prevention
            overtrading_prevention.record_trade_action(symbol, asset_type, "buy", current_price)
            
            # Create detailed reason from signal
            reasons_str = ", ".join(signal.reasons[:3])  # Top 3 reasons
            reason = f"{signal.timeframe} strategy: {reasons_str} (score: {signal.score:.1f})"
            
            # Log transaction
            db_manager.execute_insert(
                """INSERT INTO autotrader_transactions 
                   (symbol, action, quantity, price, timestamp, reason)
                   VALUES (?, 'buy', ?, ?, ?, ?)""",
                (symbol, quantity, current_price, datetime.now().isoformat(), reason)
            )
            
            # Log in portfolio transactions
            portfolio_type = 'stocks' if asset_type == 'stock' else 'crypto'
            total_amount = quantity * current_price
            db_manager.execute_insert(
                """INSERT INTO portfolio_transactions 
                   (portfolio_type, symbol, action, quantity, price, total_amount, 
                    buy_reason, timestamp, source)
                   VALUES (?, ?, 'buy', ?, ?, ?, ?, ?, 'autotrader')""",
                (portfolio_type, symbol, quantity, current_price, total_amount, reason, now)
            )
            
            action = {
                "action": "buy",
                "symbol": symbol,
                "type": asset_type,
                "quantity": quantity,
                "price": current_price,
                "value": value,
                "reason": reason,
                "strategy": signal.timeframe,
                "confidence": signal.confidence,
                "risk_level": getattr(signal, 'risk_level', 'MEDIUM'),
                "timestamp": now
            }
            
            logger.info(f"STRATEGY BUY: {symbol} ({asset_type}) - {quantity:.4f} @ ${current_price:.2f} - {reason}")
            return action
            
        except Exception as e:
            logger.error(f"Error executing strategy buy for {asset_data.get('symbol', 'unknown')}: {str(e)}")
            return None
    
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