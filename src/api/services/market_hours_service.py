"""
Market Hours Service
Handles market hours validation to optimize API calls by avoiding closed markets
"""

from datetime import datetime, time, timezone
from typing import Dict, List, Optional, Tuple
import pytz
import logging

logger = logging.getLogger(__name__)

class MarketHoursService:
    """Service to manage market hours for different countries/exchanges"""
    
    def __init__(self):
        # Market configurations: exchange -> (timezone, market_hours, country)
        self.markets = {
            # US Markets
            'NASDAQ': {
                'timezone': 'America/New_York',
                'hours': [(time(9, 30), time(16, 0))],  # 9:30 AM - 4:00 PM ET
                'country': 'US',
                'weekdays_only': True
            },
            'NYSE': {
                'timezone': 'America/New_York', 
                'hours': [(time(9, 30), time(16, 0))],
                'country': 'US',
                'weekdays_only': True
            },
            'AMEX': {
                'timezone': 'America/New_York',
                'hours': [(time(9, 30), time(16, 0))],
                'country': 'US', 
                'weekdays_only': True
            },
            
            # European Markets
            'LSE': {  # London Stock Exchange
                'timezone': 'Europe/London',
                'hours': [(time(8, 0), time(16, 30))],  # 8:00 AM - 4:30 PM GMT
                'country': 'UK',
                'weekdays_only': True
            },
            'FRA': {  # Frankfurt Stock Exchange
                'timezone': 'Europe/Berlin',
                'hours': [(time(9, 0), time(17, 30))],  # 9:00 AM - 5:30 PM CET
                'country': 'DE',
                'weekdays_only': True
            },
            'EPA': {  # Euronext Paris
                'timezone': 'Europe/Paris',
                'hours': [(time(9, 0), time(17, 30))],
                'country': 'FR',
                'weekdays_only': True
            },
            
            # Asian Markets
            'TSE': {  # Tokyo Stock Exchange
                'timezone': 'Asia/Tokyo',
                'hours': [(time(9, 0), time(11, 30)), (time(12, 30), time(15, 0))],  # Split session
                'country': 'JP',
                'weekdays_only': True
            },
            'HKG': {  # Hong Kong Stock Exchange
                'timezone': 'Asia/Hong_Kong',
                'hours': [(time(9, 30), time(12, 0)), (time(13, 0), time(16, 0))],  # Split session
                'country': 'HK',
                'weekdays_only': True
            },
            
            # Other Markets
            'ASX': {  # Australian Securities Exchange
                'timezone': 'Australia/Sydney',
                'hours': [(time(10, 0), time(16, 0))],  # 10:00 AM - 4:00 PM AEST
                'country': 'AU',
                'weekdays_only': True
            },
            'TSX': {  # Toronto Stock Exchange
                'timezone': 'America/Toronto',
                'hours': [(time(9, 30), time(16, 0))],
                'country': 'CA',
                'weekdays_only': True
            }
        }
        
        # Stock symbol to exchange mapping (based on common patterns)
        self.symbol_to_exchange = {
            # US symbols (most common, default)
            'DEFAULT': 'NASDAQ',
        }
        
        # Country-specific symbol patterns
        self.symbol_patterns = {
            '.L': 'LSE',      # London: VOD.L
            '.F': 'FRA',      # Frankfurt: BMW.F  
            '.PA': 'EPA',     # Paris: MC.PA
            '.T': 'TSE',      # Tokyo: 7203.T
            '.HK': 'HKG',     # Hong Kong: 0700.HK
            '.AX': 'ASX',     # Australia: BHP.AX
            '.TO': 'TSX',     # Toronto: SHOP.TO
        }
        
        # Cache for symbol exchange mappings
        self._symbol_cache = {}
    
    def get_exchange_for_symbol(self, symbol: str) -> str:
        """Get the exchange for a given stock symbol"""
        if symbol in self._symbol_cache:
            return self._symbol_cache[symbol]
        
        # Check for country-specific suffixes
        for suffix, exchange in self.symbol_patterns.items():
            if symbol.endswith(suffix):
                self._symbol_cache[symbol] = exchange
                return exchange
        
        # Default to NASDAQ for US symbols
        exchange = self.symbol_to_exchange.get(symbol, 'NASDAQ')
        self._symbol_cache[symbol] = exchange
        return exchange
    
    def is_market_open(self, exchange: str, current_time: Optional[datetime] = None) -> bool:
        """Check if a specific market/exchange is currently open"""
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        if exchange not in self.markets:
            logger.warning(f"Unknown exchange: {exchange}, assuming open")
            return True
        
        market_config = self.markets[exchange]
        
        # Convert current time to market timezone
        market_tz = pytz.timezone(market_config['timezone'])
        market_time = current_time.astimezone(market_tz)
        
        # Check if it's a weekday (if required)
        if market_config.get('weekdays_only', True):
            if market_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
                return False
        
        # Check if current time falls within market hours
        current_time_only = market_time.time()
        
        for start_time, end_time in market_config['hours']:
            if start_time <= current_time_only <= end_time:
                return True
        
        return False
    
    def is_stock_market_open(self, symbol: str, current_time: Optional[datetime] = None) -> bool:
        """Check if the market for a specific stock symbol is open"""
        exchange = self.get_exchange_for_symbol(symbol)
        return self.is_market_open(exchange, current_time)
    
    def get_market_status(self, exchange: str, current_time: Optional[datetime] = None) -> Dict:
        """Get detailed market status information"""
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        if exchange not in self.markets:
            return {
                'exchange': exchange,
                'is_open': True,
                'status': 'unknown',
                'local_time': None,
                'next_open': None,
                'next_close': None
            }
        
        market_config = self.markets[exchange]
        market_tz = pytz.timezone(market_config['timezone'])
        market_time = current_time.astimezone(market_tz)
        
        is_open = self.is_market_open(exchange, current_time)
        
        return {
            'exchange': exchange,
            'is_open': is_open,
            'status': 'open' if is_open else 'closed',
            'country': market_config['country'],
            'local_time': market_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
            'timezone': market_config['timezone']
        }
    
    def get_all_open_markets(self, current_time: Optional[datetime] = None) -> List[str]:
        """Get list of all currently open markets"""
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        open_markets = []
        for exchange in self.markets.keys():
            if self.is_market_open(exchange, current_time):
                open_markets.append(exchange)
        
        return open_markets
    
    def should_update_stocks(self, symbols: List[str], current_time: Optional[datetime] = None) -> Tuple[List[str], List[str]]:
        """
        Determine which stocks should be updated based on market hours
        
        Returns:
            Tuple[List[str], List[str]]: (symbols_to_update, symbols_skipped)
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        symbols_to_update = []
        symbols_skipped = []
        
        for symbol in symbols:
            if self.is_stock_market_open(symbol, current_time):
                symbols_to_update.append(symbol)
            else:
                symbols_skipped.append(symbol)
        
        logger.info(f"Market hours check: {len(symbols_to_update)} symbols to update, {len(symbols_skipped)} symbols skipped")
        
        return symbols_to_update, symbols_skipped
    
    def add_custom_symbol_mapping(self, symbol: str, exchange: str):
        """Add custom symbol to exchange mapping"""
        self.symbol_to_exchange[symbol] = exchange
        self._symbol_cache[symbol] = exchange
        logger.info(f"Added custom mapping: {symbol} -> {exchange}")

# Global instance
market_hours_service = MarketHoursService()