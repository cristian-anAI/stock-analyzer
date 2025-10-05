#!/usr/bin/env python3
"""
Optimized Backtest Engine - Usa ImprovedScoringService y trailing stops
Basado en análisis de backtest real
"""

import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# Set database path
os.environ['SQLITE_DB_PATH'] = str(project_root / 'trading.db')

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging
from dataclasses import dataclass, field

from api.services.improved_scoring_service import ImprovedScoringService
from api.strategies.optimized_trading_config import OPTIMIZED_TRADING_CONFIG
from api.database.database import db_manager

logger = logging.getLogger(__name__)

@dataclass
class Position:
    """Represents an open position"""
    symbol: str
    asset_type: str
    position_side: str
    shares: float
    entry_price: float
    entry_date: datetime
    entry_score: float
    costs_paid: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    highest_price: float = 0.0  # For trailing stop
    trailing_stop_price: float = 0.0

@dataclass
class Trade:
    """Represents a completed trade"""
    symbol: str
    asset_type: str
    position_side: str
    shares: float
    entry_price: float
    entry_date: datetime
    entry_score: float
    exit_price: float
    exit_date: datetime
    exit_score: float
    exit_reason: str
    pnl: float
    pnl_pct: float
    days_held: int
    total_costs: float
    return_after_costs: float

@dataclass
class PortfolioState:
    """Portfolio state at a point in time"""
    date: datetime
    cash_stocks: float
    cash_crypto: float
    invested_stocks: float
    invested_crypto: float
    positions_count: int
    total_value: float

