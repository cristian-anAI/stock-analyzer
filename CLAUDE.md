# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Stock Analyzer is an advanced technical analysis and automated trading system for stocks and cryptocurrencies. It features a comprehensive FastAPI backend, multiple trading strategies, real-time monitoring, and both long and short position support.

## Architecture

### Core Structure
- **`/src/api/`** - FastAPI backend with routers, services, middleware, and database management
- **`/src/traders/`** - Trading systems (automated, hybrid, interactive, server, unified)
- **`/src/core/`** - Core components (database manager, position manager)
- **`/src/utils/`** - Utilities for database syncing and position management
- **`/src/web/`** - Web interfaces (dashboard, monitor)

### Key Services
- **`autotrader_service.py`** - Main autotrader with SHORT support and advanced scoring
- **`advanced_scoring_service.py`** - Advanced SHORT position scoring system
- **`portfolio_manager.py`** - Portfolio and position management
- **`risk_management_service.py`** - Risk assessment and management
- **`background_scheduler.py`** - Scheduled tasks and market monitoring

### Database
- SQLite database (`trading.db`) with positions, transactions, symbols, and portfolio data
- Database migrations handled in `/src/api/database/`
- Position types: LONG, SHORT, CRYPTO_LONG, CRYPTO_SHORT

### Trading Strategies
- **Base Strategy** - Abstract foundation for all trading strategies
- **Swing Trading Strategy** - Medium-term position trading
- **Crypto Competition Strategy** - Specialized crypto trading approach

## Common Commands

### Start the Application
```bash
# Main API server (recommended)
python run_api.py

# Alternative entry point with menu
python main.py

# Standalone autotrader
python start_autotrader.py
# or
start_autotrader.bat
```

### Testing
```bash
# Test complete SHORT system
python tools/testing/test_complete_short_system.py

# Test advanced scoring
python tools/testing/test_advanced_scoring.py

# Test alerts endpoint
python tools/testing/test_alerts_endpoint.py

# Run pytest suite
pytest src/api/tests/
```

### Analysis & Monitoring
```bash
# Analyze trading performance
python tools/analysis/analyze_performance.py

# Check all positions
python tools/analysis/check_all_positions.py

# Portfolio diagnostics
python tools/analysis/diagnose_portfolio_inconsistencies.py

# SHORT positions dashboard
python tools/dashboards/short_dashboard.py

# Portfolio dashboard
python tools/dashboards/portfolio_dashboard.py
```

