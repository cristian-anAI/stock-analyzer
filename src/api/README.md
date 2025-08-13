# Stock Analyzer API

Complete FastAPI backend for stock analysis and automated trading application.

## Features

### 📊 Stock Management
- **GET /api/v1/stocks** - Get all stocks with optional sorting by score
- **GET /api/v1/stocks/{symbol}** - Get specific stock data
- Real-time price updates from Yahoo Finance
- Automatic scoring system (1-10 scale with color coding)

### 💰 Cryptocurrency Management  
- **GET /api/v1/cryptos** - Get all cryptocurrencies with optional sorting
- **GET /api/v1/cryptos/{symbol}** - Get specific crypto data
- Real-time crypto price data
- Crypto-specific scoring algorithm

### 🤖 Autotrader Positions
- **GET /api/v1/positions/autotrader** - Get automated trading positions
- Automatic position management based on scores
- Buy signals for scores ≥ 8, sell signals for scores ≤ 4
- Transaction logging and performance tracking

### ✋ Manual Positions (Full CRUD)
- **GET /api/v1/positions/manual** - List manual positions
- **POST /api/v1/positions/manual** - Create new position
- **PUT /api/v1/positions/manual/{id}** - Update position
- **DELETE /api/v1/positions/manual/{id}** - Delete position

## Score Color System

- **Score > 8**: 🟢 Green (Strong Buy)
- **Score 6-8**: 🔵 Blue (Buy)  
- **Score 4-6**: 🟡 Yellow (Hold)
- **Score < 4**: 🔴 Red (Sell)

## Quick Start

### Local Development

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the API**
   ```bash
   cd src/api
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Access Documentation**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Docker Deployment

1. **Build and Run**
   ```bash
   cd src/api
   docker-compose up --build
   ```

2. **Production Deployment**
   ```bash
   docker-compose up -d
   ```

## API Endpoints

### Health & Status
```
GET /              - Root endpoint
GET /health        - Health check
```

### Stocks
```
GET /api/v1/stocks                     - Get all stocks
GET /api/v1/stocks?sort=score          - Get stocks sorted by score
GET /api/v1/stocks/{symbol}            - Get specific stock
POST /api/v1/stocks/refresh            - Refresh stock data
```

### Cryptocurrencies
```
GET /api/v1/cryptos                    - Get all cryptos
GET /api/v1/cryptos?sort=score         - Get cryptos sorted by score  
GET /api/v1/cryptos/{symbol}           - Get specific crypto
POST /api/v1/cryptos/refresh           - Refresh crypto data
```

### Positions
```
GET /api/v1/positions/autotrader       - Get autotrader positions
GET /api/v1/positions/manual           - Get manual positions
POST /api/v1/positions/manual          - Create manual position
PUT /api/v1/positions/manual/{id}      - Update manual position
DELETE /api/v1/positions/manual/{id}   - Delete manual position
POST /api/v1/positions/refresh         - Refresh position prices
```

## Data Structures

### Stock Response
```json
{
  "id": "string",
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "current_price": 150.25,
  "score": 8,
  "change": 2.50,
  "change_percent": 1.69,
  "volume": 50000000,
  "market_cap": 2500000000000,
  "sector": "Technology"
}
```

### Crypto Response
```json
{
  "id": "string", 
  "symbol": "BTC",
  "name": "Bitcoin",
  "current_price": 45000.00,
  "score": 9,
  "change": 1500.00,
  "change_percent": 3.45,
  "volume": 2000000000,
  "market_cap": 850000000000
}
```

### Position Response
```json
{
  "id": "string",
  "symbol": "AAPL", 
  "name": "Apple Inc.",
  "type": "stock",
  "quantity": 100,
  "entry_price": 145.00,
  "current_price": 150.25,
  "value": 15025.00,
  "pnl": 525.00,
  "pnl_percent": 3.62,
  "source": "manual",
  "notes": "Long-term investment"
}
```

### Create Position Request
```json
{
  "symbol": "AAPL",
  "name": "Apple Inc.", 
  "type": "stock",
  "quantity": 100,
  "entry_price": 145.00,
  "notes": "Optional notes"
}
```

## Configuration

### Environment Variables
- `PYTHONPATH` - Python path (set to `/app` in Docker)
- `PYTHONUNBUFFERED` - Unbuffered output (set to `1`)

### CORS Settings
Pre-configured for frontend at:
- `http://localhost:3000`
- `http://127.0.0.1:3000`

