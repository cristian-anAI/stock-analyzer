"""
Tests for main API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from ..main import app
from ..database.database import init_db

# Test client
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db():
    """Setup test database"""
    init_db()

def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Stock Analyzer API"
    assert data["version"] == "1.0.0"

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "stock-analyzer-api"

@patch('src.api.services.data_service.DataService.update_stocks_data')
def test_get_stocks(mock_update):
    """Test stocks endpoint"""
    mock_update.return_value = AsyncMock()
    
    response = client.get("/api/v1/stocks")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@patch('src.api.services.data_service.DataService.update_cryptos_data')
def test_get_cryptos(mock_update):
    """Test cryptos endpoint"""
    mock_update.return_value = AsyncMock()
    
    response = client.get("/api/v1/cryptos")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@patch('src.api.services.data_service.DataService.update_positions_prices')
def test_get_autotrader_positions(mock_update):
    """Test autotrader positions endpoint"""
    mock_update.return_value = AsyncMock()
    
    response = client.get("/api/v1/positions/autotrader")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@patch('src.api.services.data_service.DataService.update_positions_prices')
def test_get_manual_positions(mock_update):
    """Test manual positions endpoint"""
    mock_update.return_value = AsyncMock()
    
    response = client.get("/api/v1/positions/manual")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@patch('src.api.services.data_service.DataService.get_current_price')
def test_create_manual_position(mock_price):
    """Test creating manual position"""
    mock_price.return_value = 150.0
    
    position_data = {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "type": "stock",
        "quantity": 10,
        "entry_price": 150.0,
        "notes": "Test position"
    }
    
    response = client.post("/api/v1/positions/manual", json=position_data)
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["quantity"] == 10
    assert data["source"] == "manual"

def test_cors_headers():
    """Test CORS headers are present"""
    response = client.options("/api/v1/stocks")
    assert "access-control-allow-origin" in response.headers

def test_invalid_endpoint():
    """Test invalid endpoint returns 404"""
    response = client.get("/api/v1/invalid")
    assert response.status_code == 404