### Maintenance
```bash
# Fix SHORT position stop losses
python tools/maintenance/fix_short_positions_stops.py

# Generate Excel reports
python tools/maintenance/generate_excel_reports.py

# Clean database
python tools/maintenance/fix_database.py

# Reset production database
python tools/maintenance/reset_production_database.py
```

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Debug alerts
python tools/debugging/debug_alerts.py
```

## Key Features

### Capital Allocation
- **Stocks**: $10,000 allocated capital
- **Crypto**: $50,000 allocated capital
- Supports both manual and automated position management

### SHORT Trading System
- Advanced scoring algorithm for SHORT position selection
- Risk management with stop-loss and take-profit levels
- Real-time monitoring via `/api/v1/short/positions` endpoint
- Dedicated SHORT dashboard for position tracking

### API Endpoints
- **Health**: `/health` - Service status
- **Positions**: `/api/v1/positions/*` - Position management
- **Portfolio**: `/api/v1/portfolio/*` - Portfolio tracking
- **Autotrader**: `/api/v1/autotrader/*` - Trading automation
- **SHORT Monitoring**: `/api/v1/short/*` - SHORT position tracking
- **Documentation**: `/docs` - Interactive API docs

### Data Sources
- Yahoo Finance (`yfinance`) for stock and crypto data
- Real-time price updates with caching via Redis
- Market hours detection for trading schedule compliance

## Development Notes

### Database Schema
- `positions` table tracks all trading positions
- `transactions` table logs all trading activity  
- `symbols` table manages watchlist and scoring data
- `portfolio_snapshots` table stores historical portfolio states

### Logging
- API logs: `logs/api.log`
- Console logs: `logs/api_console.log` 
- Structured logging with timestamp, component, and level

### Trading Hours
- Respects market hours (9:30 AM - 4:00 PM ET for stocks)
- Crypto trading operates 24/7
- Automatic suspension of API calls when markets are closed

### Environment Variables
- `ENVIRONMENT` - Set to "production" for production deployment
- `AUTOTRADER_ENABLED` - Enable/disable automated trading
- `LOG_LEVEL` - Logging verbosity

## Project Organization

### `/tools/` Directory Structure
- `/analysis/` - Performance and position analysis tools
- `/testing/` - Comprehensive test suite for all systems
- `/debugging/` - Debug utilities for troubleshooting
- `/maintenance/` - Database and system maintenance scripts  
- `/dashboards/` - Interactive monitoring dashboards

### `/docs/` Directory
- Main documentation and deployment guides
- SHORT system implementation docs
- Trading system expansion summaries

### `/archive/` Directory
- Historical reports and temporary files
- Legacy trading components kept for reference

## Advanced Systems

### Backtesting Framework
**CRITICAL**: The backtesting system has been extensively developed and proven with real performance data:

#### Key Backtesting Files
- **`backtest_simplified.py`** - Production-proven backtest engine
  - Based on successful `analyze_win_rate_profit.py` methodology
  - Implements rate limiting with leaky bucket pattern (60 calls/minute)
  - **PROVEN RESULTS**: 95.8% win rate (30d), 91.7% win rate (60d)
  - Uses exact thresholds: `buy_long_threshold = 6.0`, `sell_long_threshold = 4.0`
  - Generated 72 successful trades with high profitability

- **`run_1year_backtest.py`** - Enhanced long-term backtesting
  - **FIXED CRITICAL ISSUE**: Removed LIMIT 30 constraint to analyze all stocks
  - Dynamic scoring algorithm with multiple momentum periods
  - Advanced technical indicators (RSI, volatility, momentum confluence)
  - **CONFIGURATION PROVEN**: $10k position size, max 10 positions

- **`analyze_win_rate_profit.py`** - Performance validation engine
  - Real-time analysis of qualifying stocks with new thresholds
  - Historical performance validation across multiple timeframes
  - **THRESHOLD VALIDATION**: buy_long=6.0, sell_long=4.0, short=1.8

#### Critical Backtesting Insights
```python
# PROVEN THRESHOLDS (Sept 1, 2025 - Production Validated)
self.buy_score_threshold = 6.0   # Exact threshold from successful backtest
self.sell_score_threshold = 4.5  # Adjusted for better exit timing  
self.max_position_value = 10000  # $10k per position (same as backtest)
self.max_total_positions = 10    # Up to 10 positions (same as backtest)

# CRITICAL: Rate limiting implementation
self.max_calls_per_minute = 60   # Leaky bucket prevents API saturation
```

**AUTOTRADER INTEGRATION**: The production autotrader (`autotrader_service.py`) uses these exact proven parameters.

### LLaMA Training & Local AI System
**COMPREHENSIVE**: Advanced local AI training system for trading analysis:

#### Core LLaMA Integration Files
- **`local_ai/ollama_master_system.py`** - Master training orchestrator
  - Complete codebase knowledge extraction system
  - Equivalent to Claude Code but running locally
  - Auto-updating knowledge cache every 6 hours
  - Integrates Excel analysis, code knowledge, and real-time data

- **`local_ai/code_knowledge_extractor.py`** - Codebase intelligence
  - Extracts complete project structure and dependencies
  - Generates comprehensive context for LLaMA training
  - Maps all trading strategies, services, and database schemas

- **`local_ai/ollama_context_generator.py`** - Context generation
  - Creates training contexts from real trading data
  - Includes performance analysis and market conditions
  - Generates specialized prompts for trading decisions

#### LLaMA Training Data Sources
```python
# Real trading context files (generated automatically)
ollama_context_complete_20250831_203910.txt    # Complete system context
ollama_context_performance_20250831_200935.txt # Performance analysis context  
ollama_real_data_context_20250831_204658.txt   # Real market data context
```

#### Training Integration Features
- **Excel Analysis Integration**: `excel_analyzer.py` processes trading reports
- **Real-time Data Integration**: Live market data feeds into training contexts
- **Performance Feedback Loop**: Trading results automatically update training data
- **Quick Template System**: `quick_templates.py` for rapid context generation

### Critical Integration Points

#### Autotrader ↔ Backtesting
```python
# EXACT PARAMETER MAPPING from backtest to production
# backtest_simplified.py → autotrader_service.py
buy_long_threshold: 6.0      # Proven 95.8% win rate
max_position_value: $10,000  # Optimal risk/reward ratio
max_positions: 10            # Portfolio diversification limit
```

#### LLaMA ↔ Trading System  
```python
# Context generation from real trading performance
master_knowledge = {
    "code_knowledge": {},      # Complete system understanding
    "excel_analysis": {},      # Performance metrics integration
    "current_data": {},        # Real-time market conditions
    "context_templates": {}    # Training prompt optimization
}
```

**IMPORTANT**: When modifying trading parameters, always:
1. **Validate with backtesting first** using `backtest_simplified.py`
2. **Update LLaMA context** using `ollama_master_system.py`
3. **Test in production** with limited position sizes initially

## Recent Critical Fixes (September 2024)

### Autotrader Volatility System Fixes
**FIXED CRITICAL ISSUE**: TimeframeDataService `await` errors preventing trade execution:

```python
# BEFORE (BROKEN) - caused "object DataFrame can't be used in 'await' expression"
data = await self.timeframe_service.get_stock_data(symbol, tf)

# AFTER (FIXED) - TimeframeDataService methods are synchronous
data = self.timeframe_service.get_stock_data(symbol, tf)
```

### High Volatility Market Trading
**IMPLEMENTED**: Bypass system for extreme market volatility conditions:

```python
# NEW: High volatility bypass for market stress periods
self.high_volatility_bypass = True  # Allows trading during 55%+ market volatility

# Volatility filter with bypass logic
if not passes_volatility and not self.high_volatility_bypass:
    logger.debug(f"Volatility filter blocked {stock['symbol']}: {vol_reason}")
    continue
elif not passes_volatility and self.high_volatility_bypass:
    logger.info(f"High volatility bypass enabled - allowing {stock['symbol']} despite: {vol_reason}")
```

### Database Maintenance Tools
**CREATED**: `clean_database.py` - Comprehensive database cleanup system:

```python
# Complete transaction cleanup with automatic backup
tables_to_check = [
    'positions', 'transactions', 'autotrader_transactions', 
    'portfolio_transactions', 'portfolio_snapshots', 'portfolio_state'
]

# Automatic backup before cleanup
backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
```

### Portfolio Manager Enhancements
**ADDED**: Missing `get_total_portfolio_value()` method that was causing autotrader errors:

```python
def get_total_portfolio_value(self) -> float:
    """Get total portfolio value (liquid + invested + pnl)"""
    total_liquid = self.liquid_capital_stocks + self.liquid_capital_crypto
    total_invested = self.invested_capital_stocks + self.invested_capital_crypto
    total_pnl = self.total_pnl_stocks + self.total_pnl_crypto
    return total_liquid + total_invested + total_pnl
```

### Known Issues & Resolutions

#### Issue: "No daily data for NVDA"
**ROOT CAUSE**: Strategy requires multi-timeframe data (`'1d', '4h', '1h'`) but TimeframeDataService had async/sync conflicts.
**RESOLUTION**: Fixed all `await` calls with synchronous TimeframeDataService methods.

#### Issue: 0 Trades Generated Despite Qualifying Stocks
**ROOT CAUSE**: Multiple factors - volatility filters, data access errors, and async conflicts.
**RESOLUTION**: 
1. Implemented high volatility bypass
2. Fixed TimeframeDataService async errors
3. Enhanced logging for debugging

#### Issue: Market Stress Blocking All Trades
**MARKET CONDITIONS**: 55.1% symbols high volatility, 148.6% max volatility detected
**RESPONSE**: Implemented temporary bypass allowing qualified trades (score ≥ 6.0) during market stress.
- Memoriza la nueva forma de cambiar entre estrategias y la forma de guardar nuevas estrategias
- Memoriza todo lo que tenga que ver con el nuevo sistema