### Database
- **SQLite** database (`trading.db`)
- Automatic table creation on startup
- Support for stocks, cryptos, positions, and transaction logs

## Autotrader System

### Trading Logic
- **Buy Condition**: Score ≥ 8 and no existing position
- **Sell Condition**: Score ≤ 4 for existing positions
- **Position Limits**: Max 20 positions, max $10,000 per position
- **Rate Limiting**: Max 3 new positions per cycle

### Transaction Logging
All autotrader actions are logged with:
- Symbol, action (buy/sell), quantity, price
- Timestamp and reason for action
- P&L calculation for sells

## Testing

### Run Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest src/api/tests/

# Run with coverage
pytest src/api/tests/ --cov=src/api
```

### Test Structure
- `test_main.py` - API endpoint tests
- `test_services.py` - Service layer tests
- `conftest.py` - Test configuration and fixtures

## Scoring Algorithm

### Stock Scoring (1-10 scale)
- **Price Change (40%)**: +5% = +2pts, 0-2% = +0.5pts, -5% = -2pts
- **Volume (20%)**: >10M = +1pt, >1M = +0.5pts, <100K = -0.5pts  
- **Market Cap (20%)**: >100B = +1pt, 10-100B = +0.5pts, <1B = -0.5pts
- **Sector (20%)**: Tech = +1pt, Growth = +0.5pts

### Crypto Scoring (1-10 scale)
- **Price Change (50%)**: More volatile, ±10% thresholds
- **Volume (25%)**: >1B = +1.5pts, 100M-1B = +1pt
- **Market Cap (25%)**: >100B = +1.5pts, 10-100B = +1pt
- **Symbol Bonus**: Top cryptos (BTC, ETH, etc.) get bonus points

## Logging

### Log Files
- `logs/api.log` - Main application logs
- Console output in development mode
- Request ID tracking for debugging

### Log Levels
- **INFO**: Normal operations, request tracking
- **ERROR**: Errors and exceptions with full stack traces
- **DEBUG**: Detailed debugging information

## Security

### CORS Protection
- Restricted to specific frontend origins
- Credentials support enabled
- All methods and headers allowed for development

### Error Handling
- Generic error responses to prevent information leakage
- Full error logging for debugging
- Request ID correlation

## Monitoring

### Health Checks
- **Endpoint**: `GET /health`
- **Docker**: Built-in health check every 30s
- **Response**: `{"status": "healthy", "service": "stock-analyzer-api"}`

### Performance
- Request timing logged automatically
- Background data updates to minimize API response time
- Database connection pooling via context managers

## Development

### Project Structure
```
src/api/
├── main.py                 # FastAPI application
├── database/
│   └── database.py         # Database management
├── models/
│   └── schemas.py          # Pydantic models
├── routers/
│   ├── stocks.py           # Stock endpoints
│   ├── cryptos.py          # Crypto endpoints
│   └── positions.py        # Position endpoints
├── services/
│   ├── data_service.py     # External API integration
│   ├── scoring_service.py  # Scoring algorithms
│   └── autotrader_service.py # Automated trading
├── middleware/
│   ├── error_handler.py    # Error handling
│   └── logging_middleware.py # Request logging
└── tests/                  # Test suite
```

### Adding New Features

1. **New Endpoint**: Add to appropriate router
2. **New Service**: Create in `services/` directory  
3. **New Model**: Add to `models/schemas.py`
4. **New Tests**: Add to `tests/` directory

## Troubleshooting

### Common Issues

**Port 8000 already in use**
```bash
# Kill existing process
lsof -ti:8000 | xargs kill

# Or use different port
uvicorn main:app --port 8001
```

**Database locked**
```bash
# Stop all processes using the database
# Remove trading.db and restart (will recreate)
```

**API not accessible from frontend**
```bash
# Check CORS configuration in main.py
# Ensure frontend origin is in allow_origins list
```

### Debug Mode
```bash
# Enable debug logging
export PYTHONPATH=/path/to/project
uvicorn main:app --reload --log-level debug
```

## Production Deployment

### Docker Production
```bash
# Build production image
docker build -t stock-analyzer-api .

# Run with production settings
docker run -d \
  --name stock-analyzer-api \
  -p 8000:8000 \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/trading.db:/app/trading.db \
  stock-analyzer-api
```

### Performance Tuning
- Use `uvicorn` with multiple workers: `--workers 4`
- Enable Redis caching for frequent data
- Database connection pooling
- Rate limiting for external API calls

## Support

For issues and feature requests, please check the existing codebase or create an issue in the project repository.

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json