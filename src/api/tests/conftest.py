"""
Test configuration and fixtures
"""

import pytest
import tempfile
import os
from unittest.mock import patch

@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_db_path = f.name
    
    # Patch the database path
    with patch('src.api.database.database.DATABASE_PATH', temp_db_path):
        yield temp_db_path
    
    # Clean up
    if os.path.exists(temp_db_path):
        os.unlink(temp_db_path)

@pytest.fixture
def mock_yfinance():
    """Mock yfinance for consistent testing"""
    with patch('yfinance.Ticker') as mock:
        yield mock