class OptimizedBacktestEngine:
    """
    Backtesting engine optimizado con:
    - ImprovedScoringService (momentum + trend strength)
    - Trailing stops basados en precio
    - Cooldowns para reducir overtrading
    - Holdings más largos (7-30 días)
    """

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        initial_capital_stocks: float = 70000.0,
        initial_capital_crypto: float = 30000.0
    ):
        self.start_date = start_date
        self.end_date = end_date

        # Portfolio state
        self.cash_stocks = initial_capital_stocks
        self.cash_crypto = initial_capital_crypto
        self.initial_capital_stocks = initial_capital_stocks
        self.initial_capital_crypto = initial_capital_crypto

        # Positions
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.daily_states: List[PortfolioState] = []

        # Services - USE IMPROVED SCORING
        self.scoring_service = ImprovedScoringService()
        self.config = OPTIMIZED_TRADING_CONFIG

        # Historical data storage
        self.historical_data: Dict[str, pd.DataFrame] = {}

        # Trading costs
        self.costs = {
            'commission_pct': 0.001,
            'slippage_pct': 0.001,
            'spread_pct': 0.0005,
        }

        # Cooldown tracking
        self.symbol_cooldowns: Dict[str, datetime] = {}

        logger.info(f"OptimizedBacktestEngine initialized: {start_date.date()} to {end_date.date()}")
        logger.info(f"Config: buy={self.config.buy_score_threshold}, sell={self.config.sell_score_threshold}")
        logger.info(f"Trailing stop: {self.config.trailing_stop_percent}%, Min hold: {self.config.swing_min_hold_days}d")

    def load_historical_data(self, symbols: List[str], progress_callback=None) -> None:
        """Load historical data for all symbols"""
        logger.info(f"Loading historical data for {len(symbols)} symbols...")

        buffer_days = 60
        fetch_start = self.start_date - timedelta(days=buffer_days)
        fetch_end = self.end_date + timedelta(days=1)

        for i, symbol in enumerate(symbols):
            if progress_callback:
                progress_callback(i, len(symbols), symbol)

            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(start=fetch_start, end=fetch_end, interval='1d')

                if len(data) > 50:
                    self.historical_data[symbol] = data
                    logger.debug(f"Loaded {len(data)} days for {symbol}")
                else:
                    logger.warning(f"Insufficient data for {symbol}")

            except Exception as e:
                logger.error(f"Error loading {symbol}: {e}")
                continue

        logger.info(f"Loaded data for {len(self.historical_data)} symbols")

    def get_data_before(self, symbol: str, date: datetime) -> Optional[pd.DataFrame]:
        """Get ONLY data available BEFORE a specific date"""
        if symbol not in self.historical_data:
            return None

        data = self.historical_data[symbol]

        # Handle timezone
        if data.index.tz is not None and date.tzinfo is None:
            date = date.replace(tzinfo=data.index.tz)
        elif data.index.tz is None and date.tzinfo is not None:
            date = date.replace(tzinfo=None)

        filtered = data[data.index < date]

        return filtered if len(filtered) > 0 else None

    def calculate_score_at_date(self, symbol: str, date: datetime, asset_type: str) -> Optional[float]:
        """
        Calculate score using IMPROVED scoring service
        Uses historical data for momentum and trend analysis
        """
        data_subset = self.get_data_before(symbol, date)

        if data_subset is None or len(data_subset) < 30:
            return None

        try:
            if asset_type == 'stock':
                score = self.scoring_service.calculate_stock_score_from_data(data_subset)
            else:
                score = self.scoring_service.calculate_crypto_score_from_data(data_subset)

            return score

        except Exception as e:
            logger.error(f"Error calculating score for {symbol} at {date}: {e}")
            return None

    def check_buy_signal(
        self,
        symbol: str,
        date: datetime,
        asset_type: str
    ) -> Tuple[bool, Optional[float], Optional[str]]:
        """Check if symbol has a buy signal"""
        # Check if already in position
        if symbol in self.positions:
            return False, None, "Already in position"

        # Check cooldown
        if symbol in self.symbol_cooldowns:
            if date < self.symbol_cooldowns[symbol]:
                days_left = (self.symbol_cooldowns[symbol] - date).days
                return False, None, f"Cooldown ({days_left} days left)"

        # Check portfolio limits
        if asset_type == 'stock':
            if len([p for p in self.positions.values() if p.asset_type == 'stock']) >= self.config.max_positions_stocks:
                return False, None, "Max stock positions reached"
        else:
            if len([p for p in self.positions.values() if p.asset_type == 'crypto']) >= self.config.max_positions_crypto:
                return False, None, "Max crypto positions reached"

        # Check capital
        capital = self.cash_stocks if asset_type == 'stock' else self.cash_crypto
        if capital < self.config.max_position_value:
            return False, None, "Insufficient capital"

        # Calculate score
        score = self.calculate_score_at_date(symbol, date, asset_type)

        if score is None:
            return False, None, "Could not calculate score"

        # Check threshold
        if score < self.config.buy_score_threshold:
            return False, score, f"Score {score:.1f} below threshold {self.config.buy_score_threshold}"

        return True, score, "Buy signal confirmed"

    def execute_buy(
        self,
        symbol: str,
        date: datetime,
        asset_type: str,
        score: float,
        price: float
    ) -> bool:
        """Execute buy order with REAL costs"""
        try:
            capital = self.cash_stocks if asset_type == 'stock' else self.cash_crypto
            position_size = min(self.config.max_position_value, capital * 0.15)

            # Apply costs
            slippage_cost = price * self.costs['slippage_pct']
            execution_price = price + slippage_cost

            shares = position_size / execution_price

            commission = position_size * self.costs['commission_pct']
            spread = position_size * self.costs['spread_pct']
            total_cost = (shares * execution_price) + commission + spread

            if total_cost > capital:
                return False

            # Calculate stop loss and take profit
            stop_loss = execution_price * (1 - self.config.stop_loss_percent / 100)
            take_profit = execution_price * (1 + self.config.take_profit_percent / 100)

            # Initialize trailing stop
            trailing_stop_price = execution_price * (1 - self.config.trailing_stop_percent / 100)

            position = Position(
                symbol=symbol,
                asset_type=asset_type,
                position_side='LONG',
                shares=shares,
                entry_price=execution_price,
                entry_date=date,
                entry_score=score,
                costs_paid=commission + spread,
                stop_loss=stop_loss,
                take_profit=take_profit,
                highest_price=execution_price,
                trailing_stop_price=trailing_stop_price
            )

            # Update capital
            if asset_type == 'stock':
                self.cash_stocks -= total_cost
            else:
                self.cash_crypto -= total_cost

            self.positions[symbol] = position

            logger.debug(f"BUY {symbol}: {shares:.2f} @ ${execution_price:.2f} (score={score:.1f})")

            return True

        except Exception as e:
            logger.error(f"Error executing buy for {symbol}: {e}")
            return False

    def check_sell_signal(
        self,
        position: Position,
        date: datetime,
        current_price: float
    ) -> Tuple[bool, Optional[float], Optional[str]]:
        """
        Check if position should be sold using OPTIMIZED logic:
        1. Trailing stop (priority)
        2. Take profit
        3. Stop loss
        4. Min hold time (don't sell before min days)
        5. Score threshold (only after min hold)
        """
        days_held = (date - position.entry_date).days

        # 1. Check minimum hold time
        if days_held < self.config.swing_min_hold_days:
            # Don't sell unless stop loss hit
            pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100

            if pnl_pct <= -self.config.stop_loss_percent:
                return True, None, f"Stop loss hit: {pnl_pct:.2f}%"

            return False, None, f"Min hold time not reached ({days_held}/{self.config.swing_min_hold_days})"

        # 2. Update trailing stop
        if current_price > position.highest_price:
            position.highest_price = current_price
            position.trailing_stop_price = current_price * (1 - self.config.trailing_stop_percent / 100)

        # 3. Check trailing stop
        if self.config.use_trailing_stop and current_price < position.trailing_stop_price:
            pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
            return True, None, f"Trailing stop hit: {pnl_pct:.2f}%"

        # 4. Check take profit
        pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
        if pnl_pct >= self.config.take_profit_percent:
            return True, None, f"Take profit hit: {pnl_pct:.2f}%"

        # 5. Check stop loss
        if pnl_pct <= -self.config.stop_loss_percent:
            return True, None, f"Stop loss hit: {pnl_pct:.2f}%"

        # 6. Check max hold time
        if days_held >= self.config.swing_max_hold_days:
            return True, None, f"Max hold time: {days_held} days"

        # 7. Check score (only after min hold time)
        current_score = self.calculate_score_at_date(position.symbol, date, position.asset_type)

        if current_score is not None and current_score <= self.config.sell_score_threshold:
            return True, current_score, f"Score dropped to {current_score:.1f}"

        return False, current_score, "Hold position"

    def execute_sell(
        self,
        position: Position,
        date: datetime,
        price: float,
        score: Optional[float],
        reason: str
    ) -> Trade:
        """Execute sell order with REAL costs"""
        try:
            slippage_cost = price * self.costs['slippage_pct']
            execution_price = price - slippage_cost

            gross_proceeds = position.shares * execution_price
            commission = gross_proceeds * self.costs['commission_pct']
            spread = gross_proceeds * self.costs['spread_pct']

            net_proceeds = gross_proceeds - commission - spread

            invested = position.shares * position.entry_price
            total_costs = position.costs_paid + commission + spread
            pnl = net_proceeds - invested - position.costs_paid
            pnl_pct = (pnl / invested) * 100
            return_after_costs = (net_proceeds / (invested + position.costs_paid) - 1) * 100

            days_held = (date - position.entry_date).days

            trade = Trade(
                symbol=position.symbol,
                asset_type=position.asset_type,
                position_side=position.position_side,
                shares=position.shares,
                entry_price=position.entry_price,
                entry_date=position.entry_date,
                entry_score=position.entry_score,
                exit_price=execution_price,
                exit_date=date,
                exit_score=score if score else 0.0,
                exit_reason=reason,
                pnl=pnl,
                pnl_pct=pnl_pct,
                days_held=days_held,
                total_costs=total_costs,
                return_after_costs=return_after_costs
            )

            # Update capital
            if position.asset_type == 'stock':
                self.cash_stocks += net_proceeds
            else:
                self.cash_crypto += net_proceeds

            self.trades.append(trade)

            # Add cooldown
            cooldown_date = date + timedelta(days=self.config.symbol_cooldown_days)
            self.symbol_cooldowns[position.symbol] = cooldown_date

            del self.positions[position.symbol]

            logger.debug(f"SELL {position.symbol}: P&L ${pnl:.2f} ({pnl_pct:+.2f}%) | {reason}")

            return trade

        except Exception as e:
            logger.error(f"Error executing sell for {position.symbol}: {e}")
            return None

    def run_day(self, date: datetime) -> Dict[str, Any]:
        """Run backtest for a single day"""
        day_results = {
            'date': date,
            'buys': [],
            'sells': [],
            'positions_checked': 0,
            'candidates_checked': 0
        }

        # Check existing positions for sell signals
        for symbol, position in list(self.positions.items()):
            day_results['positions_checked'] += 1

            data = self.get_data_before(symbol, date)
            if data is None or len(data) == 0:
                continue

            current_price = data.iloc[-1]['Close']

            should_sell, score, reason = self.check_sell_signal(position, date, current_price)

            if should_sell:
                trade = self.execute_sell(position, date, current_price, score, reason)
                if trade:
                    day_results['sells'].append(trade)

        # Check for buy signals
        for symbol in self.historical_data.keys():
            day_results['candidates_checked'] += 1

            asset_type = 'crypto' if '-USD' in symbol or 'BTC' in symbol or 'ETH' in symbol else 'stock'

            should_buy, score, reason = self.check_buy_signal(symbol, date, asset_type)

            if should_buy:
                data = self.get_data_before(symbol, date)
                if data is None or len(data) == 0:
                    continue

                current_price = data.iloc[-1]['Close']

                success = self.execute_buy(symbol, date, asset_type, score, current_price)
                if success:
                    day_results['buys'].append(symbol)

        self.record_daily_state(date)

        return day_results

    def record_daily_state(self, date: datetime) -> None:
        """Record current portfolio state"""
        invested_stocks = sum(
            p.shares * p.entry_price
            for p in self.positions.values()
            if p.asset_type == 'stock'
        )
        invested_crypto = sum(
            p.shares * p.entry_price
            for p in self.positions.values()
            if p.asset_type == 'crypto'
        )

        total_value = (
            self.cash_stocks + self.cash_crypto +
            invested_stocks + invested_crypto
        )

        state = PortfolioState(
            date=date,
            cash_stocks=self.cash_stocks,
            cash_crypto=self.cash_crypto,
            invested_stocks=invested_stocks,
            invested_crypto=invested_crypto,
            positions_count=len(self.positions),
            total_value=total_value
        )

        self.daily_states.append(state)

    def run_backtest(self) -> Dict[str, Any]:
        """Run complete backtest day by day"""
        logger.info("="*60)
        logger.info("STARTING OPTIMIZED BACKTEST")
        logger.info("="*60)

        current_date = self.start_date
        day_count = 0

        while current_date <= self.end_date:
            if current_date.weekday() < 5:
                day_results = self.run_day(current_date)

                if day_count % 30 == 0:
                    total_value = self.daily_states[-1].total_value if self.daily_states else 0
                    logger.info(f"Day {day_count}: {current_date.date()} | Portfolio: ${total_value:,.0f} | Positions: {len(self.positions)} | Trades: {len(self.trades)}")

                day_count += 1

            current_date += timedelta(days=1)

        self.close_all_positions(self.end_date)

        logger.info("="*60)
        logger.info("OPTIMIZED BACKTEST COMPLETE")
        logger.info("="*60)

        return self.get_results()

    def close_all_positions(self, date: datetime) -> None:
        """Close all open positions at end of backtest"""
        for symbol, position in list(self.positions.items()):
            data = self.get_data_before(symbol, date)
            if data is None or len(data) == 0:
                continue

            current_price = data.iloc[-1]['Close']
            score = self.calculate_score_at_date(symbol, date, position.asset_type)

            self.execute_sell(position, date, current_price, score, "Backtest end")

    def get_results(self) -> Dict[str, Any]:
        """Get backtest results"""
        final_state = self.daily_states[-1] if self.daily_states else None

        if not final_state:
            return {'error': 'No backtest data'}

        initial_capital = self.initial_capital_stocks + self.initial_capital_crypto
        final_value = final_state.total_value
        total_return_pct = ((final_value - initial_capital) / initial_capital) * 100

        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl <= 0]

        return {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'days_simulated': len(self.daily_states),
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return_pct': total_return_pct,
            'total_return_usd': final_value - initial_capital,
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': (len(winning_trades) / len(self.trades) * 100) if self.trades else 0,
            'avg_win': np.mean([t.pnl for t in winning_trades]) if winning_trades else 0,
            'avg_loss': np.mean([t.pnl for t in losing_trades]) if losing_trades else 0,
            'largest_win': max([t.pnl for t in self.trades]) if self.trades else 0,
            'largest_loss': min([t.pnl for t in self.trades]) if self.trades else 0,
            'avg_days_held': np.mean([t.days_held for t in self.trades]) if self.trades else 0,
            'total_costs_paid': sum([t.total_costs for t in self.trades]),
            'trades': self.trades,
            'daily_states': self.daily_states
        }
