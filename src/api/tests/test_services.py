"""
Tests for services
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from ..services.scoring_service import ScoringService
from ..services.data_service import DataService

class TestScoringService:
    """Test scoring service"""
    
    def setup_method(self):
        self.scoring_service = ScoringService()
    
    def test_calculate_stock_score_high_performance(self):
        """Test stock score calculation for high performance stock"""
        stock_data = {
            'symbol': 'AAPL',
            'current_price': 150.0,
            'change_percent': 8.0,  # High change
            'volume': 50000000,     # High volume
            'market_cap': 2500000000000,  # Large cap
            'sector': 'Technology'   # Tech sector
        }
        
        score = self.scoring_service.calculate_stock_score(stock_data)
        assert score >= 8  # Should be high score
        assert 1 <= score <= 10
    
    def test_calculate_stock_score_low_performance(self):
        """Test stock score calculation for low performance stock"""
        stock_data = {
            'symbol': 'TEST',
            'current_price': 10.0,
            'change_percent': -10.0,  # Negative change
            'volume': 50000,         # Low volume
            'market_cap': 500000000, # Small cap
            'sector': 'Other'
        }
        
        score = self.scoring_service.calculate_stock_score(stock_data)
        assert score <= 4  # Should be low score
        assert 1 <= score <= 10
    
    def test_calculate_crypto_score_high_performance(self):
        """Test crypto score calculation for high performance"""
        crypto_data = {
            'symbol': 'BTC',
            'current_price': 50000.0,
            'change_percent': 15.0,  # High change
            'volume': 2000000000,    # High volume
            'market_cap': 1000000000000  # Large market cap
        }
        
        score = self.scoring_service.calculate_crypto_score(crypto_data)
        assert score >= 8  # Should be high score
        assert 1 <= score <= 10
    
    def test_calculate_crypto_score_low_performance(self):
        """Test crypto score calculation for low performance"""
        crypto_data = {
            'symbol': 'UNKNOWN',
            'current_price': 0.001,
            'change_percent': -20.0,  # Large negative change
            'volume': 10000,         # Low volume
            'market_cap': 1000000    # Small market cap
        }
        
        score = self.scoring_service.calculate_crypto_score(crypto_data)
        assert score <= 4  # Should be low score
        assert 1 <= score <= 10
    
    def test_get_score_color(self):
        """Test score color classification"""
        assert self.scoring_service.get_score_color(9) == "green"
        assert self.scoring_service.get_score_color(7) == "blue"
        assert self.scoring_service.get_score_color(5) == "yellow"
        assert self.scoring_service.get_score_color(3) == "red"

class TestDataService:
    """Test data service"""
    
    def setup_method(self):
        self.data_service = DataService()
    
    @patch('yfinance.Ticker')
    @pytest.mark.asyncio
    async def test_get_current_price_stock(self, mock_ticker):
        """Test getting current price for stock"""
        # Mock yfinance response
        mock_history = Mock()
        mock_history.empty = False
        mock_history.__getitem__ = Mock(return_value=Mock(iloc=[-1]))
        mock_history['Close'].iloc.__getitem__ = Mock(return_value=150.0)
        
        mock_ticker_instance = Mock()
        mock_ticker_instance.history.return_value = mock_history
        mock_ticker.return_value = mock_ticker_instance
        
        price = await self.data_service.get_current_price('AAPL', 'stock')
        assert price == 150.0
    
    @patch('yfinance.Ticker')
    @pytest.mark.asyncio
    async def test_get_current_price_crypto(self, mock_ticker):
        """Test getting current price for crypto"""
        # Mock yfinance response
        mock_history = Mock()
        mock_history.empty = False
        mock_history.__getitem__ = Mock(return_value=Mock(iloc=[-1]))
        mock_history['Close'].iloc.__getitem__ = Mock(return_value=50000.0)
        
        mock_ticker_instance = Mock()
        mock_ticker_instance.history.return_value = mock_history
        mock_ticker.return_value = mock_ticker_instance
        
        price = await self.data_service.get_current_price('BTC', 'crypto')
        assert price == 50000.0
    
    @pytest.mark.asyncio
    async def test_get_current_price_invalid(self):
        """Test getting current price for invalid symbol"""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.side_effect = Exception("Invalid symbol")
            
            price = await self.data_service.get_current_price('INVALID', 'stock')
            assert price is None