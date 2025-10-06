"""
Box Strategy Backtesting System

A comprehensive backtesting framework for the Box/Opening Range intraday trading strategy.
"""

__version__ = "1.0.0"
__author__ = "Stock Analyzer Team"

from .data_loader import DataLoader
from .strategy import BoxStrategy, Direction, TradeStatus, BoxSetup, TradeEntry, TradeExit
from .backtester import BacktestEngine, TradeRecord
from .metrics import PerformanceMetrics
from .visualization import StrategyVisualizer

__all__ = [
    'DataLoader',
    'BoxStrategy',
    'BacktestEngine',
    'PerformanceMetrics',
    'StrategyVisualizer',
    'Direction',
    'TradeStatus',
    'BoxSetup',
    'TradeEntry',
    'TradeExit',
    'TradeRecord'
]
